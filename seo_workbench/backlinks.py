from __future__ import annotations

import csv
import hashlib
import json
import re
from collections import Counter
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Literal
from urllib.parse import urljoin, urlsplit

from seo_workbench import dataforseo, state
from seo_workbench.tech_audit import link_scope, load_tech_inventory, normalize_url
from seo_workbench_tools.files import atomic_write_text


STATUSES = {"active", "lost"}
STATUS_ALIASES = {"live": "active", "found": "active", "removed": "lost", "deleted": "lost"}
MAX_LINKS = 250_000
DATAFORSEO_MAX_LINKS = 20_000

BacklinkSort = Literal["source_domain", "provider_status", "target_url", "target_status_code", "follow"]
BacklinkDirection = Literal["asc", "desc"]

BACKLINK_VIEW_COLUMNS: tuple[dict[str, Any], ...] = (
    {"id": "source_domain", "label": "Referring domain", "default": True},
    {"id": "source_url", "label": "Source URL", "default": True},
    {"id": "target_url", "label": "Target URL", "default": True},
    {"id": "anchor", "label": "Anchor", "default": True},
    {"id": "provider_status", "label": "Status", "default": True},
    {"id": "follow", "label": "Follow", "default": True},
    {"id": "target_status_code", "label": "Target HTTP", "default": True},
    {"id": "target_reclaim_candidate", "label": "Reclaim", "default": True},
)


@dataclass(frozen=True)
class BacklinkViewQuery:
    query: str = ""
    status: str = ""
    follow: str = ""
    reclaim_only: bool = False
    sort: BacklinkSort = "source_domain"
    direction: BacklinkDirection = "asc"
    limit: int = 50
    offset: int = 0

    def __post_init__(self) -> None:
        if self.status and self.status not in STATUSES:
            raise ValueError("status must be active or lost")
        if self.follow and self.follow not in {"follow", "nofollow", "unknown"}:
            raise ValueError("follow must be follow, nofollow, or unknown")
        if self.sort not in {"source_domain", "provider_status", "target_url", "target_status_code", "follow"}:
            raise ValueError("unsupported backlink sort field")
        if self.direction not in {"asc", "desc"}:
            raise ValueError("direction must be asc or desc")
        if self.limit < 1 or self.limit > 200:
            raise ValueError("limit must be between 1 and 200")
        if self.offset < 0:
            raise ValueError("offset must be non-negative")


