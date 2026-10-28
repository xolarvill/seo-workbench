import json

import pytest
from filelock import FileLock

from seo_workbench import clarity, state
from seo_workbench_tools.clarity_probe import collect, prepare, sanitize


@pytest.fixture
def project(tmp_path):
    p = tmp_path / "store"
    state.init_state("shopify", "Store", "https://example.com", project_dir=p)
    clarity.configure(p, "secret-token-123456", "abc123", "UTC", verify=False)
    return p


def result(payload):
    return {"ok": True, "result": {"content": [{"type": "text", "text": json.dumps(payload)}]}}


def test_dashboard_scope_and_unknown_identity_remain_partial(project):
    seen = []
    def caller(tool, arguments, **kwargs):
        seen.append((tool, arguments, kwargs))
        return result({"sessions": 7, "sessionId": "hidden", "token": "hidden"})
    report = collect(project, "query", query="Total sessions", start="2026-10-25", end="2026-10-26", caller=caller)
    assert report["collection_status"] == "partial"
    assert report["observed_scope"] is None
    assert report["response"] == {"sessions": 7}
    assert "hidden" not in json.dumps(report)
    assert seen[0][2]["timezone"] == "UTC"
    cached = collect(project, "query", query="Total sessions", start="2026-10-25", end="2026-10-26", caller=caller)
    assert cached["cache_hit"] and len(seen) == 1
    assert (project / report["manifest"]["path"]).stat().st_mode & 0o777 == 0o600


def test_failures_do_not_erase_success_or_synthesize_zero(project):
    success = collect(project, "docs", query="How does consent work?", caller=lambda *a, **k: result({"answer": "Documentation reference"}))
    failed = collect(project, "docs", query="How does consent work?", force=True, caller=lambda *a, **k: {"ok": False, "reason_code": "timeout"})
    assert failed["collection_status"] == "failed" and "response" not in failed
    assert (project / success["manifest"]["path"]).exists()
    saved = json.loads((project / "audits/clarity/documentation/last_successful.json").read_text())
    assert saved["manifest"] == success["manifest"]


def test_rate_limit_cooldown_prevents_repeated_calls(project):
    def limited(*a, **k):
        return {"ok": True, "http_status": 429}
    assert collect(project, "docs", query="Consent", caller=limited)["reason_code"] == "rate_limited"
    def forbidden(*a, **k):
        pytest.fail("should respect cooldown")
    assert collect(project, "docs", query="Consent", force=True, caller=forbidden)["reason_code"] == "rate_limited"


def test_recordings_are_bounded_and_site_filtered(project):
    binding = clarity.load(project)
    args, tz = prepare(binding, "recordings", start="2026-10-25T00:00:00Z", end="2026-10-26T00:00:00Z", device="Mobile", rage_click=True)
    assert args["count"] == 10 and args["filters"]["rageClickPresent"]
    assert args["filters"]["visitedUrls"][0]["url"] == "https://example.com"
    assert tz == "UTC"
    for invalid in ({"count": 51}, {"url": "https://elsewhere.com"}, {"url": "https://example.com/checkouts/private-capability"}, {"start": "2026-10-25"}):
        with pytest.raises(ValueError):
            prepare(binding, "recordings", **{"start": "2026-10-25T00:00:00Z", "end": "2026-10-26T00:00:00Z", **invalid})


def test_redaction_drops_ids_recording_links_and_url_secrets():
    safe = sanitize({"sessionId": "private", "recordingUrl": "https://clarity.ms/player/abc", "url": "https://example.com/p?token=private", "duration": 12}, kind="recordings")
    assert safe == {"url": "https://example.com/p", "duration": 12}


def test_busy_does_not_touch_latest(project):
    lock = project / ".runtime/clarity/operation.lock"
    lock.parent.mkdir(parents=True)
    with FileLock(lock):
        report = collect(project, "docs", query="Consent")
    assert report["reason_code"] == "busy"
    assert not (project / "audits/clarity/latest.json").exists()


def test_missing_configuration_is_structured(tmp_path):
    state.init_state("shopify", "Store", "https://example.com", project_dir=tmp_path)
    assert collect(tmp_path, "docs", query="Consent")["reason_code"] == "needs_config"


