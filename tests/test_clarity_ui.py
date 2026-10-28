import json

from fastapi.testclient import TestClient

from seo_workbench import clarity, state
from seo_workbench.ui import create_app


def client(tmp_path):
    root = tmp_path / "projects"
    project = root / "store"
    state.init_state("shopify", "Store", "https://example.com", project_dir=project)
    return TestClient(create_app(projects_root=root, runtime_dir=tmp_path / ".runtime/ui", frontend_dir=None, watch_files=False)), project


def test_clarity_credentials_never_return_secrets(tmp_path, monkeypatch):
    web, project = client(tmp_path)
    monkeypatch.setattr(clarity, "_credential_check", lambda *a, **k: None)
    with web:
        result = web.put("/api/v1/projects/store/integrations/clarity/credentials", json={"token": "private-token-123456", "project_id": "abc123", "timezone": "UTC"})
        assert result.status_code == 200
        assert "private-token" not in result.text
        assert web.get("/api/v1/projects/store/integrations/clarity").json()["integration"]["configured"]
        invalid = web.put("/api/v1/projects/store/integrations/clarity/credentials", json={"token": {"private-token": "secret"}})
        assert invalid.status_code == 400 and "private-token" not in invalid.text
        cross = web.delete("/api/v1/projects/store/integrations/clarity/credentials", headers={"Origin": "https://evil.example"})
        assert cross.status_code == 403 and clarity.path(project).exists()
        assert web.delete("/api/v1/projects/store/integrations/clarity/credentials").status_code == 200
        assert not clarity.path(project).exists()


def test_clarity_job_validation_and_evidence_isolation(tmp_path):
    web, project = client(tmp_path)
    clarity.configure(project, "private-token-123456", "abc123", "UTC", verify=False)
    with web:
        for payload in ({"action": "shell", "query": "anything"}, {"action": "docs", "query": "hi", "command": "rm -rf"}, {"action": "recordings", "start": "2026-10-26T00:00:00Z", "end": "2026-10-27T00:00:00Z", "url": "https://evil.example"}):
            assert web.post("/api/v1/projects/store/clarity/jobs", json=payload).status_code == 400
        assert web.get("/api/v1/projects/store/clarity/evidence/dashboard").json()["evidence"]["collection_status"] == "not_collected"
        assert web.get("/api/v1/projects/store/clarity/evidence/credentials").status_code == 400
        assert web.get("/api/v1/projects/missing/integrations/clarity").status_code == 404
