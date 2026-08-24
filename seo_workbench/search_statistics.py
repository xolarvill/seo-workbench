from __future__ import annotations

import math
from collections import defaultdict
from statistics import median
from typing import Any, Iterable

from seo_workbench.tech_audit import link_scope, normalize_url
from seo_workbench.statistics_methods import benjamini_hochberg


SCHEMA_VERSION = "search-statistics-v2"
RANK_BANDS = ("top_3", "positions_4_10", "positions_11_20", "positions_20_plus")


def build_search_statistics(
    previous_rows: list[Any],
    current_rows: list[Any],
    project_url: str,
) -> dict[str, Any]:
    previous = _cells(previous_rows, project_url)
    current = _cells(current_rows, project_url)
    urls = sorted({url for _query, url in previous.keys() | current.keys()})
    ctr_benchmark = _ctr_benchmarks(current, urls)
    pages = {
        url: {
            "click_change_decomposition": _decomposition(previous, current, url=url),
            "query_portfolio": _query_portfolio(previous, current, url),
            "ranking_opportunity": _ranking_opportunity(previous, current, url=url),
            "ctr_benchmark": ctr_benchmark["pages"].get(url, _empty_ctr_benchmark()),
        }
        for url in urls
    }
    return {
        "schema_version": SCHEMA_VERSION,
        "basis": "observed GSC query-page rows; hidden queries are not represented",
        "portfolio": {
            "click_change_decomposition": _decomposition(previous, current),
            "query_portfolio": _query_portfolio(previous, current),
            "ranking_opportunity": _ranking_opportunity(previous, current),
            "ctr_benchmark": ctr_benchmark["portfolio"],
        },
        "pages": pages,
    }


def ownership_metrics(owners: Iterable[dict[str, Any]]) -> dict[str, Any]:
    selected = [owner for owner in owners if float(owner.get("impressions") or 0) > 0]
    total = sum(float(owner["impressions"]) for owner in selected)
    if not selected or not total:
        return {"hhi": None, "primary_owner_share": None, "effective_owners": None}
    shares = [float(owner["impressions"]) / total for owner in selected]
    hhi = sum(share * share for share in shares)
    return {
        "hhi": round(hhi, 6),
        "primary_owner_share": round(max(shares), 6),
        "effective_owners": round(1 / hhi, 4),
    }


def commercial_value_statistics(items: list[dict[str, Any]], *, currency: str = "") -> dict[str, Any]:
    observed = []
    for item in items:
        current = ((item.get("metrics") or {}).get("current")) or {}
        ranking = ((item.get("statistics") or {}).get("ranking_opportunity")) or {}
        if "revenue" not in current:
            continue
        observed.append(
            {
                "item": item,
                "revenue": float(current["revenue"]),
                "revenue_weight": max(float(current["revenue"]), 0.0),
                "opportunity": float(ranking.get("positions_4_20_impressions") or 0),
            }
        )
    positive_revenue = [row["revenue_weight"] for row in observed if row["revenue_weight"] > 0]
    positive_opportunity = [row["opportunity"] for row in observed if row["opportunity"] > 0]
    total_revenue = sum(row["revenue_weight"] for row in observed)
    revenue_cut = median(positive_revenue) if positive_revenue else 0.0
    opportunity_cut = median(positive_opportunity) if positive_opportunity else 0.0
    for row in observed:
        value_tier = "high" if row["revenue_weight"] > 0 and row["revenue_weight"] >= revenue_cut else "low"
        opportunity_tier = "high" if row["opportunity"] > 0 and row["opportunity"] >= opportunity_cut else "low"
        quadrant = {
            ("high", "high"): "grow",
            ("high", "low"): "protect",
            ("low", "high"): "investigate",
            ("low", "low"): "maintain",
        }[(value_tier, opportunity_tier)]
        row["item"]["statistics"]["commercial_value"] = {
            "revenue": round(row["revenue"], 4),
            "currency": currency,
            "revenue_share": round(row["revenue_weight"] / total_revenue, 6) if total_revenue else None,
            "value_tier": value_tier,
            "search_opportunity_impressions": round(row["opportunity"], 4),
            "opportunity_tier": opportunity_tier,
            "quadrant": quadrant,
            "attribution": "all-channel product value; not SEO revenue attribution",
        }
    shares = [row["revenue_weight"] / total_revenue for row in observed if row["revenue_weight"] > 0] if total_revenue else []
    return {
        "observed_pages": len(observed),
        "currency": currency,
        "total_revenue": round(total_revenue, 4),
        "revenue_hhi": round(sum(share * share for share in shares), 6) if shares else None,
        "value_tier_cutoff": round(revenue_cut, 4) if observed else None,
        "opportunity_tier_cutoff": round(opportunity_cut, 4) if observed else None,
        "attribution": "all-channel product value; not SEO revenue attribution",
    }


