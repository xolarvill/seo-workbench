"""Project-scoped Clarity credentials. Tokens are never returned by public APIs."""
from __future__ import annotations

import json
import re
import secrets
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Callable
from urllib.parse import urlsplit
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError
from filelock import FileLock, Timeout

from seo_workbench import state
from seo_workbench.locks import project_lock
from seo_workbench_tools.clarity_runtime import call, runtime_status
from seo_workbench_tools.files import atomic_write_text


def now() -> str:
    return datetime.now(timezone.utc).isoformat()


def path(project_dir: Path) -> Path:
    return state.safe_project_path(project_dir, ".runtime/integrations/clarity.json")


def private_write(project_dir: Path, relative: str, payload: dict[str, Any]) -> Path:
    target = state.safe_project_path(project_dir, relative)
    parent = target.parent
    while parent != project_dir and parent.is_relative_to(project_dir):
        parent.mkdir(parents=True, exist_ok=True, mode=0o700)
        parent.chmod(0o700)
        parent = parent.parent
    atomic_write_text(target, json.dumps(payload, ensure_ascii=False, indent=2) + "\n", mode=0o600)
    return target


def load(project_dir: Path) -> dict[str, Any]:
    target = path(project_dir)
    if not target.is_file():
        raise ValueError("Clarity is not configured for this project")
    try:
        value = json.loads(target.read_text())
        if not isinstance(value, dict) or not value.get("token") or not value.get("generation"):
            raise ValueError()
        validate(project_dir, value["token"], value["project_id"], value["timezone"])
        if value.get("site_url") != site_url(project_dir):
            raise ValueError()
        return value
    except (ValueError, KeyError, TypeError):
        raise ValueError("Clarity connection is invalid; reconfigure this project") from None


def site_url(project_dir: Path) -> str:
    return str(state.read_json(state.state_path(project_dir))["project"]["url"]).rstrip("/")


def validate(project_dir: Path, token: str, project_id: str, tz: str) -> None:
    if not isinstance(token, str) or not 16 <= len(token) <= 16384 or re.search(r"[\s\x00-\x1f\x7f]", token):
        raise ValueError("Clarity token must be 16–16384 characters without whitespace")
    if not re.fullmatch(r"[A-Za-z0-9]{1,64}", project_id):
        raise ValueError("Clarity project ID must contain letters and digits only")
    try:
        ZoneInfo(tz)
    except (ZoneInfoNotFoundError, ValueError):
        raise ValueError("Clarity timezone must be a valid IANA timezone") from None
    url = urlsplit(site_url(project_dir))
    if url.scheme != "https" or not url.hostname or url.username or url.password:
        raise ValueError("Clarity requires a project with a canonical HTTPS website")


def interpret(raw: dict[str, Any]) -> tuple[Any, str | None]:
    """Decode SDK content without interpreting every non-empty response as success."""
    if not raw.get("ok"):
        return None, raw.get("reason_code", "provider_error")
    status = raw.get("http_status")
    if status in (401, 403):
        return None, "needs_auth"
    if status == 429:
        return None, "rate_limited"
    result = raw.get("result")
    if not isinstance(result, dict) or result.get("isError"):
        return None, "provider_error"
    blocks = result.get("content") or []
    texts = [item.get("text", "") for item in blocks if isinstance(item, dict) and item.get("type") == "text"]
    if not texts:
        return None, "invalid_response"
    text = "\n".join(texts)
    if "No Clarity API token provided" in text:
        return None, "needs_auth"
    if "An error occurred while fetching the data" in text:
        return None, "provider_error"
    try:
        decoded = json.loads(text)
    except ValueError:
        return {"observation": text}, "unstructured_response"
    if not isinstance(decoded, (dict, list)):
        return None, "invalid_response"
    if isinstance(decoded, dict) and (decoded.get("error") or decoded.get("success") is False):
        return None, "provider_error"
    if isinstance(decoded, dict) and decoded.get("dataErrorType") not in (None, 0):
        code = decoded["dataErrorType"]
        # Preserve only a bounded numeric enum for diagnosis, never failed payloads.
        return ({"dataErrorType": code} if type(code) is int and abs(code) <= 2**31 else None), "provider_query_error"
    return decoded, None


