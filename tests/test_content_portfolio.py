import json
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

import pytest

from seo_workbench import state
from seo_workbench.cli import main
from seo_workbench.content_portfolio import analyze_content_portfolio
from seo_workbench.measurement_regimes import record_regime


DECAY = "https://example.com/blogs/articles/decay"
CONFLICT = "https://example.com/blogs/articles/conflict"
NEW = "https://example.com/blogs/articles/new"
TECH_ONLY = "https://example.com/products/technical-only"
BUSINESS_ONLY = "https://example.com/products/business-only"
EXTERNAL = "https://external.example/page"


def _project(path: Path) -> Path:
    state.init_state("shopify", "Example", "https://example.com", project_dir=path)
    items = [
        {"id": "decay", "status": "indexed", "title": "Decay", "live_url": DECAY, "scheduled_at": "2026-01-01T00:00:00Z"},
        {"id": "conflict", "status": "indexed", "title": "Conflict", "live_url": CONFLICT, "scheduled_at": "2026-01-01T00:00:00Z"},
        {"id": "new", "status": "indexed", "title": "New", "live_url": NEW, "scheduled_at": "2026-08-20T00:00:00Z"},
        {"id": "external", "status": "indexed", "title": "External", "live_url": EXTERNAL},
        {"id": "draft", "status": "drafting", "title": "Draft", "live_url": "https://example.com/draft"},
    ]
    data = state.load_state(path)
    data["contentQueue"] = items
    state.save_state(data, path)
    (path / "content/blog-pipeline.jsonl").write_text("\n".join(json.dumps(item) for item in items) + "\n")
    return path


def _gsc(path: Path) -> Path:
    def page(start: str, end: str, values: list[tuple[str, int, int, float]]) -> dict:
        return {
            "request": {"startDate": start, "endDate": end, "dimensions": ["page"]},
            "rows": [
                {"keys": [url], "clicks": clicks, "impressions": impressions, "ctr": clicks / impressions if impressions else 0, "position": position}
                for url, clicks, impressions, position in values
            ],
        }

    report = {
        "collection_status": "ok",
        "data_state": "final",
        "windows": {
            "previous": {
                "page": page(
                    "2026-07-04",
                    "2026-07-31",
                    [(DECAY, 20, 200, 6), (CONFLICT, 10, 200, 11), (NEW, 0, 0, 0)],
                )
            },
            "current": {
                "page": page(
                    "2026-08-02",
                    "2026-08-29",
                    [(DECAY, 5, 150, 9), (CONFLICT, 10, 200, 10), (NEW, 2, 50, 15)],
                ),
                "query_page": {
                    "rows": [
                        {"keys": ["desk cable guide", CONFLICT], "impressions": 80},
                        {"keys": ["desk cable guide", "https://example.com/pages/cable-guide"], "impressions": 40},
                        {"keys": ["desk cable guide", EXTERNAL], "impressions": 500},
                    ]
                },
            },
        },
    }
    path.write_text(json.dumps(report))
    return path


def _tech(project_dir: Path) -> None:
    run = project_dir / "audits/tech-audit/runs/run-1/normalized"
    run.mkdir(parents=True)
    inventory = [
        {"url": DECAY, "host_relation": "same_host", "status_code": 200, "title": "Technical decay"},
        {"url": TECH_ONLY, "host_relation": "same_host", "status_code": 200, "title": "Technical only"},
        {"url": "https://external.example/page", "host_relation": "external", "status_code": 200},
    ]
    (run / "inventory.jsonl").write_text("\n".join(json.dumps(item) for item in inventory) + "\n")
    (run / "issues.jsonl").write_text(json.dumps({"url": TECH_ONLY, "rule_id": "MISSING_H1"}) + "\n")
    latest = project_dir / "audits/tech-audit/latest.json"
    latest.parent.mkdir(parents=True, exist_ok=True)
    latest.write_text(
        json.dumps(
            {
                "collection_status": "ok",
                "artifacts": {
                    "inventory_path": "audits/tech-audit/runs/run-1/normalized/inventory.jsonl",
                    "issues_path": "audits/tech-audit/runs/run-1/normalized/issues.jsonl",
                },
            }
        )
    )


