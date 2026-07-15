import json
import socket
from contextlib import nullcontext
from pathlib import Path

from seo_workbench import state
from seo_workbench_tools import page_probe, performance_probe, robots_sitemap_probe
from seo_workbench_tools.network_boundary import resolve_target
from seo_workbench_tools.evidence_bundle import collect, performance_confidence, write_bundle
from seo_workbench_tools.headless import build_headless_audit
from seo_workbench_tools import technology_probe


def test_page_parser_exposes_expanded_seo_evidence() -> None:
    html = """<!doctype html>
    <title>Raw Title</title>
    <meta name="description" content="Raw description">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <meta property="og:title" content="OG Title">
    <meta name="twitter:card" content="summary">
    <link rel="canonical" href="https://example.com/page">
    <meta name="robots" content="index, follow">
    <h1>Main</h1><h3>Subsection</h3>
    <a href="/internal">Internal</a><a href="https://other.example/x">External</a>
    <script type="application/ld+json">{"@context":"https://schema.org","@type":"Article","name":"A"}</script>
    <p>This page has enough raw body text for a crawler to verify that rendering is not required.</p>
    """
    result = page_probe.parse_html(html, "https://example.com/page")
    assert result["viewport"]
    assert result["open_graph"]["og:title"] == "OG Title"
    assert result["twitter"]["twitter:card"] == "summary"
    assert result["h3"] == ["Subsection"]
    assert result["canonical_audit"]["self_referencing"] is True
    assert result["robots_meta_audit"]["indexable"] is True
    assert result["link_summary"]["internal_count"] == 1
    assert result["link_summary"]["external_count"] == 1


def test_robots_parser_groups_ai_crawler_rules() -> None:
    robots = robots_sitemap_probe.parse_robots(
        "User-agent: GPTBot\nDisallow: /\n\nUser-agent: *\nAllow: /\nSitemap: https://example.com/sitemap.xml\n"
    )
    assert robots["groups"]["gptbot"] == [{"directive": "disallow", "value": "/"}]
    assert robots["ai_crawler_rules"]["gptbot"] == [{"directive": "disallow", "value": "/"}]
    assert robots["sitemaps"] == ["https://example.com/sitemap.xml"]


def test_evidence_bundle_keeps_partial_failure_json(monkeypatch) -> None:
    def fail_page(url: str, timeout: float):
        raise RuntimeError("network unavailable")

    def fail_site(url: str, timeout: float, sample_limit: int):
        raise RuntimeError("robots unavailable")

    monkeypatch.setattr(page_probe, "probe", fail_page)
    monkeypatch.setattr(robots_sitemap_probe, "probe", fail_site)
    bundle = collect("https://example.com", [], timeout=1, sample_limit=1)
    assert bundle["schema_version"] == "1.0"
    assert bundle["collection_status"] == "failed"
    assert bundle["errors"]
    assert bundle["headless_audit"]["status"] in {"warn", "fail"}


def test_headless_audit_flags_rendered_only_schema() -> None:
    raw_bundle = {
        "pages": [
            {
                "url": "https://example.com",
                "final_url": "https://example.com",
                "status": 200,
                "title": "Raw",
                "meta_description": "Desc",
                "canonical": "https://example.com",
                "robots_meta": "",
                "h1": ["Raw H1"],
                "schema_audit": {"schema_types_found": [], "inline_schema_count": 0},
                "content_audit": {"has_body_text_in_raw_html": True},
                "link_summary": {"anchor_count": 1},
                "image_stats": {"total": 0},
            }
        ]
    }
    rendered = {
        "pages": [
            {
                "url": "https://example.com",
                "viewports": {
                    "desktop_1920x1080": {
                        "url": "https://example.com",
                        "title": "Raw",
                        "meta_description": "Desc",
                        "canonical": "https://example.com",
                        "robots_meta": "",
                        "h1": ["Raw H1"],
                        "schema_types": ["Product"],
                        "schema_count": 1,
                        "has_body_text": True,
                        "link_summary": {"anchor_count": 1},
                        "images": {"total": 0},
                    }
                },
            }
        ]
    }
    audit = build_headless_audit(raw_bundle, rendered, "shopify-headless")
    assert audit["status"] == "fail"
    assert any("schema appears only after rendering" in item for item in audit["critical"])


