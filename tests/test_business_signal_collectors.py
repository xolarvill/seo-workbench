import json
from datetime import date
from pathlib import Path

import pytest

from seo_workbench import state
from seo_workbench.business_signals_merge import collect_business_signals
from seo_workbench_tools import ga4_probe, shopify_orders_probe


def _project(path: Path) -> Path:
    state.init_state("shopify", "Example", "https://example.com", project_dir=path)
    return path


def test_shopify_orders_use_disjoint_complete_days_and_line_revenue(tmp_path: Path, monkeypatch) -> None:
    calls = []

    def orders(_project_dir: Path, start: str, end: str, timeout: float = 30, time_zone: str = "UTC"):
        calls.append((start, end, time_zone))
        return [
            {
                "created_at": f"{end}T12:00:00Z",
                "status": "PAID",
                "test": False,
                "line_items": [
                    {"handle": "desk", "revenue": 40, "currency": "USD"},
                    {"handle": "lamp", "revenue": 60, "currency": "USD"},
                ],
            }
        ]

    monkeypatch.setattr(shopify_orders_probe, "_iter_orders", orders)
    monkeypatch.setattr(shopify_orders_probe, "_shop_timezone", lambda *_args: "UTC")
    report = shopify_orders_probe.collect_orders(tmp_path, days=2, today=date(2026, 8, 13))

    assert calls == [
        ("2026-08-11", "2026-08-12", "UTC"),
        ("2026-08-09", "2026-08-10", "UTC"),
    ]
    assert sum(row["revenue"] for row in report["windows"]["current"]["rows"]) == 100
    assert {row["handle"]: row["orders"] for row in report["windows"]["current"]["rows"]} == {
        "desk": 1,
        "lamp": 1,
    }
    assert report["windows"]["current"]["daily_rows"][0] == {
        "date": "2026-08-12",
        "handle": "desk",
        "revenue": 40,
        "orders": 1,
    }
    assert report["currency"] == "USD"
    assert shopify_orders_probe._midnight_utc(date(2026, 8, 11), "America/Los_Angeles") == "2026-08-11T07:00:00Z"


def test_shopify_credentials_reject_non_shopify_domain(tmp_path: Path) -> None:
    path = tmp_path / ".runtime/integrations/shopify.json"
    path.parent.mkdir(parents=True)
    path.write_text(json.dumps({"shop_domain": "attacker.example", "access_token": "secret"}), encoding="utf-8")

    with pytest.raises(RuntimeError, match="missing shop_domain"):
        shopify_orders_probe.load_credentials(tmp_path)


def test_ga4_profile_rejects_symlinked_directory(tmp_path: Path) -> None:
    profiles = tmp_path / "google/profiles"
    profiles.mkdir(parents=True)
    (profiles / "ga4").symlink_to(tmp_path / "elsewhere")

    with pytest.raises(ValueError, match="symlinks"):
        ga4_probe.profile_dir("ga4", runtime_root=tmp_path / "google")


def test_ga4_binding_rejects_symlinked_directory(tmp_path: Path) -> None:
    (tmp_path / ".runtime").mkdir()
    (tmp_path / ".runtime/integrations").symlink_to(tmp_path / "elsewhere")

    with pytest.raises(ValueError, match="symlink"):
        ga4_probe.binding_path(tmp_path)


