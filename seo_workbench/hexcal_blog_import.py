from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

from seo_workbench import state
from seo_workbench.content_pipeline import normalize_status
from seo_workbench_tools.files import atomic_write_text


HEXCAL_SCHEDULE_TZ = ZoneInfo("America/New_York")
HEXCAL_STATUS_MAP = {
    "cluster_pending": "planned",
    "cluster_approved": "ready_to_write",
    "cluster_dropped": "dropped",
    "in_writing": "drafting",
    "review": "review",
    "in_writing_failed": "blocked",
    "修改中": "revision_requested",
    "approved": "approved",
    "推送已排期": "scheduled",
    "已提交索引": "submitted_for_indexing",
    "已收录": "indexed",
    "收录异常": "indexing_issue",
}


KEYWORD_FIELDS = {name: name for name in (
    "keyword", "source", "volume_hint", "ctr_hint", "position_hint", "kd_hint", "cpc_hint",
    "intent", "seed_keyword", "competitor_domain", "cluster_ref", "priority_score",
)}

PIPELINE_FIELDS = {name: name for name in (
    "cluster_name", "representative_keyword", "long_tail_keywords", "member_keywords", "intent",
    "business_fit", "difficulty_hint", "traffic_hint", "product_anchor", "cluster_rationale", "status",
    "title", "slug", "meta_description", "draft_html", "scheduled_at", "shopify_article_id", "live_url",
    "edit_notes", "review_thread_id", "feature_image_refs", "inline_image_refs", "feature_image_hist_refs",
    "inline_image_hist_refs", "image_notes", "target_keyword",
)}


def import_hexcal_blog(
    project_dir: Path,
    *,
    keywords_path: Path | None = None,
    pipeline_path: Path | None = None,
) -> dict[str, Any]:
    project_dir = Path(project_dir)
    _ensure_content_dirs(project_dir)

    keyword_records = [_keyword_record(row) for row in _load_rows(keywords_path)] if keywords_path else []
    pipeline_records = [_pipeline_record(row) for row in _load_rows(pipeline_path)] if pipeline_path else []

    if keywords_path:
        keyword_output = state.safe_project_path(project_dir, "strategy/keyword-pool.jsonl")
        _write_jsonl(keyword_output, _preserve_local_records(keyword_records, _read_jsonl(keyword_output)))
    if pipeline_path:
        pipeline_output = state.safe_project_path(project_dir, "content/blog-pipeline.jsonl")
        local_records = _read_jsonl(pipeline_output)
        merged_records = _preserve_local_records(pipeline_records, local_records)
        _write_jsonl(pipeline_output, merged_records)
        queue = [_queue_item(record) for record in merged_records if record.get("id")]
        state.mutate_state(project_dir, lambda data: _merge_content_queue(data, queue, imported_count=len(pipeline_records)))

    return {
        "keywords_imported": len(keyword_records),
        "pipeline_imported": len(pipeline_records),
        "content_queue_count": len(merged_records) if pipeline_path else None,
        "keyword_pool_path": str(state.safe_project_path(project_dir, "strategy/keyword-pool.jsonl")) if keywords_path else "",
        "blog_pipeline_path": str(state.safe_project_path(project_dir, "content/blog-pipeline.jsonl")) if pipeline_path else "",
    }


def _ensure_content_dirs(project_dir: Path) -> None:
    for dirname in ("strategy", "content", "content/drafts", "content/reports", "audits/publish", "audits/runs"):
        state.safe_project_path(project_dir, dirname).mkdir(parents=True, exist_ok=True)


def _load_rows(path: Path | None) -> list[dict[str, Any]]:
    if path is None:
        return []
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    if isinstance(data, list):
        return [row for row in data if isinstance(row, dict)]
    if isinstance(data, dict) and isinstance(data.get("records"), list):
        return [row for row in data["records"] if isinstance(row, dict)]
    payload = data.get("data") if isinstance(data, dict) else None
    if isinstance(payload, dict) and "field_id_list" in payload:
        fields = payload.get("field_id_list") or []
        ids = payload.get("record_id_list") or []
        rows = payload.get("data") or []
        return [
            {**dict(zip(fields, values)), "_record_id": record_id}
            for record_id, values in zip(ids, rows)
            if isinstance(values, list)
        ]
    raise ValueError(f"unsupported Hexcal export JSON shape: {path}")


