"""Keep the approved skill namespace and provenance intact during future moves."""

import hashlib
import json
from pathlib import Path
import re
import subprocess

import yaml

ROOT = Path(__file__).resolve().parents[1]


def load_plan():
    return json.loads((ROOT / 'docs/skill-layout-migration.json').read_text())


def load_inventory():
    return json.loads((ROOT / 'docs/skill-sources.json').read_text())


def test_skill_entrypoints_share_one_namespace():
    actual = {str(p.relative_to(ROOT)) for p in (ROOT / 'skills').rglob('SKILL.md')}
    expected = {row['local_path'] for row in load_inventory()['files'] if row['kind'] == 'skill'}
    assert actual == expected
    names = []
    for path in sorted(actual):
        p = ROOT / path
        assert p.parent.parent == ROOT / 'skills', path
        frontmatter = yaml.safe_load(p.read_text().split('---', 2)[1])
        assert frontmatter['name'] == p.parent.name, path
        assert frontmatter['description']
        names.append(frontmatter['name'])
    assert len(names) == len(set(names))


def test_every_source_record_survives_layout_migration():
    plan = load_plan()
    inventory = load_inventory()
    records = {row['id']: row for row in inventory['files']}
    assert len(records) == len(inventory['files'])
    assert len({row['local_path'] for row in inventory['files']}) == len(records)
    for moved in plan['files']:
        record = records[moved['id']]
        assert moved['new_path'] in record['path_history']
        assert moved['old_path'] in record['path_history']
        p = ROOT / record['local_path']
        assert p.is_file(), record['local_path']
        assert hashlib.sha256(p.read_bytes()).hexdigest() == record['local_sha256']
        if record['current_owner_path']:
            assert (ROOT / record['current_owner_path']).is_file()
        if record['source_id'] != 'workbench':
            source, upstream_path = record['id'].split(':', 1)
            assert record['source_id'] == source
            assert record['upstream_path'] == upstream_path
            assert record['comparison_upstream_blob_sha']
    actual = {str(p.relative_to(ROOT)) for base in ['skills', 'third_party/skill-history']
              for p in (ROOT / base).rglob('*') if p.is_file() and p.name != '.DS_Store'}
    assert actual == {row['local_path'] for row in inventory['files']}


def test_inventory_dependency_locations_are_current():
    for edge in load_inventory()['dependencies']:
        source = ROOT / edge['from_path']
        assert source.is_file(), edge
        assert edge['target'] in source.read_text().splitlines()[edge['line'] - 1], edge
        if edge['status'] == 'resolved_local':
            assert (ROOT / edge['resolved_path']).exists(), edge


def test_index_links_every_canonical_skill_directly():
    index = ROOT / 'skills/README.md'
    targets = {str((index.parent / link).resolve().relative_to(ROOT))
               for link in re.findall(r'\]\(([^)]+/SKILL\.md)\)', index.read_text())}
    expected = {row['local_path'] for row in load_inventory()['files'] if row['kind'] == 'skill'}
    assert expected <= targets


def test_selected_upstream_methods_retain_pinned_sources_and_current_targets():
    inventory = load_inventory()
    records = {row['id']: row for row in inventory['files']}
    material = {row['local_path'] for row in records.values()}
    ledger = json.loads((ROOT / 'docs/skill-upstream-adoptions.json').read_text())
    assert len({row['id'] for row in ledger['adopted']}) == len(ledger['adopted'])
    for adoption in ledger['adopted']:
        source = ledger['sources'][adoption['source_id']]
        ref = adoption['comparison_ref']
        assert re.fullmatch(r'[0-9a-f]{40}', ref)
        prefix = f"https://github.com/{source['repository']}/blob/{ref}/"
        for upstream in adoption['upstream_files']:
            assert upstream['url'].startswith(prefix)
            assert re.fullmatch(r'[0-9a-f]{40}', upstream['blob_sha'])
            record = records[adoption['source_id'] + ':' + upstream['url'][len(prefix):]]
            # Later comparisons may advance while this adoption stays pinned.
            if inventory['sources'][adoption['source_id']]['comparison_ref'] == ref:
                assert record['comparison_upstream_blob_sha'] == upstream['blob_sha']
        assert adoption['local_paths']
        assert set(adoption['local_paths']) <= material


def test_inventory_files_are_not_hidden_by_gitignore():
    paths = [row['local_path'] for row in load_inventory()['files']]
    result = subprocess.run(
        ['git', 'check-ignore', '--no-index', '--stdin'], cwd=ROOT,
        input='\n'.join(paths) + '\n', text=True, capture_output=True,
    )
    assert result.returncode in (0, 1), result.stderr
    assert not result.stdout, result.stdout
