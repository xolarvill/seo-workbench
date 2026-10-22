from __future__ import annotations

import asyncio
import json
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from http.client import IncompleteRead
from pathlib import Path

import pytest

from seo_workbench import state, tech_audit
from seo_workbench.shopify_crawler import build_crawler_access
from seo_workbench_tools import page_probe
from seo_workbench_tools.crawl_session import CrawlDeferred, CrawlSession, active_session, retry_after_seconds


def test_signature_scoped_per_hop_and_expiry_checked(tmp_path):
    access = build_crawler_access(domain_host="example.com", signature="sig1=:private:", signature_input='sig1=("@authority");expires=4102444800', signature_agent='"https://shopify.com"', expires_at=datetime(2030, 1, 1, tzinfo=timezone.utc), seed_url="https://example.com/")
    session = CrawlSession("https://example.com/", access=access, control_root=tmp_path)
    assert session.headers_for("https://example.com/a")["Signature"] == "sig1=:private:"
    assert "Signature" not in session.headers_for("https://other.example/a")
    assert "Signature" not in session.headers_for("http://example.com/a")
    object.__setattr__(access, "expires_at", datetime(2000, 1, 1, tzinfo=timezone.utc))
    with pytest.raises(RuntimeError, match="expired"):
        session.headers_for("https://example.com/")


def test_rate_limit_cools_other_sessions_without_sleeping_or_leaking_secrets(tmp_path):
    first = CrawlSession("https://example.com/", control_root=tmp_path)
    first.observe_response("https://example.com/a", 429, {"retry-after": "90"}, signed=True)
    second = CrawlSession("https://example.com/", control_root=tmp_path)
    with pytest.raises(CrawlDeferred) as error:
        second.before_request("https://example.com/b")
    assert error.value.until >= time.time() + 89
    assert "Signature" not in next(tmp_path.glob('*.json')).read_text()


def test_host_spacing_shared_across_workers_and_sessions(tmp_path):
    a = CrawlSession("http://127.0.0.1/", control_root=tmp_path, allow_private=True, delay=0.04)
    b = CrawlSession("http://127.0.0.1/", control_root=tmp_path, allow_private=True, delay=0.04)
    def enter(session):
        session.before_request("http://127.0.0.1/")
        return time.time()
    with ThreadPoolExecutor(2) as workers:
        times = sorted(workers.map(enter, [a, b]))
    assert times[1] - times[0] >= 0.03


def test_session_context_restored_and_propagates_to_thread(tmp_path):
    session = CrawlSession("https://example.com", control_root=tmp_path)
    async def check():
        return await asyncio.to_thread(active_session)
    assert active_session() is None
    with session.activate():
        assert asyncio.run(check()) is session
    assert active_session() is None


def test_retry_after_supports_date_and_invalid_value():
    assert retry_after_seconds({"retry-after": "90"}) == 90
    assert retry_after_seconds({"retry-after": "Thu, 01 Jan 1970 00:00:00 GMT"}) == 0
    assert retry_after_seconds({"retry-after": "invalid"}) is None


def test_page_probe_uses_injected_transport(tmp_path, monkeypatch):
    session = CrawlSession("https://example.com", control_root=tmp_path)
    monkeypatch.setattr(session, "fetch", lambda *_args: {"status": 200, "final_url": "https://example.com/", "headers": {"content-type": "text/html"}, "body": b'<title>Title</title><h1>Heading</h1>', "elapsed_ms": 2, "signed_headers_attached": True})
    with session.activate():
        result = page_probe.probe("https://example.com/")
    assert result["signed_headers_attached"] is True
    assert result["h1"] == ["Heading"]


def test_recovered_transport_failure_does_not_poison_final_observation(monkeypatch):
    attempts = 0
    def request(*_args):
        nonlocal attempts
        attempts += 1
        if attempts == 1:
            raise RuntimeError("transient network failure")
        return {"status": 200, "body": b'ok', "headers": {}}
    monkeypatch.setattr(tech_audit, "_request_once", request)
    result = asyncio.run(tech_audit._fetch("https://example.com/", "https://example.com/", tech_audit.CrawlConfig(request_delay=0, backoff=0)))
    assert result["errors"] == []
    assert result["recovered_errors"] == ["transient network failure"]
    assert result["attempts"] == 2


