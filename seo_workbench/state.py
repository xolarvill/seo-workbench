from __future__ import annotations

import json
import re
from copy import deepcopy
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, TypeVar

from seo_workbench.locks import project_lock
from seo_workbench_tools.files import atomic_write_text


ROOT = Path(__file__).resolve().parent.parent
PROJECTS_ROOT = Path("projects")
DEFAULT_PROJECT_DIR = Path("projects/default")
DEFAULT_TEMPLATE = ROOT / "templates" / "project.json"
PROJECT_ID_PATTERN = re.compile(r"^[a-z0-9](?:[a-z0-9-]{0,62})$")
MutationResult = TypeVar("MutationResult")


PROJECT_DIRS = [
    "context",
    "strategy/keyword-dives",
    "strategy/briefs",
    "content/drafts",
    "content/assets",
    "content/reports",
    "reports",
    "audits/raw",
    "audits/rendered",
    "audits/browser",
    "audits/technology",
    "audits/performance",
    "audits/crux",
    "audits/gsc",
    "audits/gsc/search-analytics",
    "audits/gsc/inspection",
    "audits/gsc/sitemaps",
    "audits/tech-audit",
    "audits/tech-audit/runs",
    "audits/diffs",
    "audits/content-qc",
    "audits/publish",
    "audits/runs",
]


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, data: dict[str, Any]) -> None:
    atomic_write_text(path, json.dumps(data, ensure_ascii=False, indent=2) + "\n")


def state_path(project_dir: Path = DEFAULT_PROJECT_DIR) -> Path:
    return safe_project_path(project_dir, "project.json")


def legacy_state_path(project_dir: Path = DEFAULT_PROJECT_DIR) -> Path:
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


def _backup_legacy_state(project_dir: Path) -> None:
    legacy = legacy_state_path(project_dir)
    if not legacy.is_file():
        return
    backup = safe_project_path(project_dir, ".runtime/legacy-state.json")
    backup.parent.mkdir(parents=True, exist_ok=True)
    try:
        legacy.replace(backup)
    except OSError:
        pass


def migrate_legacy_state(project_dir: Path) -> dict[str, Any] | None:
    """Convert the retired workflow state file into the project manifest.

    Keeps only project metadata, the content queue, report stars, and notes. The
    legacy file is preserved under .runtime/ instead of being destroyed.
    """
    legacy = legacy_state_path(project_dir)
    if not legacy.is_file():
        return None
    data = read_json(legacy)
    if not isinstance(data, dict):
        raise ValueError(f"legacy state must be a JSON object: {legacy}")
    project = data.get("project")
    queue = data.get("contentQueue")
    notes = str(data.get("notes") or "").strip()
    next_action = str(data.get("nextAction") or "").strip()
    if next_action:
        notes = f"{notes}\n\nLast recorded next action: {next_action}".strip()
    manifest: dict[str, Any] = {
        "project": project if isinstance(project, dict) else {},
        "contentQueue": queue if isinstance(queue, list) else [],
        "notes": notes,
    }
    if isinstance(data.get("reportStars"), dict):
        manifest["reportStars"] = data["reportStars"]
    write_json(safe_project_path(project_dir, "project.json"), manifest)
    _backup_legacy_state(project_dir)
    return manifest


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
            data = load_state(directory)
            project = data.get("project", {})
            projects.append(
                {
                    "id": directory.name,
                    "path": str(directory),
                    "name": project.get("name", ""),
                    "url": project.get("url", ""),
                    "type": project.get("type", ""),
                    "selectable": bool(PROJECT_ID_PATTERN.fullmatch(directory.name)),
                    "valid_state": True,
                }
            )
        except FileNotFoundError:
            continue
        except (OSError, ValueError, json.JSONDecodeError) as exc:
            projects.append(
                {
                    "id": directory.name,
                    "path": str(directory),
                    "name": "",
                    "url": "",
                    "type": "",
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
    if (path.exists() or legacy_state_path(project_dir).is_file()) and not force:
        raise FileExistsError(f"{path} already exists; use --force to overwrite")
    project_paths = [safe_project_path(project_dir, dirname) for dirname in PROJECT_DIRS]

    data = deepcopy(read_json(template))
    data["project"].update(
        {
            "name": name,
            "type": project_type,
            "url": url,
            "createdAt": datetime.now(timezone.utc).isoformat(),
            "description": description,
            "platform": platform,
        }
    )
    write_json(path, data)
    _backup_legacy_state(project_dir)
    for project_path in project_paths:
        project_path.mkdir(parents=True, exist_ok=True)
    return path


def load_state(project_dir: Path = DEFAULT_PROJECT_DIR) -> dict[str, Any]:
    path = state_path(project_dir)
    if path.exists():
        return read_json(path)
    migrated = migrate_legacy_state(project_dir)
    if migrated is not None:
        return migrated
    raise FileNotFoundError(f"{path} not found; run init first")


def save_state(data: dict[str, Any], project_dir: Path = DEFAULT_PROJECT_DIR) -> None:
    write_json(state_path(project_dir), data)


def mutate_state(
    project_dir: Path,
    mutation: Callable[[dict[str, Any]], MutationResult],
    *,
    timeout: float = 30,
) -> MutationResult:
    """Serialize a complete read, mutate, write project-manifest transaction."""
    with project_lock(project_dir, timeout=timeout):
        data = load_state(project_dir)
        result = mutation(data)
        save_state(data, project_dir)
        return result
