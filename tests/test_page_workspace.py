from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path

from seo_workbench import state
from seo_workbench.page_workspace import PageWorkspaceQuery, page_workspace_detail, query_page_workspace
from seo_workbench.seo_changes import record_change
from seo_workbench.tech_issues import sync_issue_register, update_issue_status


NOW = datetime(2026, 8, 9, 8, 0, tzinfo=timezone.utc)
PAGE = "https://example.com/products/desk"
ARTICLE = "https://example.com/blogs/articles/guide"


def _project(tmp_path: Path) -> Path:
    project_dir = tmp_path / "project"
    state.init_state("shopify", "Example", "https://example.com", project_dir=project_dir)
    data = state.load_state(project_dir)
    data["contentQueue"] = [
        {"id": "content-1", "status": "indexing_issue", "title": "Guide", "live_url": ARTICLE}
    ]
    state.save_state(data, project_dir)
    portfolio = {
        "schema_version": "content-portfolio-v4",
        "collection_status": "ok",
        "generated_at": NOW.isoformat(),
        "statistics": {"commercial_value": {"observed_pages": 1, "revenue_hhi": 1.0}},
        "source_status": {
            "gsc": {"status": "ok", "generated_at": NOW.isoformat()},
            "technical": {"status": "not_collected", "generated_at": None},
        },
        "items": [
            {
                "row_key": PAGE,
                "title": "Desk",
                "url": PAGE,
                "page_type": "product",
                "status": "observed",
                "sources": {"gsc_current": True, "gsc_previous": True, "technical": True, "content": False},
                "decision": "refresh",
                "recommendation": "Refresh intent coverage.",
                "metrics": {"current": {"clicks": 5, "impressions": 200, "ctr": 0.025, "position": 8}},
                "statistics": {
                    "click_change_decomposition": {"observed_click_change": -2, "exposure_effect": 1, "ctr_effect": -3},
                    "query_portfolio": {"current": {"effective_queries": 3.2}},
                    "ranking_opportunity": {"positions_4_20_impressions": 175},
                    "commercial_value": {"quadrant": "grow", "revenue_share": 1.0},
                    "ctr_benchmark": {"recoverable_clicks": 12.5, "classification": "below_expected"},
                    "search_change_confidence": {"status": "ok", "evidence_grade": "strong"},
                    "search_trend": {"status": "ok", "direction": "down"},
                    "cross_source_consistency": {"status": "possible_measurement_break"},
                },
                "technical": {"issue_count": 1},
                "multiple_page_queries": [
                    {
                        "query": "desk setup",
                        "owner_count": 2,
                        "total_impressions": 150,
                        "ownership": {"hhi": 0.555556, "primary_owner_share": 0.666667, "effective_owners": 1.8},
                        "owners": [{"url": PAGE, "impressions": 100}, {"url": ARTICLE, "impressions": 50}],
                    }
                ],
            },
            {
                "row_key": ARTICLE,
                "id": "content-1",
                "title": "Guide",
                "url": ARTICLE,
                "page_type": "article",
                "status": "indexing_issue",
                "sources": {"gsc_current": False, "gsc_previous": False, "technical": True, "content": True},
                "decision": "wait_for_data",
                "recommendation": "Collect more evidence.",
                "metrics": {"current": None},
                "technical": {"issue_count": 0},
                "multiple_page_queries": [],
            },
        ],
    }
    path = project_dir / "audits/content-portfolio/latest.json"
    path.parent.mkdir(parents=True)
    path.write_text(json.dumps(portfolio))
    gsc = project_dir / "audits/gsc/search-analytics/latest.json"
    gsc.parent.mkdir(parents=True, exist_ok=True)
    gsc.write_text(json.dumps({"collection_status": "ok", "generated_at": NOW.isoformat()}))
    issue = {
        "fingerprint": "fp-1",
        "rule_id": "MISSING_H1",
        "title": "Missing H1",
        "severity": "high",
        "category": "content",
        "url": PAGE,
        "priority": {"score": 70, "tier": "high"},
        "remediation_guidance": "Add an H1.",
    }
    sync_issue_register(project_dir, [issue], [], run_id="run-1", verification_allowed=False, now=NOW)
    update_issue_status(project_dir, "fp-1", "fixed", note="Patched", now=NOW)
    record_change(
        project_dir,
        urls=[PAGE],
        change_type="content",
        hypothesis="Better copy improves clicks.",
        metrics=["clicks"],
        changed_at="2026-07-01",
        review_date="2026-07-29",
        now=NOW,
    )
    return project_dir


def test_page_workspace_groups_live_domain_tasks_without_new_task_state(tmp_path: Path) -> None:
    project_dir = _project(tmp_path)

    actions = query_page_workspace(project_dir, PageWorkspaceQuery(dataset="actions", group="review"))

    assert actions["summary"]["groups"] == {"now": 2, "review": 2, "watch": 1}
    assert {row["source"] for row in actions["rows"]} == {"technical", "change"}
    assert not (project_dir / "strategy/tasks.jsonl").exists()


