"""Bounded pilot acceptance against real local HTTP, never a production store."""
import hashlib
import json
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

import pytest

from seo_workbench import state, tech_audit as audit
from seo_workbench_tools.crawl_session import CrawlSession


@pytest.fixture
def pilot_server(tmp_path, monkeypatch):
    calls = []
    phase = {'limited': True, 'flaky_calls': 0}
    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *_): pass
        def do_GET(self):
            calls.append(self.path)
            if self.path == '/flaky':
                phase['flaky_calls'] += 1
                if phase['flaky_calls'] == 1:
                    self.close_connection = True
                    return
            if self.path == '/sitemap.xml':
                base = f'http://127.0.0.1:{self.server.server_port}'
                body = ('<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">' + ''.join(f'<url><loc>{base}{p}</loc></url>' for p in ['/flaky', '/throttle', '/untouched']) + '</urlset>').encode()
                self.send_response(200)
                self.send_header('Content-Type', 'application/xml')
                self.end_headers()
                self.wfile.write(body)
                return
            status = 429 if self.path == '/throttle' and phase['limited'] else 404 if self.path == '/old' else 200
            body = b'User-agent: *\nAllow: /' if self.path == '/robots.txt' else b'<title>Page title</title><svg><title>Icon title</title></svg><h1>Hello <span>nested</span> heading</h1>'
            if self.path == '/flaky': body += b'<a href="/throttle">target</a><a href="/untouched">other</a>'
            if self.path == '/a': body += b'<a href="/outside-sample">extra</a>'
            if status == 404: body += b'<a href="#main">Skip to content</a><a href="/from-error-only">template link</a>'
            if status == 429: body = b'local_rate_limited'
            self.send_response(status)
            self.send_header('Content-Type', 'text/plain' if self.path == '/robots.txt' else 'text/html')
            if status == 429: self.send_header('Retry-After', '3600')
            self.send_header('Content-Length', str(len(body)))
            self.end_headers()
            self.wfile.write(body)
    server = ThreadingHTTPServer(('127.0.0.1', 0), Handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    url = f'http://127.0.0.1:{server.server_port}'
    control = tmp_path / 'crawl-control'
    monkeypatch.setattr(audit, 'CrawlSession', lambda *args, **kwargs: CrawlSession(*args, control_root=control, **kwargs))
    try:
        yield url, calls, phase, control
    finally:
        server.shutdown(); thread.join(timeout=2); server.server_close()


def test_bounded_recrawl_preserves_full_audit_and_operator_ledger(tmp_path, pilot_server):
    url, calls, _, _ = pilot_server
    root = tmp_path / 'project'
    state.init_state('general', 'Pilot', url, project_dir=root)
    inventory = root / 'audits/tech-audit/seed.jsonl'
    inventory.write_text(''.join(json.dumps({'url': url+path, 'host_relation': 'same_host'})+'\n' for path in ['/a','/old']))
    latest = root / 'audits/tech-audit/latest.json'
    latest.write_text(json.dumps({'run_id': 'baseline', 'artifacts': {'inventory_path': str(inventory.relative_to(root))}}))
    ledger = root / 'strategy/technical-issues.jsonl'
    ledger.write_text(json.dumps({'fingerprint': 'old', 'status': 'accepted', 'owner': 'operator', 'history': [{'note': 'Deliberate'}]})+'\n')
    before = [hashlib.sha256(p.read_bytes()).hexdigest() for p in [latest, ledger]]
    report, path = audit.recrawl_urls(root, [url+'/a', url+'/old'], audit.CrawlConfig(concurrency=1, request_delay=0, retries=0, load_sitemap=False, allow_private=True))
    assert calls == ['/robots.txt', '/a', '/old']
    assert [hashlib.sha256(p.read_bytes()).hexdigest() for p in [latest, ledger]] == before
    pages = audit.load_tech_inventory(root, path)
    assert pages[0]['title'] == 'Page title'
    assert pages[0]['h1'] == ['Hello nested heading']
    assert report['summary']['still_404'] == 1
    issues = audit.evaluate_rules(pages, [], [], audit.CrawlConfig(), coverage_complete=False)
    assert any(i['rule_id'] == 'HTTP_4XX' for i in issues)
    assert not any(i['rule_id'] in {'MISSING_H1', 'NO_INTERNAL_INLINKS', 'ORPHAN_CANDIDATE', 'HREFLANG_MISSING_RETURN_LINK'} for i in issues)


def test_real_transport_recovers_then_rate_limit_survives_restart(tmp_path, pilot_server, monkeypatch):
    url, calls, phase, control = pilot_server
    root = tmp_path / 'project'
    state.init_state('general', 'Pilot', url+'/flaky', project_dir=root)
    config = audit.CrawlConfig(max_urls=3, concurrency=1, request_delay=0, retries=1, backoff=0, load_sitemap=True, allow_private=True)
    first, first_path = audit.run_tech_audit(root, config)
    before_snapshot = first_path.read_bytes()
    pages = audit.load_tech_inventory(root, first_path)
    flaky = next(p for p in pages if p['url'] == url+'/flaky')
    assert phase['flaky_calls'] == 2
    assert flaky['error'] == ''
    assert first['collection_status'] == 'partial'
    assert first['summary']['retry_pending'] == 1
    assert '/untouched' not in calls
    queue, _ = audit.load_remaining_crawl_queue(root, first_path)
    assert any(p['url'] == url+'/throttle' and p['next_eligible_at'] for p in queue)
    assert not any(i['rule_id'] in {'HTTP_4XX', 'HTTP_5XX', 'HREFLANG_TO_NON_200'} and i['url'] == url+'/throttle' for i in audit.load_tech_issues(root, first_path))
    # Advance the fixture clock beyond both the persisted host cooldown and
    # retry-queue deadline; never force a second request while still cooling.
    phase['limited'] = False
    future = time.time() + 4000
    monkeypatch.setattr(time, 'time', lambda: future)
    later, _ = audit.continue_tech_audit(root)
    assert later['collection_status'] == 'ok'
    assert later['summary']['retry_pending'] == 0
    assert later['summary']['successful_pages'] == 3
    assert first_path.read_bytes() == before_snapshot
    assert any(p['url'] == url+'/throttle' and p['status_code'] == 429 for p in audit.load_tech_inventory(root, first_path))
    assert all(p['status_code'] == 200 for p in audit.load_tech_inventory(root))


def test_error_template_self_link_is_not_evidence_of_a_live_broken_link():
    url = 'https://example.com/old'
    bad = {'url': url, 'status_code': 404, 'content_type': 'text/html', 'inlink_count': 1, 'inlinks': [{'source_url': url, 'anchor_text': 'Skip to content'}]}
    rules = {i['rule_id'] for i in audit.evaluate_rules([bad], [], [], audit.CrawlConfig(), coverage_complete=False)}
    assert 'HTTP_4XX' in rules
    assert 'BROKEN_INTERNAL_LINK' not in rules


@pytest.mark.parametrize('source_status', [200, 404, 429, None])
def test_broken_link_requires_observed_eligible_source(source_status):
    source = {'url': 'https://example.com/source', 'status_code': source_status, 'content_type': 'text/html', 'indexability': {'indexable': True}}
    target = {'url': 'https://example.com/old', 'status_code': 404, 'content_type': 'text/html', 'inlink_count': 1, 'inlinks': [{'source_url': source['url']}]}
    issues = audit.evaluate_rules([source, target], [], [], audit.CrawlConfig(), coverage_complete=False)
    assert any(i['rule_id'] == 'BROKEN_INTERNAL_LINK' for i in issues) == (source_status == 200)


def test_redirect_alias_self_link_does_not_count_as_incoming_graph_edge():
    source = {'url': 'https://example.com/alias', 'final_url': 'https://example.com/page', 'status_code': 200, 'content_type': 'text/html'}
    target = {'url': 'https://example.com/page', 'inlinks': [{'source_url': source['url']}]}
    assert audit._effective_inlinks(target, {source['url']: source}) == []


def test_error_template_never_expands_the_discovery_frontier(tmp_path, pilot_server):
    url, calls, _, _ = pilot_server
    root = tmp_path / 'project'
    state.init_state('general', 'Pilot', url+'/old', project_dir=root)
    report, _ = audit.run_tech_audit(root, audit.CrawlConfig(max_urls=10, concurrency=1, request_delay=0, retries=0, load_sitemap=False, allow_private=True))
    assert calls == ['/robots.txt', '/old']
    page = audit.load_tech_inventory(root)[0]
    assert page['outlinks']
    assert page['inlinks'] == []
    assert report['summary']['pages'] == 1
    assert not any(i['rule_id'] == 'BROKEN_INTERNAL_LINK' for i in audit.load_tech_issues(root))
