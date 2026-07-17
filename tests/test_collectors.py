import json
import socket
from contextlib import nullcontext
from pathlib import Path

from seo_workbench import state
from seo_workbench_tools import crux_probe, evidence_bundle, page_probe, performance_probe, rendered_probe, robots_sitemap_probe
from seo_workbench_tools.network_boundary import resolve_target
from seo_workbench_tools.evidence_bundle import collection_status, collect, performance_confidence, write_bundle
from seo_workbench_tools.headless import build_headless_audit
from seo_workbench_tools import technology_probe
from seo_workbench_tools.technology_architecture import analyze_architecture


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


def test_bundle_status_is_partial_when_raw_page_returns_http_error() -> None:
    bundle = {
        "pages": [{"url": "https://example.com", "status": 429}],
        "site": {"url": "https://example.com", "robots": {"status": 200}},
        "errors": [],
    }
    assert collection_status(bundle) == "partial"


def test_bundle_status_fails_when_pages_and_site_fail() -> None:
    bundle = {
        "pages": [{"url": "https://example.com", "error": "timeout"}],
        "site": {"url": "https://example.com", "error": "timeout"},
        "errors": [{"scope": "page", "error": "timeout"}],
    }
    assert collection_status(bundle) == "failed"


def test_small_site_discovery_selects_safe_representative_routes() -> None:
    pages = [
        {
            "url": "https://example.com/",
            "final_url": "https://example.com/",
            "link_summary": {
                "sample_internal": [
                    "https://example.com/product/9",
                    "https://example.com/product/10",
                    "https://example.com/about#team",
                    "https://example.com/assets/app.js",
                    "https://other.example/contact",
                ]
            },
        }
    ]
    rendered = {
        "pages": [
            {
                "url": "https://example.com/",
                "viewports": {
                    "desktop_1920x1080": {
                        "link_summary": {
                            "sample_internal": [
                                "https://example.com/product?category=1",
                                "https://example.com/contact",
                            ]
                        }
                    }
                },
            }
        ]
    }
    discovered = evidence_bundle.discover_page_urls("https://example.com/", pages, rendered, limit=5)
    assert "https://example.com/about" in discovered
    assert "https://example.com/contact" in discovered
    assert len([url for url in discovered if "/product/" in url]) == 1
    assert all("assets/app.js" not in url and "other.example" not in url for url in discovered)


def test_route_sample_audit_flags_reused_spa_shell_metadata() -> None:
    pages = [
        {
            "url": f"https://example.com/{path}",
            "title": "Same title",
            "meta_description": "Same description",
            "content_audit": {"has_body_text_in_raw_html": False},
            "link_summary": {"anchor_count": 0},
        }
        for path in ("", "product/9", "about")
    ]
    audit = evidence_bundle.route_sample_audit(pages, [page["url"] for page in pages[1:]])
    assert audit["possible_spa_shell"] is True
    assert audit["raw_shell_pages"] == 3
    assert audit["duplicate_title_groups"][0]["value"] == "Same title"


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


def test_headless_audit_records_rendered_only_body_links_and_images() -> None:
    raw = {
        "url": "https://example.com",
        "final_url": "https://example.com",
        "title": "Example",
        "meta_description": "Description",
        "canonical": "https://example.com",
        "robots_meta": "index, follow",
        "h1": [],
        "schema_audit": {"schema_types_found": [], "inline_schema_count": 0},
        "content_audit": {"has_body_text_in_raw_html": False},
        "link_summary": {"anchor_count": 0},
        "image_stats": {"total": 0},
    }
    rendered = {
        "title": "Example",
        "meta_description": "Description",
        "canonical": "https://example.com",
        "robots_meta": "index, follow",
        "h1": [],
        "schema_types": [],
        "schema_count": 0,
        "has_body_text": True,
        "link_summary": {"anchor_count": 12},
        "images": {"total": 4},
    }
    comparison = build_headless_audit(
        {"pages": [raw]},
        {"pages": [{"url": "https://example.com", "viewports": {"desktop_1920x1080": rendered}}]},
        "general",
    )["pages"][0]
    assert {item["field"] for item in comparison["diffs"]} >= {"has_body_text", "link_count", "image_count"}


