from __future__ import annotations

import json
import shlex
import subprocess
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from seo_workbench import state
from seo_workbench.feishu_gateway import list_thread_replies
from seo_workbench_tools.files import atomic_write_text


def generate_review_digest(
    project_dir: Path,
    *,
    item_id: str | None = None,
    profile: str,
    config_path: Path | None = None,
    bot_id: str = "",
    now: datetime | None = None,
    runner: Any = subprocess.run,
) -> tuple[dict[str, Any], Path]:
    current = now or datetime.now(timezone.utc)
    items = _review_items(project_dir, item_id=item_id)
    results = [
        _digest_item(
            item,
            profile=profile,
            config_path=config_path,
            bot_id=bot_id,
            runner=runner,
        )
        for item in items
    ]
    counts = Counter(item["suggested_status"] for item in results)
    private_report = {
        "schema_version": "content-review-digest-v1",
        "collection_status": "draft_ready" if results else "no_candidates",
        "generated_at": current.isoformat(),
        "profile": profile,
        "bot_id": bot_id,
        "item_count": len(results),
        "suggestion_counts": dict(sorted(counts.items())),
        "items": results,
        "state_mutated": False,
    }
    run_path = _write_run_record(project_dir, current, private_report)
    report = {
        key: value
        for key, value in private_report.items()
        if key not in {"bot_id", "items"}
    }
    report["items"] = [_public_digest_item(item) for item in results]
    report["run_record_path"] = str(run_path.relative_to(project_dir))
    report_path = _write_markdown(project_dir, current, report)
    return report, report_path


def _review_items(project_dir: Path, *, item_id: str | None) -> list[dict[str, Any]]:
    data = state.load_state(project_dir)
    queue = data.get("contentQueue") or []
    if not isinstance(queue, list):
        raise ValueError("state.contentQueue must be a list")
    items = [
        item
        for item in queue
        if isinstance(item, dict)
        and item.get("status") == "review"
        and item.get("review_thread_id")
        and (item_id is None or item.get("id") == item_id)
    ]
    if item_id and not items:
        raise ValueError(f"review queue item with thread not found: {item_id}")
    return items


def _digest_item(
    item: dict[str, Any],
    *,
    profile: str,
    config_path: Path | None,
    bot_id: str,
    runner: Any,
) -> dict[str, Any]:
    thread_id = str(item["review_thread_id"])
    replies = _fetch_thread_replies(thread_id, profile, config_path, runner)
    parsed = [_compact_reply(reply) for reply in replies]
    human_replies = [reply for reply in parsed if not bot_id or reply.get("sender_id") != bot_id]
    suggested = _suggest_status([reply["text"] for reply in human_replies])
    note = _suggest_note(suggested, human_replies)
    return {
        "id": item.get("id", ""),
        "title": item.get("title", ""),
        "slug": item.get("slug", ""),
        "review_thread_id": thread_id,
        "reply_count": len(human_replies),
        "suggested_status": suggested,
        "suggested_note": note,
        "confirmation_command": _confirmation_command(str(item.get("id", "")), suggested, note),
        "replies": human_replies,
    }


def _fetch_thread_replies(
    thread_id: str,
    profile: str,
    config_path: Path | None,
    runner: Any,
) -> list[dict[str, Any]]:
    return list_thread_replies(
        profile=profile,
        config_path=config_path,
        thread_id=thread_id,
        runner=runner,
    )


def _compact_reply(reply: dict[str, Any]) -> dict[str, str]:
    return {
        "message_id": str(reply.get("message_id") or reply.get("id") or ""),
        "sender_id": _sender_id(reply),
        "created_at": str(reply.get("create_time") or reply.get("created_at") or ""),
        "text": _message_text(reply)[:1000],
    }


def _sender_id(reply: dict[str, Any]) -> str:
    sender = reply.get("sender") if isinstance(reply.get("sender"), dict) else {}
    sender_id = sender.get("sender_id") if isinstance(sender.get("sender_id"), dict) else {}
    return str(sender_id.get("open_id") or sender_id.get("app_id") or sender_id.get("user_id") or sender.get("id") or "")


def _message_text(reply: dict[str, Any]) -> str:
    body = reply.get("body") if isinstance(reply.get("body"), dict) else {}
    raw = body.get("content") or reply.get("content") or reply.get("text") or ""
    if isinstance(raw, str):
        try:
            parsed = json.loads(raw)
        except json.JSONDecodeError:
            return raw.strip()
        return _flatten_text(parsed).strip()
    return _flatten_text(raw).strip()


def _flatten_text(value: Any) -> str:
    if isinstance(value, str):
        return value
    if isinstance(value, list):
        return " ".join(_flatten_text(item) for item in value)
    if isinstance(value, dict):
        return " ".join(_flatten_text(item) for item in value.values())
    return ""


def _suggest_status(texts: list[str]) -> str:
    joined = "\n".join(texts).lower()
    revise = any(word in joined for word in ("revise", "revision", "修改", "打回", "需改"))
    approve = any(word in joined for word in ("approve", "approved", "lgtm", "ok", "通过", "同意"))
    if revise and not approve:
        return "revision_requested"
    if approve and not revise:
        return "approved"
    return "needs_human_review"


def _suggest_note(status: str, replies: list[dict[str, str]]) -> str:
    if status == "needs_human_review":
        return "No unambiguous approve/revise reply detected."
    text = next((reply["text"] for reply in reversed(replies) if reply["text"]), "")
    return text[:300]


def _confirmation_command(item_id: str, status: str, note: str) -> str:
    if status not in {"approved", "revision_requested"}:
        return f"content status {shlex.quote(item_id)} <approved-or-revision_requested> --note <operator-note>"
    return " ".join(
        [
            "content",
            "status",
            shlex.quote(item_id),
            status,
            "--note",
            shlex.quote(note or f"Review {status}"),
        ]
    )


def _public_digest_item(item: dict[str, Any]) -> dict[str, Any]:
    status = str(item["suggested_status"])
    return {
        "id": item["id"],
        "title": item["title"],
        "slug": item["slug"],
        "reply_count": item["reply_count"],
        "suggested_status": status,
        "confirmation_command": _confirmation_command(
            str(item["id"]), status, f"Feishu review: {status}"
        ),
    }


def _write_markdown(project_dir: Path, current: datetime, report: dict[str, Any]) -> Path:
    path = state.safe_project_path(project_dir, f"content/reports/{current.date().isoformat()}-review-digest.md")
    path.parent.mkdir(parents=True, exist_ok=True)
    lines = [
        f"# Content Review Digest - {current.date().isoformat()}",
        "",
        "Status: draft only, no queue status changed.",
        "",
    ]
    if not report["items"]:
        lines.append("- no review items with Feishu thread IDs")
    for item in report["items"]:
        lines.extend(
            [
                f"## {item['id']}: {item['title'] or item['slug'] or '(untitled)'}",
                "",
                f"- replies: {item['reply_count']}",
                f"- suggested_status: {item['suggested_status']}",
                f"- confirm: `{item['confirmation_command']}`",
                "",
            ]
        )
    atomic_write_text(path, "\n".join(lines).rstrip() + "\n")
    return path


def _write_run_record(project_dir: Path, current: datetime, payload: dict[str, Any]) -> Path:
    path = state.safe_project_path(project_dir, f".runtime/feishu/review-digests/{current.strftime('%Y%m%dT%H%M%SZ')}.json")
    path.parent.mkdir(parents=True, exist_ok=True)
    atomic_write_text(path, json.dumps(payload, ensure_ascii=False, indent=2) + "\n", mode=0o600)
    return path
