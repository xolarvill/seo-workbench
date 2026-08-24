from seo_workbench.search_statistics import (
    build_search_statistics,
    commercial_value_statistics,
    ownership_metrics,
)


URL = "https://example.com/products/desk"
OTHER = "https://example.com/products/lamp"


def _row(query: str, clicks: float, impressions: float, position: float) -> dict:
    return {
        "keys": [query, URL],
        "clicks": clicks,
        "impressions": impressions,
        "position": position,
    }


def test_search_statistics_explains_observed_click_change_and_query_mix() -> None:
    report = build_search_statistics(
        [_row("desk", 10, 100, 5)],
        [_row("desk", 10, 200, 7), _row("standing desk", 5, 100, 12)],
        "https://example.com",
    )

    page = report["pages"][URL]
    decomposition = page["click_change_decomposition"]
    assert decomposition["observed_click_change"] == 5
    assert decomposition["exposure_effect"] == 10
    assert decomposition["ctr_effect"] == -5
    assert decomposition["reconciled"] is True
    assert page["query_portfolio"]["new_queries"] == 1
    assert page["query_portfolio"]["stable_queries"] == 1
    assert page["query_portfolio"]["current"]["effective_queries"] == 1.8
    assert page["ranking_opportunity"]["positions_4_20_impressions"] == 300


def test_ownership_and_commercial_value_remain_transparent() -> None:
    assert ownership_metrics([{"impressions": 75}, {"impressions": 25}]) == {
        "hhi": 0.625,
        "primary_owner_share": 0.75,
        "effective_owners": 1.6,
    }
    items = [
        {
            "metrics": {"current": {"revenue": 80}},
            "statistics": {"ranking_opportunity": {"positions_4_20_impressions": 200}},
        },
        {
            "metrics": {"current": {"revenue": 20}},
            "statistics": {"ranking_opportunity": {"positions_4_20_impressions": 50}},
        },
    ]

    portfolio = commercial_value_statistics(items, currency="USD")

    assert portfolio["revenue_hhi"] == 0.68
    assert items[0]["statistics"]["commercial_value"]["quadrant"] == "grow"
    assert items[0]["statistics"]["commercial_value"]["revenue_share"] == 0.8
    assert items[1]["statistics"]["commercial_value"]["quadrant"] == "maintain"
    assert items[1]["statistics"]["commercial_value"]["attribution"].startswith("all-channel")


def test_ctr_benchmark_uses_leave_page_out_position_bands() -> None:
    report = build_search_statistics(
        [],
        [
            _row("desk", 1, 200, 5),
            {"keys": ["lamp", OTHER], "clicks": 20, "impressions": 200, "position": 5},
        ],
        "https://example.com",
    )

    benchmark = report["pages"][URL]["ctr_benchmark"]
    assert benchmark["classification"] == "below_expected"
    assert benchmark["expected_clicks"] > 10
    assert benchmark["recoverable_clicks"] > 9
    assert benchmark["p_value_unadjusted"] < 0.05
    assert benchmark["q_value"] < 0.05
    assert benchmark["fdr_significant"] is True
    assert report["portfolio"]["ctr_benchmark"]["multiple_testing"]["method"] == "Benjamini-Hochberg"
