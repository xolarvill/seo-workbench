from __future__ import annotations

import hashlib
import json
import math
import re
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from seo_workbench import state
from seo_workbench.business_signals import METRICS as BUSINESS_METRICS
from seo_workbench.gsc import collect_change_performance
from seo_workbench.measurement_regimes import comparison_breaks
from seo_workbench.seo_changes import get_change, list_changes
from seo_workbench.statistics_history import load_daily_history, load_history_coverage
from seo_workbench.statistics_methods import moving_block_did, moving_block_differences, percentile
from seo_workbench.tech_audit import normalize_url, page_type
from seo_workbench_tools.files import atomic_write_text


SAFE_ID = re.compile(r"^[A-Za-z0-9._-]+$")
GSC_METRICS = {"clicks", "impressions", "ctr", "position"}
SUPPORTED_METRICS = GSC_METRICS | set(BUSINESS_METRICS)
_EFFECT_FIELDS = {"clicks": "click_change", "impressions": "impression_change", "ctr": "ctr_change"}
_SIGNAL_VERDICTS = {"improving": "winning", "regressing": "regressing", "flat": "no_change"}
SIGNAL_RULES = {
    "clicks": {"direction": "higher", "minimum_absolute_delta": 3.0, "minimum_relative_delta": 0.10},
    "impressions": {"direction": "higher", "minimum_absolute_delta": 10.0, "minimum_relative_delta": 0.10},
    "ctr": {"direction": "higher", "minimum_absolute_delta": 0.01, "minimum_impressions_per_window": 100.0},
    "position": {"direction": "lower", "minimum_absolute_delta": 1.0, "minimum_impressions_per_window": 100.0},
    "organic_sessions": {"direction": "higher", "minimum_absolute_delta": 3.0, "minimum_relative_delta": 0.10},
    "engaged_sessions": {"direction": "higher", "minimum_absolute_delta": 3.0, "minimum_relative_delta": 0.10},
    "key_events": {"direction": "higher", "minimum_absolute_delta": 1.0, "minimum_relative_delta": 0.10},
    "conversions": {"direction": "higher", "minimum_absolute_delta": 1.0, "minimum_relative_delta": 0.10},
    "organic_product_views": {"direction": "higher", "minimum_absolute_delta": 1.0, "minimum_relative_delta": 0.10},
    "organic_add_to_carts": {"direction": "higher", "minimum_absolute_delta": 1.0, "minimum_relative_delta": 0.10},
    "organic_checkouts": {"direction": "higher", "minimum_absolute_delta": 1.0, "minimum_relative_delta": 0.10},
    "organic_purchases": {"direction": "higher", "minimum_absolute_delta": 1.0, "minimum_relative_delta": 0.10},
    "organic_revenue": {"direction": "higher", "minimum_absolute_delta": 1.0, "minimum_relative_delta": 0.10},
    "revenue": {"direction": "higher", "minimum_absolute_delta": 1.0, "minimum_relative_delta": 0.10},
    "orders": {"direction": "higher", "minimum_absolute_delta": 1.0, "minimum_relative_delta": 0.10},
}


def evaluate_change_with_fresh_gsc(
    project_dir: Path,
    change_id: str,
    *,
    business_path: Path | None = None,
    timeout: float = 30,
) -> tuple[dict[str, Any], Path]:
    change = get_change(project_dir, change_id)
    gsc = collect_change_performance(
        project_dir,
        state.safe_project_path(project_dir, f"audits/gsc/change-outcomes/{change_id}"),
        urls=[str(url) for url in change.get("urls", [])],
        changed_at=date.fromisoformat(str(change.get("changed_at", ""))),
        review_date=date.fromisoformat(str(change.get("review_date", ""))),
        timeout=timeout,
    )
    return evaluate_change(project_dir, change_id, gsc_path=Path(gsc["manifest"]["path"]), business_path=business_path)


