from __future__ import annotations

import json
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from fastapi.testclient import TestClient

from seo_workbench import state
from seo_workbench.locks import lock_path, project_lock
from seo_workbench.ui import COOKIE_NAME, EventHub, create_app


def ui_client(tmp_path: Path) -> tuple[TestClient, Path]:
    projects_root = tmp_path / "projects"
    project_dir = projects_root / "store"
    state.init_state("shopify", "Store", "https://example.com", project_dir=project_dir)
    (project_dir / "strategy/cluster-plan.md").write_text("# Original\n", encoding="utf-8")
    app = create_app(
        token="test-token",
        projects_root=projects_root,
        runtime_dir=tmp_path / ".runtime/ui",
        frontend_dir=None,
        watch_files=False,
    )
    client = TestClient(app)
    client.cookies.set(COOKIE_NAME, "test-token")
    return client, project_dir


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
