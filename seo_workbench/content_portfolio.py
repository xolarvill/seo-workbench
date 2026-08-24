from __future__ import annotations

import json
from collections import Counter
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit

from seo_workbench import state
from seo_workbench.business_signals import METRICS as BUSINESS_METRICS
from seo_workbench.measurement_regimes import comparison_breaks
from seo_workbench.longitudinal_statistics import build_longitudinal_statistics
from seo_workbench.search_statistics import (
    build_search_statistics,
    commercial_value_statistics,
    ownership_metrics,
)
from seo_workbench.statistics_history import load_daily_history, load_history_coverage
from seo_workbench.tech_audit import (
    link_scope,
    load_tech_inventory,
    load_tech_issues,
    load_tech_snapshot,
    normalize_url,
    page_type,
)
from seo_workbench.technical_statistics import evaluate_technical_issue_effects
from seo_workbench_tools.files import atomic_write_text


RULES = {
    "minimum_impressions": 100,
    "minimum_age_days": 28,
    "click_change": {"minimum_absolute": 3, "minimum_relative": 0.10},
    "decay": {"minimum_absolute": -3, "maximum_relative": -0.20},
    "ctr_opportunity": {"maximum_ctr": 0.02, "maximum_position": 10},
    "striking_distance": {"minimum_position": 4, "maximum_position": 15},
    "multiple_page_query": {"minimum_total_impressions": 100},
}
LIVE_CONTENT_STATUSES = {"scheduled", "submitted_for_indexing", "indexed", "indexing_issue"}


