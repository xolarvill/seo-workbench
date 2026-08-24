from __future__ import annotations

import json
import os
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from seo_workbench import state
from seo_workbench_tools.files import atomic_write_text


TAVILY_ENDPOINT = "https://api.tavily.com/search"
DEFAULT_EXCLUDE_DOMAINS = (
    "reddit.com",
    "wikipedia.org",
    "amazon.com",
    "pinterest.com",
    "youtube.com",
    "quora.com",
    "facebook.com",
    "instagram.com",
    "tiktok.com",
)


def write_serp_competitors(
    project_dir: Path,
    item_id: str,
    *,
    query: str = "",
    api_key: str = "",
    max_results: int = 3,
    timeout: float = 20,
    requester: Any = None,
    now: datetime | None = None,
) -> tuple[dict[str, Any], Path]:
    current = now or datetime.now(timezone.utc)
    record = _find_record(project_dir, item_id)
    search_query = (
        query
        or record.get("target_keyword")
        or record.get("representative_kw")
        or record.get("representative_keyword")
        or record.get("cluster_name")
        or ""
    )
    if not str(search_query).strip():
        raise ValueError("SERP query is empty; pass --query or set target keyword")
    key = api_key or os.environ.get("TAVILY_API_KEY", "")
    if not key:
        raise ValueError("TAVILY_API_KEY is not set")
    requester = requester or _tavily_search
    result_limit = max(1, min(max_results, 20))
    raw = requester(str(search_query), api_key=key, max_results=result_limit, timeout=timeout)
    competitors = _compact_results(raw.get("results") or [], limit=result_limit)
    report = {
        "schema_version": "content-serp-competitors-v1",
        "collection_status": "ok",
        "generated_at": current.isoformat(),
        "item_id": item_id,
        "query": str(search_query),
        "provider": "tavily",
        "competitor_count": len(competitors),
        "competitors": competitors,
        "source": {"response_time": raw.get("response_time"), "request_id": raw.get("request_id", "")},
    }
    path = state.safe_project_path(project_dir, f"strategy/briefs/{_safe_name(item_id)}-serp.json")
    path.parent.mkdir(parents=True, exist_ok=True)
    atomic_write_text(path, json.dumps(report, ensure_ascii=False, indent=2) + "\n", mode=0o600)
    return report, path


def _tavily_search(query: str, *, api_key: str, max_results: int, timeout: float) -> dict[str, Any]:
    payload = {
        "query": query,
        "max_results": max_results,
        "search_depth": "basic",
        "include_answer": False,
        "exclude_domains": list(DEFAULT_EXCLUDE_DOMAINS),
    }
    request = Request(
        TAVILY_ENDPOINT,
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}",
            "User-Agent": "SEO-Workbench/0.2",
        },
        method="POST",
    )
    try:
        with urlopen(request, timeout=timeout) as response:
            body = response.read(1_000_001)
    except HTTPError as exc:
        raise ValueError(f"Tavily returned HTTP {exc.code}") from exc
    except (OSError, URLError) as exc:
        raise ValueError("Tavily could not be reached") from exc
    if len(body) > 1_000_000:
        raise ValueError("Tavily response exceeded the safety limit")
    try:
        data = json.loads(body)
    except json.JSONDecodeError as exc:
        raise ValueError("Tavily returned invalid JSON") from exc
    if not isinstance(data, dict):
        raise ValueError("Tavily returned an invalid payload")
    return data


def _compact_results(results: list[Any], *, limit: int) -> list[dict[str, Any]]:
    competitors = []
    for item in results:
        if not isinstance(item, dict) or not item.get("url"):
            continue
        competitors.append(
            {
                "title": str(item.get("title") or "").strip(),
                "url": str(item.get("url") or "").strip(),
                "snippet": str(item.get("content") or item.get("snippet") or "").strip()[:500],
                "score": float(item.get("score") or 0.0),
            }
        )
        if len(competitors) >= limit:
            break
    return competitors


def _find_record(project_dir: Path, item_id: str) -> dict[str, Any]:
    path = state.safe_project_path(project_dir, "content/blog-pipeline.jsonl")
    if not path.exists():
        raise FileNotFoundError(f"{path} not found; import content first")
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.strip():
            record = json.loads(line)
            if record.get("id") == item_id:
                return record
    raise ValueError(f"content pipeline item not found: {item_id}")


def _safe_name(value: str) -> str:
    return re.sub(r"[^A-Za-z0-9_.-]+", "-", value).strip("-") or "serp"