def test_technology_output_contract_and_latest_pointer(tmp_path) -> None:
    report = technology_probe.parse_detector_output(
        """{
          "schema_version":"1.0",
          "detector_version":"0.1.0",
          "provider":"projectdiscovery/wappalyzergo",
          "provider_version":"v0.2.89",
          "generated_at":"2026-07-15T00:00:00Z",
          "collection_status":"ok",
          "pages":[{"url":"https://example.com","technologies":[]}],
          "errors":[],
          "warnings":[]
        }"""
    )
    path = technology_probe.write_report(report, tmp_path)
    assert path.exists()
    assert (tmp_path / "latest.json").exists()
    assert report["manifest"]["collection_status"] == "ok"


def test_collector_latest_pointers_replace_symlinks_without_touching_target(tmp_path) -> None:
    outside = tmp_path / "outside.json"
    outside.write_text("do not overwrite", encoding="utf-8")

    raw_dir = tmp_path / "raw"
    raw_dir.mkdir()
    (raw_dir / "latest.json").symlink_to(outside)
    write_bundle({"seed_url": "https://example.com", "pages": [], "site": {}}, raw_dir)
    assert outside.read_text(encoding="utf-8") == "do not overwrite"
    assert not (raw_dir / "latest.json").is_symlink()

    technology_dir = tmp_path / "technology"
    technology_dir.mkdir()
    (technology_dir / "latest.json").symlink_to(outside)
    technology_probe.write_report(
        {
            "schema_version": "1.0",
            "detector_version": "0.1.0",
            "provider": "projectdiscovery/wappalyzergo",
            "provider_version": "v0.2.89",
            "collection_status": "ok",
            "pages": [{"url": "https://example.com", "technologies": []}],
            "errors": [],
            "warnings": [],
        },
        technology_dir,
    )
    assert outside.read_text(encoding="utf-8") == "do not overwrite"
    assert not (technology_dir / "latest.json").is_symlink()


def test_technology_urls_from_state_deduplicates() -> None:
    data = {
        "project": {"url": "https://example.com"},
        "contentQueue": [
            {"status": "published", "url": "https://example.com"},
            {"status": "draft", "publishedUrl": "https://example.com/article"},
            {"status": "planned", "url": "https://example.com/future"},
        ],
    }
    assert technology_probe.urls_from_state(data) == ["https://example.com", "https://example.com/article"]


def test_project_initialization_creates_technology_audit_dir(tmp_path) -> None:
    project_dir = tmp_path / "project"
    state.init_state("general", "Example", "https://example.com", project_dir)
    assert (project_dir / "audits/technology").is_dir()
    assert (project_dir / "audits/performance").is_dir()


def test_technology_probe_rejects_non_positive_timeout() -> None:
    try:
        technology_probe.collect(["https://example.com"], timeout=0)
    except ValueError as exc:
        assert str(exc) == "timeout must be greater than zero"
    else:
        raise AssertionError("expected timeout validation to fail")


def test_technology_probe_limits_representative_urls(monkeypatch) -> None:
    captured = {}

    def fake_run(command, *args, **kwargs):
        captured["command"] = command
        return type(
            "Completed",
            (),
            {
                "returncode": 0,
                "stderr": "",
                "stdout": """{
                  "schema_version":"1.0", "detector_version":"0.1.0",
                  "provider":"projectdiscovery/wappalyzergo", "provider_version":"v0.2.89",
                  "generated_at":"2026-07-15T00:00:00Z", "collection_status":"ok",
                  "pages":[], "errors":[], "warnings":[]
                }""",
            },
        )()

    monkeypatch.setattr(technology_probe, "detector_command", lambda: (["detector"], None))
    monkeypatch.setattr(technology_probe.subprocess, "run", fake_run)
    report = technology_probe.collect([f"https://example.com/{index}" for index in range(12)])
    assert captured["command"].count("-url") == technology_probe.MAX_TECHNOLOGY_URLS
    assert "omitted 2" in report["warnings"][0]["message"]