def analyze_content_portfolio(
    project_dir: Path,
    *,
    gsc_path: Path | None = None,
    business_path: Path | None = None,
    now: datetime | None = None,
) -> tuple[dict[str, Any], Path]:
    generated_at = (now or datetime.now(timezone.utc)).astimezone(timezone.utc)
    source_path = gsc_path or state.safe_project_path(project_dir, "audits/gsc/search-analytics/latest.json")
    try:
        gsc = _read_json(source_path, "GSC Search Analytics artifact")
    except FileNotFoundError:
        if gsc_path is not None:
            raise
        gsc = {}
    gsc_ready = gsc.get("collection_status") == "ok"
    if gsc_ready:
        previous = _page_window(gsc, "previous")
        current = _page_window(gsc, "current")
        previous_queries = ((gsc.get("windows") or {}).get("previous") or {}).get("query_page")
        current_queries = ((gsc.get("windows") or {}).get("current") or {}).get("query_page")
        if not isinstance(current_queries, dict) or not isinstance(current_queries.get("rows"), list):
            raise ValueError("GSC Search Analytics artifact has no query-page evidence; collect GSC again")
        if not isinstance(previous_queries, dict) or not isinstance(previous_queries.get("rows"), list):
            previous_queries = {"rows": []}
        if current_queries.get("truncated") or previous_queries.get("truncated"):
            raise ValueError("GSC query-page evidence is truncated; refusing partial statistical guidance")
        comparability = _comparability(previous, current)
    else:
        previous, current, previous_queries, current_queries = {}, {}, {"rows": []}, {"rows": []}
        comparability = {"comparable": False, "issues": ["GSC Search Analytics evidence is not complete"]}

    regime_breaks = {"gsc": [], "business": []}
    if gsc_ready:
        comparison_start = str((previous.get("request") or {}).get("startDate") or "")
        comparison_end = str((current.get("request") or {}).get("endDate") or "")
        regime_breaks["gsc"] = comparison_breaks(
            project_dir, start_date=comparison_start, end_date=comparison_end, sources={"gsc"}
        )
        regime_breaks["business"] = comparison_breaks(
            project_dir,
            start_date=comparison_start,
            end_date=comparison_end,
            sources={"ga4", "shopify", "consent"},
        )
        if regime_breaks["gsc"]:
            comparability["comparable"] = False
            comparability["issues"].append("GSC measurement regime changed inside the comparison range.")

    project = state.load_state(project_dir)
    project_url = str((project.get("project") or {}).get("url", ""))
    content = _content_items(project_dir, project)
    technical_path = state.safe_project_path(project_dir, "audits/tech-audit/latest.json")
    technical_snapshot = load_tech_snapshot(project_dir, technical_path)
    technical = _technical_pages(project_dir, project_url)
    previous_metrics = _gsc_metrics_by_url(previous.get("rows", []), project_url)
    current_metrics = _gsc_metrics_by_url(current.get("rows", []), project_url)
    business_source = business_path or state.safe_project_path(project_dir, "audits/business-signals/latest.json")
    business_report = _read_json(business_source, "business signal artifact") if business_source.is_file() else {}
    business_comparable = (
        gsc_ready
        and business_report.get("collection_status") == "ok"
        and _business_matches_gsc(business_report, previous, current)
        and not regime_breaks["business"]
    )
    urls = set(content) | set(technical) | set(previous_metrics) | set(current_metrics)
    if business_comparable:
        urls.update(_business_urls(business_report, project_url))
    queries, conflicts = _query_evidence(current_queries["rows"], urls, project_url)
    search_statistics = build_search_statistics(previous_queries["rows"], current_queries["rows"], project_url)
    longitudinal = (
        build_longitudinal_statistics(
            load_daily_history(project_dir, "gsc"),
            load_daily_history(project_dir, "business"),
            load_history_coverage(project_dir),
            previous=previous,
            current=current,
            include_business=business_comparable,
        )
        if gsc_ready
        else {"portfolio": {}, "pages": {}}
    )
    business = _business_metrics(business_report, urls) if business_comparable else {}
    business_status = _source_status(business_report)
    if business_report and not business_comparable:
        business_status.update(
            status="incomparable",
            reason=(
                "Business measurement regime changed inside the comparison range."
                if regime_breaks["business"]
                else "Business and GSC previous/current windows must match exactly."
            ),
        )
    if business_path and not business_source.is_file():
        raise FileNotFoundError(f"business signal artifact not found: {business_source}")

    current_end = date.fromisoformat(str((current.get("request") or {}).get("endDate"))) if gsc_ready else generated_at.date()
    rows = []
    for url in urls:
        item = content.get(url, {})
        tech = technical.get(url, {})
        before = previous_metrics.get(url)
        after = current_metrics.get(url)
        previous_business = business.get(url, {}).get("previous", {})
        current_business = business.get(url, {}).get("current", {})
        if before is not None or previous_business:
            before = (before or {}) | previous_business
        if after is not None or current_business:
            after = (after or {}) | current_business
        delta = _deltas(before, after) if before is not None and after is not None else None
        query_signals = conflicts.get(url, [])
        page_statistics = {
            **dict((search_statistics.get("pages") or {}).get(url) or {}),
            **dict((longitudinal.get("pages") or {}).get(url) or {}),
        }
        decision, recommendation, signals = _decision(
            item,
            before,
            after,
            delta,
            query_signals,
            current_end,
            statistics=page_statistics,
            comparable=comparability["comparable"],
        )
        rows.append(
            {
                "row_key": url,
                "id": item.get("id", ""),
                "title": item.get("title") or item.get("cluster_name") or tech.get("title") or _url_title(url),
                "url": url,
                "page_type": page_type(url),
                "status": item.get("status", "observed"),
                "sources": {
                    "gsc_current": url in current_metrics,
                    "gsc_previous": url in previous_metrics,
                    "technical": url in technical,
                    "content": url in content,
                    "business": url in business,
                },
                "business_currency": business_report.get("currency", "") if url in business else "",
                "content_item": _compact_content(item),
                "technical": tech,
                "decision": decision,
                "recommendation": recommendation,
                "signals": signals,
                "metrics": {"previous": before, "current": after, "delta": delta},
                "statistics": page_statistics,
                "top_queries": queries.get(url, [])[:10],
                "multiple_page_queries": query_signals[:5],
            }
        )
    commercial_statistics = commercial_value_statistics(rows, currency=str(business_report.get("currency", "")))
    technical_statistics = evaluate_technical_issue_effects(project_dir)
    for row in rows:
        effects = (technical_statistics.get("pages") or {}).get(row["url"])
        if effects:
            row["statistics"]["technical_issue_effects"] = effects
    rows.sort(
        key=lambda row: (
            _decision_order(str(row["decision"])),
            -float((row["metrics"]["current"] or {}).get("impressions", 0)),
            row["url"],
        )
    )
    counts = Counter(str(row["decision"]) for row in rows)
    report = {
        "schema_version": "content-portfolio-v4",
        "collection_status": "ok" if gsc_ready else "partial",
        "generated_at": generated_at.isoformat(),
        "comparability": comparability,
        "rules": RULES,
        "count": len(rows),
        "counts": dict(sorted(counts.items())),
        "statistics": (
            (search_statistics.get("portfolio") or {})
            | (longitudinal.get("portfolio") or {})
            | {
                "commercial_value": commercial_statistics,
                "technical_issue_effects": {
                    key: value for key, value in technical_statistics.items() if key != "pages"
                },
            }
        ),
        "items": rows,
        "source_status": {
            "gsc": _source_status(gsc),
            "technical": _source_status(technical_snapshot),
            "business": business_status,
            "statistics_history": {
                "status": (
                    "ok"
                    if (longitudinal.get("portfolio") or {}).get("search_change_confidence", {}).get("status") == "ok"
                    else "insufficient_data"
                ),
                "schema_version": longitudinal.get("schema_version", ""),
            },
        },
        "measurement_regimes": regime_breaks,
        "source": {
            "gsc_path": str(source_path),
            "technical_path": str(technical_path),
            "business_path": str(business_source) if business_source.is_file() else "",
            "business_comparable": business_comparable,
            "statistics_history_path": str(
                state.safe_project_path(project_dir, "audits/statistics/history/coverage.json")
            ),
        },
        "mutation_performed": False,
    }
    output_dir = state.safe_project_path(project_dir, "audits/content-portfolio")
    output_dir.mkdir(parents=True, exist_ok=True)
    path = output_dir / f"content-portfolio-{generated_at.strftime('%Y%m%dT%H%M%S%fZ')}.json"
    _write(path, report)
    _write(output_dir / "latest.json", report)
    return report, path


