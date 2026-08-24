"""Merge GA4 and Shopify evidence into the business-signals schema.

GA4 supplies page-level organic sessions and key events; Shopify supplies
product-level revenue mapped to product URLs. This module produces the same
`business-signals-v2` artifact that `business-signals import` writes, so the
rest of the Workbench (SEO outcomes, content portfolio, Pages) consumes it
without changes.
"""

from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit, urlunsplit

from seo_workbench import state
from seo_workbench.tech_audit import link_scope, normalize_url
from seo_workbench_tools.files import atomic_write_text

from seo_workbench.business_signals import WINDOWS


SCHEMA_VERSION = "business-signals-v2"
GA4_METRICS = {
    "organic_sessions": "sessions",
    "engaged_sessions": "engagedSessions",
    "key_events": "keyEvents",
    "organic_product_views": "itemViewEvents",
    "organic_add_to_carts": "addToCarts",
    "organic_checkouts": "checkouts",
    "organic_purchases": "ecommercePurchases",
    "organic_revenue": "purchaseRevenue",
}
PRIVATE_LANDING_PATH = re.compile(
    r"^/(?:[a-z]{2}(?:-[a-z]{2})?/)?(?:admin|account|cart|checkouts?|orders?|payments?)(?:/|$)",
    re.IGNORECASE,
)


def _now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _timestamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")


def _read_optional(path: Path) -> dict[str, Any] | None:
    if not path.is_file() or path.is_symlink():
        return None
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    return payload if isinstance(payload, dict) else None


def _project_origin(project_dir: Path) -> str:
    data = state.load_state(project_dir)
    url = str((data.get("project") or {}).get("url", ""))
    if not url.startswith(("http://", "https://")):
        raise ValueError("project.url must be an absolute HTTP(S) URL")
    parts = urlsplit(url)
    return urlunsplit((parts.scheme, parts.netloc, "", "", ""))


def _page_url(project_dir: Path, landing_path: str) -> str | None:
    path = urlsplit(landing_path).path
    if not landing_path or landing_path == "(not set)" or PRIVATE_LANDING_PATH.search(path):
        return None
    origin = _project_origin(project_dir)
    candidate = landing_path if landing_path.startswith(("http://", "https://")) else f"{origin}{landing_path}"
    normalized = normalize_url(candidate)
    if not normalized or link_scope(normalized, origin)[1] not in {"same_host", "subdomain"}:
        return None
    parts = urlsplit(normalized)
    return urlunsplit((parts.scheme, parts.netloc, parts.path, "", ""))


def _first_key(row: dict[str, Any]) -> str:
    keys = row.get("keys") or []
    return str(keys[0]) if keys else ""


def collect_business_signals(
    project_dir: Path,
    *,
    ga4_path: Path | None = None,
    shopify_path: Path | None = None,
) -> tuple[dict[str, Any], Path]:
    """Merge audits/ga4/latest.json and audits/shopify-orders/latest.json into
    the business-signals schema, keyed by URL.

    Missing inputs raise FileNotFoundError; a GA4 or Shopify source with no
    usable rows is recorded as a warning rather than a failure.
    """
    ga4_source = ga4_path or state.safe_project_path(project_dir, "audits/ga4/latest.json")
    shopify_source = shopify_path or state.safe_project_path(project_dir, "audits/shopify-orders/latest.json")
    if not ga4_source.is_file():
        raise FileNotFoundError(f"GA4 evidence not found: {ga4_source}; run ga4 collect first")
    if not shopify_source.is_file():
        raise FileNotFoundError(f"Shopify order evidence not found: {shopify_source}; run shopify-orders collect first")

    ga4 = _read_optional(ga4_source)
    shopify = _read_optional(shopify_source)
    if ga4 is None:
        raise ValueError("GA4 evidence artifact is not readable JSON")
    if shopify is None:
        raise ValueError("Shopify order evidence artifact is not readable JSON")
    if ga4.get("collection_status") != "ok" or shopify.get("collection_status") != "ok":
        raise ValueError("GA4 and Shopify evidence must both have collection_status=ok")
    ga4_time_zone = str(ga4.get("property_time_zone") or "")
    shopify_time_zone = str(shopify.get("shop_time_zone") or "")
    if ga4_time_zone and shopify_time_zone and ga4_time_zone != shopify_time_zone:
        raise ValueError("GA4 property and Shopify shop time zones are not comparable")

    windows: dict[str, dict[str, Any]] = {}
    warnings: list[dict[str, str]] = []
    if not ga4_time_zone or not shopify_time_zone:
        warnings.append(
            {
                "scope": "window",
                "code": "time_zone_not_verified",
                "message": "GA4 or Shopify time zone metadata is missing; date boundaries could not be verified.",
            }
        )
    for name in WINDOWS:
        ga4_window = _window(ga4, name)
        shopify_window = _window(shopify, name)
        if not ga4_window or not shopify_window:
            raise ValueError(f"GA4 and Shopify evidence must both include the {name} window")
        ga4_dates = (ga4_window.get("startDate"), ga4_window.get("endDate"))
        shopify_request = shopify_window.get("request") or {}
        shopify_dates = (shopify_request.get("startDate"), shopify_request.get("endDate"))
        if ga4_dates != shopify_dates or not all(ga4_dates):
            raise ValueError(f"GA4 and Shopify {name} windows are not comparable")
        rows: dict[str, dict[str, float]] = {}
        daily_rows: dict[tuple[str, str], dict[str, float]] = {}
        organic_rows = ga4_window.get("landing_page_organic") or []
        if not isinstance(organic_rows, list):
            organic_rows = []
        if organic_rows:
            _merge_ga4_rows(project_dir, organic_rows, rows)
        else:
            warnings.append({"scope": "ga4", "window": name, "code": "no_rows", "message": "no GA4 organic landing rows for this window"})
        _merge_shopify_rows(project_dir, shopify_window.get("rows") or [], rows)
        _merge_daily_ga4_rows(project_dir, ga4_window.get("landing_page_organic_daily") or [], daily_rows)
        _merge_daily_shopify_rows(project_dir, shopify_window.get("daily_rows") or [], daily_rows)
        request = {
            "startDate": ga4_dates[0],
            "endDate": ga4_dates[1],
            "dimensions": ["page"],
        }
        windows[name] = {
            "request": request,
            "rows": [
                {"url": url, **{metric: round(value, 4) for metric, value in totals.items()}}
                for url, totals in sorted(rows.items())
            ],
            "daily_rows": [
                {"date": day, "url": url, **{metric: round(value, 4) for metric, value in totals.items()}}
                for (day, url), totals in sorted(daily_rows.items())
            ],
            "commerce_tracking": _commerce_tracking(
                ga4_window.get("commerce_event_coverage"),
                shopify_window.get("rows") or [],
            ),
        }

    report = {
        "schema_version": SCHEMA_VERSION,
        "collection_status": "ok",
        "generated_at": _now(),
        "metrics": [*GA4_METRICS, "revenue", "orders"],
        "currency": shopify.get("currency", ""),
        "time_zone": ga4_time_zone or shopify_time_zone,
        "windows": windows,
        "source": {
            "ga4": str(ga4_source),
            "shopify": str(shopify_source),
            "format": "merged",
        },
        "attribution": {
            "organic_commerce": "GA4 Organic Search landing-page-associated session aggregate; not a user path or causal attribution.",
            "shopify": "All-channel product value; not SEO revenue attribution.",
        },
        "warnings": warnings,
        "privacy": "Aggregated page-level data only; no user, event, or order identifiers are stored.",
    }
    output_dir = state.safe_project_path(project_dir, "audits/business-signals")
    output_dir.mkdir(parents=True, exist_ok=True, mode=0o700)
    path = output_dir / f"business-signals-{_timestamp()}.json"
    payload = json.dumps(report, ensure_ascii=False, indent=2) + "\n"
    atomic_write_text(path, payload, mode=0o600)
    atomic_write_text(output_dir / "latest.json", payload, mode=0o600)
    return report, path