def import_backlink_snapshot(
    project_dir: Path,
    source_path: Path,
    *,
    source: str,
    complete: bool = False,
    captured_at: str = "",
    now: datetime | None = None,
    allow_empty: bool = False,
    provider: dict[str, Any] | None = None,
) -> tuple[dict[str, Any], Path]:
    source = source.strip()
    source_id = _safe_id(source)
    if not source or not source_id or len(source) > 100 or "\n" in source or "\r" in source:
        raise ValueError("backlink source is required")
    rows = _source_rows(source_path, allow_empty=allow_empty)
    if len(rows) > MAX_LINKS:
        raise ValueError(f"backlink snapshot exceeds {MAX_LINKS} rows")
    project_url = normalize_url(str((state.load_state(project_dir).get("project") or {}).get("url", "")))
    if not project_url:
        raise ValueError("project.url must be an absolute HTTP(S) URL")
    technical_snapshot_path = state.safe_project_path(project_dir, "audits/tech-audit/latest.json")
    technical_snapshot = _optional_json(technical_snapshot_path) or {}
    target_status = {
        normalize_url(str(page.get("url", ""))): int(page.get("status_code") or 0)
        for page in load_tech_inventory(project_dir)
        if isinstance(page, dict) and normalize_url(str(page.get("url", "")))
    }

    links: dict[str, dict[str, Any]] = {}
    for row in rows:
        source_url = normalize_url(str(row.get("source_url") or row.get("source") or ""))
        target_url = normalize_url(str(row.get("target_url") or row.get("target") or ""))
        if not source_url or link_scope(source_url, project_url)[1] != "external":
            raise ValueError(f"backlink source URL must be external to the project site: {row.get('source_url', '')}")
        if not target_url or link_scope(target_url, project_url)[1] not in {"same_host", "subdomain"}:
            raise ValueError(f"backlink target URL is outside the project site family: {row.get('target_url', '')}")
        provider_status = STATUS_ALIASES.get(str(row.get("status", "active")).strip().lower(), str(row.get("status", "active")).strip().lower())
        if provider_status not in STATUSES:
            raise ValueError(f"backlink status must be active or lost: {row.get('status', '')}")
        link_id = hashlib.sha256(f"{source_url}\n{target_url}".encode()).hexdigest()[:20]
        code = target_status.get(target_url, 0)
        links[link_id] = {
            "id": link_id,
            "source_url": source_url,
            "source_domain": (urlsplit(source_url).hostname or "").lower(),
            "target_url": target_url,
            "anchor": str(row.get("anchor") or row.get("anchor_text") or "").strip()[:1000],
            "follow": _follow(row),
            "provider_status": provider_status,
            "first_seen": str(row.get("first_seen") or "").strip()[:100],
            "last_seen": str(row.get("last_seen") or "").strip()[:100],
            "target_status_code": code or None,
            "target_reclaim_candidate": code in {404, 410},
        }

    generated_at = (now or datetime.now(timezone.utc)).astimezone(timezone.utc)
    captured = _captured_at(captured_at, generated_at)
    output_dir = state.safe_project_path(project_dir, "audits/backlinks")
    snapshots_dir = output_dir / "snapshots"
    diffs_dir = output_dir / "diffs"
    snapshots_dir.mkdir(parents=True, exist_ok=True)
    diffs_dir.mkdir(parents=True, exist_ok=True)
    source_latest = output_dir / f"latest-{source_id}.json"
    baseline = _optional_json(source_latest)
    comparison = _compare(baseline, links, current_complete=complete)
    active = [link for link in links.values() if link["provider_status"] == "active"]
    report = {
        "schema_version": "backlink-snapshot-v1",
        "collection_status": "ok",
        "generated_at": generated_at.isoformat(),
        "captured_at": captured,
        "source": {"name": source, "id": source_id, "input_path": str(source_path)},
        "provider": provider or {},
        "target_status_evidence": {
            "path": str(technical_snapshot_path) if technical_snapshot else "",
            "generated_at": technical_snapshot.get("generated_at", ""),
            "run_id": technical_snapshot.get("run_id", ""),
            "collection_status": technical_snapshot.get("collection_status", "not_collected"),
        },
        "complete_snapshot": complete,
        "summary": {
            "links": len(links),
            "active_links": len(active),
            "provider_reported_lost": sum(link["provider_status"] == "lost" for link in links.values()),
            "referring_domains": len({link["source_domain"] for link in active}),
            "target_pages": len({link["target_url"] for link in active}),
            "follow": dict(sorted(Counter("unknown" if link["follow"] is None else "follow" if link["follow"] else "nofollow" for link in active).items())),
            "target_reclaim_candidates": sum(link["target_reclaim_candidate"] for link in active),
        },
        "top_anchors": [
            {"anchor": anchor, "count": count}
            for anchor, count in Counter(link["anchor"] or "(empty)" for link in active).most_common(20)
        ],
        "comparison": comparison,
        "links": sorted(links.values(), key=lambda link: (link["source_domain"], link["source_url"], link["target_url"])),
        "claims": {
            "authority_score": "not_calculated",
            "toxicity_score": "not_calculated",
            "absence_rule": "A missing link is classified as lost only when both same-source snapshots are marked complete.",
        },
    }
    path = snapshots_dir / f"backlinks-{source_id}-{generated_at.strftime('%Y%m%dT%H%M%S%fZ')}.json"
    _write_json(path, report)
    _write_json(source_latest, report)
    _write_json(output_dir / "latest.json", report)
    diff_path = diffs_dir / f"diff-{source_id}-{generated_at.strftime('%Y%m%dT%H%M%S%fZ')}.json"
    _write_json(diff_path, {"schema_version": "backlink-diff-v1", "generated_at": generated_at.isoformat(), "source": report["source"], **comparison})
    _write_json(output_dir / f"diff-latest-{source_id}.json", {"schema_version": "backlink-diff-v1", "generated_at": generated_at.isoformat(), "source": report["source"], **comparison})
    _write_markdown(
        state.safe_project_path(project_dir, "audits/backlinks-report.md"),
        report,
        path.relative_to(project_dir),
    )
    if baseline:
        _write_markdown(
            state.safe_project_path(project_dir, "audits/backlinks-recheck.md"),
            report,
            path.relative_to(project_dir),
        )
    return report, path


