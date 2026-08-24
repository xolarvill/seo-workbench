from __future__ import annotations

import hashlib
import json
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from fastapi.testclient import TestClient

from seo_workbench import state, ui as ui_module
from seo_workbench.locks import lock_path, project_lock
from seo_workbench.seo_changes import list_changes, record_change
from seo_workbench.tech_issues import list_issue_register, sync_issue_register
from seo_workbench.ui import ACTION_COMMANDS, COOKIE_NAME, BrowserCapture, EventHub, _safe_job_output, create_app
from seo_workbench.tech_audit import set_schedule
from seo_workbench_tools import gsc_probe


def ui_client(tmp_path: Path) -> tuple[TestClient, Path]:
    projects_root = tmp_path / "projects"
    project_dir = projects_root / "store"
    state.init_state("shopify", "Store", "https://example.com", project_dir=project_dir)
    (project_dir / "strategy/cluster-plan.md").write_text("# Original\n", encoding="utf-8")
    tutorials_dir = tmp_path / "docs"
    tutorials_dir.mkdir()
    (tutorials_dir / "SEO基础知识与证据模型.md").write_text("# SEO Foundations\n\nLocal tutorial.\n", encoding="utf-8")
    app = create_app(
        token="test-token",
        projects_root=projects_root,
        runtime_dir=tmp_path / ".runtime/ui",
        frontend_dir=None,
        tutorials_dir=tutorials_dir,
        watch_files=False,
    )
    client = TestClient(app)
    client.cookies.set(COOKIE_NAME, "test-token")
    return client, project_dir


def browser_capture(url: str = "https://example.com/product?utm_source=test&token=secret") -> dict:
    return {
        "schema_version": "browser-capture-v1",
        "capture_id": "7b260d67-3b08-4b59-b775-cec7ccdcf25c",
        "captured_at": "2026-07-26T03:00:00Z",
        "collection_status": "complete",
        "requested_url": url,
        "final_url": url,
        "document": {"title": "Example", "description": "Summary", "canonical": "https://example.com/product", "robots": "", "lang": "en", "viewport": "width=device-width", "word_count": 20},
        "headings": [{"level": 1, "text": "Example"}],
        "images": {"total": 0, "missing_alt": 0, "empty_alt": 0, "lazy_loaded": 0, "missing_dimensions": 0},
        "links": {"total": 0, "internal": 0, "external": 0, "nofollow": 0, "sponsored": 0, "ugc": 0, "empty_anchor": 0},
        "structured_data": {"blocks": 0, "types": [], "parse_errors": 0},
        "hreflang": [],
        "social": {"open_graph": {}, "twitter": {}},
        "performance_observation": {"source": "browser_navigation_timing", "dom_content_loaded_ms": 100, "load_ms": 200, "transfer_size_bytes": 1000, "decoded_body_size_bytes": 2000, "resource_count": 2},
        "source": {"kind": "chrome_extension", "extension_version": "0.1.0", "user_agent": "Chrome test", "viewport": {"width": 1280, "height": 720, "device_pixel_ratio": 1}},
        "findings": [],
        "summary": {"critical": 0, "warning": 0, "passed": 0},
        "errors": [],
        "warnings": [],
    }


def test_keyword_workspace_api_materializes_candidates_and_detects_conflict(tmp_path: Path) -> None:
    client, project_dir = ui_client(tmp_path)
    (project_dir / "audits/gsc/search-analytics").mkdir(parents=True, exist_ok=True)
    (project_dir / "audits/gsc/search-analytics/latest.json").write_text(
        json.dumps(
            {
                "collection_status": "ok",
                "windows": {
                    "current": {
                        "query": {
                            "rows": [
                                {"keys": ["monitor riser"], "clicks": 3, "impressions": 90, "ctr": 0.033, "position": 9}
                            ]
                        }
                    }
                },
            }
        ),
        encoding="utf-8",
    )

    view = client.get("/api/v1/projects/store/keywords/view").json()
    assert view["rows"][0]["managed"] is False
    update = client.patch(
        "/api/v1/projects/store/keywords",
        json={
            "keywords": ["monitor riser"],
            "patch": {"decision": "prioritize", "target_url": "/collections/monitor-stands"},
            "base_revision": view["revision"],
        },
    )
    assert update.status_code == 200
    assert json.loads((project_dir / "strategy/keyword-pool.jsonl").read_text())["decision"] == "prioritize"

    conflict = client.patch(
        "/api/v1/projects/store/keywords",
        json={
            "keywords": ["monitor riser"],
            "patch": {"decision": "hold"},
            "base_revision": view["revision"],
        },
    )
    assert conflict.status_code == 409
    assert conflict.json()["detail"]["code"] == "revision_conflict"


def test_keyword_handoff_api_returns_stable_path_without_creating_file(tmp_path: Path) -> None:
    client, project_dir = ui_client(tmp_path)
    (project_dir / "audits/gsc/search-analytics").mkdir(parents=True, exist_ok=True)
    (project_dir / "audits/gsc/search-analytics/latest.json").write_text(
        json.dumps(
            {
                "windows": {
                    "current": {
                        "query": {"rows": [{"keys": ["monitor riser"], "impressions": 90}]}
                    }
                }
            }
        ),
        encoding="utf-8",
    )

    response = client.get("/api/v1/projects/store/keywords/handoff", params={"keyword": "monitor riser"})
    assert response.status_code == 200
    assert response.json()["output_path"] == "strategy/keyword-dives/info-monitor-riser.md"
    assert not (project_dir / response.json()["output_path"]).exists()


def test_browser_capture_schema_matches_server_contract() -> None:
    schema = json.loads((state.ROOT / "schema/browser-capture-v1.schema.json").read_text(encoding="utf-8"))
    assert set(schema["properties"]) == set(BrowserCapture.model_fields)


def test_ui_requires_local_session_but_health_is_public(tmp_path: Path) -> None:
    projects_root = tmp_path / "projects"
    app = create_app(
        token="secret",
        projects_root=projects_root,
        runtime_dir=tmp_path / ".runtime/ui",
        frontend_dir=None,
        watch_files=False,
    )
    with TestClient(app) as client:
        assert client.get("/api/v1/health").status_code == 200
        assert client.get("/api/v1/projects").status_code == 401
        boot = client.get("/?token=secret", follow_redirects=False)
        assert boot.status_code == 303
        assert COOKIE_NAME in boot.cookies


def test_ui_cookieless_mode_accepts_token_without_cookie(tmp_path: Path) -> None:
    projects_root = tmp_path / "projects"
    state.init_state("shopify", "Store", "https://example.com", project_dir=projects_root / "store")
    app = create_app(
        token="secret",
        projects_root=projects_root,
        runtime_dir=tmp_path / ".runtime/ui",
        frontend_dir=None,
        watch_files=False,
        allow_cookieless=True,
    )
    with TestClient(app) as client:
        assert client.get("/api/v1/health").status_code == 200
        bearer = client.get("/api/v1/projects", headers={"Authorization": "Bearer secret"})
        assert bearer.status_code == 200
        query = client.get("/api/v1/projects?token=secret")
        assert query.status_code == 200
        assert client.get("/api/v1/projects").status_code == 401
        assert client.get("/api/v1/projects", headers={"Authorization": "Bearer wrong"}).status_code == 401


def test_ui_cookieless_mode_keeps_token_url_and_sets_cookie(tmp_path: Path) -> None:
    projects_root = tmp_path / "projects"
    app = create_app(
        token="secret",
        projects_root=projects_root,
        runtime_dir=tmp_path / ".runtime/ui",
        frontend_dir=None,
        watch_files=False,
        allow_cookieless=True,
    )
    with TestClient(app) as client:
        boot = client.get("/?token=secret", follow_redirects=False)
        assert boot.status_code == 200
        assert COOKIE_NAME in boot.cookies


