import json
import stat

import pytest

from seo_workbench import clarity, state


@pytest.fixture
def project(tmp_path):
    p = tmp_path / "store"
    state.init_state("shopify", "Store", "https://example.com", project_dir=p)
    return p


def good(*args, **kwargs):
    return {"ok": True, "result": {"content": [{"type": "text", "text": '{"sessions": 2}'}]}}


def test_private_configuration_and_public_status(project):
    result = clarity.configure(project, "secret-token-123456", "store123", "UTC", caller=good)
    assert result["credential_verified"] and not result["identity_verified"]
    assert "secret-token" not in json.dumps(result)
    assert stat.S_IMODE(clarity.path(project).stat().st_mode) == 0o600
    assert stat.S_IMODE(clarity.path(project).parent.stat().st_mode) == 0o700


def test_failed_rotation_preserves_credential(project):
    clarity.configure(project, "secret-token-original", "store123", "UTC", caller=good)
    before = clarity.path(project).read_bytes()
    with pytest.raises(ValueError, match="verification failed"):
        clarity.configure(project, "secret-token-replace", "store123", "UTC", verify=False,
                          caller=lambda *a, **k: {"ok": False, "reason_code": "needs_auth"})
    assert clarity.path(project).read_bytes() == before


def test_project_isolation_and_symlink_rejection(project, tmp_path):
    second = tmp_path / "second"
    state.init_state("shopify", "Other", "https://other.com", project_dir=second)
    clarity.configure(project, "secret-token-original", "store123", "UTC", verify=False)
    assert not clarity.integration_status(second)["configured"]
    (second / ".runtime").symlink_to(project / ".runtime", target_is_directory=True)
    assert clarity.integration_status(second)["status"] == "invalid_connection"
    with pytest.raises(ValueError, match="symlink"):
        clarity.configure(second, "secret-token-replace", "other123", "UTC", verify=False)


def test_concurrent_rotation_does_not_overwrite(project):
    clarity.configure(project, "secret-token-original", "store123", "UTC", verify=False)
    def concurrent(*a, **k):
        value = clarity.load(project)
        value["generation"] = "newer"
        clarity.private_write(project, ".runtime/integrations/clarity.json", value)
        return good()
    with pytest.raises(ValueError, match="concurrently"):
        clarity.configure(project, "secret-token-replace", "store123", "UTC", caller=concurrent)
    assert clarity.load(project)["generation"] == "newer"


@pytest.mark.parametrize("raw,reason", [
    ({"ok": True, "result": {"content": [{"type": "text", "text": "An error occurred while fetching the data."}]}}, "provider_error"),
    ({"ok": True, "http_status": 429}, "rate_limited"),
    ({"ok": True, "http_status": 401}, "needs_auth"),
    ({"ok": True, "result": {"content": []}}, "invalid_response"),
])
def test_provider_error_contract(raw, reason):
    assert clarity.interpret(raw)[1] == reason


def test_verify_respects_same_project_operation_lease(project):
    clarity.configure(project, "secret-token-123456", "abc123", "UTC", verify=False)
    with clarity.operation_lock(project):
        with pytest.raises(ValueError, match="running operation"):
            clarity.verify_connection(project, caller=lambda *a, **k: pytest.fail("must not call during another operation"))


def test_verify_respects_cooldown(project):
    clarity.configure(project, "secret-token-123456", "abc123", "UTC", verify=False)
    clarity.record_cooldown(project)
    with pytest.raises(ValueError, match="rate_limited"):
        clarity.verify_connection(project, caller=lambda *a, **k: pytest.fail("must not call during cooldown"))


def test_control_characters_in_tokens_are_rejected(project):
    with pytest.raises(ValueError, match="token must"):
        clarity.configure(project, "secret-token-with\x00null", "abc123", "UTC", verify=False)
