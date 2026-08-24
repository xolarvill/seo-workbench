from __future__ import annotations

from datetime import datetime, time, timedelta, timezone
from pathlib import Path
from typing import Any

from seo_workbench import state
from seo_workbench.content_indexing import list_due_for_indexing


BJT = timezone(timedelta(hours=8))


def build_content_ops(project_dir: Path, *, now: datetime | None = None) -> dict[str, Any]:
    current = now or datetime.now(timezone.utc)
    queue = _queue(project_dir)
    planned = [item for item in queue if item.get("status") == "planned"]
    ready_to_write = [item for item in queue if item.get("status") == "ready_to_write"]
    review_push = [item for item in queue if item.get("status") == "review" and not item.get("review_thread_id")]
    review_digest = [item for item in queue if item.get("status") == "review" and item.get("review_thread_id")]
    revise = [item for item in queue if item.get("status") == "revision_requested"]
    publish = [item for item in queue if item.get("status") == "approved"]
    index_due = list_due_for_indexing(project_dir, now=current)["items"]
    inspect = index_due + [
        item for item in queue if item.get("status") in {"submitted_for_indexing", "indexing_issue"} and item.get("live_url")
    ]
    return {
        "schema_version": "content-ops-v1",
        "generated_at": current.isoformat(),
        "actions": [
            _action("review_push", "manual", True, review_push, "content review-push <item_id> --role seo_review --confirm"),
            _action("cluster_review", "manual", True, planned, "content queue --status planned"),
            _action("write_brief", "manual", True, ready_to_write, "content brief <item_id>"),
            _action("review_digest", "every_30m", bool(review_digest), review_digest, "content review-digest"),
            _action("revise_brief", "manual", True, revise, "content revise-brief <item_id>"),
            _action("publish", "manual", True, publish, "content publish <item_id> --blog-id <blog_id> --confirm"),
            _action("gsc_inspect", "daily_09:00_bjt", _past_bjt(current, time(9, 0)), inspect, "gsc inspect --limit <n>"),
            _action("content_report", "daily_or_weekly", True, queue, "content report --period daily"),
        ],
    }


def _queue(project_dir: Path) -> list[dict[str, Any]]:
    data = state.load_state(project_dir)
    queue = data.get("contentQueue") or []
    if not isinstance(queue, list):
        raise ValueError("state.contentQueue must be a list")
    return [item for item in queue if isinstance(item, dict)]


def _action(action_id: str, cadence: str, time_ready: bool, items: list[dict[str, Any]], command: str) -> dict[str, Any]:
    return {
        "id": action_id,
        "cadence": cadence,
        "due": bool(time_ready and items),
        "count": len(items),
        "command": command,
        "items": [_compact(item) for item in items],
    }


def _past_bjt(current: datetime, threshold: time) -> bool:
    local = current.astimezone(BJT)
    return local.time() >= threshold


def _compact(item: dict[str, Any]) -> dict[str, Any]:
    return {
        key: item.get(key, "")
        for key in ("id", "status", "title", "slug", "live_url", "scheduled_at", "review_thread_id")
        if item.get(key)
    }