def test_ui_default_mode_rejects_bearer_and_query_tokens(tmp_path: Path) -> None:
    projects_root = tmp_path / "projects"
    state.init_state("shopify", "Store", "https://example.com", project_dir=projects_root / "store")
    app = create_app(
        token="secret",
        projects_root=projects_root,
        runtime_dir=tmp_path / ".runtime/ui",
        frontend_dir=None,
        watch_files=False,
    )
    with TestClient(app) as client:
        assert client.get("/api/v1/projects", headers={"Authorization": "Bearer secret"}).status_code == 401
        assert client.get("/api/v1/projects?token=secret").status_code == 401


def test_ui_accepts_nucleus_identity_headers_without_local_cookie(tmp_path: Path) -> None:
    projects_root = tmp_path / "projects"
    state.init_state("shopify", "Store", "https://example.com", project_dir=projects_root / "store")
    app = create_app(
        token="secret",
        projects_root=projects_root,
        runtime_dir=tmp_path / ".runtime/ui",
        frontend_dir=None,
        watch_files=False,
    )
    nucleus_headers = {"host": "seo.nucleus.localhost:8080", "x-nucleus-user-id": "user-1"}
    with TestClient(app) as client:
        assert client.get("/health", headers={"host": "seo.nucleus.localhost:8080"}).status_code == 200
        assert client.get("/api/v1/projects", headers={"host": "seo.nucleus.localhost:8080"}).status_code == 401
        assert client.get("/api/v1/projects", headers=nucleus_headers).status_code == 200
        rejected = client.post(
            "/api/v1/projects/store/workflow",
            headers={**nucleus_headers, "origin": "http://evil.example"},
            json={"action": "unknown"},
        )
        assert rejected.status_code == 403
        passed = client.post(
            "/api/v1/projects/store/workflow",
            headers={**nucleus_headers, "origin": "http://seo.nucleus.localhost:8080"},
            json={"action": "unknown"},
        )
        assert passed.status_code == 400


def test_extension_pairing_persists_redacted_browser_capture(tmp_path: Path) -> None:
    client, project_dir = ui_client(tmp_path)
    origin = "chrome-extension://abcdefghijklmnopabcdefghijklmnop"
    headers = {"Origin": origin}
    verifier = "v" * 48
    verifier_hash = hashlib.sha256(verifier.encode()).hexdigest()

    with client:
        extension_health = client.get("/api/v1/health", headers=headers)
        assert extension_health.status_code == 200
        assert "projects_root" not in extension_health.json()
        assert client.get("/api/v1/extension/projects", headers=headers).status_code == 401
        preflight = client.options("/api/v1/extension/projects", headers=headers)
        assert preflight.status_code == 204
        assert preflight.headers["access-control-allow-origin"] == origin
        started = client.post(
            "/api/v1/extension/pairings",
            headers=headers,
            json={"verifier_hash": verifier_hash, "extension_version": "0.1.0"},
        )
        assert started.status_code == 201
        assert started.headers["access-control-allow-origin"] == origin
        pairing_id = started.json()["pairing_id"]

        approval = client.get(f"/extension/pair/{pairing_id}")
        assert approval.status_code == 200
        assert approval.headers["x-frame-options"] == "DENY"
        assert "frame-ancestors 'none'" in approval.headers["content-security-policy"]
        assert client.post(f"/extension/pair/{pairing_id}/approve", headers={"Origin": "http://testserver:9999"}).status_code == 403
        assert client.post(f"/extension/pair/{pairing_id}/approve").status_code == 200
        finished = client.post(
            f"/api/v1/extension/pairings/{pairing_id}/token",
            headers=headers,
            json={"verifier": verifier},
        )
        token = finished.json()["token"]
        authorized = headers | {"Authorization": f"Bearer {token}"}

        projects = client.get("/api/v1/extension/projects", headers=authorized)
        assert projects.status_code == 200
        capture = browser_capture()
        capture["findings"] = [{"id": "canonical", "severity": "warning", "title": "Canonical", "detail": capture["final_url"]}]
        capture["social"]["open_graph"] = {"og:url": capture["final_url"]}
        saved = client.post(
            "/api/v1/extension/projects/store/captures",
            headers=authorized,
            json={"capture": capture},
        )

    assert saved.status_code == 201
    artifact = project_dir / saved.json()["artifact"]
    latest = project_dir / "audits/browser/latest.json"
    assert artifact.is_file() and latest.is_file() and artifact != latest
    persisted_text = latest.read_text(encoding="utf-8")
    persisted = json.loads(persisted_text)
    assert "secret" not in persisted_text
    assert "secret" not in persisted["final_url"]
    assert "%5BREDACTED%5D" in persisted["final_url"]
    registry = tmp_path / ".runtime/ui/extensions.json"
    assert token not in registry.read_text(encoding="utf-8")
    assert registry.stat().st_mode & 0o777 == 0o600


def test_extension_capture_rejects_private_page_data(tmp_path: Path) -> None:
    client, _ = ui_client(tmp_path)
    origin = "chrome-extension://abcdefghijklmnopabcdefghijklmnop"
    token = "paired-token"
    registry = tmp_path / ".runtime/ui/extensions.json"
    registry.parent.mkdir(parents=True)
    registry.write_text(
        json.dumps({"clients": [{"id": "client", "origin": origin, "token_hash": hashlib.sha256(token.encode()).hexdigest(), "expires_at": "2999-01-01T00:00:00+00:00"}]}),
        encoding="utf-8",
    )
    capture = browser_capture()
    capture["cookies"] = "private"
    capture["source"]["cookie_header"] = "private"
    with client:
        response = client.post(
            "/api/v1/extension/projects/store/captures",
            headers={"Origin": origin, "Authorization": f"Bearer {token}"},
            json={"capture": capture},
        )
    assert response.status_code == 422
    assert "cookies" in response.text
    assert "cookie_header" in response.text


def test_extension_rejects_expired_token_and_oversized_capture(tmp_path: Path) -> None:
    client, _ = ui_client(tmp_path)
    origin = "chrome-extension://abcdefghijklmnopabcdefghijklmnop"
    token = "paired-token"
    registry = tmp_path / ".runtime/ui/extensions.json"
    registry.parent.mkdir(parents=True)
    client_record = {"id": "client", "origin": origin, "token_hash": hashlib.sha256(token.encode()).hexdigest(), "expires_at": "2020-01-01T00:00:00+00:00"}
    registry.write_text(json.dumps({"clients": [client_record]}), encoding="utf-8")
    headers = {"Origin": origin, "Authorization": f"Bearer {token}"}
    with client:
        assert client.get("/api/v1/extension/projects", headers=headers).status_code == 401
        client_record["expires_at"] = "2999-01-01T00:00:00+00:00"
        registry.write_text(json.dumps({"clients": [client_record]}), encoding="utf-8")
        oversized = client.post(
            "/api/v1/extension/projects/store/captures",
            headers=headers,
            content=b"x" * (2 * 1024 * 1024 + 1025),
        )
    assert oversized.status_code == 413


def test_codex_launch_timeout_reaps_process_and_throttles(tmp_path: Path, monkeypatch) -> None:
    client, _ = ui_client(tmp_path)
    origin = "chrome-extension://abcdefghijklmnopabcdefghijklmnop"
    token = "paired-token"
    registry = tmp_path / ".runtime/ui/extensions.json"
    registry.parent.mkdir(parents=True)
    registry.write_text(
        json.dumps({"clients": [{"id": "client", "origin": origin, "token_hash": hashlib.sha256(token.encode()).hexdigest(), "expires_at": "2999-01-01T00:00:00+00:00"}]}),
        encoding="utf-8",
    )

    class HangingProcess:
        returncode = None
        terminated = False

        async def wait(self):
            if not self.terminated:
                raise TimeoutError
            self.returncode = -15

        def terminate(self):
            self.terminated = True

        def kill(self):
            self.returncode = -9

    process = HangingProcess()

    async def create_process(*args, **kwargs):
        return process

    monkeypatch.setattr("seo_workbench.ui.asyncio.create_subprocess_exec", create_process)
    headers = {"Origin": origin, "Authorization": f"Bearer {token}"}
    with client:
        first = client.post("/api/v1/extension/open-codex", headers=headers)
        second = client.post("/api/v1/extension/open-codex", headers=headers)
    assert first.status_code == 504
    assert process.terminated is True
    assert second.status_code == 429


