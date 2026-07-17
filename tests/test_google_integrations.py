from __future__ import annotations

import json
from datetime import date
from pathlib import Path

import pytest

from seo_workbench_tools import gsc_probe


class Credentials:
    token = "test-token"


def project(tmp_path: Path, url: str = "https://shop.example.com/path/") -> Path:
    (tmp_path / "state.json").write_text(json.dumps({"project": {"url": url}}))
    return tmp_path


def bind(tmp_path: Path, property_url: str = "sc-domain:example.com") -> None:
    path = gsc_probe.binding_path(tmp_path)
    path.parent.mkdir(parents=True)
    path.write_text(json.dumps({"profile": "default", "property": property_url}))


def test_property_coverage_supports_domain_and_url_prefix() -> None:
    assert gsc_probe.property_covers_url("sc-domain:example.com", "https://shop.example.com/a")
    assert not gsc_probe.property_covers_url("sc-domain:example.com", "https://notexample.com/a")
    assert gsc_probe.property_covers_url("https://example.com/shop/", "https://example.com/shop/a")
    assert not gsc_probe.property_covers_url("https://example.com/shop/", "http://example.com/shop/a")
    assert not gsc_probe.property_covers_url("https://example.com/shop/", "https://example.com/other")


def test_bind_requires_accessible_covering_property(tmp_path, monkeypatch) -> None:
    project(tmp_path)
    monkeypatch.setattr(gsc_probe, "load_credentials", lambda profile: Credentials())

    def requester(method, url, body, credentials, timeout):
        return {
            "siteEntry": [
                {"siteUrl": "sc-domain:example.com", "permissionLevel": "siteOwner"},
                {"siteUrl": "https://other.example.net/", "permissionLevel": "siteFullUser"},
            ]
        }

    result = gsc_probe.bind_property(tmp_path, "sc-domain:example.com", requester=requester)
    assert result["permission_level"] == "siteOwner"
    assert gsc_probe.binding_path(tmp_path).stat().st_mode & 0o777 == 0o600
    with pytest.raises(ValueError, match="does not cover"):
        gsc_probe.bind_property(tmp_path, "https://other.example.net/", requester=requester)


def test_search_analytics_collects_current_previous_and_paginates(tmp_path, monkeypatch) -> None:
    project(tmp_path)
    bind(tmp_path)
    monkeypatch.setattr(gsc_probe, "load_credentials", lambda profile: Credentials())
    calls = []

    def requester(method, url, body, credentials, timeout):
        calls.append(body)
        if body.get("dimensions") == ["page"] and body["startRow"] == 0:
            return {"rows": [{"keys": [f"https://example.com/{i}"]} for i in range(25000)]}
        return {"rows": [], "metadata": {"first_incomplete_date": "2026-07-10"}}

    report = gsc_probe.collect_performance(
        tmp_path,
        tmp_path / "audits/gsc/search-analytics",
        days=28,
        requester=requester,
        today=date(2026, 7, 17),
    )

    assert report["collection_status"] == "ok"
    assert report["windows"]["current"]["page"]["row_count"] == 25000
    assert any(call["startRow"] == 25000 for call in calls)
    assert report["windows"]["current"]["date"]["request"]["endDate"] == "2026-07-14"
    assert (tmp_path / "audits/gsc/search-analytics/latest.json").stat().st_mode & 0o777 == 0o600


def test_inspection_stops_after_quota_error_and_marks_indexed_only(tmp_path, monkeypatch) -> None:
    project(tmp_path)
    bind(tmp_path)
    monkeypatch.setattr(gsc_probe, "load_credentials", lambda profile: Credentials())
    calls = 0

    def requester(method, url, body, credentials, timeout):
        nonlocal calls
        calls += 1
        if calls == 2:
            raise gsc_probe.GscQuotaExceeded("quota")
        return {"inspectionResult": {"indexStatusResult": {"verdict": "PASS"}}}

    report = gsc_probe.collect_inspection(
        tmp_path,
        tmp_path / "audits/gsc/inspection",
        urls=["https://shop.example.com/path/", "https://shop.example.com/path/two", "https://shop.example.com/path/three"],
        requester=requester,
    )
    assert calls == 2
    assert report["collection_status"] == "partial"
    assert report["quota_exhausted"] is True
    assert report["indexed_version_only"] is True


def test_sitemaps_omit_deprecated_indexed_field(tmp_path, monkeypatch) -> None:
    project(tmp_path)
    bind(tmp_path)
    monkeypatch.setattr(gsc_probe, "load_credentials", lambda profile: Credentials())

    def requester(method, url, body, credentials, timeout):
        return {
            "sitemap": [
                {
                    "path": "https://shop.example.com/sitemap.xml",
                    "errors": "2",
                    "warnings": "1",
                    "contents": [{"type": "web", "submitted": "100", "indexed": "80"}],
                }
            ]
        }

    report = gsc_probe.collect_sitemaps(tmp_path, tmp_path / "audits/gsc/sitemaps", requester=requester)
    assert report["sitemaps"][0]["contents"] == [{"type": "web", "submitted": 100}]


def test_representative_urls_prioritize_failed_and_canonical_pages(tmp_path) -> None:
    project(tmp_path, "https://example.com/")
    raw = tmp_path / "audits/raw"
    raw.mkdir(parents=True)
    (raw / "latest.json").write_text(
        json.dumps(
            {
                "pages": [
                    {"url": "https://example.com/ok"},
                    {"url": "https://example.com/canonical", "canonical_audit": {"issues": ["mismatch"]}},
                    {"url": "https://example.com/failed", "error": "timeout"},
                ]
            }
        )
    )
    assert gsc_probe.representative_urls(tmp_path, 3) == [
        "https://example.com/",
        "https://example.com/failed",
        "https://example.com/canonical",
    ]
