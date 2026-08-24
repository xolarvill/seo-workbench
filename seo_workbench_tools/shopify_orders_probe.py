from __future__ import annotations

import json
import re
from datetime import date, datetime, time, timedelta, timezone
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from seo_workbench_tools.files import atomic_write_text
from seo_workbench_tools.http_transport import read_url


SCHEMA_VERSION = "1.0"
COLLECTOR_VERSION = "0.1.0"
SHOPIFY_API_VERSION = "2026-07"
MAX_RESPONSE_BYTES = 4 * 1024 * 1024
CREDENTIAL_RELATIVE_PATH = ".runtime/integrations/shopify.json"
SHOPIFY_DOMAIN = re.compile(r"^[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?\.myshopify\.com$")


class ShopifyOrderError(RuntimeError):
    """Shopify refused an order query."""


def _now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _timestamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")


def credential_path(project_dir: Path) -> Path:
    from seo_workbench import state

    return state.safe_project_path(project_dir, CREDENTIAL_RELATIVE_PATH)


def load_credentials(project_dir: Path) -> dict[str, Any]:
    path = credential_path(project_dir)
    if not path.is_file():
        raise RuntimeError("Shopify Admin API is not configured; connect it in the UI first")
    try:
        stored = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise RuntimeError(f"invalid Shopify credential file: {path}") from exc
    shop_domain = str(stored.get("shop_domain") or "").strip().lower()
    access_token = stored.get("access_token")
    if not SHOPIFY_DOMAIN.fullmatch(shop_domain) or not isinstance(access_token, str) or not access_token:
        raise RuntimeError("Shopify credential file is missing shop_domain or access_token")
    return {"shop_domain": shop_domain, "access_token": access_token}


def _graphql(
    project_dir: Path,
    query: str,
    variables: dict[str, Any],
    *,
    timeout: float = 30,
) -> dict[str, Any]:
    credentials = load_credentials(project_dir)
    request = Request(
        f"https://{credentials['shop_domain']}/admin/api/{SHOPIFY_API_VERSION}/graphql.json",
        data=json.dumps({"query": query, "variables": variables}).encode("utf-8"),
        headers={
            "Content-Type": "application/json",
            "User-Agent": "SEO-Workbench/0.2",
            "X-Shopify-Access-Token": credentials["access_token"],
        },
        method="POST",
    )
    try:
        raw = read_url(request, timeout=timeout, max_bytes=MAX_RESPONSE_BYTES)
    except HTTPError as exc:
        if exc.code in {401, 403}:
            raise ShopifyOrderError("Shopify rejected this Admin API access token") from exc
        raise ShopifyOrderError(f"Shopify Admin API returned HTTP {exc.code}") from exc
    except (OSError, URLError) as exc:
        raise ShopifyOrderError("Shopify Admin API could not be reached") from exc
    if len(raw) > MAX_RESPONSE_BYTES:
        raise ShopifyOrderError("Shopify Admin API response exceeded the safety limit")
    try:
        payload = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise ShopifyOrderError("Shopify Admin API returned invalid JSON") from exc
    if payload.get("errors"):
        raise ShopifyOrderError(f"Shopify Admin API error: {payload['errors'][0].get('message', 'unknown')}")
    return payload


_ORDER_QUERY = """query WorkbenchOrders($first: Int!, $cursor: String, $orderQuery: String!) {
  orders(first: $first, after: $cursor, sortKey: CREATED_AT, reverse: true, query: $orderQuery) {
    pageInfo { hasNextPage endCursor }
    edges { node {
      id
      createdAt
      displayFinancialStatus
      test
      lineItems(first: 250) {
        pageInfo { hasNextPage }
        edges { node {
        product { handle }
        priceAfterAllDiscountsBeforeTaxesSet { shopMoney { amount currencyCode } }
      } } }
    } }
  }
}"""

_SHOP_QUERY = """query WorkbenchShopTimezone { shop { ianaTimezone } }"""


