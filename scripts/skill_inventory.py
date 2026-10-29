"""Refresh/check repository skill provenance without fetching or executing source text."""

from __future__ import annotations

import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import posixpath
import re
import subprocess
from urllib.parse import unquote

ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / 'docs/skill-sources.json'
ROOTS = ('skills', 'third_party/skill-history')
PREFIXES = ('references/', 'assets/', '../', './', 'skills/', 'third_party/',
            'docs/', 'scripts/', 'data_sources/', '.claude/', '~/.claude/',
            'templates/', 'agents/', 'schema/', 'context/', 'strategy/', 'audits/',
            'projects/', '@context/', '${CLAUDE_PLUGIN_ROOT}/')


def git(*args: str) -> str:
    return subprocess.check_output(['git', *args], cwd=ROOT, text=True).strip()


def local_path(raw: str) -> Path:
    path = (ROOT / raw).resolve()
    if not path.is_relative_to(ROOT):
        raise ValueError(f'path outside repository: {raw}')
    return path


def material_paths() -> set[str]:
    result = subprocess.check_output(
        ['git', 'ls-files', '-z', '--cached', '--others', '--exclude-standard', '--', *ROOTS],
        cwd=ROOT,
    )
    return {raw for raw in result.decode().split('\0') if raw and local_path(raw).is_file()}


def dependencies(files: list[dict]) -> list[dict]:
    rows = []
    for record in files:
        path = record['local_path']
        if not path.endswith('.md'):
            continue
        fence = False
        for number, line in enumerate(local_path(path).read_text().splitlines(), 1):
            if re.match(r'^\s*(```|~~~)', line):
                fence = not fence
                continue
            matches = [('markdown_link', m[1]) for m in re.finditer(r'\]\(([^)\s]+)(?:\s+"[^"]*")?\)', line)]
            matches += [('backtick_path', m[1]) for m in re.finditer(r'(?<!`)`([^`]+)`(?!`)', line)
                        if m[1].startswith(PREFIXES) and not re.search(r'\s', m[1])]
            seen = set()
            for syntax, raw in matches:
                if raw in seen:
                    continue
                seen.add(raw)
                target = unquote(raw.split('#', 1)[0])
                resolved = None
                if not target or re.match(r'^[a-zA-Z][a-zA-Z0-9+.-]*:', target):
                    continue
                if fence or target in {'url', 'URL', 'SOUTH,WEST,NORTH,EAST'}:
                    status = 'example_reference'
                elif target.startswith(('@context/', 'context/', 'strategy/', 'audits/', 'projects/')):
                    status = 'project_context_reference'
                elif target.startswith(('${CLAUDE_PLUGIN_ROOT}/', '~/.claude/')):
                    status = 'upstream_runtime_reference'
                elif any(char in target for char in '<>*{}'):
                    status = 'template_reference'
                elif target.startswith('/'):
                    status = 'route_or_example'
                else:
                    rooted = target.startswith(('skills/', 'third_party/', 'docs/', 'scripts/', 'data_sources/', '.claude/'))
                    resolved = posixpath.normpath(target if rooted else str(Path(path).parent / target))
                    try:
                        exists = local_path(resolved).exists()
                    except ValueError:
                        status = 'outside_repository'
                    else:
                        status = 'resolved_local' if exists else 'upstream_runtime_reference' if target.startswith(('scripts/', 'data_sources/', '.claude/')) else 'missing_literal_target'
                rows.append({'from_path': path, 'line': number, 'syntax': syntax, 'target': raw,
                             'resolved_path': resolved, 'status': status})
    return rows


def unavailable_runtime_paths(files: list[dict]) -> list[str]:
    errors = []
    pattern = re.compile(r'(?:scripts|data_sources|agents|templates)/[\w./-]+\.(?:py|sh|md|html|json)\b')
    for row in files:
        path = row['local_path']
        if not path.startswith('skills/') or not path.endswith('.md'):
            continue
        for number, line in enumerate(local_path(path).read_text().splitlines(), 1):
            # A link to an upstream source file is attribution, not a local dependency.
            line = re.sub(r'https?://[^\s)>]+', '', line)
            # Markdown destinations are resolved by dependencies(), including
            # legitimate relative links into the preserved historical archive.
            line = re.sub(r'\[[^\]]*\]\([^)]+\)', '', line)
            for match in pattern.finditer(line):
                target = match[0]
                candidates = [ROOT / target, local_path(path).parent / target]
                if not any(p.is_relative_to(ROOT) and p.is_file() for p in candidates):
                    errors.append(f'{path}:{number}: unavailable runtime path: {target}')
    return errors


