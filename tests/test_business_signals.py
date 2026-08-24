import csv
import json
from datetime import datetime, timezone
from pathlib import Path

import pytest

from seo_workbench import state
from seo_workbench.business_signals import import_business_signals
from seo_workbench.cli import main
from seo_workbench.seo_changes import record_change
from seo_workbench.seo_outcomes import evaluate_change


URL = "https://example.com/products/desk"


def _project(path: Path) -> Path:
    state.init_state("shopify", "Example", "https://example.com", project_dir=path)
    return path


def _csv(path: Path, *, url: str = URL) -> Path:
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=[
                "window",
                "start_date",
                "end_date",
                "url",
                "organic_sessions",
                "engaged_sessions",
                "conversions",
                "revenue",
                "orders",
            ],
        )
        writer.writeheader()
        writer.writerow({"window": "previous", "start_date": "2026-07-04", "end_date": "2026-07-31", "url": url, "organic_sessions": 10, "engaged_sessions": 8, "conversions": 1, "revenue": 50, "orders": 1})
        writer.writerow({"window": "current", "start_date": "2026-08-02", "end_date": "2026-08-29", "url": url, "organic_sessions": 30, "engaged_sessions": 24, "conversions": 3, "revenue": 150, "orders": 3})
    return path


def _gsc(path: Path) -> Path:
    def page(start: str, end: str) -> dict:
        return {
            "request": {"startDate": start, "endDate": end},
            "rows": [{"keys": [URL], "clicks": 10, "impressions": 200, "ctr": 0.05, "position": 8}],
        }

    path.write_text(
        json.dumps(
            {
                "collection_status": "ok",
                "windows": {
                    "previous": {"page": page("2026-07-04", "2026-07-31")},
                    "current": {"page": page("2026-08-02", "2026-08-29"), "query_page": {"rows": []}},
                },
            }
        )
    )
    return path


def test_import_business_signals_normalizes_aggregate_windows(tmp_path: Path) -> None:
    project_dir = _project(tmp_path / "project")
    report, path = import_business_signals(
        project_dir,
        _csv(tmp_path / "signals.csv"),
        now=datetime(2026, 9, 1, tzinfo=timezone.utc),
    )

    assert report["windows"]["current"]["rows"][0]["conversions"] == 3
    assert report["schema_version"] == "business-signals-v2"
    assert "key_events" not in report["windows"]["current"]["rows"][0]
    assert "key_events" not in report["metrics"]
    assert report["privacy"].startswith("Aggregated page-level")
    assert path.stat().st_mode & 0o777 == 0o600
    assert (path.parent / "latest.json").is_file()


def test_import_business_signals_rejects_external_urls(tmp_path: Path) -> None:
    project_dir = _project(tmp_path / "project")
    with pytest.raises(ValueError, match="outside the project site family"):
        import_business_signals(project_dir, _csv(tmp_path / "signals.csv", url="https://other.example/page"))


def test_change_outcome_uses_optional_conversion_evidence(tmp_path: Path, capsys) -> None:
    project_dir = _project(tmp_path / "project")
    business, business_path = import_business_signals(project_dir, _csv(tmp_path / "signals.csv"))
    assert business["collection_status"] == "ok"
    change = record_change(
        project_dir,
        urls=[URL],
        change_type="content",
        hypothesis="Qualified organic traffic should convert more often.",
        metrics=["engaged_sessions", "conversions", "revenue", "orders"],
        changed_at="2026-08-01",
        review_date="2026-08-29",
    )

    report, _ = evaluate_change(
        project_dir,
        change["id"],
        gsc_path=_gsc(tmp_path / "gsc.json"),
        business_path=business_path,
    )
    assert report["classification"] == "winning"
    assert report["metrics"]["delta"]["conversions"]["absolute"] == 2
    assert report["metrics"]["delta"]["engaged_sessions"]["absolute"] == 16
    assert report["metrics"]["delta"]["orders"]["absolute"] == 2
    assert report["missing_expected_metrics"] == []

    assert main(
        ["--project-dir", str(project_dir), "business-signals", "import", "--from-file", str(tmp_path / "signals.csv"), "--json"]
    ) == 0
    assert json.loads(capsys.readouterr().out)["ok"] is True


def test_change_outcome_marks_missing_business_evidence(tmp_path: Path) -> None:
    project_dir = _project(tmp_path / "project")
    change = record_change(
        project_dir,
        urls=[URL],
        change_type="content",
        hypothesis="Organic sessions should grow.",
        metrics=["organic_sessions"],
        changed_at="2026-08-01",
        review_date="2026-08-29",
    )

    report, _ = evaluate_change(project_dir, change["id"], gsc_path=_gsc(tmp_path / "gsc.json"))
    assert report["classification"] == "insufficient_data"
    assert report["missing_expected_metrics"] == ["organic_sessions"]