def collect_dataforseo_backlinks(
    project_dir: Path,
    *,
    confirm_paid: bool,
    max_links: int = 10_000,
    timeout: float = 45,
    requester: Callable[..., dict[str, Any]] = dataforseo.post,
    now: datetime | None = None,
) -> tuple[dict[str, Any], Path]:
    if not confirm_paid:
        raise ValueError("DataForSEO backlink collection is paid; pass --confirm-paid")
    if not 1 <= max_links <= DATAFORSEO_MAX_LINKS:
        raise ValueError(f"max-links must be between 1 and {DATAFORSEO_MAX_LINKS}")
    project_url = normalize_url(str((state.load_state(project_dir).get("project") or {}).get("url", "")))
    target = _domain_target(project_url)
    endpoint = "/v3/backlinks/backlinks/live"
    provider_items: list[dict[str, Any]] = []
    requests: list[dict[str, Any]] = []
    total_count = 0
    offset = 0
    while len(provider_items) < max_links:
        task: dict[str, Any] = {
            "target": target,
            "mode": "one_per_domain",
            "backlinks_status_type": "live",
            "include_subdomains": True,
            "exclude_internal_backlinks": True,
            "limit": min(1_000, max_links - len(provider_items)),
            "offset": offset,
        }
        task_result, result = _provider_result(requester(project_dir, endpoint, task, timeout))
        batch = [item for item in result.get("items") or [] if isinstance(item, dict)]
        total_count = max(total_count, len(provider_items) + len(batch), _provider_total(result))
        provider_items.extend(batch)
        requests.append({"task_id": task_result.get("id", ""), "cost_usd": float(task_result.get("cost") or 0)})
        if not batch or len(provider_items) >= total_count:
            break
        offset += len(batch)

    observed = (now or datetime.now(timezone.utc)).astimezone(timezone.utc)
    complete = len(provider_items) >= total_count
    rows = [
        {
            "source_url": item.get("url_from"),
            "target_url": item.get("url_to"),
            "anchor": item.get("anchor") or "",
            "follow": item.get("dofollow"),
            "status": "lost" if item.get("is_lost") is True else "active",
            "first_seen": item.get("first_seen") or "",
            "last_seen": item.get("last_seen") or "",
        }
        for item in provider_items
    ]
    raw_dir = state.safe_project_path(project_dir, "audits/backlinks/dataforseo/raw")
    raw_dir.mkdir(parents=True, exist_ok=True, mode=0o700)
    raw_path = raw_dir / f"backlinks-{observed.strftime('%Y%m%dT%H%M%S%fZ')}.json"
    provider = {
        "name": "dataforseo",
        "endpoint": endpoint,
        "target": target,
        "mode": "one_per_domain",
        "total_count": total_count,
        "collected_count": len(provider_items),
        "request_count": len(requests),
        "cost_usd": round(sum(item["cost_usd"] for item in requests), 6),
        "truncated": not complete,
        "requests": requests,
    }
    _write_json(
        raw_path,
        {
            "schema_version": "dataforseo-backlinks-raw-v1",
            "generated_at": observed.isoformat(),
            "provider": provider,
            "rows": rows,
            "provider_items": provider_items,
        },
    )
    return import_backlink_snapshot(
        project_dir,
        raw_path,
        source="dataforseo",
        complete=complete,
        captured_at=observed.isoformat(),
        now=observed,
        allow_empty=True,
        provider=provider,
    )


