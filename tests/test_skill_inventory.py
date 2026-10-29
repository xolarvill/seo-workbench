"""Exercise inventory boundaries and actual references, without accessing providers."""

from pathlib import Path

import pytest

from scripts import skill_inventory


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
    )
    errors = skill_inventory.unavailable_runtime_paths([{'local_path': 'skills/example/SKILL.md'}])
    assert len(errors) == 1
    assert 'scripts/missing.py' in errors[0]
