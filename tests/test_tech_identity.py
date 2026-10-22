import asyncio
import json
from dataclasses import asdict
from pathlib import Path

import pytest

from seo_workbench import state, tech_audit as audit
from seo_workbench.cli import main
from seo_workbench.tech_confirmation import confirm_candidates
from seo_workbench.tech_identity import IDENTITY_FIELDS, IDENTITY_VERSION
from seo_workbench.tech_issues import (
    REGISTER_PATH, load_issue_register, preview_identity_migration,
    sync_issue_register, update_issue_status,
)


def project(tmp_path):
    root = tmp_path / 'project'
    state.init_state('general', 'Example', 'https://example.com/', project_dir=root)
    return root


def issue(rule='SLOW_RESPONSE', evidence=None, url='https://example.com/a'):
    return audit._issue(rule, {'url': url}, evidence or {'response_time_ms': 1500, 'threshold_ms': 1000})


def test_every_rule_has_an_explicit_identity_policy():
    assert set(IDENTITY_FIELDS) == set(audit.RULES)


def test_timing_and_size_variations_are_observations_not_new_issues():
    first = issue()
    second = issue(evidence={'response_time_ms': 2400, 'threshold_ms': 1000})
    assert first['fingerprint'] == second['fingerprint']
    assert first['observation_hash'] != second['observation_hash']


@pytest.mark.parametrize('rule,key', [('HREFLANG_TO_NON_200', 'href'), ('HREFLANG_MISSING_RETURN_LINK', 'target_url'), ('CANONICAL_TO_NON_200', 'declared_canonical'), ('HTTP_HTTPS_MIX', 'target_url')])
def test_distinct_targets_never_merge(rule, key):
    first = issue(rule, {key: 'https://example.com/one'})
    second = issue(rule, {key: 'https://example.com/two'})
    assert first['fingerprint'] != second['fingerprint']


def test_group_order_and_new_members_do_not_reset_identity():
    first = issue('DUPLICATE_CONTENT_HASH', {'content_hash': 'dynamic1', 'urls': ['a', 'b']})
    second = issue('DUPLICATE_CONTENT_HASH', {'content_hash': 'dynamic2', 'urls': ['c', 'b', 'a']})
    assert first['fingerprint'] == second['fingerprint']
    assert first['observation_hash'] != second['observation_hash']


def test_source_url_still_distinguishes_broken_targets():
    assert issue('BROKEN_INTERNAL_LINK', {'source_urls': ['x']})['fingerprint'] != issue('BROKEN_INTERNAL_LINK', {'source_urls': ['x']}, 'https://example.com/b')['fingerprint']
    assert issue('BROKEN_INTERNAL_LINK', {'source_urls': ['x']})['fingerprint'] == issue('BROKEN_INTERNAL_LINK', {'source_urls': ['y']})['fingerprint']


def test_same_identity_keeps_owner_decision_and_history(tmp_path):
    root = project(tmp_path)
    first = issue()
    sync_issue_register(root, [first], [], run_id='one', verification_allowed=False)
    update_issue_status(root, first['fingerprint'], 'accepted', owner='theme', note='Crawler timing is diagnostic')
    second = issue(evidence={'response_time_ms': 1800})
    sync_issue_register(root, [second], [first], run_id='two', verification_allowed=True)
    sync_issue_register(root, [], [second], run_id='three', verification_allowed=True)
    records = load_issue_register(root)
    assert len(records) == 1
    assert records[0]['status'] == 'accepted'
    assert records[0]['owner'] == 'theme'
    assert any(h.get('note') == 'Crawler timing is diagnostic' for h in records[0]['history'])
    assert any(h.get('run_id') == 'two' and h['event'] == 'observed' for h in records[0]['history'])


def test_candidate_cannot_reopen_fixed_or_verified_but_confirmed_can(tmp_path):
    root = project(tmp_path)
    candidate = issue('MISSING_H1', {'h1': []})
    sync_issue_register(root, [candidate], [], run_id='one', verification_allowed=False)
    fp = candidate['fingerprint']
    update_issue_status(root, fp, 'fixed', note='Patched')
    sync_issue_register(root, [candidate], [candidate], run_id='two', verification_allowed=True)
    assert load_issue_register(root)[0]['status'] == 'fixed'
    confirmed = {**candidate, 'confirmation_status': 'confirmed'}
    sync_issue_register(root, [confirmed], [candidate], run_id='three', verification_allowed=True)
    assert load_issue_register(root)[0]['status'] == 'open'


