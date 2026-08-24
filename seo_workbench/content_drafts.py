from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from seo_workbench import state
from seo_workbench.content_pipeline import set_queue_status
from seo_workbench.content_quality import scrub_ai_signatures
from seo_workbench_tools.files import atomic_write_text


def import_draft(project_dir: Path, from_file: Path, *, now: datetime | None = None) -> tuple[dict[str, Any], Path]:
    current = now or datetime.now(timezone.utc)
    payload = _load_payload(from_file)
    item_id = str(payload.get("pipeline_record_id") or payload.get("item_id") or "")
    if not item_id:
        raise ValueError("draft payload must include pipeline_record_id or item_id")
    article = payload.get("article") if isinstance(payload.get("article"), dict) else payload
    if not isinstance(article, dict) or not article.get("draft_html"):
        raise ValueError("draft payload must include article.draft_html")
    qc_status = _qc_status(payload)
    status = "blocked" if qc_status == "review_flag" else "review"
    update = _article_update(article, payload, item_id=item_id, status=status)
    _upsert_pipeline(project_dir, item_id, update)
    _update_queue(project_dir, item_id, update, status=status)
    draft_path = _write_draft(project_dir, item_id, update)
    report = {
        "schema_version": "content-draft-import-v1",
        "collection_status": "ok",
        "imported_at": current.isoformat(),
        "item_id": item_id,
        "status": status,
        "qc_status": qc_status,
        "scrub_stats": update.get("scrub_stats", {}),
        "draft_path": str(draft_path.relative_to(project_dir)),
    }
    run_path = state.safe_project_path(project_dir, f"audits/runs/{current.strftime('%Y%m%dT%H%M%SZ')}-content-draft-import.json")
    run_path.parent.mkdir(parents=True, exist_ok=True)
    atomic_write_text(run_path, json.dumps(report, ensure_ascii=False, indent=2) + "\n")
    return report, run_path


def _load_payload(path: Path) -> dict[str, Any]:
    text = path.read_text(encoding="utf-8")
    if path.suffix.lower() == ".json":
        payload = json.loads(text)
    else:
        try:
            import yaml
        except ImportError as exc:
            raise RuntimeError("YAML draft import requires PyYAML; use JSON or install dev dependencies") from exc
        payload = yaml.safe_load(text)
    if not isinstance(payload, dict):
        raise ValueError("draft payload must be an object")
    return payload


def _qc_status(payload: dict[str, Any]) -> str:
    raw = str(payload.get("qc_status") or "review_flag").strip()
    if raw == "fail":
        return "review_flag"
    if raw == "pass":
        score = payload.get("qc_score")
        return "review_ready" if isinstance(score, (int, float)) and score >= 10 else "review"
    return raw if raw in {"review_ready", "review", "review_flag"} else "review_flag"


def _article_update(article: dict[str, Any], payload: dict[str, Any], *, item_id: str, status: str) -> dict[str, Any]:
    draft_html = str(article.get("draft_html") or "").strip()
    draft_html, scrub_stats = scrub_ai_signatures(draft_html)
    update = {
        "id": item_id,
        "status": status,
        "title": str(article.get("title") or "").strip(),
        "slug": str(article.get("article_slug") or article.get("slug") or "").strip(),
        "meta_description": str(article.get("meta_description") or "").strip(),
        "target_keyword": str(article.get("target_keyword") or "").strip(),
        "draft_html": draft_html,
        "word_count": _word_count(draft_html),
        "scrub_stats": scrub_stats,
        "internal_links": article.get("internal_links") or [],
        "image_notes": str(article.get("image_resolution_notes") or "").strip(),
        "feature_image_refs": _refs(article.get("feature_image_rid")),
        "inline_image_refs": _refs(article.get("inline_image_rids")),
        "qc_score": payload.get("qc_score"),
        "qc_breakdown": str(payload.get("qc_breakdown") or "").strip(),
        "review_thread_id": "",
    }
    for key in ("shopify_article_id", "live_url"):
        value = article.get(key) or payload.get(key)
        if value:
            update[key] = str(value).strip()
    scheduled_at = article.get("scheduled_at") or payload.get("scheduled_at")
    if scheduled_at:
        update["scheduled_at"] = _scheduled_at(scheduled_at)
    if status == "blocked":
        issues = payload.get("qc_issues") or []
        update["edit_notes"] = "Self-QC review_flag" + (": " + "; ".join(str(item) for item in issues) if issues else "")
    return update


def _scheduled_at(value: Any) -> str:
    text = str(value).strip()
    try:
        parsed = datetime.fromisoformat(text.replace("Z", "+00:00"))
    except ValueError as exc:
        raise ValueError("scheduled_at must be an ISO 8601 datetime") from exc
    if parsed.tzinfo is None:
        raise ValueError("scheduled_at must include a timezone")
    return parsed.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _refs(value: Any) -> list[str]:
    if not value:
        return []
    if isinstance(value, list):
        return [str(item) for item in value if item]
    return [str(value)]


def _upsert_pipeline(project_dir: Path, item_id: str, update: dict[str, Any]) -> None:
    path = state.safe_project_path(project_dir, "content/blog-pipeline.jsonl")
    rows = []
    found = False
    if path.exists():
        for line in path.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            row = json.loads(line)
            if row.get("id") == item_id:
                row.update(update)
                found = True
            rows.append(row)
    if not found:
        rows.append(update)
    path.parent.mkdir(parents=True, exist_ok=True)
    atomic_write_text(path, "".join(json.dumps(row, ensure_ascii=False) + "\n" for row in rows))


def _update_queue(project_dir: Path, item_id: str, update: dict[str, Any], *, status: str) -> None:
    def mutation(data: dict[str, Any]) -> None:
        try:
            item = set_queue_status(data, item_id, status, note="Draft imported")
        except ValueError:
            item = {"id": item_id, "status": status}
            data.setdefault("contentQueue", []).append(item)
        for key in ("title", "slug", "target_keyword", "review_thread_id"):
            item[key] = update.get(key) or ""
        if "scheduled_at" in update:
            item["scheduled_at"] = update["scheduled_at"]
        state.record_history(data, "content-draft-import", "CONTENT_PRODUCTION", item_id)

    state.mutate_state(project_dir, mutation)


def _write_draft(project_dir: Path, item_id: str, update: dict[str, Any]) -> Path:
    name = re.sub(r"[^A-Za-z0-9_.-]+", "-", update.get("slug") or item_id).strip("-") or item_id
    path = state.safe_project_path(project_dir, f"content/drafts/{name}.html")
    path.parent.mkdir(parents=True, exist_ok=True)
    atomic_write_text(path, str(update.get("draft_html") or "") + "\n")
    return path


def _word_count(html: str) -> int:
    return len(re.findall(r"[A-Za-z0-9]+(?:[-'][A-Za-z0-9]+)?", re.sub(r"<[^>]+>", " ", html)))
