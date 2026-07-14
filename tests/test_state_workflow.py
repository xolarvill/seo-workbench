from pathlib import Path

from seo_workbench import state
from seo_workbench.validation import validate_project
from seo_workbench.workflow import DEFAULT_WORKFLOW


def test_non_headless_init_skips_headless_precheck(tmp_path: Path) -> None:
    path = state.init_state("general", "General", "https://example.com", project_dir=tmp_path, force=True)
    data = state.read_json(path)
    precheck = data["phases"]["TECHNICAL_AUDIT"]["steps"][0]
    assert precheck["id"] == "headless-precheck"
    assert precheck["status"] == "done"


def test_step_history_and_skip_marker(tmp_path: Path) -> None:
    path = state.init_state("shopify-headless", "Shop", "https://example.com", project_dir=tmp_path, force=True)
    data = state.read_json(path)
    state.set_phase(data, "TECHNICAL_AUDIT")
    phase, step_id = state.update_step(data, "skip", "headless-precheck")
    assert (phase, step_id) == ("TECHNICAL_AUDIT", "headless-precheck")
    step = data["phases"]["TECHNICAL_AUDIT"]["steps"][0]
    assert step["status"] == "done"
    assert step["skipped"] is True
    assert data["history"][-1]["action"] == "skip"


def test_validate_project_reports_contract(tmp_path: Path) -> None:
    state.init_state("general", "General", "https://example.com", project_dir=tmp_path, force=True)
    result = validate_project(tmp_path, DEFAULT_WORKFLOW)
    assert result["ok"] is True
    assert all(issue["severity"] != "error" for issue in result["issues"])
