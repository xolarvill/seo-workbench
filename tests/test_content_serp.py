import json
from datetime import datetime, timezone
from pathlib import Path

from seo_workbench import state
from seo_workbench.cli import main
from seo_workbench.content_serp import write_serp_competitors


def test_write_serp_competitors_uses_pipeline_keyword(tmp_path: Path) -> None:
    project_dir = tmp_path / "project"
    state.init_state("shopify", "Store", "https://example.com", project_dir=project_dir)
    (project_dir / "content/blog-pipeline.jsonl").write_text(
        json.dumps({"id": "rec1", "target_keyword": "desk setup"}) + "\n",
        encoding="utf-8",
    )

    report, path = write_serp_competitors(
        project_dir,
        "rec1",
        api_key="tvly-test",
        now=datetime(2026, 1, 2, tzinfo=timezone.utc),
        requester=lambda query, **_: {
            "response_time": 0.1,
            "results": [
                {"title": "Competitor", "url": "https://competitor.example/post", "content": "Useful SERP angle", "score": 0.8},
                {"title": "Ignored", "content": "Missing URL"},
            ],
        },
    )

    data = json.loads(path.read_text(encoding="utf-8"))
    assert report["query"] == "desk setup"
    assert path.name == "rec1-serp.json"
    assert data["competitor_count"] == 1
    assert data["competitors"][0]["url"] == "https://competitor.example/post"


def test_content_serp_competitors_cli_outputs_json(tmp_path: Path, monkeypatch, capsys) -> None:
    project_dir = tmp_path / "project"
    state.init_state("shopify", "Store", "https://example.com", project_dir=project_dir)

    def fake_write(project_dir_arg, item_id, **kwargs):
        path = project_dir_arg / "strategy/briefs/rec1-serp.json"
        return {"collection_status": "ok", "item_id": item_id, "competitor_count": 0}, path

    monkeypatch.setattr("seo_workbench.cli.write_serp_competitors", fake_write)

    assert main(["--project-dir", str(project_dir), "content", "serp-competitors", "rec1", "--json"]) == 0
    payload = json.loads(capsys.readouterr().out)

    assert payload["ok"] is True
    assert payload["item_id"] == "rec1"
