from datetime import date, timedelta

from seo_workbench.technical_statistics import build_technical_issue_effects


def test_technical_issue_effects_require_repeated_verified_fixes_and_control_fdr() -> None:
    fixed = date(2026, 7, 20)
    coverage = [(fixed - timedelta(days=14) + timedelta(days=offset)).isoformat() for offset in range(29)]
    records = []
    rows = []
    for index in range(6):
        url = f"https://example.com/page-{index}"
        records.append(
            {
                "rule_id": "MISSING_H1",
                "url": url,
                "status": "verified",
                "verification_status": "passed",
                "history": [
                    {
                        "event": "status_changed",
                        "status": "fixed",
                        "at": "2026-07-20T12:00:00+00:00",
                    }
                ],
            }
        )
        for day in (date.fromisoformat(value) for value in coverage):
            after = day > fixed
            rows.append(
                {
                    "date": day.isoformat(),
                    "url": url,
                    "clicks": 3 if after else 1,
                    "impressions": 10,
                }
            )

    report = build_technical_issue_effects(records, rows, coverage)
    effect = report["rules"]["MISSING_H1"]

    assert effect["verified_fixes"] == 6
    assert effect["provisional_fixes"] == 0
    assert effect["classification"] == "positive_association"
    assert effect["q_value"] < 0.05
    assert report["significant_rules"] == 1
    assert report["causal_claim"] is False

    broken = build_technical_issue_effects(records, rows, coverage, regime_dates={"2026-07-20"})
    assert broken["rules"]["MISSING_H1"]["status"] == "insufficient_data"


def test_technical_issue_effects_stay_insufficient_for_one_fix() -> None:
    report = build_technical_issue_effects(
        [
            {
                "rule_id": "MISSING_H1",
                "url": "https://example.com/page",
                "status": "verified",
                "verification_status": "passed",
                "history": [{"event": "status_changed", "status": "fixed", "at": "2026-07-20T12:00:00Z"}],
            }
        ],
        [],
        [],
    )

    assert report["rules"]["MISSING_H1"]["status"] == "insufficient_data"


def test_technical_issue_effects_accept_provisional_fixes_with_confidence() -> None:
    fixed = date(2026, 7, 20)
    coverage = [(fixed - timedelta(days=14) + timedelta(days=offset)).isoformat() for offset in range(29)]
    records = []
    rows = []
    for index in range(6):
        url = f"https://example.com/page-{index}"
        records.append(
            {
                "rule_id": "MISSING_H1",
                "url": url,
                "status": "fixed",
                "verification_status": "provisional",
                "history": [
                    {
                        "event": "status_changed",
                        "status": "fixed",
                        "at": "2026-07-20T12:00:00+00:00",
                    }
                ],
            }
        )
        for day in (date.fromisoformat(value) for value in coverage):
            after = day > fixed
            rows.append(
                {
                    "date": day.isoformat(),
                    "url": url,
                    "clicks": 3 if after else 1,
                    "impressions": 10,
                }
            )

    report = build_technical_issue_effects(records, rows, coverage)
    effect = report["rules"]["MISSING_H1"]

    assert effect["status"] == "tested"
    assert effect["verified_fixes"] == 6
    assert effect["provisional_fixes"] == 6
    assert all(observation["confidence"] == "provisional" for observation in effect["observations"])