def _window(report: dict[str, Any], name: str) -> dict[str, Any]:
    return (report.get("windows") or {}).get(name) or {}


def _merge_ga4_rows(project_dir: Path, rows_source: list[dict[str, Any]], rows: dict[str, dict[str, float]]) -> None:
    for row in rows_source:
        url = _page_url(project_dir, _first_key(row))
        if not url:
            continue
        entry = rows.setdefault(url, {})
        source_metrics = row.get("metrics") or {}
        for metric, source_name in GA4_METRICS.items():
            if source_name in source_metrics:
                entry[metric] = entry.get(metric, 0.0) + float(source_metrics.get(source_name) or 0)


def _merge_shopify_rows(project_dir: Path, rows_source: list[dict[str, Any]], rows: dict[str, dict[str, float]]) -> None:
    origin = _project_origin(project_dir)
    for row in rows_source:
        handle = str(row.get("handle") or "")
        if not handle:
            continue
        url = f"{origin}/products/{handle}"
        entry = rows.setdefault(url, {})
        entry["revenue"] = entry.get("revenue", 0.0) + float(row.get("revenue") or 0)
        entry["orders"] = entry.get("orders", 0.0) + float(row.get("orders") or 0)


def _merge_daily_ga4_rows(
    project_dir: Path,
    rows_source: list[dict[str, Any]],
    rows: dict[tuple[str, str], dict[str, float]],
) -> None:
    for row in rows_source:
        keys = row.get("keys") or []
        url = _page_url(project_dir, str(keys[1])) if len(keys) > 1 else None
        if not url:
            continue
        entry = rows.setdefault((str(keys[0]), url), {})
        metrics = row.get("metrics") or {}
        for metric, source_name in GA4_METRICS.items():
            if source_name in metrics:
                entry[metric] = entry.get(metric, 0.0) + float(metrics.get(source_name) or 0)


def _merge_daily_shopify_rows(
    project_dir: Path,
    rows_source: list[dict[str, Any]],
    rows: dict[tuple[str, str], dict[str, float]],
) -> None:
    origin = _project_origin(project_dir)
    for row in rows_source:
        day, handle = str(row.get("date") or ""), str(row.get("handle") or "")
        if not day or not handle:
            continue
        entry = rows.setdefault((day, f"{origin}/products/{handle}"), {})
        entry["revenue"] = entry.get("revenue", 0.0) + float(row.get("revenue") or 0)
        entry["orders"] = entry.get("orders", 0.0) + float(row.get("orders") or 0)


def _commerce_tracking(coverage: Any, shopify_rows: list[dict[str, Any]]) -> dict[str, Any]:
    source = coverage if isinstance(coverage, dict) else {}
    observed = [str(event) for event in source.get("observed_events") or []]
    missing = [str(event) for event in source.get("missing_events") or []]
    shopify_orders = sum(float(row.get("orders") or 0) for row in shopify_rows)
    status = "complete" if not missing and observed else "needs_tracking" if shopify_orders > 0 and "purchase" in missing else "partial"
    return {"status": status, "scope": "all_channels", "observed_events": observed, "missing_events": missing}
