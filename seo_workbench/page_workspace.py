from __future__ import annotations

import json
import re
from collections import Counter
from dataclasses import dataclass
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any, Literal
from urllib.parse import quote, urljoin, urlsplit

from seo_workbench import state
from seo_workbench.content_ops import build_content_ops
from seo_workbench.seo_changes import get_change, list_changes
from seo_workbench.tech_audit import link_scope, normalize_url, page_template, page_type
from seo_workbench.tech_issues import list_issue_register


PageDataset = Literal["actions", "pages", "query_conflicts"]
PageDirection = Literal["asc", "desc"]

PAGE_VIEW_COLUMNS: dict[str, tuple[dict[str, Any], ...]] = {
    "actions": (
        {"id": "urgency", "label": "Urgency", "default": True},
        {"id": "title", "label": "Action", "default": True},
        {"id": "source", "label": "Source", "default": True},
        {"id": "status", "label": "Status", "default": True},
        {"id": "url", "label": "URL", "default": True},
        {"id": "reason", "label": "Why", "default": True},
        {"id": "owner", "label": "Owner", "default": False},
        {"id": "due_date", "label": "Due", "default": False},
    ),
    "pages": (
        {"id": "title", "label": "Page", "default": True},
        {"id": "url", "label": "URL", "default": True},
        {"id": "page_type", "label": "Type", "default": True},
        {"id": "decision", "label": "Decision", "default": True},
        {"id": "clicks", "label": "Clicks", "default": True},
        {"id": "impressions", "label": "Impressions", "default": True},
        {"id": "position", "label": "Position", "default": True},
        {"id": "ctr", "label": "CTR", "default": False},
        {"id": "opportunity_impressions", "label": "Position 4–20", "default": True},
        {"id": "recoverable_clicks", "label": "CTR opportunity", "default": True},
        {"id": "evidence_strength", "label": "Evidence", "default": True},
        {"id": "trend", "label": "8-week trend", "default": False},
        {"id": "cross_source_status", "label": "GSC ↔ GA4", "default": False},
        {"id": "commercial_quadrant", "label": "Value × opportunity", "default": True},
        {"id": "click_driver", "label": "Click driver", "default": False},
        {"id": "technical_issues", "label": "Issues", "default": True},
        {"id": "source_status", "label": "Evidence", "default": False},
    ),
    "query_conflicts": (
        {"id": "query", "label": "Query", "default": True},
        {"id": "owner_count", "label": "Owners", "default": True},
        {"id": "total_impressions", "label": "Impressions", "default": True},
        {"id": "primary_owner_share", "label": "Primary share", "default": True},
        {"id": "ownership_hhi", "label": "Owner HHI", "default": False},
        {"id": "leading_url", "label": "Leading URL", "default": True},
    ),
}

SORT_FIELDS = {
    "actions": {"urgency", "title", "source", "status", "url", "due_date"},
    "pages": {
        "title", "url", "page_type", "decision", "clicks", "impressions", "position",
        "opportunity_impressions", "recoverable_clicks", "evidence_strength", "trend", "cross_source_status",
        "commercial_quadrant", "click_driver", "technical_issues",
    },
    "query_conflicts": {
        "query", "owner_count", "total_impressions", "primary_owner_share", "ownership_hhi", "leading_url",
    },
}


@dataclass(frozen=True)
class PageWorkspaceQuery:
    dataset: PageDataset = "actions"
    group: str = ""
    query: str = ""
    source: str = ""
    page_type: str = ""
    decision: str = ""
    status: str = ""
    sort: str = ""
    direction: PageDirection = "asc"
    limit: int = 50
    offset: int = 0

    def __post_init__(self) -> None:
        if self.dataset not in PAGE_VIEW_COLUMNS:
            raise ValueError("dataset must be actions, pages, or query_conflicts")
        if not self.sort:
            object.__setattr__(self, "sort", _default_sort(self.dataset))
        if self.direction not in {"asc", "desc"}:
            raise ValueError("direction must be asc or desc")
        if self.limit < 1 or self.limit > 200:
            raise ValueError("limit must be between 1 and 200")
        if self.offset < 0:
            raise ValueError("offset must be non-negative")
        if self.sort not in SORT_FIELDS[self.dataset]:
            raise ValueError(f"unsupported sort field for {self.dataset}: {self.sort}")


