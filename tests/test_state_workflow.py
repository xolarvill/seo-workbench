import json
from pathlib import Path

import pytest

from seo_workbench import state
from seo_workbench.cli import main
from seo_workbench.validation import validate_project


def test_next_is_not_an_agent_command(capsys) -> None:
    with pytest.raises(SystemExit) as exc:
        main(["next", "--json"])
    assert exc.value.code == 2
    assert "invalid choice" in capsys.readouterr().err


@pytest.mark.parametrize("command", (["status", "--json"], ["phase", "INIT"], ["step", "done"]))
def test_state_commands_are_not_registered(command, capsys) -> None:
    with pytest.raises(SystemExit) as exc:
        main(command)
    assert exc.value.code == 2
    assert "invalid choice" in capsys.readouterr().err


def test_init_creates_project_manifest_without_workflow_fields(tmp_path: Path) -> None:
    path = state.init_state("general", "General", "https://example.com", project_dir=tmp_path, force=True)
    data = state.read_json(path)

    assert path.name == "project.json"
    assert data["project"]["name"] == "General"
    assert data["contentQueue"] == []
    assert not {"currentPhase", "phaseOrder", "phases", "nextAction", "history"} & data.keys()


def test_legacy_state_migrates_to_project_manifest(tmp_path: Path) -> None:
    project_dir = tmp_path / "store"
    project_dir.mkdir()
    legacy = {
        "project": {"name": "Shop", "url": "https://example.com", "type": "shopify"},
        "contentQueue": [{"id": "rec1", "status": "planned"}],
        "reportStars": {"reports/a.md": True},
        "notes": "Launch constraints.",
        "nextAction": "Ship the first article",
        "currentPhase": "INIT",
        "phaseOrder": ["INIT"],
        "phases": {"INIT": {"status": "pending", "steps": []}},
        "history": [{"action": "phase"}],
    }
    (project_dir / "state.json").write_text(json.dumps(legacy), encoding="utf-8")

    data = state.load_state(project_dir)

    assert data["project"]["name"] == "Shop"
    assert data["contentQueue"] == [{"id": "rec1", "status": "planned"}]
    assert data["reportStars"] == {"reports/a.md": True}
    assert "Launch constraints." in data["notes"]
    assert "Ship the first article" in data["notes"]
    assert not {"currentPhase", "phaseOrder", "phases", "history"} & data.keys()
    assert (project_dir / "project.json").is_file()
    assert not (project_dir / "state.json").exists()
    assert (project_dir / ".runtime/legacy-state.json").is_file()


def test_validate_project_reports_contract(tmp_path: Path) -> None:
    state.init_state("general", "General", "https://example.com", project_dir=tmp_path, force=True)
    result = validate_project(tmp_path)
    assert result["ok"] is True
    assert all(issue["severity"] != "error" for issue in result["issues"])


def test_project_id_and_discovery_keep_stores_isolated(tmp_path: Path) -> None:
    projects_root = tmp_path / "projects"
    first = state.project_dir_from_id("store-one", projects_root)
    second = state.project_dir_from_id("store-two", projects_root)
    state.init_state("shopify", "Store One", "https://one.example", project_dir=first)
    state.init_state("shopify-headless", "Store Two", "https://two.example", project_dir=second)

    projects = state.discover_projects(projects_root)
    assert [project["id"] for project in projects] == ["store-one", "store-two"]
    assert projects[0]["name"] == "Store One"
    assert "phase" not in projects[0]
    assert state.state_path(first) != state.state_path(second)
    assert (first / "audits/diffs").is_dir()
    assert (first / "audits/publish").is_dir()
    assert (first / "audits/runs").is_dir()
    assert (first / "content/reports").is_dir()


def test_content_queue_validation_rejects_invalid_status(tmp_path: Path) -> None:
    project_path = state.init_state("shopify", "Shop", "https://example.com", project_dir=tmp_path)
    data = state.read_json(project_path)
    data["contentQueue"] = [{"id": "rec1", "status": "unknown"}]
    state.write_json(project_path, data)

    result = validate_project(tmp_path)

    assert result["ok"] is False
    assert any(issue["code"] == "content_queue.item" for issue in result["issues"])


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
    assert "phase" not in payload["projects"][0]


def test_cli_rejects_unsafe_project_id_as_json(capsys) -> None:
    assert main(["--project", "../store", "validate", "--json"]) == 1
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
    captured = {}

    def fake_collect(*args, **kwargs):
        captured.update(kwargs)
        return report_path

    monkeypatch.setattr("seo_workbench.cli.collect_from_state", fake_collect)

    assert main(["--project-dir", str(project_dir), "evidence", "--json"]) == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["ok"] is True
    assert payload["collection_status"] == "partial"
    assert payload["warning_count"] == 1
    assert captured["crawl_limit"] == 5


def test_evidence_surfaces_google_configuration_states_without_failing_raw(tmp_path: Path, monkeypatch) -> None:
    from seo_workbench_tools import crux_probe, workflow_evidence

    project_dir = tmp_path / "project"
    state.init_state("shopify", "Shop", "https://example.com", project_dir=project_dir)

    def base_bundle(*args, **kwargs):
        return {
            "schema_version": "1.0",
            "collector_version": "0.6.0",
            "seed_url": "https://example.com",
            "pages": [{"url": "https://example.com", "status": 200}],
            "site": {},
            "errors": [],
            "warnings": [],
            "source_confidence": {"performance_field": 0.0, "search_console": 0.0},
        }

    monkeypatch.setattr(workflow_evidence, "collect", base_bundle)
    monkeypatch.setattr(crux_probe, "collect", lambda *args, **kwargs: (_ for _ in ()).throw(RuntimeError("key missing")))
    path = workflow_evidence.collect_from_state(
        project_dir / "project.json",
        15,
        10,
        project_dir / "audits/raw",
        crux=True,
        gsc=True,
    )
    report = json.loads(path.read_text())
    assert report["collection_status"] == "ok"
    assert report["crux_audit"]["collection_status"] == "needs_config"
    assert report["gsc_audit"]["collection_status"] == "needs_auth"


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


def test_project_file_symlink_is_rejected(tmp_path: Path) -> None:
    project_dir = tmp_path / "projects/store"
    project_dir.mkdir(parents=True)
    outside = tmp_path / "outside-project.json"
    outside.write_text("{}", encoding="utf-8")
    (project_dir / "project.json").symlink_to(outside)
    try:
        state.load_state(project_dir)
    except ValueError as exc:
        assert "symlink" in str(exc)
    else:
        raise AssertionError("expected symlinked project file to fail")


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
    assert main(["validate", "--json"]) == 1
    payload = json.loads(capsys.readouterr().out)
    assert payload["ok"] is False
    assert "projects root" in payload["error"]