def test_failed_page_with_empty_frontier_can_be_resumed(tmp_path, monkeypatch):
    project = tmp_path / "project"
    seed = "http://127.0.0.1:8765/"
    state.init_state("general", "Test", seed, project_dir=project)
    failing = True
    async def fetch(url, *_args):
        if url.endswith('robots.txt'):
            return {"status": 200, "headers": {}, "body": b'User-agent: *\nAllow: /'}
        if failing:
            return {"status": None, "headers": {}, "body": b'', "errors": ["offline"]}
        return {"status": 200, "headers": {"content-type": "text/html"}, "body": b'<title>Title</title><h1>Heading</h1>'}
    monkeypatch.setattr(tech_audit, "_fetch", fetch)
    config = tech_audit.CrawlConfig(load_sitemap=False, allow_private=True, request_delay=0, backoff=0)
    first, _ = tech_audit.run_tech_audit(project, config)
    assert first["summary"]["continuation_available"] is True
    assert first["summary"]["retry_pending"] == 1
    assert not json.loads((project / first['artifacts']['inventory_path']).read_text().splitlines()[0])["evidence_quality"]["html_eligible"]
    failing = False
    resumed, _ = tech_audit.continue_tech_audit(project)
    assert resumed["collection_status"] == "ok"
    assert resumed["summary"]["retry_pending"] == 0
    assert resumed["summary"]["successful_pages"] == 1
    assert first["run_id"] != resumed["run_id"]


def test_future_retry_is_not_replayed_early(tmp_path):
    project = tmp_path / "project"
    state.init_state("general", "Test", "http://127.0.0.1/", project_dir=project)
    root = project / 'audits/tech-audit'
    root.mkdir(parents=True, exist_ok=True)
    (root / 'retry.jsonl').write_text(json.dumps({"url": "http://127.0.0.1/", "crawl_source": "retry", "next_eligible_at": time.time() + 60}) + '\n')
    (root / 'latest.json').write_text(json.dumps({"artifacts": {"retry_queue_path": "audits/tech-audit/retry.jsonl"}, "summary": {}}))
    with pytest.raises(ValueError, match="cooling down"):
        tech_audit.continue_tech_audit(project)


def test_failed_urls_survive_a_second_early_stop(tmp_path, monkeypatch):
    project = tmp_path / 'project'
    seed = 'http://127.0.0.1:8765/'
    state.init_state('general', 'Test', seed, project_dir=project)
    phase = 0
    async def fetch(url, *_args):
        if url.endswith('robots.txt'):
            return {'status': 200, 'headers': {}, 'body': b'User-agent: *\nAllow: /'}
        if phase == 0:
            return {'status': None, 'headers': {}, 'body': b'', 'errors': ['offline']}
        if phase == 1:
            return {'status': 429, 'headers': {}, 'body': b'', 'next_eligible_at': 0}
        return {'status': 200, 'headers': {'content-type': 'text/html'}, 'body': b'<title>Page</title><h1>Page</h1>'}
    monkeypatch.setattr(tech_audit, '_fetch', fetch)
    original = tech_audit._crawl
    async def first_crawl(*args, **kwargs):
        return await original(*args, start_urls=[seed, seed + 'b'], **kwargs)
    monkeypatch.setattr(tech_audit, '_crawl', first_crawl)
    config = tech_audit.CrawlConfig(max_urls=2, concurrency=1, load_sitemap=False, allow_private=True, request_delay=0, backoff=0)
    first, _ = tech_audit.run_tech_audit(project, config)
    assert first['summary']['retry_pending'] == 2
    monkeypatch.setattr(tech_audit, '_crawl', original)
    phase = 1
    stopped, _ = tech_audit.continue_tech_audit(project)
    assert stopped['summary']['retry_pending'] == 2
    phase = 2
    complete, _ = tech_audit.continue_tech_audit(project)
    assert complete['summary']['successful_pages'] == 2
    assert complete['summary']['retry_pending'] == 0
    assert complete['collection_status'] == 'ok'


