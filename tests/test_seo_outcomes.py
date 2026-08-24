import json
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

from seo_workbench import state
from seo_workbench.cli import main
from seo_workbench.seo_changes import record_change
from seo_workbench.seo_outcomes import evaluate_change
from seo_workbench.measurement_regimes import record_regime


NOW = datetime(2026, 9, 5, 8, 0, tzinfo=timezone.utc)
URL = "https://www.example.com/collections/desks"


def _project(tmp_path: Path) -> tuple[Path, str]:
    project_dir = tmp_path / "project"
    state.init_state("shopify", "Example", "https://www.example.com", project_dir=project_dir)
    change = record_change(
        project_dir,
        urls=[URL],
        change_type="content",
        hypothesis="Fit guidance will increase qualified organic clicks.",
        metrics=["clicks", "ctr"],
        changed_at="2026-08-01",
        review_date="2026-08-29",
        now=datetime(2026, 8, 1, tzinfo=timezone.utc),
    )
    return project_dir, change["id"]


def _gsc(path: Path, *, current_clicks: int = 30, current_start: str = "2026-08-02") -> Path:
    def page(start: str, end: str, clicks: int, impressions: int, position: float) -> dict:
        return {
            "request": {"startDate": start, "endDate": end, "dimensions": ["page"]},
            "rows": [
                {
                    "keys": [URL],
                    "clicks": clicks,
                    "impressions": impressions,
                    "ctr": clicks / impressions,
                    "position": position,
                }
            ],
        }

    def date_page(start: str, end: str, clicks: int) -> dict:
        start_day, end_day = date.fromisoformat(start), date.fromisoformat(end)
        days = (end_day - start_day).days + 1
        quotient, remainder = divmod(clicks, days)
        return {
            "request": {"startDate": start, "endDate": end, "dimensions": ["date", "page"]},
            "rows": [
                {
                    "keys": [(start_day + timedelta(days=index)).isoformat(), URL],
                    "clicks": quotient + (1 if index < remainder else 0),
                    "impressions": 10,
                    "ctr": 0,
                    "position": 8,
                }
                for index in range(days)
            ],
            "truncated": False,
        }

    payload = {
        "collection_status": "ok",
        "property": "sc-domain:example.com",
        "data_state": "final",
        "windows": {
            "previous": {
                "page": page("2026-07-04", "2026-07-31", 10, 200, 9.0),
                "date_page": date_page("2026-07-04", "2026-07-31", 10),
                "query_page": {"rows": []},
            },
            "current": {
                "page": page(current_start, "2026-08-29", current_clicks, 300, 7.0),
                "date_page": date_page(current_start, "2026-08-29", current_clicks),
                "query_page": {
                    "rows": [
                        {"keys": ["desk shelf", URL], "clicks": current_clicks, "impressions": 250, "ctr": 0.12, "position": 6.5},
                        {
                            "keys": ["desk shelf", "https://www.example.com/blogs/desk-shelf"],
                            "clicks": 2,
                            "impressions": 50,
                            "ctr": 0.04,
                            "position": 12.0,
                        },
                    ]
                },
            },
        },
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload))
    return path


def test_evaluate_change_reports_winning_metrics_and_query_ownership(tmp_path: Path) -> None:
    project_dir, change_id = _project(tmp_path)
    report, path = evaluate_change(project_dir, change_id, gsc_path=_gsc(tmp_path / "gsc.json"), now=NOW)

    assert report["classification"] == "winning"
    assert report["schema_version"] == "seo-outcome-v2"
    assert report["causal_claim"] is False
    assert report["metrics"]["delta"]["clicks"]["absolute"] == 20
    assert report["expected_metric_signals"] == {"clicks": "improving", "ctr": "improving"}
    assert report["query_ownership"][0]["multiple_page_signal"] is True
    assert report["statistical_evidence"]["pre_post"]["click_change"]["direction"] == "increase"
    assert path.stat().st_mode & 0o777 == 0o600
    assert (path.parent / "latest.json").is_file()


def test_evaluate_change_refuses_to_label_contaminated_window(tmp_path: Path) -> None:
    project_dir, change_id = _project(tmp_path)
    report, _ = evaluate_change(
        project_dir,
        change_id,
        gsc_path=_gsc(tmp_path / "gsc.json", current_start="2026-07-30"),
        now=NOW,
    )

    assert report["classification"] == "insufficient_data"
    assert report["comparability"]["comparable"] is False
    assert "current window includes pre-change or change-day dates" in report["comparability"]["issues"]