def _keyword_record(row: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": _record_id(row),
        "keyword": _scalar(_field(row, "keyword", KEYWORD_FIELDS)),
        "source": _scalar(_field(row, "source", KEYWORD_FIELDS)),
        "seed_keyword": _scalar(_field(row, "seed_keyword", KEYWORD_FIELDS)),
        "competitor_domain": _scalar(_field(row, "competitor_domain", KEYWORD_FIELDS)),
        "volume_hint": _number(_field(row, "volume_hint", KEYWORD_FIELDS)),
        "ctr_hint": _number(_field(row, "ctr_hint", KEYWORD_FIELDS)),
        "position_hint": _number(_field(row, "position_hint", KEYWORD_FIELDS)),
        "kd_hint": _number(_field(row, "kd_hint", KEYWORD_FIELDS)),
        "cpc_hint": _number(_field(row, "cpc_hint", KEYWORD_FIELDS)),
        "intent": _scalar(_field(row, "intent", KEYWORD_FIELDS)),
        "cluster_ref": _link_refs(_field(row, "cluster_ref", KEYWORD_FIELDS)),
        "priority_score": _number(_field(row, "priority_score", KEYWORD_FIELDS)),
        "source_record": {"system": "hexcal-feishu", "record_id": _record_id(row)},
    }


def _pipeline_record(row: dict[str, Any]) -> dict[str, Any]:
    raw_status = _scalar(_field(row, "status", PIPELINE_FIELDS))
    feature_refs = _link_refs(_field(row, "feature_image_refs", PIPELINE_FIELDS))
    inline_refs = _link_refs(_field(row, "inline_image_refs", PIPELINE_FIELDS))
    feature_refs.extend(_link_refs(_field(row, "feature_image_hist_refs", PIPELINE_FIELDS)))
    inline_refs.extend(_link_refs(_field(row, "inline_image_hist_refs", PIPELINE_FIELDS)))
    return {
        "id": _record_id(row),
        "status": normalize_status(raw_status, HEXCAL_STATUS_MAP),
        "source_status": raw_status,
        "cluster_name": _scalar(_field(row, "cluster_name", PIPELINE_FIELDS)),
        "representative_keyword": _scalar(_field(row, "representative_keyword", PIPELINE_FIELDS)),
        "long_tail_keywords": _split_keywords(_field(row, "long_tail_keywords", PIPELINE_FIELDS), ","),
        "member_keywords": _split_keywords(_field(row, "member_keywords", PIPELINE_FIELDS), "|"),
        "intent": _scalar(_field(row, "intent", PIPELINE_FIELDS)),
        "business_fit": _number(_field(row, "business_fit", PIPELINE_FIELDS)),
        "difficulty_hint": _scalar(_field(row, "difficulty_hint", PIPELINE_FIELDS)),
        "traffic_hint": _number(_field(row, "traffic_hint", PIPELINE_FIELDS)),
        "product_anchor": _multi_select(_field(row, "product_anchor", PIPELINE_FIELDS)),
        "cluster_rationale": _scalar(_field(row, "cluster_rationale", PIPELINE_FIELDS)),
        "slug": _scalar(_field(row, "slug", PIPELINE_FIELDS)),
        "title": _scalar(_field(row, "title", PIPELINE_FIELDS)),
        "meta_description": _scalar(_field(row, "meta_description", PIPELINE_FIELDS)),
        "target_keyword": _scalar(_field(row, "target_keyword", PIPELINE_FIELDS)),
        "draft_html": _scalar(_field(row, "draft_html", PIPELINE_FIELDS)),
        "scheduled_at": _lark_datetime_to_utc_iso(_field(row, "scheduled_at", PIPELINE_FIELDS)),
        "shopify_article_id": _scalar(_field(row, "shopify_article_id", PIPELINE_FIELDS)),
        "live_url": _scalar(_field(row, "live_url", PIPELINE_FIELDS)),
        "edit_notes": _scalar(_field(row, "edit_notes", PIPELINE_FIELDS)),
        "review_thread_id": _scalar(_field(row, "review_thread_id", PIPELINE_FIELDS)),
        "feature_image_refs": _dedupe(feature_refs),
        "inline_image_refs": _dedupe(inline_refs),
        "image_notes": _scalar(_field(row, "image_notes", PIPELINE_FIELDS)),
        "source_record": {"system": "hexcal-feishu", "record_id": _record_id(row)},
    }


