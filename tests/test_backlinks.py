import json
from datetime import datetime, timezone
from pathlib import Path

import pytest

from seo_workbench import state
from seo_workbench import backlinks as backlinks_module
from seo_workbench.backlinks import (
    BacklinkViewQuery,
    backlink_status,
    collect_dataforseo_backlinks,
    collect_dataforseo_gap,
    import_backlink_snapshot,
    query_backlink_workspace,
)
from seo_workbench.cli import main


LINK_A = {"source_url": "https://publisher.example/a", "target_url": "https://example.com/guides/a", "anchor": "Guide A", "follow": True}
LINK_B = {"source_url": "https://news.example/b", "target_url": "https://example.com/guides/b", "anchor": "Guide B", "rel": "nofollow"}
LINK_C = {"source_url": "https://blog.example.net/c", "target_url": "https://example.com/guides/c", "anchor": "Guide C"}


def _project(path: Path) -> Path:
    state.init_state("shopify", "Example", "https://example.com", project_dir=path)
    return path


def _json(path: Path, rows: list[dict]) -> Path:
    path.write_text(json.dumps({"rows": rows}))
    return path


def test_backlink_snapshot_keeps_provenance_without_invented_scores(tmp_path: Path) -> None:
    project_dir = _project(tmp_path / "project")
    report, path = import_backlink_snapshot(
        project_dir,
        _json(tmp_path / "links.json", [LINK_A, LINK_B]),
        source="Semrush export",
        captured_at="2026-08-01T00:00:00Z",
        now=datetime(2026, 8, 1, tzinfo=timezone.utc),
    )

    assert report["summary"]["active_links"] == 2
    assert report["summary"]["referring_domains"] == 2
    assert report["summary"]["follow"] == {"follow": 1, "nofollow": 1}
    assert report["comparison"]["status"] == "no_baseline"
    assert report["claims"]["authority_score"] == "not_calculated"
    assert path.stat().st_mode & 0o777 == 0o600
    assert (project_dir / "audits/backlinks-report.md").is_file()
    assert backlink_status(project_dir, source="Semrush export")["summary"]["active_links"] == 2


def test_complete_same_source_snapshots_confirm_new_and_lost_links(tmp_path: Path) -> None:
    project_dir = _project(tmp_path / "project")
    import_backlink_snapshot(
        project_dir,
        _json(tmp_path / "before.json", [LINK_A, LINK_B]),
        source="provider",
        complete=True,
        now=datetime(2026, 8, 1, tzinfo=timezone.utc),
    )
    report, _ = import_backlink_snapshot(
        project_dir,
        _json(tmp_path / "after.json", [LINK_A, LINK_C]),
        source="provider",
        complete=True,
        now=datetime(2026, 9, 1, tzinfo=timezone.utc),
    )

    comparison = report["comparison"]
    assert comparison["comparable"] is True
    assert [link["source_url"] for link in comparison["new_observed"]] == [LINK_C["source_url"]]
    assert [link["source_url"] for link in comparison["lost"]] == [LINK_B["source_url"]]
    assert comparison["missing_unconfirmed"] == []
    assert (project_dir / "audits/backlinks-recheck.md").is_file()


def test_partial_snapshot_does_not_claim_absent_links_are_lost(tmp_path: Path) -> None:
    project_dir = _project(tmp_path / "project")
    import_backlink_snapshot(
        project_dir,
        _json(tmp_path / "before.json", [LINK_A, LINK_B]),
        source="provider",
        complete=True,
        now=datetime(2026, 8, 1, tzinfo=timezone.utc),
    )
    report, _ = import_backlink_snapshot(
        project_dir,
        _json(tmp_path / "partial.json", [LINK_A]),
        source="provider",
        complete=False,
        now=datetime(2026, 9, 1, tzinfo=timezone.utc),
    )

    assert report["comparison"]["lost"] == []
    assert [link["source_url"] for link in report["comparison"]["missing_unconfirmed"]] == [LINK_B["source_url"]]


def test_backlink_workspace_filters_and_paginates_latest_snapshot(tmp_path: Path) -> None:
    project_dir = _project(tmp_path / "project")
    import_backlink_snapshot(
        project_dir,
        _json(tmp_path / "links.json", [LINK_A, LINK_B, LINK_C]),
        source="provider",
        now=datetime(2026, 8, 1, tzinfo=timezone.utc),
    )

    view = query_backlink_workspace(
        project_dir,
        BacklinkViewQuery(query="blog.example", follow="unknown", limit=1),
    )

    assert view["pagination"] == {"offset": 0, "limit": 1, "total": 1}
    assert view["rows"][0]["source_domain"] == "blog.example.net"
    assert view["rows"][0]["provider_status"] == "active"


def test_backlink_snapshot_marks_404_targets_from_technical_evidence(tmp_path: Path, monkeypatch) -> None:
    project_dir = _project(tmp_path / "project")
    monkeypatch.setattr(backlinks_module, "load_tech_inventory", lambda _: [{"url": LINK_A["target_url"], "status_code": 404}])
    report, _ = import_backlink_snapshot(project_dir, _json(tmp_path / "links.json", [LINK_A]), source="manual")
    assert report["summary"]["target_reclaim_candidates"] == 1
    assert report["links"][0]["target_reclaim_candidate"] is True


