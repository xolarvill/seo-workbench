"""Exercise inventory boundaries and actual references, without accessing providers."""

from pathlib import Path
import json

import pytest

from scripts import skill_inventory


def test_active_skills_have_resolvable_execution_dependencies():
    inventory = json.loads(skill_inventory.MANIFEST.read_text())
    assert skill_inventory.check(inventory, strict=True) == []


def test_inventory_rejects_paths_outside_repository(tmp_path, monkeypatch):
    monkeypatch.setattr(skill_inventory, 'ROOT', tmp_path)
    with pytest.raises(ValueError, match='outside repository'):
        skill_inventory.local_path('../outside.md')


def test_dependency_scan_distinguishes_real_targets_context_and_examples(tmp_path, monkeypatch):
    monkeypatch.setattr(skill_inventory, 'ROOT', tmp_path)
    folder = tmp_path / 'skills/example'
    folder.mkdir(parents=True)
    (folder / 'reference.md').write_text('available')
    (folder / 'SKILL.md').write_text(
        '[reference](reference.md)\n[missing](missing.md)\n'
        '`context/brand-voice.md`\n```markdown\n[example](example.md)\n```\n'
    )
    records = skill_inventory.dependencies([{'local_path': 'skills/example/SKILL.md'}])
    assert {r['target']: r['status'] for r in records} == {
        'reference.md': 'resolved_local', 'missing.md': 'missing_literal_target',
        'context/brand-voice.md': 'project_context_reference', 'example.md': 'example_reference',
    }


def test_runtime_scan_checks_real_scripts_and_ignores_remote_source_urls(tmp_path, monkeypatch):
    monkeypatch.setattr(skill_inventory, 'ROOT', tmp_path)
    folder = tmp_path / 'skills/example'
    folder.mkdir(parents=True)
    (tmp_path / 'scripts').mkdir()
    (tmp_path / 'scripts/local.py').write_text('pass\n')
    (folder / 'SKILL.md').write_text(
        'python scripts/missing.py\npython scripts/local.py\n'
        '[source](https://github.com/example/repo/blob/main/scripts/upstream.py)\n'
        '[original](../../third_party/agents/editor.md)\n'
    )
    errors = skill_inventory.unavailable_runtime_paths([{'local_path': 'skills/example/SKILL.md'}])
    assert len(errors) == 1
    assert 'scripts/missing.py' in errors[0]


@pytest.fixture
def history_repo(tmp_path, monkeypatch):
    import subprocess

    monkeypatch.setattr(skill_inventory, 'ROOT', tmp_path)

    def run(*args):
        return subprocess.check_output(['git', '-c', 'user.name=Skill Inventory Test',
                                        '-c', 'user.email=skill-test@example.invalid', *args],
                                       cwd=tmp_path, text=True).strip()

    run('init', '-q')
    return tmp_path, run


def test_history_refresh_tracks_commits_renames_and_reverted_content(history_repo):
    root, run = history_repo
    old = 'skills/old/SKILL.md'
    current = 'skills/current/SKILL.md'
    original = b'# Original\n'
    (root / old).parent.mkdir(parents=True)
    (root / old).write_bytes(original)
    run('add', '.')
    run('commit', '-qm', 'feat: first source')
    first_sha = run('rev-parse', 'HEAD')
    first = {'commit': first_sha, 'path': old, 'subject': 'feat: first source'}
    row = {'local_path': current, 'path_history': [old, current],
           'first_local_record': first.copy(), 'last_local_change': first.copy(),
           'content_changed_since_first_local_record': True}
    (root / current).parent.mkdir(parents=True)
    run('mv', old, current)
    (root / current).write_text('# Revised\n')
    run('add', '.')
    run('commit', '-qm', 'refactor: move and adapt')
    latest_sha = run('rev-parse', 'HEAD')
    skill_inventory.refresh_history(row, (root / current).read_bytes())
    assert row['first_local_record'] == first
    assert row['last_local_change']['commit'] == latest_sha
    assert row['last_local_change']['path'] == current
    assert row['last_local_change']['subject'] == 'refactor: move and adapt'
    assert row['content_changed_since_first_local_record'] is True
    assert row['workingtree_modified'] is False

    (root / current).write_bytes(original)
    skill_inventory.refresh_history(row, original)
    assert row['last_local_change']['commit'] == latest_sha
    assert row['content_changed_since_first_local_record'] is False
    assert row['workingtree_modified'] is True


def test_history_refresh_distinguishes_new_uncommitted_and_committed_material(history_repo):
    root, run = history_repo
    path = 'skills/new/reference.md'
    (root / path).parent.mkdir(parents=True)
    (root / path).write_text('# New method\n')
    introduced = {'commit': None, 'path': path, 'record_status': 'introduced_in_current_change'}
    row = {'local_path': path, 'path_history': [path],
           'first_local_record': introduced.copy(), 'last_local_change': introduced.copy()}
    skill_inventory.refresh_history(row, (root / path).read_bytes())
    assert row['first_local_record']['commit'] is None
    assert row['last_local_change']['commit'] is None
    assert row['content_changed_since_first_local_record'] is None
    assert row['workingtree_modified'] is True

    run('add', '.')
    run('commit', '-qm', 'feat: add new method')
    skill_inventory.refresh_history(row, (root / path).read_bytes())
    assert row['first_local_record']['commit'] == run('rev-parse', 'HEAD')
    assert row['first_local_record']['subject'] == 'feat: add new method'
    assert row['last_local_change'] == row['first_local_record']
    assert row['content_changed_since_first_local_record'] is False
    assert row['workingtree_modified'] is False


def test_check_returns_missing_material_instead_of_crashing(tmp_path, monkeypatch):
    monkeypatch.setattr(skill_inventory, 'ROOT', tmp_path)
    monkeypatch.setattr(skill_inventory, 'material_paths', lambda: set())
    inventory = {'files': [{'id': 'workbench:missing', 'local_path': 'skills/missing.md',
                            'local_sha256': 'missing'}], 'dependencies': []}
    errors = skill_inventory.check(inventory, strict=True)
    assert 'stale or missing file: skills/missing.md' in errors
