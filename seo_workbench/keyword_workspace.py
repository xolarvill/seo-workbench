from __future__ import annotations

import hashlib
import json
import re
from collections import Counter, defaultdict
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Literal
from urllib.parse import urlsplit

from seo_workbench import state
from seo_workbench.keywords import normalize_keyword, priority_score
from seo_workbench.locks import project_lock
from seo_workbench_tools.files import atomic_write_text


KeywordDataset = Literal["keywords", "topics", "research"]
KeywordDirection = Literal["asc", "desc"]
KeywordScope = Literal["", "queue", "map"]
DECISIONS = {"unreviewed", "prioritize", "hold", "drop"}
STAGES = {"needs_decision", "needs_mapping", "mapped", "demand_check", "researched", "handed_off", "held", "dropped"}
MAX_BATCH = 1_000
QUEUE_MIN_SCORE = 40.0


@dataclass(frozen=True)
class KeywordWorkspaceQuery:
    dataset: KeywordDataset = "keywords"
    query: str = ""
    decision: str = ""
    stage: str = ""
    intent: str = ""
    source: str = ""
    mapping: str = ""
    scope: KeywordScope = ""
    sort: str = "priority_score"
    direction: KeywordDirection = "desc"
    limit: int = 50
    offset: int = 0

    def __post_init__(self) -> None:
        if self.dataset not in {"keywords", "topics", "research"}:
            raise ValueError("dataset must be keywords, topics, or research")
        if self.direction not in {"asc", "desc"}:
            raise ValueError("direction must be asc or desc")
        if self.scope not in {"", "queue", "map"}:
            raise ValueError("scope must be queue, map, or empty")
        if self.limit < 1 or self.limit > MAX_BATCH:
            raise ValueError("limit must be between 1 and 1000")
        if self.offset < 0:
            raise ValueError("offset must be non-negative")


def query_keyword_workspace(project_dir: Path, query: KeywordWorkspaceQuery) -> dict[str, Any]:
    data = _workspace_data(project_dir)
    rows = _filter(data["rows"], query)
    if query.dataset == "topics":
        rows = _topic_rows(rows)
    elif query.dataset == "research":
        rows = [row for row in rows if row.get("research_path") or row.get("decision") == "prioritize"]
    if query.scope == "queue":
        rows = [row for row in rows if _in_queue(row)]
    elif query.scope == "map":
        rows = [row for row in rows if not _in_queue(row)]
    observed = [row for row in rows if _sort_value(row, query.sort) is not None]
    missing = [row for row in rows if _sort_value(row, query.sort) is None]
    observed.sort(key=lambda row: _sort_value(row, query.sort), reverse=query.direction == "desc")
    rows = [*observed, *missing]
    total = len(rows)
    return {
        "ok": True,
        "dataset": query.dataset,
        "scope": query.scope,
        "rows": rows[query.offset : query.offset + query.limit],
        "pagination": {"offset": query.offset, "limit": query.limit, "total": total},
        "summary": _summary(data["rows"]),
        "facets": _facets(data["rows"]),
        "sources": data["sources"],
        "options": data["options"],
        "revision": data["revision"],
    }