def test_preview_is_read_only_and_retains_all_conflicting_decisions(tmp_path):
    root = project(tmp_path)
    path = root / REGISTER_PATH
    path.parent.mkdir(exist_ok=True)
    records = [dict(issue(), fingerprint='old-one', owner='a', status='accepted', history=[{'note': 'Keep'}]), dict(issue(), fingerprint='old-two', owner='b', status='fixed', history=[{'note': 'Patched'}]), dict(issue('HREFLANG_TO_NON_200', {'href': 'https://example.com/b'}), fingerprint='old-three')]
    # Old ledgers lost target evidence: never guess it from rule + source.
    records[2].pop('evidence'); records[2].pop('identity')
    path.write_text(''.join(json.dumps(r)+'\n' for r in records))
    before = path.read_bytes()
    preview = preview_identity_migration(root)
    assert path.read_bytes() == before
    assert preview['merge_groups'] == 1
    assert preview['decision_conflicts'] == 1
    assert preview['unresolved_count'] == 1
    assert preview['applied'] is False
    assert sorted(r['owner'] for r in preview['groups'][0]['members']) == ['a', 'b']


def test_preview_can_recover_target_from_exact_immutable_fingerprint(tmp_path):
    root = project(tmp_path)
    item = dict(issue('HREFLANG_TO_NON_200', {'href': 'https://example.com/b'}), fingerprint='legacy')
    artifact = root / 'audits/tech-audit/runs/old/normalized/issues.jsonl'
    artifact.parent.mkdir(parents=True, exist_ok=True)
    artifact.write_text(json.dumps(item)+'\n')
    ledger = root / REGISTER_PATH
    ledger.parent.mkdir(exist_ok=True)
    ledger.write_text(json.dumps({'fingerprint': 'legacy', 'rule_id': item['rule_id'], 'url': item['url'], 'status': 'accepted', 'history': [{'note': 'Keep'}]})+'\n')
    result = preview_identity_migration(root)
    assert result['unresolved_count'] == 0
    assert result['groups'][0]['identity']['href'] == 'https://example.com/b'
    assert result['groups'][0]['members'][0]['history'] == [{'note': 'Keep'}]


def setup_confirmation(tmp_path, monkeypatch, *, fresh_present=True, rule='MISSING_H1', unavailable=False, concurrent=False):
    root = project(tmp_path)
    item = issue(rule, {'h1': []}) if rule == 'MISSING_H1' else issue(rule, {'inlink_count': 0})
    config = audit.CrawlConfig(load_sitemap=False)
    latest = root / 'audits/tech-audit/latest.json'
    latest.parent.mkdir(parents=True, exist_ok=True)
    snapshot = {'run_id': 'baseline', 'config': asdict(config), 'config_fingerprint_version': audit.CONFIG_FINGERPRINT_VERSION}
    latest.write_text(json.dumps(snapshot))
    sync_issue_register(root, [item], [], run_id='baseline', verification_allowed=False)
    monkeypatch.setattr(audit, 'load_tech_issues', lambda *_: [item])
    fresh = {'url': item['url'], 'status_code': None if unavailable else 200, 'content_type': 'text/html', 'h1': [] if fresh_present else ['Hello'], 'indexability': {'indexable': True}, 'title': 'Page', 'canonical': item['url'], 'meta_description': 'Summary', 'error': 'timeout' if unavailable else ''}
    monkeypatch.setattr(audit, 'load_tech_inventory', lambda *_: [fresh])
    def recrawl(_root, urls, passed_config):
        assert passed_config.retries == 0 and passed_config.max_redirects == 1
        assert passed_config.concurrency == 1
        if concurrent:
            latest.write_text(json.dumps({**snapshot, 'run_id': 'new'}))
        return {'run_id': 'confirmation'}, latest.parent / 'recrawl.json'
    monkeypatch.setattr(audit, 'recrawl_urls', recrawl)
    return root, item


def test_local_candidate_confirmed_by_bounded_recrawl(tmp_path, monkeypatch):
    root, item = setup_confirmation(tmp_path, monkeypatch)
    report = confirm_candidates(root)
    assert report['confirmed'] == 1
    assert load_issue_register(root)[0]['confirmation_status'] == 'confirmed'
    assert report['absence_verification'] is False


