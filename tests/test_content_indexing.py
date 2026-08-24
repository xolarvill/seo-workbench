import json
from datetime import datetime, timezone
from pathlib import Path

import pytest

from seo_workbench import cli as cli_module
from seo_workbench import state
from seo_workbench.cli import main
from seo_workbench.content_indexing import (
    apply_gsc_index_status,
    list_due_for_indexing,
    mark_index_notifications_sent,
    pending_index_notifications,
    submit_due_for_indexing,
)


def seed_project(project_dir: Path) -> None:
    state.init_state("shopify", "Store", "https://example.com", project_dir=project_dir)
    data = state.load_state(project_dir)
    data["contentQueue"] = [
        {
            "id": "rec1",
            "status": "scheduled",
            "title": "Indexed",
            "slug": "indexed",
            "live_url": "https://example.com/blogs/articles/indexed",
            "scheduled_at": "2026-07-20T00:00:00Z",
        },
        {
            "id": "rec2",
            "status": "scheduled",
            "title": "Pending",
            "slug": "pending",
            "live_url": "https://example.com/blogs/articles/pending",
            "scheduled_at": "2026-07-01T00:00:00Z",
        },
    ]
    state.save_state(data, project_dir)
    (project_dir / "content/blog-pipeline.jsonl").write_text(
        "\n".join(
            json.dumps(item, ensure_ascii=False)
            for item in data["contentQueue"]
        )
        + "\n",
        encoding="utf-8",
    )


def test_list_due_for_indexing_returns_scheduled_live_urls(tmp_path: Path) -> None:
    project_dir = tmp_path / "project"
    seed_project(project_dir)

    report = list_due_for_indexing(project_dir, now=datetime(2026, 7, 21, tzinfo=timezone.utc))

    assert report["count"] == 2
    assert report["urls"] == [
        "https://example.com/blogs/articles/indexed",
        "https://example.com/blogs/articles/pending",
    ]


def test_apply_gsc_index_status_updates_queue_and_pipeline(tmp_path: Path) -> None:
    project_dir = tmp_path / "project"
    seed_project(project_dir)
    inspection = project_dir / "inspection.json"
    inspection.write_text(
        json.dumps(
            {
                "inspections": [
                    {
                        "url": "https://example.com/blogs/articles/indexed",
                        "inspection_result": {"indexStatusResult": {"verdict": "PASS", "coverageState": "Submitted and indexed"}},
                    },
                    {
                        "url": "https://example.com/blogs/articles/pending",
                        "inspection_result": {"indexStatusResult": {"verdict": "NEUTRAL", "coverageState": "Crawled - currently not indexed"}},
                    },
                ]
            }
        ),
        encoding="utf-8",
    )

    report, path = apply_gsc_index_status(
        project_dir,
        inspection_path=inspection,
        now=datetime(2026, 7, 29, tzinfo=timezone.utc),
    )

    assert report["changed_count"] == 2
    assert path.name.endswith("-content-index-status.json")
    queue = state.load_state(project_dir)["contentQueue"]
    assert queue[0]["status"] == "indexed"
    assert queue[1]["status"] == "indexing_issue"
    pipeline = [json.loads(line) for line in (project_dir / "content/blog-pipeline.jsonl").read_text(encoding="utf-8").splitlines()]
    assert pipeline[0]["status"] == "indexed"
    assert pipeline[1]["status"] == "indexing_issue"

    changes = pending_index_notifications(project_dir, report["changes"])
    assert [change["id"] for change in changes] == ["rec1"]
    mark_index_notifications_sent(project_dir, ["rec1"], now=datetime(2026, 7, 29, tzinfo=timezone.utc))
    assert pending_index_notifications(project_dir, report["changes"]) == []
    assert state.load_state(project_dir)["contentQueue"][0]["index_notification_sent_at"] == "2026-07-29T00:00:00+00:00"


