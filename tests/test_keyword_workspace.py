from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

import pytest

from seo_workbench import state
from seo_workbench.keyword_workspace import (
    KeywordWorkspaceQuery,
    keyword_handoff,
    query_keyword_workspace,
    update_keywords,
)


def project(tmp_path: Path) -> Path:
    project_dir = tmp_path / "store"
    state.init_state("shopify", "Store", "https://example.com", project_dir=project_dir)
    (project_dir / "strategy").mkdir(exist_ok=True)
    (project_dir / "strategy/keyword-pool.jsonl").write_text(
        json.dumps(
            {
                "keyword": "desk shelf",
                "source": "semrush_manual",
                "priority_score": 72,
                "intent": "commercial",
                "cluster_ref": ["desk-shelf-cluster"],
                "source_record": {"system": "feishu", "record_id": "record-1"},
                "unknown_field": "keep me",
            }
        )
        + "\n",
        encoding="utf-8",
    )
    (project_dir / "content").mkdir(exist_ok=True)
    (project_dir / "content/blog-pipeline.jsonl").write_text(
        json.dumps({"id": "desk-shelf-cluster", "cluster_name": "Desk shelf", "status": "planned"}) + "\n",
        encoding="utf-8",
    )
    data = state.load_state(project_dir)
    data["contentQueue"] = [
        {"id": "article-1", "title": "Cable guide", "status": "drafted", "target_keyword": "cable management"}
    ]
    (project_dir / "state.json").write_text(json.dumps(data), encoding="utf-8")
    gsc = {
        "collection_status": "ok",
        "generated_at": "2026-08-18T00:00:00Z",
        "windows": {
            "current": {
                "query": {
                    "rows": [
                        {"keys": ["desk shelf"], "clicks": 4, "impressions": 100, "ctr": 0.04, "position": 8},
                        {"keys": ["monitor riser"], "clicks": 2, "impressions": 80, "ctr": 0.025, "position": 11},
                    ]
                }
            }
        },
    }
    (project_dir / "audits/gsc/search-analytics").mkdir(parents=True, exist_ok=True)
    (project_dir / "audits/gsc/search-analytics/latest.json").write_text(json.dumps(gsc), encoding="utf-8")
    (project_dir / "audits/content-portfolio").mkdir(parents=True, exist_ok=True)
    (project_dir / "audits/content-portfolio/latest.json").write_text(
        json.dumps(
            {
                "collection_status": "ok",
                "generated_at": "2026-08-18T01:00:00Z",
                "items": [
                    {
                        "url": "https://example.com/products/desk-shelf",
                        "top_queries": [{"query": "desk shelf"}],
                    }
                ],
            }
        ),
        encoding="utf-8",
    )
    (project_dir / "audits/keywords/dataforseo").mkdir(parents=True, exist_ok=True)
    (project_dir / "audits/keywords/dataforseo/latest.json").write_text(
        json.dumps(
            {
                "collection_status": "complete",
                "generated_at": "2026-08-18T02:00:00Z",
                "items": [
                    {
                        "keyword": "desk shelf",
                        "provider": "dataforseo",
                        "search_volume": 3600,
                        "cpc": 0.7,
                        "competition": 0.62,
                        "intent": "commercial",
                    }
                ],
            }
        ),
        encoding="utf-8",
    )
    (project_dir / "strategy/keyword-dives").mkdir(exist_ok=True)
    (project_dir / "strategy/keyword-dives/product-desk-shelf.md").write_text(
        "# Keyword deep dive: desk shelf\n\nPrimary keyword: **desk shelf**\n",
        encoding="utf-8",
    )
    return project_dir


def test_projection_joins_sources_and_supports_historical_cluster_ref(tmp_path: Path) -> None:
    project_dir = project(tmp_path)
    view = query_keyword_workspace(project_dir, KeywordWorkspaceQuery(limit=100))
    rows = {row["keyword"]: row for row in view["rows"]}

    assert rows["desk shelf"]["cluster_ref"] == "desk-shelf-cluster"
    assert rows["desk shelf"]["research_path"].endswith("product-desk-shelf.md")
    assert rows["desk shelf"]["gsc"]["impressions"] == 100
    assert rows["desk shelf"]["market"]["search_volume"] == 3600
    assert view["sources"]["dataforseo"]["generated_at"] == "2026-08-18T02:00:00Z"
    assert rows["desk shelf"]["stage"] == "researched"
    assert rows["monitor riser"]["managed"] is False
    assert rows["monitor riser"]["stage"] == "needs_decision"
    assert rows["cable management"]["stage"] == "needs_decision"
    assert view["sources"]["gsc"]["generated_at"] == "2026-08-18T00:00:00Z"