def query_page_workspace(project_dir: Path, query: PageWorkspaceQuery) -> dict[str, Any]:
    portfolio, pages, actions, conflicts = _workspace_data(project_dir)
    rows = {
        "actions": actions,
        "pages": pages,
        "query_conflicts": conflicts,
    }[query.dataset]
    rows = _filter(rows, query)
    rows.sort(key=lambda row: _sort_value(row, query.sort), reverse=query.direction == "desc")
    rows.sort(key=lambda row: row.get(query.sort) is None)
    total = len(rows)
    return {
        "ok": True,
        "dataset": query.dataset,
        "columns": list(PAGE_VIEW_COLUMNS[query.dataset]),
        "rows": rows[query.offset : query.offset + query.limit],
        "pagination": {"offset": query.offset, "limit": query.limit, "total": total},
        "summary": {
            "groups": dict(sorted(Counter(str(item.get("group", "")) for item in actions).items())),
            "pages": len(pages),
            "query_conflicts": len(conflicts),
            "statistics": portfolio.get("statistics") if isinstance(portfolio.get("statistics"), dict) else {},
        },
        "sources": _source_status(project_dir, portfolio),
    }


def page_workspace_detail(project_dir: Path, dataset: PageDataset, key: str) -> dict[str, Any]:
    portfolio, pages, actions, conflicts = _workspace_data(project_dir)
    rows = {"actions": actions, "pages": pages, "query_conflicts": conflicts}.get(dataset)
    if rows is None:
        raise ValueError("dataset must be actions, pages, or query_conflicts")
    row = next((item for item in rows if str(item.get("row_key", "")) == key), None)
    if row is None:
        raise ValueError(f"{dataset} row not found")
    url = normalize_url(str(row.get("url", "")))
    page = next((item for item in pages if item.get("row_key") == url), None) if url else None
    return {
        "ok": True,
        "dataset": dataset,
        "row": row,
        "page": page,
        "source_record": _source_record(project_dir, row),
        "sources": _source_status(project_dir, portfolio),
        "internal_link_candidates": _internal_link_candidates(project_dir, url, pages),
    }


def _workspace_data(
    project_dir: Path,
) -> tuple[dict[str, Any], list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]]]:
    portfolio = _load_optional(project_dir, "audits/content-portfolio/latest.json")
    pages = [_page_row(item) for item in portfolio.get("items", []) if isinstance(item, dict)]
    return portfolio, pages, _actions(project_dir, pages), _conflict_rows(pages)


def _page_row(item: dict[str, Any]) -> dict[str, Any]:
    url = normalize_url(str(item.get("url") or item.get("row_key") or ""))
    current = ((item.get("metrics") or {}).get("current")) or None
    technical = item.get("technical") if isinstance(item.get("technical"), dict) else {}
    sources = item.get("sources") if isinstance(item.get("sources"), dict) else {"content": True}
    statistics = item.get("statistics") if isinstance(item.get("statistics"), dict) else {}
    decomposition = statistics.get("click_change_decomposition") if isinstance(statistics.get("click_change_decomposition"), dict) else {}
    ranking = statistics.get("ranking_opportunity") if isinstance(statistics.get("ranking_opportunity"), dict) else {}
    commercial = statistics.get("commercial_value") if isinstance(statistics.get("commercial_value"), dict) else {}
    confidence = statistics.get("search_change_confidence") if isinstance(statistics.get("search_change_confidence"), dict) else {}
    trend = statistics.get("search_trend") if isinstance(statistics.get("search_trend"), dict) else {}
    ctr_benchmark = statistics.get("ctr_benchmark") if isinstance(statistics.get("ctr_benchmark"), dict) else {}
    cross_source = statistics.get("cross_source_consistency") if isinstance(statistics.get("cross_source_consistency"), dict) else {}
    exposure_effect = float(decomposition.get("exposure_effect") or 0)
    ctr_effect = float(decomposition.get("ctr_effect") or 0)
    click_driver = "exposure" if abs(exposure_effect) > abs(ctr_effect) else "ctr" if abs(ctr_effect) > abs(exposure_effect) else "mixed"
    return {
        **item,
        "row_key": url,
        "url": url,
        "title": item.get("title") or _url_title(url),
        "page_type": item.get("page_type") or page_type(url),
        "sources": sources,
        "source_status": ", ".join(key.replace("gsc_", "GSC ") for key, value in sources.items() if value) or "not_observed",
        "clicks": None if current is None else current.get("clicks"),
        "impressions": None if current is None else current.get("impressions"),
        "ctr": None if current is None else current.get("ctr"),
        "position": None if current is None else current.get("position"),
        "opportunity_impressions": ranking.get("positions_4_20_impressions"),
        "recoverable_clicks": (
            ctr_benchmark.get("recoverable_clicks")
            if ctr_benchmark.get("classification") == "below_expected"
            else None
        ),
        "evidence_strength": confidence.get("evidence_grade") if confidence.get("status") == "ok" else None,
        "trend": trend.get("direction") if trend.get("status") == "ok" else None,
        "cross_source_status": (
            cross_source.get("status") if cross_source.get("status") != "insufficient_data" else None
        ),
        "commercial_quadrant": commercial.get("quadrant"),
        "click_driver": click_driver if decomposition else None,
        "technical_issues": technical.get("issue_count") if technical else None,
    }