def _cells(rows: list[Any], project_url: str) -> dict[tuple[str, str], dict[str, Any]]:
    grouped: dict[tuple[str, str], dict[str, Any]] = {}
    for row in rows:
        keys = row.get("keys") if isinstance(row, dict) else None
        if not isinstance(keys, list) or len(keys) < 2:
            continue
        query, url = str(keys[0]).strip(), normalize_url(str(keys[1]))
        if not query or not url or link_scope(url, project_url)[1] not in {"same_host", "subdomain"}:
            continue
        key = (query.casefold(), url)
        cell = grouped.setdefault(
            key,
            {"query": query, "url": url, "clicks": 0.0, "impressions": 0.0, "position_total": 0.0},
        )
        impressions = float(row.get("impressions") or 0)
        cell["clicks"] += float(row.get("clicks") or 0)
        cell["impressions"] += impressions
        cell["position_total"] += float(row.get("position") or 0) * impressions
    for cell in grouped.values():
        cell["position"] = cell["position_total"] / cell["impressions"] if cell["impressions"] else 0.0
    return grouped


def _selected(
    cells: dict[tuple[str, str], dict[str, Any]],
    *,
    url: str | None = None,
) -> dict[tuple[str, str], dict[str, Any]]:
    return {key: cell for key, cell in cells.items() if url is None or key[1] == url}


def _decomposition(
    previous: dict[tuple[str, str], dict[str, Any]],
    current: dict[tuple[str, str], dict[str, Any]],
    *,
    url: str | None = None,
) -> dict[str, Any]:
    before, after = _selected(previous, url=url), _selected(current, url=url)
    contributions = []
    for key in before.keys() | after.keys():
        old, new = before.get(key, {}), after.get(key, {})
        old_impressions, new_impressions = float(old.get("impressions") or 0), float(new.get("impressions") or 0)
        old_clicks, new_clicks = float(old.get("clicks") or 0), float(new.get("clicks") or 0)
        old_ctr = old_clicks / old_impressions if old_impressions else 0.0
        new_ctr = new_clicks / new_impressions if new_impressions else 0.0
        exposure_effect = (new_impressions - old_impressions) * (old_ctr + new_ctr) / 2
        ctr_effect = (new_ctr - old_ctr) * (old_impressions + new_impressions) / 2
        contributions.append(
            {
                "query": str((new or old).get("query", key[0])),
                "url": key[1],
                "click_change": round(new_clicks - old_clicks, 6),
                "exposure_effect": round(exposure_effect, 6),
                "ctr_effect": round(ctr_effect, 6),
            }
        )
    previous_clicks = sum(float(cell["clicks"]) for cell in before.values())
    current_clicks = sum(float(cell["clicks"]) for cell in after.values())
    exposure_effect = sum(float(row["exposure_effect"]) for row in contributions)
    ctr_effect = sum(float(row["ctr_effect"]) for row in contributions)
    contributions.sort(key=lambda row: (-abs(float(row["click_change"])), row["query"], row["url"]))
    return {
        "method": "symmetric two-factor decomposition of clicks = impressions × CTR",
        "previous_observed_clicks": round(previous_clicks, 6),
        "current_observed_clicks": round(current_clicks, 6),
        "observed_click_change": round(current_clicks - previous_clicks, 6),
        "exposure_effect": round(exposure_effect, 6),
        "ctr_effect": round(ctr_effect, 6),
        "reconciled": abs((exposure_effect + ctr_effect) - (current_clicks - previous_clicks)) < 1e-5,
        "top_drivers": contributions[:10],
    }


def _query_portfolio(
    previous: dict[tuple[str, str], dict[str, Any]],
    current: dict[tuple[str, str], dict[str, Any]],
    url: str | None = None,
) -> dict[str, Any]:
    before = _query_impressions(_selected(previous, url=url).values())
    after = _query_impressions(_selected(current, url=url).values())
    previous_queries, current_queries = set(before), set(after)
    return {
        "basis": "observed queries only",
        "previous": _concentration(before),
        "current": _concentration(after),
        "new_queries": len(current_queries - previous_queries),
        "stable_queries": len(current_queries & previous_queries),
        "lost_queries": len(previous_queries - current_queries),
        "new_query_impression_share": _share(after, current_queries - previous_queries),
        "retained_query_impression_share": _share(after, current_queries & previous_queries),
        "lost_query_impression_share": _share(before, previous_queries - current_queries),
    }


