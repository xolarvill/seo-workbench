from __future__ import annotations

from pathlib import Path
from typing import Any

from seo_workbench.content_pipeline import validate_queue_item
from seo_workbench import state


VALID_PROJECT_TYPES = {"shopify", "shopify-headless", "general", "existing", ""}


def _issue(severity: str, code: str, message: str, path: str = "") -> dict[str, str]:
    result = {"severity": severity, "code": code, "message": message}
    if path:
        result["path"] = path
    return result


def validate_manifest(data: dict[str, Any], project_dir: Path) -> list[dict[str, str]]:
    issues: list[dict[str, str]] = []
    project = data.get("project")
    if not isinstance(project, dict):
        issues.append(_issue("error", "project.missing", "project must be an object"))
        project = {}

    project_type = project.get("type", "")
    if project_type not in VALID_PROJECT_TYPES:
        issues.append(_issue("error", "project.type", f"unknown project type: {project_type}"))

    for dirname in state.PROJECT_DIRS:
        try:
            runtime_dir = state.safe_project_path(project_dir, dirname)
        except ValueError as exc:
            issues.append(_issue("error", "project_dir.unsafe", str(exc), str(project_dir / dirname)))
            continue
        if not runtime_dir.exists():
            issues.append(_issue("warning", "project_dir.missing", f"missing runtime directory: {runtime_dir}"))

    content_queue = data.get("contentQueue", [])
    if content_queue is None:
        content_queue = []
    if not isinstance(content_queue, list):
        issues.append(_issue("error", "content_queue.shape", "contentQueue must be a list", "contentQueue"))
    else:
        seen_ids: set[str] = set()
        for index, item in enumerate(content_queue):
            location = f"contentQueue[{index}]"
            if not isinstance(item, dict):
                issues.append(_issue("error", "content_queue.item_shape", f"{location} must be an object", location))
                continue
            for error in validate_queue_item(item, location):
                issues.append(_issue("error", "content_queue.item", error, location))
            item_id = item.get("id")
            if isinstance(item_id, str) and item_id in seen_ids:
                issues.append(_issue("error", "content_queue.duplicate", f"duplicate content queue id: {item_id}", location))
            if isinstance(item_id, str):
                seen_ids.add(item_id)
    return issues


def validate_project(project_dir: Path) -> dict[str, Any]:
    issues: list[dict[str, str]] = []
    path = state.state_path(project_dir)
    try:
        data = state.load_state(project_dir)
    except FileNotFoundError:
        issues.append(_issue("error", "project.not_found", f"{path} not found; run init first", str(path)))
        return {"ok": False, "issues": issues}
    except Exception as exc:
        issues.append(_issue("error", "project.invalid_json", str(exc), str(path)))
        return {"ok": False, "issues": issues}

    issues.extend(validate_manifest(data, project_dir))
    return {"ok": not any(issue["severity"] == "error" for issue in issues), "issues": issues}