def test_backlinks_cli_and_site_boundary_validation(tmp_path: Path, capsys) -> None:
    project_dir = _project(tmp_path / "project")
    source = _json(tmp_path / "links.json", [LINK_A])
    assert main(["--project-dir", str(project_dir), "backlinks", "import", "--from-file", str(source), "--source", "manual", "--json"]) == 0
    assert json.loads(capsys.readouterr().out)["ok"] is True
    assert main(["--project-dir", str(project_dir), "backlinks", "status", "--source", "manual", "--json"]) == 0
    assert json.loads(capsys.readouterr().out)["summary"]["active_links"] == 1

    with pytest.raises(ValueError, match="source URL must be external"):
        import_backlink_snapshot(
            project_dir,
            _json(tmp_path / "invalid.json", [{**LINK_A, "source_url": "https://example.com/internal"}]),
            source="manual",
        )


def test_dataforseo_backlink_collection_requires_confirmation_and_marks_truncation(tmp_path: Path) -> None:
    project_dir = _project(tmp_path / "project")
    calls: list[dict] = []
    provider_links = [
        {"url_from": LINK_A["source_url"], "url_to": LINK_A["target_url"], "anchor": "Guide A", "dofollow": True},
        {"url_from": LINK_B["source_url"], "url_to": LINK_B["target_url"], "anchor": "Guide B", "dofollow": False},
    ]

    def requester(_project_dir: Path, endpoint: str, task: dict, _timeout: float) -> dict:
        calls.append(task)
        item = provider_links[task["offset"]]
        return {
            "status_code": 20000,
            "tasks": [{"id": f"task-{len(calls)}", "status_code": 20000, "cost": 0.01, "result": [{"total_count": 2, "items": [item]}]}],
        }

    with pytest.raises(ValueError, match="confirm-paid"):
        collect_dataforseo_backlinks(project_dir, confirm_paid=False, requester=requester)
    assert calls == []

    def missing_total(_project_dir: Path, _endpoint: str, _task: dict, _timeout: float) -> dict:
        return {"status_code": 20000, "tasks": [{"result": [{"items": []}]}]}

    with pytest.raises(ValueError, match="total_count"):
        collect_dataforseo_backlinks(project_dir, confirm_paid=True, requester=missing_total)

    report, path = collect_dataforseo_backlinks(
        project_dir,
        confirm_paid=True,
        max_links=2,
        requester=requester,
        now=datetime(2026, 8, 20, tzinfo=timezone.utc),
    )

    assert [task["offset"] for task in calls] == [0, 1]
    assert report["complete_snapshot"] is True
    assert report["provider"]["cost_usd"] == 0.02
    assert report["claims"]["authority_score"] == "not_calculated"
    assert path.is_file()

    partial_project = _project(tmp_path / "partial")
    partial, _ = collect_dataforseo_backlinks(
        partial_project,
        confirm_paid=True,
        max_links=1,
        requester=requester,
        now=datetime(2026, 8, 21, tzinfo=timezone.utc),
    )
    assert partial["complete_snapshot"] is False
    assert partial["provider"]["truncated"] is True


def test_dataforseo_gap_writes_provider_evidence_and_exact_target_mapping(tmp_path: Path) -> None:
    project_dir = _project(tmp_path / "project")
    portfolio = project_dir / "audits/content-portfolio/latest.json"
    portfolio.parent.mkdir(parents=True)
    portfolio.write_text(json.dumps({"items": [{"url": LINK_A["target_url"]}]}), encoding="utf-8")
    pool = project_dir / "strategy/keyword-pool.jsonl"
    pool.parent.mkdir(parents=True, exist_ok=True)
    pool.write_text(json.dumps({"keyword": "Guide A", "target_url": "/guides/a"}) + "\n", encoding="utf-8")

    def requester(_project_dir: Path, endpoint: str, task: dict, _timeout: float) -> dict:
        assert endpoint.endswith("/page_intersection/live")
        assert task["exclude_targets"] == ["example.com"]
        assert task["intersection_mode"] == "partial"
        return {
            "status_code": 20000,
            "tasks": [
                {
                    "id": "gap-task",
                    "status_code": 20000,
                    "cost": 0.02,
                    "result": [
                        {
                            "total_count": 1,
                            "items": [
                                {
                                    "page_intersection": {
                                        "1": [{"url_from": "https://publisher.example/list", "url_to": "https://competitor-a.example/guide", "anchor": "Guide A", "dofollow": True}],
                                        "2": [{"url_from": "https://publisher.example/list", "url_to": "https://competitor-b.example/guide", "anchor": "Read more", "dofollow": False}],
                                    },
                                    "summary": {"intersections_count": 2},
                                }
                            ],
                        }
                    ],
                }
            ],
        }

    report, path = collect_dataforseo_gap(
        project_dir,
        ["competitor-a.example", "https://www.competitor-b.example/"],
        confirm_paid=True,
        requester=requester,
        now=datetime(2026, 8, 20, tzinfo=timezone.utc),
    )

    assert report["collection_status"] == "complete"
    assert report["items"][0]["suggested_target_url"] == LINK_A["target_url"]
    assert report["items"][0]["mapping_status"] == "mapped"
    assert report["claims"]["toxicity_score"] == "not_calculated"
    assert path.is_file()
    assert path.with_suffix(".md").is_file()
    assert "No authority, toxicity, outreach, or disavow judgment" in path.with_suffix(".md").read_text(encoding="utf-8")


def test_dataforseo_cli_reports_missing_credentials_without_calling_provider(tmp_path: Path, capsys) -> None:
    project_dir = _project(tmp_path / "project")

    assert main(["--project-dir", str(project_dir), "backlinks", "collect", "--confirm-paid", "--json"]) == 1

    payload = json.loads(capsys.readouterr().out)
    assert payload["collection_status"] == "needs_credentials"