def render_tables(inventory: dict) -> str:
    lines = ['## 入口与上游文件映射', '']
    groups = [('superseo', 'skill'), ('claude-seo', 'skill'), ('seomachine', 'skill'),
              ('workbench', 'skill'), ('seomachine', 'specialist_reference'),
              ('seomachine', 'workflow_reference'), ('workbench', 'reference')]
    for source, kind in groups:
        files = [row for row in inventory['files'] if row['source_id'] == source and row['kind'] == kind]
        lines += [f'### {source} / {kind}（{len(files)}）', '',
                  '| 当前文件 | 固定版本中的上游路径／派生来源 | 内容比对 | 本地首次记录 |', '|---|---|---|---|']
        for row in files:
            path = row['local_path']
            if source == 'workbench':
                origin = '；'.join(row.get('derived_from', row.get('composed_from', []))) or 'Workbench 本地方法'
            else:
                spec = inventory['sources'][source]
                remote = row['upstream_path']
                origin = f"[{remote}](https://github.com/{spec['repository']}/blob/{spec['comparison_ref']}/{remote})"
            first = row['first_local_record'].get('commit')
            state = {'identical': '相同', 'different': '有差异', 'workbench_native': '本地方法'}[row['comparison_status']]
            first_label = f'`{first[:7]}`' if first else '本轮新增'
            lines.append(f'| [{path}](../{path}) | {origin} | {state} | {first_label} |')
        lines.append('')
    # Imported entrypoints retained as references still have an independent source record.
    retained = [r for r in inventory['files'] if r.get('original_kind') == 'skill' and r['kind'] == 'reference']
    lines += ['### 归入参考的来源方法', '', '| 当前文件 | 来源 ID |', '|---|---|']
    lines += [f"| [{r['local_path']}](../{r['local_path']}) | `{r['id']}` |" for r in retained]
    return '\n'.join(lines).rstrip() + '\n'


def render_summary(inventory: dict) -> str:
    rows = ['## 当前清点范围', '', '| 来源 | 全部文件 | 活跃技能 | 专家原文 | 流程原文 | 与上游相同 | 与上游有差异 |', '|---|---:|---:|---:|---:|---:|---:|']
    for source in ['superseo', 'claude-seo', 'seomachine', 'workbench']:
        files = [r for r in inventory['files'] if r['source_id'] == source]
        kinds = Counter(r['kind'] for r in files)
        states = Counter(r['comparison_status'] for r in files)
        rows.append(f"| {source} | {len(files)} | {kinds['skill']} | {kinds['specialist_reference']} | {kinds['workflow_reference']} | {states['identical'] if source != 'workbench' else '不适用'} | {states['different'] if source != 'workbench' else '不适用'} |")
    summary = inventory['summary']
    rows += [f"| 合计 | **{summary['tracked_files']}** | **{summary['by_kind']['skill']}** | **11** | **24** | **{summary['by_comparison_status']['identical']}** | **{summary['by_comparison_status']['different']}** |", '',
             '原有 364 个文件的来源 ID 全部保留。新增组合入口和适配参考分别登记为 Workbench 文件，并通过 composed_from 或 derived_from 关联原记录；历史专家与流程原文保留在 third_party/skill-history。', '',
             'JSON 覆盖 skills/ 和 third_party/skill-history/ 的受维护文件，不含系统文件或店铺私有技能。指纹包括换行、路径和适配差异；different 只表示内容不同，不能全部解释为上游升级。', '']
    return '\n'.join(rows) + '\n'


def committed_blob(commit: str, path: str) -> bytes | None:
    """Read a Git blob as bytes; a new/untracked path has no committed blob."""
    result = subprocess.run(['git', 'show', f'{commit}:{path}'], cwd=ROOT,
                            stdout=subprocess.PIPE, stderr=subprocess.DEVNULL)
    return result.stdout if result.returncode == 0 else None


