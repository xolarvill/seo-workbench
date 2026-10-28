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
    for invalid in ({"count": 51}, {"url": "https://elsewhere.com"}, {"start": "2026-10-25"}):
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