def evaluate_change(
    project_dir: Path,
    change_id: str,
    *,
    gsc_path: Path | None = None,
    business_path: Path | None = None,
    now: datetime | None = None,
) -> tuple[dict[str, Any], Path]:
    if not SAFE_ID.fullmatch(change_id):
        raise ValueError("invalid SEO change id")
    change = get_change(project_dir, change_id)
    source_path = gsc_path or state.safe_project_path(project_dir, "audits/gsc/search-analytics/latest.json")
    gsc = _read_json(source_path, "GSC Search Analytics artifact")
    if gsc.get("collection_status") != "ok":
        raise ValueError("GSC Search Analytics artifact is not complete")

    current = _window(gsc, "current")
    previous = _window(gsc, "previous")
    changed_urls = {normalize_url(str(url)) for url in change.get("urls", [])}
    current_metrics = _aggregate_pages(current["page"].get("rows", []), changed_urls)
    previous_metrics = _aggregate_pages(previous["page"].get("rows", []), changed_urls)
    expected = [str(metric) for metric in change.get("expected_metrics", [])]
    required_business = bool(set(expected) & set(BUSINESS_METRICS))
    business_source = business_path or state.safe_project_path(project_dir, "audits/business-signals/latest.json")
    missing = []
    gsc_check = _window_check(change, previous["page"], current["page"])
    comparison_start = str((previous["page"].get("request") or {}).get("startDate") or "")
    comparison_end = str((current["page"].get("request") or {}).get("endDate") or "")
    regime_breaks = {
        "gsc": comparison_breaks(
            project_dir, start_date=comparison_start, end_date=comparison_end, sources={"gsc"}
        ),
        "business": comparison_breaks(
            project_dir,
            start_date=comparison_start,
            end_date=comparison_end,
            sources={"ga4", "shopify", "consent"},
        ),
    }
    if regime_breaks["gsc"]:
        gsc_check["comparable"] = False
        gsc_check["issues"].append("GSC measurement regime changed inside the outcome range")
    checks = {"gsc": gsc_check}
    if required_business and business_source.is_file():
        business = _read_json(business_source, "business signal artifact")
        if business.get("collection_status") != "ok":
            raise ValueError("business signal artifact is not complete")
        business_previous = _business_window(business, "previous")
        business_current = _business_window(business, "current")
        previous_business = _aggregate_business(business_previous.get("rows", []), changed_urls)
        current_business = _aggregate_business(business_current.get("rows", []), changed_urls)
        previous_metrics.update(previous_business)
        current_metrics.update(current_business)
        missing.extend(
            sorted((set(expected) & set(BUSINESS_METRICS)) - (previous_business.keys() & current_business.keys()))
        )
        checks["business"] = _window_check(change, business_previous, business_current)
        if regime_breaks["business"]:
            checks["business"]["comparable"] = False
            checks["business"]["issues"].append("business measurement regime changed inside the outcome range")
    elif required_business:
        missing.extend(sorted(set(expected) & set(BUSINESS_METRICS)))
    deltas = _deltas(previous_metrics, current_metrics)
    window_check = {
        **gsc_check,
        "comparable": all(check["comparable"] for check in checks.values()),
        "issues": [
            issue if source == "gsc" else f"{source}: {issue}"
            for source, check in checks.items()
            for issue in check["issues"]
        ],
        "sources": checks,
    }
    signals = {
        metric: _signal(metric, previous_metrics, current_metrics, deltas)
        for metric in expected
        if metric in SUPPORTED_METRICS and metric not in missing
    }
    unsupported = [metric for metric in expected if metric not in SUPPORTED_METRICS]
    effect = _pre_post_effect(previous, current, changed_urls, change_id)
    verdicts = _metric_verdicts(signals, effect, expected)
    classification = _overall_classification(window_check, verdicts, unsupported)
    matched_control = _matched_control_effect(project_dir, change, previous, current, changed_urls)
    queries = _query_ownership(current["query_page"].get("rows", []), changed_urls)
    generated_at = (now or datetime.now(timezone.utc)).astimezone(timezone.utc)
    report = {
        "schema_version": "seo-outcome-v2",
        "collection_status": "ok",
        "generated_at": generated_at.isoformat(),
        "change": change,
        "classification": classification,
        "causal_claim": False,
        "interpretation": "Statistically bounded per-metric pre/post evidence; metrics without sufficient evidence are reported as insufficient_data instead of vetoing the outcome. Matched controls are observational when available. Concurrent demand, SERP, campaign, stock, price, and site changes may contribute.",
        "comparability": window_check,
        "measurement_regimes": regime_breaks,
        "metrics": {"previous": previous_metrics, "current": current_metrics, "delta": deltas},
        "expected_metric_signals": signals,
        "metric_verdicts": verdicts,
        "unsupported_expected_metrics": unsupported,
        "missing_expected_metrics": missing,
        "signal_rules": SIGNAL_RULES,
        "query_ownership": queries,
        "statistical_evidence": {
            "pre_post": effect,
            "matched_control": matched_control,
            "causal_claim": False,
        },
        "source": {
            "path": str(source_path),
            "property": gsc.get("property", ""),
            "data_state": gsc.get("data_state", ""),
            "business_path": str(business_source) if required_business and business_source.is_file() else "",
        },
    }
    output_dir = state.safe_project_path(project_dir, f"audits/outcomes/{change_id}")
    output_dir.mkdir(parents=True, exist_ok=True)
    path = output_dir / f"outcome-{generated_at.strftime('%Y%m%dT%H%M%S%fZ')}.json"
    _write_private(path, report)
    _write_private(output_dir / "latest.json", report)
    return report, path