def test_content_portfolio_returns_actionable_non_mutating_decisions(tmp_path: Path) -> None:
    project_dir = _project(tmp_path / "project")
    report, path = analyze_content_portfolio(
        project_dir,
        gsc_path=_gsc(tmp_path / "gsc.json"),
        now=datetime(2026, 9, 1, tzinfo=timezone.utc),
    )

    decisions = {item["id"]: item["decision"] for item in report["items"]}
    assert decisions == {"decay": "refresh", "conflict": "consolidate_review", "new": "wait_for_data"}
    assert report["counts"] == {"consolidate_review": 1, "refresh": 1, "wait_for_data": 1}
    assert report["mutation_performed"] is False
    assert report["items"][1]["multiple_page_queries"][0]["query"] == "desk cable guide"
    assert report["items"][1]["multiple_page_queries"][0]["owner_count"] == 2
    assert report["schema_version"] == "content-portfolio-v4"
    assert report["statistics"]["click_change_decomposition"]["reconciled"] is True
    assert report["items"][1]["multiple_page_queries"][0]["ownership"]["primary_owner_share"] == 0.666667
    assert path.stat().st_mode & 0o777 == 0o600


def test_content_portfolio_rejects_truncated_gsc_statistics(tmp_path: Path) -> None:
    project_dir = _project(tmp_path / "project")
    gsc_path = _gsc(tmp_path / "gsc.json")
    report = json.loads(gsc_path.read_text())
    report["windows"]["current"]["query_page"]["truncated"] = True
    gsc_path.write_text(json.dumps(report))

    with pytest.raises(ValueError, match="query-page evidence is truncated"):
        analyze_content_portfolio(project_dir, gsc_path=gsc_path)


def test_content_portfolio_unifies_gsc_content_and_same_site_technical_pages(tmp_path: Path) -> None:
    project_dir = _project(tmp_path / "project")
    _tech(project_dir)

    report, _ = analyze_content_portfolio(
        project_dir,
        gsc_path=_gsc(tmp_path / "gsc.json"),
        now=datetime(2026, 9, 1, tzinfo=timezone.utc),
    )

    rows = {item["url"]: item for item in report["items"]}
    assert set(rows) == {DECAY, CONFLICT, NEW, TECH_ONLY}
    assert rows[DECAY]["sources"] == {
        "gsc_current": True,
        "gsc_previous": True,
        "technical": True,
        "content": True,
        "business": False,
    }
    assert rows[TECH_ONLY]["page_type"] == "product"
    assert rows[TECH_ONLY]["metrics"]["current"] is None
    assert rows[TECH_ONLY]["signals"] == ["gsc_not_observed"]
    assert rows[TECH_ONLY]["business_currency"] == ""
    assert rows[TECH_ONLY]["technical"]["issue_count"] == 1
    assert report["source_status"]["gsc"]["status"] == "ok"
    assert report["source_status"]["technical"]["status"] == "ok"


def test_content_portfolio_rejects_incomparable_business_windows(tmp_path: Path) -> None:
    project_dir = _project(tmp_path / "project")
    business = project_dir / "audits/business-signals/latest.json"
    business.parent.mkdir(parents=True)
    business.write_text(json.dumps({
        "collection_status": "ok",
        "windows": {
            name: {
                "request": {"startDate": start, "endDate": end},
                "rows": [{"url": DECAY, "organic_sessions": 99}],
            }
            for name, start, end in (
                ("previous", "2026-07-05", "2026-08-01"),
                ("current", "2026-08-03", "2026-08-30"),
            )
        },
    }))

    report, _ = analyze_content_portfolio(project_dir, gsc_path=_gsc(tmp_path / "gsc.json"))
    decay = next(item for item in report["items"] if item["url"] == DECAY)

    assert report["source_status"]["business"]["status"] == "incomparable"
    assert decay["sources"]["business"] is False
    assert "organic_sessions" not in decay["metrics"]["current"]


def test_content_portfolio_keeps_comparable_business_only_pages_as_unobserved_in_gsc(tmp_path: Path) -> None:
    project_dir = _project(tmp_path / "project")
    business = project_dir / "audits/business-signals/latest.json"
    business.parent.mkdir(parents=True)
    business.write_text(json.dumps({
        "collection_status": "ok",
        "currency": "USD",
        "windows": {
            name: {
                "request": {"startDate": start, "endDate": end},
                "rows": [{"url": BUSINESS_ONLY, "revenue": revenue}],
            }
            for name, start, end, revenue in (
                ("previous", "2026-07-04", "2026-07-31", 50),
                ("current", "2026-08-02", "2026-08-29", 80),
            )
        },
    }))

    report, _ = analyze_content_portfolio(project_dir, gsc_path=_gsc(tmp_path / "gsc.json"))
    row = next(item for item in report["items"] if item["url"] == BUSINESS_ONLY)

    assert row["sources"]["business"] is True
    assert row["sources"]["gsc_current"] is False
    assert row["signals"] == ["gsc_not_observed"]
    assert row["metrics"]["current"] == {"revenue": 80.0}
    assert row["statistics"]["commercial_value"]["quadrant"] == "protect"
    assert report["statistics"]["commercial_value"]["total_revenue"] == 80