def test_ui_bootstrap_preserves_project_and_serves_built_frontend(tmp_path: Path) -> None:
    frontend = tmp_path / "dist"
    frontend.mkdir()
    (frontend / "index.html").write_text("<main>Built workbench</main>", encoding="utf-8")
    app = create_app(
        token="secret",
        projects_root=tmp_path / "projects",
        runtime_dir=tmp_path / ".runtime/ui",
        frontend_dir=frontend,
        watch_files=False,
    )
    with TestClient(app) as client:
        boot = client.get("/?token=secret&project=store", follow_redirects=False)
        assert boot.headers["location"] == "/?project=store"
        client.cookies.set(COOKIE_NAME, "secret")
        assert "Built workbench" in client.get("/").text


def test_ui_lists_projects_workspace_and_real_evidence(tmp_path: Path) -> None:
    client, project_dir = ui_client(tmp_path)
    performance = {
        "collection_status": "ok",
        "aggregate": {
            "performance_score": {"median": 25},
            "high_variance": True,
            "metrics": {
                "largest-contentful-paint": {"median": 14754.8},
                "total-blocking-time": {"median": 940.5},
                "cumulative-layout-shift": {"median": 0.215},
            },
        },
    }
    diff = {"collection_status": "partial", "summary": {"changes": 11, "regressions": 2, "improvements": 5}}
    for relative, payload in (("audits/performance/latest.json", performance), ("audits/diffs/latest.json", diff)):
        path = project_dir / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(payload), encoding="utf-8")
    ledger = project_dir / "strategy/seo-changes.jsonl"
    ledger.write_text(
        json.dumps(
            {
                "id": "chg-1",
                "status": "shipped",
                "change_type": "content",
                "changed_at": "2026-07-01",
                "review_date": "2026-07-29",
                "hypothesis": "Improve qualified clicks",
                "urls": ["https://example.com/page"],
            }
        )
        + "\n",
        encoding="utf-8",
    )
    outcome = project_dir / "audits/outcomes/chg-1/latest.json"
    outcome.parent.mkdir(parents=True)
    outcome.write_text(json.dumps({"classification": "winning"}), encoding="utf-8")
    portfolio = project_dir / "audits/content-portfolio/latest.json"
    portfolio.parent.mkdir(parents=True)
    portfolio.write_text(
        json.dumps({"collection_status": "ok", "count": 1, "counts": {"refresh": 1}, "items": [{"id": "rec1", "title": "Refresh", "url": "https://example.com/refresh", "decision": "refresh", "recommendation": "Update it"}]}),
        encoding="utf-8",
    )

    with client:
        projects = client.get("/api/v1/projects").json()
        assert projects["count"] == 1
        workspace = client.get("/api/v1/projects/store/workspace").json()["workspace"]

    assert workspace["project"]["name"] == "Store"
    assert workspace["evidence"]["performance"]["score"] == 25
    assert workspace["evidence"]["diff"]["regressions"] == 2
    assert workspace["changes"]["due"] == 1
    assert workspace["changes"]["items"][0]["classification"] == "winning"
    assert workspace["content"]["portfolio"]["counts"]["refresh"] == 1
    statuses = {item["id"]: item["status"] for item in workspace["evidence"]["items"]}
    assert statuses["crux"] == "needs_key"
    assert statuses["gsc"] == "not_bound"
    assert statuses["backlinks"] == "not_collected"


def test_google_integration_api_stores_crux_key_without_returning_it(tmp_path: Path) -> None:
    client, _ = ui_client(tmp_path)
    secret = "test-crux-key-123456"
    key_path = tmp_path / ".runtime/google/crux-api-key"

    with client:
        before = client.get("/api/v1/projects/store/integrations/google")
        saved = client.put(
            "/api/v1/projects/store/integrations/google/crux",
            json={"api_key": secret},
        )
        after = client.get("/api/v1/projects/store/integrations/google")

    assert before.json()["integration"]["crux"]["status"] == "needs_key"
    assert saved.status_code == 200
    assert secret not in saved.text
    assert key_path.read_text(encoding="utf-8").strip() == secret
    assert key_path.stat().st_mode & 0o777 == 0o600
    assert after.json()["integration"]["crux"] == {
        "status": "ready",
        "configured": True,
        "source": "private_file",
        "removable": True,
    }

    with client:
        removed = client.delete("/api/v1/projects/store/integrations/google/crux")
    assert removed.status_code == 200
    assert not key_path.exists()


def test_google_integration_api_refuses_to_override_environment_key(tmp_path: Path, monkeypatch) -> None:
    client, _ = ui_client(tmp_path)
    monkeypatch.setenv("SEO_WORKBENCH_CRUX_API_KEY", "environment-secret")
    with client:
        status = client.get("/api/v1/projects/store/integrations/google")
        saved = client.put(
            "/api/v1/projects/store/integrations/google/crux",
            json={"api_key": "replacement-key"},
        )
    assert status.json()["integration"]["crux"]["source"] == "environment"
    assert saved.status_code == 409
    assert "environment-secret" not in saved.text


def test_google_integration_api_manages_gsc_profile_and_binding(tmp_path: Path, monkeypatch) -> None:
    client, project_dir = ui_client(tmp_path)
    credential = {"installed": {"client_id": "client-id", "client_secret": "client-secret"}}

    def fake_authenticate(profile: str, *, client_secret=None, service_account_path=None, runtime_root=None, **kwargs):
        directory = gsc_probe.profile_dir(profile, runtime_root=runtime_root)
        directory.mkdir(parents=True, mode=0o700)
        (directory / "client-secret.json").write_text(json.dumps(credential), encoding="utf-8")
        (directory / "token.json").write_text("{}", encoding="utf-8")
        for path in directory.iterdir():
            path.chmod(0o600)
        return {"profile": profile, "credential_type": "oauth"}

    class Credentials:
        valid = True
        refresh_token = "refreshable"
        service_account_email = None

    properties = [{"site_url": "sc-domain:example.com", "permission_level": "siteOwner"}]
    monkeypatch.setattr(gsc_probe, "authenticate", fake_authenticate)
    monkeypatch.setattr(gsc_probe, "load_credentials", lambda profile, **kwargs: Credentials())
    monkeypatch.setattr(
        gsc_probe,
        "list_properties",
        lambda profile="default", **kwargs: {"collection_status": "ok", "properties": properties},
    )

    with client:
        imported = client.post(
            "/api/v1/projects/store/integrations/google/gsc/credentials",
            json={"profile": "default", "credential_type": "oauth", "credential": credential},
        )
        listed = client.post(
            "/api/v1/projects/store/integrations/google/gsc/properties",
            json={"profile": "default"},
        )
        bound = client.put(
            "/api/v1/projects/store/integrations/google/gsc/binding",
            json={"profile": "default", "property": "sc-domain:example.com"},
        )
        blocked_delete = client.delete(
            "/api/v1/projects/store/integrations/google/gsc/profiles/default"
        )

    assert imported.status_code == 200
    assert "client-secret" not in imported.text
    assert listed.json()["properties"] == properties
    assert bound.json()["integration"]["gsc"]["status"] == "ready"
    binding_path = project_dir / ".runtime/integrations/google.json"
    assert binding_path.stat().st_mode & 0o777 == 0o600
    assert blocked_delete.status_code == 409

    with client:
        assert client.delete("/api/v1/projects/store/integrations/google/gsc/binding").status_code == 200
        deleted = client.delete("/api/v1/projects/store/integrations/google/gsc/profiles/default")
    assert deleted.status_code == 200
    assert not (tmp_path / ".runtime/google/profiles/default").exists()


def test_google_credential_management_is_local_only(tmp_path: Path) -> None:
    client, _ = ui_client(tmp_path)
    headers = {
        "host": "seo.nucleus.localhost:8080",
        "origin": "http://seo.nucleus.localhost:8080",
        "x-nucleus-user-id": "operator-1",
    }
    with client:
        response = client.get("/api/v1/projects/store/integrations/google", headers=headers)
    assert response.status_code == 403