def _window(gsc: dict[str, Any], name: str) -> dict[str, Any]:
    window = (gsc.get("windows") or {}).get(name)
    if not isinstance(window, dict):
        raise ValueError(f"GSC Search Analytics artifact has no {name} window")
    page = window.get("page")
    query_page = window.get("query_page")
    if not isinstance(page, dict):
        raise ValueError(f"GSC Search Analytics {name} window has no page evidence")
    if name == "current" and not isinstance(query_page, dict):
        raise ValueError("GSC Search Analytics artifact has no query-page evidence; collect GSC again")
    date_page = window.get("date_page")
    return {
        "page": page,
        "date_page": date_page if isinstance(date_page, dict) else {},
        "query_page": query_page if isinstance(query_page, dict) else {"rows": []},
    }


def _business_window(report: dict[str, Any], name: str) -> dict[str, Any]:
    window = (report.get("windows") or {}).get(name)
    if not isinstance(window, dict):
        raise ValueError(f"business signal artifact has no {name} window")
    return window


def _window_check(change: dict[str, Any], previous: dict[str, Any], current: dict[str, Any]) -> dict[str, Any]:
    changed_at = _parse_day(str(change.get("changed_at", "")), "change.changed_at")
    review_date = _parse_day(str(change.get("review_date", "")), "change.review_date")
    previous_request = previous.get("request") or {}
    current_request = current.get("request") or {}
    previous_end = _parse_day(str(previous_request.get("endDate", "")), "previous endDate")
    current_start = _parse_day(str(current_request.get("startDate", "")), "current startDate")
    current_end = _parse_day(str(current_request.get("endDate", "")), "current endDate")
    issues = []
    if previous_end >= changed_at:
        issues.append("previous window includes change-day or post-change dates")
    if current_start <= changed_at:
        issues.append("current window includes pre-change or change-day dates")
    if current_end < review_date:
        issues.append("current window does not reach the planned review date")
    return {
        "comparable": not issues,
        "issues": issues,
        "changed_at": changed_at.isoformat(),
        "review_date": review_date.isoformat(),
        "previous_end": previous_end.isoformat(),
        "current_start": current_start.isoformat(),
        "current_end": current_end.isoformat(),
    }


def _aggregate_pages(rows: list[Any], urls: set[str]) -> dict[str, float | int]:
    selected = []
    for row in rows:
        if not isinstance(row, dict):
            continue
        keys = row.get("keys") or []
        if keys and normalize_url(str(keys[0])) in urls:
            selected.append(row)
    clicks = sum(float(row.get("clicks") or 0) for row in selected)
    impressions = sum(float(row.get("impressions") or 0) for row in selected)
    position = (
        sum(float(row.get("position") or 0) * float(row.get("impressions") or 0) for row in selected) / impressions
        if impressions
        else 0.0
    )
    return {
        "expected_pages": len(urls),
        "matched_pages": len(selected),
        "clicks": round(clicks, 4),
        "impressions": round(impressions, 4),
        "ctr": round(clicks / impressions, 6) if impressions else 0.0,
        "position": round(position, 4),
    }


def _aggregate_business(rows: list[Any], urls: set[str]) -> dict[str, float]:
    selected = [row for row in rows if isinstance(row, dict) and normalize_url(str(row.get("url", ""))) in urls]
    return {
        metric: round(sum(float(row[metric]) for row in selected), 4)
        for metric in BUSINESS_METRICS
        if len(selected) == len(urls) and all(metric in row for row in selected)
    }


def _deltas(previous: dict[str, float | int], current: dict[str, float | int]) -> dict[str, Any]:
    result = {}
    for metric in previous.keys() & current.keys() & SUPPORTED_METRICS:
        before = float(previous[metric])
        after = float(current[metric])
        result[metric] = {
            "absolute": round(after - before, 6),
            "relative": round((after - before) / before, 6) if before else None,
        }
    return result