def _actions(project_dir: Path, pages: list[dict[str, Any]]) -> list[dict[str, Any]]:
    project_url = str((state.load_state(project_dir).get("project") or {}).get("url", ""))
    rows = [_portfolio_action(page) for page in pages]
    rows.extend(_content_actions(project_dir, project_url))
    rows.extend(_technical_actions(project_dir, project_url))
    rows.extend(_change_actions(project_dir))
    return rows


def _portfolio_action(page: dict[str, Any]) -> dict[str, Any]:
    decision = str(page.get("decision", "wait_for_data"))
    group = "now" if decision in {"refresh", "consolidate_review", "improve_snippet", "expand_and_link"} else "watch"
    urgency = {
        "refresh": "high",
        "consolidate_review": "high",
        "improve_snippet": "medium",
        "expand_and_link": "medium",
    }.get(decision, "low")
    url = str(page.get("url", ""))
    return {
        "row_key": f"portfolio:{url}",
        "source": "portfolio",
        "source_id": url,
        "group": group,
        "urgency": urgency,
        "title": page.get("title") or _url_title(url),
        "url": url,
        "status": decision,
        "owner": "",
        "due_date": "",
        "reason": page.get("recommendation", ""),
        "target_view": "#/pages",
    }


def _content_actions(project_dir: Path, project_url: str) -> list[dict[str, Any]]:
    selected: dict[str, tuple[str, dict[str, Any]]] = {}
    for action in build_content_ops(project_dir).get("actions", []):
        action_id = str(action.get("id", ""))
        if action_id == "content_report":
            continue
        for item in action.get("items", []):
            if not isinstance(item, dict):
                continue
            if not action.get("due") and item.get("status") != "indexing_issue":
                continue
            item_id = str(item.get("id", ""))
            if item_id:
                selected.setdefault(item_id, (action_id, item))
    rows = []
    for item_id, (action_id, item) in selected.items():
        status = str(item.get("status", ""))
        rows.append(
            {
                "row_key": f"content:{action_id}:{item_id}",
                "source": "content",
                "source_id": item_id,
                "group": "now",
                "urgency": "critical" if status == "indexing_issue" else "high",
                "title": item.get("title") or item.get("slug") or item_id,
                "url": _site_url(item.get("live_url", ""), project_url),
                "status": status or action_id,
                "owner": "",
                "due_date": item.get("scheduled_at", ""),
                "reason": action_id.replace("_", " "),
                "target_view": f"#/content?item={quote(item_id)}",
            }
        )
    return rows