def _content_items(project_dir: Path, project: dict[str, Any]) -> dict[str, dict[str, Any]]:
    merged: dict[str, dict[str, Any]] = {}
    queue = project.get("contentQueue") or []
    for item in queue if isinstance(queue, list) else []:
        if isinstance(item, dict) and item.get("id"):
            merged[str(item["id"])] = dict(item)
    pipeline = state.safe_project_path(project_dir, "content/blog-pipeline.jsonl")
    if pipeline.is_file():
        for line_number, line in enumerate(pipeline.read_text(encoding="utf-8").splitlines(), start=1):
            if not line.strip():
                continue
            try:
                item = json.loads(line)
            except json.JSONDecodeError as exc:
                raise ValueError(f"invalid content pipeline line {line_number}: {exc.msg}") from exc
            if isinstance(item, dict) and item.get("id"):
                merged.setdefault(str(item["id"]), {}).update(item)
    project_url = str((project.get("project") or {}).get("url", "")).rstrip("/")
    result: dict[str, dict[str, Any]] = {}
    for item in merged.values():
        if item.get("status") not in LIVE_CONTENT_STATUSES:
            continue
        live_url = normalize_url(str(item.get("live_url") or ""))
        if not live_url and item.get("status") == "indexed" and item.get("slug"):
            live_url = normalize_url(f"{project_url}/blogs/articles/{item['slug']}")
        if live_url and link_scope(live_url, project_url)[1] in {"same_host", "subdomain"}:
            result[live_url] = item | {"live_url": live_url}
    return result