def test_headless_audit_records_profile_specific_navigation() -> None:
    raw = {
        "url": "https://example.com/",
        "final_url": "https://example.com/",
        "status": 200,
        "title": "Example",
        "meta_description": "Description",
        "canonical": "https://example.com/",
        "robots_meta": "index, follow",
        "h1": ["Example"],
        "schema_audit": {"schema_types_found": [], "inline_schema_count": 0},
        "content_audit": {"has_body_text_in_raw_html": True},
        "link_summary": {"anchor_count": 1},
        "image_stats": {"total": 0},
    }
    base_view = {
        "title": "Example",
        "meta_description": "Description",
        "canonical": "https://example.com/",
        "robots_meta": "index, follow",
        "h1": ["Example"],
        "schema_types": [],
        "schema_count": 0,
        "has_body_text": True,
        "link_summary": {"anchor_count": 1},
        "images": {"total": 0},
    }
    rendered = {
        "pages": [
            {
                "url": "https://example.com/",
                "viewports": {
                    "desktop_1920x1080": {**base_view, "url": "https://example.com/desktop/"},
                    "mobile_375x812": {**base_view, "url": "https://example.com/mobile/"},
                },
            }
        ]
    }
    audit = build_headless_audit({"pages": [raw]}, rendered, "general")
    assert audit["pages"][0]["profile_navigation"]["varies"] is True
    assert any("navigation varies by browser profile" in item for item in audit["warnings"])


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


def test_balanced_technology_results_normalize_extended_signals(monkeypatch) -> None:
    monkeypatch.setattr(technology_probe, "version", lambda _: "2.0.2")
    report = technology_probe._normalize_wappalyzer_results(
        {
            "https://example.com/": {
                "React": {
                    "version": "18",
                    "confidence": 100,
                    "categories": ["JavaScript frameworks"],
                    "groups": ["Web development"],
                }
            }
        },
        ["https://example.com"],
        "balanced",
    )
    assert report["collection_status"] == "ok"
    assert report["scan_mode"] == "balanced"
    assert report["pages"][0]["technologies"][0]["name"] == "React"
    assert "script_sources" in report["pages"][0]["fingerprint_inputs"]


def test_technology_fallback_uses_explicit_asset_evidence() -> None:
    report = technology_probe._normalize_wappalyzer_results(
        {"https://example.com/": {}},
        ["https://example.com/"],
        "balanced",
    )
    evidence_pages = [
        {
            "url": "https://example.com/",
            "final_url": "https://example.com/",
            "links": [
                {"rel": "modulepreload", "href": "https://example.com/js/vue-vendor-abc.js"},
                {"rel": "modulepreload", "href": "https://example.com/js/swiper-vendor-def.js"},
            ],
            "resources": [
                {"type": "script", "url": "https://hm.baidu.com/hm.js?site=secret"},
            ],
        }
    ]
    technology_probe.enrich_with_page_evidence(report, evidence_pages)
    page = report["pages"][0]
    assert {item["name"] for item in page["technologies"]} >= {"Vue.js", "Swiper", "Baidu Analytics"}
    assert "asset_urls" in page["fingerprint_inputs"]
    assert page["tag_audit"]["status"] == "detected"
    assert "secret" not in json.dumps(page["tag_audit"])


def test_technology_report_consumes_existing_runtime_evidence() -> None:
    report = {
        "scan_mode": "balanced",
        "pages": [
            {
                "url": "https://example.com/",
                "final_url": "https://example.com/",
                "fingerprint_inputs": ["raw_html"],
                "technologies": [],
                "tag_audit": {"status": "not_detected_in_static_assets", "detected": []},
            }
        ],
        "tag_audit": {"status": "not_detected_in_static_assets", "detected": []},
    }
    evidence = {
        "seed_url": "https://example.com/",
        "rendered": {
            "generated_at": "2026-07-17T00:00:00Z",
            "runtime_summary": {"technologies": ["Swiper"], "analytics_tags": ["Baidu Analytics"]},
            "pages": [
                {
                    "url": "https://example.com/",
                    "viewports": {
                        "desktop_1920x1080": {
                            "url": "https://example.com/",
                            "technology_signals": [
                                {
                                    "name": "Swiper",
                                    "version": "",
                                    "confidence": 90,
                                    "categories": ["JavaScript libraries"],
                                    "groups": ["Web development"],
                                    "evidence": ["https://example.com/swiper-vendor.js"],
                                }
                            ],
                            "analytics_audit": {
                                "detected": [
                                    {"name": "Baidu Analytics", "evidence": ["https://hm.baidu.com/hm.js"]}
                                ]
                            },
                        }
                    },
                }
            ],
        },
    }
    technology_probe.enrich_with_runtime_evidence(report, evidence)
    page = report["pages"][0]
    assert {item["name"] for item in page["technologies"]} == {"Swiper"}
    assert {item["name"] for item in report["tag_audit"]["detected"]} == {"Baidu Analytics"}
    assert {"rendered_dom", "runtime_javascript", "network_requests"}.issubset(page["fingerprint_inputs"])


