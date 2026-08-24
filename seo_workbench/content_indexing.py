from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from seo_workbench import state
from seo_workbench.content_pipeline import set_queue_status
from seo_workbench_tools.files import atomic_write_text


def list_due_for_indexing(project_dir: Path, *, now: datetime | None = None) -> dict[str, Any]:
    current = now or datetime.now(timezone.utc)
    queue = _queue(project_dir)
    due = [
        _compact(item)
        for item in queue
        if item.get("status") == "scheduled" and item.get("live_url") and _due(item.get("scheduled_at"), current)
    ]
    return {
        "collection_status": "ok",
        "generated_at": current.isoformat(),
        "count": len(due),
        "items": due,
        "urls": [item["live_url"] for item in due],
    }


def submit_due_for_indexing(
    project_dir: Path,
    *,
    profile: str = "default",
    limit: int | None = None,
    timeout: float = 20,
    now: datetime | None = None,
    credential_loader: Any = None,
    requester: Any = None,
) -> tuple[dict[str, Any], Path]:
    raise ValueError("Google Indexing API does not support ordinary Blog articles; use gsc inspect and content index-status")


def apply_gsc_index_status(
    project_dir: Path,
    *,
    inspection_path: Path | None = None,
    anomaly_days: int = 12,
    now: datetime | None = None,
) -> tuple[dict[str, Any], Path]:
    current = now or datetime.now(timezone.utc)
    path = inspection_path or state.safe_project_path(project_dir, "audits/gsc/inspection/latest.json")
    report = json.loads(path.read_text(encoding="utf-8"))
    changes = []
    by_url = {item.get("live_url"): item for item in _queue(project_dir) if item.get("live_url")}
    pipeline_updates: dict[str, dict[str, Any]] = {}
    for inspection in report.get("inspections", []):
        url = inspection.get("url")
        item = by_url.get(url)
        if not item:
            continue
        result = inspection.get("inspection_result") or {}
        status = _next_status(item, result, current=current, anomaly_days=anomaly_days)
        coverage = _coverage_text(result)
        update = {"coverage_state": coverage, "last_inspected_at": current.isoformat()}
        if status and status != item.get("status"):
            update["status"] = status
        pipeline_updates[item["id"]] = update
        changes.append({"id": item["id"], "url": url, "previous_status": item.get("status"), "status": status or item.get("status"), "coverage_state": coverage})
    if changes:
        _apply_updates(project_dir, pipeline_updates)
    output = {
        "schema_version": "content-index-status-v1",
        "collection_status": "ok",
        "generated_at": current.isoformat(),
        "source_path": str(path),
        "changes": changes,
        "changed_count": len(changes),
        "notification_sent": False,
    }
    run_path = state.safe_project_path(project_dir, f"audits/runs/{current.strftime('%Y%m%dT%H%M%SZ')}-content-index-status.json")
    run_path.parent.mkdir(parents=True, exist_ok=True)
    atomic_write_text(run_path, json.dumps(output, ensure_ascii=False, indent=2) + "\n")
    return output, run_path


def pending_index_notifications(project_dir: Path, changes: list[dict[str, Any]]) -> list[dict[str, Any]]:
    queue = {str(item.get("id")): item for item in _queue(project_dir)}
    return [
        change
        for change in changes
        if change.get("status") == "indexed" and not queue.get(str(change.get("id")), {}).get("index_notification_sent_at")
    ]


def mark_index_notifications_sent(project_dir: Path, item_ids: list[str], *, now: datetime | None = None) -> None:
    current = now or datetime.now(timezone.utc)
    updates = {item_id: {"index_notification_sent_at": current.isoformat()} for item_id in item_ids}

    def mutation(data: dict[str, Any]) -> None:
        queue = data.get("contentQueue") or []
        for item in queue:
            if isinstance(item, dict) and item.get("id") in updates:
                item.update(updates[item["id"]])
        state.record_history(data, "content-index-notify", "CONTENT_PRODUCTION", f"Notified {len(updates)} indexed items")

    state.mutate_state(project_dir, mutation)
    _update_pipeline(project_dir, updates)


def _queue(project_dir: Path) -> list[dict[str, Any]]:
    data = state.load_state(project_dir)
    queue = data.get("contentQueue") or []
    if not isinstance(queue, list):
        raise ValueError("state.contentQueue must be a list")
    return [item for item in queue if isinstance(item, dict)]


def _apply_updates(project_dir: Path, updates: dict[str, dict[str, Any]]) -> None:
    def mutation(data: dict[str, Any]) -> None:
        for item_id, update in updates.items():
            status = update.get("status")
            if status:
                item = set_queue_status(data, item_id, status, note="GSC inspection applied")
            else:
                item = next((row for row in data.get("contentQueue", []) if isinstance(row, dict) and row.get("id") == item_id), None)
                if item is None:
                    continue
            item.update(update)
        state.record_history(data, "content-index-status", "CONTENT_PRODUCTION", "prepare-publish")

    state.mutate_state(project_dir, mutation)
    _update_pipeline(project_dir, updates)


def _update_pipeline(project_dir: Path, updates: dict[str, dict[str, Any]]) -> None:
    path = state.safe_project_path(project_dir, "content/blog-pipeline.jsonl")
    if not path.exists():
        return
    lines = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        record = json.loads(line)
        if record.get("id") in updates:
            record.update(updates[record["id"]])
        lines.append(json.dumps(record, ensure_ascii=False))
    atomic_write_text(path, "\n".join(lines) + "\n")


def _next_status(item: dict[str, Any], inspection: dict[str, Any], *, current: datetime, anomaly_days: int) -> str:
    if _is_indexed(inspection):
        return "indexed"
    scheduled = _parse_dt(item.get("scheduled_at"))
    if scheduled and (current - scheduled).days > anomaly_days:
        return "indexing_issue"
    return str(item.get("status", ""))


def _is_indexed(inspection: dict[str, Any]) -> bool:
    status = inspection.get("indexStatusResult") or {}
    verdict = str(status.get("verdict", "")).upper()
    coverage = str(status.get("coverageState", "")).lower()
    return verdict == "PASS" or "submitted and indexed" in coverage or "indexed, not submitted" in coverage


def _coverage_text(inspection: dict[str, Any]) -> str:
    status = inspection.get("indexStatusResult") or {}
    parts = [
        f"verdict={status.get('verdict', '-')}",
        f"coverageState={status.get('coverageState', '-')}",
        f"lastCrawlTime={status.get('lastCrawlTime', '-')}",
        f"googleCanonical={status.get('googleCanonical', '-')}",
    ]
    return " | ".join(parts)


def _due(value: Any, current: datetime) -> bool:
    parsed = _parse_dt(value)
    return bool(parsed and parsed <= current)


def _parse_dt(value: Any) -> datetime | None:
    if not value:
        return None
    try:
        parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except ValueError:
        return None
    return parsed if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)


def _compact(item: dict[str, Any]) -> dict[str, Any]:
    return {key: item.get(key, "") for key in ("id", "title", "slug", "live_url", "scheduled_at", "status") if item.get(key)}