def test_page_workspace_groups_technical_actions_by_rule_and_template(tmp_path: Path) -> None:
    project_dir = _project(tmp_path)
    issue = {
        "fingerprint": "fp-2",
        "rule_id": "MISSING_H1",
        "title": "Missing H1",
        "severity": "high",
        "category": "content",
        "url": "https://example.com/products/chair",
        "template": "product",
        "priority": {"score": 65, "tier": "high"},
        "remediation_guidance": "Add an H1.",
    }
    sync_issue_register(project_dir, [issue], [], run_id="run-2", verification_allowed=False, now=NOW)
    update_issue_status(project_dir, "fp-2", "fixed", note="Patched", now=NOW)

    actions = query_page_workspace(project_dir, PageWorkspaceQuery(dataset="actions", group="review", source="technical"))

    assert actions["pagination"]["total"] == 1
    assert actions["rows"][0]["issue_count"] == 2
    assert actions["rows"][0]["template"] == "product"
    assert actions["rows"][0]["read_only"] is True
    assert actions["rows"][0]["source_id"] == ""
    assert actions["rows"][0]["url"] == ""
    assert actions["rows"][0]["target_view"] == "#/audits/url-inventory?dataset=issues&rule_id=MISSING_H1&template=product"


def test_page_workspace_filters_and_paginates_page_and_query_views(tmp_path: Path) -> None:
    project_dir = _project(tmp_path)

    pages = query_page_workspace(
        project_dir,
        PageWorkspaceQuery(dataset="pages", page_type="product", source="technical", sort="impressions", direction="desc", limit=1),
    )
    conflicts = query_page_workspace(
        project_dir,
        PageWorkspaceQuery(dataset="query_conflicts", query="desk", sort="total_impressions", direction="desc"),
    )
    sorted_pages = query_page_workspace(
        project_dir,
        PageWorkspaceQuery(dataset="pages", sort="impressions", direction="desc"),
    )

    assert pages["pagination"] == {"offset": 0, "limit": 1, "total": 1}
    assert pages["rows"][0]["clicks"] == 5
    assert pages["rows"][0]["opportunity_impressions"] == 175
    assert pages["rows"][0]["commercial_quadrant"] == "grow"
    assert pages["rows"][0]["click_driver"] == "ctr"
    assert pages["rows"][0]["recoverable_clicks"] == 12.5
    assert pages["rows"][0]["evidence_strength"] == "strong"
    assert pages["rows"][0]["trend"] == "down"
    assert pages["rows"][0]["cross_source_status"] == "possible_measurement_break"
    assert pages["summary"]["statistics"]["commercial_value"]["revenue_hhi"] == 1.0
    assert [row["url"] for row in sorted_pages["rows"]] == [PAGE, ARTICLE]
    assert conflicts["rows"][0]["owner_count"] == 2
    assert conflicts["rows"][0]["primary_owner_share"] == 0.666667
    assert conflicts["rows"][0]["ownership_hhi"] == 0.555556
    assert conflicts["rows"][0]["leading_url"] == PAGE


def test_page_workspace_detail_includes_related_page_and_source_health(tmp_path: Path) -> None:
    project_dir = _project(tmp_path)
    portfolio_modified = (project_dir / "audits/content-portfolio/latest.json").stat().st_mtime_ns
    gsc_path = project_dir / "audits/gsc/search-analytics/latest.json"
    os.utime(gsc_path, ns=(portfolio_modified + 1_000_000, portfolio_modified + 1_000_000))

    detail = page_workspace_detail(project_dir, "actions", f"portfolio:{PAGE}")

    assert detail["row"]["status"] == "refresh"
    assert detail["page"]["row_key"] == PAGE
    assert detail["sources"]["gsc"]["status"] == "ok"
    assert detail["sources"]["technical"]["status"] == "not_collected"
    assert detail["sources"]["portfolio"]["status"] == "needs_refresh"
    assert detail["sources"]["portfolio"]["refresh_reasons"] == ["gsc evidence is newer than the page analysis"]

    technical = page_workspace_detail(project_dir, "actions", "technical:fp-1")
    assert technical["source_record"]["status"] == "fixed"