def test_rendered_mobile_profile_uses_mobile_user_agent() -> None:
    options = rendered_probe.context_options("mobile_375x812", {"width": 375, "height": 812})
    assert options["is_mobile"] is True
    assert "Mobile" in options["user_agent"]
    assert options["viewport"] == {"width": 375, "height": 812}


def test_rendered_runtime_summary_keeps_profile_navigation_variants() -> None:
    report = {
        "pages": [
            {
                "url": "https://example.com/",
                "viewports": {
                    "desktop_1920x1080": {
                        "url": "https://example.com/desktop/",
                        "technology_signals": [{"name": "Vue.js", "evidence": ["https://example.com/vue-vendor.js"]}],
                        "analytics_audit": {"detected": []},
                    },
                    "mobile_375x812": {
                        "url": "https://example.com/mobile/",
                        "technology_signals": [{"name": "Vue.js", "evidence": ["https://example.com/vue-vendor.js"]}],
                        "analytics_audit": {
                            "detected": [{"name": "Baidu Analytics", "evidence": ["https://hm.baidu.com/hm.js"]}]
                        },
                    },
                },
            }
        ]
    }
    summary = rendered_probe.summarize_runtime_report(report)
    assert summary["navigation_variants"][0]["final_urls"] == [
        "https://example.com/desktop/",
        "https://example.com/mobile/",
    ]
    assert summary["technologies"] == ["Vue.js"]
    assert summary["analytics_tags"] == ["Baidu Analytics"]


def test_architecture_analysis_connects_stack_to_measured_seo_risk() -> None:
    report = {
        "scan_mode": "full",
        "pages": [
            {
                "fingerprint_inputs": ["rendered_dom", "runtime_javascript", "network_requests"],
                "technologies": [
                    {"name": "Shopify", "categories": ["Ecommerce"]},
                    {"name": "Cloudflare", "categories": ["CDN"]},
                    {"name": "React", "categories": ["JavaScript frameworks"]},
                    {"name": "Vue.js", "categories": ["JavaScript frameworks"]},
                    {"name": "Google Tag Manager", "categories": ["Tag managers"]},
                ],
            }
        ],
    }
    performance = {
        "aggregate": {
            "performance_score": {"median": 25},
            "metrics": {
                "largest-contentful-paint": {"median": 14755},
                "total-blocking-time": {"median": 941},
            },
        }
    }
    analysis = analyze_architecture(report, performance=performance)
    assert "Shopify-managed commerce" in analysis["summary"]
    assert analysis["evidence_quality"]["runtime_browser_signals"] is True
    performance_impact = next(item for item in analysis["seo_impacts"] if item["area"] == "performance")
    assert performance_impact["risk"] == "high"
    assert any("Lighthouse median performance score: 25" in item for item in performance_impact["evidence"])


def test_architecture_analysis_does_not_invent_zero_evidence_integrations() -> None:
    analysis = analyze_architecture(
        {
            "scan_mode": "balanced",
            "pages": [{"fingerprint_inputs": ["raw_html", "script_sources"], "technologies": []}],
        }
    )
    impacts = {item["area"]: item for item in analysis["seo_impacts"]}
    assert impacts["crawl_and_rendering"]["risk"] == "unknown"
    assert impacts["analytics_consent"]["evidence"] == []
    assert "no analytics" in impacts["analytics_consent"]["conclusion"].lower()
    assert impacts["commerce_search_features"]["evidence"] == []
    assert "no commerce" in impacts["commerce_search_features"]["conclusion"].lower()


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
    monkeypatch.setattr(technology_probe, "_collect_page_evidence", lambda *args: ([], []))
    report = technology_probe.collect([f"https://example.com/{index}" for index in range(12)], scan_mode="fast")
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
        "requested_url": "https://example.com/",
        "final_url": "https://m.example.com/",
        "main_document_url": "https://m.example.com/",
        "redirected": True,
        "run_final_urls": ["https://m.example.com/"],
        "redirect_consistent": True,
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
    assert report["final_url"] == "https://m.example.com/"
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