def collect_dataforseo_gap(
    project_dir: Path,
    competitors: list[str],
    *,
    confirm_paid: bool,
    limit: int = 1_000,
    timeout: float = 45,
    requester: Callable[..., dict[str, Any]] = dataforseo.post,
    now: datetime | None = None,
) -> tuple[dict[str, Any], Path]:
    if not confirm_paid:
        raise ValueError("DataForSEO backlink gap collection is paid; pass --confirm-paid")
    if not 1 <= limit <= 1_000:
        raise ValueError("limit must be between 1 and 1000")
    project_url = normalize_url(str((state.load_state(project_dir).get("project") or {}).get("url", "")))
    project_target = _domain_target(project_url)
    normalized_competitors = list(dict.fromkeys(_domain_target(value) for value in competitors))
    if not 1 <= len(normalized_competitors) <= 3:
        raise ValueError("backlink gap requires 1 to 3 unique competitors")
    if any(link_scope(f"https://{competitor}/", project_url)[1] != "external" for competitor in normalized_competitors):
        raise ValueError("backlink gap competitors must be external domains")
    target_map = _exact_keyword_targets(project_dir, project_url)

    endpoint = "/v3/backlinks/page_intersection/live"
    targets = {str(index): competitor for index, competitor in enumerate(normalized_competitors, start=1)}
    task_result, result = _provider_result(
        requester(
            project_dir,
            endpoint,
            {
                "targets": targets,
                "exclude_targets": [project_target],
                "backlinks_status_type": "live",
                "intersection_mode": "partial",
                "exclude_internal_backlinks": True,
                "limit": limit,
            },
            timeout,
        )
    )
    provider_items = [item for item in result.get("items") or [] if isinstance(item, dict)]
    opportunities: list[dict[str, Any]] = []
    for item in provider_items:
        intersections = item.get("page_intersection") if isinstance(item.get("page_intersection"), dict) else {}
        matched: dict[str, list[dict[str, Any]]] = {
            targets[key]: [link for link in intersections.get(key) or [] if isinstance(link, dict)]
            for key in targets
            if intersections.get(key)
        }
        links = [link for values in matched.values() for link in values]
        source_url = normalize_url(str((links[0] if links else {}).get("url_from") or ""))
        if not source_url or link_scope(source_url, project_url)[1] != "external":
            continue
        anchors = list(dict.fromkeys(str(link.get("anchor") or "").strip() for link in links if str(link.get("anchor") or "").strip()))
        suggested = next((target_map[anchor.casefold()] for anchor in anchors if anchor.casefold() in target_map), "")
        opportunities.append(
            {
                "source_url": source_url,
                "source_domain": (urlsplit(source_url).hostname or "").lower(),
                "competitors": list(matched),
                "competitor_target_urls": {
                    competitor: list(dict.fromkeys(str(link.get("url_to") or "") for link in links_for_target if link.get("url_to")))
                    for competitor, links_for_target in matched.items()
                },
                "anchors": anchors[:10],
                "dofollow": any(link.get("dofollow") is True for link in links),
                "suggested_target_url": suggested,
                "mapping_status": "mapped" if suggested else "not_mapped",
            }
        )

    observed = (now or datetime.now(timezone.utc)).astimezone(timezone.utc)
    total_count = max(len(provider_items), _provider_total(result))
    collection_status = "complete" if len(provider_items) >= total_count else "partial"
    provider = {
        "name": "dataforseo",
        "endpoint": endpoint,
        "task_id": task_result.get("id", ""),
        "cost_usd": round(float(task_result.get("cost") or 0), 6),
        "total_count": total_count,
        "collected_count": len(provider_items),
        "truncated": collection_status != "complete",
    }
    report = {
        "schema_version": "dataforseo-backlink-gap-v1",
        "collection_status": collection_status,
        "generated_at": observed.isoformat(),
        "project_target": project_target,
        "competitors": normalized_competitors,
        "provider": provider,
        "summary": {
            "opportunities": len(opportunities),
            "mapped_targets": sum(bool(item["suggested_target_url"]) for item in opportunities),
            "unmapped_targets": sum(not item["suggested_target_url"] for item in opportunities),
        },
        "items": opportunities,
        "claims": {
            "authority_score": "not_calculated",
            "toxicity_score": "not_calculated",
            "outreach_status": "not_managed",
        },
    }
    root = state.safe_project_path(project_dir, "audits/backlinks/dataforseo")
    raw_dir = root / "raw"
    output_dir = root / "opportunities"
    raw_dir.mkdir(parents=True, exist_ok=True, mode=0o700)
    output_dir.mkdir(parents=True, exist_ok=True, mode=0o700)
    stamp = observed.strftime("%Y%m%dT%H%M%S%fZ")
    _write_json(
        raw_dir / f"gap-{stamp}.json",
        {
            "schema_version": "dataforseo-backlink-gap-raw-v1",
            "generated_at": observed.isoformat(),
            "provider": provider,
            "provider_items": provider_items,
        },
    )
    path = output_dir / f"gap-{stamp}.json"
    markdown_path = output_dir / f"gap-{stamp}.md"
    _write_json(path, report)
    _write_json(output_dir / "latest.json", report)
    markdown = _gap_markdown(report)
    atomic_write_text(markdown_path, markdown, mode=0o600)
    atomic_write_text(output_dir / "latest.md", markdown, mode=0o600)
    return report, path