def _technical_pages(project_dir: Path, project_url: str) -> dict[str, dict[str, Any]]:
    issue_counts = Counter(
        normalize_url(str(issue.get("url", "")))
        for issue in load_tech_issues(project_dir)
        if issue.get("url")
    )
    result = {}
    for page in load_tech_inventory(project_dir):
        url = normalize_url(str(page.get("url", "")))
        if not url or link_scope(url, project_url)[1] not in {"same_host", "subdomain"}:
            continue
        result[url] = {
            key: page.get(key)
            for key in (
                "status_code",
                "final_url",
                "indexability",
                "title",
                "meta_description",
                "h1",
                "canonical",
                "crawl_depth",
                "inlink_count",
                "outlink_count",
                "response_time_ms",
                "crawl_status",
                "error",
            )
        } | {"issue_count": issue_counts.get(url, 0)}
    return result


def _compact_content(item: dict[str, Any]) -> dict[str, Any]:
    return {
        key: item.get(key)
        for key in ("id", "status", "title", "slug", "live_url", "scheduled_at", "target_keyword")
        if item.get(key) not in (None, "")
    }


def _source_status(report: dict[str, Any]) -> dict[str, Any]:
    return {
        "status": report.get("collection_status", "not_collected"),
        "generated_at": report.get("generated_at"),
        "schema_version": report.get("schema_version"),
    }


def _page_window(gsc: dict[str, Any], name: str) -> dict[str, Any]:
    page = (((gsc.get("windows") or {}).get(name) or {}).get("page"))
    if not isinstance(page, dict):
        raise ValueError(f"GSC Search Analytics artifact has no {name} page window")
    if page.get("truncated"):
        raise ValueError(f"GSC Search Analytics {name} page window is truncated")
    return page


def _comparability(previous: dict[str, Any], current: dict[str, Any]) -> dict[str, Any]:
    previous_start, previous_end = _request_days(previous, "previous")
    current_start, current_end = _request_days(current, "current")
    issues = []
    if (previous_end - previous_start).days != (current_end - current_start).days:
        issues.append("previous and current windows have different durations")
    if previous_end >= current_start:
        issues.append("previous and current windows overlap")
    return {"comparable": not issues, "issues": issues}


def _request_days(window: dict[str, Any], name: str) -> tuple[date, date]:
    request = window.get("request") or {}
    try:
        start = date.fromisoformat(str(request.get("startDate", "")))
        end = date.fromisoformat(str(request.get("endDate", "")))
    except ValueError as exc:
        raise ValueError(f"GSC {name} window must include YYYY-MM-DD startDate and endDate") from exc
    if start > end:
        raise ValueError(f"GSC {name} startDate cannot be after endDate")
    return start, end


def _gsc_metrics_by_url(rows: list[Any], project_url: str) -> dict[str, dict[str, float]]:
    grouped: dict[str, list[dict[str, Any]]] = {}
    for row in rows:
        keys = row.get("keys") if isinstance(row, dict) else None
        url = normalize_url(str(keys[0])) if isinstance(keys, list) and keys else ""
        if url and link_scope(url, project_url)[1] in {"same_host", "subdomain"}:
            grouped.setdefault(url, []).append(row)
    result = {}
    for url, selected in grouped.items():
        clicks = sum(float(row.get("clicks") or 0) for row in selected)
        impressions = sum(float(row.get("impressions") or 0) for row in selected)
        position = (
            sum(float(row.get("position") or 0) * float(row.get("impressions") or 0) for row in selected)
            / impressions
            if impressions
            else 0
        )
        result[url] = {
            "clicks": round(clicks, 4),
            "impressions": round(impressions, 4),
            "ctr": round(clicks / impressions, 6) if impressions else 0.0,
            "position": round(position, 4),
        }
    return result


def _business_metrics(report: dict[str, Any], urls: set[str]) -> dict[str, dict[str, dict[str, float]]]:
    if report.get("collection_status") != "ok":
        raise ValueError("business signal artifact is not complete")
    result: dict[str, dict[str, dict[str, float]]] = {}
    for name in ("previous", "current"):
        rows = (((report.get("windows") or {}).get(name) or {}).get("rows")) or []
        for row in rows:
            url = normalize_url(str(row.get("url", ""))) if isinstance(row, dict) else ""
            if url in urls:
                result.setdefault(url, {}).setdefault(name, {}).update(
                    {metric: float(row[metric]) for metric in BUSINESS_METRICS if metric in row}
                )
    return result