def test_proxy_fake_ip_range_is_allowed_without_private_bypass(monkeypatch) -> None:
    monkeypatch.setattr(
        socket,
        "getaddrinfo",
        lambda *args, **kwargs: [(socket.AF_INET, socket.SOCK_STREAM, 6, "", ("198.18.0.26", 443))],
    )
    _, _, addresses = resolve_target("public.example", 443, allow_private=False)
    assert addresses == ["198.18.0.26"]


def test_single_run_performance_is_smoke_confidence_only() -> None:
    assert performance_confidence({"collection_status": "ok", "runs_succeeded": 1, "aggregate": {}}) == 0.6
    assert performance_confidence({"collection_status": "ok", "runs_succeeded": 5, "aggregate": {}}) == 0.9


def _crux_payload(scope: str, value: str, p75: int | float = 1200, *, history: bool = False) -> dict:
    metrics = {}
    for name in crux_probe.METRICS:
        if history:
            metrics[name] = {"percentilesTimeseries": {"p75s": [p75 + 100, p75]}}
        else:
            metrics[name] = {"percentiles": {"p75": str(p75) if name == "cumulative_layout_shift" else p75}}
    record = {"key": {scope: value}, "metrics": metrics}
    if history:
        record["collectionPeriods"] = [{"firstDate": {"year": 2026}, "lastDate": {"year": 2026}}]
    return {"record": record}


def test_crux_collects_current_history_and_latest_pointer(tmp_path) -> None:
    calls = []

    def request(endpoint, body, key, timeout):
        calls.append((endpoint, body, key, timeout))
        scope = "url" if "url" in body else "origin"
        return _crux_payload(scope, body[scope], history="queryHistoryRecord" in endpoint)

    report = crux_probe.collect(
        "https://example.com/page",
        tmp_path,
        form_factors=("aggregate", "mobile"),
        key="secret-key",
        requester=request,
    )

    assert report["collection_status"] == "ok"
    assert len(calls) == 4
    assert calls[1][1]["collectionPeriodCount"] == 40
    assert calls[2][1]["formFactor"] == "PHONE"
    assert report["summary"]["aggregate"]["core_web_vitals"] == "poor"
    assert Path(report["manifest"]["path"]).is_file()
    assert (tmp_path / "latest.json").is_file()
    assert "secret-key" not in (tmp_path / "latest.json").read_text()


def test_crux_page_no_data_falls_back_to_origin_without_mixing_history(tmp_path) -> None:
    calls = []

    def request(endpoint, body, key, timeout):
        calls.append(body)
        if "url" in body:
            raise crux_probe.CruxNoData("missing")
        return _crux_payload("origin", body["origin"], history="collectionPeriodCount" in body)

    report = crux_probe.collect(
        "https://example.com/page", tmp_path, form_factors=("desktop",), key="key", requester=request
    )

    query = report["queries"][0]
    assert query["effective_scope"] == "origin"
    assert query["fallback_reason"] == "page_data_unavailable"
    assert "origin" in calls[-1]
    assert "url" not in calls[-1]
    assert any(item["code"] == "origin_fallback" for item in report["warnings"])


def test_crux_no_data_is_not_a_failed_collection(tmp_path) -> None:
    def request(*args):
        raise crux_probe.CruxNoData("missing")

    report = crux_probe.collect(
        "https://example.com", tmp_path, form_factors=("aggregate",), key="key", requester=request
    )
    assert report["collection_status"] == "no_data"
    assert report["errors"] == []


def test_crux_classifies_core_web_vitals() -> None:
    assert crux_probe.classify("largest_contentful_paint", 2500) == "good"
    assert crux_probe.classify("interaction_to_next_paint", 350) == "needs_improvement"
    assert crux_probe.classify("cumulative_layout_shift", "0.3") == "poor"