def test_recording_links_are_transient_and_host_checked(project):
    from seo_workbench_tools.clarity_probe import recording_links
    link = "https://clarity.microsoft.com/player/abc/secret"
    assert recording_links([link, "https://clarity.microsoft.com.evil.test/player/secret"]) == [link]
    temporary = {}
    report = collect(project, "recordings", start="2026-10-25T00:00:00Z", end="2026-10-26T00:00:00Z",
                     caller=lambda *a, **k: result([{"link": link, "duration": 20}]), transient_sink=temporary.update)
    assert temporary["links"] == [link]
    assert link not in json.dumps(report)
    assert "secret" not in (project / report["manifest"]["path"]).read_text()


def test_storage_failure_is_structured(project, monkeypatch):
    def fail(*a, **k):
        raise OSError("disk full")
    monkeypatch.setattr(clarity, "private_write", fail)
    report = collect(project, "docs", query="Consent", caller=lambda *a, **k: result({"answer": "Documentation"}))
    assert report["reason_code"] == "evidence_write_failed"
    assert "manifest" not in report


def test_provider_description_is_preserved_without_claiming_verified_scope(project):
    description = "Counts non-bot unique sessions on https://example.com/?token=secret in UTC; secret-token-123456; person@example.com"
    report = collect(project, "query", query="Sessions", start="2026-10-26", end="2026-10-26",
                     caller=lambda *a, **k: result({"query": description, "data": [{"TotalSessions": 7}]}))
    assert report["transport_status"] == "ok"
    assert report["scope_status"] == "provider_described"
    assert report["identity_status"] == "operator_declared"
    assert report["capability_status"] == "available"
    assert report["collection_status"] == "partial"
    assert "non-bot unique sessions" in report["provider_query_description"]
    assert "token=secret" not in report["provider_query_description"]
    assert "secret-token-123456" not in report["provider_query_description"]
    assert "person@example.com" not in report["provider_query_description"]


@pytest.mark.parametrize("scope,scope_status,reason", [
    ({"startDate": "2026-10-26", "endDate": "2026-10-26", "timezone": "UTC", "site_url": "https://example.com"}, "structured_match", "identity_unverified"),
    ({"startDate": "2026-10-25", "endDate": "2026-10-26", "timezone": "UTC", "site_url": "https://example.com"}, "mismatch", "scope_mismatch"),
    ({"startDate": "2026-10-26", "endDate": "2026-10-26", "timezone": "UTC", "site_url": "https://other.com"}, "mismatch", "scope_mismatch"),
    ({"startDate": "2026-10-26", "endDate": "2026-10-26", "timezone": "America/New_York", "site_url": "https://example.com"}, "mismatch", "scope_mismatch"),
    ({"startDate": "2026-10-26", "endDate": "2026-10-26", "timezone": "UTC"}, "unknown", "scope_incomplete"),
])
def test_structured_scope_is_compared_to_actual_request(project, scope, scope_status, reason):
    report = collect(project, "query", query="Sessions", start="2026-10-26", end="2026-10-26",
                     caller=lambda *a, **k: result({"scope": scope, "data": [{"TotalSessions": 7}]}))
    assert report["scope_status"] == scope_status
    assert report["reason_code"] == reason
    assert not report["identity_verified"]
    assert report["collection_status"] == "partial"


def test_documentation_failure_does_not_contaminate_dashboard(project):
    failed = collect(project, "docs", query="Consent", caller=lambda *a, **k: {"ok": True, "http_status": 500, "result": {"content": [{"type": "text", "text": "An error occurred while fetching the data."}]}})
    assert failed["capability_status"] == "unavailable"
    dashboard = collect(project, "query", query="Sessions", start="2026-10-26", end="2026-10-26",
                        caller=lambda *a, **k: result({"sessions": 7}))
    assert dashboard["transport_status"] == "ok"
    assert dashboard["capability_status"] == "available"
    assert dashboard["errors"] == []
    index = json.loads((project / "audits/clarity/latest.json").read_text())["sources"]
    assert index["dashboard"]["transport_status"] == "ok"
    assert index["documentation"]["capability_status"] == "unavailable"


def test_unrecognized_metrics_are_not_a_usable_empty_result(project):
    report = collect(project, "query", query="Sessions", start="2026-10-26", end="2026-10-26",
                     caller=lambda *a, **k: result({"data": [{"unrecognizedMetric": 7}], "dataErrorType": 0}))
    assert report["transport_status"] == "ok"
    assert report["capability_status"] == "unsupported_response"
    assert report["reason_code"] == "unsupported_response"