def _business_urls(report: dict[str, Any], project_url: str) -> set[str]:
    result = set()
    for window in (report.get("windows") or {}).values():
        for row in window.get("rows", []) if isinstance(window, dict) else []:
            url = normalize_url(str(row.get("url", ""))) if isinstance(row, dict) else ""
            if url and link_scope(url, project_url)[1] in {"same_host", "subdomain"}:
                result.add(url)
    return result


def _business_matches_gsc(report: dict[str, Any], previous: dict[str, Any], current: dict[str, Any]) -> bool:
    for name, window in (("previous", previous), ("current", current)):
        business_request = ((report.get("windows") or {}).get(name) or {}).get("request") or {}
        gsc_request = window.get("request") or {}
        if (business_request.get("startDate"), business_request.get("endDate")) != (
            gsc_request.get("startDate"),
            gsc_request.get("endDate"),
        ):
            return False
    return True


def _deltas(previous: dict[str, float], current: dict[str, float]) -> dict[str, dict[str, float | None]]:
    result = {}
    for metric in previous.keys() & current.keys():
        before, after = float(previous[metric]), float(current[metric])
        result[metric] = {"absolute": round(after - before, 6), "relative": round((after - before) / before, 6) if before else None}
    return result


def _query_evidence(
    rows: list[Any], target_urls: set[str], project_url: str
) -> tuple[dict[str, list[dict[str, Any]]], dict[str, list[dict[str, Any]]]]:
    queries: dict[str, dict[str, dict[str, float | str]]] = {}
    for row in rows:
        keys = row.get("keys") if isinstance(row, dict) else None
        if not isinstance(keys, list) or len(keys) < 2:
            continue
        query, url = str(keys[0]).strip(), normalize_url(str(keys[1]))
        if query and url and link_scope(url, project_url)[1] in {"same_host", "subdomain"}:
            owner = queries.setdefault(query.casefold(), {}).setdefault(
                url,
                {"query": query, "url": url, "clicks": 0.0, "impressions": 0.0, "position_total": 0.0},
            )
            impressions = float(row.get("impressions") or 0)
            owner["clicks"] = float(owner["clicks"]) + float(row.get("clicks") or 0)
            owner["impressions"] = float(owner["impressions"]) + impressions
            owner["position_total"] = float(owner["position_total"]) + float(row.get("position") or 0) * impressions
    by_url: dict[str, list[dict[str, Any]]] = {}
    conflicts: dict[str, list[dict[str, Any]]] = {}
    for owners_by_url in queries.values():
        owners = list(owners_by_url.values())
        for owner in owners:
            impressions = float(owner["impressions"])
            evidence = {
                "query": owner["query"],
                "clicks": round(float(owner["clicks"]), 4),
                "impressions": round(impressions, 4),
                "ctr": round(float(owner["clicks"]) / impressions, 6) if impressions else 0.0,
                "position": round(float(owner["position_total"]) / impressions, 4) if impressions else 0.0,
            }
            if owner["url"] in target_urls:
                by_url.setdefault(str(owner["url"]), []).append(evidence)
        total = sum(float(owner["impressions"]) for owner in owners)
        if len(owners) < 2 or total < RULES["multiple_page_query"]["minimum_total_impressions"]:
            continue
        ranked = sorted(owners, key=lambda owner: (-float(owner["impressions"]), str(owner["url"])))
        signal = {
            "query": str(ranked[0]["query"]),
            "owner_count": len(owners),
            "total_impressions": round(total, 4),
            "ownership": ownership_metrics(owners),
            "owners": [
                {"url": owner["url"], "impressions": round(float(owner["impressions"]), 4)}
                for owner in ranked[:10]
            ],
        }
        for owner in owners:
            if owner["url"] in target_urls:
                conflicts.setdefault(str(owner["url"]), []).append(signal)
    for evidence in by_url.values():
        evidence.sort(key=lambda item: (-float(item["impressions"]), str(item["query"])))
    for signals in conflicts.values():
        signals.sort(key=lambda signal: (-signal["total_impressions"], signal["query"]))
    return by_url, conflicts