def test_oversized_retry_after_cannot_poison_persisted_deadline(tmp_path):
    import math
    session = CrawlSession('https://example.com/', control_root=tmp_path)
    session.observe_response('https://example.com/', 429, {'retry-after': '9' * 1000})
    until = session.next_eligible_at('https://example.com/')
    assert math.isfinite(until)
    assert datetime.fromtimestamp(until, timezone.utc)
    assert 'Infinity' not in next(tmp_path.glob('*.json')).read_text()


def test_failed_resource_head_is_not_a_missing_cache_header(tmp_path, monkeypatch):
    from seo_workbench_tools.evidence_bundle import resource_cache_audit
    session = CrawlSession('https://example.com/', control_root=tmp_path)
    def fail(*args, **kwargs):
        raise CrawlDeferred(time.time() + 60)
    monkeypatch.setattr(session, 'fetch', fail)
    with session.activate():
        result = resource_cache_audit([{'resources': [{'type': 'script', 'url': 'https://example.com/app.js'}]}], 1)
    assert result['errors']
    assert result['issues'] == []
    assert result['no_cache_control'] == 0


def test_empty_html_is_kept_in_the_retry_queue(tmp_path, monkeypatch):
    seed = 'http://127.0.0.1:8765/'
    project = tmp_path / 'project'
    state.init_state('general', 'Test', seed, project_dir=project)
    async def fetch(url, *_args):
        return {'status': 200, 'headers': {'content-type': 'text/html'}, 'body': b'User-agent: *\nAllow: /' if url.endswith('robots.txt') else b''}
    monkeypatch.setattr(tech_audit, '_fetch', fetch)
    report, _ = tech_audit.run_tech_audit(project, tech_audit.CrawlConfig(load_sitemap=False, allow_private=True, request_delay=0, backoff=0))
    assert report['summary']['retry_pending'] == 1
    assert report['summary']['continuation_available'] is True


def test_actual_tech_request_cannot_sign_http_downgrade(tmp_path, monkeypatch):
    access = build_crawler_access(domain_host='example.com', signature='sig1=:private:', signature_input='sig1=("@authority");expires=4102444800', signature_agent='"https://shopify.com"', expires_at=datetime(2030, 1, 1, tzinfo=timezone.utc), seed_url='https://example.com/')
    seen = []
    class Response:
        status = 200
        headers = {}
        def __enter__(self): return self
        def __exit__(self, *_): return None
        def read(self): return b'<h1>Page</h1>'
        def geturl(self): return 'http://example.com/'
    def open_request(request, **_):
        seen.append(dict(request.header_items()))
        return Response()
    monkeypatch.setattr(tech_audit._OPENER, 'open', open_request)
    session = CrawlSession('https://example.com/', access=access, control_root=tmp_path, delay=0)
    monkeypatch.setattr(session, 'before_request', lambda *_: None)
    with session.activate():
        tech_audit._request_once('http://example.com/', tech_audit.CrawlConfig(), access)
    assert not any(key.lower().startswith('signature') for key in seen[0])
    assert access.headers_for('http://example.com/') == {}


def test_long_retry_after_is_deferred_instead_of_blocking_a_worker(monkeypatch):
    monkeypatch.setattr(tech_audit, '_request_once', lambda *_: {'status': 503, 'headers': {'retry-after': '3600'}, 'body': b'unavailable'})
    result = asyncio.run(tech_audit._fetch('https://example.com/', 'https://example.com/', tech_audit.CrawlConfig(request_delay=0, backoff=0)))
    assert result['status'] == 503
    assert result['next_eligible_at'] >= time.time() + 3599