def _signal(
    metric: str,
    previous: dict[str, float | int],
    current: dict[str, float | int],
    deltas: dict[str, Any],
) -> str:
    rule = SIGNAL_RULES[metric]
    if int(previous.get("matched_pages", 0)) < int(previous.get("expected_pages", 0)) or int(
        current.get("matched_pages", 0)
    ) < int(current.get("expected_pages", 0)):
        return "insufficient_data"
    minimum_impressions = float(rule.get("minimum_impressions_per_window", 0))
    if minimum_impressions and (
        float(previous["impressions"]) < minimum_impressions or float(current["impressions"]) < minimum_impressions
    ):
        return "insufficient_data"
    absolute = float(deltas[metric]["absolute"])
    if abs(absolute) < float(rule["minimum_absolute_delta"]):
        return "flat"
    minimum_relative = float(rule.get("minimum_relative_delta", 0))
    relative = deltas[metric]["relative"]
    if minimum_relative and relative is not None and abs(float(relative)) < minimum_relative:
        return "flat"
    improving = absolute > 0 if rule["direction"] == "higher" else absolute < 0
    return "improving" if improving else "regressing"


def _metric_verdicts(signals: dict[str, str], effect: dict[str, Any], expected: list[str]) -> dict[str, str]:
    """Per-expected-metric verdict; a metric without sufficient evidence is insufficient_data on its own."""
    verdicts: dict[str, str] = {}
    for metric in expected:
        if metric not in SUPPORTED_METRICS:
            continue
        signal = signals.get(metric, "insufficient_data")
        effect_field = _EFFECT_FIELDS.get(metric)
        if signal == "insufficient_data":
            verdicts[metric] = "insufficient_data"
        elif effect_field and (effect.get("status") != "ok" or (effect.get(effect_field) or {}).get("direction") == "uncertain"):
            verdicts[metric] = "insufficient_data"
        else:
            verdicts[metric] = _SIGNAL_VERDICTS.get(signal, "insufficient_data")
    return verdicts


def _overall_classification(
    window_check: dict[str, Any],
    verdicts: dict[str, str],
    unsupported: list[str],
) -> str:
    if not window_check["comparable"] or unsupported:
        return "insufficient_data"
    sufficient = [verdict for verdict in verdicts.values() if verdict in {"winning", "regressing", "no_change"}]
    if not sufficient:
        return "insufficient_data"
    if "regressing" in sufficient:
        return "regressing"
    if "winning" in sufficient:
        return "winning"
    return "no_change"


def _query_ownership(rows: list[Any], changed_urls: set[str]) -> list[dict[str, Any]]:
    queries: dict[str, list[dict[str, Any]]] = {}
    for row in rows:
        if not isinstance(row, dict):
            continue
        keys = row.get("keys") or []
        if len(keys) < 2:
            continue
        query, page = str(keys[0]), normalize_url(str(keys[1]))
        if not query or not page:
            continue
        queries.setdefault(query, []).append(
            {
                "url": page,
                "clicks": float(row.get("clicks") or 0),
                "impressions": float(row.get("impressions") or 0),
                "ctr": float(row.get("ctr") or 0),
                "position": float(row.get("position") or 0),
            }
        )
    result = []
    for query, owners in queries.items():
        if not any(owner["url"] in changed_urls for owner in owners):
            continue
        owners.sort(key=lambda owner: (-owner["impressions"], owner["url"]))
        result.append(
            {
                "query": query,
                "total_impressions": round(sum(owner["impressions"] for owner in owners), 4),
                "owner_count": len(owners),
                "multiple_page_signal": len(owners) > 1,
                "owners": owners,
            }
        )
    result.sort(key=lambda item: (-item["total_impressions"], item["query"]))
    return result[:50]


