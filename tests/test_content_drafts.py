import json
from datetime import datetime, timezone
from pathlib import Path

import pytest

from seo_workbench import state
from seo_workbench.cli import main
from seo_workbench.content_drafts import import_draft


def test_import_draft_updates_pipeline_queue_and_draft_file(tmp_path: Path) -> None:
    project_dir = tmp_path / "project"
    state.init_state("shopify", "Hexcal", "https://www.hexcal.com", project_dir=project_dir)
    data = state.load_state(project_dir)
    data["contentQueue"] = [{"id": "rec1", "status": "drafting", "review_thread_id": "old_thread"}]
    state.save_state(data, project_dir)
    (project_dir / "content/blog-pipeline.jsonl").write_text(json.dumps({"id": "rec1", "status": "drafting"}) + "\n", encoding="utf-8")
    draft = tmp_path / "draft.json"
    draft.write_text(
        json.dumps(
            {
                "pipeline_record_id": "rec1",
                "qc_status": "review_ready",
                "qc_score": 12,
                "article": {
                    "title": "New Draft",
                    "article_slug": "new-draft",
                    "target_keyword": "desk setup",
                    "scheduled_at": "2026-08-10T12:00:00-05:00",
                    "draft_html": "<p>Useful desk setup guide.</p>",
                    "feature_image_rid": "ugc1",
                    "inline_image_rids": ["ugc2"],
                },
            }
        ),
        encoding="utf-8",
    )

    report, path = import_draft(project_dir, draft, now=datetime(2026, 7, 29, tzinfo=timezone.utc))

    assert report["status"] == "review"
    assert path.name.endswith("-content-draft-import.json")
    queue = state.load_state(project_dir)["contentQueue"]
    assert queue[0]["status"] == "review"
    assert queue[0]["review_thread_id"] == ""
    assert queue[0]["scheduled_at"] == "2026-08-10T17:00:00Z"
    record = json.loads((project_dir / "content/blog-pipeline.jsonl").read_text(encoding="utf-8").splitlines()[0])
    assert record["title"] == "New Draft"
    assert record["scheduled_at"] == "2026-08-10T17:00:00Z"
    assert record["feature_image_refs"] == ["ugc1"]
    assert (project_dir / "content/drafts/new-draft.html").read_text(encoding="utf-8").strip() == "<p>Useful desk setup guide.</p>"


def test_import_draft_preserves_shopify_article_id_and_live_url(tmp_path: Path) -> None:
    project_dir = tmp_path / "project"
    state.init_state("shopify", "Hexcal", "https://www.hexcal.com", project_dir=project_dir)
    draft = tmp_path / "draft.json"
    draft.write_text(
        json.dumps(
            {
                "pipeline_record_id": "rec-refresh",
                "qc_status": "review_ready",
                "article": {
                    "title": "Refresh",
                    "article_slug": "refresh-guide",
                    "draft_html": "<p>Refreshed body.</p>",
                    "shopify_article_id": "123",
                    "live_url": "https://www.hexcal.com/blogs/articles/refresh-guide",
                },
            }
        ),
        encoding="utf-8",
    )

    import_draft(project_dir, draft, now=datetime(2026, 8, 14, tzinfo=timezone.utc))

    record = json.loads((project_dir / "content/blog-pipeline.jsonl").read_text(encoding="utf-8").splitlines()[0])
    assert record["shopify_article_id"] == "123"
    assert record["live_url"] == "https://www.hexcal.com/blogs/articles/refresh-guide"


def test_import_draft_qc_flag_blocks_item(tmp_path: Path) -> None:
    project_dir = tmp_path / "project"
    state.init_state("shopify", "Hexcal", "https://www.hexcal.com", project_dir=project_dir)
    draft = tmp_path / "draft.json"
    draft.write_text(
        json.dumps(
            {
                "pipeline_record_id": "rec1",
                "qc_status": "review_flag",
                "qc_issues": ["Unsupported claim"],
                "article": {"draft_html": "<p>Body</p>"},
            }
        ),
        encoding="utf-8",
    )

    import_draft(project_dir, draft)

    item = state.load_state(project_dir)["contentQueue"][0]
    assert item["status"] == "blocked"
    record = json.loads((project_dir / "content/blog-pipeline.jsonl").read_text(encoding="utf-8").splitlines()[0])
    assert "Unsupported claim" in record["edit_notes"]


def test_import_draft_scrubs_ai_signatures_before_writing(tmp_path: Path) -> None:
    project_dir = tmp_path / "project"
    state.init_state("shopify", "Hexcal", "https://www.hexcal.com", project_dir=project_dir)
    draft = tmp_path / "draft.json"
    draft.write_text(
        json.dumps(
            {
                "pipeline_record_id": "rec1",
                "qc_status": "review_ready",
                "article": {
                    "draft_html": "<p>In today's world\u200b, Hexcal works — cleanly.</p>",
                },
            }
        ),
        encoding="utf-8",
    )

    report, _ = import_draft(project_dir, draft)
    record = json.loads((project_dir / "content/blog-pipeline.jsonl").read_text(encoding="utf-8").splitlines()[0])

    assert report["scrub_stats"]["watermarks"] == 1
    assert "In today's world" not in record["draft_html"]
    assert "—" not in record["draft_html"]


def test_content_import_draft_cli_outputs_json(tmp_path: Path, capsys) -> None:
    project_dir = tmp_path / "project"
    state.init_state("shopify", "Hexcal", "https://www.hexcal.com", project_dir=project_dir)
    draft = tmp_path / "draft.json"
    draft.write_text(json.dumps({"pipeline_record_id": "rec1", "article": {"draft_html": "<p>Body</p>"}}), encoding="utf-8")

    assert main(["--project-dir", str(project_dir), "content", "import-draft", "--from-file", str(draft), "--json"]) == 0
    payload = json.loads(capsys.readouterr().out)

    assert payload["ok"] is True
    assert payload["schema_version"] == "content-draft-import-v1"


def test_import_draft_rejects_schedule_without_timezone(tmp_path: Path) -> None:
    project_dir = tmp_path / "project"
    state.init_state("shopify", "Store", "https://example.com", project_dir=project_dir)
    draft = tmp_path / "draft.json"
    draft.write_text(
        json.dumps({"item_id": "rec1", "scheduled_at": "2026-08-10T12:00:00", "draft_html": "<p>Body.</p>"}),
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="include a timezone"):
        import_draft(project_dir, draft)