@pytest.mark.parametrize('unavailable', [True, False])
def test_unknown_or_not_reproduced_never_means_fixed(tmp_path, monkeypatch, unavailable):
    root, item = setup_confirmation(tmp_path, monkeypatch, fresh_present=False, unavailable=unavailable)
    update_issue_status(root, item['fingerprint'], 'fixed', note='Patch')
    report = confirm_candidates(root)
    assert report['confirmed'] == 0
    assert load_issue_register(root)[0]['status'] == 'fixed'
    assert load_issue_register(root)[0]['verification_status'] == 'pending'


def test_graph_candidate_remains_pending_without_network(tmp_path, monkeypatch):
    root, _ = setup_confirmation(tmp_path, monkeypatch, rule='NO_INTERNAL_INLINKS')
    monkeypatch.setattr(audit, 'recrawl_urls', lambda *_: pytest.fail('graph-only confirmation must not fetch'))
    report = confirm_candidates(root)
    assert report['confirmed'] == 0
    assert report['results'][0]['status'] == 'pending'


def test_confirmation_refuses_concurrent_baseline_change(tmp_path, monkeypatch):
    root, _ = setup_confirmation(tmp_path, monkeypatch, concurrent=True)
    report = confirm_candidates(root)
    assert report['confirmed'] == 0
    assert report['results'][0]['reason'] == 'baseline_changed'
    assert load_issue_register(root)[0]['confirmation_status'] == 'candidate'


def test_confirmation_limit_and_legacy_context_are_guarded(tmp_path):
    root = project(tmp_path)
    with pytest.raises(ValueError): confirm_candidates(root, limit=51)
    path = root / 'audits/tech-audit/latest.json'
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text('{}')
    with pytest.raises(ValueError, match='current-version'): confirm_candidates(root)


def test_preview_cli_is_available_without_a_crawl(tmp_path, capsys):
    root = project(tmp_path)
    assert main(['--project-dir', str(root), 'tech-audit', 'issues', 'migration-preview', '--json']) == 0
    assert json.loads(capsys.readouterr().out)['read_only'] is True


def test_disappearing_unconfirmed_candidate_is_not_a_verified_fix(tmp_path):
    root = project(tmp_path)
    candidate = issue('MISSING_H1', {'h1': []})
    sync_issue_register(root, [candidate], [], run_id='one', verification_allowed=False)
    result, _ = sync_issue_register(root, [], [candidate], run_id='two', verification_allowed=True)
    assert result['verified'] == 0
    assert load_issue_register(root)[0]['status'] == 'open'
    assert load_issue_register(root)[0]['confirmation_reason'] == 'not_reproduced_no_fix_claim'


def test_actual_audit_repeat_confirms_and_ua_change_breaks_context(tmp_path, monkeypatch):
    from dataclasses import replace
    root = project(tmp_path)
    async def fetch(url, *_):
        if url.endswith('robots.txt'):
            return {'status': 200, 'headers': {'content-type': 'text/plain'}, 'body': b'User-agent: *\nAllow: /'}
        return {'status': 200, 'final_url': url, 'headers': {'content-type': 'text/html'}, 'body': b'<title>Example</title><h2>Body</h2>', 'elapsed_ms': 1200}
    monkeypatch.setattr(audit, '_fetch', fetch)
    config = audit.CrawlConfig(load_sitemap=False, request_delay=0)
    audit.run_tech_audit(root, config)
    first = {r['rule_id']: r for r in load_issue_register(root)}
    assert first['MISSING_H1']['confirmation_status'] == 'candidate'
    audit.run_tech_audit(root, config)
    repeated = {r['rule_id']: r for r in load_issue_register(root)}
    assert repeated['MISSING_H1']['confirmation_status'] == 'confirmed'
    assert len(repeated) == len(first)
    assert repeated['MISSING_H1']['fingerprint'] == first['MISSING_H1']['fingerprint']
    audit.run_tech_audit(root, replace(config, user_agent='Other'))
    changed = {r['rule_id']: r for r in load_issue_register(root)}
    assert changed['MISSING_H1']['confirmation_status'] == 'candidate'


def test_empty_invalid_hreflang_is_an_issue_not_an_audit_crash():
    page = {'url': 'https://example.com/', 'status_code': 200, 'content_type': 'text/html', 'indexability': {'indexable': True}, **audit._parse_html('<link rel="alternate" hreflang=" " href="https://example.com/fr/">', 'https://example.com/')}
    issues = audit.evaluate_rules([page], [], [], audit.CrawlConfig(), coverage_complete=False)
    assert any(i['rule_id'] == 'HREFLANG_INVALID_CODE' for i in issues)


