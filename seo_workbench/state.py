from __future__ import annotations

import json
import re
from copy import deepcopy
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from seo_workbench_tools.files import atomic_write_text


ROOT = Path(__file__).resolve().parent.parent
PROJECTS_ROOT = Path("projects")
DEFAULT_PROJECT_DIR = Path("projects/default")
DEFAULT_TEMPLATE = ROOT / "templates" / "state.json"
PROJECT_ID_PATTERN = re.compile(r"^[a-z0-9](?:[a-z0-9-]{0,62})$")


PROJECT_DIRS = [
    "context",
    "strategy/keyword-dives",
    "strategy/briefs",
    "content/drafts",
    "audits/raw",
    "audits/rendered",
    "audits/technology",
    "audits/performance",
    "audits/diffs",
]


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, data: dict[str, Any]) -> None:
    atomic_write_text(path, json.dumps(data, ensure_ascii=False, indent=2) + "\n")


def state_path(project_dir: Path = DEFAULT_PROJECT_DIR) -> Path:
    return safe_project_path(project_dir, "state.json")


def safe_project_path(project_dir: Path, relative_path: str | Path) -> Path:
    """Return a path inside a project without following project-local symlinks."""
    relative = Path(relative_path)
    if relative.is_absolute() or ".." in relative.parts:
        raise ValueError(f"project path must be relative and cannot contain '..': {relative}")
    if project_dir.is_symlink():
        raise ValueError(f"project directory cannot be a symlink: {project_dir}")

    project_root = project_dir.resolve(strict=False)
    candidate = project_dir / relative
    current = project_dir
    for part in relative.parts:
        current = current / part
        if current.is_symlink():
            raise ValueError(f"project path cannot contain a symlink: {current}")
    if not candidate.resolve(strict=False).is_relative_to(project_root):
        raise ValueError(f"project path resolves outside {project_dir}: {candidate}")
    return candidate


def project_dir_from_id(project_id: str, projects_root: Path = PROJECTS_ROOT) -> Path:
    if not PROJECT_ID_PATTERN.fullmatch(project_id):
        raise ValueError("project id must use 1-63 lowercase letters, numbers, or hyphens")
    project_dir = projects_root / project_id
    if projects_root.is_symlink():
        raise ValueError(f"projects root cannot be a symlink: {projects_root}")
    if project_dir.is_symlink():
        raise ValueError(f"project directory cannot be a symlink: {project_dir}")
    if not project_dir.resolve(strict=False).is_relative_to(projects_root.resolve(strict=False)):
        raise ValueError(f"project id resolves outside {projects_root}: {project_id}")
    return project_dir


def discover_projects(projects_root: Path = PROJECTS_ROOT) -> list[dict[str, Any]]:
    if projects_root.is_symlink():
        raise ValueError(f"projects root cannot be a symlink: {projects_root}")
    if not projects_root.exists():
        return []
    projects = []
    for directory in sorted(
        (item for item in projects_root.iterdir() if item.is_dir() and not item.is_symlink()), key=lambda item: item.name
    ):
        try:
            path = state_path(directory)
            if not path.is_file():
                continue
            data = read_json(path)
            if not isinstance(data, dict):
                raise ValueError(f"state must be a JSON object: {path}")
            project = data.get("project", {})
            projects.append(
                {
                    "id": directory.name,
                    "path": str(directory),
                    "name": project.get("name", ""),
                    "url": project.get("url", ""),
                    "type": project.get("type", ""),
                    "phase": data.get("currentPhase", ""),
                    "selectable": bool(PROJECT_ID_PATTERN.fullmatch(directory.name)),
                    "valid_state": True,
                }
            )
        except (OSError, ValueError, json.JSONDecodeError) as exc:
            projects.append(
                {
                    "id": directory.name,
                    "path": str(directory),
                    "name": "",
                    "url": "",
                    "type": "",
                    "phase": "",
                    "selectable": bool(PROJECT_ID_PATTERN.fullmatch(directory.name)),
                    "valid_state": False,
                    "error": str(exc),
                }
            )
    return projects


def init_state(
    project_type: str,
    name: str,
    url: str,
    project_dir: Path = DEFAULT_PROJECT_DIR,
    template: Path = DEFAULT_TEMPLATE,
    description: str = "",
    platform: dict[str, str] | None = None,
    force: bool = False,
) -> Path:
    path = state_path(project_dir)
    if path.exists() and not force:
        raise FileExistsError(f"{path} already exists; use --force to overwrite")
    project_paths = [safe_project_path(project_dir, dirname) for dirname in PROJECT_DIRS]

    state = deepcopy(read_json(template))
    state["project"].update(
        {
            "name": name,
            "type": project_type,
            "url": url,
            "createdAt": datetime.now(timezone.utc).isoformat(),
            "description": description,
            "platform": platform,
        }
    )
    if project_type != "shopify-headless":
        for step in state["phases"]["TECHNICAL_AUDIT"]["steps"]:
            if step.get("id") == "headless-precheck":
                step["status"] = "done"
    write_json(path, state)
    for project_path in project_paths:
        project_path.mkdir(parents=True, exist_ok=True)
    return path