def test_update_materializes_gsc_candidate_and_preserves_unknown_fields(tmp_path: Path) -> None:
    project_dir = project(tmp_path)
    view = query_keyword_workspace(project_dir, KeywordWorkspaceQuery(limit=100))
    result = update_keywords(
        project_dir,
        ["monitor riser", "desk shelf"],
        {"decision": "prioritize", "target_url": "/collections/monitor-stands"},
        view["revision"],
        now=datetime(2026, 8, 19, tzinfo=timezone.utc),
    )
    rows = [json.loads(line) for line in (project_dir / "strategy/keyword-pool.jsonl").read_text().splitlines()]

    assert result["updated"] == 2
    assert rows[0]["unknown_field"] == "keep me"
    assert rows[0]["source_record"]["record_id"] == "record-1"
    assert rows[1]["source"] == "gsc"
    assert rows[1]["decision"] == "prioritize"
    assert rows[1]["updated_at"] == "2026-08-19T00:00:00+00:00"
    refreshed = query_keyword_workspace(project_dir, KeywordWorkspaceQuery(query="monitor riser"))["rows"][0]
    assert refreshed["stage"] == "mapped"

def test_update_is_all_or_nothing_and_rejects_invalid_assignments(tmp_path: Path) -> None:
    project_dir = project(tmp_path)
    view = query_keyword_workspace(project_dir, KeywordWorkspaceQuery(limit=100))
    original = (project_dir / "strategy/keyword-pool.jsonl").read_text()

    with pytest.raises(ValueError, match="target_content_id"):
        update_keywords(
            project_dir,
            ["desk shelf", "monitor riser"],
            {"decision": "prioritize", "target_content_id": "missing"},
            view["revision"],
        )
    assert (project_dir / "strategy/keyword-pool.jsonl").read_text() == original

    with pytest.raises(ValueError, match="same-domain"):
        update_keywords(project_dir, ["desk shelf"], {"target_url": "https://other.test/page"}, view["revision"])
    assert (project_dir / "strategy/keyword-pool.jsonl").read_text() == original


def test_revision_conflict_does_not_overwrite_concurrent_edit(tmp_path: Path) -> None:
    project_dir = project(tmp_path)
    view = query_keyword_workspace(project_dir, KeywordWorkspaceQuery(limit=100))
    path = project_dir / "strategy/keyword-pool.jsonl"
    path.write_text(path.read_text() + json.dumps({"keyword": "new agent row", "source": "manual"}) + "\n")

    with pytest.raises(RuntimeError):
        update_keywords(project_dir, ["desk shelf"], {"decision": "drop"}, view["revision"])
    assert "new agent row" in path.read_text()


def test_stage_progression_and_handoff_paths(tmp_path: Path) -> None:
    project_dir = project(tmp_path)
    view = query_keyword_workspace(project_dir, KeywordWorkspaceQuery(limit=100))
    updated = update_keywords(
        project_dir,
        ["cable management"],
        {"target_content_id": "article-1"},
        view["revision"],
    )
    rows = query_keyword_workspace(project_dir, KeywordWorkspaceQuery(limit=100))["rows"]
    cable = next(row for row in rows if row["keyword"] == "cable management")
    assert cable["stage"] == "handed_off"
    assert cable["content"]["status"] == "drafted"

    existing = keyword_handoff(project_dir, "desk shelf")
    assert existing["existing_path"].endswith("product-desk-shelf.md")
    handoff = keyword_handoff(project_dir, "cable management")
    assert handoff["output_path"].endswith("info-cable-management.md")
    assert "skills/keyword-deep-dive/SKILL.md" in handoff["prompt"]
    assert updated["revision"]


