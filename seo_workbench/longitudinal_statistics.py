from __future__ import annotations

import hashlib
import math
from datetime import date, timedelta
from statistics import median
from typing import Any

from seo_workbench.statistics_methods import moving_block_differences, percentile


BOOTSTRAP_SAMPLES = 500
BLOCK_DAYS = 7


def build_longitudinal_statistics(
    gsc_rows: list[dict[str, Any]],
    business_rows: list[dict[str, Any]],
    coverage: dict[str, list[str]],
    *,
    previous: dict[str, Any],
    current: dict[str, Any],
    include_business: bool,
) -> dict[str, Any]:
    previous_dates = _window_dates(previous)
    current_dates = _window_dates(current)
    gsc = _index(gsc_rows, ("clicks", "impressions"))
    business = _index(business_rows, ("organic_sessions", "engaged_sessions", "key_events"))
    urls = sorted((set(gsc) | set(business)) - {"*"})
    pages = {}
    for url in urls:
        statistics = {
            "search_change_confidence": _search_confidence(
                gsc, coverage.get("gsc", []), previous_dates, current_dates, url
            ),
            "search_trend": _trend(gsc, coverage.get("gsc", []), url),
        }
        if include_business:
            statistics["organic_engagement"] = _engagement(
                business, coverage.get("business", []), previous_dates, current_dates, url
            )
            statistics["cross_source_consistency"] = _cross_source(
                gsc,
                business,
                coverage,
                previous_dates,
                current_dates,
                url,
            )
        pages[url] = statistics
    portfolio = {
        "search_change_confidence": _search_confidence(
            gsc, coverage.get("gsc", []), previous_dates, current_dates, "*"
        ),
        "search_trend": _trend(gsc, coverage.get("gsc", []), "*"),
    }
    if include_business:
        portfolio["organic_engagement"] = _engagement(
            business, coverage.get("business", []), previous_dates, current_dates, "*"
        )
        portfolio["cross_source_consistency"] = _cross_source(
            gsc,
            business,
            coverage,
            previous_dates,
            current_dates,
            "*",
        )
    return {
        "schema_version": "longitudinal-statistics-v1",
        "basis": "private aggregate date-by-page history; uncovered dates are never synthesized as zero",
        "portfolio": portfolio,
        "pages": pages,
    }


def _index(rows: list[dict[str, Any]], metrics: tuple[str, ...]) -> dict[str, dict[str, dict[str, float]]]:
    result: dict[str, dict[str, dict[str, float]]] = {"*": {}}
    for row in rows:
        url, day = str(row.get("url") or ""), str(row.get("date") or "")
        if not url or not day:
            continue
        selected = {metric: float(row[metric]) for metric in metrics if metric in row}
        if not selected:
            continue
        result.setdefault(url, {})[day] = selected
        aggregate = result["*"].setdefault(day, {})
        for metric, value in selected.items():
            aggregate[metric] = aggregate.get(metric, 0.0) + value
    return result


def _search_confidence(
    indexed: dict[str, dict[str, dict[str, float]]],
    coverage: list[str],
    previous_dates: list[str],
    current_dates: list[str],
    url: str,
) -> dict[str, Any]:
    if url not in indexed:
        return _insufficient("page was never observed in GSC date-page history")
    covered = set(coverage)
    before_dates = [day for day in previous_dates if day in covered]
    after_dates = [day for day in current_dates if day in covered]
    if len(before_dates) != len(previous_dates) or len(after_dates) != len(current_dates):
        return _insufficient("comparison windows are not fully covered by daily GSC history")
    before_clicks = _values(indexed[url], before_dates, "clicks")
    after_clicks = _values(indexed[url], after_dates, "clicks")
    before_impressions = _values(indexed[url], before_dates, "impressions")
    after_impressions = _values(indexed[url], after_dates, "impressions")
    total_clicks = sum(before_clicks) + sum(after_clicks)
    total_impressions = sum(before_impressions) + sum(after_impressions)
    if total_impressions < 100:
        return {
            **_insufficient("at least 100 observed impressions across both windows are required"),
            "evidence_grade": "insufficient",
            "covered_days": {"previous": len(before_dates), "current": len(after_dates)},
            "observed_impressions": round(total_impressions, 4),
        }
    grade = "strong" if total_clicks >= 30 and total_impressions >= 1000 else "moderate" if total_impressions >= 300 else "weak"
    seed = int(hashlib.sha256(url.encode()).hexdigest()[:16], 16)
    draws = moving_block_differences(
        before_clicks,
        after_clicks,
        seed=seed,
        samples=BOOTSTRAP_SAMPLES,
        block_days=BLOCK_DAYS,
    )
    previous_clicks, current_clicks = sum(before_clicks), sum(after_clicks)
    previous_impressions, current_impressions = sum(before_impressions), sum(after_impressions)
    lower, upper = percentile(draws, 0.025), percentile(draws, 0.975)
    return {
        "status": "ok",
        "evidence_grade": grade,
        "covered_days": {"previous": len(before_dates), "current": len(after_dates)},
        "method": f"deterministic moving-block bootstrap; {BLOCK_DAYS}-day blocks; {BOOTSTRAP_SAMPLES} samples",
        "click_change": {
            "previous": round(previous_clicks, 4),
            "current": round(current_clicks, 4),
            "observed": round(current_clicks - previous_clicks, 4),
            "ci95": [round(lower, 4), round(upper, 4)],
            "probability_increase": round(sum(draw > 0 for draw in draws) / len(draws), 4),
            "direction": "increase" if lower > 0 else "decrease" if upper < 0 else "uncertain",
        },
        "ctr": {
            "previous": _rate(previous_clicks, previous_impressions),
            "current": _rate(current_clicks, current_impressions),
        },
        "caveat": "Uncertainty is descriptive and reflects observed daily variation, not causal attribution.",
    }


