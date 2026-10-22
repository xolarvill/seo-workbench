"""Regression cases where collection failures used to become SEO findings."""
from __future__ import annotations

import pytest

from seo_workbench.tech_audit import CrawlConfig, _classify_response, evaluate_rules
from seo_workbench_tools import evidence_bundle, page_probe
from seo_workbench_tools.headless import build_headless_audit


def page(url: str = "https://example.com/", **changes) -> dict:
    return {
        "url": url, "final_url": url, "status_code": 200,
        "crawl_status": "ok", "content_type": "text/html",
        "title": url, "meta_description": url, "h1": ["Page"],
        "canonical": url, "hreflang": [], "outlinks": [],
        "indexability": {"indexable": True, "directives": []},
        "inlink_count": 1, "redirect_chain": [url], **changes,
    }


@pytest.mark.parametrize("status,crawl_status", [(429, "rate_limited"), (None, "fetch_error"), (200, "parse_error"), (403, "blocked_by_waf")])
def test_unavailable_alternate_does_not_prove_missing_return_or_non_200(status, crawl_status):
    alternate = page("https://example.com/de", status_code=status, crawl_status=crawl_status)
    source = page(hreflang=[{"hreflang": "de", "href": alternate["url"]}], canonical=alternate["url"])
    rules = {i["rule_id"] for i in evaluate_rules([source, alternate], [], [], CrawlConfig())}
    assert not rules & {"HREFLANG_MISSING_RETURN_LINK", "HREFLANG_TO_NON_200", "CANONICAL_TO_NON_200"}


def test_known_error_target_and_successful_missing_return_are_still_reported():
    alternate = page("https://example.com/de", status_code=404, crawl_status="http_error")
    source = page(hreflang=[{"hreflang": "de", "href": alternate["url"]}], canonical=alternate["url"])
    rules = {i["rule_id"] for i in evaluate_rules([source, alternate], [], [], CrawlConfig())}
    assert {"HTTP_4XX", "HREFLANG_TO_NON_200", "CANONICAL_TO_NON_200"} <= rules
    assert "HREFLANG_MISSING_RETURN_LINK" not in rules
    alternate.update(status_code=200, crawl_status="ok")
    assert "HREFLANG_MISSING_RETURN_LINK" in {i["rule_id"] for i in evaluate_rules([source, alternate], [], [], CrawlConfig())}


@pytest.mark.parametrize("status,crawl_status", [(None, "fetch_error"), (429, "rate_limited"), (200, "parse_error"), (403, "blocked_by_waf")])
def test_failed_sitemap_observation_is_not_a_sitemap_defect(status, crawl_status):
    sitemap = {"url": "https://example.com/sitemap.xml", "status_code": status, "crawl_status": crawl_status}
    assert not evaluate_rules([page()], [sitemap], [], CrawlConfig())


def test_true_sitemap_error_is_not_suppressed():
    issues = evaluate_rules([page()], [{"url": "https://example.com/sitemap.xml", "status_code": 404}], [], CrawlConfig())
    assert "SITEMAP_NON_200" in {i["rule_id"] for i in issues}


def test_noindex_with_inlinks_remains_detectable():
    p = page(indexability={"indexable": False, "directives": ["noindex"]})
    assert "ACCIDENTAL_NOINDEX" in {i["rule_id"] for i in evaluate_rules([p], [], [], CrawlConfig())}


def test_http_error_body_is_not_used_for_metadata_or_duplicates():
    pages = [page(), page("https://example.com/missing", status_code=404, crawl_status="http_error", title="", h1=[], canonical="")]
    rules = {i["rule_id"] for i in evaluate_rules(pages, [], [], CrawlConfig())}
    assert "HTTP_4XX" in rules
    assert not rules & {"MISSING_TITLE", "MISSING_H1", "MISSING_CANONICAL"}


def test_partial_crawl_does_not_prove_orphan_or_missing_sitemap_member():
    p = page("https://example.com/deep", inlink_count=0)
    rules = {i["rule_id"] for i in evaluate_rules([page(), p], [], [{"url": p["url"]}, {"url": "https://example.com/unfetched"}], CrawlConfig(), coverage_complete=False)}
    assert not rules & {"NO_INTERNAL_INLINKS", "ORPHAN_CANDIDATE", "SITEMAP_NOT_CRAWLED", "CRAWLED_NOT_IN_SITEMAP"}