def _technical_actions(project_dir: Path, project_url: str) -> list[dict[str, Any]]:
    grouped: dict[tuple[str, str, str, str], list[dict[str, Any]]] = {}
    for issue in list_issue_register(project_dir).get("issues", []):
        status = str(issue.get("status", "open"))
        template = str(issue.get("template") or page_template(str(issue.get("url", ""))))
        grouped.setdefault((str(issue.get("rule_id", "")), template, status, str(issue.get("owner", ""))), []).append(issue)
    rows = []
    for (rule_id, template, status, owner), issues in grouped.items():
        issue = issues[0]
        group = "now" if status in {"open", "planned"} else "review" if status == "fixed" else "done"
        fingerprint = str(issue.get("fingerprint", ""))
        count = len(issues)
        rows.append(
            {
                "row_key": f"technical:{fingerprint}" if count == 1 else f"technical-group:{rule_id}:{template}:{status}:{owner or 'unassigned'}",
                "source": "technical",
                "source_id": fingerprint if count == 1 else "",
                "group": group,
                "urgency": str(issue.get("priority_tier") or "low"),
                "native_priority": float(issue.get("priority", 0) or 0),
                "title": (issue.get("title") or rule_id or "Technical issue") + (f" · {template} ({count})" if count > 1 else ""),
                "url": _site_url(issue.get("url", ""), project_url) if count == 1 else "",
                "status": status,
                "owner": owner,
                "due_date": "",
                "reason": issue.get("remediation_guidance", ""),
                "target_view": (
                    f"#/audits/url-inventory?dataset=issues&key={quote(fingerprint)}"
                    if count == 1
                    else f"#/audits/url-inventory?dataset=issues&rule_id={quote(rule_id)}&template={quote(template)}"
                ),
                "issue_count": count,
                "template": template,
                "read_only": count > 1,
            }
        )
    return rows


def _change_actions(project_dir: Path) -> list[dict[str, Any]]:
    today = datetime.now(timezone.utc).date()
    rows = []
    for change in list_changes(project_dir).get("changes", []):
        status = str(change.get("status", ""))
        review_date = _day(str(change.get("review_date", "")))
        if status == "planned":
            group = "now"
        elif status == "shipped" and review_date and review_date <= today:
            group = "review"
        elif status == "shipped":
            group = "watch"
        else:
            group = "done"
        urls = change.get("urls") if isinstance(change.get("urls"), list) else []
        rows.append(
            {
                "row_key": f"change:{change.get('id', '')}",
                "source": "change",
                "source_id": change.get("id", ""),
                "group": group,
                "urgency": "critical" if group == "review" else "medium" if group == "now" else "low",
                "title": change.get("hypothesis") or change.get("id") or "SEO change",
                "url": urls[0] if urls else "",
                "status": status,
                "owner": "",
                "due_date": change.get("review_date", ""),
                "reason": "Review descriptive pre/post evidence." if group == "review" else "Track until the planned review date.",
                "target_view": "#/pages",
            }
        )
    return rows


def _conflict_rows(pages: list[dict[str, Any]]) -> list[dict[str, Any]]:
    conflicts: dict[str, dict[str, Any]] = {}
    for page in pages:
        for conflict in page.get("multiple_page_queries", []):
            if not isinstance(conflict, dict) or not conflict.get("query"):
                continue
            query = str(conflict["query"])
            row = conflicts.get(query.casefold())
            if row is None or float(conflict.get("total_impressions", 0) or 0) > float(row.get("total_impressions", 0) or 0):
                conflicts[query.casefold()] = {"row_key": query, **conflict}
    for row in conflicts.values():
        owners = row.get("owners") if isinstance(row.get("owners"), list) else []
        ownership = row.get("ownership") if isinstance(row.get("ownership"), dict) else {}
        row["primary_owner_share"] = ownership.get("primary_owner_share")
        row["ownership_hhi"] = ownership.get("hhi")
        row["leading_url"] = owners[0].get("url", "") if owners and isinstance(owners[0], dict) else ""
        row["url"] = row["leading_url"]
    return list(conflicts.values())