def test_evaluate_change_refuses_measurement_regime_breaks(tmp_path: Path) -> None:
    project_dir, change_id = _project(tmp_path)
    record_regime(
        project_dir,
        source="gsc",
        effective_at="2026-08-15",
        description="Changed Search Console property",
    )

    report, _ = evaluate_change(project_dir, change_id, gsc_path=_gsc(tmp_path / "gsc.json"), now=NOW)

    assert report["classification"] == "insufficient_data"
    assert report["comparability"]["comparable"] is False
    assert len(report["measurement_regimes"]["gsc"]) == 1


def test_evaluate_change_adds_matched_controls_only_when_history_is_valid(tmp_path: Path) -> None:
    project_dir, change_id = _project(tmp_path)
    before = [date(2026, 7, 4) + timedelta(days=offset) for offset in range(28)]
    after = [date(2026, 8, 2) + timedelta(days=offset) for offset in range(28)]
    controls = [f"https://www.example.com/collections/control-{index}" for index in range(3)]
    rows = []
    for day in before + after:
        current = day >= date(2026, 8, 2)
        rows.append(
            {
                "date": day.isoformat(),
                "url": URL,
                "clicks": 4 if current else 1,
                "impressions": 10,
                "ctr": 0.4 if current else 0.1,
                "position": 8,
            }
        )
        rows.extend(
            {
                "date": day.isoformat(),
                "url": control,
                "clicks": 1,
                "impressions": 10,
                "ctr": 0.1,
                "position": 8,
            }
            for control in controls
        )
    history = project_dir / "audits/statistics/history"
    history.mkdir(parents=True)
    (history / "gsc-page-daily.jsonl").write_text("".join(json.dumps(row) + "\n" for row in rows))
    (history / "coverage.json").write_text(
        json.dumps({"schema_version": "statistics-coverage-v1", "sources": {"gsc": [day.isoformat() for day in before + after], "business": []}})
    )

    report, _ = evaluate_change(project_dir, change_id, gsc_path=_gsc(tmp_path / "gsc.json"), now=NOW)
    matched = report["statistical_evidence"]["matched_control"]

    assert matched["status"] == "ok"
    assert matched["control_urls"] == controls
    assert matched["click_effect"]["direction"] == "increase"
    assert matched["causal_claim"] is False


def test_evaluate_change_treats_unobserved_page_as_insufficient_data(tmp_path: Path) -> None:
    project_dir, change_id = _project(tmp_path)
    source = _gsc(tmp_path / "gsc.json")
    payload = json.loads(source.read_text())
    payload["windows"]["previous"]["page"]["rows"] = []
    payload["windows"]["current"]["page"]["rows"] = []
    source.write_text(json.dumps(payload))

    report, _ = evaluate_change(project_dir, change_id, gsc_path=source, now=NOW)

    assert report["classification"] == "insufficient_data"
    assert report["expected_metric_signals"] == {"clicks": "insufficient_data", "ctr": "insufficient_data"}


def test_changes_evaluate_cli_writes_json_report(tmp_path: Path, capsys) -> None:
    project_dir, change_id = _project(tmp_path)
    source = _gsc(tmp_path / "gsc.json")

    assert main(
        [
            "--project-dir",
            str(project_dir),
            "changes",
            "evaluate",
            change_id,
            "--gsc-json",
            str(source),
            "--json",
        ]
    ) == 0
    report = json.loads(capsys.readouterr().out)
    assert report["ok"] is True
    assert report["classification"] == "winning"


def test_changes_evaluate_cli_can_refresh_change_scoped_gsc(tmp_path: Path, capsys, monkeypatch) -> None:
    project_dir, change_id = _project(tmp_path)
    source = _gsc(tmp_path / "gsc.json")
    captured = {}

    def collect(_project_dir, _output_dir, **kwargs):
        captured.update(kwargs)
        return {"manifest": {"path": str(source)}}

    monkeypatch.setattr("seo_workbench.seo_outcomes.collect_change_performance", collect)

    assert main(["--project-dir", str(project_dir), "changes", "evaluate", change_id, "--refresh-gsc", "--json"]) == 0
    report = json.loads(capsys.readouterr().out)
    assert report["classification"] == "winning"
    assert captured["changed_at"].isoformat() == "2026-08-01"
    assert captured["review_date"].isoformat() == "2026-08-29"
