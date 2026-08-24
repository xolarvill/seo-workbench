import json
from datetime import datetime, timezone
from pathlib import Path

import pytest

from seo_workbench import state
from seo_workbench import tech_audit as tech_audit_module
from seo_workbench.cli import main
from seo_workbench.tech_audit import TechAuditViewQuery, query_tech_audit
from seo_workbench.tech_issues import list_issue_register, sync_issue_register, update_issue_status


NOW = datetime(2026, 8, 9, 8, 0, tzinfo=timezone.utc)


def _project(tmp_path: Path) -> Path:
    project_dir = tmp_path / "project"
    state.init_state("general", "Example", "https://example.com", project_dir=project_dir)
    return project_dir


def _issue(fingerprint: str = "fp-1") -> dict:
    return {
        "fingerprint": fingerprint,
        "rule_id": "MISSING_H1",
        "title": "Missing H1",
        "severity": "medium",
        "category": "content",
        "url": "https://example.com/page",
        "priority": {"score": 42, "tier": "medium"},
        "remediation_guidance": "Add one visible H1.",
    }


def test_issue_register_tracks_failed_and_passed_verification(tmp_path: Path) -> None:
    project_dir = _project(tmp_path)
    issue = _issue()
    first, _ = sync_issue_register(
        project_dir, [issue], [], run_id="run-1", verification_allowed=False, now=NOW
    )
    assert first["created"] == 1
    assert list_issue_register(project_dir)["issues"][0]["status"] == "open"

    update_issue_status(project_dir, "fp-1", "fixed", owner="theme", note="Template patched", now=NOW)
    failed, _ = sync_issue_register(
        project_dir, [issue], [issue], run_id="run-2", verification_allowed=True, now=NOW
    )
    assert failed["verification_failed"] == 1
    assert list_issue_register(project_dir)["issues"][0]["status"] == "open"

    update_issue_status(project_dir, "fp-1", "fixed", note="Second patch", now=NOW)
    passed, _ = sync_issue_register(
        project_dir, [], [issue], run_id="run-3", verification_allowed=True, now=NOW
    )
    record = list_issue_register(project_dir)["issues"][0]
    assert passed["verified"] == 1
    assert record["status"] == "verified"
    assert record["verification_status"] == "passed"


def test_issue_register_does_not_verify_absence_from_incomparable_run(tmp_path: Path) -> None:
    project_dir = _project(tmp_path)
    issue = _issue()
    sync_issue_register(project_dir, [issue], [], run_id="run-1", verification_allowed=False, now=NOW)
    update_issue_status(project_dir, "fp-1", "fixed", note="Patched", now=NOW)

    sync_issue_register(project_dir, [], [issue], run_id="run-2", verification_allowed=False, now=NOW)

    assert list_issue_register(project_dir)["issues"][0]["status"] == "fixed"


def test_issue_cli_requires_reason_for_accepted_risk(tmp_path: Path, capsys) -> None:
    project_dir = _project(tmp_path)
    issue = _issue()
    sync_issue_register(project_dir, [issue], [], run_id="run-1", verification_allowed=False, now=NOW)

    assert main(
        ["--project-dir", str(project_dir), "tech-audit", "issues", "status", "fp-1", "accepted", "--json"]
    ) == 1
    assert "decision note" in json.loads(capsys.readouterr().out)["error"]
    assert main(
        [
            "--project-dir",
            str(project_dir),
            "tech-audit",
            "issues",
            "status",
            "fp-1",
            "accepted",
            "--owner",
            "seo",
            "--note",
            "Intentional noindex landing page",
            "--json",
        ]
    ) == 0
    assert json.loads(capsys.readouterr().out)["issue"]["owner"] == "seo"


def test_issue_view_includes_operator_status(tmp_path: Path, monkeypatch) -> None:
    project_dir = _project(tmp_path)
    issue = _issue()
    sync_issue_register(project_dir, [issue], [], run_id="run-1", verification_allowed=False, now=NOW)
    update_issue_status(project_dir, "fp-1", "planned", owner="theme", note="Queued", now=NOW)
    monkeypatch.setattr(tech_audit_module, "load_tech_inventory", lambda _project: [])
    monkeypatch.setattr(tech_audit_module, "load_tech_issues", lambda _project: [issue])
    monkeypatch.setattr(tech_audit_module, "_recrawl_pages", lambda _project: {})
    monkeypatch.setattr(tech_audit_module, "_snapshot_summary", lambda _project: {})

    result = query_tech_audit(project_dir, TechAuditViewQuery(dataset="issues"))

    assert result.rows[0]["workflow_status"] == "planned"
    assert result.rows[0]["owner"] == "theme"
