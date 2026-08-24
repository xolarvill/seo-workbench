import json
from datetime import date
from pathlib import Path

from seo_workbench import state
from seo_workbench.cli import main
from seo_workbench.content_reports import generate_content_report


def test_generate_content_report_writes_draft_and_run_record(tmp_path: Path) -> None:
    project_dir = tmp_path / "project"
    state.init_state("shopify", "Store", "https://example.com", project_dir=project_dir)
    data = state.load_state(project_dir)
    data["contentQueue"] = [
        {
            "id": "rec1",
            "status": "scheduled",
            "title": "Due",
            "slug": "due",
            "scheduled_at": "2026-07-29T00:00:00Z",
            "live_url": "https://example.com/blogs/articles/due",
        },
        {"id": "rec2", "status": "review", "title": "Needs review", "slug": "needs-review"},
    ]
    state.save_state(data, project_dir)
    (project_dir / "content/blog-pipeline.jsonl").write_text(
        json.dumps({"id": "rec1", "shopify_article_id": "123", "live_url": "https://example.com/blogs/articles/due"})
        + "\n",
        encoding="utf-8",
    )

    summary, path = generate_content_report(project_dir, period="daily", report_date=date(2026, 7, 29))

    assert summary["collection_status"] == "draft_ready"
    assert summary["notification_sent"] is False
    assert summary["totals"]["due_for_indexing"] == 1
    assert summary["totals"]["needs_review"] == 1
    assert any(action["id"] == "review_push" for action in summary["next_actions"])
    assert any(action["id"] == "gsc_inspect" for action in summary["next_actions"])
    assert path == project_dir / "content/reports/2026-07-29-daily.md"
    report_text = path.read_text(encoding="utf-8")
    assert "Due For Indexing" in report_text
    assert "Next Actions" in report_text
    assert "content review-push" in report_text
    run_record = project_dir / summary["run_record_path"]
    assert json.loads(run_record.read_text(encoding="utf-8"))["report_path"] == "content/reports/2026-07-29-daily.md"


def test_content_report_cli_outputs_json(tmp_path: Path, capsys) -> None:
    project_dir = tmp_path / "project"
    state.init_state("shopify", "Store", "https://example.com", project_dir=project_dir)

    assert main(["--project-dir", str(project_dir), "content", "report", "--period", "weekly", "--date", "2026-07-29", "--json"]) == 0
    payload = json.loads(capsys.readouterr().out)

    assert payload["ok"] is True
    assert payload["period"] == "weekly"
    assert Path(payload["path"]).name == "2026-07-29-weekly.md"