def history_record(paths: list[str], *, first: bool = False) -> dict | None:
    options = ['--reverse', '--diff-filter=A'] if first else ['-1']
    process = subprocess.run(['git', 'log', *options, '--format=%H%x09%ad%x09%s',
                              '--date=short', '--name-only', '--', *paths], cwd=ROOT,
                             stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    if process.returncode:
        head = subprocess.run(['git', 'rev-parse', '--verify', 'HEAD'], cwd=ROOT,
                              stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        if head.returncode:
            return None
        process.check_returncode()
    if not process.stdout.strip():
        return None
    lines = process.stdout.strip().splitlines()
    commit, date, subject = lines[0].split('\t', 2)
    changed = []
    for line in lines[1:]:
        if '\t' in line:
            break
        if line:
            changed.append(line)
    path = next((path for path in reversed(paths) if path in changed), paths[-1])
    return {'commit': commit, 'date': date, 'subject': subject, 'path': path,
            'record_status': 'committed'}


def refresh_history(row: dict, data: bytes) -> None:
    """Preserve source identity while deriving history fields from real Git data."""
    path = row['local_path']
    paths = list(dict.fromkeys([*row.get('path_history', []), path]))
    first = row['first_local_record']
    if first.get('commit') is None:
        committed_first = history_record(paths, first=True)
        if committed_first:
            row['first_local_record'] = first = committed_first
    latest = history_record(paths)
    if latest:
        row['last_local_change'] = latest
    baseline = committed_blob(first['commit'], first.get('path', path)) if first.get('commit') else None
    row['content_changed_since_first_local_record'] = data != baseline if baseline is not None else None
    head = committed_blob('HEAD', path)
    row['workingtree_modified'] = head is None or data != head


def refresh(inventory: dict, register: list[str]) -> None:
    material = material_paths()
    known = {r['local_path'] for r in inventory['files']}
    registry_path = ROOT / 'docs/skill-method-adaptations.json'
    adaptations = json.loads(registry_path.read_text())['materials'] if registry_path.exists() else []
    derived = {r['adapted_path']: r for r in adaptations if r.get('adapted_path')}
    allowed = set(register) | set(derived)
    if material - known - allowed:
        raise ValueError(f'unregistered material: {sorted(material - known - allowed)}')
    if known - material:
        raise ValueError(f'missing or ignored provenance material: {sorted(known - material)}')
    for path in sorted(material - known):
        owner = derived[path]['owner_path'] if path in derived else next(
            (str(p / 'SKILL.md') for p in local_path(path).parents
             if p.is_relative_to(ROOT) and (p / 'SKILL.md').is_file()), None)
        if owner and Path(owner).is_absolute():
            owner = str(Path(owner).relative_to(ROOT))
        introduced = {'commit': None, 'date': '2026-10-29', 'path': path,
                      'subject': 'Workbench method adaptation', 'record_status': 'introduced_in_current_change'}
        inventory['files'].append({'id': 'workbench:' + path, 'local_path': path, 'path_history': [path],
            'kind': 'reference' if '/references/' in path else 'index',
            'capability': Path(owner).parent.name if owner else 'source-history', 'current_owner_path': owner,
            'source_id': 'workbench', 'upstream_path': None, 'baseline_status': 'workbench_native',
            'imported_upstream_commit': None, 'comparison_upstream_blob_sha': None,
            'comparison_status': 'workbench_native', 'first_local_record': introduced.copy(),
            'last_local_change': introduced.copy(), 'content_changed_since_first_local_record': False,
            'semantic_review': 'portable_method_adaptation', 'declared_attribution': [],
            'derived_from': [derived[path]['source_id']] if path in derived else []})
    records = {r['id']: r for r in inventory['files']}
    for row in inventory['files']:
        path = row['local_path']
        data = local_path(path).read_bytes()
        digest = hashlib.sha256(data).hexdigest()
        refresh_history(row, data)
        row['local_sha256'] = digest
        row['local_git_blob_sha'] = hashlib.sha1(b'blob ' + str(len(data)).encode() + b'\0' + data).hexdigest()
        row['comparison_status'] = 'workbench_native' if row['source_id'] == 'workbench' else 'identical' if row['local_git_blob_sha'] == row['comparison_upstream_blob_sha'] else 'different'
        row['maintenance_status'] = 'historical_source' if path.startswith('third_party/skill-history/') else 'active'
    for adapter in adaptations:
        row = records[adapter['source_id']]
        row['adapted_by'] = ['workbench:' + adapter['adapted_path']] if adapter.get('adapted_path') else []
        row['adaptation_disposition'] = adapter['disposition']
    inventory['files'].sort(key=lambda r: r['local_path'])
    inventory['dependencies'] = dependencies(inventory['files'])
    inventory['local_snapshot_commit'] = git('rev-parse', 'HEAD')
    inventory['dependency_scan'] = 'Literal Markdown/inline paths; fenced examples are classified separately. No source text is executed.'
    inventory['operation'] = 'method_adaptation_inventory'
    inventory['summary'] = {'tracked_files': len(inventory['files']),
        'by_source': dict(sorted(Counter(r['source_id'] for r in inventory['files']).items())),
        'by_kind': dict(sorted(Counter(r['kind'] for r in inventory['files']).items())),
        'by_comparison_status': dict(sorted(Counter(r['comparison_status'] for r in inventory['files']).items())),
        'dependency_occurrences': len(inventory['dependencies']),
        'dependencies_by_status': dict(sorted(Counter(r['status'] for r in inventory['dependencies']).items()))}
    MANIFEST.write_text(json.dumps(inventory, ensure_ascii=False, indent=2) + '\n')
    doc = ROOT / 'docs/skill-sources.md'
    text = doc.read_text().split('## 入口与上游文件映射')[0]
    start = text.index('## 当前清点范围')
    end = text.index('当前上游而本地尚无对应入口的技能：')
    text = text[:start] + render_summary(inventory) + text[end:]
    text = re.sub(r'当前 \d+ 个受维护文件均有记录[：；][^\n]+',
                  f"当前 {len(inventory['files'])} 个受维护文件均有记录；原材料与派生方法保持独立来源身份。", text)
    text = re.sub(r'当前登记 \d+ 处字面路径引用：', f"当前登记 {len(inventory['dependencies'])} 处字面路径引用：", text)
    doc.write_text(text.rstrip() + '\n\n' + render_tables(inventory))


def check(inventory: dict, strict: bool) -> list[str]:
    errors = []
    files = inventory['files']
    recorded = {r['local_path'] for r in files}
    if recorded != material_paths():
        errors.append('material coverage differs from inventory')
    if len(recorded) != len(files) or len({r['id'] for r in files}) != len(files):
        errors.append('duplicate local path or source ID')
    for row in files:
        path = local_path(row['local_path'])
        if not path.is_file() or hashlib.sha256(path.read_bytes()).hexdigest() != row['local_sha256']:
            errors.append('stale or missing file: ' + row['local_path'])
    available = [row for row in files if local_path(row['local_path']).is_file()]
    actual = dependencies(available)
    if actual != inventory['dependencies']:
        errors.append('dependency inventory is stale')
    if strict:
        errors += [f"{r['from_path']}:{r['line']}: {r['status']}: {r['target']}" for r in actual
                   if r['from_path'].startswith('skills/') and r['status'] in
                   {'missing_literal_target', 'upstream_runtime_reference', 'outside_repository'}]
        errors += unavailable_runtime_paths(available)
    return errors


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=['check', 'refresh'])
    parser.add_argument('--register-workbench', action='append', default=[])
    parser.add_argument('--strict-active', action='store_true')
    args = parser.parse_args()
    inventory = json.loads(MANIFEST.read_text())
    if args.action == 'refresh':
        refresh(inventory, args.register_workbench)
    errors = check(inventory, args.strict_active)
    print(json.dumps({'ok': not errors, 'files': len(inventory['files']), 'errors': errors}, ensure_ascii=False, indent=2))
    return 1 if errors else 0


if __name__ == '__main__':
    raise SystemExit(main())