def _queue_item(record: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": record["id"],
        "status": record["status"],
        "slug": record.get("slug") or "",
        "title": record.get("title") or record.get("cluster_name") or "",
        "target_keyword": record.get("target_keyword") or record.get("representative_keyword") or "",
        "scheduled_at": record.get("scheduled_at") or "",
        "shopify_article_id": record.get("shopify_article_id") or "",
        "live_url": record.get("live_url") or "",
        "review_thread_id": record.get("review_thread_id") or "",
        "source": record.get("source_record", {}),
    }


def _merge_content_queue(data: dict[str, Any], queue: list[dict[str, Any]], *, imported_count: int) -> None:
    local_queue = data.get("contentQueue") or []
    if not isinstance(local_queue, list):
        raise ValueError("state.contentQueue must be a list")
    data["contentQueue"] = _preserve_local_records(queue, [item for item in local_queue if isinstance(item, dict)])
    state.record_history(data, "content-import", phase="CONTENT_PRODUCTION", note=f"Merged {imported_count} Hexcal Blog records")
    data["lastAction"] = f"Merged {imported_count} Hexcal Blog records"
    data["nextAction"] = "Review content queue"


def _write_jsonl(path: Path, records: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    atomic_write_text(path, "".join(json.dumps(record, ensure_ascii=False) + "\n" for record in records))


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def _preserve_local_records(imported: list[dict[str, Any]], local: list[dict[str, Any]]) -> list[dict[str, Any]]:
    local_by_id = {record.get("id"): record for record in local if record.get("id")}
    merged = [{**record, **local_by_id.pop(record.get("id"), {})} for record in imported]
    merged.extend(local_by_id.values())
    merged.extend(record for record in local if not record.get("id"))
    return merged


def _field(row: dict[str, Any], name: str, mapping: dict[str, str]) -> Any:
    if name in row:
        return row[name]
    field_id = mapping.get(name)
    if field_id and field_id in row:
        return row[field_id]
    return None


def _record_id(row: dict[str, Any]) -> str:
    return _scalar(row.get("_record_id") or row.get("record_id") or row.get("id"))


_MD_LINK_RE = re.compile(r"^\s*\[(?P<text>[^\]]+)\]\((?P<url>[^)]+)\)\s*$")


def _scalar(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, list):
        if not value:
            return ""
        first = value[0]
        if isinstance(first, dict):
            return _scalar(first.get("text", first.get("name", first.get("id", ""))))
        return _scalar(first)
    if isinstance(value, dict):
        return _scalar(value.get("text", value.get("name", value.get("id", ""))))
    result = str(value).strip()
    match = _MD_LINK_RE.match(result)
    if match and match.group("text") == match.group("url"):
        return match.group("url")
    return result


def _number(value: Any) -> int | float | None:
    if value in (None, ""):
        return None
    if isinstance(value, (int, float)):
        return value
    try:
        num = float(str(value).strip())
    except ValueError:
        return None
    return int(num) if num.is_integer() else num


def _multi_select(value: Any) -> list[str]:
    if not value:
        return []
    if isinstance(value, list):
        return [text for text in (_scalar(item) for item in value) if text]
    text = _scalar(value)
    return [text] if text else []


def _link_refs(value: Any) -> list[str]:
    if not value:
        return []
    if not isinstance(value, list):
        return []
    refs: list[str] = []
    for item in value:
        if isinstance(item, dict):
            ref = item.get("id") or item.get("record_id") or item.get("text") or item.get("name")
        else:
            ref = item
        text = _scalar(ref)
        if text:
            refs.append(text)
    return refs


def _lark_datetime_to_utc_iso(value: Any) -> str:
    if not value:
        return ""
    if isinstance(value, (int, float)):
        try:
            return datetime.fromtimestamp(int(value) / 1000, tz=timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        except (TypeError, ValueError, OSError):
            return ""
    text = str(value).strip()
    aware = text[:-1] + "+00:00" if text.endswith("Z") else text
    try:
        parsed = datetime.fromisoformat(aware)
    except ValueError:
        parsed = None
    if parsed and parsed.tzinfo:
        return parsed.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%dT%H:%M:%S", "%Y-%m-%d"):
        try:
            local = datetime.strptime(text, fmt).replace(tzinfo=HEXCAL_SCHEDULE_TZ)
            return local.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        except ValueError:
            continue
    return text


def _split_keywords(value: Any, sep: str) -> list[str]:
    text = _scalar(value)
    if not text:
        return []
    return [item.strip() for item in text.split(sep) if item.strip()]


def _dedupe(values: list[str]) -> list[str]:
    return list(dict.fromkeys(values))