def _source_record(project_dir: Path, row: dict[str, Any]) -> dict[str, Any] | None:
    source = str(row.get("source", ""))
    source_id = str(row.get("source_id", ""))
    if source == "change" and source_id:
        try:
            return get_change(project_dir, source_id)
        except ValueError:
            return None
    if source == "technical":
        return next(
            (item for item in list_issue_register(project_dir).get("issues", []) if item.get("fingerprint") == source_id),
            None,
        )
    if source == "content":
        queue = state.load_state(project_dir).get("contentQueue") or []
        return next((item for item in queue if isinstance(item, dict) and str(item.get("id", "")) == source_id), None)
    return None


def _internal_link_candidates(
    project_dir: Path,
    current_url: str,
    pages: list[dict[str, Any]],
) -> dict[str, Any]:
    if not current_url:
        return {"status": "insufficient_data", "reason": "This row has no page URL.", "rows": []}
    mappings = _read_jsonl(state.safe_project_path(project_dir, "strategy/keyword-pool.jsonl"))
    if not mappings:
        return {"status": "insufficient_data", "reason": "No keyword cluster mappings are available.", "rows": []}
    links = _internal_link_edges(project_dir)
    if links is None:
        return {"status": "insufficient_data", "reason": "No readable technical link inventory is available.", "rows": []}

    project_url = str((state.load_state(project_dir).get("project") or {}).get("url", ""))
    page_by_url = {normalize_url(str(page.get("url", ""))): page for page in pages}
    source_by_content_id: dict[str, dict[str, Any]] = {}
    for page in pages:
        content = page.get("content_item") if isinstance(page.get("content_item"), dict) else {}
        content_id = str(content.get("id") or page.get("id") or "")
        if content_id:
            source_by_content_id[content_id] = page

    targets: dict[str, list[tuple[str, str]]] = {}
    source_ids: dict[str, set[str]] = {}
    for mapping in mappings:
        cluster = _cluster_ref(mapping.get("cluster_ref"))
        if not cluster:
            continue
        target_url = _mapped_url(mapping.get("target_url"), project_url)
        if target_url:
            targets.setdefault(cluster, []).append((target_url, str(mapping.get("keyword") or "")))
        content_id = str(mapping.get("target_content_id") or "")
        if content_id:
            source_ids.setdefault(cluster, set()).add(content_id)

    candidates: list[dict[str, Any]] = []
    related_pairs = 0
    for cluster, cluster_targets in targets.items():
        for target_url, keyword in cluster_targets:
            target = page_by_url.get(target_url)
            if not target or str(target.get("page_type")) not in {"product", "collection"} or not _linkable_page(target):
                continue
            for content_id in sorted(source_ids.get(cluster, set())):
                source = source_by_content_id.get(content_id)
                source_url = normalize_url(str((source or {}).get("url", "")))
                if not source or str(source.get("page_type")) not in {"article", "page"} or not _linkable_page(source):
                    continue
                if _locale(source_url) != _locale(target_url) or current_url not in {source_url, target_url}:
                    continue
                related_pairs += 1
                if (source_url, target_url) in links:
                    continue
                anchors = _anchor_candidates(keyword, target)
                candidates.append(
                    {
                        "source_url": source_url,
                        "target_url": target_url,
                        "anchor_candidates": anchors,
                        "already_linked": False,
                        "cluster_ref": cluster,
                        "reason": "Same mapped keyword cluster; both pages are indexable and no source-to-target link was observed.",
                    }
                )
    unique: dict[tuple[str, str], dict[str, Any]] = {}
    for row in candidates:
        key = (row["source_url"], row["target_url"])
        if key not in unique:
            unique[key] = row
            continue
        anchors = unique[key]["anchor_candidates"]
        unique[key]["anchor_candidates"] = list(dict.fromkeys([*anchors, *row["anchor_candidates"]]))[:3]
    rows = [unique[key] for key in sorted(unique)][:20]
    if rows or related_pairs:
        return {
            "status": "ok",
            "reason": "Candidates are deterministic suggestions only; implementation and later crawl verification remain manual.",
            "rows": rows,
        }
    return {
        "status": "insufficient_data",
        "reason": "No same-locale, indexable article-to-product or article-to-collection mapping was found for this page.",
        "rows": [],
    }