def test_shopify_integration_api_verifies_and_stores_write_only_token(tmp_path: Path, monkeypatch) -> None:
    client, project_dir = ui_client(tmp_path)
    secret = "shpat_test_secret_123456"
    calls: list[tuple[str, str]] = []

    def fake_verify(shop_domain: str, access_token: str, timeout: float = 15) -> dict:
        calls.append((shop_domain, access_token))
        return {
            "shop_name": "Example Store",
            "shop_domain": shop_domain,
            "scopes": ["read_content", "read_products", "write_products"],
            "verified_at": "2026-07-28T09:00:00+00:00",
        }

    monkeypatch.setattr(ui_module, "_verify_shopify_credentials", fake_verify)
    with client:
        before = client.get("/api/v1/projects/store/integrations/shopify")
        saved = client.put(
            "/api/v1/projects/store/integrations/shopify/credentials",
            json={"shop_domain": "example-store.myshopify.com", "access_token": secret},
        )
        verified = client.post("/api/v1/projects/store/integrations/shopify/verify")

    assert before.json()["integration"]["status"] == "needs_credentials"
    assert saved.status_code == 200
    assert secret not in saved.text
    status = saved.json()["integration"]
    assert status["shop_name"] == "Example Store"
    assert status["write_scope_count"] == 1
    assert status["secret_visibility"] == "write_only"
    assert calls == [
        ("example-store.myshopify.com", secret),
        ("example-store.myshopify.com", secret),
    ]
    credential_path = project_dir / ".runtime/integrations/shopify.json"
    assert json.loads(credential_path.read_text(encoding="utf-8"))["access_token"] == secret
    assert credential_path.stat().st_mode & 0o777 == 0o600
    assert verified.status_code == 200
    assert secret not in verified.text

    with client:
        removed = client.delete("/api/v1/projects/store/integrations/shopify/credentials")
    assert removed.status_code == 200
    assert removed.json()["integration"]["status"] == "needs_credentials"
    assert not credential_path.exists()


def test_shopify_integration_rejects_non_shopify_domain_before_network(tmp_path: Path, monkeypatch) -> None:
    client, _ = ui_client(tmp_path)
    monkeypatch.setattr(ui_module, "_verify_shopify_credentials", lambda *args, **kwargs: (_ for _ in ()).throw(AssertionError("network should not run")))
    with client:
        response = client.put(
            "/api/v1/projects/store/integrations/shopify/credentials",
            json={"shop_domain": "example.com", "access_token": "shpat_test_secret"},
        )
    assert response.status_code == 400
    assert "myshopify.com" in response.json()["detail"]


def test_shopify_crawler_access_is_stored_write_only_and_scoped_to_project_host(tmp_path: Path) -> None:
    client, project_dir = ui_client(tmp_path)
    signature = "sig1=:private-signature:"
    signature_input = 'sig1=("@authority" "signature-agent");keyid="private-key";expires=4102444800'
    payload = {
        "domain_host": "example.com",
        "signature": signature,
        "signature_input": signature_input,
        "signature_agent": '"https://shopify.com"',
        "expires_at": "2030-01-01T00:00:00+00:00",
    }
    with client:
        saved = client.put("/api/v1/projects/store/integrations/shopify/crawler-access", json=payload)
        status = client.get("/api/v1/projects/store/integrations/shopify")

    assert saved.status_code == 200
    assert signature not in saved.text
    assert signature_input not in saved.text
    crawler = saved.json()["integration"]["crawler_access"]
    assert crawler["status"] == "ready"
    assert crawler["domain_host"] == "example.com"
    assert status.json()["integration"]["crawler_access"]["expires_at"].startswith("2030-01-01")
    crawler_path = project_dir / ".runtime/integrations/shopify-crawler.json"
    assert json.loads(crawler_path.read_text(encoding="utf-8"))["signature"] == signature
    assert crawler_path.stat().st_mode & 0o777 == 0o600

    with client:
        removed = client.delete("/api/v1/projects/store/integrations/shopify/crawler-access")
    assert removed.status_code == 200
    assert not crawler_path.exists()


def test_shopify_credential_management_is_local_only(tmp_path: Path) -> None:
    client, _ = ui_client(tmp_path)
    headers = {
        "host": "seo.nucleus.localhost:8080",
        "origin": "http://seo.nucleus.localhost:8080",
        "x-nucleus-user-id": "operator-1",
    }
    with client:
        response = client.get("/api/v1/projects/store/integrations/shopify", headers=headers)
    assert response.status_code == 403


def test_dataforseo_integration_verifies_and_stores_write_only_credentials(tmp_path: Path, monkeypatch) -> None:
    client, project_dir = ui_client(tmp_path)
    api_login = "api@example.com"
    api_password = "private-api-password"
    calls: list[tuple[str, str]] = []

    def fake_verify(login: str, password: str, timeout: float = 15) -> dict:
        calls.append((login, password))
        return {"verified_at": "2026-08-19T08:00:00+00:00"}

    monkeypatch.setattr(ui_module, "_verify_dataforseo_credentials", fake_verify)
    with client:
        before = client.get("/api/v1/projects/store/integrations/dataforseo")
        saved = client.put(
            "/api/v1/projects/store/integrations/dataforseo/credentials",
            json={"api_login": api_login, "api_password": api_password},
        )

    assert before.json()["integration"]["status"] == "needs_credentials"
    assert saved.status_code == 200
    assert api_login not in saved.text
    assert api_password not in saved.text
    assert saved.json()["integration"] == {
        "access": "local_only",
        "status": "ready",
        "configured": True,
        "source": "private_file",
        "verified_at": "2026-08-19T08:00:00+00:00",
        "removable": True,
        "secret_visibility": "write_only",
        "transport": "rest_v3",
        "billing": "metered",
    }
    assert calls == [(api_login, api_password)]
    credential_path = project_dir / ".runtime/integrations/dataforseo.json"
    assert json.loads(credential_path.read_text(encoding="utf-8"))["api_password"] == api_password
    assert credential_path.stat().st_mode & 0o777 == 0o600

    with client:
        removed = client.delete("/api/v1/projects/store/integrations/dataforseo/credentials")
    assert removed.status_code == 200
    assert removed.json()["integration"]["status"] == "needs_credentials"
    assert not credential_path.exists()


def test_dataforseo_keyword_collection_requires_confirmation_and_uses_fixed_scope(tmp_path: Path, monkeypatch) -> None:
    client, _ = ui_client(tmp_path)
    calls: list[tuple[str, int, str]] = []

    def fake_collect(project_dir: Path, keyword: str, location_code: int, language_code: str) -> dict:
        calls.append((keyword, location_code, language_code))
        return {"ok": True, "keyword": keyword, "cost_usd": 0.004, "generated_at": "2026-08-19T08:00:00Z"}

    monkeypatch.setattr(ui_module, "_collect_dataforseo_keyword", fake_collect)
    with client:
        rejected = client.post(
            "/api/v1/projects/store/keywords/dataforseo",
            json={"keyword": "desk shelf", "location_code": 2840, "language_code": "en", "confirm": False},
        )
        collected = client.post(
            "/api/v1/projects/store/keywords/dataforseo",
            json={"keyword": "desk shelf", "location_code": 2840, "language_code": "en", "confirm": True},
        )

    assert rejected.status_code == 422
    assert collected.status_code == 200
    assert collected.json()["cost_usd"] == 0.004
    assert calls == [("desk shelf", 2840, "en")]


