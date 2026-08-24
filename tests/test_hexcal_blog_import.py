import json
from pathlib import Path

from seo_workbench import state
from seo_workbench.cli import main
from seo_workbench.hexcal_blog_import import import_hexcal_blog
from seo_workbench.workflow import DEFAULT_WORKFLOW
from seo_workbench.validation import validate_project


def _read_jsonl(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def test_import_hexcal_blog_lark_envelope_updates_project_files_and_queue(tmp_path: Path) -> None:
    state.init_state("shopify", "Hexcal", "https://www.hexcal.com", project_dir=tmp_path)
    keywords = tmp_path / "keywords.json"
    pipeline = tmp_path / "pipeline.json"
    keywords.write_text(
        json.dumps(
            {
                "data": {
                    "field_id_list": ["keyword", "source", "priority_score"],
                    "record_id_list": ["kw1"],
                    "data": [["minimal desk setup", "autocomplete", 42.5]],
                }
            }
        ),
        encoding="utf-8",
    )
    pipeline.write_text(
        json.dumps(
            {
                "data": {
                    "field_id_list": ["cluster_name", "status", "slug", "title", "target_keyword", "scheduled_at", "live_url", "review_thread_id"],
                    "record_id_list": ["rec1"],
                    "data": [["small desk setup", "cluster_approved", "small-desk-setup", "Small Desk Setup", "small desk setup", "2026-08-01T00:00:00Z", "https://www.hexcal.com/blogs/articles/small-desk-setup", "om_review"]],
                }
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    result = import_hexcal_blog(tmp_path, keywords_path=keywords, pipeline_path=pipeline)

    assert result["keywords_imported"] == 1
    assert result["pipeline_imported"] == 1
    assert _read_jsonl(tmp_path / "strategy/keyword-pool.jsonl")[0]["priority_score"] == 42.5
    pipeline_record = _read_jsonl(tmp_path / "content/blog-pipeline.jsonl")[0]
    assert pipeline_record["status"] == "ready_to_write"
    assert pipeline_record["review_thread_id"] == "om_review"
    data = state.load_state(tmp_path)
    assert data["contentQueue"][0]["id"] == "rec1"
    assert data["contentQueue"][0]["status"] == "ready_to_write"
    assert data["contentQueue"][0]["scheduled_at"] == "2026-08-01T00:00:00Z"
    assert data["contentQueue"][0]["live_url"] == "https://www.hexcal.com/blogs/articles/small-desk-setup"
    assert data["contentQueue"][0]["review_thread_id"] == "om_review"
    assert validate_project(tmp_path, DEFAULT_WORKFLOW)["ok"] is True


def test_import_hexcal_blog_accepts_name_keyed_rows(tmp_path: Path) -> None:
    state.init_state("shopify", "Hexcal", "https://www.hexcal.com", project_dir=tmp_path)
    pipeline = tmp_path / "pipeline.json"
    pipeline.write_text(
        json.dumps(
            [
                {
                    "_record_id": "rec2",
                    "status": "修改中",
                    "cluster_name": "ergonomic desk setup",
                    "feature_image_refs": [{"id": "ugc1"}],
                    "feature_image_hist_refs": [{"record_id": "ugc2"}],
                }
            ],
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    import_hexcal_blog(tmp_path, pipeline_path=pipeline)

    record = _read_jsonl(tmp_path / "content/blog-pipeline.jsonl")[0]
    assert record["status"] == "revision_requested"
    assert record["feature_image_refs"] == ["ugc1", "ugc2"]


def test_import_hexcal_blog_normalizes_lark_schedule_to_utc(tmp_path: Path) -> None:
    state.init_state("shopify", "Hexcal", "https://www.hexcal.com", project_dir=tmp_path)
    pipeline = tmp_path / "pipeline.json"
    pipeline.write_text(
        json.dumps(
            [
                {"_record_id": "rec_lark", "status": "approved", "scheduled_at": "2026-08-01 12:00:00"},
                {"_record_id": "rec_utc", "status": "approved", "scheduled_at": "2026-08-01T17:00:00Z"},
            ]
        ),
        encoding="utf-8",
    )

    import_hexcal_blog(tmp_path, pipeline_path=pipeline)

    records = _read_jsonl(tmp_path / "content/blog-pipeline.jsonl")
    assert records[0]["scheduled_at"] == "2026-08-01T16:00:00Z"
    assert records[1]["scheduled_at"] == "2026-08-01T17:00:00Z"


def test_content_import_hexcal_cli(tmp_path: Path, capsys) -> None:
    project_dir = tmp_path / "project"
    state.init_state("shopify", "Hexcal", "https://www.hexcal.com", project_dir=project_dir)
    pipeline = tmp_path / "pipeline.json"
    pipeline.write_text(json.dumps([{"_record_id": "rec3", "status": "已收录", "title": "Done"}], ensure_ascii=False), encoding="utf-8")

    assert main(["--project-dir", str(project_dir), "content", "import-hexcal", "--pipeline-json", str(pipeline), "--json"]) == 0
    payload = json.loads(capsys.readouterr().out)

    assert payload["ok"] is True
    assert payload["pipeline_imported"] == 1
    assert state.load_state(project_dir)["contentQueue"][0]["status"] == "indexed"


def test_content_import_hexcal_requires_input(tmp_path: Path, capsys) -> None:
    project_dir = tmp_path / "project"
    state.init_state("shopify", "Hexcal", "https://www.hexcal.com", project_dir=project_dir)

    assert main(["--project-dir", str(project_dir), "content", "import-hexcal", "--json"]) == 1
    payload = json.loads(capsys.readouterr().out)

    assert payload["ok"] is False
    assert "requires" in payload["error"]


def test_content_queue_and_status_cli_are_human_gates(tmp_path: Path, capsys) -> None:
    project_dir = tmp_path / "project"
    state_path = state.init_state("shopify", "Hexcal", "https://www.hexcal.com", project_dir=project_dir)
    data = state.read_json(state_path)
    data["contentQueue"] = [{"id": "rec4", "status": "review", "title": "Review me"}]
    state.write_json(state_path, data)
    (project_dir / "content/blog-pipeline.jsonl").write_text(
        json.dumps({"id": "rec4", "status": "review", "title": "Review me"}) + "\n",
        encoding="utf-8",
    )

    assert main(["--project-dir", str(project_dir), "content", "queue", "--status", "review", "--json"]) == 0
    queue = json.loads(capsys.readouterr().out)
    assert queue["count"] == 1

    assert main(["--project-dir", str(project_dir), "content", "status", "rec4", "approved", "--note", "human approved", "--json"]) == 0
    item = json.loads(capsys.readouterr().out)["item"]
    updated = state.load_state(project_dir)
    pipeline = _read_jsonl(project_dir / "content/blog-pipeline.jsonl")

    assert item["status"] == "approved"
    assert updated["contentQueue"][0]["note"] == "human approved"
    assert pipeline[0]["status"] == "approved"
    assert pipeline[0]["note"] == "human approved"
    assert updated["history"][-1]["action"] == "content-status"


def test_reimport_preserves_workbench_records_and_local_decisions(tmp_path: Path) -> None:
    state.init_state("shopify", "Hexcal", "https://www.hexcal.com", project_dir=tmp_path)
    (tmp_path / "strategy/keyword-pool.jsonl").write_text(
        json.dumps({"id": "local-keyword", "keyword": "workbench keyword", "source": "workbench"}) + "\n",
        encoding="utf-8",
    )
    (tmp_path / "content/blog-pipeline.jsonl").write_text(
        "\n".join(
            [
                json.dumps({"id": "shared", "status": "approved", "title": "Workbench title", "draft_html": "<p>Local draft</p>"}),
                json.dumps({"id": "local-idea", "status": "planned", "cluster_name": "Workbench idea"}),
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    data = state.load_state(tmp_path)
    data["contentQueue"] = [
        {"id": "shared", "status": "approved", "title": "Workbench title", "note": "human approved", "review_thread_id": "om_local"},
        {"id": "local-idea", "status": "planned", "title": "Workbench idea"},
    ]
    state.save_state(data, tmp_path)
    pipeline = tmp_path / "feishu-pipeline.json"
    keywords = tmp_path / "feishu-keywords.json"
    keywords.write_text(
        json.dumps([{"_record_id": "feishu-keyword", "keyword": "legacy keyword", "source": "feishu"}]),
        encoding="utf-8",
    )
    pipeline.write_text(
        json.dumps(
            [
                {"_record_id": "shared", "status": "cluster_pending", "title": "Stale Feishu title"},
                {"_record_id": "feishu-new", "status": "cluster_approved", "title": "Imported idea"},
            ]
        ),
        encoding="utf-8",
    )

    result = import_hexcal_blog(tmp_path, keywords_path=keywords, pipeline_path=pipeline)

    records = {record["id"]: record for record in _read_jsonl(tmp_path / "content/blog-pipeline.jsonl")}
    queue = {item["id"]: item for item in state.load_state(tmp_path)["contentQueue"]}
    keyword_pool = {item["id"]: item for item in _read_jsonl(tmp_path / "strategy/keyword-pool.jsonl")}
    assert result["keywords_imported"] == 1
    assert result["pipeline_imported"] == 2
    assert result["content_queue_count"] == 3
    assert records["shared"]["status"] == "approved"
    assert records["shared"]["title"] == "Workbench title"
    assert records["shared"]["draft_html"] == "<p>Local draft</p>"
    assert records["local-idea"]["cluster_name"] == "Workbench idea"
    assert records["feishu-new"]["status"] == "ready_to_write"
    assert queue["shared"]["note"] == "human approved"
    assert queue["shared"]["review_thread_id"] == "om_local"
    assert queue["local-idea"]["title"] == "Workbench idea"
    assert keyword_pool["local-keyword"]["keyword"] == "workbench keyword"
    assert keyword_pool["feishu-keyword"]["keyword"] == "legacy keyword"