def update_keywords(
    project_dir: Path,
    keywords: list[str],
    patch: dict[str, Any],
    base_revision: str,
    *,
    lock_root: Path | None = None,
    now: datetime | None = None,
) -> dict[str, Any]:
    normalized = list(dict.fromkeys(normalize_keyword(item) for item in keywords if normalize_keyword(item)))
    if not normalized:
        raise ValueError("at least one keyword is required")
    if len(normalized) > MAX_BATCH:
        raise ValueError("a keyword update is limited to 1000 rows")
    allowed = {"decision", "cluster_ref", "target_url", "target_content_id", "note"}
    if not patch or set(patch) - allowed:
        raise ValueError("patch must contain only editable keyword fields")

    pool_path = state.safe_project_path(project_dir, "strategy/keyword-pool.jsonl")
    lock_args = {"lock_root": lock_root} if lock_root is not None else {}
    with project_lock(project_dir, **lock_args):
        current_bytes = pool_path.read_bytes() if pool_path.exists() else b""
        current_revision = _revision(current_bytes)
        if current_revision != base_revision:
            raise RuntimeError(current_revision)

        data = _workspace_data(project_dir)
        by_keyword = {row["keyword"]: row for row in data["rows"]}
        missing = [keyword for keyword in normalized if keyword not in by_keyword]
        if missing:
            raise ValueError(f"unknown keyword: {missing[0]}")
        cleaned = _validate_patch(project_dir, patch, data["options"])

        pool_rows = _jsonl(pool_path)
        indexed = {normalize_keyword(str(row.get("keyword") or "")): row for row in pool_rows}
        updated_at = (now or datetime.now(timezone.utc)).isoformat()
        for keyword in normalized:
            row = indexed.get(keyword)
            if row is None:
                candidate = by_keyword[keyword]
                metrics = candidate.get("gsc") or {}
                row = {
                    "keyword": keyword,
                    "source": candidate.get("source") or "gsc",
                    "volume_hint": candidate.get("volume_hint") or metrics.get("impressions") or 0,
                    "ctr_hint": candidate.get("ctr_hint") or (metrics.get("ctr") or 0) * 100,
                    "position_hint": candidate.get("position_hint") or metrics.get("position") or 0,
                    "intent": candidate.get("intent") or "",
                    "priority_score": candidate.get("priority_score") or 0,
                }
                pool_rows.append(row)
                indexed[keyword] = row
            row.update(cleaned)
            row["updated_at"] = updated_at
        pool_path.parent.mkdir(parents=True, exist_ok=True)
        serialized = "".join(json.dumps(row, ensure_ascii=False) + "\n" for row in pool_rows)
        atomic_write_text(pool_path, serialized)
    return {"ok": True, "updated": len(normalized), "revision": _revision(serialized.encode())}


def keyword_handoff(project_dir: Path, keyword: str) -> dict[str, Any]:
    normalized = normalize_keyword(keyword)
    data = _workspace_data(project_dir)
    row = next((item for item in data["rows"] if item["keyword"] == normalized), None)
    if row is None:
        raise ValueError("keyword not found")
    if row.get("research_path"):
        return {
            "ok": True,
            "keyword": normalized,
            "existing_path": row["research_path"],
            "skill": "skills/keyword-deep-dive/SKILL.md",
        }
    prefix = "product" if row.get("intent") in {"commercial", "transactional"} else "info"
    output = f"strategy/keyword-dives/{prefix}-{_slug(normalized)}.md"
    context = [
        path
        for path in (
            "strategy/keyword-pool.jsonl",
            "context/target-keywords.md",
            "audits/gsc/search-analytics/latest.json",
            "audits/content-portfolio/latest.json",
        )
        if (project_dir / path).exists()
    ]
    target = row.get("target_url") or "unassigned"
    prompt = (
        "Use skills/keyword-deep-dive/SKILL.md to research "
        f'\"{normalized}\". Read the available project evidence ({", ".join(context) or "none"}); '
        f"current target URL: {target}. Write the result to {output}. "
        "Do not create a second metrics store, and treat missing evidence as unknown rather than zero."
    )
    return {
        "ok": True,
        "keyword": normalized,
        "existing_path": None,
        "skill": "skills/keyword-deep-dive/SKILL.md",
        "context": context,
        "output_path": output,
        "prompt": prompt,
    }


