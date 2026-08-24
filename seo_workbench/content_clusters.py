from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from seo_workbench import state
from seo_workbench_tools.files import atomic_write_text


def export_cluster_brief(project_dir: Path, *, max_keywords: int = 200, now: datetime | None = None) -> tuple[dict[str, Any], Path]:
    current = now or datetime.now(timezone.utc)
    keywords = [row for row in _keyword_pool(project_dir) if not row.get("cluster_ref")]
    keywords.sort(key=lambda item: float(item.get("priority_score") or 0), reverse=True)
    keywords = keywords[:max_keywords]
    topics = _existing_topics(project_dir)
    payload = {
        "schema_version": "content-cluster-brief-v1",
        "generated_at": current.isoformat(),
        "keywords": keywords,
        "already_planned_or_published_topics": topics,
        "expected_output_schema": {
            "clusters": [
                {
                    "cluster_name": "string",
                    "representative_kw": "string",
                    "long_tail_kws": ["string"],
                    "member_keywords": ["string"],
                    "intent": "informational|commercial|navigational|mixed",
                    "business_fit": 3,
                    "difficulty_hint": "low|med|high",
                    "traffic_hint": 0,
                    "product_anchor": ["string"],
                    "rationale": "string",
                    "drop_recommendation": False,
                }
            ]
        },
    }
    path = state.safe_project_path(project_dir, f"strategy/briefs/{current.date().isoformat()}-cluster-brief.json")
    path.parent.mkdir(parents=True, exist_ok=True)
    atomic_write_text(path, json.dumps(payload, ensure_ascii=False, indent=2) + "\n")
    return {
        "collection_status": "ok" if keywords else "no_keywords",
        "keyword_count": len(keywords),
        "existing_topic_count": len(topics),
        "path": str(path),
    }, path


def import_clusters(project_dir: Path, from_file: Path, *, now: datetime | None = None) -> tuple[dict[str, Any], Path]:
    current = now or datetime.now(timezone.utc)
    payload = _load_payload(from_file)
    clusters = payload.get("clusters")
    if not isinstance(clusters, list):
        raise ValueError("cluster payload must include clusters list")
    records = [_cluster_record(cluster) for cluster in clusters if isinstance(cluster, dict)]
    _upsert_pipeline(project_dir, records)
    _merge_queue(project_dir, records)
    backlinked = _backlink_keywords(project_dir, records)
    report = {
        "schema_version": "content-cluster-import-v1",
        "collection_status": "ok",
        "imported_at": current.isoformat(),
        "cluster_count": len(records),
        "backlinked_keywords": backlinked,
        "pipeline_path": "content/blog-pipeline.jsonl",
    }
    run_path = state.safe_project_path(project_dir, f"audits/runs/{current.strftime('%Y%m%dT%H%M%SZ')}-content-cluster-import.json")
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
            raise RuntimeError("YAML cluster import requires PyYAML; use JSON or install dev dependencies") from exc
        payload = yaml.safe_load(text)
    if not isinstance(payload, dict):
        raise ValueError("cluster payload must be an object")
    return payload


def _cluster_record(cluster: dict[str, Any]) -> dict[str, Any]:
    name = str(cluster.get("cluster_name") or "").strip()
    if not name:
        raise ValueError("cluster_name is required")
    item_id = str(cluster.get("id") or _safe_id(name))
    status = "dropped" if cluster.get("drop_recommendation") else "planned"
    members = [str(item).strip().lower() for item in cluster.get("member_keywords") or [] if str(item).strip()]
    return {
        "id": item_id,
        "status": status,
        "cluster_name": name,
        "representative_keyword": str(cluster.get("representative_kw") or cluster.get("representative_keyword") or "").strip(),
        "long_tail_keywords": [str(item).strip() for item in cluster.get("long_tail_kws") or [] if str(item).strip()],
        "member_keywords": members,
        "intent": str(cluster.get("intent") or "informational").strip(),
        "business_fit": cluster.get("business_fit") or 3,
        "difficulty_hint": str(cluster.get("difficulty_hint") or "med").strip(),
        "traffic_hint": cluster.get("traffic_hint") or 0,
        "product_anchor": [str(item).strip() for item in cluster.get("product_anchor") or [] if str(item).strip()],
        "cluster_rationale": str(cluster.get("rationale") or cluster.get("cluster_rationale") or "").strip(),
        "drop_reason": "drop_recommendation=true" if cluster.get("drop_recommendation") else "",
        "source_record": {"system": "seo-workbench-cluster-import"},
    }


def _upsert_pipeline(project_dir: Path, records: list[dict[str, Any]]) -> None:
    path = state.safe_project_path(project_dir, "content/blog-pipeline.jsonl")
    by_id = {record["id"]: record for record in records}
    rows = []
    if path.exists():
        for line in path.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            row = json.loads(line)
            if row.get("id") in by_id:
                row.update(by_id.pop(row["id"]))
            rows.append(row)
    rows.extend(by_id.values())
    path.parent.mkdir(parents=True, exist_ok=True)
    atomic_write_text(path, "".join(json.dumps(row, ensure_ascii=False) + "\n" for row in rows))


def _merge_queue(project_dir: Path, records: list[dict[str, Any]]) -> None:
    def mutation(data: dict[str, Any]) -> None:
        queue = data.setdefault("contentQueue", [])
        if not isinstance(queue, list):
            raise ValueError("state.contentQueue must be a list")
        by_id = {item.get("id"): item for item in queue if isinstance(item, dict)}
        for record in records:
            item = by_id.get(record["id"])
            if item is None:
                item = {"id": record["id"]}
                queue.append(item)
            item.update(
                {
                    "status": record["status"],
                    "title": record["cluster_name"],
                    "target_keyword": record["representative_keyword"],
                    "source": record["source_record"],
                }
            )
        state.record_history(data, "content-cluster-import", "STRATEGY", note=f"Imported {len(records)} content clusters")

    state.mutate_state(project_dir, mutation)


def _backlink_keywords(project_dir: Path, records: list[dict[str, Any]]) -> int:
    path = state.safe_project_path(project_dir, "strategy/keyword-pool.jsonl")
    if not path.exists():
        return 0
    clusters_by_keyword = {
        keyword: record["id"]
        for record in records
        for keyword in record.get("member_keywords", [])
    }
    count = 0
    rows = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        row = json.loads(line)
        keyword = str(row.get("keyword") or "").strip().lower()
        if keyword in clusters_by_keyword:
            row["cluster_ref"] = clusters_by_keyword[keyword]
            count += 1
        rows.append(row)
    atomic_write_text(path, "".join(json.dumps(row, ensure_ascii=False) + "\n" for row in rows))
    return count


def _keyword_pool(project_dir: Path) -> list[dict[str, Any]]:
    path = state.safe_project_path(project_dir, "strategy/keyword-pool.jsonl")
    if not path.exists():
        return []
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def _existing_topics(project_dir: Path) -> list[str]:
    path = state.safe_project_path(project_dir, "content/blog-pipeline.jsonl")
    if not path.exists():
        return []
    topics = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        row = json.loads(line)
        if row.get("status") != "dropped":
            topic = row.get("cluster_name") or row.get("title")
            if topic:
                topics.append(str(topic))
    return topics


def _safe_id(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")[:80] or "cluster"