def test_page_workspace_detail_suggests_only_unlinked_mapped_pages(tmp_path: Path) -> None:
    project_dir = _project(tmp_path)
    portfolio_path = project_dir / "audits/content-portfolio/latest.json"
    portfolio = json.loads(portfolio_path.read_text(encoding="utf-8"))
    for item in portfolio["items"]:
        item["technical"].update(
            {
                "status_code": 200,
                "final_url": item["url"],
                "crawl_status": "ok",
                "indexability": {"status": "indexable", "indexable": True},
            }
        )
    portfolio["items"][0]["top_queries"] = [{"query": "standing desk"}]
    portfolio_path.write_text(json.dumps(portfolio), encoding="utf-8")
    (project_dir / "strategy/keyword-pool.jsonl").write_text(
        json.dumps({"keyword": "desk", "cluster_ref": "desk-cluster", "target_url": "/products/desk"})
        + "\n"
        + json.dumps({"keyword": "desk guide", "cluster_ref": "desk-cluster", "target_content_id": "content-1"})
        + "\n",
        encoding="utf-8",
    )
    run = project_dir / "audits/tech-audit/runs/run-1/normalized"
    run.mkdir(parents=True)
    inventory = run / "link-inventory.jsonl"
    inventory.write_text("", encoding="utf-8")
    latest = project_dir / "audits/tech-audit/latest.json"
    latest.parent.mkdir(parents=True, exist_ok=True)
    latest.write_text(
        json.dumps({"artifacts": {"link_inventory_path": "audits/tech-audit/runs/run-1/normalized/link-inventory.jsonl"}}),
        encoding="utf-8",
    )

    detail = page_workspace_detail(project_dir, "pages", PAGE)

    assert detail["internal_link_candidates"]["status"] == "ok"
    assert detail["internal_link_candidates"]["rows"] == [
        {
            "source_url": ARTICLE,
            "target_url": PAGE,
            "anchor_candidates": ["desk", "standing desk"],
            "already_linked": False,
            "cluster_ref": "desk-cluster",
            "reason": "Same mapped keyword cluster; both pages are indexable and no source-to-target link was observed.",
        }
    ]

    inventory.write_text(
        json.dumps(
            {
                "url": PAGE,
                "final_url": PAGE,
                "internal_external": "Internal",
                "sources": [ARTICLE],
            }
        )
        + "\n",
        encoding="utf-8",
    )
    linked = page_workspace_detail(project_dir, "pages", PAGE)
    assert linked["internal_link_candidates"]["status"] == "ok"
    assert linked["internal_link_candidates"]["rows"] == []

    portfolio["items"][1]["url"] = "https://example.com/de/blogs/articles/guide"
    portfolio["items"][1]["technical"]["final_url"] = portfolio["items"][1]["url"]
    portfolio_path.write_text(json.dumps(portfolio), encoding="utf-8")
    inventory.write_text("", encoding="utf-8")
    localized = page_workspace_detail(project_dir, "pages", PAGE)
    assert localized["internal_link_candidates"]["status"] == "insufficient_data"
    assert localized["internal_link_candidates"]["rows"] == []


def test_page_workspace_uses_due_date_after_action_urgency(tmp_path: Path) -> None:
    project_dir = _project(tmp_path)
    record_change(
        project_dir,
        urls=[PAGE],
        change_type="metadata",
        hypothesis="Later review.",
        metrics=["ctr"],
        changed_at="2026-08-02",
        review_date="2026-08-20",
        status="planned",
        now=NOW,
    )
    record_change(
        project_dir,
        urls=[ARTICLE],
        change_type="content",
        hypothesis="Earlier review.",
        metrics=["clicks"],
        changed_at="2026-08-03",
        review_date="2026-08-15",
        status="planned",
        now=NOW,
    )

    actions = query_page_workspace(
        project_dir,
        PageWorkspaceQuery(dataset="actions", group="now", source="change"),
    )

    assert [row["due_date"] for row in actions["rows"]] == ["2026-08-15", "2026-08-20"]


def test_page_workspace_does_not_link_external_task_urls(tmp_path: Path) -> None:
    project_dir = _project(tmp_path)
    data = state.load_state(project_dir)
    data["contentQueue"].append(
        {"id": "external", "status": "indexing_issue", "title": "External", "live_url": "https://external.example/page"}
    )
    state.save_state(data, project_dir)

    actions = query_page_workspace(
        project_dir,
        PageWorkspaceQuery(dataset="actions", source="content"),
    )

    external = next(row for row in actions["rows"] if row["source_id"] == "external")
    assert external["url"] == ""


def test_page_workspace_reads_v1_portfolio_as_content_evidence(tmp_path: Path) -> None:
    project_dir = tmp_path / "project"
    state.init_state("shopify", "Example", "https://example.com", project_dir=project_dir)
    path = project_dir / "audits/content-portfolio/latest.json"
    path.parent.mkdir(parents=True)
    path.write_text(
        json.dumps(
            {
                "schema_version": "content-portfolio-v1",
                "collection_status": "ok",
                "items": [{"id": "old", "title": "Old", "url": ARTICLE, "decision": "monitor", "metrics": {"current": None}}],
            }
        )
    )

    result = query_page_workspace(project_dir, PageWorkspaceQuery(dataset="pages", sort="url"))

    assert result["rows"][0]["sources"] == {"content": True}
    assert result["rows"][0]["page_type"] == "article"
