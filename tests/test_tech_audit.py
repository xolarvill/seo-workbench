from __future__ import annotations

import asyncio
import hashlib
import json
import os
import pytest
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from threading import Thread

from seo_workbench import state, tech_audit as tech_audit_module
from seo_workbench.shopify_crawler import build_crawler_access
from seo_workbench.cli import main
from seo_workbench.tech_audit import (
    CrawlConfig,
    CONFIG_FINGERPRINT_VERSION,
    RULES,
    TechAuditViewQuery,
    _classify_response,
    _retry_after_seconds,
    _xml_entries,
    _parse_html,
    _semantic_config_fingerprint,
    continue_tech_audit,
    delete_tech_audit_run,
    evaluate_rules,
    normalize_url,
    page_template,
    page_type,
    prune_tech_audit_history,
    prioritize_issues,
    query_tech_audit,
    recrawl_urls,
    run_tech_audit,
    schedule_due,
    set_schedule,
    tech_audit_history,
)


def _test_page(url: str, *, outlinks: list[dict] | None = None, depth: int = 0) -> dict:
    return {
        "page_id": f"page_{url.rsplit('/', 1)[-1] or 'root'}",
        "url": url,
        "final_url": url,
        "scope": "Internal",
        "host_relation": "same_host",
        "status_code": 200,
        "content_type": "text/html",
        "response_time_ms": 10,
        "response_size": 100,
        "crawl_depth": depth,
        "inlinks": [],
        "inlink_count": 0,
        "outlinks": outlinks or [],
        "outlink_count": len(outlinks or []),
        "anchor_text": [],
        "rel": [],
        "title": "Page",
        "meta_description": "Description",
        "meta_keywords": "",
        "h1": ["Page"],
        "h2": [],
        "canonical": url,
        "canonical_values": [url],
        "hreflang": [],
        "meta_robots": "",
        "x_robots_tag": "",
        "indexability": {"status": "indexable", "indexable": True, "directives": []},
        "html_content_hash": url,
        "redirect_chain": [url],
        "redirect_loop": False,
        "redirect_to_external": False,
        "crawl_sources": ["seed"],
        "crawl_status": "ok",
        "error": "",
    }


def test_crawl_deduplicates_candidates_and_persists_remaining_queue(tmp_path: Path, monkeypatch) -> None:
    seed = "https://example.com/"

    async def fake_fetch(url: str, *_args: object, **_kwargs: object) -> dict:
        if url.endswith("/robots.txt"):
            return {"status": 200, "final_url": url, "headers": {"content-type": "text/plain"}, "body": b"User-agent: *\nAllow: /\n"}
        return {"status": 200, "final_url": url, "headers": {"content-type": "text/html"}, "body": b'<html><title>Page</title><h1>Page</h1><a href="/a">A</a><a href="/a">A again</a><a href="/b">B</a></html>'}

    monkeypatch.setattr(tech_audit_module, "_fetch", fake_fetch)
    output_root = tmp_path / "run"
    result = asyncio.run(tech_audit_module._crawl(seed, CrawlConfig(max_urls=1, load_sitemap=False), output_root))

    assert result["discovered_unique"] == 3
    assert result["queued_remaining"] == 2
    queue = [json.loads(line) for line in (output_root / "normalized/remaining-queue.jsonl").read_text().splitlines()]
    assert [item["url"] for item in queue] == ["https://example.com/a", "https://example.com/b"]
    known_result = asyncio.run(tech_audit_module._crawl(seed, CrawlConfig(max_urls=1, load_sitemap=False), tmp_path / "known", known_urls={"https://example.com/a"}))
    assert [item["url"] for item in known_result["remaining_queue"]] == ["https://example.com/b"]