def test_dataforseo_keyword_collection_keeps_normalized_metrics_and_organic_serp(tmp_path: Path, monkeypatch) -> None:
    _, project_dir = ui_client(tmp_path)

    def fake_post(project_dir: Path, endpoint: str, task: dict, timeout: float = 45) -> dict:
        if "keyword_overview" in endpoint:
            return {"status_code": 20000, "tasks": [{"status_code": 20000, "cost": .001, "result": [{"items": [{"keyword_info": {"search_volume": 3600, "cpc": .7, "competition": .62, "competition_level": "MEDIUM", "monthly_searches": [{"year": 2026, "month": 7, "search_volume": 3600}]}, "search_intent_info": {"main_intent": "commercial"}}]}]}]}
        return {"status_code": 20000, "tasks": [{"status_code": 20000, "cost": .003, "result": [{"se_results_count": 1000, "item_types": ["organic", "people_also_ask"], "items": [{"type": "people_also_ask"}, {"type": "organic", "rank_group": 1, "title": "Desk Shelf", "url": "https://example.com/desk-shelf", "domain": "example.com", "description": "Result"}]}]}]}

    monkeypatch.setattr(ui_module, "_dataforseo_post", fake_post)
    result = ui_module._collect_dataforseo_keyword(project_dir, " Desk Shelf ", 2840, "en")
    artifact = json.loads((project_dir / "audits/keywords/dataforseo/latest.json").read_text(encoding="utf-8"))

    assert result["cost_usd"] == .004
    assert artifact["items"][0]["keyword"] == "desk shelf"
    assert artifact["items"][0]["intent"] == "commercial"
    assert artifact["items"][0]["serp"]["results"] == [{"rank": 1, "title": "Desk Shelf", "url": "https://example.com/desk-shelf", "domain": "example.com", "description": "Result"}]


def test_ui_tutorial_registry_points_to_existing_files() -> None:
    from seo_workbench.ui import DEFAULT_TUTORIALS_DIR, TUTORIALS

    slugs = [tutorial["slug"] for tutorial in TUTORIALS]
    assert len(slugs) == len(set(slugs))
    assert "statistics-principles" in slugs
    for tutorial in TUTORIALS:
        assert tutorial["filename"].endswith(".md")
        assert (DEFAULT_TUTORIALS_DIR / tutorial["filename"]).is_file(), tutorial["filename"]


def test_ui_serves_allowlisted_tutorials_as_read_only_content(tmp_path: Path) -> None:
    client, _ = ui_client(tmp_path)
    with client:
        listed = client.get("/api/v1/tutorials")
        opened = client.get("/api/v1/tutorials/seo-foundations")
        missing = client.get("/api/v1/tutorials/not-allowlisted")
        mutation = client.put("/api/v1/tutorials/seo-foundations", json={"content": "changed"})

    assert listed.status_code == 200
    assert listed.json()["count"] == 1
    assert listed.json()["tutorials"][0]["source"] == "SEO基础知识与证据模型.md"
    assert opened.status_code == 200
    assert opened.json()["tutorial"]["content"].startswith("# SEO Foundations")
    assert opened.json()["tutorial"]["revision"]
    assert missing.status_code == 404
    assert mutation.status_code == 405


def test_markdown_api_saves_with_revision_and_rejects_stale_write(tmp_path: Path) -> None:
    client, project_dir = ui_client(tmp_path)
    path = "strategy/cluster-plan.md"
    with client:
        opened = client.get(f"/api/v1/projects/store/files/{path}").json()["file"]
        saved = client.put(
            f"/api/v1/projects/store/files/{path}",
            json={"content": "# User edit\n", "base_revision": opened["revision"]},
        )
        assert saved.status_code == 200
        saved_revision = saved.json()["file"]["revision"]

        (project_dir / path).write_text("# Agent edit\n", encoding="utf-8")
        conflict = client.put(
            f"/api/v1/projects/store/files/{path}",
            json={"content": "# Stale user edit\n", "base_revision": saved_revision},
        )

    assert conflict.status_code == 409
    assert conflict.json()["detail"]["code"] == "revision_conflict"
    assert (project_dir / path).read_text(encoding="utf-8") == "# Agent edit\n"


def test_markdown_api_rejects_runtime_non_markdown_and_traversal_paths(tmp_path: Path) -> None:
    client, _ = ui_client(tmp_path)
    with client:
        assert client.get("/api/v1/projects/store/files/.runtime/token.md").status_code == 400
        assert client.get("/api/v1/projects/store/files/audits/latest.json").status_code == 400
        assert client.get("/api/v1/projects/store/files/%2E%2E/secret.md").status_code in {400, 404}


def test_reports_api_lists_archive_and_serves_weekly_files(tmp_path: Path) -> None:
    client, project_dir = ui_client(tmp_path)
    reports = project_dir / "reports"
    reports.mkdir(exist_ok=True)
    (reports / "2026_week_34_work_done.md").write_text(
        "# Store 周报 · 2026 Week 34（08-17 → 08-23）\n"
        "\n"
        "## 速览\n\n- [x] 完成 A\n- [ ] 待办 B\n\n"
        "## 遗留工作\n\n- [ ] **任务 D**：原因；后续：2026-09-11 再评估\n",
        encoding="utf-8",
    )
    (reports / "20260817_tech_theme-fix-handoff.md").write_text("# Handoff\n", encoding="utf-8")

    with client:
        payload = client.get("/api/v1/projects/store/reports").json()

    assert payload["ok"] is True
    assert payload["latest_week"] == {"year": 2026, "week": 34}
    weekly = payload["weekly"][0]
    assert weekly["checked"] == 1
    assert weekly["total"] == 2
    assert weekly["carry_over"] == 1
    assert weekly["follow_ups"][0]["date"] == "2026-09-11"
    assert payload["categories"]["tech"][0]["topic"] == "theme-fix-handoff"

    with client:
        opened = client.get("/api/v1/projects/store/files/reports/2026_week_34_work_done.md")
    assert opened.status_code == 200
    assert "周报" in opened.json()["file"]["content"]


def test_reports_new_action_runs_scaffold_command(tmp_path: Path, monkeypatch) -> None:
    client, _ = ui_client(tmp_path)
    captured: list[dict[str, object]] = []

    def fake_start_command(self, project_id: str, action: str, command_args: tuple[str, ...]) -> dict:
        captured.append({"action": action, "command": command_args})
        return {"id": "job3", "project_id": project_id, "action": action, "status": "queued", "created_at": "2026-07-29T00:00:00Z", "started_at": None, "finished_at": None, "exit_code": None, "output": "queued"}

    monkeypatch.setattr(ui_module.JobManager, "start_command", fake_start_command)
    with client:
        started = client.post("/api/v1/projects/store/content/actions", json={"action": "reports-new"})

    assert started.status_code == 202
    assert started.json()["job"]["action"] == "content:reports-new"
    assert captured == [{"action": "content:reports-new", "command": ("reports", "new", "--json")}]


def test_ui_updates_workflow_through_shared_state_mutation(tmp_path: Path) -> None:
    client, project_dir = ui_client(tmp_path)
    before = state.load_state(project_dir)
    phase, step = state.current_step(before)
    assert step is not None
    with client:
        response = client.post(
            "/api/v1/projects/store/workflow",
            json={"action": "start", "step_id": step["id"]},
        )
    assert response.status_code == 200
    updated = state.load_state(project_dir)
    assert updated["phases"][phase]["steps"][0]["status"] in {"done", "in_progress"}
    assert next(item for item in updated["phases"][phase]["steps"] if item["id"] == step["id"])["status"] == "in_progress"


def test_ui_exposes_content_queue_and_updates_status(tmp_path: Path) -> None:
    client, project_dir = ui_client(tmp_path)
    data = state.load_state(project_dir)
    data["contentQueue"] = [
        {
            "id": "rec1",
            "status": "scheduled",
            "title": "Ready",
            "live_url": "https://example.com/blogs/articles/ready",
            "scheduled_at": "2026-07-01T00:00:00Z",
        }
    ]
    state.save_state(data, project_dir)

    with client:
        queue = client.get("/api/v1/projects/store/content/queue")
        updated = client.put(
            "/api/v1/projects/store/content/queue/rec1/status",
            json={"status": "indexed", "note": "checked"},
        )
        rejected = client.put(
            "/api/v1/projects/store/content/queue/rec1/status",
            json={"status": "not-real"},
        )

    assert queue.status_code == 200
    assert queue.json()["queue"]["counts"]["scheduled"] == 1
    assert queue.json()["queue"]["due_for_indexing"]["count"] == 1
    assert updated.status_code == 200
    assert updated.json()["item"]["status"] == "indexed"
    assert state.load_state(project_dir)["contentQueue"][0]["note"] == "checked"
    assert rejected.status_code == 400