def test_ga4_artifact_preserves_query_windows(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setattr(ga4_probe, "load_binding", lambda _path: {"profile": "ga4", "property": "123"})
    monkeypatch.setattr(ga4_probe, "load_credentials", lambda _profile: object())
    metric_names: set[str] = set()
    event_filters: list[dict] = []

    def requester(method, _url, body, _credentials, _timeout):
        if method == "GET":
            return {"timeZone": "UTC"}
        metric_names.update(metric["name"] for metric in body.get("metrics") or [])
        if body.get("dimensions") == [{"name": "eventName"}]:
            event_filters.append(body["dimensionFilter"])
        return {"metricHeaders": [], "rows": []}

    report = ga4_probe.collect(
        tmp_path,
        tmp_path / "ga4",
        days=2,
        today=date(2026, 8, 13),
        end_date=date(2026, 8, 12),
        requester=requester,
    )

    assert report["windows"]["current"]["startDate"] == "2026-08-11"
    assert report["windows"]["current"]["endDate"] == "2026-08-12"
    assert report["windows"]["previous"]["endDate"] == "2026-08-10"
    assert {"itemViewEvents", "addToCarts", "checkouts", "ecommercePurchases", "purchaseRevenue"} <= metric_names
    assert {item["filter"]["fieldName"] for item in event_filters} == {"eventName"}


def test_ga4_defaults_to_two_complete_processing_days(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setattr(ga4_probe, "load_binding", lambda _path: {"profile": "ga4", "property": "123"})
    monkeypatch.setattr(ga4_probe, "load_credentials", lambda _profile: object())
    report = ga4_probe.collect(
        tmp_path,
        tmp_path / "ga4",
        days=2,
        today=date(2026, 8, 13),
        requester=lambda method, *_args: {"timeZone": "UTC"} if method == "GET" else {"metricHeaders": [], "rows": []},
    )

    assert report["windows"]["current"]["endDate"] == "2026-08-11"


def test_ga4_redacts_landing_queries_and_drops_private_paths() -> None:
    rows = ga4_probe._public_landing_rows(
        [
            {"keys": ["/products/desk?variant=secret"], "metrics": {"sessions": 2}},
            {"keys": ["/products/desk?utm_source=test"], "metrics": {"sessions": 3}},
            {"keys": ["/checkouts/cn/private-token/en-us"], "metrics": {"sessions": 1}},
            {"keys": ["/en-us/account/orders/123"], "metrics": {"sessions": 1}},
            {"keys": ["(not set)"], "metrics": {"sessions": 1}},
        ]
    )

    assert rows == [{"keys": ["/products/desk"], "metrics": {"sessions": 5}}]

    daily = ga4_probe._public_landing_rows(
        [{"keys": ["20260812", "/products/desk?variant=secret"], "metrics": {"sessions": 2}}],
        dated=True,
    )
    assert daily == [{"keys": ["2026-08-12", "/products/desk"], "metrics": {"sessions": 2}}]


def test_ga4_commerce_event_coverage_reports_only_observed_standard_events() -> None:
    coverage = ga4_probe._commerce_event_coverage(
        [
            {"keys": ["view_item"], "metrics": {"eventCount": 10}},
            {"keys": ["add_to_cart"], "metrics": {"eventCount": 2}},
            {"keys": ["purchase"], "metrics": {"eventCount": 0}},
        ]
    )

    assert coverage == {
        "status": "partial",
        "scope": "all_channels",
        "observed_events": ["add_to_cart", "view_item"],
        "missing_events": ["begin_checkout", "purchase"],
    }


def test_ga4_report_rows_paginates_without_sampling() -> None:
    offsets: list[int] = []

    def requester(_method, _url, body, _credentials, _timeout):
        offsets.append(body["offset"])
        offset = int(body["offset"])
        batch_size = 10000 if offset == 0 else 2
        return {
            "rowCount": 10002,
            "metricHeaders": [{"name": "sessions"}],
            "rows": [
                {
                    "dimensionValues": [{"value": f"/page-{offset + index}"}],
                    "metricValues": [{"value": "1"}],
                }
                for index in range(batch_size)
            ],
        }

    rows = ga4_probe._report_rows("123", object(), {}, 30, requester)

    assert offsets == [0, 10000]
    assert len(rows) == 10002


def test_business_merge_keeps_homepage_and_requires_comparable_windows(tmp_path: Path) -> None:
    project = _project(tmp_path / "project")
    ga4 = {
        "collection_status": "ok",
        "property_time_zone": "UTC",
        "windows": {
            name: {
                "startDate": start,
                "endDate": end,
                "landing_page_organic": [
                    {"keys": ["/"], "metrics": {"sessions": 10, "engagedSessions": 8, "keyEvents": 1}},
                    {
                        "keys": ["/products/desk?variant=1"],
                        "metrics": {
                            "sessions": 5,
                            "engagedSessions": 4,
                            "keyEvents": 2,
                            "itemViewEvents": 5,
                            "addToCarts": 2,
                            "checkouts": 1,
                            "ecommercePurchases": 1,
                            "purchaseRevenue": 80,
                        },
                    },
                    {"keys": ["/checkouts/cn/private-token"], "metrics": {"sessions": 1, "keyEvents": 1}},
                ],
                "landing_page_organic_daily": [
                    {
                        "keys": [end, "/products/desk?variant=1"],
                        "metrics": {
                            "sessions": 5,
                            "engagedSessions": 4,
                            "keyEvents": 2,
                            "itemViewEvents": 5,
                            "addToCarts": 2,
                            "checkouts": 1,
                            "ecommercePurchases": 1,
                            "purchaseRevenue": 80,
                        },
                    }
                ],
                "commerce_event_coverage": {
                    "status": "complete",
                    "observed_events": ["view_item", "add_to_cart", "begin_checkout", "purchase"],
                    "missing_events": [],
                },
            }
            for name, start, end in (
                ("previous", "2026-08-09", "2026-08-10"),
                ("current", "2026-08-11", "2026-08-12"),
            )
        },
    }
    shopify = {
        "collection_status": "ok",
        "currency": "USD",
        "shop_time_zone": "UTC",
        "windows": {
            name: {
                "request": {"startDate": start, "endDate": end},
                "rows": [{"handle": "desk", "revenue": 100, "orders": 2}],
                "daily_rows": [{"date": end, "handle": "desk", "revenue": 100, "orders": 2}],
            }
            for name, start, end in (
                ("previous", "2026-08-09", "2026-08-10"),
                ("current", "2026-08-11", "2026-08-12"),
            )
        },
    }
    ga4_path = tmp_path / "ga4.json"
    shopify_path = tmp_path / "shopify.json"
    ga4_path.write_text(json.dumps(ga4), encoding="utf-8")
    shopify_path.write_text(json.dumps(shopify), encoding="utf-8")

    report, _ = collect_business_signals(project, ga4_path=ga4_path, shopify_path=shopify_path)
    rows = {row["url"]: row for row in report["windows"]["current"]["rows"]}
    assert rows["https://example.com/"] == {
        "url": "https://example.com/",
        "organic_sessions": 10,
        "engaged_sessions": 8,
        "key_events": 1,
    }
    assert rows["https://example.com/products/desk"] == {
        "url": "https://example.com/products/desk",
        "organic_sessions": 5,
        "engaged_sessions": 4,
        "key_events": 2,
        "organic_product_views": 5,
        "organic_add_to_carts": 2,
        "organic_checkouts": 1,
        "organic_purchases": 1,
        "organic_revenue": 80,
        "revenue": 100,
        "orders": 2,
    }
    assert report["schema_version"] == "business-signals-v2"
    assert report["windows"]["current"]["daily_rows"] == [
        {
            "date": "2026-08-12",
            "url": "https://example.com/products/desk",
            "organic_sessions": 5,
            "engaged_sessions": 4,
            "key_events": 2,
            "organic_product_views": 5,
            "organic_add_to_carts": 2,
            "organic_checkouts": 1,
            "organic_purchases": 1,
            "organic_revenue": 80,
            "revenue": 100,
            "orders": 2,
        }
    ]
    assert report["currency"] == "USD"
    assert report["windows"]["current"]["commerce_tracking"]["status"] == "complete"
    assert report["attribution"]["shopify"].startswith("All-channel")

    shopify["windows"]["current"]["request"]["endDate"] = "2026-08-13"
    shopify_path.write_text(json.dumps(shopify), encoding="utf-8")
    with pytest.raises(ValueError, match="not comparable"):
        collect_business_signals(project, ga4_path=ga4_path, shopify_path=shopify_path)