def _shop_timezone(project_dir: Path, timeout: float = 30) -> str:
    name = str(((_graphql(project_dir, _SHOP_QUERY, {}, timeout=timeout).get("data") or {}).get("shop") or {}).get("ianaTimezone") or "")
    try:
        ZoneInfo(name)
    except (ValueError, ZoneInfoNotFoundError) as exc:
        raise ShopifyOrderError("Shopify returned an invalid IANA time zone") from exc
    return name


def _midnight_utc(day: date, time_zone: str) -> str:
    return datetime.combine(day, time.min, tzinfo=ZoneInfo(time_zone)).astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


def _iter_orders(
    project_dir: Path,
    start_date: str,
    end_date: str,
    timeout: float = 30,
    time_zone: str = "UTC",
) -> list[dict[str, Any]]:
    orders: list[dict[str, Any]] = []
    cursor: str | None = None
    start_inclusive = _midnight_utc(date.fromisoformat(start_date), time_zone)
    end_exclusive = _midnight_utc(date.fromisoformat(end_date) + timedelta(days=1), time_zone)
    while True:
        payload = _graphql(
            project_dir,
            _ORDER_QUERY,
            {
                "first": 100,
                "cursor": cursor,
                "orderQuery": f"created_at:>='{start_inclusive}' created_at:<'{end_exclusive}'",
            },
            timeout=timeout,
        )
        data = payload["data"]["orders"]
        for edge in data["edges"]:
            node = edge["node"]
            if node.get("lineItems", {}).get("pageInfo", {}).get("hasNextPage"):
                raise ShopifyOrderError("Shopify order has more than 250 line items; refusing partial revenue evidence")
            orders.append(
                {
                    "id": str(node["id"]).split("/")[-1],
                    "created_at": str(node["createdAt"]),
                    "status": str(node.get("displayFinancialStatus") or ""),
                    "test": bool(node.get("test")),
                    "line_items": [
                        {
                            "handle": _handle(item["node"].get("product")),
                            "revenue": _money(item["node"].get("priceAfterAllDiscountsBeforeTaxesSet")),
                            "currency": _currency(item["node"].get("priceAfterAllDiscountsBeforeTaxesSet")),
                        }
                        for item in node.get("lineItems", {}).get("edges", [])
                        if isinstance(item, dict) and isinstance(item.get("node"), dict)
                    ],
                }
            )
        if not data["pageInfo"]["hasNextPage"]:
            break
        cursor = data["pageInfo"]["endCursor"]
    return orders


def _handle(product: Any) -> str:
    if isinstance(product, dict):
        return str(product.get("handle") or "")
    return ""


def _money(total: Any) -> float:
    if isinstance(total, dict) and isinstance(total.get("shopMoney"), dict):
        try:
            return float(total["shopMoney"].get("amount") or 0)
        except (TypeError, ValueError):
            return 0.0
    return 0.0


def _currency(total: Any) -> str:
    if isinstance(total, dict) and isinstance(total.get("shopMoney"), dict):
        return str(total["shopMoney"].get("currencyCode") or "")
    return ""


def _date_windows(
    days: int,
    today: date | None = None,
    end_date: date | None = None,
) -> tuple[dict[str, str], dict[str, str]]:
    if not 1 <= days <= 90:
        raise ValueError("days must be between 1 and 90")
    end = end_date or (today or datetime.now(timezone.utc).date()) - timedelta(days=1)
    start = end - timedelta(days=days - 1)
    previous_end = start - timedelta(days=1)
    previous_start = previous_end - timedelta(days=days - 1)
    return (
        {"startDate": start.isoformat(), "endDate": end.isoformat()},
        {"startDate": previous_start.isoformat(), "endDate": previous_end.isoformat()},
    )


