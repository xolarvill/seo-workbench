from __future__ import annotations

import base64
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from seo_workbench import state
from seo_workbench_tools.files import atomic_write_text


MAX_RESPONSE_BYTES = 4 * 1024 * 1024


class DataForSeoCredentialsError(ValueError):
    pass


class DataForSeoUnavailable(ValueError):
    pass


def credential_path(project_dir: Path) -> Path:
    return state.safe_project_path(project_dir, ".runtime/integrations/dataforseo.json")


def integration_status(project_dir: Path) -> dict[str, Any]:
    base = {
        "access": "local_only",
        "status": "needs_credentials",
        "configured": False,
        "source": "missing",
        "verified_at": None,
        "removable": False,
        "secret_visibility": "write_only",
        "transport": "rest_v3",
        "billing": "metered",
    }
    try:
        path = credential_path(project_dir)
    except ValueError:
        return {**base, "status": "unsafe_path"}
    if path.is_symlink():
        return {**base, "status": "unsafe_path"}
    if not path.is_file():
        return base
    try:
        stored = json.loads(path.read_text(encoding="utf-8"))
        login, password = stored["api_login"], stored["api_password"]
        if not isinstance(login, str) or not login or not isinstance(password, str) or not password:
            raise ValueError("invalid credential file")
    except (KeyError, OSError, TypeError, ValueError, json.JSONDecodeError):
        return {**base, "status": "invalid", "source": "private_file", "removable": True}
    return {
        **base,
        "status": "ready",
        "configured": True,
        "source": "private_file",
        "verified_at": stored.get("verified_at"),
        "removable": True,
    }


def verify_credentials(api_login: str, api_password: str, timeout: float = 15) -> dict[str, Any]:
    request = Request(
        "https://api.dataforseo.com/v3/appendix/user_data",
        headers={"Authorization": _authorization(api_login, api_password), "Accept": "application/json", "User-Agent": "SEO-Workbench/0.2"},
        method="GET",
    )
    payload = _request(
        request,
        timeout,
        invalid_credentials="DataForSEO rejected this API login or API password",
        forbidden_is_credentials=True,
    )
    try:
        result = payload["tasks"][0]["result"][0]
        if payload["status_code"] != 20000 or not isinstance(result["login"], str) or not result["login"]:
            raise ValueError("invalid credential response")
    except (KeyError, IndexError, TypeError, ValueError) as exc:
        raise DataForSeoCredentialsError("DataForSEO returned an invalid credential response") from exc
    return {"verified_at": datetime.now(timezone.utc).isoformat()}


def write_credentials(project_dir: Path, api_login: str, api_password: str, verified: dict[str, Any]) -> None:
    path = credential_path(project_dir)
    for directory in (path.parent.parent, path.parent):
        if directory.is_symlink():
            raise ValueError(f"DataForSEO runtime directory cannot be a symlink: {directory}")
        directory.mkdir(parents=True, exist_ok=True)
        directory.chmod(0o700)
    atomic_write_text(
        path,
        json.dumps(
            {"schema_version": "1.0", "api_login": api_login, "api_password": api_password, **verified},
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        mode=0o600,
    )


def post(project_dir: Path, endpoint: str, task: dict[str, Any], timeout: float = 45) -> dict[str, Any]:
    if not endpoint.startswith("/v3/") or "://" in endpoint:
        raise ValueError("DataForSEO endpoint must be a fixed v3 API path")
    path = credential_path(project_dir)
    if path.is_symlink() or not path.is_file():
        raise DataForSeoCredentialsError("DataForSEO credentials are not configured")
    try:
        stored = json.loads(path.read_text(encoding="utf-8"))
        authorization = _authorization(stored["api_login"], stored["api_password"])
    except (KeyError, OSError, TypeError, ValueError, json.JSONDecodeError) as exc:
        raise DataForSeoCredentialsError("DataForSEO credentials are invalid") from exc
    request = Request(
        f"https://api.dataforseo.com{endpoint}",
        data=json.dumps([task]).encode("utf-8"),
        headers={
            "Authorization": authorization,
            "Accept": "application/json",
            "Content-Type": "application/json",
            "User-Agent": "SEO-Workbench/0.2",
        },
        method="POST",
    )
    payload = _request(request, timeout, invalid_credentials="DataForSEO rejected the configured credentials")
    try:
        task_result = payload["tasks"][0]
        if payload["status_code"] != 20000 or task_result["status_code"] != 20000:
            raise DataForSeoUnavailable(str(task_result.get("status_message") or payload.get("status_message") or "request failed"))
    except (KeyError, IndexError, TypeError) as exc:
        raise DataForSeoUnavailable("DataForSEO returned an invalid response") from exc
    return payload


def _authorization(api_login: Any, api_password: Any) -> str:
    if not isinstance(api_login, str) or not api_login or not isinstance(api_password, str) or not api_password:
        raise DataForSeoCredentialsError("DataForSEO credentials are invalid")
    encoded = base64.b64encode(f"{api_login}:{api_password}".encode("utf-8")).decode("ascii")
    return f"Basic {encoded}"


def _request(
    request: Request,
    timeout: float,
    *,
    invalid_credentials: str,
    forbidden_is_credentials: bool = False,
) -> dict[str, Any]:
    try:
        with urlopen(request, timeout=timeout) as response:
            content = response.read(MAX_RESPONSE_BYTES + 1)
    except HTTPError as exc:
        if exc.code == 401 or (forbidden_is_credentials and exc.code == 403):
            raise DataForSeoCredentialsError(invalid_credentials) from exc
        raise DataForSeoUnavailable(f"DataForSEO returned HTTP {exc.code}") from exc
    except (OSError, URLError) as exc:
        raise DataForSeoUnavailable("DataForSEO could not be reached") from exc
    if len(content) > MAX_RESPONSE_BYTES:
        raise DataForSeoUnavailable("DataForSEO response exceeded the safety limit")
    try:
        payload = json.loads(content)
    except json.JSONDecodeError as exc:
        raise DataForSeoUnavailable("DataForSEO returned invalid JSON") from exc
    if not isinstance(payload, dict):
        raise DataForSeoUnavailable("DataForSEO returned an invalid response")
    return payload