def test_nested_headings_and_svg_titles_are_parsed_in_document_context():
    parsed = page_probe.parse_html('<head><title>Shop</title></head><body><h1><a><span>Desk</span> setup</a></h1><svg><title>Visa</title></svg><h2>Choose <em>well</em></h2></body>', "https://example.com/")
    assert parsed["title"] == "Shop"
    assert parsed["h1"] == ["Desk setup"]
    assert parsed["h2"] == ["Choose well"]


def test_closing_void_tag_does_not_pop_the_heading():
    parsed = page_probe.parse_html('<title>Shop</title><h1>Desk<br/> setup</h1>', "https://example.com/")
    assert parsed["h1"] == ["Desk setup"]


def test_embedded_challenge_script_is_not_alone_proof_of_a_block():
    assert _classify_response(200, {}, b'<html><title>Security guide</title><script src="/cdn-cgi/challenge-platform/widget.js"></script></html>') == "ok"


def test_200_challenge_is_unavailable_and_not_a_missing_content_finding(monkeypatch):
    html = '<html><title>Just a moment...</title><script>window._cf_chl_opt = {};</script></html>'
    assert _classify_response(200, {}, html.encode()) == "blocked_by_waf"
    monkeypatch.setattr(page_probe, "fetch", lambda *_: {"status": 200, "final_url": "https://example.com/", "content_type": "text/html", "headers": {}, "html": html, "html_bytes": len(html)})
    raw = page_probe.probe("https://example.com/")
    assert raw["evidence_quality"]["html_eligible"] is False
    bundle = {"pages": [raw], "site": {}, "errors": []}
    assert evidence_bundle.collection_status(bundle) == "partial"
    audit = build_headless_audit(bundle, None, "shopify-headless")
    assert not audit["critical"]
    assert audit["status"] == "warn"


def test_rate_limit_does_not_masquerade_as_raw_rendered_content_failure():
    raw = {"url": "https://example.com/", "status": 429, "h1": [], "error": "rate limited"}
    audit = build_headless_audit({"pages": [raw]}, None, "shopify-headless")
    assert not audit["critical"]
    assert audit["status"] == "warn"


@pytest.mark.parametrize("failure", ["page", "sitemap", "robots"])
def test_unavailable_evidence_never_verifies_a_fixed_issue(tmp_path, monkeypatch, failure):
    from seo_workbench import state, tech_audit
    from seo_workbench.tech_issues import list_issue_register, update_issue_status

    project = tmp_path / "project"
    seed = "http://127.0.0.1:8765/"
    state.init_state("general", "Test", seed, project_dir=project)
    failing = False

    async def crawl(*_args, **_kwargs):
        p = page(seed, h1=[] if not failing else ["Fixed"])
        if failing and failure == "page":
            p.update(status_code=429, crawl_status="rate_limited")
        return {
            "pages": {seed: p}, "errors": [], "stopped_by_limit": False,
            "remaining_queue": [], "sitemap_entries": [],
            "sitemap_records": [{"url": seed + "sitemap.xml", "status_code": 429, "crawl_status": "rate_limited"}] if failing and failure == "sitemap" else [],
            "robots": {"collection_status": "unavailable" if failing and failure == "robots" else "ok"},
        }

    monkeypatch.setattr(tech_audit, "_crawl", crawl)
    config = CrawlConfig(allow_private=True)
    first, _ = tech_audit.run_tech_audit(project, config)
    issue = next(i for i in tech_audit.load_tech_issues(project) if i["rule_id"] == "MISSING_H1")
    update_issue_status(project, issue["fingerprint"], "fixed", note="Patched", owner="maintainer")
    failing = True
    second, _ = tech_audit.run_tech_audit(project, config)
    assert first["config_fingerprint"] == second["config_fingerprint"]
    assert second["collection_status"] == "partial"
    assert second["summary"]["issue_register"]["verified"] == 0
    assert second["summary"]["issue_register"]["provisional_verified"] == 0
    record = next(i for i in list_issue_register(project)["issues"] if i["fingerprint"] == issue["fingerprint"])
    assert record["status"] == "fixed"
    assert record["verification_status"] == "pending"
    assert record["owner"] == "maintainer"


