from __future__ import annotations

import json
import os
from datetime import date
from pathlib import Path

import pytest

from seo_workbench_tools import ga4_probe, gsc_probe


class Credentials:
    token = "test-token"


def project(tmp_path: Path, url: str = "https://shop.example.com/path/") -> Path:
    (tmp_path / "project.json").write_text(json.dumps({"project": {"url": url}}))
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
    dimensions = {tuple(call.get("dimensions", [])) for call in calls if call["startRow"] == 0}
    assert {("date", "page"), ("date", "page", "device"), ("query", "page"), ("country",)} <= dimensions
    assert report["windows"]["current"]["query_page"]["request"]["dimensions"] == ["query", "page"]
    assert report["windows"]["current"]["date_page_device"]["request"]["dimensions"] == ["date", "page", "device"]
    assert report["windows"]["current"]["date"]["request"]["endDate"] == "2026-07-14"
    assert (tmp_path / "audits/gsc/search-analytics/latest.json").stat().st_mode & 0o777 == 0o600


def test_change_performance_collects_url_scoped_windows_around_change_day(tmp_path, monkeypatch) -> None:
    project(tmp_path)
    bind(tmp_path)
    monkeypatch.setattr(gsc_probe, "load_credentials", lambda profile: Credentials())
    calls = []

    def requester(method, url, body, credentials, timeout):
        calls.append(body)
        return {"rows": []}

    report = gsc_probe.collect_change_performance(
        tmp_path,
        tmp_path / "audits/gsc/change-outcomes/change-1",
        urls=["https://shop.example.com/path/article"],
        changed_at=date(2026, 8, 1),
        review_date=date(2026, 8, 29),
        requester=requester,
        today=date(2026, 9, 5),
    )

    assert report["windows"]["previous"]["page"]["request"]["endDate"] == "2026-07-31"
    assert report["windows"]["current"]["page"]["request"]["startDate"] == "2026-08-02"
    assert {tuple(call["dimensions"]) for call in calls} == {
        ("page",),
        ("date", "page"),
        ("date", "page", "device"),
        ("query", "page"),
    }
    assert all(call["dimensionFilterGroups"][0]["filters"][0]["operator"] == "equals" for call in calls)
    assert (tmp_path / "audits/gsc/change-outcomes/change-1/latest.json").stat().st_mode & 0o777 == 0o600

    with pytest.raises(ValueError, match="newer than finalized GSC data"):
        gsc_probe.collect_change_performance(
            tmp_path,
            tmp_path / "audits/gsc/change-outcomes/future",
            urls=["https://shop.example.com/path/article"],
            changed_at=date(2026, 8, 10),
            review_date=date(2026, 9, 4),
            requester=requester,
            today=date(2026, 9, 5),
        )

    with pytest.raises(ValueError, match="at most 25 URLs"):
        gsc_probe.collect_change_performance(
            tmp_path,
            tmp_path / "audits/gsc/change-outcomes/too-many",
            urls=[f"https://shop.example.com/path/{index}" for index in range(26)],
            changed_at=date(2026, 8, 1),
            review_date=date(2026, 8, 29),
            requester=requester,
            today=date(2026, 9, 5),
        )


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


def test_binding_rejects_symlinked_runtime_directory(tmp_path) -> None:
    outside = tmp_path / "outside"
    outside.mkdir()
    (tmp_path / "project").mkdir()
    (tmp_path / "project/.runtime").symlink_to(outside, target_is_directory=True)
    with pytest.raises(ValueError, match="symlink"):
        gsc_probe.binding_path(tmp_path / "project")


