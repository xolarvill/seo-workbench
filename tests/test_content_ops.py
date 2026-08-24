import json
from datetime import datetime, timezone
from pathlib import Path

from seo_workbench import state
from seo_workbench.cli import main
from seo_workbench.content_ops import build_content_ops


def test_build_content_ops_maps_hexcal_blog_actions(tmp_path: Path) -> None:
    project_dir = tmp_path / "project"
    state.init_state("shopify", "Hexcal", "https://www.hexcal.com", project_dir=project_dir)
    data = state.load_state(project_dir)
    data["contentQueue"] = [
        {"id": "rec_review_push", "status": "review", "title": "Push"},
        {"id": "rec_planned", "status": "planned", "title": "Plan"},
        {"id": "rec_write", "status": "ready_to_write", "title": "Write"},
        {"id": "rec_review_digest", "status": "review", "title": "Digest", "review_thread_id": "om_1"},
        {"id": "rec_revise", "status": "revision_requested", "title": "Revise"},
        {"id": "rec_publish", "status": "approved", "title": "Publish"},
        {
            "id": "rec_index",
            "status": "scheduled",
            "title": "Index",
            "live_url": "https://example.com/blogs/articles/index",
            "scheduled_at": "2026-07-29T00:00:00Z",
        },
        {"id": "rec_inspect", "status": "submitted_for_indexing", "title": "Inspect", "live_url": "https://example.com/blogs/articles/inspect"},
    ]
    state.save_state(data, project_dir)

    report = build_content_ops(project_dir, now=datetime(2026, 7, 29, 5, 0, tzinfo=timezone.utc))
    actions = {item["id"]: item for item in report["actions"]}

    assert actions["review_push"]["due"] is True
    assert actions["cluster_review"]["due"] is True
    assert actions["write_brief"]["due"] is True
    assert actions["write_brief"]["command"] == "content brief <item_id>"
    assert actions["review_digest"]["due"] is True
    assert actions["revise_brief"]["due"] is True
    assert actions["publish"]["count"] == 1
    assert "index_submit" not in actions
    assert actions["gsc_inspect"]["due"] is True
    assert actions["content_report"]["command"] == "content report --period daily"


def test_content_ops_cli_outputs_json(tmp_path: Path, capsys) -> None:
    project_dir = tmp_path / "project"
    state.init_state("shopify", "Hexcal", "https://www.hexcal.com", project_dir=project_dir)

    assert main(["--project-dir", str(project_dir), "content", "ops", "--json"]) == 0
    payload = json.loads(capsys.readouterr().out)

    assert payload["ok"] is True
    assert payload["schema_version"] == "content-ops-v1"