def test_preview_rejects_symlink_ancestors(tmp_path):
    root = project(tmp_path)
    outside = tmp_path / 'outside'
    outside.mkdir()
    outside.joinpath('issues.jsonl').write_text(json.dumps(issue('HREFLANG_TO_NON_200', {'href': 'https://external.example/private'}))+'\n')
    folder = root / 'audits/tech-audit/runs/evil'
    folder.mkdir(parents=True)
    folder.joinpath('normalized').symlink_to(outside, target_is_directory=True)
    ledger = root / REGISTER_PATH
    ledger.parent.mkdir(exist_ok=True)
    i = issue('HREFLANG_TO_NON_200', {'href': 'https://external.example/private'})
    i.pop('evidence'); i.pop('identity')
    ledger.write_text(json.dumps(i)+'\n')
    preview = preview_identity_migration(root)
    assert preview['unresolved_count'] == 1
    assert 'external.example' not in json.dumps(preview)


def test_operator_edit_during_confirmation_is_never_reopened(tmp_path, monkeypatch):
    root, item = setup_confirmation(tmp_path, monkeypatch)
    original = audit.recrawl_urls
    def recrawl(*args):
        result = original(*args)
        update_issue_status(root, item['fingerprint'], 'fixed', owner='new-owner', note='Just deployed')
        return result
    monkeypatch.setattr(audit, 'recrawl_urls', recrawl)
    report = confirm_candidates(root)
    assert report['confirmed'] == 0
    assert report['results'][0]['reason'] == 'operator_or_register_changed'
    record = load_issue_register(root)[0]
    assert record['status'] == 'fixed' and record['owner'] == 'new-owner'
    assert any(h.get('note') == 'Just deployed' for h in record['history'])


def test_unsupported_high_priority_candidates_do_not_starve_local_candidates(tmp_path, monkeypatch):
    root, local = setup_confirmation(tmp_path, monkeypatch)
    graph = [dict(issue('NO_INTERNAL_INLINKS', {'inlink_count': 0}, f'https://example.com/p{i}'), priority={'score': 999}) for i in range(51)]
    monkeypatch.setattr(audit, 'load_tech_issues', lambda *_: graph + [local])
    report = confirm_candidates(root, limit=1)
    assert report['confirmed'] == 1
    assert report['requires_coverage_count'] == 51


def test_successive_confirmations_skip_already_confirmed_baseline(tmp_path, monkeypatch):
    root, _ = setup_confirmation(tmp_path, monkeypatch)
    assert confirm_candidates(root)['confirmed'] == 1
    monkeypatch.setattr(audit, 'recrawl_urls', lambda *_: pytest.fail('already confirmed must not fetch'))
    report = confirm_candidates(root)
    assert report['selected'] == 0


def test_http_only_response_cannot_disprove_missing_html_element(tmp_path, monkeypatch):
    root, item = setup_confirmation(tmp_path, monkeypatch)
    monkeypatch.setattr(audit, 'load_tech_inventory', lambda *_: [{'url': item['url'], 'status_code': 404, 'content_type': 'text/html'}])
    report = confirm_candidates(root)
    assert report['results'][0]['status'] == 'pending'
    assert report['results'][0]['reason'] == 'unavailable_evidence'


def test_continued_inventory_does_not_confirm_stale_page(tmp_path, monkeypatch):
    root = project(tmp_path)
    page_url = 'https://example.com/a'
    async def fetch(url, *_):
        if url.endswith('robots.txt'):
            return {'status': 200, 'headers': {'content-type': 'text/plain'}, 'body': b'User-agent: *\nAllow: /'}
        body = b'<title>Example</title>'
        if url == 'https://example.com/':
            body += b'<a href="/a">a</a>'
        return {'status': 200, 'final_url': url, 'headers': {'content-type': 'text/html'}, 'body': body}
    monkeypatch.setattr(audit, '_fetch', fetch)
    config = audit.CrawlConfig(load_sitemap=False, request_delay=0, max_urls=1)
    first, _ = audit.run_tech_audit(root, config)
    old = [i for i in audit.load_tech_issues(root) if i['rule_id'] == 'MISSING_H1'][0]
    assert first['collection_status'] == 'partial'
    second, _ = audit.continue_tech_audit(root)
    current = {i['url']: i for i in audit.load_tech_issues(root) if i['rule_id'] == 'MISSING_H1'}
    assert current[old['url']]['confirmation_status'] == 'candidate'
    assert current[old['url']]['observed_run'] == ''
    assert current[page_url]['confirmation_status'] == 'candidate'