def test_performance_output_contract_and_latest_pointer(tmp_path, monkeypatch) -> None:
    summary = {
        "schema_version": "1.0",
        "runner_version": "0.1.0",
        "lighthouse_version": "13.4.0",
        "generated_at": "2026-07-15T00:00:00Z",
        "collection_status": "ok",
        "url": "https://example.com/",
        "form_factor": "mobile",
        "runs_requested": 5,
        "runs_succeeded": 5,
        "aggregate": {"performance_score": {"median": 90}, "high_variance": False},
        "environment": {"node_version": "v24.18.0"},
        "errors": [],
        "warnings": [],
        "artifacts": {},
    }

    def fake_run(command, *args, **kwargs):
        return type("Completed", (), {"returncode": 0, "stdout": json.dumps(summary), "stderr": ""})()

    monkeypatch.setattr(performance_probe, "preflight_target", lambda *args: {"status_code": 200})
    monkeypatch.setattr(performance_probe, "node_command", lambda: "/node")
    monkeypatch.setattr(performance_probe, "browser_executable", lambda: "/chrome")
    monkeypatch.setattr(performance_probe, "guarded_proxy", lambda *args: nullcontext("http://127.0.0.1:1234"))
    monkeypatch.setattr(performance_probe, "run_runner", fake_run)
    report = performance_probe.collect("https://example.com", tmp_path, runs=5)
    assert report["collection_status"] == "ok"
    assert Path(report["manifest"]["path"]).exists()
    assert (tmp_path / "latest.json").exists()


def test_performance_runner_contract_rejects_invalid_output() -> None:
    try:
        performance_probe.parse_runner_output('{"collection_status":"ok"}')
    except RuntimeError as exc:
        assert "missing keys" in str(exc)
    else:
        raise AssertionError("expected invalid runner output to fail")


def test_performance_probe_rejects_sensitive_urls() -> None:
    for url in (
        "https://user:password@example.com/",
        "https://example.com/?access_token=secret",
        "file:///tmp/page.html",
    ):
        try:
            performance_probe.validate_url(url)
        except ValueError:
            pass
        else:
            raise AssertionError(f"expected sensitive URL to fail: {url}")
    assert performance_probe.slugify("https://example.com/page?utm_term=private-value") == "example-com-page"


def test_performance_probe_rejects_two_run_false_reliability(tmp_path) -> None:
    try:
        performance_probe.collect("https://example.com", tmp_path, runs=2)
    except ValueError as exc:
        assert "smoke test" in str(exc)
    else:
        raise AssertionError("expected a two-run analysis to fail")


def test_performance_proxy_blocks_loopback_resolution(monkeypatch) -> None:
    monkeypatch.setattr(
        socket,
        "getaddrinfo",
        lambda *args, **kwargs: [(socket.AF_INET, socket.SOCK_STREAM, 6, "", ("127.0.0.1", 80))],
    )
    try:
        resolve_target("example.test", 80, allow_private=False)
    except RuntimeError as exc:
        assert "non-public" in str(exc)
    else:
        raise AssertionError("expected loopback target to be blocked")


def test_single_run_performance_is_smoke_confidence_only() -> None:
    assert performance_confidence({"collection_status": "ok", "runs_succeeded": 1, "aggregate": {}}) == 0.6
    assert performance_confidence({"collection_status": "ok", "runs_succeeded": 5, "aggregate": {}}) == 0.9