def test_content_portfolio_excludes_sources_crossing_measurement_regimes(tmp_path: Path) -> None:
    project_dir = _project(tmp_path / "project")
    business = project_dir / "audits/business-signals/latest.json"
    business.parent.mkdir(parents=True)
    business.write_text(
        json.dumps(
            {
                "collection_status": "ok",
                "windows": {
                    name: {
                        "request": {"startDate": start, "endDate": end},
                        "rows": [{"url": DECAY, "organic_sessions": 99}],
                    }
                    for name, start, end in (
                        ("previous", "2026-07-04", "2026-07-31"),
                        ("current", "2026-08-02", "2026-08-29"),
                    )
                },
            }
        )
    )
    record_regime(
        project_dir,
        source="ga4",
        effective_at="2026-08-01",
        description="Changed key event definition",
    )
    record_regime(
        project_dir,
        source="gsc",
        effective_at="2026-08-01",
        description="Changed Search Console property",
    )

    report, _ = analyze_content_portfolio(project_dir, gsc_path=_gsc(tmp_path / "gsc.json"))
    decay = next(item for item in report["items"] if item["url"] == DECAY)

    assert report["comparability"]["comparable"] is False
    assert report["source_status"]["business"]["status"] == "incomparable"
    assert len(report["measurement_regimes"]["gsc"]) == 1
    assert len(report["measurement_regimes"]["business"]) == 1
    assert decay["decision"] == "wait_for_data"
    assert "organic_sessions" not in decay["metrics"]["current"]


def test_content_portfolio_merges_private_daily_history_statistics(tmp_path: Path) -> None:
    project_dir = _project(tmp_path / "project")
    history = project_dir / "audits/statistics/history"
    history.mkdir(parents=True)
    days = [date(2026, 7, 4) + timedelta(days=offset) for offset in range(57) if offset != 28]
    (history / "gsc-page-daily.jsonl").write_text(
        "".join(
            json.dumps(
                {
                    "date": day.isoformat(),
                    "url": DECAY,
                    "clicks": 2 if day <= date(2026, 7, 31) else 5,
                    "impressions": 100,
                    "ctr": 0.02,
                    "position": 8,
                }
            )
            + "\n"
            for day in days
        )
    )
    (history / "coverage.json").write_text(
        json.dumps({"schema_version": "statistics-coverage-v1", "sources": {"gsc": [day.isoformat() for day in days], "business": []}})
    )

    report, _ = analyze_content_portfolio(project_dir, gsc_path=_gsc(tmp_path / "gsc.json"))
    decay = next(item for item in report["items"] if item["url"] == DECAY)

    assert report["schema_version"] == "content-portfolio-v4"
    assert report["statistics"]["search_change_confidence"]["status"] == "ok"
    assert decay["statistics"]["search_change_confidence"]["click_change"]["direction"] == "increase"
    assert decay["decision"] != "refresh"
    assert report["source_status"]["statistics_history"]["status"] == "ok"


def test_content_portfolio_cli_writes_latest_report(tmp_path: Path, capsys) -> None:
    project_dir = _project(tmp_path / "project")
    source = _gsc(tmp_path / "gsc.json")
    assert main(["--project-dir", str(project_dir), "content", "portfolio", "--gsc-json", str(source), "--json"]) == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["ok"] is True
    assert payload["count"] == 3
    assert (project_dir / "audits/content-portfolio/latest.json").is_file()


def test_pages_refresh_is_the_primary_cli_alias(tmp_path: Path, capsys) -> None:
    project_dir = _project(tmp_path / "project")
    source = _gsc(tmp_path / "gsc.json")

    assert main(["--project-dir", str(project_dir), "pages", "refresh", "--gsc-json", str(source), "--json"]) == 0

    payload = json.loads(capsys.readouterr().out)
    assert payload["ok"] is True
    assert payload["schema_version"] == "content-portfolio-v4"
    assert payload["count"] == 3
    assert "items" not in payload


def test_pages_refresh_keeps_local_assets_when_gsc_is_missing(tmp_path: Path) -> None:
    project_dir = _project(tmp_path / "project")
    _tech(project_dir)

    report, _ = analyze_content_portfolio(
        project_dir,
        now=datetime(2026, 9, 1, tzinfo=timezone.utc),
    )

    rows = {item["url"]: item for item in report["items"]}
    assert report["collection_status"] == "partial"
    assert set(rows) == {DECAY, CONFLICT, NEW, TECH_ONLY}
    assert rows[TECH_ONLY]["metrics"]["current"] is None
    assert rows[TECH_ONLY]["signals"] == ["gsc_not_observed"]