def _query_impressions(cells: Iterable[dict[str, Any]]) -> dict[str, float]:
    result: dict[str, float] = defaultdict(float)
    for cell in cells:
        result[str(cell["query"]).casefold()] += float(cell["impressions"])
    return dict(result)


def _concentration(values: dict[str, float]) -> dict[str, Any]:
    total = sum(values.values())
    if not total:
        return {
            "observed_query_count": 0,
            "effective_queries": None,
            "hhi": None,
            "top_1_impression_share": None,
            "top_5_impression_share": None,
            "top_10_impression_share": None,
        }
    shares = sorted((value / total for value in values.values()), reverse=True)
    hhi = sum(share * share for share in shares)
    return {
        "observed_query_count": len(shares),
        "effective_queries": round(1 / hhi, 4),
        "hhi": round(hhi, 6),
        "top_1_impression_share": round(sum(shares[:1]), 6),
        "top_5_impression_share": round(sum(shares[:5]), 6),
        "top_10_impression_share": round(sum(shares[:10]), 6),
    }


def _share(values: dict[str, float], selected: set[str]) -> float | None:
    total = sum(values.values())
    return round(sum(values.get(key, 0.0) for key in selected) / total, 6) if total else None


def _ranking_opportunity(
    previous: dict[tuple[str, str], dict[str, Any]],
    current: dict[tuple[str, str], dict[str, Any]],
    *,
    url: str | None = None,
) -> dict[str, Any]:
    before, after = _selected(previous, url=url), _selected(current, url=url)
    bands = {band: 0.0 for band in RANK_BANDS}
    for cell in after.values():
        bands[_rank_band(float(cell["position"]))] += float(cell["impressions"])
    total = sum(bands.values())
    transitions: dict[str, dict[str, float | int]] = {}
    for key in before.keys() & after.keys():
        label = f"{_rank_band(float(before[key]['position']))}->{_rank_band(float(after[key]['position']))}"
        transition = transitions.setdefault(label, {"cell_count": 0, "current_impressions": 0.0})
        transition["cell_count"] = int(transition["cell_count"]) + 1
        transition["current_impressions"] = round(
            float(transition["current_impressions"]) + float(after[key]["impressions"]), 4
        )
    return {
        "basis": "aggregated query-page average position",
        "current_impressions": {band: round(value, 4) for band, value in bands.items()},
        "current_impression_share": {
            band: round(value / total, 6) if total else None for band, value in bands.items()
        },
        "positions_4_20_impressions": round(bands["positions_4_10"] + bands["positions_11_20"], 4),
        "transitions": dict(sorted(transitions.items())),
    }


def _rank_band(position: float) -> str:
    if position <= 3:
        return "top_3"
    if position <= 10:
        return "positions_4_10"
    if position <= 20:
        return "positions_11_20"
    return "positions_20_plus"


