from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from seo_workbench import state
from seo_workbench_tools.files import atomic_write_text


VALID_CONTENT_STATUSES = {
    "planned",
    "ready_to_write",
    "drafting",
    "review",
    "revision_requested",
    "blocked",
    "approved",
    "scheduled",
    "submitted_for_indexing",
    "indexed",
    "indexing_issue",
    "dropped",
}


def normalize_status(status: str, aliases: dict[str, str] | None = None) -> str:
    value = (status or "").strip()
    return (aliases or {}).get(value, value)


def set_queue_status(data: dict[str, Any], item_id: str, status: str, *, note: str = "") -> dict[str, Any]:
    normalized = normalize_status(status)
    if normalized not in VALID_CONTENT_STATUSES:
        raise ValueError(f"invalid content status: {status}")
    queue = data.get("contentQueue", [])
    if not isinstance(queue, list):
        raise ValueError("state.contentQueue must be a list")
    for item in queue:
        if isinstance(item, dict) and item.get("id") == item_id:
            item["status"] = normalized
            if note:
                item["note"] = note
            return item
    raise ValueError(f"content queue item not found: {item_id}")


def sync_pipeline_status(project_dir: Path, item_id: str, item: dict[str, Any]) -> bool:
    path = state.safe_project_path(project_dir, "content/blog-pipeline.jsonl")
    if not path.exists():
        return False
    rows = []
    synced = False
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        row = json.loads(line)
        if row.get("id") == item_id:
            row["status"] = item["status"]
            if item.get("note"):
                row["note"] = item["note"]
            synced = True
        rows.append(row)
    if synced:
        atomic_write_text(path, "".join(json.dumps(row, ensure_ascii=False) + "\n" for row in rows))
    return synced


def validate_queue_item(item: dict[str, Any], location: str) -> list[str]:
    errors: list[str] = []
    item_id = item.get("id")
    if not isinstance(item_id, str) or not item_id.strip():
        errors.append(f"{location}.id must be a non-empty string")
    status = item.get("status")
    if status not in VALID_CONTENT_STATUSES:
        errors.append(f"{location}.status has invalid status: {status}")
    for key in ("slug", "title", "target_keyword"):
        if key in item and item[key] is not None and not isinstance(item[key], str):
            errors.append(f"{location}.{key} must be a string when present")
    return errors