def test_cluster_aggregates_raw_query_evidence_and_measured_stage(tmp_path: Path) -> None:
    project_dir = project(tmp_path)
    pool_path = project_dir / "strategy/keyword-pool.jsonl"
    rows = [json.loads(line) for line in pool_path.read_text(encoding="utf-8").splitlines()]
    rows[0]["target_url"] = "/products/desk-shelf"
    rows.append(
        {
            "keyword": "desk shelf for standing desk",
            "source": "gsc",
            "cluster_ref": "desk-shelf-cluster",
            "target_url": "/products/desk-shelf",
        }
    )
    pool_path.write_text("".join(json.dumps(row) + "\n" for row in rows), encoding="utf-8")

    gsc_path = project_dir / "audits/gsc/search-analytics/latest.json"
    gsc = json.loads(gsc_path.read_text(encoding="utf-8"))
    gsc["windows"]["current"]["query"]["rows"] = [
        {"keys": ["Desk Shelf"], "clicks": 4, "impressions": 100, "ctr": 0.04, "position": 8},
        {"keys": ["Desk Shelf for Standing Desk"], "clicks": 2, "impressions": 40, "ctr": 0.05, "position": 10},
    ]
    gsc_path.write_text(json.dumps(gsc), encoding="utf-8")

    portfolio_path = project_dir / "audits/content-portfolio/latest.json"
    portfolio = json.loads(portfolio_path.read_text(encoding="utf-8"))
    portfolio["items"][0]["top_queries"].append({"query": "Desk Shelf for Standing Desk"})
    portfolio_path.write_text(json.dumps(portfolio), encoding="utf-8")

    view = query_keyword_workspace(project_dir, KeywordWorkspaceQuery(limit=100))
    desk_shelf = next(row for row in view["rows"] if row["keyword"] == "desk shelf")
    assert desk_shelf["gsc"]["query"] == "Desk Shelf"
    assert desk_shelf["cluster_gsc"] == {
        "clicks": 6.0,
        "impressions": 140.0,
        "ctr": pytest.approx(6 / 140),
        "position": pytest.approx((8 * 100 + 10 * 40) / 140),
    }
    assert [item["query"] for item in desk_shelf["observed_queries"]] == [
        "Desk Shelf",
        "Desk Shelf for Standing Desk",
    ]
    assert desk_shelf["stage"] == "researched"
    assert next(row for row in view["rows"] if row["keyword"] == "desk shelf for standing desk")["stage"] == "mapped"

    topics = query_keyword_workspace(project_dir, KeywordWorkspaceQuery(dataset="topics", limit=100))["rows"]
    topic = next(row for row in topics if row["cluster_ref"] == "desk-shelf-cluster")
    assert topic["query_count"] == 2
    assert topic["impressions"] == 140
    assert topic["target_urls"] == ["/products/desk-shelf"]
    assert topic["target_conflict"] is False


def test_topic_map_keeps_one_cluster_row_and_flags_target_conflicts(tmp_path: Path) -> None:
    project_dir = project(tmp_path)
    pool_path = project_dir / "strategy/keyword-pool.jsonl"
    rows = [json.loads(line) for line in pool_path.read_text(encoding="utf-8").splitlines()]
    rows[0]["target_url"] = "/products/desk-shelf"
    rows.append(
        {
            "keyword": "desk shelf ideas",
            "source": "manual",
            "cluster_ref": "desk-shelf-cluster",
            "target_url": "/blogs/desk-shelf-ideas",
        }
    )
    pool_path.write_text("".join(json.dumps(row) + "\n" for row in rows), encoding="utf-8")

    topics = query_keyword_workspace(project_dir, KeywordWorkspaceQuery(dataset="topics", limit=100))["rows"]
    matches = [row for row in topics if row["cluster_ref"] == "desk-shelf-cluster"]
    assert len(matches) == 1
    assert matches[0]["target_urls"] == ["/blogs/desk-shelf-ideas", "/products/desk-shelf"]
    assert matches[0]["target_conflict"] is True


