import json
import subprocess
from datetime import datetime, timezone
from pathlib import Path

from seo_workbench import state
from seo_workbench.cli import main
from seo_workbench.content_review_push import push_review_request


FEISHU_CONFIG = Path(__file__).resolve().parents[1] / "templates/hexcal-feishu-profile.json"


def test_push_review_request_sends_feishu_post_and_stores_thread_id(tmp_path: Path) -> None:
    project_dir = tmp_path / "project"
    state.init_state("shopify", "Hexcal", "https://www.hexcal.com", project_dir=project_dir)
    data = state.load_state(project_dir)
    data["contentQueue"] = [{"id": "rec1", "status": "review", "title": "Draft", "slug": "draft"}]
    state.save_state(data, project_dir)
    (project_dir / "content/blog-pipeline.jsonl").write_text(
        json.dumps({"id": "rec1", "draft_html": "<h1>Draft</h1><p>Body</p>", "meta_description": "Meta"}) + "\n",
        encoding="utf-8",
    )
    calls = []
    payloads = []

    def runner(cmd, **kwargs):
        calls.append((cmd, kwargs))
        cwd = Path(kwargs["cwd"])
        payloads.append(
            (
                json.loads((cwd / "params.json").read_text(encoding="utf-8")),
                json.loads((cwd / "body.json").read_text(encoding="utf-8")),
            )
        )
        return subprocess.CompletedProcess(cmd, 0, stdout=json.dumps({"data": {"message_id": "om_review"}}), stderr="")

    report, path = push_review_request(
        project_dir,
        "rec1",
        role="seo_review",
        profile="hexcal-seo",
        config_path=FEISHU_CONFIG,
        now=datetime(2026, 7, 29, tzinfo=timezone.utc),
        runner=runner,
    )

    item = state.load_state(project_dir)["contentQueue"][0]
    assert report["collection_status"] == "sent"
    assert report["review_thread_id"] == "om_review"
    assert item["status"] == "review"
    assert item["review_thread_id"] == "om_review"
    assert "/open-apis/im/v1/messages" in calls[0][0]
    params, body = payloads[0]
    assert params["uuid"] == "content-review-rec1"
    sent_text = body["content"]
    assert "🧾 ID: rec1" in sent_text
    assert "👀 Draft preview:" in sent_text
    assert "approve" in sent_text
    assert path.name.endswith("-content-review-push.json")


def test_content_review_push_requires_confirm(tmp_path: Path, capsys) -> None:
    project_dir = tmp_path / "project"
    state.init_state("shopify", "Hexcal", "https://www.hexcal.com", project_dir=project_dir)

    assert main(["--project-dir", str(project_dir), "content", "review-push", "rec1", "--role", "seo", "--profile", "hexcal-seo", "--json"]) == 1
    payload = json.loads(capsys.readouterr().out)

    assert payload["ok"] is False
    assert "requires --confirm" in payload["error"]
