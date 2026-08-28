import json
from pathlib import Path

import pytest

from seo_workbench import state
from seo_workbench.statistics_history import (
    canonical_device,
    ingest_daily_history,
    load_daily_history,
    load_history_coverage,
)


def _project(path: Path) -> Path:
    state.init_state("shopify", "Example", "https://example.com", project_dir=path)
    return path


def _write(path: Path, payload: dict) -> Path:
    path.write_text(json.dumps(payload), encoding="utf-8")
    return path


def test_history_ingest_is_private_idempotent_and_retained(tmp_path: Path) -> None:
    project = _project(tmp_path / "project")
    gsc = _write(
        tmp_path / "gsc.json",
        {
            "collection_status": "ok",
            "windows": {
                "previous": {
                    "date_page": {
                        "request": {"startDate": "2026-04-01", "endDate": "2026-04-01"},
                        "rows": [
                            {
                                "keys": ["2026-04-01", "https://example.com/old"],
                                "clicks": 1,
                                "impressions": 10,
                                "ctr": 0.1,
                                "position": 4,
                            }
                        ]
                    },
                    "date_page_device": {
                        "request": {"startDate": "2026-04-01", "endDate": "2026-04-01"},
                        "rows": [
                            {
                                "keys": ["2026-04-01", "https://example.com/old", "MOBILE"],
                                "clicks": 1,
                                "impressions": 10,
                                "ctr": 0.1,
                                "position": 4,
                            }
                        ],
                    },
                },
                "current": {
                    "date_page": {
                        "request": {"startDate": "2026-08-12", "endDate": "2026-08-12"},
                        "rows": [
                            {
                                "keys": ["2026-08-12", "https://example.com/new"],
                                "clicks": 2,
                                "impressions": 20,
                                "ctr": 0.1,
                                "position": 5,
                            }
                        ]
                    },
                    "date_page_device": {
                        "request": {"startDate": "2026-08-12", "endDate": "2026-08-12"},
                        "rows": [
                            {
                                "keys": ["2026-08-12", "https://example.com/new", "MOBILE"],
                                "clicks": 2,
                                "impressions": 20,
                                "ctr": 0.1,
                                "position": 5,
                            },
                            {
                                "keys": ["2026-08-12", "https://example.com/new", "TV"],
                                "impressions": 3,
                                "position": 9,
                            },
                        ],
                    },
                },
            },
        },
    )
    business = _write(
        tmp_path / "business.json",
        {
            "collection_status": "ok",
            "windows": {
                "current": {
                    "request": {"startDate": "2026-08-12", "endDate": "2026-08-12"},
                    "daily_rows": [
                        {
                            "date": "2026-08-12",
                            "url": "https://example.com/new",
                            "organic_sessions": 3,
                            "organic_purchases": 1,
                            "organic_revenue": -2,
                            "revenue": -5,
                        }
                    ]
                }
            },
        },
    )

    first = ingest_daily_history(project, gsc_path=gsc, business_path=business, retain_days=120)
    second = ingest_daily_history(project, gsc_path=gsc, business_path=business, retain_days=120)

    assert first["sources"]["gsc"]["stored_rows"] == 1
    assert second["sources"]["gsc"]["stored_rows"] == 1
    assert first["sources"]["gsc_page_device"]["stored_rows"] == 2
    assert second["sources"]["gsc_page_device"]["stored_rows"] == 2
    assert load_daily_history(project, "gsc")[0]["url"] == "https://example.com/new"
    device_rows = load_daily_history(project, "gsc_page_device")
    assert device_rows[0]["device"] == "MOBILE"
    assert device_rows[0]["device_canonical"] == "mobile"
    assert device_rows[1]["device_canonical"] == "other"
    assert "clicks" not in device_rows[1]
    assert load_daily_history(project, "business")[0]["revenue"] == -5
    assert load_daily_history(project, "business")[0]["organic_revenue"] == -2
    for path in (
        project / "audits/statistics/history/gsc-page-daily.jsonl",
        project / "audits/statistics/history/gsc-page-device-daily.jsonl",
        project / "audits/statistics/history/business-page-daily.jsonl",
    ):
        assert path.stat().st_mode & 0o777 == 0o600
    assert (project / "audits/statistics/history/coverage.json").stat().st_mode & 0o777 == 0o600
    assert first["sources"]["gsc"]["covered_days"] == 1
    assert first["sources"]["gsc_page_device"]["covered_days"] == 1
    assert load_history_coverage(project)["gsc_page_device"] == ["2026-08-12"]