def _pre_post_effect(
    previous: dict[str, Any],
    current: dict[str, Any],
    changed_urls: set[str],
    change_id: str,
) -> dict[str, Any]:
    before = _daily_metrics(previous.get("date_page") or {}, changed_urls)
    after = _daily_metrics(current.get("date_page") or {}, changed_urls)
    if before is None or after is None:
        return {"status": "insufficient_data", "reason": "complete date-page evidence is required"}
    if len(before["clicks"]) != len(after["clicks"]) or len(before["clicks"]) < 14:
        return {"status": "insufficient_data", "reason": "equal windows of at least 14 daily observations are required"}
    seed = int(hashlib.sha256(change_id.encode()).hexdigest()[:16], 16)
    click_change = _block_effect(before["clicks"], after["clicks"], seed)
    impression_change = _block_effect(before["impressions"], after["impressions"], seed + 1)
    previous_clicks, current_clicks = sum(before["clicks"]), sum(after["clicks"])
    previous_impressions, current_impressions = sum(before["impressions"]), sum(after["impressions"])
    previous_ctr, current_ctr = _wilson(previous_clicks, previous_impressions), _wilson(current_clicks, current_impressions)
    ctr_change = {
        "observed": round(current_clicks / current_impressions - previous_clicks / previous_impressions, 6),
        "ci95": [
            round(current_ctr["ci95"][0] - previous_ctr["ci95"][1], 6),
            round(current_ctr["ci95"][1] - previous_ctr["ci95"][0], 6),
        ],
    } if previous_ctr and current_ctr else None
    if ctr_change:
        ctr_change["direction"] = "increase" if ctr_change["ci95"][0] > 0 else "decrease" if ctr_change["ci95"][1] < 0 else "uncertain"
    return {
        "status": "ok",
        "design": "change-scoped pre/post; change day excluded",
        "method": "deterministic moving-block bootstrap; 7-day blocks; 500 samples",
        "days_per_window": len(before["clicks"]),
        "click_change": click_change,
        "impression_change": impression_change,
        "ctr_change": ctr_change,
        "causal_claim": False,
    }


def _daily_metrics(evidence: dict[str, Any], urls: set[str]) -> dict[str, list[float]] | None:
    if not evidence or evidence.get("truncated"):
        return None
    request = evidence.get("request") or {}
    try:
        start = date.fromisoformat(str(request.get("startDate") or ""))
        end = date.fromisoformat(str(request.get("endDate") or ""))
    except ValueError:
        return None
    daily = {
        (start + timedelta(days=offset)).isoformat(): {"clicks": 0.0, "impressions": 0.0}
        for offset in range((end - start).days + 1)
    }
    seen_urls = set()
    for row in evidence.get("rows") or []:
        keys = row.get("keys") or []
        if len(keys) < 2:
            continue
        day, url = str(keys[0]), normalize_url(str(keys[1]))
        if url in urls and day in daily:
            daily[day]["clicks"] += float(row.get("clicks") or 0)
            daily[day]["impressions"] += float(row.get("impressions") or 0)
            seen_urls.add(url)
    return (
        {metric: [daily[day][metric] for day in sorted(daily)] for metric in ("clicks", "impressions")}
        if seen_urls == urls
        else None
    )


def _block_effect(before: list[float], after: list[float], seed: int) -> dict[str, Any]:
    draws = moving_block_differences(before, after, seed=seed)
    lower, upper = percentile(draws, 0.025), percentile(draws, 0.975)
    return {
        "observed": round(sum(after) - sum(before), 4),
        "ci95": [round(lower, 4), round(upper, 4)],
        "probability_increase": round(sum(draw > 0 for draw in draws) / len(draws), 4),
        "direction": "increase" if lower > 0 else "decrease" if upper < 0 else "uncertain",
    }


def _wilson(successes: float, total: float) -> dict[str, Any] | None:
    if total <= 0 or successes < 0 or successes > total:
        return None
    estimate, z = successes / total, 1.96
    denominator = 1 + z * z / total
    center = (estimate + z * z / (2 * total)) / denominator
    margin = z * math.sqrt(estimate * (1 - estimate) / total + z * z / (4 * total * total)) / denominator
    return {
        "estimate": round(estimate, 6),
        "ci95": [round(max(0.0, center - margin), 6), round(min(1.0, center + margin), 6)],
    }


