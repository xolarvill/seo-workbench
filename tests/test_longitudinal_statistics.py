from datetime import date, timedelta

from seo_workbench.longitudinal_statistics import build_longitudinal_statistics


URL = "https://example.com/page"


def _dates(start: date, count: int) -> list[str]:
    return [(start + timedelta(days=offset)).isoformat() for offset in range(count)]


def test_longitudinal_statistics_produce_confidence_trend_and_cross_source_diagnostics() -> None:
    days = _dates(date(2026, 6, 18), 56)
    gsc = []
    business = []
    for index, day in enumerate(days):
        current = index >= 28
        clicks = 8 if current else 2
        sessions = 30 if current else 4
        gsc.append({"date": day, "url": URL, "clicks": clicks, "impressions": 100})
        business.append(
            {
                "date": day,
                "url": URL,
                "organic_sessions": sessions,
                "engaged_sessions": sessions * 0.6,
                "key_events": sessions * 0.1,
            }
        )
    report = build_longitudinal_statistics(
        gsc,
        business,
        {"gsc": days, "business": days},
        previous={"request": {"startDate": days[0], "endDate": days[27]}},
        current={"request": {"startDate": days[28], "endDate": days[-1]}},
        include_business=True,
    )

    page = report["pages"][URL]
    assert page["search_change_confidence"]["evidence_grade"] == "strong"
    assert page["search_change_confidence"]["click_change"]["direction"] == "increase"
    assert page["search_trend"]["direction"] == "up"
    assert page["organic_engagement"]["current"]["engagement_rate"]["estimate"] == 0.6
    assert page["cross_source_consistency"]["status"] == "possible_measurement_break"


def test_longitudinal_statistics_refuse_uncovered_or_never_observed_pages() -> None:
    days = _dates(date(2026, 7, 1), 56)
    report = build_longitudinal_statistics(
        [],
        [],
        {"gsc": days[:20], "business": []},
        previous={"request": {"startDate": days[0], "endDate": days[27]}},
        current={"request": {"startDate": days[28], "endDate": days[-1]}},
        include_business=False,
    )

    assert report["portfolio"]["search_change_confidence"]["status"] == "insufficient_data"
