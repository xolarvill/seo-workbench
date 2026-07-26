from __future__ import annotations

import hashlib
import json
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from fastapi.testclient import TestClient

from seo_workbench import state
from seo_workbench.locks import lock_path, project_lock
from seo_workbench.ui import ACTION_COMMANDS, COOKIE_NAME, EventHub, _safe_job_output, create_app


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


def test_extension_pairing_persists_redacted_browser_capture(tmp_path: Path) -> None:
    client, project_dir = ui_client(tmp_path)
    origin = "chrome-extension://abcdefghijklmnopabcdefghijklmnop"
    headers = {"Origin": origin}
    verifier = "v" * 48
    verifier_hash = hashlib.sha256(verifier.encode()).hexdigest()

    with client:
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

        assert client.get(f"/extension/pair/{pairing_id}").status_code == 200
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
        saved = client.post(
            "/api/v1/extension/projects/store/captures",
            headers=authorized,
            json={"capture": browser_capture()},
        )

    assert saved.status_code == 201
    artifact = project_dir / saved.json()["artifact"]
    latest = project_dir / "audits/browser/latest.json"
    assert artifact.is_file() and latest.is_file() and artifact != latest
    persisted = json.loads(latest.read_text(encoding="utf-8"))
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
        json.dumps({"clients": [{"id": "client", "origin": origin, "token_hash": hashlib.sha256(token.encode()).hexdigest()}]}),
        encoding="utf-8",
    )
    capture = browser_capture()
    capture["cookies"] = "private"
    with client:
        response = client.post(
            "/api/v1/extension/projects/store/captures",
            headers={"Origin": origin, "Authorization": f"Bearer {token}"},
            json={"capture": capture},
        )
    assert response.status_code == 400
    assert "cookies" in response.json()["detail"]


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

    with client:
        projects = client.get("/api/v1/projects").json()
        assert projects["count"] == 1
        workspace = client.get("/api/v1/projects/store/workspace").json()["workspace"]

    assert workspace["project"]["name"] == "Store"
    assert workspace["evidence"]["performance"]["score"] == 25
    assert workspace["evidence"]["diff"]["regressions"] == 2
    statuses = {item["id"]: item["status"] for item in workspace["evidence"]["items"]}
    assert statuses["crux"] == "needs_key"
    assert statuses["gsc"] == "not_bound"


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