def _workspace_data(project_dir: Path) -> dict[str, Any]:
    pool_path = state.safe_project_path(project_dir, "strategy/keyword-pool.jsonl")
    pool_bytes = pool_path.read_bytes() if pool_path.exists() else b""
    pool = _jsonl(pool_path)
    project_state = state.load_state(project_dir)
    queue = [item for item in project_state.get("contentQueue", []) if isinstance(item, dict)]
    pipeline = _jsonl(state.safe_project_path(project_dir, "content/blog-pipeline.jsonl"))
    contents = {str(item.get("id")): item for item in [*pipeline, *queue] if item.get("id")}
    clusters = {str(item.get("id")): item for item in pipeline if item.get("id")}
    gsc, gsc_meta = _gsc(project_dir)
    market, market_meta = _dataforseo(project_dir)
    portfolio, portfolio_meta = _portfolio(project_dir)
    dives = _dives(project_dir)

    combined: dict[str, dict[str, Any]] = {}
    for row in pool:
        keyword = normalize_keyword(str(row.get("keyword") or ""))
        if keyword:
            combined[keyword] = _keyword_row(keyword, row, True)
    for keyword, metrics in gsc.items():
        row = combined.setdefault(keyword, _keyword_row(keyword, {"source": "gsc"}, False))
        row["gsc"] = metrics
        if not row.get("volume_hint"):
            row["volume_hint"] = metrics["impressions"]
        if not row.get("priority_score"):
            row["priority_score"] = priority_score("gsc", metrics["impressions"], 0, 0, row.get("intent", ""))
    for item in contents.values():
        keyword = normalize_keyword(str(item.get("target_keyword") or item.get("representative_keyword") or ""))
        if keyword:
            combined.setdefault(keyword, _keyword_row(keyword, {"source": "content"}, False))

    owners: dict[str, list[str]] = defaultdict(list)
    portfolio_urls: set[str] = set()
    for item in portfolio:
        url = str(item.get("url") or item.get("row_key") or "")
        if url:
            portfolio_urls.add(url)
        for query in item.get("top_queries") or []:
            if isinstance(query, dict):
                value = normalize_keyword(str(query.get("query") or query.get("keys", [""])[0]))
                if value and url and url not in owners[value]:
                    owners[value].append(url)

    for keyword, row in combined.items():
        row["market"] = market.get(keyword)
        if not row.get("intent") and row["market"]:
            row["intent"] = str(row["market"].get("intent") or "")
        row["research_path"] = dives.get(keyword)
        row["research_updated_at"] = (
            datetime.fromtimestamp((project_dir / row["research_path"]).stat().st_mtime, timezone.utc).isoformat()
            if row["research_path"]
            else None
        )
        row["owner_urls"] = owners.get(keyword, [])
        row["mapping_conflict"] = len(row["owner_urls"]) > 1
        content = contents.get(str(row.get("target_content_id") or ""))
        row["content"] = _content_summary(content)
        row["mapping"] = "mapped" if _is_mapped(row) else "unmapped"

    cluster_members: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in combined.values():
        if row.get("cluster_ref"):
            cluster_members[str(row["cluster_ref"])].append(row)
    for row in combined.values():
        members = cluster_members.get(str(row.get("cluster_ref") or ""), [row])
        row["observed_queries"] = _query_evidence(members)
        row["cluster_gsc"] = _aggregate_gsc(row["observed_queries"])
        row["cluster_mapping_conflict"] = any(len(item["owner_urls"]) > 1 for item in row["observed_queries"])
        content = contents.get(str(row.get("target_content_id") or ""))
        row["stage"] = _stage(row, content, portfolio_urls)

    return {
        "rows": list(combined.values()),
        "revision": _revision(pool_bytes),
        "sources": {
            "keyword_pool": {"path": "strategy/keyword-pool.jsonl", "count": len(pool)},
            "gsc": gsc_meta,
            "dataforseo": market_meta,
            "portfolio": portfolio_meta,
            "research": {"path": "strategy/keyword-dives", "count": len(dives)},
        },
        "options": {
            "clusters": [{"id": key, "label": str(value.get("cluster_name") or value.get("title") or key)} for key, value in clusters.items()],
            "content_items": [{"id": key, "label": str(value.get("title") or key), "status": value.get("status", "")} for key, value in contents.items()],
        },
    }


def _keyword_row(keyword: str, source: dict[str, Any], managed: bool) -> dict[str, Any]:
    cluster_ref = source.get("cluster_ref")
    if isinstance(cluster_ref, list):
        cluster_ref = str(cluster_ref[0]) if cluster_ref else ""
    decision = str(source.get("decision") or "unreviewed")
    return {
        "row_key": keyword,
        "keyword": keyword,
        "managed": managed,
        "source": str(source.get("source") or "unknown"),
        "intent": str(source.get("intent") or ""),
        "priority_score": _number(source.get("priority_score")),
        "volume_hint": _number(source.get("volume_hint")),
        "ctr_hint": _number(source.get("ctr_hint")),
        "position_hint": _number(source.get("position_hint")),
        "kd_hint": _number(source.get("kd_hint")),
        "cpc_hint": _number(source.get("cpc_hint")),
        "decision": decision if decision in DECISIONS else "unreviewed",
        "cluster_ref": str(cluster_ref or ""),
        "target_url": str(source.get("target_url") or ""),
        "target_content_id": str(source.get("target_content_id") or ""),
        "note": str(source.get("note") or ""),
        "updated_at": source.get("updated_at"),
        "gsc": None,
    }


