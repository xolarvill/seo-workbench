import json
from datetime import datetime, timezone
from pathlib import Path

import pytest

from seo_workbench import state
from seo_workbench.presentation import generate_weekly_presentation, presentation_due, presentation_status


def _write_json(project_dir: Path, relative: str, payload: dict) -> None:
    path = state.safe_project_path(project_dir, relative)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload), encoding="utf-8")


def _ready_project(tmp_path: Path) -> tuple[Path, datetime]:
    project_dir = tmp_path / "project"
    state.init_state("shopify", "Store", "https://example.com", project_dir=project_dir)
    now = datetime(2026, 8, 28, 8, 0, tzinfo=timezone.utc)
    _write_json(
        project_dir,
        "audits/statistics/latest.json",
        {
            "schema_version": "statistics-run-v1",
            "collection_status": "ok",
            "completed_at": now.isoformat(),
            "common_finalized_end_date": "2026-08-26",
            "steps": {"history": {"sources": {"gsc": {"covered_days": 28}, "business": {"covered_days": 28}}}, "portfolio": {"status": "ok"}},
        },
    )
    _write_json(
        project_dir,
        "audits/content-portfolio/latest.json",
        {
            "collection_status": "ok",
            "generated_at": now.isoformat(),
            "count": 1,
            "statistics": {
                "click_change_decomposition": {"current_observed_clicks": 120, "previous_observed_clicks": 100, "observed_click_change": 20},
                "search_trend": {"weekly_clicks": [80, 90, 100]},
                "ranking_opportunity": {"positions_4_20_impressions": 240},
                "query_portfolio": {"current": {"observed_query_count": 12}},
            },
        },
    )
    _write_json(
        project_dir,
        "audits/business-signals/latest.json",
        {"collection_status": "ok", "currency": "USD", "windows": {"current": {"rows": [{"organic_sessions": 20, "organic_product_views": 10, "organic_add_to_carts": 3, "organic_checkouts": 2, "organic_purchases": 1, "organic_revenue": 99}]}}},
    )
    report = state.safe_project_path(project_dir, "reports/2026_week_35_work_done.md")
    report.write_text("# Store\n\n## 速览\n\n- [x] Done\n\n## 实质工作\n\n### 1. Evidence refresh（08-28）\n\n## 遗留工作\n\n- [ ] Follow-up\n", encoding="utf-8")
    return project_dir, now


def test_presentation_status_blocks_stale_or_unfinalized_data(tmp_path: Path) -> None:
    project_dir = tmp_path / "project"
    state.init_state("shopify", "Store", "https://example.com", project_dir=project_dir)
    status = presentation_status(project_dir, now=datetime(2026, 8, 28, 8, 0, tzinfo=timezone.utc))
    assert status["status"] == "blocked"
    assert any(check["code"] == "statistics_status" and not check["passed"] for check in status["checks"])


def test_presentation_is_due_only_on_friday_afternoon(tmp_path: Path) -> None:
    project_dir, _now = _ready_project(tmp_path)
    assert presentation_due(project_dir, now=datetime(2026, 8, 28, 7, 59, tzinfo=timezone.utc).astimezone()) is False
    assert presentation_due(project_dir, now=datetime(2026, 8, 28, 8, 0, tzinfo=timezone.utc).astimezone()) is True


def test_generate_weekly_presentation_writes_pdf_and_manifest(tmp_path: Path) -> None:
    pytest.importorskip("matplotlib")
    project_dir, now = _ready_project(tmp_path)
    result, path = generate_weekly_presentation(project_dir, now=now)
    assert result["path"] == "reports/presentations/2026_week_35.pdf"
    assert path.is_file() and path.stat().st_size > 1_000
    manifest = json.loads(state.safe_project_path(project_dir, result["manifest_path"]).read_text(encoding="utf-8"))
    assert manifest["pages"] == 4
    assert manifest["period"] == {"start": "2026-08-24", "end": "2026-08-28"}