def test_continue_crawl_merges_previous_pages_and_consumes_queue(tmp_path: Path, monkeypatch) -> None:
    project = tmp_path / "project"
    state.init_state("general", "Test", "http://127.0.0.1:8765", project_dir=project)
    root = "http://127.0.0.1:8765/"
    page_a = "http://127.0.0.1:8765/a"
    page_b = "http://127.0.0.1:8765/b"

    async def fake_crawl(_seed: str, _config: CrawlConfig, _output_root: Path, start_urls: list[str] | None = None, **_kwargs: object) -> dict:
        if start_urls is None:
            link = {"url": page_a, "internal_external": "Internal", "host_relation": "same_host", "anchor_text": "A", "rel": [], "excluded_reason": ""}
            remaining = [{"url": page_a, "crawl_depth": 1, "crawl_source": "link"}]
            result = {"pages": {root: _test_page(root, outlinks=[link])}, "sitemap_records": [], "sitemap_entries": [], "errors": [], "stopped_by_limit": True, "discovered_unique": 2, "queued_remaining": 1, "remaining_queue": remaining}
        else:
            remaining = [{"url": page_b, "crawl_depth": 2, "crawl_source": "link"}]
            result = {"pages": {page_a: _test_page(page_a, depth=1)}, "sitemap_records": [], "sitemap_entries": [], "errors": [], "stopped_by_limit": False, "discovered_unique": 2, "queued_remaining": 1, "remaining_queue": remaining}
        tech_audit_module._jsonl_write(_output_root / "normalized/remaining-queue.jsonl", remaining)
        return result

    monkeypatch.setattr(tech_audit_module, "_crawl", fake_crawl)
    first, _ = run_tech_audit(project, CrawlConfig(max_urls=1, allow_private=True))
    assert first["summary"]["queued_remaining"] == 1
    continued, _ = continue_tech_audit(project)

    assert continued["continuation_of"] == first["run_id"]
    assert continued["summary"]["pages"] == 2
    assert continued["summary"]["crawl_batch"] == 2
    assert continued["summary"]["queued_remaining"] == 1
    assert continued["config_fingerprint"] == first["config_fingerprint"]


def test_normalize_url_and_html_fields() -> None:
    assert normalize_url("HTTPS://Example.com/a/?utm_source=x#fragment") == "https://example.com/a"
    assert normalize_url("https://example.com/blogs/news/hexcal-studio%E2%84%A2-plus-review") == "https://example.com/blogs/news/hexcal-studio%E2%84%A2-plus-review"
    assert normalize_url("https://example.com/blogs/news/hexcal-studio™-plus-review") == "https://example.com/blogs/news/hexcal-studio%E2%84%A2-plus-review"
    parsed = _parse_html(
        '<head><title>Title</title><meta name="description" content="Description"></head>'
        '<meta name="keywords" content="one,two"><h1>Heading</h1><h2>Sub</h2>'
        '<a href="/target" rel="nofollow sponsored"> Target </a>'
        '<svg><title>Visa</title></svg>',
        "https://example.com/",
    )
    assert parsed["title"] == "Title"
    assert parsed["meta_keywords"] == "one,two"
    assert parsed["h1"] == ["Heading"]
    assert parsed["h2"] == ["Sub"]
    assert parsed["outlinks"][0]["anchor_text"] == "Target"
    assert parsed["outlinks"][0]["rel"] == ["nofollow", "sponsored"]


def test_page_template_ignores_locale_prefixes() -> None:
    assert page_template("https://example.com/de/products/desk") == "product"


def test_semantic_config_fingerprint_ignores_collection_parameters() -> None:
    base = CrawlConfig(allow_private=False)
    relaxed = CrawlConfig(allow_private=True, max_urls=10, timeout=5.0, concurrency=1)
    assert _semantic_config_fingerprint(base) == _semantic_config_fingerprint(relaxed)
    strict = CrawlConfig(high_depth=5)
    assert _semantic_config_fingerprint(base) != _semantic_config_fingerprint(strict)
    assert CONFIG_FINGERPRINT_VERSION == "v2-semantic"
    assert page_template("https://example.com/en-ca/blogs/articles/guide") == "article"
    assert page_template("https://example.com/es/blogs/news") == "blog"
    assert page_type("https://example.com/es/custom/landing") == "other"


