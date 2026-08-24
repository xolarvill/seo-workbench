from __future__ import annotations

import json
from collections import Counter
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any

from seo_workbench import state
from seo_workbench.content_ops import build_content_ops
from seo_workbench_tools.files import atomic_write_text


def generate_content_report(project_dir: Path, *, period: str = "daily", report_date: date | None = None) -> tuple[dict[str, Any], Path]:
    if period not in {"daily", "weekly"}:
        raise ValueError("period must be daily or weekly")
    day = report_date or datetime.now(timezone.utc).date()
    records = _load_pipeline(project_dir)
    queue = _load_queue(project_dir)
    counts = Counter(str(item.get("status", "")) for item in queue if isinstance(item, dict))
    due = [item for item in queue if _status(item) == "scheduled" and _is_due(item.get("scheduled_at"), day)]
    needs_review = [item for item in queue if _status(item) in {"review", "revision_requested", "blocked", "indexing_issue"}]
    published = [record for record in records if record.get("shopify_article_id") or record.get("live_url")]
    ops_now = datetime(day.year, day.month, day.day, 5, 0, tzinfo=timezone.utc)
    actions = [_compact_action(action) for action in build_content_ops(project_dir, now=ops_now)["actions"] if action.get("due")]
    summary = {
        "schema_version": "content-report-run-v1",
        "kind": "content-report",
        "period": period,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "report_date": day.isoformat(),
        "collection_status": "draft_ready",
        "notification_sent": False,
        "counts": dict(sorted(counts.items())),
        "totals": {
            "queue": len(queue),
            "pipeline": len(records),
            "published_or_scheduled": len(published),
            "due_for_indexing": len(due),
            "needs_review": len(needs_review),
        },
        "due_for_indexing": [_compact(item) for item in due],
        "needs_review": [_compact(item) for item in needs_review],
        "next_actions": actions,
    }
    report_path = _write_markdown(project_dir, period, day, summary)
    run_path = _write_run_record(project_dir, period, day, {**summary, "report_path": str(report_path.relative_to(project_dir))})
    summary["run_record_path"] = str(run_path.relative_to(project_dir))
    return summary, report_path


def _load_queue(project_dir: Path) -> list[dict[str, Any]]:
    data = state.load_state(project_dir)
    queue = data.get("contentQueue") or []
    if not isinstance(queue, list):
        raise ValueError("state.contentQueue must be a list")
    return [item for item in queue if isinstance(item, dict)]


def _load_pipeline(project_dir: Path) -> list[dict[str, Any]]:
    path = state.safe_project_path(project_dir, "content/blog-pipeline.jsonl")
    if not path.exists():
        return []
    records = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.strip():
            records.append(json.loads(line))
    return records


def _write_markdown(project_dir: Path, period: str, day: date, summary: dict[str, Any]) -> Path:
    path = state.safe_project_path(project_dir, f"content/reports/{day.isoformat()}-{period}.md")
    path.parent.mkdir(parents=True, exist_ok=True)
    lines = [
        f"# Content {period.title()} Report - {day.isoformat()}",
        "",
        "Status: draft only, no notification sent.",
        "",
        "## Totals",
        "",
    ]
    for key, value in summary["totals"].items():
        lines.append(f"- {key}: {value}")
    lines.extend(["", "## Status Counts", ""])
    for key, value in summary["counts"].items():
        lines.append(f"- {key or 'unknown'}: {value}")
    lines.extend(["", "## Due For Indexing", ""])
    lines.extend(_bullet_rows(summary["due_for_indexing"]))
    lines.extend(["", "## Needs Review", ""])
    lines.extend(_bullet_rows(summary["needs_review"]))
    lines.extend(["", "## Next Actions", ""])
    lines.extend(_action_rows(summary["next_actions"]))
    atomic_write_text(path, "\n".join(lines).rstrip() + "\n")
    return path


def _write_run_record(project_dir: Path, period: str, day: date, payload: dict[str, Any]) -> Path:
    path = state.safe_project_path(project_dir, f"audits/runs/{day.isoformat()}-{period}-content-report.json")
    path.parent.mkdir(parents=True, exist_ok=True)
    atomic_write_text(path, json.dumps(payload, ensure_ascii=False, indent=2) + "\n")
    return path


def _bullet_rows(items: list[dict[str, Any]]) -> list[str]:
    if not items:
        return ["- none"]
    return [f"- {item.get('id', '')}: {item.get('title') or item.get('slug') or '(untitled)'} [{item.get('status', '')}]" for item in items]


def _compact(item: dict[str, Any]) -> dict[str, Any]:
    return {key: item.get(key, "") for key in ("id", "status", "title", "slug", "live_url", "scheduled_at") if item.get(key)}


def _compact_action(action: dict[str, Any]) -> dict[str, Any]:
    return {key: action.get(key) for key in ("id", "cadence", "count", "command")}


def _action_rows(actions: list[dict[str, Any]]) -> list[str]:
    if not actions:
        return ["- none"]
    return [f"- {item['id']}: {item['count']} due, run `{item['command']}`" for item in actions]


def _status(item: dict[str, Any]) -> str:
    return str(item.get("status", ""))


def _is_due(value: Any, day: date) -> bool:
    if not value:
        return False
    try:
        raw = str(value).replace("Z", "+00:00")
        return datetime.fromisoformat(raw).date() <= day
    except ValueError:
        return False
