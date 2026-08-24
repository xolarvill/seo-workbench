from __future__ import annotations

import hashlib
import json
import re
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from seo_workbench import state
from seo_workbench.locks import project_lock
from seo_workbench.tech_audit import link_scope, normalize_url
from seo_workbench_tools.files import atomic_write_text


LEDGER_PATH = "strategy/seo-changes.jsonl"
CHANGE_TYPES = (
    "content",
    "internal_links",
    "metadata",
    "performance",
    "redirect",
    "schema",
    "technical",
    "other",
)
CHANGE_STATUSES = ("planned", "shipped", "reviewed", "cancelled")
METRIC_PATTERN = re.compile(r"^[a-z][a-z0-9_.-]{0,63}$")


def record_change(
    project_dir: Path,
    *,
    urls: list[str],
    change_type: str,
    hypothesis: str,
    metrics: list[str],
    changed_at: str | date | None = None,
    review_date: str | date | None = None,
    review_after_days: int = 28,
    status: str = "shipped",
    note: str = "",
    now: datetime | None = None,
) -> dict[str, Any]:
    if change_type not in CHANGE_TYPES:
        raise ValueError(f"change type must be one of: {', '.join(CHANGE_TYPES)}")
    if status not in CHANGE_STATUSES:
        raise ValueError(f"change status must be one of: {', '.join(CHANGE_STATUSES)}")
    hypothesis = hypothesis.strip()
    if not hypothesis:
        raise ValueError("hypothesis is required")
    if review_after_days < 1:
        raise ValueError("review-after-days must be at least 1")

    project_url = str(state.load_state(project_dir).get("project", {}).get("url", ""))
    normalized_urls = _change_urls(urls, project_url)
    normalized_metrics = _metrics(metrics)
    change_day = _day(changed_at, "changed-at") if changed_at else (now or datetime.now(timezone.utc)).date()
    review_day = _day(review_date, "review-date") if review_date else change_day + timedelta(days=review_after_days)
    if review_day < change_day:
        raise ValueError("review-date cannot be before changed-at")

    created_at = (now or datetime.now(timezone.utc)).astimezone(timezone.utc).isoformat()
    identity = json.dumps(
        [change_day.isoformat(), change_type, normalized_urls, hypothesis],
        ensure_ascii=False,
        separators=(",", ":"),
    )
    change = {
        "schema_version": "seo-change-v1",
        "id": f"chg-{change_day.strftime('%Y%m%d')}-{hashlib.sha256(identity.encode()).hexdigest()[:10]}",
        "created_at": created_at,
        "changed_at": change_day.isoformat(),
        "review_date": review_day.isoformat(),
        "status": status,
        "change_type": change_type,
        "urls": normalized_urls,
        "hypothesis": hypothesis,
        "expected_metrics": normalized_metrics,
        "note": note.strip(),
        "updates": [],
    }

    path = state.safe_project_path(project_dir, LEDGER_PATH)
    with project_lock(project_dir):
        changes = _read(path)
        if any(item.get("id") == change["id"] for item in changes):
            raise ValueError(f"SEO change already exists: {change['id']}")
        _write(path, [*changes, change])
    return change


def list_changes(
    project_dir: Path,
    *,
    status: str = "",
    due: bool = False,
    as_of: str | date | None = None,
) -> dict[str, Any]:
    if status and status not in CHANGE_STATUSES:
        raise ValueError(f"change status must be one of: {', '.join(CHANGE_STATUSES)}")
    changes = _read(state.safe_project_path(project_dir, LEDGER_PATH))
    if status:
        changes = [item for item in changes if item.get("status") == status]
    if due:
        day = _day(as_of, "as-of") if as_of else datetime.now(timezone.utc).date()
        changes = [
            item
            for item in changes
            if item.get("status") == "shipped" and _day(str(item.get("review_date", "")), "review-date") <= day
        ]
    changes.sort(key=lambda item: (str(item.get("changed_at", "")), str(item.get("id", ""))), reverse=True)
    return {
        "schema_version": "seo-change-list-v1",
        "collection_status": "ok",
        "count": len(changes),
        "changes": changes,
    }


def get_change(project_dir: Path, change_id: str) -> dict[str, Any]:
    change = next(
        (item for item in _read(state.safe_project_path(project_dir, LEDGER_PATH)) if item.get("id") == change_id),
        None,
    )
    if change is None:
        raise ValueError(f"SEO change not found: {change_id}")
    return change


def update_change_status(
    project_dir: Path,
    change_id: str,
    status: str,
    *,
    note: str = "",
    now: datetime | None = None,
) -> dict[str, Any]:
    if status not in CHANGE_STATUSES:
        raise ValueError(f"change status must be one of: {', '.join(CHANGE_STATUSES)}")
    path = state.safe_project_path(project_dir, LEDGER_PATH)
    updated_at = (now or datetime.now(timezone.utc)).astimezone(timezone.utc).isoformat()
    with project_lock(project_dir):
        changes = _read(path)
        change = next((item for item in changes if item.get("id") == change_id), None)
        if change is None:
            raise ValueError(f"SEO change not found: {change_id}")
        previous = str(change.get("status", ""))
        change["status"] = status
        change.setdefault("updates", []).append(
            {"updated_at": updated_at, "previous_status": previous, "status": status, "note": note.strip()}
        )
        _write(path, changes)
    return change


def _change_urls(urls: list[str], project_url: str) -> list[str]:
    seed = normalize_url(project_url)
    if not seed:
        raise ValueError("project.url must be an absolute HTTP(S) URL")
    normalized = list(dict.fromkeys(normalize_url(value) for value in urls))
    if not normalized or any(not value for value in normalized):
        raise ValueError("at least one valid absolute HTTP(S) URL is required")
    if len(normalized) > 1000:
        raise ValueError("a change can reference at most 1000 URLs")
    outside = [url for url in normalized if link_scope(url, seed)[1] not in {"same_host", "subdomain"}]
    if outside:
        raise ValueError(f"change URL is outside the project site family: {outside[0]}")
    return normalized


def _metrics(values: list[str]) -> list[str]:
    metrics = list(dict.fromkeys(value.strip().lower() for value in values if value.strip()))
    if not metrics:
        raise ValueError("at least one expected metric is required")
    invalid = next((value for value in metrics if not METRIC_PATTERN.fullmatch(value)), None)
    if invalid:
        raise ValueError(f"invalid metric name: {invalid}")
    return metrics


def _day(value: str | date, field: str) -> date:
    if isinstance(value, date):
        return value
    try:
        return date.fromisoformat(value)
    except ValueError as exc:
        raise ValueError(f"{field} must be YYYY-MM-DD") from exc


def _read(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    changes = []
    for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        if not line.strip():
            continue
        try:
            item = json.loads(line)
        except json.JSONDecodeError as exc:
            raise ValueError(f"invalid SEO change ledger line {line_number}: {exc.msg}") from exc
        if not isinstance(item, dict):
            raise ValueError(f"invalid SEO change ledger line {line_number}: expected an object")
        changes.append(item)
    return changes


def _write(path: Path, changes: list[dict[str, Any]]) -> None:
    atomic_write_text(path, "".join(json.dumps(item, ensure_ascii=False) + "\n" for item in changes))