def _decision(
    item: dict[str, Any],
    previous: dict[str, float] | None,
    current: dict[str, float] | None,
    delta: dict[str, dict[str, float | None]] | None,
    conflicts: list[dict[str, Any]],
    current_end: date,
    *,
    statistics: dict[str, Any],
    comparable: bool,
) -> tuple[str, str, list[str]]:
    if current is None or "impressions" not in current:
        return "wait_for_data", "No finalized GSC page observation is available for this URL.", ["gsc_not_observed"]
    if not comparable:
        return "wait_for_data", "Collect equal, non-overlapping finalized windows before making a decision.", ["incomparable_windows"]
    clicks = (delta or {}).get("clicks")
    confidence = statistics.get("search_change_confidence") or {}
    click_direction = (confidence.get("click_change") or {}).get("direction") if confidence.get("status") == "ok" else None
    ctr_benchmark = statistics.get("ctr_benchmark") or {}
    published = _published_day(item)
    if clicks and float(clicks["absolute"]) <= RULES["decay"]["minimum_absolute"] and clicks["relative"] is not None and float(clicks["relative"]) <= RULES["decay"]["maximum_relative"] and click_direction in {None, "decrease"}:
        return "refresh", "Investigate decay, refresh the page, and review intent coverage.", ["click_decay"]
    if published and (current_end - published).days < RULES["minimum_age_days"]:
        return "wait_for_data", "Wait until the page has a complete observation window.", ["new_content"]
    if current["impressions"] < RULES["minimum_impressions"]:
        return "wait_for_data", "Collect more finalized impressions before changing the page.", ["low_impressions"]
    if conflicts:
        return "consolidate_review", "Review query ownership before merging, redirecting, or differentiating pages.", ["multiple_page_query"]
    if ctr_benchmark.get("classification") == "below_expected":
        return "improve_snippet", "Test the snippet for pages below the FDR-controlled internal CTR benchmark.", ["fdr_ctr_opportunity"]
    if ctr_benchmark.get("q_value") is None and current["position"] <= RULES["ctr_opportunity"]["maximum_position"] and current["ctr"] <= RULES["ctr_opportunity"]["maximum_ctr"]:
        return "improve_snippet", "Test title and meta description against the dominant query intent.", ["low_ctr_on_page_one"]
    if RULES["striking_distance"]["minimum_position"] <= current["position"] <= RULES["striking_distance"]["maximum_position"]:
        return "expand_and_link", "Strengthen intent coverage and add relevant internal links.", ["striking_distance"]
    if clicks and float(clicks["absolute"]) >= RULES["click_change"]["minimum_absolute"] and (clicks["relative"] is None or float(clicks["relative"]) >= RULES["click_change"]["minimum_relative"]) and click_direction in {None, "increase"}:
        return "defend", "Preserve the winning page and monitor ownership and business signals.", ["click_growth"]
    return "monitor", "Keep the page stable and review it in the next comparable window.", ["stable"]


def _published_day(item: dict[str, Any]) -> date | None:
    value = str(item.get("published_at") or item.get("scheduled_at") or "")
    if not value:
        return None
    try:
        return date.fromisoformat(value[:10])
    except ValueError:
        return None


def _decision_order(decision: str) -> int:
    return ("refresh", "consolidate_review", "improve_snippet", "expand_and_link", "defend", "monitor", "wait_for_data").index(decision)


def _url_title(url: str) -> str:
    path = urlsplit(url).path.rstrip("/")
    if not path:
        return urlsplit(url).hostname or url
    return path.rsplit("/", 1)[-1].replace("-", " ").replace("_", " ").strip().title()


def _read_json(path: Path, label: str) -> dict[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise FileNotFoundError(f"{label} not found: {path}") from exc
    except json.JSONDecodeError as exc:
        raise ValueError(f"invalid {label}: {exc.msg}") from exc
    if not isinstance(payload, dict):
        raise ValueError(f"invalid {label}: expected an object")
    return payload


def _write(path: Path, report: dict[str, Any]) -> None:
    atomic_write_text(path, json.dumps(report, ensure_ascii=False, indent=2) + "\n", mode=0o600)