def test_crawl_block_classification_and_retry_after() -> None:
    assert _retry_after_seconds({"retry-after": "60"}) == 60.0
    assert _classify_response(429, {"server": "cloudflare"}, b"local_rate_limited") == "rate_limited"
    assert _classify_response(403, {"server": "cloudflare"}, b"Access denied") == "blocked_by_waf"
    assert _classify_response(404, {"content-type": "text/html"}, b"<h1>Not found</h1>") == "http_error"


def test_shopify_crawler_headers_are_scoped_to_exact_domain() -> None:
    access = build_crawler_access(
        domain_host="example.com",
        signature="sig1=:private:",
        signature_input='sig1=("@authority");expires=4102444800',
        signature_agent='"https://shopify.com"',
        expires_at=datetime(2030, 1, 1, tzinfo=timezone.utc),
        seed_url="https://example.com/",
    )
    assert access.headers_for("https://example.com/page")["Signature"] == "sig1=:private:"
    assert access.headers_for("https://cdn.example.com/image.png") == {}


def test_rate_limited_response_is_not_a_real_http_4xx_issue() -> None:
    common = {
        "page_id": "page_1",
        "url": "https://example.com/limited",
        "final_url": "https://example.com/limited",
        "content_type": "text/html",
        "indexability": {"indexable": None, "directives": []},
        "inlinks": [],
        "inlink_count": 0,
        "redirect_chain": ["https://example.com/limited"],
        "h1": [],
        "h2": [],
        "html_content_hash": "",
    }
    blocked = evaluate_rules([{**common, "status_code": 429, "crawl_status": "rate_limited"}], [], [], CrawlConfig())
    assert "HTTP_4XX" not in {issue["rule_id"] for issue in blocked}
    not_found = evaluate_rules([{**common, "status_code": 404, "crawl_status": "http_error"}], [], [], CrawlConfig())
    assert "HTTP_4XX" in {issue["rule_id"] for issue in not_found}


def test_rule_evaluation_deduplicates_repeated_link_fingerprints() -> None:
    link = {"url": "http://example.com/", "host_relation": "same_host"}
    issues = evaluate_rules([_test_page("https://example.com/page", outlinks=[link, link])], [], [], CrawlConfig())

    mixed = [issue for issue in issues if issue["rule_id"] == "HTTP_HTTPS_MIX"]
    assert len(mixed) == 1
    assert mixed[0]["template"] == "page"


def test_sitemap_parser_ignores_nested_image_locations() -> None:
    kind, entries = _xml_entries(
        '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9" xmlns:image="http://www.google.com/schemas/sitemap-image/1.1">'
        '<url><loc>https://example.com/products/item</loc><image:image><image:loc>https://cdn.example.com/item.png</image:loc></image:image></url>'
        '</urlset>'
    )
    assert kind == "urlset"
    assert entries == [{"loc": "https://example.com/products/item"}]


def test_rule_registry_and_structured_evidence() -> None:
    assert len(RULES) >= 30
    page = {
        "page_id": "page_1",
        "url": "https://example.com/",
        "final_url": "https://example.com/",
        "status_code": 200,
        "content_type": "text/html",
        "title": "",
        "meta_description": "",
        "h1": [],
        "h2": [],
        "canonical": "",
        "canonical_values": [],
        "hreflang": [],
        "indexability": {"indexable": True, "directives": []},
        "inlinks": [],
        "inlink_count": 0,
        "outlinks": [],
        "crawl_depth": 0,
        "response_time_ms": 1,
        "response_size": 10,
        "html_content_hash": "abc",
    }
    issues = evaluate_rules([page], [], [], CrawlConfig())
    by_rule = {item["rule_id"]: item for item in issues}
    assert {"MISSING_TITLE", "MISSING_META_DESCRIPTION", "MISSING_H1", "MISSING_CANONICAL"} <= by_rule.keys()
    assert by_rule["MISSING_TITLE"]["evidence"]["title"] == ""
    assert by_rule["MISSING_TITLE"]["fingerprint"]


