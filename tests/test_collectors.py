from seo_workbench_tools import page_probe, robots_sitemap_probe
from seo_workbench_tools.evidence_bundle import collect
from seo_workbench_tools.headless import build_headless_audit


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