def load_state(project_dir: Path = DEFAULT_PROJECT_DIR) -> dict[str, Any]:
    path = state_path(project_dir)
    if not path.exists():
        raise FileNotFoundError(f"{path} not found; run init first")
    return read_json(path)


def save_state(data: dict[str, Any], project_dir: Path = DEFAULT_PROJECT_DIR) -> None:
    write_json(state_path(project_dir), data)


def record_history(data: dict[str, Any], action: str, phase: str = "", step_id: str = "", note: str = "") -> None:
    entry = {
        "at": datetime.now(timezone.utc).isoformat(),
        "action": action,
    }
    if phase:
        entry["phase"] = phase
    if step_id:
        entry["step"] = step_id
    if note:
        entry["note"] = note
    data.setdefault("history", []).append(entry)


def current_step(data: dict[str, Any]) -> tuple[str, dict[str, Any] | None]:
    phase = data.get("currentPhase", "INIT")
    steps = data.get("phases", {}).get(phase, {}).get("steps", [])
    for step in steps:
        if step.get("status") in {"pending", "in_progress"}:
            return phase, step
    return phase, None


def set_phase(data: dict[str, Any], phase: str) -> None:
    if phase not in data.get("phases", {}):
        raise ValueError(f"unknown phase: {phase}")
    data["currentPhase"] = phase
    data["lastAction"] = f"Switched to {phase}"
    data["nextAction"] = "Run next"
    record_history(data, "phase", phase)


def phase_after(data: dict[str, Any], phase: str) -> str | None:
    order = data.get("phaseOrder", [])
    try:
        index = order.index(phase)
    except ValueError:
        return None
    return order[index + 1] if index + 1 < len(order) else None


def advance_if_done(data: dict[str, Any]) -> None:
    phase = data.get("currentPhase", "INIT")
    steps = data.get("phases", {}).get(phase, {}).get("steps", [])
    if steps and all(step.get("status") == "done" for step in steps):
        data["phases"][phase]["status"] = "done"
        if next_phase := phase_after(data, phase):
            data["currentPhase"] = next_phase
            data["nextAction"] = f"Run {next_phase}"
        else:
            data["nextAction"] = "Workflow complete"


def update_step(data: dict[str, Any], action: str, step_id: str | None = None) -> tuple[str, str]:
    phase = data.get("currentPhase", "INIT")
    steps = data.get("phases", {}).get(phase, {}).get("steps", [])
    if not steps:
        raise ValueError(f"{phase} has no steps")

    target = None
    if step_id:
        target = next((step for step in steps if step.get("id") == step_id), None)
        if target is None:
            raise ValueError(f"unknown step in {phase}: {step_id}")
    else:
        _, target = current_step(data)
    if target is None:
        raise ValueError(f"{phase} has no pending step")

    statuses = {"done": "done", "skip": "done", "reset": "pending", "start": "in_progress"}
    if action not in statuses:
        raise ValueError(f"unknown step action: {action}")
    target["status"] = statuses[action]
    if action == "skip":
        target["skipped"] = True
    elif action in {"done", "reset", "start"}:
        target.pop("skipped", None)
    data["lastAction"] = f"{action}: {phase}/{target['id']}"
    data["nextAction"] = "Run next"
    record_history(data, action, phase, target["id"])
    advance_if_done(data)
    return phase, target["id"]


def _self_test() -> None:
    state = {"currentPhase": "INIT", "phases": {"INIT": {"steps": [{"id": "a", "status": "done"}, {"id": "b", "status": "pending"}]}}}
    assert current_step(state) == ("INIT", {"id": "b", "status": "pending"})
    set_phase({"phases": {"X": {}}, "currentPhase": "INIT"}, "X")
    data = {
        "currentPhase": "A",
        "phaseOrder": ["A", "B"],
        "phases": {"A": {"steps": [{"id": "x", "status": "pending"}]}, "B": {"steps": []}},
    }
    assert update_step(data, "done") == ("A", "x")
    assert data["currentPhase"] == "B"
    import tempfile

    with tempfile.TemporaryDirectory() as dirname:
        path = init_state("general", "T", "https://example.com", Path(dirname), force=True)
        initialized = read_json(path)
        precheck = initialized["phases"]["TECHNICAL_AUDIT"]["steps"][0]
        assert precheck["id"] == "headless-precheck"
        assert precheck["status"] == "done"