def _ctr_benchmarks(
    cells: dict[tuple[str, str], dict[str, Any]],
    urls: list[str],
) -> dict[str, Any]:
    bands: dict[str, dict[str, float]] = {}
    page_bands: dict[str, dict[str, dict[str, float]]] = {}
    for cell in cells.values():
        band = _ctr_band(float(cell["position"]))
        clicks, impressions = float(cell["clicks"]), float(cell["impressions"])
        aggregate = bands.setdefault(band, {"clicks": 0.0, "impressions": 0.0})
        aggregate["clicks"] += clicks
        aggregate["impressions"] += impressions
        page = page_bands.setdefault(str(cell["url"]), {}).setdefault(
            band, {"clicks": 0.0, "impressions": 0.0}
        )
        page["clicks"] += clicks
        page["impressions"] += impressions
    total_clicks = sum(row["clicks"] for row in bands.values())
    total_impressions = sum(row["impressions"] for row in bands.values())
    global_ctr = total_clicks / total_impressions if total_impressions else 0.0
    prior_strength = 100.0
    alpha = max(global_ctr * prior_strength, 0.5)
    beta = max((1 - global_ctr) * prior_strength, 0.5)
    portfolio_bands = {
        band: {
            "clicks": round(values["clicks"], 4),
            "impressions": round(values["impressions"], 4),
            "posterior_ctr": round((values["clicks"] + alpha) / (values["impressions"] + alpha + beta), 6),
        }
        for band, values in sorted(bands.items())
    }
    pages = {}
    for url in urls:
        actual_clicks = sum(values["clicks"] for values in page_bands.get(url, {}).values())
        actual_impressions = sum(values["impressions"] for values in page_bands.get(url, {}).values())
        expected_clicks = 0.0
        variance = 0.0
        details = {}
        for band, values in page_bands.get(url, {}).items():
            others_clicks = max(bands[band]["clicks"] - values["clicks"], 0.0)
            others_impressions = max(bands[band]["impressions"] - values["impressions"], 0.0)
            expected_ctr = (others_clicks + alpha) / (others_impressions + alpha + beta)
            expected_clicks += values["impressions"] * expected_ctr
            variance += values["impressions"] * expected_ctr * (1 - expected_ctr)
            details[band] = {
                "impressions": round(values["impressions"], 4),
                "actual_ctr": round(values["clicks"] / values["impressions"], 6) if values["impressions"] else None,
                "leave_page_out_expected_ctr": round(expected_ctr, 6),
            }
        z_score = (actual_clicks - expected_clicks) / math.sqrt(variance) if variance > 0 else None
        p_value = math.erfc(abs(z_score) / math.sqrt(2)) if z_score is not None else None
        classification = "insufficient_data"
        if actual_impressions >= 100 and z_score is not None:
            classification = "below_expected" if z_score <= -1.96 else "above_expected" if z_score >= 1.96 else "within_expected"
        pages[url] = {
            "basis": "within-property leave-page-out CTR by coarse average-position band",
            "prior_strength_impressions": prior_strength,
            "actual_clicks": round(actual_clicks, 4),
            "actual_impressions": round(actual_impressions, 4),
            "expected_clicks": round(expected_clicks, 4),
            "click_residual": round(actual_clicks - expected_clicks, 4),
            "recoverable_clicks": round(max(expected_clicks - actual_clicks, 0.0), 4),
            "standardized_residual": round(z_score, 4) if z_score is not None else None,
            "p_value_unadjusted": round(p_value, 12) if p_value is not None else None,
            "classification": classification,
            "bands": dict(sorted(details.items())),
            "caveat": "Observed internal benchmark only; average position and query mix do not fully control SERP features or intent.",
        }
    tested = [(url, float(page["p_value_unadjusted"])) for url, page in pages.items() if page["p_value_unadjusted"] is not None and page["classification"] != "insufficient_data"]
    q_values = benjamini_hochberg(tested)
    for url, q_value in q_values.items():
        page = pages[url]
        page["unadjusted_classification"] = page["classification"]
        page["q_value"] = round(q_value, 6)
        page["fdr_significant"] = q_value <= 0.05
        if page["classification"] in {"below_expected", "above_expected"} and q_value > 0.05:
            page["classification"] = "not_significant_after_fdr"
    classifications: dict[str, int] = defaultdict(int)
    for page in pages.values():
        classifications[str(page["classification"])] += 1
    return {
        "portfolio": {
            "basis": "observed current GSC query-page rows",
            "global_ctr": round(global_ctr, 6) if total_impressions else None,
            "prior_strength_impressions": prior_strength,
            "bands": portfolio_bands,
            "recoverable_clicks": round(
                sum(
                    float(page["recoverable_clicks"])
                    for page in pages.values()
                    if page["classification"] == "below_expected"
                ),
                4,
            ),
            "recoverable_clicks_unadjusted": round(
                sum(float(page["recoverable_clicks"]) for page in pages.values()), 4
            ),
            "page_classifications": dict(sorted(classifications.items())),
            "multiple_testing": {
                "method": "Benjamini-Hochberg",
                "false_discovery_rate": 0.05,
                "hypotheses": len(tested),
                "significant_pages": sum(q_value <= 0.05 for q_value in q_values.values()),
            },
        },
        "pages": pages,
    }


def _ctr_band(position: float) -> str:
    if position < 1.5:
        return "position_1"
    if position < 2.5:
        return "position_2"
    if position < 3.5:
        return "position_3"
    if position < 5.5:
        return "positions_4_5"
    if position < 10.5:
        return "positions_6_10"
    if position < 20.5:
        return "positions_11_20"
    return "positions_20_plus"


def _empty_ctr_benchmark() -> dict[str, Any]:
    return {
        "basis": "within-property leave-page-out CTR by coarse average-position band",
        "actual_clicks": 0.0,
        "actual_impressions": 0.0,
        "expected_clicks": 0.0,
        "click_residual": 0.0,
        "recoverable_clicks": 0.0,
        "standardized_residual": None,
        "p_value_unadjusted": None,
        "classification": "insufficient_data",
        "bands": {},
    }
