from __future__ import annotations

import json
from copy import deepcopy
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parent.parent
DEFAULT_PROJECT_DIR = Path("projects/default")
DEFAULT_TEMPLATE = ROOT / "templates" / "state.json"


PROJECT_DIRS = [
    "context",
    "strategy/keyword-dives",
    "strategy/briefs",
    "content/drafts",
    "audits/raw",
    "audits/rendered",
]


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def state_path(project_dir: Path = DEFAULT_PROJECT_DIR) -> Path:
    return project_dir / "state.json"


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
    write_json(path, state)
    for dirname in PROJECT_DIRS:
        (project_dir / dirname).mkdir(parents=True, exist_ok=True)
    return path


def load_state(project_dir: Path = DEFAULT_PROJECT_DIR) -> dict[str, Any]:
    path = state_path(project_dir)
    if not path.exists():
        raise FileNotFoundError(f"{path} not found; run init first")
    return read_json(path)


def save_state(data: dict[str, Any], project_dir: Path = DEFAULT_PROJECT_DIR) -> None:
    write_json(state_path(project_dir), data)


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
    data["lastAction"] = f"{action}: {phase}/{target['id']}"
    data["nextAction"] = "Run next"
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