def backlink_status(project_dir: Path, *, source: str = "") -> dict[str, Any]:
    source_id = _safe_id(source) if source else ""
    path = state.safe_project_path(project_dir, f"audits/backlinks/latest-{source_id}.json" if source_id else "audits/backlinks/latest.json")
    report = _optional_json(path)
    if report is None:
        return {"schema_version": "backlink-status-v1", "collection_status": "not_collected", "path": str(path)}
    return {
        "schema_version": "backlink-status-v1",
        "collection_status": report.get("collection_status", "unknown"),
        "path": str(path),
        "captured_at": report.get("captured_at", ""),
        "source": report.get("source", {}),
        "complete_snapshot": report.get("complete_snapshot", False),
        "summary": report.get("summary", {}),
        "comparison": report.get("comparison", {}),
    }


def query_backlink_workspace(project_dir: Path, query: BacklinkViewQuery) -> dict[str, Any]:
    report = _optional_json(state.safe_project_path(project_dir, "audits/backlinks/latest.json"))
    if report is None:
        return {
            "ok": True,
            "collection_status": "not_collected",
            "generated_at": None,
            "captured_at": None,
            "source": None,
            "complete_snapshot": False,
            "summary": {},
            "comparison": {},
            "top_anchors": [],
            "claims": {},
            "columns": list(BACKLINK_VIEW_COLUMNS),
            "rows": [],
            "pagination": {"offset": query.offset, "limit": query.limit, "total": 0},
        }

    rows = [row for row in report.get("links", []) if isinstance(row, dict)]
    needle = query.query.strip().lower()
    if needle:
        rows = [
            row for row in rows
            if any(needle in str(row.get(field, "")).lower() for field in ("source_domain", "source_url", "target_url", "anchor"))
        ]
    if query.status:
        rows = [row for row in rows if row.get("provider_status") == query.status]
    if query.follow:
        rows = [row for row in rows if _follow_label(row.get("follow")) == query.follow]
    if query.reclaim_only:
        rows = [row for row in rows if row.get("target_reclaim_candidate") is True]

    rows.sort(key=lambda row: _backlink_sort_value(row, query.sort), reverse=query.direction == "desc")
    return {
        "ok": True,
        "collection_status": report.get("collection_status", "unknown"),
        "generated_at": report.get("generated_at"),
        "captured_at": report.get("captured_at"),
        "source": report.get("source"),
        "complete_snapshot": report.get("complete_snapshot", False),
        "summary": report.get("summary", {}),
        "comparison": report.get("comparison", {}),
        "top_anchors": report.get("top_anchors", []),
        "claims": report.get("claims", {}),
        "columns": list(BACKLINK_VIEW_COLUMNS),
        "rows": rows[query.offset : query.offset + query.limit],
        "pagination": {"offset": query.offset, "limit": query.limit, "total": len(rows)},
    }


def _follow_label(value: Any) -> str:
    return "follow" if value is True else "nofollow" if value is False else "unknown"


def _backlink_sort_value(row: dict[str, Any], field: str) -> str | int:
    if field == "follow":
        return _follow_label(row.get("follow"))
    value = row.get(field)
    if field == "target_status_code":
        return int(value) if isinstance(value, int) else -1
    return str(value or "").lower()


