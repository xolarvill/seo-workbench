from __future__ import annotations

import json
import re
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from seo_workbench import state
from seo_workbench.feishu_gateway import send_role_post
from seo_workbench_tools.files import atomic_write_text


def push_review_request(
    project_dir: Path,
    item_id: str,
    *,
    role: str,
    profile: str,
    config_path: Path | None = None,
    now: datetime | None = None,
    runner: Any = subprocess.run,
) -> tuple[dict[str, Any], Path]:
    current = now or datetime.now(timezone.utc)
    item = _queue_item(project_dir, item_id)
    if item.get("status") != "review":
        raise ValueError(f"content item must be in review status: {item_id}")
    if item.get("review_thread_id"):
        raise ValueError(f"content item already has review_thread_id: {item_id}")
    record = _pipeline_record(project_dir, item_id)
    response = _send_review_post(
        profile=profile,
        role=role,
        config_path=config_path,
        title=f"Blog Review: {item.get('title') or item_id}",
        lines=_review_lines(item, record),
        idempotency_key=f"content-review-{item_id}",
        runner=runner,
    )
    message_id = str(response.get("message_id") or "")
    if not message_id:
        raise RuntimeError(f"feishu-gateway send returned no message_id: {str(response)[:300]}")
    state.mutate_state(project_dir, lambda data: _set_review_thread(data, item_id, message_id))
    report = {
        "schema_version": "content-review-push-v1",
        "collection_status": "sent",
        "sent_at": current.isoformat(),
        "item_id": item_id,
        "role": role,
        "profile": profile,
        "review_thread_id": message_id,
        "state_mutated": True,
        "gateway_response": response,
    }
    output = state.safe_project_path(project_dir, f"audits/runs/{current.strftime('%Y%m%dT%H%M%SZ')}-content-review-push.json")
    output.parent.mkdir(parents=True, exist_ok=True)
    atomic_write_text(output, json.dumps(report, ensure_ascii=False, indent=2) + "\n", mode=0o600)
    return report, output


def _queue_item(project_dir: Path, item_id: str) -> dict[str, Any]:
    data = state.load_state(project_dir)
    queue = data.get("contentQueue") or []
    if not isinstance(queue, list):
        raise ValueError("state.contentQueue must be a list")
    for item in queue:
        if isinstance(item, dict) and item.get("id") == item_id:
            return item
    raise ValueError(f"content queue item not found: {item_id}")


def _pipeline_record(project_dir: Path, item_id: str) -> dict[str, Any]:
    path = state.safe_project_path(project_dir, "content/blog-pipeline.jsonl")
    if not path.exists():
        return {}
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        record = json.loads(line)
        if isinstance(record, dict) and record.get("id") == item_id:
            return record
    return {}


def _send_review_post(
    *,
    profile: str,
    role: str,
    config_path: Path | None,
    title: str,
    lines: list[str],
    idempotency_key: str,
    runner: Any,
) -> dict[str, Any]:
    return send_role_post(
        profile=profile,
        config_path=config_path,
        role=role,
        title=title,
        lines=lines,
        idempotency_key=idempotency_key,
        runner=runner,
    )


def _review_lines(item: dict[str, Any], record: dict[str, Any]) -> list[str]:
    draft = _plain_text(record.get("draft_html", ""))[:500]
    lines = [
        f"🧾 ID: {item.get('id', '')}",
        f"📝 Title: {item.get('title') or record.get('title') or ''}",
        f"🔗 Slug: {item.get('slug') or record.get('slug') or ''}",
        f"🎯 Target keyword: {item.get('target_keyword') or record.get('target_keyword') or ''}",
    ]
    if record.get("meta_description"):
        lines.append(f"📣 Meta: {record['meta_description']}")
    if draft:
        lines.extend(["👀 Draft preview:", f"  {draft}"])
    lines.append("✅ Reply in thread with approve, or add revise notes.")
    return lines


def _plain_text(html: Any) -> str:
    return re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", str(html))).strip()


def _set_review_thread(data: dict[str, Any], item_id: str, message_id: str) -> None:
    for item in data.get("contentQueue", []):
        if isinstance(item, dict) and item.get("id") == item_id:
            item["review_thread_id"] = message_id
            state.record_history(data, "content-review-push", "CONTENT_PRODUCTION", item_id)
            data["lastAction"] = f"Sent content review request for {item_id}"
            data["nextAction"] = "Review Feishu replies with content review-digest"
            return
    raise ValueError(f"content queue item not found: {item_id}")