def test_ui_content_actions_are_fixed_and_project_scoped(tmp_path: Path, monkeypatch) -> None:
    client, project_dir = ui_client(tmp_path)
    data = state.load_state(project_dir)
    data["contentQueue"] = [{"id": "rec1", "status": "drafting", "title": "Draft"}]
    state.save_state(data, project_dir)
    captured: dict[str, object] = {}

    def fake_start_command(self, project_id: str, action: str, command_args: tuple[str, ...]) -> dict:
        captured.update({"project_id": project_id, "action": action, "command": command_args})
        return {
            "id": "job1",
            "project_id": project_id,
            "action": action,
            "status": "queued",
            "created_at": "2026-07-29T00:00:00Z",
            "started_at": None,
            "finished_at": None,
            "exit_code": None,
            "output": "",
        }

    monkeypatch.setattr(ui_module.JobManager, "start_command", fake_start_command)
    with client:
        started = client.post("/api/v1/projects/store/content/actions", json={"action": "brief", "item_id": "rec1"})
        unsupported = client.post("/api/v1/projects/store/content/actions", json={"action": "shell", "item_id": "rec1"})
        missing_item = client.post("/api/v1/projects/store/content/actions", json={"action": "brief", "item_id": "missing"})

    assert started.status_code == 202
    assert started.json()["job"]["action"] == "content:brief"
    assert captured == {"project_id": "store", "action": "content:brief", "command": ("content", "brief", "rec1", "--json")}
    assert unsupported.status_code == 400
    assert missing_item.status_code == 400


def test_ui_content_actions_require_confirm_and_safe_paths(tmp_path: Path, monkeypatch) -> None:
    client, project_dir = ui_client(tmp_path)
    data = state.load_state(project_dir)
    data["contentQueue"] = [{"id": "rec1", "status": "approved", "title": "Ready"}]
    state.save_state(data, project_dir)
    (project_dir / "content/drafts").mkdir(parents=True, exist_ok=True)
    (project_dir / "content/drafts/draft.json").write_text("{}", encoding="utf-8")
    captured: list[dict[str, object]] = []

    def fake_start_command(self, project_id: str, action: str, command_args: tuple[str, ...]) -> dict:
        captured.append({"action": action, "command": command_args})
        return {
            "id": "job2",
            "project_id": project_id,
            "action": action,
            "status": "queued",
            "created_at": "2026-07-29T00:00:00Z",
            "started_at": None,
            "finished_at": None,
            "exit_code": None,
            "output": "queued",
        }

    monkeypatch.setattr(ui_module.JobManager, "start_command", fake_start_command)
    with client:
        unconfirmed = client.post(
            "/api/v1/projects/store/content/actions",
            json={"action": "publish", "item_id": "rec1", "blog_id": "100"},
        )
        bad_path = client.post(
            "/api/v1/projects/store/content/actions",
            json={"action": "import-draft", "project_relative_path": "../draft.json"},
        )
        started = client.post(
            "/api/v1/projects/store/content/actions",
            json={"action": "publish", "item_id": "rec1", "blog_id": "100", "confirm": True, "allow_warnings": True},
        )
        confirmed = client.post(
            "/api/v1/projects/store/content/actions",
            json={"action": "publish", "item_id": "rec1", "blog_id": "100", "confirm": True},
        )
        imported = client.post(
            "/api/v1/projects/store/content/actions",
            json={"action": "import-draft", "project_relative_path": "content/drafts/draft.json"},
        )

    assert unconfirmed.status_code == 400
    assert bad_path.status_code == 400
    assert started.status_code == 400
    assert confirmed.status_code == 202
    assert "--confirm" in captured[0]["command"]
    assert "--allow-warnings" not in captured[0]["command"]
    assert imported.status_code == 202
    assert captured[1]["action"] == "content:import-draft"
    assert str(project_dir / "content/drafts/draft.json") in captured[1]["command"]


def test_ui_content_runs_gsc_inspection_then_confirmed_index_notification(tmp_path: Path, monkeypatch) -> None:
    client, _project_dir = ui_client(tmp_path)
    captured: list[tuple[str, ...]] = []

    def fake_start_command(self, project_id: str, action: str, command_args: tuple[str, ...]) -> dict:
        captured.append(command_args)
        return {
            "id": f"job{len(captured)}",
            "project_id": project_id,
            "action": action,
            "status": "queued",
            "created_at": "2026-08-03T00:00:00Z",
            "started_at": None,
            "finished_at": None,
            "exit_code": None,
            "output": "",
        }

    monkeypatch.setattr(ui_module.JobManager, "start_command", fake_start_command)
    with client:
        inspected = client.post("/api/v1/projects/store/content/actions", json={"action": "gsc-inspect", "limit": 5})
        unconfirmed = client.post("/api/v1/projects/store/content/actions", json={"action": "index-status", "role": "seo"})
        notified = client.post(
            "/api/v1/projects/store/content/actions",
            json={"action": "index-status", "role": "seo", "profile": "hexcal-seo", "confirm": True},
        )

    assert inspected.status_code == 202
    assert unconfirmed.status_code == 400
    assert notified.status_code == 202
    assert captured[0] == ("gsc", "inspect", "--limit", "5", "--json")
    assert captured[1] == (
        "content",
        "index-status",
        "--notify-role",
        "seo",
        "--profile",
        "hexcal-seo",
        "--confirm",
        "--json",
    )


def test_ui_runs_only_whitelisted_project_jobs(tmp_path: Path, monkeypatch) -> None:
    client, _ = ui_client(tmp_path)
    monkeypatch.setitem(ACTION_COMMANDS, "evidence", ("projects", "--json"))
    with client:
        assert client.post("/api/v1/projects/store/actions", json={"action": "unknown"}).status_code == 400
        started = client.post("/api/v1/projects/store/actions", json={"action": "evidence"})
        assert started.status_code == 202
        job_id = started.json()["job"]["id"]
        job = started.json()["job"]
        for _ in range(100):
            jobs = client.get("/api/v1/projects/store/jobs").json()["jobs"]
            job = next(item for item in jobs if item["id"] == job_id)
            if job["status"] not in {"queued", "running"}:
                break
            time.sleep(0.01)
    assert job["status"] == "succeeded"
    assert job["exit_code"] == 0


def test_ui_technical_audit_crawls_subdomains() -> None:
    assert ACTION_COMMANDS["tech-audit"] == ("tech-audit", "run", "--include-subdomains", "--json")
    assert ACTION_COMMANDS["pages-refresh"] == ("pages", "refresh", "--json")
    assert ACTION_COMMANDS["statistics-collect"] == ("statistics", "collect", "--json")


def test_ui_serves_statistics_evidence_bundle(tmp_path: Path) -> None:
    client, project_dir = ui_client(tmp_path)
    portfolio = project_dir / "audits/content-portfolio/latest.json"
    portfolio.parent.mkdir(parents=True, exist_ok=True)
    portfolio.write_text(
        json.dumps(
            {
                "schema_version": "content-portfolio-v4",
                "collection_status": "ok",
                "generated_at": "2026-08-17T00:00:00Z",
                "count": 3,
                "comparability": {"comparable": True, "issues": []},
                "source_status": {"gsc": "ok"},
                "statistics": {"query_portfolio": {"current": {"effective_queries": 4.9}}},
            }
        )
    )
    coverage = project_dir / "audits/statistics/history/coverage.json"
    coverage.parent.mkdir(parents=True, exist_ok=True)
    coverage.write_text(
        json.dumps(
            {
                "schema_version": "statistics-coverage-v1",
                "sources": {"gsc": ["2026-07-01", "2026-07-02"], "business": ["2026-07-01"]},
            }
        )
    )
    with client:
        payload = client.get("/api/v1/projects/store/statistics").json()
    assert payload["portfolio"]["collection_status"] == "ok"
    assert payload["portfolio"]["statistics"]["query_portfolio"]["current"]["effective_queries"] == 4.9
    assert payload["coverage"]["sources"]["gsc"] == {"count": 2, "first": "2026-07-01", "last": "2026-07-02"}
    assert payload["coverage"]["sources"]["business"] == {"count": 1, "first": "2026-07-01", "last": "2026-07-01"}
    assert payload["regimes"]["count"] == 0


