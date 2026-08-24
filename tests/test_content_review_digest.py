import json
import subprocess
from datetime import datetime, timezone
from pathlib import Path

from seo_workbench import state
from seo_workbench.cli import main
from seo_workbench.content_review_digest import generate_review_digest


FEISHU_CONFIG = Path(__file__).resolve().parents[1] / "templates/hexcal-feishu-profile.json"


def test_generate_review_digest_reads_feishu_thread_without_mutating_state(tmp_path: Path) -> None:
    project_dir = tmp_path / "project"
    state.init_state("shopify", "Hexcal", "https://www.hexcal.com", project_dir=project_dir)
    data = state.load_state(project_dir)
    data["contentQueue"] = [
        {"id": "rec1", "status": "review", "title": "Draft", "review_thread_id": "om_1"},
        {"id": "rec2", "status": "approved", "title": "Done", "review_thread_id": "om_2"},
    ]
    state.save_state(data, project_dir)
    calls = []

    def runner(cmd, **kwargs):
        calls.append((cmd, kwargs))
        replies = [
            {"message_id": "root_bot", "sender": {"sender_id": {"app_id": "bot_1"}}, "body": {"content": json.dumps({"text": "summary"})}},
            {"message_id": "reply_1", "sender": {"sender_id": {"open_id": "ou_1"}}, "body": {"content": json.dumps({"text": "approve"})}},
        ]
        return subprocess.CompletedProcess(cmd, 0, stdout=json.dumps(replies), stderr="")

    report, path = generate_review_digest(
        project_dir,
        profile="hexcal-seo",
        config_path=FEISHU_CONFIG,
        bot_id="bot_1",
        now=datetime(2026, 7, 29, tzinfo=timezone.utc),
        runner=runner,
    )

    assert report["collection_status"] == "draft_ready"
    assert report["state_mutated"] is False
    assert report["items"][0]["suggested_status"] == "approved"
    assert report["items"][0]["confirmation_command"] == "content status rec1 approved --note 'Feishu review: approved'"
    assert report["items"][0]["reply_count"] == 1
    assert "replies" not in report["items"][0]
    assert "review_thread_id" not in report["items"][0]
    assert "suggested_note" not in report["items"][0]
    assert state.load_state(project_dir)["contentQueue"][0]["status"] == "review"
    assert "+threads-messages-list" in calls[0][0]
    assert path == project_dir / "content/reports/2026-07-29-review-digest.md"
    public_digest = path.read_text(encoding="utf-8")
    assert "`content status rec1 approved --note 'Feishu review: approved'`" in public_digest
    assert "om_1" not in public_digest
    assert "ou_1" not in public_digest
    private_run = project_dir / report["run_record_path"]
    assert report["run_record_path"].startswith(".runtime/feishu/review-digests/")
    assert private_run.is_file()
    assert private_run.stat().st_mode & 0o777 == 0o600
    assert "ou_1" in private_run.read_text(encoding="utf-8")


def test_content_review_digest_cli_outputs_json(tmp_path: Path, capsys, monkeypatch) -> None:
    project_dir = tmp_path / "project"
    state.init_state("shopify", "Hexcal", "https://www.hexcal.com", project_dir=project_dir)

    def fake_digest(project_dir, **kwargs):
        return {"collection_status": "no_candidates", "state_mutated": False, "items": []}, project_dir / "content/reports/review.md"

    monkeypatch.setattr("seo_workbench.cli.generate_review_digest", fake_digest)

    assert main(["--project-dir", str(project_dir), "content", "review-digest", "--profile", "hexcal-seo", "--json"]) == 0
    payload = json.loads(capsys.readouterr().out)

    assert payload["ok"] is True
    assert payload["state_mutated"] is False