def operation_lock(project_dir: Path) -> FileLock:
    target = state.safe_project_path(project_dir, ".runtime/clarity/operation.lock")
    target.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    return FileLock(str(target), timeout=0)


def check_cooldown(project_dir: Path) -> None:
    target = state.safe_project_path(project_dir, ".runtime/clarity/cooldown.json")
    if target.exists() and datetime.fromisoformat(json.loads(target.read_text())["until"]) > datetime.now(timezone.utc):
        raise ValueError("rate_limited")


def record_cooldown(project_dir: Path) -> None:
    private_write(project_dir, ".runtime/clarity/cooldown.json", {"until": (datetime.now(timezone.utc) + timedelta(seconds=60)).isoformat()})


def _credential_check(value: dict[str, Any], caller: Callable = call, *, project_dir: Path) -> None:
    day = (datetime.now(ZoneInfo(value["timezone"])) - timedelta(days=1)).date().isoformat()
    try:
        with operation_lock(project_dir):
            check_cooldown(project_dir)
            response = caller("query-analytics-dashboard", {"query":
                f"Total sessions on {value['site_url']} from {day} through {day}, timezone {value['timezone']}."},
                token=value["token"], timezone=value["timezone"])
            _, error = interpret(response)
            if error:
                if error == "rate_limited":
                    record_cooldown(project_dir)
                raise ValueError(f"Clarity connection verification failed ({error})")
    except Timeout:
        raise ValueError("Clarity project already has a running operation") from None


def configure(project_dir: Path, token: str, project_id: str, tz: str, *, verify: bool = True, caller: Callable = call) -> dict[str, Any]:
    validate(project_dir, token, project_id, tz)
    existing = None
    if path(project_dir).exists():
        existing = load(project_dir)["generation"]
    value = {"schema_version": "clarity-connection-v1", "token": token, "project_id": project_id,
             "timezone": tz, "site_url": site_url(project_dir), "generation": secrets.token_hex(16),
             "configured_at": now(), "credential_verified_at": None, "identity_verified": False,
             "identity_source": "operator_declared"}
    # Rotation always verifies before replacing a working credential.
    if verify or existing:
        _credential_check(value, caller, project_dir=project_dir)
        value["credential_verified_at"] = now()
    with project_lock(project_dir):
        current = load(project_dir)["generation"] if path(project_dir).exists() else None
        if current != existing:
            raise ValueError("Clarity connection changed concurrently; reload before saving")
        private_write(project_dir, ".runtime/integrations/clarity.json", value)
    return integration_status(project_dir)


def verify_connection(project_dir: Path, *, caller: Callable = call) -> dict[str, Any]:
    value = load(project_dir)
    _credential_check(value, caller, project_dir=project_dir)
    with project_lock(project_dir):
        current = load(project_dir)
        if current["generation"] != value["generation"]:
            raise ValueError("Clarity connection changed while verifying")
        current["credential_verified_at"] = now()
        private_write(project_dir, ".runtime/integrations/clarity.json", current)
    return integration_status(project_dir)


def disconnect(project_dir: Path) -> dict[str, Any]:
    with project_lock(project_dir):
        path(project_dir).unlink(missing_ok=True)
    return integration_status(project_dir)


def integration_status(project_dir: Path) -> dict[str, Any]:
    result = {**runtime_status(), "configured": False, "status": "needs_config", "credential_verified": False,
              "identity_verified": False, "secret_visibility": "write_only"}
    try:
        if not path(project_dir).exists():
            return result
        value = load(project_dir)
    except (ValueError, OSError):
        return {**result, "status": "invalid_connection"}
    return {**result, "configured": True,
            "status": "ready" if value.get("credential_verified_at") else "configured_unverified",
            "project_id": value["project_id"], "site_url": value["site_url"], "timezone": value["timezone"],
            "credential_verified": bool(value.get("credential_verified_at")),
            "credential_verified_at": value.get("credential_verified_at"), "identity_source": "operator_declared"}