def test_ui_statistics_evidence_defaults_when_missing(tmp_path: Path) -> None:
    client, _ = ui_client(tmp_path)
    with client:
        payload = client.get("/api/v1/projects/store/statistics").json()
    assert payload["portfolio"]["collection_status"] == "not_collected"
    assert payload["coverage"]["status"] == "not_collected"
    assert payload["regimes"]["count"] == 0


def test_ui_backlink_workspace_defaults_when_missing(tmp_path: Path) -> None:
    client, _ = ui_client(tmp_path)
    with client:
        response = client.get("/api/v1/projects/store/backlinks/view", params={"status": "active"})
    assert response.status_code == 200
    assert response.json()["collection_status"] == "not_collected"
    assert response.json()["pagination"]["total"] == 0


def test_ui_exposes_paginated_page_workspace_views(tmp_path: Path) -> None:
    client, project_dir = ui_client(tmp_path)
    url = "https://example.com/products/desk"
    portfolio = project_dir / "audits/content-portfolio/latest.json"
    portfolio.parent.mkdir(parents=True, exist_ok=True)
    portfolio.write_text(
        json.dumps(
            {
                "schema_version": "content-portfolio-v2",
                "collection_status": "ok",
                "generated_at": "2026-08-09T00:00:00Z",
                "items": [
                    {
                        "row_key": url,
                        "url": url,
                        "title": "Desk",
                        "page_type": "product",
                        "sources": {"gsc_current": True},
                        "decision": "refresh",
                        "recommendation": "Refresh intent coverage.",
                        "metrics": {"current": {"clicks": 5, "impressions": 200, "ctr": 0.025, "position": 8}},
                        "technical": {"issue_count": 0},
                        "multiple_page_queries": [
                            {
                                "query": "desk setup",
                                "owner_count": 2,
                                "total_impressions": 120,
                                "owners": [{"url": url, "impressions": 80}],
                            }
                        ],
                    }
                ],
            }
        ),
        encoding="utf-8",
    )

    with client:
        actions = client.get("/api/v1/projects/store/pages/view", params={"dataset": "actions", "group": "now"})
        pages = client.get("/api/v1/projects/store/pages/view", params={"dataset": "pages", "page_type": "product"})
        conflicts = client.get("/api/v1/projects/store/pages/view", params={"dataset": "query_conflicts", "q": "desk", "sort": "total_impressions"})
        detail = client.get("/api/v1/projects/store/pages/view/detail", params={"dataset": "pages", "key": url})
        invalid = client.get("/api/v1/projects/store/pages/view", params={"dataset": "pages", "sort": "urgency"})

    assert actions.status_code == 200
    assert actions.json()["summary"]["groups"] == {"now": 1}
    assert pages.json()["rows"][0]["impressions"] == 200
    assert conflicts.json()["rows"][0]["query"] == "desk setup"
    assert detail.json()["row"]["row_key"] == url
    assert invalid.status_code == 400


def test_ui_page_workspace_light_actions_preserve_domain_rules(tmp_path: Path, monkeypatch) -> None:
    client, project_dir = ui_client(tmp_path)
    url = "https://example.com/products/desk"
    issue = {
        "fingerprint": "fp-1",
        "rule_id": "MISSING_H1",
        "title": "Missing H1",
        "severity": "high",
        "category": "content",
        "url": url,
        "priority": {"score": 70, "tier": "high"},
        "remediation_guidance": "Add an H1.",
    }
    sync_issue_register(project_dir, [issue], [], run_id="run-1", verification_allowed=False)
    analytics = {
        "collection_status": "ok",
        "windows": {
            "previous": {"page": {"request": {"startDate": "2026-06-01", "endDate": "2026-06-28"}, "rows": [{"keys": [url], "clicks": 5, "impressions": 100, "ctr": 0.05, "position": 8}]}},
            "current": {"page": {"request": {"startDate": "2026-07-01", "endDate": "2026-07-29"}, "rows": [{"keys": [url], "clicks": 10, "impressions": 120, "ctr": 0.083, "position": 6}]}, "query_page": {"rows": []}},
        },
    }
    gsc = project_dir / "audits/gsc/search-analytics/latest.json"
    gsc.parent.mkdir(parents=True, exist_ok=True)
    gsc.write_text(json.dumps(analytics), encoding="utf-8")
    with client:
        external = client.post("/api/v1/projects/store/seo-changes", json={"urls": ["https://outside.example/page"], "change_type": "content", "hypothesis": "Test", "metrics": ["clicks"]})
        created = client.post("/api/v1/projects/store/seo-changes", json={"urls": [url], "change_type": "content", "hypothesis": "Better copy improves clicks.", "metrics": ["clicks"], "changed_at": "2026-06-29", "review_date": "2026-07-29"})
        change_id = created.json()["change"]["id"]
        listed = client.get("/api/v1/projects/store/seo-changes")
        compatible = client.post(f"/api/v1/projects/store/seo-changes/{change_id}/evaluate", json={})
        evaluated = client.post(f"/api/v1/projects/store/seo-changes/{change_id}/evaluate-job", json={})
        assert list_changes(project_dir)["changes"][0]["status"] == "shipped"
        accepted_without_note = client.put("/api/v1/projects/store/tech-audit/issues/fp-1/status", json={"status": "accepted", "owner": "seo"})
        accepted = client.put("/api/v1/projects/store/tech-audit/issues/fp-1/status", json={"status": "accepted", "owner": "seo", "note": "Intentional exception"})
        reviewed = client.put(f"/api/v1/projects/store/seo-changes/{change_id}/status", json={"status": "reviewed", "note": "Checked comparable windows"})

    assert external.status_code == 400
    assert created.status_code == 201
    assert listed.status_code == 200
    assert listed.json()["changes"][0]["id"] == change_id
    assert compatible.status_code == 200
    assert compatible.json()["report"]["change"]["id"] == change_id
    assert "/audits/outcomes/" in compatible.json()["path"]
    assert evaluated.status_code == 202
    assert evaluated.json()["job"]["action"] == f"seo-change:evaluate:{change_id}"
    assert list_changes(project_dir)["changes"][0]["status"] == "reviewed"
    assert accepted_without_note.status_code == 400
    assert accepted.json()["issue"]["owner"] == "seo"
    assert list_issue_register(project_dir)["issues"][0]["status"] == "accepted"
    assert reviewed.status_code == 200


def test_ui_change_evaluation_rejects_multi_url_refresh(tmp_path: Path) -> None:
    client, project_dir = ui_client(tmp_path)
    change = record_change(
        project_dir,
        urls=["https://example.com/products/desk", "https://example.com/products/chair"],
        change_type="content",
        hypothesis="Improve clicks.",
        metrics=["clicks"],
    )
    with client:
        response = client.post(f"/api/v1/projects/store/seo-changes/{change['id']}/evaluate-job", json={})

    assert response.status_code == 400
    assert response.json()["detail"] == "UI outcome evaluation supports one URL; use the CLI for multi-URL changes"


def test_ui_reads_latest_change_outcome(tmp_path: Path) -> None:
    client, project_dir = ui_client(tmp_path)
    change = record_change(
        project_dir,
        urls=["https://example.com/products/desk"],
        change_type="content",
        hypothesis="Improve clicks.",
        metrics=["clicks"],
    )
    outcome = project_dir / f"audits/outcomes/{change['id']}/latest.json"
    outcome.parent.mkdir(parents=True)
    outcome.write_text(json.dumps({"classification": "insufficient_data"}), encoding="utf-8")

    with client:
        response = client.get(f"/api/v1/projects/store/seo-changes/{change['id']}/outcome")

    assert response.status_code == 200
    assert response.json()["report"]["classification"] == "insufficient_data"