def test_browser_signatures_are_scoped_to_each_cdp_redirect_hop(tmp_path, monkeypatch):
    from types import SimpleNamespace
    from seo_workbench_tools.rendered_probe import install_crawl_routes
    access = build_crawler_access(domain_host='example.com', signature='sig1=:private:', signature_input='sig1=("@authority");expires=4102444800', signature_agent='"https://shopify.com"', expires_at=datetime(2030, 1, 1, tzinfo=timezone.utc), seed_url='https://example.com/')
    session = CrawlSession('https://example.com/', access=access, control_root=tmp_path, delay=0)
    monkeypatch.setattr(session, 'before_request', lambda *_: None)
    seen = []
    cdp = SimpleNamespace(on=lambda name, fn: setattr(cdp, 'handler', fn), send=lambda name, value: seen.append((name, value)))
    page = SimpleNamespace(context=SimpleNamespace(new_cdp_session=lambda _: cdp), on=lambda *_: None)
    failures = install_crawl_routes(page, session, 1)
    for url in ['https://example.com/', 'https://other.example/']:
        cdp.handler({'requestId': url, 'resourceType': 'Document', 'request': {'url': url, 'headers': {'user-agent': 'Mobile UA', 'signature': 'old-secret'}}})
    assert not failures
    requests = [dict((h['name'], h['value']) for h in value['headers']) for name, value in seen if name == 'Fetch.continueRequest']
    assert requests[0]['signature'] == 'sig1=:private:'
    assert not any(k.startswith('signature') for k in requests[1])
    assert requests[0]['user-agent'] == 'Mobile UA'


def test_browser_callback_handles_cooldown_without_raising_to_event_loop(tmp_path, monkeypatch):
    from types import SimpleNamespace
    from seo_workbench_tools.rendered_probe import install_crawl_routes
    session = CrawlSession('https://example.com/', control_root=tmp_path)
    def deferred(*_): raise CrawlDeferred(time.time() + 30)
    monkeypatch.setattr(session, 'before_request', deferred)
    seen = []
    cdp = SimpleNamespace(on=lambda name, fn: setattr(cdp, 'handler', fn), send=lambda name, value: seen.append(name))
    page = SimpleNamespace(context=SimpleNamespace(new_cdp_session=lambda _: cdp), on=lambda *_: None)
    failures = install_crawl_routes(page, session, 1)
    cdp.handler({'requestId': 'first', 'resourceType': 'Document', 'request': {'url': 'https://example.com/', 'headers': {}}})
    assert failures[0]['kind'] == 'cooldown'
    assert 'Fetch.failRequest' in seen


def test_expired_access_stops_after_first_attempt(monkeypatch):
    from seo_workbench_tools.crawl_session import CrawlAccessError
    calls = []
    def fail(*_):
        calls.append(True)
        raise CrawlAccessError('crawler signature expired')
    monkeypatch.setattr(tech_audit, '_request_once', fail)
    result = asyncio.run(tech_audit._fetch('https://example.com/', 'https://example.com/', tech_audit.CrawlConfig(request_delay=0)))
    assert len(calls) == 1
    assert result['access_required'] is True


def test_fast_browser_response_keeps_signed_receipt(tmp_path, monkeypatch):
    from types import SimpleNamespace
    from seo_workbench_tools.rendered_probe import install_crawl_routes
    session = CrawlSession('https://example.com/', control_root=tmp_path, delay=0)
    monkeypatch.setattr(session, 'before_request', lambda *_: None)
    monkeypatch.setattr(session, 'headers_for', lambda *_args, **_kwargs: {'signature': 'private'})
    receipts = []
    monkeypatch.setattr(session, 'observe_response', lambda *args, **kwargs: receipts.append(kwargs['signed']))
    callbacks = {}
    def send(name, value):
        if name == 'Fetch.continueRequest':
            callbacks['response'](SimpleNamespace(url='https://example.com/', status=200, headers={}, request=SimpleNamespace(is_navigation_request=lambda: True)))
    cdp = SimpleNamespace(on=lambda name, fn: callbacks.update(paused=fn), send=send)
    page = SimpleNamespace(context=SimpleNamespace(new_cdp_session=lambda _: cdp), on=lambda name, fn: callbacks.update({name: fn}))
    assert install_crawl_routes(page, session, 1) == []
    callbacks['paused']({'requestId': 'fast', 'resourceType': 'Document', 'request': {'url': 'https://example.com/', 'headers': {}}})
    assert receipts == [True]


def test_partial_browser_view_cannot_prove_raw_rendered_mismatch():
    from seo_workbench_tools.headless import _first_rendered_view
    partial = {'title': '', 'comparison_eligible': False}
    assert _first_rendered_view({'viewports': {'desktop_1920x1080': partial, 'other': partial}}) == {}
    complete = {'title': 'Observed', 'comparison_eligible': True}
    assert _first_rendered_view({'viewports': {'desktop_1920x1080': partial, 'mobile_375x812': complete}}) == complete