def _gsc(project_dir: Path) -> tuple[dict[str, dict[str, Any]], dict[str, Any]]:
    path = project_dir / "audits/gsc/search-analytics/latest.json"
    payload = _json(path)
    rows = (((payload.get("windows") or {}).get("current") or {}).get("query") or {}).get("rows") or []
    result: dict[str, dict[str, Any]] = {}
    for row in rows:
        if not isinstance(row, dict):
            continue
        keys = row.get("keys") or []
        raw_query = str(keys[0] if keys else "").strip()
        keyword = normalize_keyword(raw_query)
        if keyword:
            incoming = {
                "query": raw_query,
                "raw_queries": [raw_query],
                "clicks": _number(row.get("clicks")),
                "impressions": _number(row.get("impressions")),
                "ctr": _number(row.get("ctr")),
                "position": _number(row.get("position")),
            }
            existing = result.get(keyword)
            if existing is None:
                result[keyword] = incoming
                continue
            previous_impressions = existing["impressions"]
            impressions = previous_impressions + incoming["impressions"]
            clicks = existing["clicks"] + incoming["clicks"]
            existing.update(
                {
                    "raw_queries": list(dict.fromkeys([*existing["raw_queries"], raw_query])),
                    "clicks": clicks,
                    "impressions": impressions,
                    "ctr": clicks / impressions if impressions else 0.0,
                    "position": (
                        (existing["position"] * previous_impressions + incoming["position"] * incoming["impressions"])
                        / impressions
                        if impressions
                        else 0.0
                    ),
                }
            )
    return result, {
        "path": "audits/gsc/search-analytics/latest.json",
        "collection_status": payload.get("collection_status", "not_collected"),
        "generated_at": payload.get("generated_at"),
        "count": len(result),
    }


def _portfolio(project_dir: Path) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    payload = _json(project_dir / "audits/content-portfolio/latest.json")
    items = [item for item in payload.get("items", []) if isinstance(item, dict)]
    return items, {
        "path": "audits/content-portfolio/latest.json",
        "collection_status": payload.get("collection_status", "not_collected"),
        "generated_at": payload.get("generated_at"),
        "count": len(items),
    }


def _dataforseo(project_dir: Path) -> tuple[dict[str, dict[str, Any]], dict[str, Any]]:
    payload = _json(project_dir / "audits/keywords/dataforseo/latest.json")
    items = [item for item in payload.get("items", []) if isinstance(item, dict)]
    result = {
        keyword: item
        for item in items
        if (keyword := normalize_keyword(str(item.get("keyword") or "")))
    }
    return result, {
        "path": "audits/keywords/dataforseo/latest.json",
        "collection_status": payload.get("collection_status", "not_collected"),
        "generated_at": payload.get("generated_at"),
        "count": len(result),
    }


def _dives(project_dir: Path) -> dict[str, str]:
    root = project_dir / "strategy/keyword-dives"
    found: dict[str, str] = {}
    if not root.is_dir():
        return found
    for path in sorted(root.glob("*.md")):
        text = path.read_text(encoding="utf-8")[:4_000]
        match = re.search(r"(?:Primary keyword|Keyword deep dive):\s*(?:\*\*)?([^\n*]+)", text, re.IGNORECASE)
        keyword = normalize_keyword(match.group(1)) if match else re.sub(r"^(?:product|info)-", "", path.stem).replace("-", " ")
        if keyword:
            found[keyword] = path.relative_to(project_dir).as_posix()
    return found


def _stage(row: dict[str, Any], content: dict[str, Any] | None, portfolio_urls: set[str]) -> str:
    """Keyword-side pipeline state (steps 0-4 + gate). Content-side status lives on the linked content item."""
    del portfolio_urls
    decision = str(row.get("decision") or "unreviewed")
    if decision == "drop":
        return "dropped"
    if decision == "hold":
        return "held"
    if content:
        return "handed_off"
    if row.get("research_path"):
        return "researched"
    if row.get("market"):
        return "demand_check"
    if _is_mapped(row):
        return "mapped"
    return "needs_decision" if decision == "unreviewed" else "needs_mapping"