def test_new_collector_does_not_reuse_legacy_cache(project):
    old = collect(project, "query", query="Sessions", start="2026-10-26", end="2026-10-26", caller=lambda *a, **k: result({"sessions": 7}))
    target = project / old["manifest"]["latest_path"]
    payload = json.loads(target.read_text())
    payload.pop("collector_version", None)
    target.write_text(json.dumps(payload))
    refreshed = collect(project, "query", query="Sessions", start="2026-10-26", end="2026-10-26", caller=lambda *a, **k: result({"sessions": 8}))
    assert not refreshed["cache_hit"]
    assert refreshed["response"]["sessions"] == 8


def test_homepage_dashboard_preserves_observed_provider_metric_aliases(project):
    row = {"Device": "Mobile", "HomepageURL": "https://example.com/?private=value",
           "StartDateUTC": "2026-10-20T00:00:00Z", "EndDateUTC": "2026-10-26T23:59:59Z",
           "TotalSessions": 7, "TotalPageViews": 12, "AvgScrollDepthPercent": 48.5,
           "TotalDeadClicks": 2, "TotalRageClicks": 0, "TotalQuickbackClicks": 1,
           "TotalExcessiveScrolls": 0, "sessionId": "private-session"}
    report = collect(project, "query", query="Homepage metrics", start="2026-10-20", end="2026-10-26",
                     caller=lambda *a, **k: result({"data": [row]}))
    expected = {k: v for k, v in row.items() if k != "sessionId"}
    expected["HomepageURL"] = "https://example.com/"
    assert report["response"]["data"] == [expected]
    assert report["scope_status"] == "unknown"  # Row labels are not independent scope verification.
    assert "private-session" not in json.dumps(report)


def test_mixed_known_and_unknown_numeric_fields_are_not_silently_projected(project):
    report = collect(project, "query", query="Metrics", start="2026-10-26", end="2026-10-26",
                     caller=lambda *a, **k: result({"data": [{"TotalSessions": 7, "UnrecognizedMetric": 9, "sessionId": 123}]}))
    assert report["response"]["data"] == [{"TotalSessions": 7}]
    assert report["response_projection"]["omitted_numeric_fields"] == 1
    assert any("numeric fields" in warning for warning in report["warnings"])


@pytest.mark.parametrize('explicit', [False, True])
def test_click_source_page_rejects_entry_url_substitution(project, explicit):
    report = collect(project, 'query', query='Count ordinary clicks. Source page must be exactly https://example.com/.',
                     start='2026-10-20', end='2026-10-26',
                     **({'source_page': 'https://example.com/'} if explicit else {}),
                     caller=lambda *a, **k: result({'query': "Counts clicks for users (EntryUrl = 'https://example.com/')", 'data': [{'count': 14}]}))
    assert report['scope_status'] == 'mismatch'
    assert report['reason_code'] == 'click_source_scope_conflict'
    assert report['capability_status'] == 'unsupported_scope'
    assert report['requested_scope']['source_page_url'] == 'https://example.com/'
    assert report['response']['data'][0]['count'] == 14  # Observation retained, attribution rejected.


def test_click_source_claim_does_not_become_verified_by_text(project):
    report = collect(project, 'query', query='Count article clicks', source_page='https://example.com/',
                     start='2026-10-20', end='2026-10-26',
                     caller=lambda *a, **k: result({'query': "Clicks occurred only on https://example.com/", 'data': [{'count': 14}]}))
    assert report['capability_status'] == 'unsupported_scope'
    assert report['reason_code'] == 'click_source_scope_unverified'


def test_click_source_page_must_be_clean_same_site(project):
    with pytest.raises(ValueError):
        prepare(clarity.load(project), 'query', query='Clicks', source_page='https://elsewhere.com/', start='2026-10-20', end='2026-10-26')


def test_provider_query_error_is_not_a_transport_failure(project):
    report = collect(project, 'query', query='Clicks', source_page='https://example.com/',
                     start='2026-10-26', end='2026-10-26',
                     caller=lambda *a, **k: result({'dataErrorType': 42, 'data': [{'sessionId': 'private'}], 'query': 'secret-token-123456'}))
    assert report['transport_status'] == 'ok'
    assert report['collection_status'] == 'failed'
    assert report['reason_code'] == 'provider_query_error'
    assert report['provider_error_code'] == 42
    assert report['requested_scope']['source_page_url'] == 'https://example.com/'
    assert 'response' not in report
    assert 'private' not in json.dumps(report)
    assert 'secret-token' not in json.dumps(report)


def test_dashboard_warns_about_documented_window_limit(project):
    report = collect(project, 'query', query='Sessions', start='2026-10-20', end='2026-10-26',
                     caller=lambda *a, **k: result({'sessions': 7}))
    assert any('3 days' in warning for warning in report['warnings'])