def test_topic_map_sorts_missing_query_evidence_last_without_coercing_to_zero(tmp_path: Path) -> None:
    project_dir = project(tmp_path)
    pool_path = project_dir / "strategy/keyword-pool.jsonl"
    rows = [json.loads(line) for line in pool_path.read_text(encoding="utf-8").splitlines()]
    rows.append({"keyword": "unobserved topic", "source": "manual", "cluster_ref": "unobserved-cluster"})
    pool_path.write_text("".join(json.dumps(row) + "\n" for row in rows), encoding="utf-8")

    topics = query_keyword_workspace(
        project_dir,
        KeywordWorkspaceQuery(dataset="topics", sort="impressions", direction="desc", limit=100),
    )["rows"]
    unobserved = next(row for row in topics if row["cluster_ref"] == "unobserved-cluster")
    assert unobserved["impressions"] is None
    assert topics[-1] == unobserved


def test_queue_scope_holds_only_rows_needing_operator_judgment(tmp_path: Path) -> None:
    project_dir = project(tmp_path)
    pool_path = project_dir / "strategy/keyword-pool.jsonl"
    rows = [json.loads(line) for line in pool_path.read_text(encoding="utf-8").splitlines()]
    rows.append({"keyword": "held term", "source": "manual", "decision": "hold"})
    rows.append({"keyword": "cable management", "source": "gsc", "decision": "prioritize"})
    rows.append({"keyword": "long tail seed", "source": "manual", "decision": "drop"})
    pool_path.write_text("".join(json.dumps(row) + "\n" for row in rows), encoding="utf-8")
    gsc = json.loads((project_dir / "audits/gsc/search-analytics/latest.json").read_text(encoding="utf-8"))
    gsc["windows"]["current"]["query"]["rows"] = [
        {"keys": ["desk shelf"], "clicks": 4, "impressions": 100, "ctr": 0.04, "position": 8},
        {"keys": ["monitor riser"], "clicks": 2, "impressions": 6000, "ctr": 0.025, "position": 11},
    ]
    (project_dir / "audits/gsc/search-analytics/latest.json").write_text(json.dumps(gsc), encoding="utf-8")

    queue = query_keyword_workspace(project_dir, KeywordWorkspaceQuery(scope="queue", limit=100))["rows"]
    queue_keywords = {row["keyword"] for row in queue}
    assert "desk shelf" in queue_keywords  # managed seed, unreviewed
    assert "cable management" in queue_keywords  # prioritized
    assert "monitor riser" in queue_keywords  # high-demand unreviewed
    assert "held term" not in queue_keywords  # decided
    assert "long tail seed" not in queue_keywords  # dropped

    pool = query_keyword_workspace(project_dir, KeywordWorkspaceQuery(scope="map", limit=100))["rows"]
    assert {row["keyword"] for row in pool} == {"held term", "long tail seed"}


def test_queue_includes_unreviewed_conflict_rows_regardless_of_score(tmp_path: Path) -> None:
    project_dir = project(tmp_path)
    portfolio = json.loads((project_dir / "audits/content-portfolio/latest.json").read_text(encoding="utf-8"))
    portfolio["items"].append(
        {"url": "https://example.com/blogs/second-page", "top_queries": [{"query": "monitor riser"}]}
    )
    portfolio["items"].append(
        {"url": "https://example.com/products/riser", "top_queries": [{"query": "Monitor Riser"}]}
    )
    (project_dir / "audits/content-portfolio/latest.json").write_text(json.dumps(portfolio), encoding="utf-8")

    queue = query_keyword_workspace(project_dir, KeywordWorkspaceQuery(scope="queue", limit=100))["rows"]
    conflict = next(row for row in queue if row["keyword"] == "monitor riser")
    assert conflict["mapping_conflict"] is True
    assert conflict["stage"] == "needs_decision"
    summary = query_keyword_workspace(project_dir, KeywordWorkspaceQuery(limit=100))["summary"]
    assert summary["queue"] == len(queue)
    assert summary["queue_stages"].get("needs_decision", 0) >= 1


def test_stage_filter_accepts_comma_list_and_scope_complements(tmp_path: Path) -> None:
    project_dir = project(tmp_path)
    both = query_keyword_workspace(
        project_dir,
        KeywordWorkspaceQuery(scope="queue", stage="mapped,demand_check", limit=100),
    )["rows"]
    assert {row["keyword"] for row in both} == set()

    view = query_keyword_workspace(project_dir, KeywordWorkspaceQuery(limit=100))
    assert view["summary"]["queue"] > 0
    assert view["summary"]["queue"] + view["summary"]["total"] >= view["summary"]["total"]
    assert "queue_stages" in view["summary"]