def _trend(
    indexed: dict[str, dict[str, dict[str, float]]],
    coverage: list[str],
    url: str,
) -> dict[str, Any]:
    if url not in indexed or len(coverage) < 56:
        return _insufficient("eight weeks of daily GSC coverage are required")
    latest = max(date.fromisoformat(day) for day in coverage)
    dates = [(latest - timedelta(days=55 - offset)).isoformat() for offset in range(56)]
    covered = set(coverage)
    if any(day not in covered for day in dates):
        return _insufficient("the latest eight weeks are not continuously covered")
    clicks = _values(indexed[url], dates, "clicks")
    impressions = _values(indexed[url], dates, "impressions")
    weekly_clicks = [sum(clicks[index : index + 7]) for index in range(0, 56, 7)]
    weekly_impressions = [sum(impressions[index : index + 7]) for index in range(0, 56, 7)]
    if sum(value > 0 for value in weekly_impressions) < 6:
        return _insufficient("the page has impressions in fewer than six of the latest eight weeks")
    slope = _theil_sen(weekly_clicks)
    baseline_slope = _theil_sen(weekly_clicks[:-1])
    intercept = median(value - baseline_slope * index for index, value in enumerate(weekly_clicks[:-1]))
    residuals = [
        value - (intercept + baseline_slope * index) for index, value in enumerate(weekly_clicks[:-1])
    ]
    mad = median(abs(value - median(residuals)) for value in residuals)
    latest_expected = intercept + baseline_slope * 7
    latest_residual = weekly_clicks[-1] - latest_expected
    anomaly_score = latest_residual / (1.4826 * mad) if mad else (math.inf if latest_residual else 0.0)
    normalized_slope = slope / max(median(weekly_clicks), 1.0)
    return {
        "status": "ok",
        "method": "Theil-Sen weekly slope with median-absolute-deviation anomaly score",
        "weeks": 8,
        "weekly_clicks": [round(value, 4) for value in weekly_clicks],
        "click_slope_per_week": round(slope, 4),
        "normalized_slope": round(normalized_slope, 4),
        "direction": "up" if normalized_slope > 0.1 else "down" if normalized_slope < -0.1 else "stable",
        "latest_expected_clicks": round(latest_expected, 4),
        "latest_anomaly_score": round(anomaly_score, 4) if math.isfinite(anomaly_score) else None,
        "latest_anomaly": abs(anomaly_score) >= 3,
    }