def test_duplicate_group_evidence_is_bounded_without_changing_fingerprints() -> None:
    pages = [
        {
            **_test_page(f"https://example.com/page-{index}"),
            "title": "Shared title",
            "meta_description": f"Description {index}",
            "html_content_hash": f"hash-{index}",
        }
        for index in range(25)
    ]

    issues = [issue for issue in evaluate_rules(pages, [], [], CrawlConfig()) if issue["rule_id"] == "DUPLICATE_TITLE"]

    assert len(issues) == 25
    assert issues[0]["evidence"]["url_count"] == 25
    assert len(issues[0]["evidence"]["urls"]) == 10
    legacy_evidence = {"title": "Shared title", "urls": [page["url"] for page in pages]}
    expected = hashlib.sha256(
        json.dumps(
            {"rule_id": "DUPLICATE_TITLE", "url": pages[0]["url"], "evidence": legacy_evidence},
            sort_keys=True,
            ensure_ascii=False,
        ).encode()
    ).hexdigest()
    assert issues[0]["fingerprint"] == expected


def test_technical_view_reuses_projection_until_source_state_changes(tmp_path: Path, monkeypatch) -> None:
    project = tmp_path / "project"
    state.init_state("general", "Test", "https://example.com", project_dir=project)
    calls = {"inventory": 0, "issues": 0}

    def inventory(_project: Path) -> list[dict]:
        calls["inventory"] += 1
        return [_test_page("https://example.com/page")]

    def issues(_project: Path) -> list[dict]:
        calls["issues"] += 1
        return []

    monkeypatch.setattr(tech_audit_module, "load_tech_inventory", inventory)
    monkeypatch.setattr(tech_audit_module, "load_tech_issues", issues)
    monkeypatch.setattr(tech_audit_module, "load_issue_register", lambda _project: [])

    query_tech_audit(project, TechAuditViewQuery(dataset="pages"))
    query_tech_audit(project, TechAuditViewQuery(dataset="pages", query="page"))
    assert calls == {"inventory": 1, "issues": 1}

    register = project / "strategy/technical-issues.jsonl"
    register.parent.mkdir(parents=True, exist_ok=True)
    register.write_text("")
    current = register.stat().st_mtime_ns
    os.utime(register, ns=(current + 1_000_000, current + 1_000_000))
    query_tech_audit(project, TechAuditViewQuery(dataset="pages"))
    assert calls == {"inventory": 2, "issues": 2}


def test_schedule_is_due_and_private(tmp_path: Path) -> None:
    project = tmp_path / "project"
    state.init_state("general", "Test", "https://example.com", project_dir=project)
    schedule = set_schedule(project, 60)
    assert schedule_due(schedule)
    assert (project / ".runtime/tech-audit/schedule.json").stat().st_mode & 0o777 == 0o600


def test_recrawl_rejects_external_pages_and_more_than_1000_targets(tmp_path: Path, monkeypatch) -> None:
    project = tmp_path / "project"
    state.init_state("general", "Test", "https://example.com", project_dir=project)
    pages = [{"url": f"https://example.com/page-{index}", "host_relation": "same_host"} for index in range(1001)]
    monkeypatch.setattr(tech_audit_module, "load_tech_inventory", lambda _project: pages)
    with pytest.raises(ValueError, match="1000"):
        recrawl_urls(project, [page["url"] for page in pages])
    pages.append({"url": "https://cdn.example.net/asset", "host_relation": "external"})
    with pytest.raises(ValueError, match="already-crawled"):
        recrawl_urls(project, ["https://cdn.example.net/asset"])