def _in_queue(row: dict[str, Any]) -> bool:
    """Decision queue membership: rows that need operator judgment now."""
    decision = str(row.get("decision") or "unreviewed")
    if decision == "prioritize":
        return True
    if decision == "unreviewed":
        if row.get("managed"):
            return True
        if row.get("mapping_conflict"):
            return True
        return (row.get("priority_score") or 0) >= QUEUE_MIN_SCORE
    return False


def _filter(rows: list[dict[str, Any]], query: KeywordWorkspaceQuery) -> list[dict[str, Any]]:
    needle = query.query.strip().casefold()
    stages = {value.strip() for value in query.stage.split(",") if value.strip()}
    return [
        row
        for row in rows
        if (not needle or needle in row["keyword"].casefold() or needle in str(row.get("note", "")).casefold())
        and (not query.decision or row.get("decision") == query.decision)
        and (not stages or row.get("stage") in stages)
        and (not query.intent or row.get("intent") == query.intent)
        and (not query.source or row.get("source") == query.source)
        and (not query.mapping or row.get("mapping") == query.mapping)
    ]


def _topic_rows(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    groups: dict[tuple[str, ...], list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        cluster_ref = str(row.get("cluster_ref") or "")
        key = ("cluster", cluster_ref) if cluster_ref else (
            "mapping",
            str(row.get("target_url") or ""),
            str(row.get("target_content_id") or ""),
        )
        groups[key].append(row)
    result = []
    for key, members in groups.items():
        cluster_ref = key[1] if key[0] == "cluster" else ""
        target_urls = sorted({str(row.get("target_url")) for row in members if row.get("target_url")})
        content_ids = sorted({str(row.get("target_content_id")) for row in members if row.get("target_content_id")})
        evidence = _query_evidence(members)
        aggregate = _aggregate_gsc(evidence)
        representative = max(members, key=lambda row: (row.get("priority_score") or 0, row["keyword"]))
        result.append({
            "row_key": cluster_ref or "|".join(key),
            "cluster_ref": cluster_ref,
            "representative_keyword": representative["keyword"],
            "target_url": target_urls[0] if len(target_urls) == 1 else "",
            "target_urls": target_urls,
            "target_content_id": content_ids[0] if len(content_ids) == 1 else "",
            "target_content_ids": content_ids,
            "keyword_count": len(members),
            "keywords": [row["keyword"] for row in members[:8]],
            "observed_queries": evidence,
            "query_count": len(evidence),
            "unassigned": not any((cluster_ref, target_urls, content_ids)),
            "missing_content": bool(cluster_ref and not target_urls and not content_ids),
            "target_conflict": len(target_urls) > 1,
            "content_conflict": len(content_ids) > 1,
            "ownership_conflict": any(len(item["owner_urls"]) > 1 for item in evidence),
            "priority_score": max((row.get("priority_score") or 0 for row in members), default=0),
            "impressions": (aggregate or {}).get("impressions"),
        })
    return result


def _query_evidence(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    evidence = []
    for row in rows:
        metrics = row.get("gsc")
        if not metrics:
            continue
        evidence.append(
            {
                "query": metrics.get("query") or row["keyword"],
                "raw_queries": list(metrics.get("raw_queries") or [metrics.get("query") or row["keyword"]]),
                "clicks": metrics["clicks"],
                "impressions": metrics["impressions"],
                "ctr": metrics["ctr"],
                "position": metrics["position"],
                "owner_urls": list(row.get("owner_urls") or []),
            }
        )
    return sorted(evidence, key=lambda item: str(item["query"]).casefold())


def _aggregate_gsc(evidence: list[dict[str, Any]]) -> dict[str, float] | None:
    if not evidence:
        return None
    clicks = sum(item["clicks"] for item in evidence)
    impressions = sum(item["impressions"] for item in evidence)
    return {
        "clicks": clicks,
        "impressions": impressions,
        "ctr": clicks / impressions if impressions else 0.0,
        "position": (
            sum(item["position"] * item["impressions"] for item in evidence) / impressions
            if impressions
            else 0.0
        ),
    }


def _validate_patch(project_dir: Path, patch: dict[str, Any], options: dict[str, Any]) -> dict[str, Any]:
    cleaned = dict(patch)
    if "decision" in cleaned and cleaned["decision"] not in DECISIONS:
        raise ValueError("decision must be unreviewed, prioritize, hold, or drop")
    cluster_ids = {item["id"] for item in options["clusters"]}
    if "cluster_ref" in cleaned and cleaned["cluster_ref"] and cleaned["cluster_ref"] not in cluster_ids:
        raise ValueError("cluster_ref does not exist")
    content_ids = {item["id"] for item in options["content_items"]}
    if "target_content_id" in cleaned and cleaned["target_content_id"] and cleaned["target_content_id"] not in content_ids:
        raise ValueError("target_content_id does not exist")
    if "target_url" in cleaned:
        cleaned["target_url"] = _validate_target_url(project_dir, str(cleaned["target_url"] or ""))
    for field in ("cluster_ref", "target_content_id", "note"):
        if field in cleaned:
            cleaned[field] = str(cleaned[field] or "").strip()
    return cleaned


def _validate_target_url(project_dir: Path, value: str) -> str:
    value = value.strip()
    if not value:
        return ""
    if value.startswith("/") and not value.startswith("//"):
        return value
    parsed = urlsplit(value)
    project_url = str(state.load_state(project_dir).get("project", {}).get("url") or "")
    host = (urlsplit(project_url).hostname or "").lower().removeprefix("www.")
    target_host = (parsed.hostname or "").lower().removeprefix("www.")
    if parsed.scheme not in {"http", "https"} or target_host != host:
        raise ValueError("target_url must be a same-domain URL or site path")
    return value


def _summary(rows: list[dict[str, Any]]) -> dict[str, Any]:
    queue = [row for row in rows if _in_queue(row)]
    return {
        "total": len(rows),
        "queue": len(queue),
        "queue_stages": dict(Counter(str(row.get("stage")) for row in queue)),
        "unmanaged": sum(not row.get("managed") for row in rows),
        "unmapped": sum(row.get("mapping") == "unmapped" for row in rows),
        "decisions": dict(Counter(str(row.get("decision")) for row in rows)),
        "stages": dict(Counter(str(row.get("stage")) for row in rows)),
    }


def _facets(rows: list[dict[str, Any]]) -> dict[str, list[str]]:
    return {
        key: sorted({str(row.get(key)) for row in rows if row.get(key)})
        for key in ("decision", "stage", "intent", "source", "mapping")
    }


def _sort_value(row: dict[str, Any], field: str) -> Any:
    if field in {"impressions", "clicks", "position"}:
        exact = (row.get("gsc") or {}).get(field)
        return exact if exact is not None else row.get(field)
    if field == "research_updated_at":
        return row.get("research_updated_at")
    market = row.get("market") or {}
    if field == "volume":
        return market.get("search_volume") if market.get("search_volume") is not None else (
            row.get("volume_hint") if row.get("source") in {"semrush_manual", "ads"} else None
        )
    if field == "cpc":
        return market.get("cpc") if market.get("cpc") is not None else (
            row.get("cpc_hint") if row.get("source") in {"semrush_manual", "ads"} else None
        )
    if field == "competition":
        return market.get("competition")
    value = row.get(field)
    return value.casefold() if isinstance(value, str) else value


def _is_mapped(row: dict[str, Any]) -> bool:
    return any(row.get(field) for field in ("cluster_ref", "target_url", "target_content_id"))


def _content_summary(content: dict[str, Any] | None) -> dict[str, Any] | None:
    if not content:
        return None
    return {key: content.get(key) for key in ("id", "title", "status", "target_keyword", "live_url")}


def _url_observed(url: str, observed: set[str]) -> bool:
    path = urlsplit(url).path.rstrip("/")
    return any(url == item or (path and urlsplit(item).path.rstrip("/") == path) for item in observed)


def _json(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    return payload if isinstance(payload, dict) else {}


def _jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.is_file():
        return []
    rows = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        row = json.loads(line)
        if isinstance(row, dict):
            rows.append(row)
    return rows


def _revision(content: bytes) -> str:
    return hashlib.sha256(content).hexdigest()


def _number(value: Any) -> float:
    try:
        return float(value or 0)
    except (TypeError, ValueError):
        return 0.0


def _slug(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", value.casefold()).strip("-")[:100] or "keyword"