def test_submit_due_for_indexing_rejects_ordinary_blog_articles(tmp_path: Path) -> None:
    project_dir = tmp_path / "project"
    seed_project(project_dir)

    with pytest.raises(ValueError, match="does not support ordinary Blog articles"):
        submit_due_for_indexing(project_dir)

    assert all(item["status"] == "scheduled" for item in state.load_state(project_dir)["contentQueue"])


def test_content_index_queue_cli_outputs_urls(tmp_path: Path, capsys) -> None:
    project_dir = tmp_path / "project"
    seed_project(project_dir)

    assert main(["--project-dir", str(project_dir), "content", "index-queue", "--json"]) == 0
    payload = json.loads(capsys.readouterr().out)

    assert payload["ok"] is True
    assert payload["count"] >= 1


def test_content_index_submit_requires_confirm(tmp_path: Path, capsys) -> None:
    project_dir = tmp_path / "project"
    seed_project(project_dir)

    assert main(["--project-dir", str(project_dir), "content", "index-submit", "--json"]) == 1
    payload = json.loads(capsys.readouterr().out)

    assert payload["ok"] is False
    assert "requires --confirm" in payload["error"]

    assert main(["--project-dir", str(project_dir), "content", "index-submit", "--confirm", "--json"]) == 1
    payload = json.loads(capsys.readouterr().out)
    assert "does not support ordinary Blog articles" in payload["error"]


def test_content_index_status_retries_feishu_until_index_notification_is_recorded(tmp_path: Path, capsys, monkeypatch) -> None:
    project_dir = tmp_path / "project"
    state.init_state("shopify", "Store", "https://example.com", project_dir=project_dir)
    data = state.load_state(project_dir)
    data["contentQueue"] = [{"id": "rec1", "status": "indexed"}]
    state.save_state(data, project_dir)
    index_path = project_dir / "audits/runs/index-status.json"
    index_path.write_text("{}", encoding="utf-8")
    report_path = project_dir / "content/reports/daily.md"
    report_path.write_text("# Daily\n", encoding="utf-8")
    sent: list[dict] = []

    monkeypatch.setattr(
        cli_module,
        "apply_gsc_index_status",
        lambda *_args, **_kwargs: (
            {
                "collection_status": "ok",
                "changes": [{"id": "rec1", "previous_status": "scheduled", "status": "indexed"}],
                "notification_sent": False,
            },
            index_path,
        ),
    )
    monkeypatch.setattr(cli_module, "generate_content_report", lambda *_args, **_kwargs: ({}, report_path))

    def fake_send(*_args, **kwargs):
        sent.append(kwargs)
        if len(sent) == 1:
            raise RuntimeError("Feishu unavailable")
        return {"notification_sent": True}, project_dir / "audits/runs/feishu.json"

    monkeypatch.setattr(cli_module, "send_report_via_feishu_gateway", fake_send)

    assert main(["--project-dir", str(project_dir), "content", "index-status", "--notify-role", "seo", "--json"]) == 1
    assert "require --confirm" in json.loads(capsys.readouterr().out)["error"]
    assert main(
        ["--project-dir", str(project_dir), "content", "index-status", "--notify-role", "seo", "--profile", "hexcal-seo", "--confirm", "--json"]
    ) == 1
    assert "Feishu unavailable" in json.loads(capsys.readouterr().out)["error"]
    assert not state.load_state(project_dir)["contentQueue"][0].get("index_notification_sent_at")
    assert main(
        ["--project-dir", str(project_dir), "content", "index-status", "--notify-role", "seo", "--profile", "hexcal-seo", "--confirm", "--json"]
    ) == 0
    payload = json.loads(capsys.readouterr().out)

    assert payload["notification_sent"] is True
    assert sent[1]["role"] == "seo"
    assert sent[1]["title"] == "BLOG indexed: 1 new"
    assert state.load_state(project_dir)["contentQueue"][0]["index_notification_sent_at"]

    assert main(
        ["--project-dir", str(project_dir), "content", "index-status", "--notify-role", "seo", "--profile", "hexcal-seo", "--confirm", "--json"]
    ) == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["notification_reason"] == "no newly indexed items"
    assert len(sent) == 2