def test_non_200_raw_document_reports_http_without_inventing_missing_metadata():
    audit = build_headless_audit({"pages": [{"url": "https://example.com/missing", "status": 404}]}, None, "shopify-headless")
    assert audit["critical"] == ["https://example.com/missing: raw response status is 404"]


def test_edge_provider_headers_alone_do_not_prove_a_waf_block():
    assert _classify_response(403, {"server": "cloudflare", "cf-ray": "request-id"}, b'<title>Forbidden</title>') == "http_error"


def test_challenge_literal_in_documentation_is_not_a_block():
    html = b'<html><title>Diagnosing Cloudflare challenges</title><h1>Guide</h1><pre>window._cf_chl_opt = {};</pre></html>'
    assert _classify_response(200, {}, html) == "ok"


def test_cf_mitigated_header_survives_raw_header_projection():
    from seo_workbench_tools.response_quality import response_quality
    headers = page_probe.response_headers({"cf-mitigated": "challenge"})
    assert response_quality(200, "text/html", headers=headers, body=b'<title>Please wait</title>')["html_eligible"] is False


def test_non_html_success_does_not_invent_missing_metadata(monkeypatch):
    monkeypatch.setattr(page_probe, "fetch", lambda *_: {"status": 200, "final_url": "https://example.com/", "content_type": "application/json", "headers": {}, "html": '{}', "html_bytes": 2})
    raw = page_probe.probe("https://example.com/")
    audit = build_headless_audit({"pages": [raw]}, None, "general")
    assert not audit["critical"]
    assert not raw["evidence_quality"]["html_eligible"]


@pytest.mark.parametrize("limit", ["urls", "sitemaps"])
def test_sitemap_coverage_limits_are_explicit(tmp_path, monkeypatch, limit):
    import asyncio
    from seo_workbench import tech_audit
    xml = (b'<urlset><url><loc>https://example.com/a</loc></url><url><loc>https://example.com/b</loc></url></urlset>' if limit == "urls" else b'<sitemapindex><sitemap><loc>https://example.com/child.xml</loc></sitemap></sitemapindex>')

    async def fetch(*_args):
        return {"status": 200, "body": xml, "headers": {"content-type": "application/xml"}}

    monkeypatch.setattr(tech_audit, "_fetch", fetch)
    records, _ = asyncio.run(tech_audit._fetch_sitemaps("https://example.com/", {}, CrawlConfig(max_urls=1, max_sitemaps=1), tmp_path))
    assert records[0]["entries_truncated" if limit == "urls" else "sitemaps_truncated"] is True


def test_successful_sitemap_retry_supersedes_old_failure_in_continuation(tmp_path, monkeypatch):
    import json
    from seo_workbench import state, tech_audit
    project = tmp_path / "project"
    seed = "http://127.0.0.1:8765/"
    state.init_state("general", "Test", seed, project_dir=project)

    async def crawl(_seed, _config, root, start_urls=None, **_kwargs):
        first = start_urls is None
        sitemap = {"url": seed + "sitemap.xml", "status_code": 429 if first else 200, "crawl_status": "rate_limited" if first else "ok", "type": "unknown" if first else "urlset"}
        (root / "raw").mkdir(parents=True, exist_ok=True)
        (root / "raw/site.json").write_text(json.dumps({"sitemaps": [sitemap]}))
        remaining = [{"url": seed + "next", "crawl_depth": 1, "crawl_source": "link"}] if first else []
        tech_audit._jsonl_write(root / "normalized/remaining-queue.jsonl", remaining)
        p = page(seed if first else seed + "next")
        return {"pages": {p["url"]: p}, "errors": [], "stopped_by_limit": first, "remaining_queue": remaining, "sitemap_entries": [], "sitemap_records": [sitemap]}

    monkeypatch.setattr(tech_audit, "_crawl", crawl)
    first, _ = tech_audit.run_tech_audit(project, CrawlConfig(allow_private=True))
    assert first["collection_status"] == "partial"
    resumed, _ = tech_audit.continue_tech_audit(project)
    assert resumed["collection_status"] == "ok"
    assert not resumed["errors"]