def _internal_link_edges(project_dir: Path) -> set[tuple[str, str]] | None:
    audit = _load_optional(project_dir, "audits/tech-audit/latest.json")
    relative = str((audit.get("artifacts") or {}).get("link_inventory_path") or "")
    if not relative:
        return None
    path = state.safe_project_path(project_dir, relative)
    rows = _read_jsonl(path)
    if rows is None:
        return None
    edges: set[tuple[str, str]] = set()
    for row in rows:
        if row.get("internal_external") != "Internal":
            continue
        targets = {
            normalize_url(str(row.get("url") or "")),
            normalize_url(str(row.get("final_url") or "")),
        } - {""}
        for source in row.get("sources") or []:
            source_url = normalize_url(str(source))
            edges.update((source_url, target) for target in targets if source_url)
    return edges


def _linkable_page(page: dict[str, Any]) -> bool:
    technical = page.get("technical") if isinstance(page.get("technical"), dict) else {}
    indexability = technical.get("indexability") if isinstance(technical.get("indexability"), dict) else {}
    url = normalize_url(str(page.get("url") or ""))
    final_url = normalize_url(str(technical.get("final_url") or url))
    return (
        technical.get("status_code") == 200
        and technical.get("crawl_status") == "ok"
        and indexability.get("indexable") is True
        and final_url == url
    )


def _anchor_candidates(keyword: str, page: dict[str, Any]) -> list[str]:
    values = [keyword, *(str(row.get("query") or "") for row in page.get("top_queries") or [] if isinstance(row, dict))]
    result: list[str] = []
    for value in values:
        cleaned = value.strip()
        if cleaned and cleaned.casefold() not in {item.casefold() for item in result}:
            result.append(cleaned)
    return result[:3]


def _cluster_ref(value: Any) -> str:
    if isinstance(value, list):
        return str(value[0]) if value else ""
    return str(value or "")


def _mapped_url(value: Any, project_url: str) -> str:
    raw = str(value or "").strip()
    return normalize_url(urljoin(project_url.rstrip("/") + "/", raw)) if raw else ""


def _locale(url: str) -> str:
    first = urlsplit(url).path.strip("/").split("/", 1)[0].lower()
    return first if re.fullmatch(r"[a-z]{2}(?:-[a-z]{2})?", first) else ""


def _read_jsonl(path: Path) -> list[dict[str, Any]] | None:
    if not path.is_file() or path.is_symlink():
        return None
    try:
        rows = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]
    except (OSError, json.JSONDecodeError):
        return None
    return rows if all(isinstance(row, dict) for row in rows) else None


def _filter(rows: list[dict[str, Any]], query: PageWorkspaceQuery) -> list[dict[str, Any]]:
    result = rows
    if query.group:
        result = [row for row in result if str(row.get("group", "")).casefold() == query.group.casefold()]
    if query.source:
        result = [
            row
            for row in result
            if str(row.get("source", "")).casefold() == query.source.casefold()
            or bool((row.get("sources") or {}).get(query.source))
        ]
    if query.page_type:
        result = [row for row in result if str(row.get("page_type", "")).casefold() == query.page_type.casefold()]
    if query.decision:
        result = [row for row in result if str(row.get("decision", "")).casefold() == query.decision.casefold()]
    if query.status:
        result = [row for row in result if str(row.get("status", "")).casefold() == query.status.casefold()]
    needle = query.query.casefold().strip()
    if needle:
        result = [row for row in result if needle in _search_text(row)]
    return result


def _search_text(row: dict[str, Any]) -> str:
    values = [row.get(key, "") for key in ("row_key", "title", "url", "query", "reason", "status", "source", "owner")]
    return " ".join(str(value) for value in values).casefold()


def _sort_value(row: dict[str, Any], field: str) -> tuple[Any, ...]:
    if field == "urgency":
        due_date = str(row.get("due_date", ""))
        return ({"critical": 0, "high": 1, "medium": 2, "low": 3}.get(str(row.get(field, "")), 4), -float(row.get("native_priority", 0) or 0), not bool(due_date), due_date, str(row.get("title", "")).casefold())
    value = row.get(field)
    if value is None:
        return (1, "")
    if isinstance(value, (int, float)):
        return (0, value)
    return (0, str(value).casefold())