def test_ui_exposes_tech_audit_queue_schedule_and_safe_recrawl_command(tmp_path: Path, monkeypatch) -> None:
    client, project_dir = ui_client(tmp_path)
    run_dir = project_dir / "audits/tech-audit/runs/run-1/normalized"
    run_dir.mkdir(parents=True)
    (run_dir.parent / "run.json").write_text(json.dumps({"run_id": "run-1", "kind": "tech-audit", "status": "running", "started_at": "2026-08-03T00:00:00+00:00", "config": {"max_urls": 10}, "phase": "crawl", "processed_urls": 3, "discovered_urls": 7}), encoding="utf-8")
    inventory = [
        {"page_id": "page_404", "url": "https://example.com/missing", "final_url": "https://example.com/missing", "status_code": 404, "indexability": {"status": "unknown", "indexable": None}, "title": "", "meta_description": "", "meta_keywords": "", "h1": [], "h2": [], "inlink_count": 2, "crawl_depth": 1, "response_time_ms": 20, "response_size": 10},
        {"page_id": "page_200", "url": "https://example.com/", "final_url": "https://example.com/", "status_code": 200, "indexability": {"status": "indexable", "indexable": True}, "title": "Home", "meta_description": "Home", "meta_keywords": "", "h1": ["Home"], "h2": [], "inlink_count": 0, "crawl_depth": 0, "response_time_ms": 20, "response_size": 10},
        {"page_id": "page_external", "url": "https://cdn.example.net/asset", "final_url": "https://cdn.example.net/asset", "status_code": 200, "host_relation": "external", "indexability": {"status": "unknown", "indexable": None}, "title": "", "meta_description": "", "meta_keywords": "", "h1": [], "h2": [], "inlink_count": 1, "crawl_depth": 1, "response_time_ms": 20, "response_size": 10},
    ]
    (run_dir / "inventory.jsonl").write_text("".join(json.dumps(row) + "\n" for row in inventory), encoding="utf-8")
    (run_dir / "link-inventory.jsonl").write_text(
        json.dumps({
            "url": "https://external.example/path",
            "internal_external": "External",
            "host_relation": "external",
            "status_code": None,
            "final_url": "",
            "indexability": {"status": "not_crawled", "indexable": None},
            "sources": ["https://example.com/"],
            "anchor_texts": ["External"],
            "rel": ["nofollow"],
            "excluded_reason": "external",
        }) + "\n",
        encoding="utf-8",
    )
    (run_dir / "issues.jsonl").write_text(json.dumps({"rule_id": "HTTP_4XX", "url": "https://example.com/missing", "priority": {"score": 60}}) + "\n", encoding="utf-8")
    latest = project_dir / "audits/tech-audit/latest.json"
    latest.parent.mkdir(parents=True, exist_ok=True)
    latest.write_text(json.dumps({"generated_at": "2026-08-03T00:00:00Z", "run_id": "run-1", "collection_status": "ok", "summary": {"pages": 2}, "artifacts": {"inventory_path": "audits/tech-audit/runs/run-1/normalized/inventory.jsonl", "link_inventory_path": "audits/tech-audit/runs/run-1/normalized/link-inventory.jsonl", "issues_path": "audits/tech-audit/runs/run-1/normalized/issues.jsonl"}}), encoding="utf-8")
    set_schedule(project_dir, 60, notify_role="seo", profile="hexcal-seo")
    captured: list[tuple[str, ...]] = []

    def fake_start_command(self, project_id: str, action: str, command_args: tuple[str, ...]) -> dict:
        captured.append(command_args)
        return {"id": "job1", "project_id": project_id, "action": action, "status": "queued", "created_at": "2026-08-03T00:00:00Z", "started_at": None, "finished_at": None, "exit_code": None, "output": ""}

    monkeypatch.setattr(ui_module.JobManager, "start_command", fake_start_command)
    with client:
        view = client.get("/api/v1/projects/store/tech-audit")
        delete_running = client.delete("/api/v1/projects/store/tech-audit/history/run-1")
        pages_view = client.get("/api/v1/projects/store/tech-audit/view", params={"dataset": "pages", "status": "404", "limit": 1})
        links_view = client.get("/api/v1/projects/store/tech-audit/view", params={"dataset": "links"})
        issues_view = client.get("/api/v1/projects/store/tech-audit/view", params={"dataset": "issues", "rule_id": "HTTP_4XX"})
        page_detail = client.get("/api/v1/projects/store/tech-audit/view/detail", params={"dataset": "pages", "key": "https://example.com/missing"})
        invalid_view = client.get("/api/v1/projects/store/tech-audit/view", params={"dataset": "pages", "sort": "severity"})
        schedule = client.put("/api/v1/projects/store/tech-audit/schedule", json={"enabled": True, "every_minutes": 30, "notify_role": "seo", "profile": "hexcal-seo"})
        recrawl = client.post("/api/v1/projects/store/actions", json={"action": "tech-audit-recrawl", "urls": ["https://example.com/missing"]})
        accepted_page = client.post("/api/v1/projects/store/actions", json={"action": "tech-audit-recrawl", "urls": ["https://example.com/"]})
        rejected = client.post("/api/v1/projects/store/actions", json={"action": "tech-audit-recrawl", "urls": ["https://cdn.example.net/asset"]})
        continue_without_queue = client.post("/api/v1/projects/store/actions", json={"action": "tech-audit-continue"})

    assert view.status_code == 200
    assert view.json()["history"][0]["run_id"] == "run-1"
    assert delete_running.status_code == 409
    assert view.json()["summary"]["four_oh_four"] == 1
    assert view.json()["pages"][0]["priority"] == 60
    assert view.json()["run"]["phase"] == "crawl"
    assert view.json()["run"]["processed_urls"] == 3
    assert pages_view.status_code == 200
    assert pages_view.json()["pagination"] == {"offset": 0, "limit": 1, "total": 1}
    assert pages_view.json()["rows"][0]["status_code"] == 404
    assert links_view.status_code == 200
    assert links_view.json()["rows"][0]["excluded_reason"] == "external"
    assert links_view.json()["rows"][0]["crawled"] is False
    assert issues_view.status_code == 200
    assert issues_view.json()["rows"][0]["rule_id"] == "HTTP_4XX"
    assert page_detail.status_code == 200
    assert page_detail.json()["row"]["url"] == "https://example.com/missing"
    assert invalid_view.status_code == 400
    assert schedule.status_code == 200
    assert schedule.json()["schedule"]["every_minutes"] == 30
    assert recrawl.status_code == 202
    assert accepted_page.status_code == 202
    assert rejected.status_code == 400
    assert continue_without_queue.status_code == 400
    assert captured == [
        ("tech-audit", "recrawl", "--url", "https://example.com/missing", "--json"),
        ("tech-audit", "recrawl", "--url", "https://example.com/", "--json"),
    ]


def test_state_mutations_are_serialized_by_project_lock(tmp_path: Path) -> None:
    project_dir = tmp_path / "project"
    state.init_state("general", "Store", "https://example.com", project_dir=project_dir)

    def add_note(number: int) -> None:
        def mutation(data: dict) -> None:
            data.setdefault("concurrency_test", []).append(number)

        state.mutate_state(project_dir, mutation, timeout=5)

    with ThreadPoolExecutor(max_workers=8) as pool:
        list(pool.map(add_note, range(20)))

    assert sorted(state.load_state(project_dir)["concurrency_test"]) == list(range(20))


def test_project_lock_uses_private_runtime_file(tmp_path: Path) -> None:
    lock_root = tmp_path / "locks"
    project_dir = tmp_path / "project"
    with project_lock(project_dir, lock_root=lock_root):
        path = lock_path(project_dir, lock_root)
        assert path.stat().st_mode & 0o777 == 0o600
    assert lock_root.stat().st_mode & 0o777 == 0o700


def test_event_hub_drops_oldest_event_for_slow_subscriber() -> None:
    hub = EventHub()
    queue = hub.subscribe()
    for number in range(101):
        hub.publish({"number": number})
    assert queue.qsize() == 100
    assert queue.get_nowait()["number"] == 1


def test_ui_job_output_is_bounded_and_redacts_common_secret_fields() -> None:
    safe = _safe_job_output('token=abc123 api_key: super-secret\n')
    assert "abc123" not in safe
    assert "super-secret" not in safe
    assert len(_safe_job_output("x" * 70_000).encode("utf-8")) <= 64 * 1024
    assert len(_safe_job_output("测" * 30_000).encode("utf-8")) <= 64 * 1024