def test_history_rejects_truncated_or_external_evidence(tmp_path: Path) -> None:
    project = _project(tmp_path / "project")
    business = _write(tmp_path / "business.json", {"collection_status": "ok", "windows": {}})
    truncated = _write(
        tmp_path / "truncated.json",
        {"collection_status": "ok", "windows": {"current": {"date_page": {"truncated": True, "rows": []}}}},
    )
    with pytest.raises(ValueError, match="truncated"):
        ingest_daily_history(project, gsc_path=truncated, business_path=business)

    truncated_device = _write(
        tmp_path / "truncated-device.json",
        {
            "collection_status": "ok",
            "windows": {
                "current": {
                    "date_page": {
                        "request": {"startDate": "2026-08-12", "endDate": "2026-08-12"},
                        "rows": [],
                    },
                    "date_page_device": {
                        "request": {"startDate": "2026-08-12", "endDate": "2026-08-12"},
                        "truncated": True,
                        "rows": [],
                    },
                }
            },
        },
    )
    with pytest.raises(ValueError, match="date-page-device.*truncated"):
        ingest_daily_history(project, gsc_path=truncated_device, business_path=business)

    external = _write(
        tmp_path / "external.json",
        {
            "collection_status": "ok",
            "windows": {
                "current": {
                    "date_page": {
                        "request": {"startDate": "2026-08-12", "endDate": "2026-08-12"},
                        "rows": [
                            {
                                "keys": ["2026-08-12", "https://attacker.example/page"],
                                "clicks": 1,
                                "impressions": 1,
                                "ctr": 1,
                                "position": 1,
                            }
                        ]
                    }
                }
            },
        },
    )
    with pytest.raises(ValueError, match="outside"):
        ingest_daily_history(project, gsc_path=external, business_path=business)


@pytest.mark.parametrize(
    ("provider", "canonical"),
    [("MOBILE", "mobile"), ("desktop", "desktop"), ("TABLET", "tablet"), ("TV", "other"), ("", "unknown")],
)
def test_canonical_device_preserves_supported_buckets(provider: str, canonical: str) -> None:
    assert canonical_device(provider) == canonical


def test_history_accepts_legacy_gsc_artifact_without_device_rows(tmp_path: Path) -> None:
    project = _project(tmp_path / "project")
    gsc = _write(
        tmp_path / "legacy-gsc.json",
        {
            "collection_status": "ok",
            "windows": {
                "current": {
                    "date_page": {
                        "request": {"startDate": "2026-08-12", "endDate": "2026-08-12"},
                        "rows": [{"keys": ["2026-08-12", "https://example.com/new"], "clicks": 1}],
                    }
                }
            },
        },
    )
    business = _write(
        tmp_path / "business.json",
        {
            "collection_status": "ok",
            "windows": {
                "current": {
                    "request": {"startDate": "2026-08-12", "endDate": "2026-08-12"},
                    "daily_rows": [],
                }
            },
        },
    )

    result = ingest_daily_history(project, gsc_path=gsc, business_path=business)

    assert result["sources"]["gsc"]["stored_rows"] == 1
    assert result["sources"]["gsc_page_device"]["stored_rows"] == 0
    assert load_daily_history(project, "gsc_page_device") == []
    assert load_history_coverage(project)["gsc_page_device"] == []
