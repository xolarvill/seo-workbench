"""Project-scoped product anchors used by content briefs and asset matching."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from seo_workbench import state


ANCHORS_PATH = "context/product-anchors.json"


def load_product_anchors(project_dir: Path) -> dict[str, list[dict[str, str]]]:
    """Return anchor key -> product entries declared by the project.

    The file is optional. It lives with the project's context so no store-specific
    product catalog ships inside the workbench package.
    """

    path = state.safe_project_path(project_dir, ANCHORS_PATH)
    if not path.exists():
        return {}
    data: Any = json.loads(path.read_text(encoding="utf-8") or "{}")
    if not isinstance(data, dict):
        return {}
    anchors: dict[str, list[dict[str, str]]] = {}
    for anchor, items in data.items():
        if not isinstance(items, list):
            continue
        entries: list[dict[str, str]] = []
        for item in items:
            if not isinstance(item, dict):
                continue
            title = str(item.get("title") or "").strip()
            handle = str(item.get("handle") or "").strip()
            if title and handle:
                entries.append({"title": title, "handle": handle})
        if entries:
            anchors[str(anchor)] = entries
    return anchors
