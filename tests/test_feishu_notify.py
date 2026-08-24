import json
import subprocess
from pathlib import Path

from seo_workbench import cli as cli_module
from seo_workbench import state
from seo_workbench.cli import main
from seo_workbench.feishu_notify import send_report_via_feishu_gateway


FEISHU_CONFIG = Path(__file__).resolve().parents[1] / "templates/hexcal-feishu-profile.json"


def test_send_report_via_feishu_gateway_writes_private_run_record(tmp_path: Path) -> None:
    project_dir = tmp_path / "project"
    state.init_state("shopify", "Hexcal", "https://www.hexcal.com", project_dir=project_dir)
    report = project_dir / "content/reports/daily.md"
    report.write_text("# Daily\n\n- one\n", encoding="utf-8")
    calls = []
    bodies = []

    def runner(cmd, **kwargs):
        calls.append((cmd, kwargs))
        bodies.append(json.loads((Path(kwargs["cwd"]) / "body.json").read_text(encoding="utf-8")))
        return subprocess.CompletedProcess(cmd, 0, stdout=json.dumps({"data": {"message_id": "om_1"}}), stderr="")

    result, path = send_report_via_feishu_gateway(
        project_dir,
        Path("content/reports/daily.md"),
        title="Daily",
        role="seo_review",
        profile="hexcal-seo",
        config_path=FEISHU_CONFIG,
        runner=runner,
    )

    assert result["notification_sent"] is True
    assert result["message_id"] == "om_1"
    assert "gateway_response" not in result
    assert path.stat().st_mode & 0o777 == 0o600
    assert calls[0][0][:3] == ["lark-cli", "--profile", "hexcal-seo"]
    assert bodies[0]["receive_id"] == "oc_replace_with_review_chat_id"


def test_send_report_accepts_project_prefixed_path_and_marks_sent(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)
    project_dir = Path("projects/hexcal")
    state.init_state("shopify", "Hexcal", "https://www.hexcal.com", project_dir=project_dir)
    report = project_dir / "content/reports/daily.md"
    report.write_text("# Daily\n\nStatus: draft only, no notification sent.\n\n- one\n", encoding="utf-8")
    calls = []
    bodies = []

    def runner(cmd, **kwargs):
        calls.append((cmd, kwargs))
        bodies.append(json.loads((Path(kwargs["cwd"]) / "body.json").read_text(encoding="utf-8")))
        return subprocess.CompletedProcess(cmd, 0, stdout=json.dumps({"data": {"message_id": "om_1"}}), stderr="")

    result, _ = send_report_via_feishu_gateway(
        project_dir,
        Path("projects/hexcal/content/reports/daily.md"),
        title="Daily",
        role="seo_review",
        profile="hexcal-seo",
        config_path=FEISHU_CONFIG,
        runner=runner,
    )

    sent_text = bodies[0]["content"]
    assert result["report_path"] == "content/reports/daily.md"
    assert "✅ Status: notification sent via Feishu." in sent_text
    assert "📌 Daily" in sent_text
    assert "  • one" in sent_text
    assert "draft only, no notification sent" not in sent_text


def test_content_notify_report_requires_confirm(tmp_path: Path, capsys) -> None:
    project_dir = tmp_path / "project"
    state.init_state("shopify", "Hexcal", "https://www.hexcal.com", project_dir=project_dir)
    (project_dir / "content/reports/daily.md").write_text("# Daily\n", encoding="utf-8")

    assert main(["--project-dir", str(project_dir), "content", "notify-report", "content/reports/daily.md", "--role", "seo", "--title", "Daily", "--profile", "hexcal-seo", "--json"]) == 1
    assert "requires --confirm" in json.loads(capsys.readouterr().out)["error"]


def test_content_notify_report_cli_outputs_json(tmp_path: Path, capsys, monkeypatch) -> None:
    project_dir = tmp_path / "project"
    state.init_state("shopify", "Hexcal", "https://www.hexcal.com", project_dir=project_dir)

    def fake_send(project_dir, report_path, **kwargs):
        return {"collection_status": "sent", "notification_sent": True, "report_path": str(report_path)}, project_dir / "audits/runs/sent.json"

    monkeypatch.setattr(cli_module, "send_report_via_feishu_gateway", fake_send)

    assert main(["--project-dir", str(project_dir), "content", "notify-report", "content/reports/daily.md", "--role", "seo", "--title", "Daily", "--profile", "hexcal-seo", "--confirm", "--json"]) == 0
    payload = json.loads(capsys.readouterr().out)

    assert payload["ok"] is True
    assert payload["notification_sent"] is True