def _engagement(
    indexed: dict[str, dict[str, dict[str, float]]],
    coverage: list[str],
    previous_dates: list[str],
    current_dates: list[str],
    url: str,
) -> dict[str, Any]:
    if url not in indexed or not any("organic_sessions" in row for row in indexed[url].values()):
        return _insufficient("organic landing sessions were not observed for this page")
    covered = set(coverage)
    if any(day not in covered for day in previous_dates + current_dates):
        return _insufficient("comparison windows are not fully covered by daily business history")
    windows = {}
    for name, dates in (("previous", previous_dates), ("current", current_dates)):
        sessions = sum(_values(indexed[url], dates, "organic_sessions"))
        engaged = sum(_values(indexed[url], dates, "engaged_sessions"))
        key_events = sum(_values(indexed[url], dates, "key_events"))
        windows[name] = {
            "organic_sessions": round(sessions, 4),
            "engaged_sessions": round(engaged, 4),
            "engagement_rate": _rate(engaged, sessions),
            "key_events_per_session": round(key_events / sessions, 6) if sessions else None,
        }
    sessions_total = windows["previous"]["organic_sessions"] + windows["current"]["organic_sessions"]
    return {
        "status": "ok",
        "evidence_grade": "strong" if sessions_total >= 500 else "moderate" if sessions_total >= 100 else "weak",
        "previous": windows["previous"],
        "current": windows["current"],
        "engagement_rate_change": (
            round(windows["current"]["engagement_rate"]["estimate"] - windows["previous"]["engagement_rate"]["estimate"], 6)
            if windows["current"]["engagement_rate"] and windows["previous"]["engagement_rate"]
            else None
        ),
        "interpretation": "GA4 landing-page engagement; key events are configured events, not purchase attribution.",
    }


def _cross_source(
    gsc: dict[str, dict[str, dict[str, float]]],
    business: dict[str, dict[str, dict[str, float]]],
    coverage: dict[str, list[str]],
    previous_dates: list[str],
    current_dates: list[str],
    url: str,
) -> dict[str, Any]:
    if url not in gsc or url not in business or not any("organic_sessions" in row for row in business[url].values()):
        return _insufficient("both GSC clicks and GA4 organic sessions are required")
    covered = set(coverage.get("gsc", [])) & set(coverage.get("business", []))
    if any(day not in covered for day in previous_dates + current_dates):
        return _insufficient("aligned GSC and business daily coverage is incomplete")

    def ratios(dates: list[str]) -> list[float]:
        values = []
        for day in dates:
            clicks = float(gsc[url].get(day, {}).get("clicks", 0))
            sessions = float(business[url].get(day, {}).get("organic_sessions", 0))
            if clicks + sessions > 0:
                values.append(math.log((sessions + 0.5) / (clicks + 0.5)))
        return values

    before, after = ratios(previous_dates), ratios(current_dates)
    if len(before) < 14 or len(after) < 14:
        return _insufficient("at least 14 active aligned days per window are required")
    previous_median, current_median = median(before), median(after)
    mad = median(abs(value - previous_median) for value in before)
    delta = current_median - previous_median
    robust_z = abs(delta) / (1.4826 * mad) if mad else (math.inf if delta else 0.0)
    factor = math.exp(delta)
    possible_break = robust_z >= 3 and abs(math.log(factor)) >= math.log(1.2)
    return {
        "status": "possible_measurement_break" if possible_break else "stable",
        "method": "median log(GA4 organic sessions / GSC clicks) with previous-window MAD",
        "active_days": {"previous": len(before), "current": len(after)},
        "previous_sessions_per_click": round(math.exp(previous_median), 4),
        "current_sessions_per_click": round(math.exp(current_median), 4),
        "ratio_change_factor": round(factor, 4),
        "robust_shift_score": round(robust_z, 4) if math.isfinite(robust_z) else None,
        "interpretation": "Tracking consistency diagnostic only; clicks and sessions are different units.",
    }


def _values(rows: dict[str, dict[str, float]], dates: list[str], metric: str) -> list[float]:
    return [float(rows.get(day, {}).get(metric, 0)) for day in dates]


def _rate(successes: float, total: float) -> dict[str, Any] | None:
    if total <= 0 or successes < 0 or successes > total:
        return None
    estimate = successes / total
    z = 1.96
    denominator = 1 + z * z / total
    center = (estimate + z * z / (2 * total)) / denominator
    margin = z * math.sqrt(estimate * (1 - estimate) / total + z * z / (4 * total * total)) / denominator
    return {"estimate": round(estimate, 6), "ci95": [round(max(0.0, center - margin), 6), round(min(1.0, center + margin), 6)]}


def _theil_sen(values: list[float]) -> float:
    return median(
        (right - left) / (right_index - left_index)
        for left_index, left in enumerate(values)
        for right_index, right in enumerate(values)
        if right_index > left_index
    )


def _window_dates(window: dict[str, Any]) -> list[str]:
    request = window.get("request") or {}
    start = date.fromisoformat(str(request.get("startDate") or ""))
    end = date.fromisoformat(str(request.get("endDate") or ""))
    return [(start + timedelta(days=offset)).isoformat() for offset in range((end - start).days + 1)]


def _insufficient(reason: str) -> dict[str, Any]:
    return {"status": "insufficient_data", "reason": reason}