def test_priority_combines_search_and_historical_inputs() -> None:
    issue = {"rule_id": "HTTP_4XX", "severity": "high", "url": "https://example.com/products/item"}
    prioritized = prioritize_issues(
        [issue],
        {issue["url"]: {"clicks": 100, "impressions": 1000, "ctr": 0.1, "position": 5}},
        {issue["url"]: {"clicks": 200, "impressions": 1200, "ctr": 0.16, "position": 4}},
    )[0]
    assert prioritized["priority"]["search_performance"]["clicks"] == 100
    assert prioritized["priority"]["historical_change"]["click_delta"] == -100
    assert prioritized["priority"]["business_importance"] == 1.5
    assert prioritized["priority"]["score"] > 50


def test_technical_audit_uses_canonical_search_analytics_pointer(tmp_path: Path) -> None:
    project = tmp_path / "project"
    state.init_state("general", "Test", "https://example.com", project_dir=project)
    url = "https://example.com/products/item"
    report = {
        "collection_status": "ok",
        "generated_at": "2026-08-09T05:05:30Z",
        "property": "https://example.com/",
        "window_days": 28,
        "data_state": "final",
        "windows": {
            "current": {"page": {"rows": [{"keys": [url], "clicks": 20, "impressions": 200, "ctr": 0.1, "position": 5}]}},
            "previous": {"page": {"rows": [{"keys": [url], "clicks": 10, "impressions": 100, "ctr": 0.1, "position": 6}]}},
        },
    }
    state.write_json(project / "audits/gsc/search-analytics/latest.json", report)

    current, previous, metadata = tech_audit_module._gsc_page_metrics(project)

    assert current[url]["clicks"] == 20
    assert previous[url]["clicks"] == 10
    assert metadata["generated_at"] == "2026-08-09T05:05:30Z"
    assert metadata["source"] == "audits/gsc/search-analytics/latest.json"


def test_site_family_link_filter_excludes_external_rows(tmp_path: Path, monkeypatch) -> None:
    links = [
        {"url": "https://example.com/", "host_relation": "same_host", "internal_external": "Internal"},
        {"url": "https://help.example.com/", "host_relation": "subdomain", "internal_external": "External"},
        {"url": "https://facebook.com/example", "host_relation": "external", "internal_external": "External"},
    ]
    monkeypatch.setattr(tech_audit_module, "load_tech_inventory", lambda _project: [])
    monkeypatch.setattr(tech_audit_module, "load_tech_issues", lambda _project: [])
    monkeypatch.setattr(tech_audit_module, "load_tech_links", lambda _project: links)
    monkeypatch.setattr(tech_audit_module, "_recrawl_pages", lambda _project: {})
    monkeypatch.setattr(tech_audit_module, "_snapshot_summary", lambda _project: {})
    result = query_tech_audit(tmp_path, TechAuditViewQuery(dataset="links", host_relation="site_family"))
    assert [row["url"] for row in result.rows] == ["https://example.com/", "https://help.example.com/"]