def _compare(baseline: dict[str, Any] | None, current: dict[str, dict[str, Any]], *, current_complete: bool) -> dict[str, Any]:
    if not baseline:
        return {"status": "no_baseline", "comparable": False, "new_observed": [], "lost": [], "missing_unconfirmed": [], "retained_count": 0}
    previous = {str(link.get("id")): link for link in baseline.get("links", []) if isinstance(link, dict) and link.get("id")}
    previous_active = {link_id for link_id, link in previous.items() if link.get("provider_status") == "active"}
    current_active = {link_id for link_id, link in current.items() if link.get("provider_status") == "active"}
    current_lost = {link_id for link_id, link in current.items() if link.get("provider_status") == "lost"}
    new_ids = current_active - previous_active
    reported_lost = previous_active & current_lost
    absent = previous_active - current_active - current_lost
    comparable = bool(baseline.get("complete_snapshot")) and current_complete
    lost_ids = reported_lost | (absent if comparable else set())
    missing_ids = set() if comparable else absent
    all_links = previous | current
    details = lambda ids: [all_links[link_id] for link_id in sorted(ids)]
    return {
        "status": "comparable" if comparable else "partial",
        "comparable": comparable,
        "baseline_captured_at": baseline.get("captured_at", ""),
        "new_observed": details(new_ids),
        "lost": details(lost_ids),
        "missing_unconfirmed": details(missing_ids),
        "retained_count": len(previous_active & current_active),
    }


def _source_rows(path: Path, *, allow_empty: bool = False) -> list[dict[str, Any]]:
    try:
        if path.suffix.lower() == ".csv":
            with path.open(encoding="utf-8-sig", newline="") as handle:
                rows = list(csv.DictReader(handle))
        else:
            payload = json.loads(path.read_text(encoding="utf-8"))
            rows = payload.get("rows") if isinstance(payload, dict) else payload
    except FileNotFoundError as exc:
        raise FileNotFoundError(f"backlink source not found: {path}") from exc
    except json.JSONDecodeError as exc:
        raise ValueError(f"invalid backlink JSON: {exc.msg}") from exc
    if not isinstance(rows, list) or (not rows and not allow_empty) or any(not isinstance(row, dict) for row in rows):
        raise ValueError("backlink source must contain a non-empty row list")
    return rows


def _provider_result(payload: dict[str, Any]) -> tuple[dict[str, Any], dict[str, Any]]:
    try:
        task = payload["tasks"][0]
        result = task["result"][0]
    except (KeyError, IndexError, TypeError) as exc:
        raise ValueError("DataForSEO returned incomplete backlink evidence") from exc
    if not isinstance(task, dict) or not isinstance(result, dict) or not isinstance(result.get("items") or [], list):
        raise ValueError("DataForSEO returned invalid backlink evidence")
    return task, result


def _provider_total(result: dict[str, Any]) -> int:
    value = result.get("total_count")
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise ValueError("DataForSEO returned invalid backlink total_count evidence")
    return value


def _domain_target(value: str) -> str:
    raw = value.strip()
    parsed = urlsplit(raw if "://" in raw else f"//{raw}")
    if (
        parsed.scheme not in {"", "http", "https"}
        or not parsed.hostname
        or parsed.username
        or parsed.password
        or parsed.port
        or parsed.path not in {"", "/"}
        or parsed.query
        or parsed.fragment
    ):
        raise ValueError(f"DataForSEO backlink target must be a bare domain: {value}")
    host = parsed.hostname.lower()
    return host[4:] if host.startswith("www.") else host


