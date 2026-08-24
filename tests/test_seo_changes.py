import json
from datetime import datetime, timezone
from pathlib import Path

import pytest

from seo_workbench import state
from seo_workbench.cli import main
from seo_workbench.seo_changes import list_changes, record_change, update_change_status


NOW = datetime(2026, 8, 9, 8, 0, tzinfo=timezone.utc)


def _project(tmp_path: Path) -> Path:
    project_dir = tmp_path / "project"
    state.init_state("shopify", "Example", "https://www.example.com", project_dir=project_dir)
    return project_dir


def test_change_ledger_records_due_change_and_status_history(tmp_path: Path) -> None:
    project_dir = _project(tmp_path)

    change = record_change(
        project_dir,
        urls=["https://www.example.com/products/desk/?utm_source=test#hero"],
        change_type="metadata",
        hypothesis="A clearer title will improve qualified CTR.",
        metrics=["ctr", "clicks", "ctr"],
        changed_at="2026-08-01",
        review_after_days=7,
        now=NOW,
    )

    assert change["urls"] == ["https://www.example.com/products/desk"]
    assert change["expected_metrics"] == ["ctr", "clicks"]
    assert change["review_date"] == "2026-08-08"
    assert list_changes(project_dir, due=True, as_of="2026-08-07")["count"] == 0
    assert list_changes(project_dir, due=True, as_of="2026-08-08")["count"] == 1

    reviewed = update_change_status(project_dir, change["id"], "reviewed", note="28-day result checked", now=NOW)
    assert reviewed["status"] == "reviewed"
    assert reviewed["updates"][-1]["previous_status"] == "shipped"
    assert list_changes(project_dir, due=True, as_of="2026-08-09")["count"] == 0


def test_change_ledger_rejects_external_and_duplicate_changes(tmp_path: Path) -> None:
    project_dir = _project(tmp_path)
    kwargs = {
        "change_type": "technical",
        "hypothesis": "Stable canonicals will improve index consistency.",
        "metrics": ["indexation"],
        "changed_at": "2026-08-01",
        "now": NOW,
    }

    with pytest.raises(ValueError, match="outside the project site family"):
        record_change(project_dir, urls=["https://competitor.example/page"], **kwargs)

    record_change(project_dir, urls=["https://www.example.com/page"], **kwargs)
    with pytest.raises(ValueError, match="already exists"):
        record_change(project_dir, urls=["https://www.example.com/page"], **kwargs)


def test_changes_cli_adds_and_lists_due_records(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    project_dir = _project(tmp_path)

    assert main(
        [
            "--project-dir",
            str(project_dir),
            "changes",
            "add",
            "--url",
            "https://www.example.com/collections/desks",
            "--type",
            "content",
            "--hypothesis",
            "Adding fit guidance will increase qualified clicks.",
            "--metric",
            "clicks",
            "--changed-at",
            "2026-07-01",
            "--review-date",
            "2026-07-29",
            "--json",
        ]
    ) == 0
    added = json.loads(capsys.readouterr().out)
    assert added["change"]["status"] == "shipped"

    assert main(
        ["--project-dir", str(project_dir), "changes", "list", "--due", "--as-of", "2026-07-29", "--json"]
    ) == 0
    listed = json.loads(capsys.readouterr().out)
    assert listed["count"] == 1
    assert listed["changes"][0]["id"] == added["change"]["id"]