def test_history_selects_one_run_and_deleting_latest_repairs_conclusion(tmp_path: Path) -> None:
    project = tmp_path / "project"
    state.init_state("general", "Test", "https://example.com", project_dir=project)
    root = project / "audits/tech-audit"
    snapshots = []
    for run_id, title in (("run-1", "Correct title"), ("run-2", "Wrong title")):
        run_root = root / "runs" / run_id / "normalized"
        run_root.mkdir(parents=True, exist_ok=True)
        inventory = _test_page("https://example.com/page") | {"title": title}
        (run_root / "inventory.jsonl").write_text(json.dumps(inventory) + "\n")
        (run_root / "link-inventory.jsonl").write_text("")
        (run_root / "issues.jsonl").write_text("")
        (run_root.parent / "run.json").write_text(json.dumps({"run_id": run_id, "kind": "tech-audit", "status": "ok", "started_at": f"2026-08-0{run_id[-1]}T00:00:00Z", "finished_at": f"2026-08-0{run_id[-1]}T00:01:00Z"}))
        snapshot = {"kind": "tech-audit", "run_id": run_id, "generated_at": f"2026-08-0{run_id[-1]}T00:01:00+00:00", "collection_status": "ok", "summary": {"pages": 1}, "artifacts": {"run_dir": f"audits/tech-audit/runs/{run_id}", "inventory_path": f"audits/tech-audit/runs/{run_id}/normalized/inventory.jsonl", "link_inventory_path": f"audits/tech-audit/runs/{run_id}/normalized/link-inventory.jsonl", "issues_path": f"audits/tech-audit/runs/{run_id}/normalized/issues.jsonl"}}
        path = root / f"tech-audit-{run_id}.json"
        path.write_text(json.dumps(snapshot), encoding="utf-8")
        snapshots.append(snapshot)
    (root / "latest.json").write_text(json.dumps(snapshots[-1]), encoding="utf-8")

    selected = query_tech_audit(project, TechAuditViewQuery(dataset="pages", run_id="run-1"))
    assert selected.snapshot["run_id"] == "run-1"
    assert selected.rows[0]["title"] == "Correct title"
    assert [item["run_id"] for item in tech_audit_history(project)] == ["run-2", "run-1"]

    deleted = delete_tech_audit_run(project, "run-2")
    assert deleted["latest_run_id"] == "run-1"
    assert json.loads((root / "latest.json").read_text())["run_id"] == "run-1"
    assert not (root / "tech-audit-run-2.json").exists()
    assert not (root / "runs/run-2").exists()
    assert query_tech_audit(project, TechAuditViewQuery(dataset="pages")).rows[0]["title"] == "Correct title"


def test_prune_tech_audit_history_keeps_newest_completed_runs(tmp_path: Path) -> None:
    project = tmp_path / "project"
    state.init_state("general", "Test", "https://example.com", project_dir=project)
    root = project / "audits/tech-audit"
    snapshots = []
    for index in range(4):
        run_id = f"2026080{index + 1}T000000000000Z"
        run_root = root / "runs" / run_id / "normalized"
        run_root.mkdir(parents=True, exist_ok=True)
        (run_root / "inventory.jsonl").write_text("{}\n")
        (run_root.parent / "run.json").write_text(json.dumps({"run_id": run_id, "kind": "tech-audit", "status": "ok"}))
        snapshot = {
            "kind": "tech-audit",
            "run_id": run_id,
            "generated_at": f"2026-08-0{index + 1}T00:00:00+00:00",
            "collection_status": "ok",
            "summary": {"pages": 1},
            "artifacts": {
                "run_dir": f"audits/tech-audit/runs/{run_id}",
                "inventory_path": f"audits/tech-audit/runs/{run_id}/normalized/inventory.jsonl",
            },
        }
        (root / f"tech-audit-{run_id}.json").write_text(json.dumps(snapshot))
        snapshots.append(snapshot)
    (root / "latest.json").write_text(json.dumps(snapshots[-1]))

    assert prune_tech_audit_history(project, keep=3) == [snapshots[0]["run_id"]]
    assert [item["run_id"] for item in tech_audit_history(project)] == [item["run_id"] for item in snapshots[-1::-1][:3]]
    assert not (root / "runs" / snapshots[0]["run_id"]).exists()