def _exact_keyword_targets(project_dir: Path, project_url: str) -> dict[str, str]:
    portfolio = _optional_json(state.safe_project_path(project_dir, "audits/content-portfolio/latest.json")) or {}
    observed_urls = {
        normalize_url(str(item.get("url") or ""))
        for item in portfolio.get("items") or []
        if isinstance(item, dict) and item.get("url")
    }
    path = state.safe_project_path(project_dir, "strategy/keyword-pool.jsonl")
    if not path.is_file() or path.is_symlink():
        return {}
    result: dict[str, str] = {}
    try:
        rows = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]
    except (OSError, json.JSONDecodeError):
        return {}
    for row in rows:
        if not isinstance(row, dict):
            continue
        keyword = str(row.get("keyword") or "").strip().casefold()
        raw_target = str(row.get("target_url") or "").strip()
        target = normalize_url(urljoin(project_url.rstrip("/") + "/", raw_target)) if raw_target else ""
        if keyword and target in observed_urls and link_scope(target, project_url)[1] in {"same_host", "subdomain"}:
            result[keyword] = target
    return result


def _gap_markdown(report: dict[str, Any]) -> str:
    def cell(value: Any) -> str:
        return str(value or "").replace("\n", " ").replace("|", "\\|")

    lines = [
        "# Backlink Gap Opportunities",
        "",
        f"- Generated: {report['generated_at']}",
        f"- Competitors: {', '.join(report['competitors'])}",
        f"- Provider coverage: {report['collection_status']}",
        f"- Provider cost (USD): {report['provider']['cost_usd']}",
        f"- Opportunities: {report['summary']['opportunities']}",
        "",
        "This is provider-observed opportunity evidence only. No authority, toxicity, outreach, or disavow judgment is inferred.",
        "",
        "| Referring page | Competitors | Anchors | Suggested site target |",
        "| --- | --- | --- | --- |",
    ]
    for item in report["items"][:100]:
        lines.append(
            "| "
            + " | ".join(
                (
                    cell(item["source_url"]),
                    cell(", ".join(item["competitors"])),
                    cell(", ".join(item["anchors"])),
                    cell(item["suggested_target_url"] or "Not mapped"),
                )
            )
            + " |"
        )
    return "\n".join(lines) + "\n"


def _follow(row: dict[str, Any]) -> bool | None:
    value = row.get("follow")
    if value not in (None, ""):
        normalized = str(value).strip().lower()
        if normalized in {"true", "1", "yes", "follow", "dofollow"}:
            return True
        if normalized in {"false", "0", "no", "nofollow"}:
            return False
        raise ValueError(f"backlink follow must be true or false: {value}")
    rel = {part.lower() for part in str(row.get("rel") or "").split()}
    return False if rel & {"nofollow", "ugc", "sponsored"} else None


def _captured_at(value: str, fallback: datetime) -> str:
    if not value:
        return fallback.isoformat()
    try:
        captured = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise ValueError("captured-at must be an ISO 8601 datetime") from exc
    if captured.tzinfo is None:
        captured = captured.replace(tzinfo=timezone.utc)
    return captured.astimezone(timezone.utc).isoformat()


def _safe_id(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", value.strip().lower()).strip("-")[:80]


def _optional_json(path: Path) -> dict[str, Any] | None:
    if not path.is_file():
        return None
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"invalid backlink artifact: {path}")
    return payload


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    atomic_write_text(path, json.dumps(payload, ensure_ascii=False, indent=2) + "\n", mode=0o600)


def _write_markdown(path: Path, report: dict[str, Any], snapshot_path: Path) -> None:
    summary = report["summary"]
    comparison = report["comparison"]
    lines = [
        "# Backlink Evidence Report",
        "",
        f"- Source: {report['source']['name']}",
        f"- Captured: {report['captured_at']}",
        f"- Complete snapshot: {'yes' if report['complete_snapshot'] else 'no'}",
        f"- Active links: {summary['active_links']}",
        f"- Referring domains: {summary['referring_domains']}",
        f"- Target reclaim candidates: {summary['target_reclaim_candidates']}",
        f"- Comparison: {comparison['status']}",
        f"- New observed: {len(comparison['new_observed'])}",
        f"- Lost: {len(comparison['lost'])}",
        f"- Missing but unconfirmed: {len(comparison['missing_unconfirmed'])}",
        "",
        "No authority or toxicity score is inferred. Missing links are only called lost when both same-source snapshots are complete.",
        "",
        f"Private evidence: `{snapshot_path}`",
        "",
    ]
    atomic_write_text(path, "\n".join(lines))