def collect_orders(
    project_dir: Path,
    *,
    days: int = 28,
    timeout: float = 30,
    today: date | None = None,
    end_date: date | None = None,
) -> dict[str, Any]:
    """Collect recent paid orders and aggregate revenue by product handle.

    Revenue is mapped to each product's canonical URL
    (https://<store>/products/<handle>). This is a product-level signal, not a
    channel attribution claim: orders are not attributed to a search source
    here. Key events and sessions come from GA4, which is collected
    separately and merged by the business-signals writer.
    """
    current, previous = _date_windows(days, today, end_date)
    shop_time_zone = _shop_timezone(project_dir, timeout)
    windows: dict[str, dict[str, Any]] = {}
    for name, window in (("current", current), ("previous", previous)):
        orders = _iter_orders(
            project_dir,
            window["startDate"],
            window["endDate"],
            timeout=timeout,
            time_zone=shop_time_zone,
        )
        by_handle: dict[str, dict[str, float]] = {}
        daily: dict[tuple[str, str], dict[str, float]] = {}
        currencies: set[str] = set()
        order_count = 0
        for order in orders:
            if order.get("test") or order["status"] not in {"PAID", "PARTIALLY_REFUNDED"}:
                continue
            try:
                order_day = datetime.fromisoformat(str(order["created_at"]).replace("Z", "+00:00")).astimezone(
                    ZoneInfo(shop_time_zone)
                ).date().isoformat()
            except (KeyError, ValueError) as exc:
                raise ShopifyOrderError("Shopify order has an invalid createdAt value") from exc
            order_count += 1
            order_handles: set[str] = set()
            for item in order["line_items"]:
                handle = item["handle"]
                if not handle:
                    continue
                revenue = float(item.get("revenue") or 0)
                by_handle.setdefault(handle, {"revenue": 0.0, "orders": 0.0})["revenue"] += revenue
                daily.setdefault((order_day, handle), {"revenue": 0.0, "orders": 0.0})["revenue"] += revenue
                order_handles.add(handle)
                if item.get("currency"):
                    currencies.add(str(item["currency"]))
            for handle in order_handles:
                by_handle[handle]["orders"] += 1
                daily[(order_day, handle)]["orders"] += 1
        windows[name] = {
            "request": {"startDate": window["startDate"], "endDate": window["endDate"], "source": "shopify_orders"},
            "orders": order_count,
            "currency": next(iter(currencies)) if len(currencies) == 1 else "",
            "rows": sorted(
                ({"handle": handle, **totals} for handle, totals in by_handle.items()),
                key=lambda row: -row["revenue"],
            ),
            "daily_rows": [
                {"date": day, "handle": handle, **totals}
                for (day, handle), totals in sorted(daily.items())
            ],
        }
    currencies = {window["currency"] for window in windows.values() if window.get("currency")}
    report = {
        "schema_version": SCHEMA_VERSION,
        "collector_version": COLLECTOR_VERSION,
        "generated_at": _now(),
        "collection_status": "ok",
        "source": "shopify_orders",
        "currency": next(iter(currencies)) if len(currencies) == 1 else "",
        "shop_time_zone": shop_time_zone,
        "revenue_basis": "Line-item price after all discounts, returns, and refunds; excludes tax and shipping.",
        "window_days": days,
        "windows": windows,
        "errors": [],
        "warnings": [],
        "privacy": "Aggregated order revenue by product handle only; no customer or order identifiers are stored.",
    }
    _artifact(report, project_dir / "audits/shopify-orders")
    return report


def _artifact(report: dict[str, Any], output_dir: Path) -> Path:
    output_dir.mkdir(parents=True, exist_ok=True, mode=0o700)
    path = output_dir / f"shopify-orders-{_timestamp()}.json"
    report["manifest"] = {"path": str(path), "latest_path": str(output_dir / "latest.json")}
    atomic_write_text(path, json.dumps(report, ensure_ascii=False, indent=2) + "\n", mode=0o600)
    atomic_write_text(output_dir / "latest.json", json.dumps(report, ensure_ascii=False, indent=2) + "\n", mode=0o600)
    return path