def test_tech_audit_integration_writes_layered_snapshot(tmp_path: Path, capsys) -> None:
    class Handler(BaseHTTPRequestHandler):
        def do_GET(self) -> None:  # noqa: N802 - stdlib server API
            if self.path == "/robots.txt":
                body = f"User-agent: *\nAllow: /\nSitemap: http://127.0.0.1:{self.server.server_port}/sitemap.xml\n".encode()
                self.send_response(200)
                self.send_header("Content-Type", "text/plain")
                self.end_headers()
                self.wfile.write(body)
                return
            if self.path == "/sitemap.xml":
                body = (
                    f'<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9" xmlns:image="http://www.google.com/schemas/sitemap-image/1.1">'
                    f'<url><loc>http://127.0.0.1:{self.server.server_port}/</loc><image:image><image:loc>https://cdn.example.com/hero.png</image:loc></image:image></url>'
                    f'<url><loc>http://127.0.0.1:{self.server.server_port}/missing</loc></url></urlset>'
                ).encode()
                self.send_response(200)
                self.send_header("Content-Type", "application/xml")
                self.end_headers()
                self.wfile.write(body)
                return
            if self.path == "/missing":
                self.send_response(404)
                self.send_header("Content-Type", "text/html")
                self.end_headers()
                self.wfile.write(b"<title>Missing</title>")
                return
            body = b'<html><head><title>Home</title></head><body><h1>Home</h1><a href="/missing">broken</a></body></html>'
            self.send_response(200)
            self.send_header("Content-Type", "text/html")
            self.end_headers()
            self.wfile.write(body)

        def log_message(self, *_args: object) -> None:
            return

    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    thread = Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        project = tmp_path / "project"
        state.init_state("general", "Test", f"http://127.0.0.1:{server.server_port}", project_dir=project)
        report, snapshot_path = run_tech_audit(project, CrawlConfig(max_urls=10, concurrency=2, retries=0, allow_private=True))
        assert report["collection_status"] == "ok"
        assert report["summary"]["pages"] == 2
        assert report["summary"]["issues"] >= 2
        assert report["new_high_impact"]
        assert all("evidence" not in issue for issue in report["new_high_impact"])
        assert snapshot_path.is_file()
        assert (project / "audits/tech-audit/latest.json").is_file()
        assert (project / report["artifacts"]["inventory_path"]).is_file()
        assert (project / report["artifacts"]["summary_path"]).is_file()
        assert (project / report["artifacts"]["link_inventory_path"]).is_file()
        assert (project / report["artifacts"]["issues_path"]).is_file()
        assert (project / report["artifacts"]["action_groups_path"]).is_file()
        assert report["summary"]["issue_actions"] <= report["summary"]["issues"]
        rows = [json.loads(line) for line in (project / report["artifacts"]["issues_path"]).read_text().splitlines()]
        assert any(row["rule_id"] == "BROKEN_INTERNAL_LINK" for row in rows)
        legacy_query = TechAuditViewQuery("issues", "", (), "", "", "HTTP_4XX", "status", "high")
        assert legacy_query.category == "status"
        assert legacy_query.severity == "high"
        assert legacy_query.template == ""
        pages_view = query_tech_audit(project, TechAuditViewQuery(dataset="pages", status_codes=(404,), limit=1))
        links_view = query_tech_audit(project, TechAuditViewQuery(dataset="links", limit=10))
        issues_view = query_tech_audit(project, TechAuditViewQuery(dataset="issues", rule_id="HTTP_4XX", template="missing", sort="priority", direction="desc"))
        assert pages_view.total == 1
        assert pages_view.rows[0]["status_code"] == 404
        assert links_view.total >= 1
        assert issues_view.total >= 1
        assert all(row["template"] == "missing" for row in issues_view.rows)
        recrawl, recrawl_path = recrawl_urls(project, [f"http://127.0.0.1:{server.server_port}/missing"], CrawlConfig(max_urls=1, retries=0, allow_private=True))
        assert recrawl["summary"]["still_404"] == 1
        assert recrawl_path.is_file()
        assert (project / "audits/tech-audit/latest-recrawl.json").is_file()
        recovered, _ = recrawl_urls(project, [f"http://127.0.0.1:{server.server_port}/"], CrawlConfig(max_urls=1, retries=0, allow_private=True))
        assert recovered["summary"]["successful_pages"] == 1
        assert main(["--project-dir", str(project), "tech-audit", "run", "--allow-private", "--max-urls", "10", "--retries", "0", "--json"]) == 0
        cli_report = json.loads(capsys.readouterr().out)
        assert cli_report["ok"] is True
        assert main(["--project-dir", str(project), "tech-audit", "diff", "--json"]) == 0
        diff = json.loads(capsys.readouterr().out)
        assert diff["ok"] is True
        assert diff["comparisons"]["tech-audit"]["status"] == "ok"
    finally:
        server.shutdown()
        thread.join(timeout=5)
