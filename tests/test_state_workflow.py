import json
from pathlib import Path

from seo_workbench import state
from seo_workbench.cli import main
from seo_workbench.validation import validate_project
from seo_workbench.workflow import DEFAULT_WORKFLOW, load_workflow, next_contract


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


def test_init_steps_declare_skill_context_and_output(tmp_path: Path) -> None:
    workflow = load_workflow(DEFAULT_WORKFLOW)
    brand = next_contract(workflow, "INIT", {"id": "config-brand-voice", "label": "Brand"}, tmp_path)
    keywords = next_contract(workflow, "INIT", {"id": "config-target-keywords", "label": "Keywords"}, tmp_path)

    assert brand["skill"] == "skills/project-context/SKILL.md"
    assert brand["output"] == str(tmp_path / "context/brand-voice.md")
    assert str(tmp_path / "audits/technology/latest.json") in brand["context"]
    assert keywords["skill"] == "skills/project-context/SKILL.md"
    assert keywords["output"] == str(tmp_path / "context/target-keywords.md")
    assert str(tmp_path / "context/brand-voice.md") in keywords["context"]


def test_project_id_and_discovery_keep_stores_isolated(tmp_path: Path) -> None:
    projects_root = tmp_path / "projects"
    first = state.project_dir_from_id("store-one", projects_root)
    second = state.project_dir_from_id("store-two", projects_root)
    state.init_state("shopify", "Store One", "https://one.example", project_dir=first)
    state.init_state("shopify-headless", "Store Two", "https://two.example", project_dir=second)

    projects = state.discover_projects(projects_root)
    assert [project["id"] for project in projects] == ["store-one", "store-two"]
    assert projects[0]["name"] == "Store One"
    assert state.state_path(first) != state.state_path(second)
    assert (first / "audits/diffs").is_dir()


def test_project_id_rejects_path_traversal() -> None:
    for project_id in ("../store", "Store", "store_name", "a" * 64):
        try:
            state.project_dir_from_id(project_id)
        except ValueError:
            pass
        else:
            raise AssertionError(f"expected invalid project id: {project_id}")


def test_cli_initializes_and_lists_projects_by_id(tmp_path: Path, monkeypatch, capsys) -> None:
    monkeypatch.chdir(tmp_path)
    assert main(["--project", "store-one", "init", "shopify", "--name", "One", "--url", "https://one.example"]) == 0
    capsys.readouterr()
    assert main(["projects", "--json"]) == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["count"] == 1
    assert payload["projects"][0]["id"] == "store-one"


def test_cli_rejects_unsafe_project_id_as_json(capsys) -> None:
    assert main(["--project", "../store", "status", "--json"]) == 1
    payload = json.loads(capsys.readouterr().out)
    assert payload["ok"] is False


def test_evidence_json_surfaces_partial_collection_status(tmp_path: Path, monkeypatch, capsys) -> None:
    project_dir = tmp_path / "project"
    state.init_state("shopify", "Shop", "https://example.com", project_dir=project_dir)
    report_path = project_dir / "audits/raw/evidence.json"
    report_path.write_text(
        json.dumps({"collection_status": "partial", "errors": [], "warnings": [{"scope": "page"}]}),
        encoding="utf-8",
    )
    monkeypatch.setattr("seo_workbench.cli.collect_from_state", lambda *args, **kwargs: report_path)

    assert main(["--project-dir", str(project_dir), "evidence", "--json"]) == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["ok"] is True
    assert payload["collection_status"] == "partial"
    assert payload["warning_count"] == 1


def test_project_id_rejects_symlink_escape(tmp_path: Path) -> None:
    projects_root = tmp_path / "projects"
    outside = tmp_path / "outside"
    projects_root.mkdir()
    outside.mkdir()
    (projects_root / "store").symlink_to(outside, target_is_directory=True)
    try:
        state.project_dir_from_id("store", projects_root)
    except ValueError as exc:
        assert "symlink" in str(exc)
    else:
        raise AssertionError("expected symlink escape to fail")


def test_project_id_rejects_same_root_symlink_alias(tmp_path: Path) -> None:
    projects_root = tmp_path / "projects"
    victim = projects_root / "victim"
    state.init_state("shopify", "Victim", "https://victim.example", project_dir=victim)
    (projects_root / "alias").symlink_to(victim, target_is_directory=True)
    try:
        state.project_dir_from_id("alias", projects_root)
    except ValueError as exc:
        assert "symlink" in str(exc)
    else:
        raise AssertionError("expected same-root symlink alias to fail")


def test_state_file_symlink_is_rejected(tmp_path: Path) -> None:
    project_dir = tmp_path / "projects/store"
    project_dir.mkdir(parents=True)
    outside = tmp_path / "outside-state.json"
    outside.write_text("{}", encoding="utf-8")
    (project_dir / "state.json").symlink_to(outside)
    try:
        state.load_state(project_dir)
    except ValueError as exc:
        assert "symlink" in str(exc)
    else:
        raise AssertionError("expected symlinked state file to fail")


def test_discovery_marks_invalid_directory_id_non_selectable(tmp_path: Path) -> None:
    projects_root = tmp_path / "projects"
    state.init_state("shopify", "Store", "https://example.com", project_dir=projects_root / "Store")
    projects = state.discover_projects(projects_root)
    assert projects[0]["id"] == "Store"
    assert projects[0]["selectable"] is False


def test_cli_default_project_rejects_symlinked_projects_root(tmp_path: Path, monkeypatch, capsys) -> None:
    outside = tmp_path / "outside"
    outside.mkdir()
    monkeypatch.chdir(tmp_path)
    (tmp_path / "projects").symlink_to(outside, target_is_directory=True)
    assert main(["status", "--json"]) == 1
    payload = json.loads(capsys.readouterr().out)
    assert payload["ok"] is False
    assert "projects root" in payload["error"]