def test_ga4_import_service_account_replaces_oauth_token(tmp_path, monkeypatch) -> None:
    seen: dict[str, object] = {}

    class FakeServiceAccountCredentials:
        @staticmethod
        def from_service_account_info(payload, scopes=None):
            seen["payload"] = payload
            seen["scopes"] = scopes
            return object()

    class FakeServiceAccount:
        pass

    FakeServiceAccount.Credentials = FakeServiceAccountCredentials
    monkeypatch.setattr(ga4_probe, "_load_google_auth", lambda: (None, None, FakeServiceAccount, ValueError))
    directory = tmp_path / "profiles/ga4"
    directory.mkdir(parents=True)
    (directory / "ga4-token.json").write_text("{}")
    payload = {
        "type": "service_account",
        "client_email": "seo@example.iam.gserviceaccount.com",
        "private_key": "-----BEGIN PRIVATE KEY-----\ntest\n-----END PRIVATE KEY-----\n",
    }

    result = ga4_probe.import_credentials("ga4", payload, runtime_root=tmp_path)

    assert result["credential_type"] == "service_account"
    assert seen["payload"] == payload
    assert seen["scopes"] == ga4_probe.SCOPES
    stored = directory / "ga4-service-account.json"
    assert json.loads(stored.read_text(encoding="utf-8"))["client_email"] == payload["client_email"]
    assert not (directory / "ga4-token.json").exists()
    if os.name != "nt":
        assert stored.stat().st_mode & 0o777 == 0o600


def test_ga4_import_oauth_removes_service_account(tmp_path) -> None:
    directory = tmp_path / "profiles/ga4"
    directory.mkdir(parents=True)
    (directory / "ga4-service-account.json").write_text("{}")
    (directory / "service-account.json").write_text("{}")

    result = ga4_probe.import_credentials(
        "ga4",
        {
            "access_token": "access",
            "refresh_token": "refresh",
            "client_id": "client",
            "client_secret": "secret",
        },
        runtime_root=tmp_path,
    )

    assert result["credential_type"] == "oauth"
    assert not (directory / "ga4-service-account.json").exists()
    assert (directory / "ga4-token.json").is_file()
    assert (directory / "service-account.json").exists()


def test_ga4_import_rejects_invalid_service_account(tmp_path, monkeypatch) -> None:
    class FakeServiceAccountCredentials:
        @staticmethod
        def from_service_account_info(payload, scopes=None):
            raise ValueError("bad key")

    class FakeServiceAccount:
        pass

    FakeServiceAccount.Credentials = FakeServiceAccountCredentials
    monkeypatch.setattr(ga4_probe, "_load_google_auth", lambda: (None, None, FakeServiceAccount, ValueError))
    with pytest.raises(ValueError, match="invalid Google service account key"):
        ga4_probe.import_credentials(
            "ga4",
            {"type": "service_account", "client_email": "seo@example.com", "private_key": "broken"},
            runtime_root=tmp_path,
        )


def test_ga4_load_credentials_refreshes_service_account(tmp_path, monkeypatch) -> None:
    refreshes: list[object] = []

    class FakeServiceAccountCredentials:
        valid = False
        token = None
        service_account_email = "seo@example.iam.gserviceaccount.com"

        def refresh(self, request):
            refreshes.append(request)
            self.valid = True
            self.token = "service-account-token"

    class FakeCredentialsFactory:
        @staticmethod
        def from_service_account_file(path, scopes=None):
            assert Path(path).name == "ga4-service-account.json"
            assert scopes == ga4_probe.SCOPES
            return FakeServiceAccountCredentials()

    class FakeServiceAccount:
        pass

    FakeServiceAccount.Credentials = FakeCredentialsFactory

    def request_factory():
        return "auth-request"

    monkeypatch.setattr(
        ga4_probe, "_load_google_auth", lambda: (request_factory, None, FakeServiceAccount, ValueError)
    )
    directory = tmp_path / "profiles/ga4"
    directory.mkdir(parents=True)
    (directory / "ga4-service-account.json").write_text(
        json.dumps({"type": "service_account", "client_email": "seo@example.iam.gserviceaccount.com"})
    )

    credentials = ga4_probe.load_credentials("ga4", runtime_root=tmp_path)

    assert credentials.token == "service-account-token"
    assert refreshes == ["auth-request"]