def _source_status(project_dir: Path, portfolio: dict[str, Any]) -> dict[str, Any]:
    embedded = portfolio.get("source_status") if isinstance(portfolio.get("source_status"), dict) else {}
    gsc = embedded.get("gsc") if isinstance(embedded.get("gsc"), dict) else None
    technical = embedded.get("technical") if isinstance(embedded.get("technical"), dict) else None
    business = embedded.get("business") if isinstance(embedded.get("business"), dict) else None
    statistics_history = embedded.get("statistics_history") if isinstance(embedded.get("statistics_history"), dict) else None
    sources = {
        "portfolio": _status(portfolio, "not_collected"),
        "gsc": dict(gsc) if gsc is not None else _status(_load_optional(project_dir, "audits/gsc/search-analytics/latest.json"), "not_collected"),
        "technical": dict(technical) if technical is not None else _status(_load_optional(project_dir, "audits/tech-audit/latest.json"), "not_collected"),
        "ga4": _status(_load_optional(project_dir, "audits/ga4/latest.json"), "not_collected"),
        "business": dict(business) if business is not None else _status(_load_optional(project_dir, "audits/business-signals/latest.json"), "not_collected"),
        "statistics_history": dict(statistics_history) if statistics_history is not None else {"status": "not_collected"},
    }
    portfolio_path = state.safe_project_path(project_dir, "audits/content-portfolio/latest.json")
    dependencies = {
        "gsc": state.safe_project_path(project_dir, "audits/gsc/search-analytics/latest.json"),
        "technical": state.safe_project_path(project_dir, "audits/tech-audit/latest.json"),
        "business": state.safe_project_path(project_dir, "audits/business-signals/latest.json"),
        "statistics_history": state.safe_project_path(project_dir, "audits/statistics/history/coverage.json"),
    }
    portfolio_modified = _modified_at(portfolio_path)
    refresh_reasons = []
    for name, path in dependencies.items():
        changed = bool(portfolio_modified and _modified_at(path) > portfolio_modified)
        sources[name]["changed_since_refresh"] = changed
        if changed:
            refresh_reasons.append(f"{name} evidence is newer than the page analysis")
    sources["portfolio"]["needs_refresh"] = bool(refresh_reasons)
    sources["portfolio"]["refresh_reasons"] = refresh_reasons
    if refresh_reasons and sources["portfolio"]["status"] == "ok":
        sources["portfolio"]["status"] = "needs_refresh"
    for item in sources.values():
        item["age_days"] = _age_days(item.get("generated_at"))
    return sources


def _status(report: dict[str, Any], fallback: str) -> dict[str, Any]:
    return {
        "status": report.get("collection_status", fallback),
        "generated_at": report.get("generated_at"),
        "schema_version": report.get("schema_version"),
    }


def _modified_at(path: Path) -> int:
    try:
        return path.stat().st_mtime_ns
    except OSError:
        return 0


def _age_days(value: object) -> float | None:
    try:
        generated_at = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except ValueError:
        return None
    if generated_at.tzinfo is None:
        generated_at = generated_at.replace(tzinfo=timezone.utc)
    return round(max(0.0, (datetime.now(timezone.utc) - generated_at.astimezone(timezone.utc)).total_seconds()) / 86400, 1)


def _load_optional(project_dir: Path, relative: str) -> dict[str, Any]:
    path = state.safe_project_path(project_dir, relative)
    if not path.is_file():
        return {}
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    return value if isinstance(value, dict) else {}


def _default_sort(dataset: PageDataset) -> str:
    return {"actions": "urgency", "pages": "url", "query_conflicts": "total_impressions"}[dataset]


def _day(value: str) -> date | None:
    try:
        return date.fromisoformat(value)
    except ValueError:
        return None


def _url_title(url: str) -> str:
    path = urlsplit(url).path.rstrip("/")
    return (path.rsplit("/", 1)[-1] if path else urlsplit(url).hostname or url).replace("-", " ").title()


def _site_url(value: object, project_url: str) -> str:
    url = normalize_url(str(value or ""))
    return url if url and link_scope(url, project_url)[1] in {"same_host", "subdomain"} else ""