def _matched_control_effect(
    project_dir: Path,
    change: dict[str, Any],
    previous: dict[str, Any],
    current: dict[str, Any],
    changed_urls: set[str],
) -> dict[str, Any]:
    rows = load_daily_history(project_dir, "gsc")
    coverage = set(load_history_coverage(project_dir).get("gsc", []))
    before_dates = _request_dates(previous["page"])
    after_dates = _request_dates(current["page"])
    if not rows or any(day not in coverage for day in before_dates + after_dates):
        return {"status": "insufficient_data", "reason": "private GSC history does not cover both outcome windows"}
    indexed: dict[str, dict[str, dict[str, float]]] = {}
    for row in rows:
        indexed.setdefault(str(row.get("url") or ""), {})[str(row.get("date") or "")] = {
            "clicks": float(row.get("clicks") or 0),
            "impressions": float(row.get("impressions") or 0),
        }
    if any(url not in indexed for url in changed_urls):
        return {"status": "insufficient_data", "reason": "changed URLs are not fully observed in private GSC history"}
    target_before = _history_values(indexed, changed_urls, before_dates, "clicks")
    target_after = _history_values(indexed, changed_urls, after_dates, "clicks")
    target_impressions = sum(_history_values(indexed, changed_urls, before_dates, "impressions"))
    if target_impressions < 100:
        return {"status": "insufficient_data", "reason": "changed URLs have fewer than 100 pre-change impressions"}
    start, end = date.fromisoformat(before_dates[0]), date.fromisoformat(after_dates[-1])
    excluded = set(changed_urls)
    for other in list_changes(project_dir).get("changes", []):
        try:
            changed_at = date.fromisoformat(str(other.get("changed_at") or ""))
        except ValueError:
            continue
        if start <= changed_at <= end and other.get("status") != "cancelled":
            excluded.update(normalize_url(str(url)) for url in other.get("urls") or [])
    target_types = {page_type(url) for url in changed_urls}
    candidates = []
    for url, series in indexed.items():
        if not url or url in excluded or page_type(url) not in target_types:
            continue
        impressions = sum(float(series.get(day, {}).get("impressions", 0)) for day in before_dates)
        clicks = sum(float(series.get(day, {}).get("clicks", 0)) for day in before_dates)
        if impressions < 100:
            continue
        target_clicks = sum(target_before)
        distance = abs(math.log((impressions + 1) / (target_impressions + 1))) + abs(
            math.log((clicks + 1) / (target_clicks + 1))
        )
        candidates.append((distance, url))
    controls = [url for _distance, url in sorted(candidates)[:5]]
    if len(controls) < 3:
        return {"status": "insufficient_data", "reason": "fewer than three comparable unchanged control pages were found"}
    control_before = _history_values(indexed, set(controls), before_dates, "clicks")
    control_after = _history_values(indexed, set(controls), after_dates, "clicks")
    control_impressions = sum(_history_values(indexed, set(controls), before_dates, "impressions"))
    scale = target_impressions / control_impressions if control_impressions else 0.0
    if not scale:
        return {"status": "insufficient_data", "reason": "matched controls have no pre-change impressions"}
    observed = (sum(target_after) - sum(target_before)) - scale * (sum(control_after) - sum(control_before))
    seed = int(hashlib.sha256(str(change.get("id") or "").encode()).hexdigest()[:16], 16)
    draws = moving_block_did(
        target_before,
        target_after,
        control_before,
        control_after,
        control_scale=scale,
        seed=seed,
    )
    lower, upper = percentile(draws, 0.025), percentile(draws, 0.975)
    return {
        "status": "ok",
        "design": "matched observational difference-in-differences",
        "matched_on": "page type plus pre-change clicks and impressions",
        "control_urls": controls,
        "control_scale": round(scale, 6),
        "click_effect": {
            "estimate": round(observed, 4),
            "ci95": [round(lower, 4), round(upper, 4)],
            "direction": "increase" if lower > 0 else "decrease" if upper < 0 else "uncertain",
        },
        "causal_claim": False,
    }


def _request_dates(evidence: dict[str, Any]) -> list[str]:
    request = evidence.get("request") or {}
    start = date.fromisoformat(str(request.get("startDate") or ""))
    end = date.fromisoformat(str(request.get("endDate") or ""))
    return [(start + timedelta(days=offset)).isoformat() for offset in range((end - start).days + 1)]


def _history_values(
    indexed: dict[str, dict[str, dict[str, float]]],
    urls: set[str],
    dates: list[str],
    metric: str,
) -> list[float]:
    return [sum(float(indexed[url].get(day, {}).get(metric, 0)) for url in urls) for day in dates]


def _parse_day(value: str, field: str) -> date:
    try:
        return date.fromisoformat(value)
    except ValueError as exc:
        raise ValueError(f"{field} must be YYYY-MM-DD") from exc


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


def _write_private(path: Path, payload: dict[str, Any]) -> None:
    atomic_write_text(path, json.dumps(payload, ensure_ascii=False, indent=2) + "\n", mode=0o600)
