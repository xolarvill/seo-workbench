"""Portable methods must retain source identity and reach their canonical owner."""

import hashlib
import json
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]


def adaptations():
    return json.loads((ROOT / 'docs/skill-method-adaptations.json').read_text())['materials']


def test_legacy_methods_have_current_owners_or_a_history_only_reason():
    inventory = json.loads((ROOT / 'docs/skill-sources.json').read_text())
    originals = {r['id']: r for r in inventory['files']
                 if r['source_id'] == 'seomachine' and r['kind'] in
                 {'specialist_reference', 'workflow_reference'}}
    rows = adaptations()
    assert {row['source_id'] for row in rows} == set(originals)
    assert len(rows) == len(originals)
    for row in rows:
        original = ROOT / row['historical_path']
        assert hashlib.sha256(original.read_bytes()).hexdigest() == row['preserved_sha256']
        if row['disposition'] == 'historical_only':
            assert row['reason'] and row['adapted_path'] is None
            continue
        reference = ROOT / row['adapted_path']
        owner = ROOT / row['owner_path']
        assert reference.is_file() and owner.is_file()
        assert reference.name in owner.read_text()
        assert row['source_id'] in next(r for r in inventory['files']
                                       if r['local_path'] == row['adapted_path'])['derived_from']


def test_current_adapters_do_not_require_the_old_executor():
    for row in adaptations():
        if not row['adapted_path']:
            continue
        text = (ROOT / row['adapted_path']).read_text()
        assert not re.search(r'\bpython3?\s+|data_sources/|\.claude/|`/(?:write|article|publish-draft|scrub)\b', text)


def test_scrub_stays_historical_instead_of_becoming_a_quality_gate():
    scrub = next(row for row in adaptations() if row['historical_path'].endswith('/scrub.md'))
    assert scrub['disposition'] == 'historical_only'
    assert scrub['adapted_path'] is None
