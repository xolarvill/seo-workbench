from __future__ import annotations

import json
import re
import shutil
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Callable
from urllib.error import HTTPError, URLError
from urllib.parse import quote, urlsplit
from urllib.request import Request
from zoneinfo import ZoneInfo

from seo_workbench_tools.files import atomic_write_text
from seo_workbench_tools.http_transport import read_url
from seo_workbench_tools.network_boundary import validate_url


ROOT = Path(__file__).resolve().parent.parent
RUNTIME_ROOT = ROOT / ".runtime/google"
SCOPES = ("https://www.googleapis.com/auth/webmasters.readonly",)
SCHEMA_VERSION = "1.0"
COLLECTOR_VERSION = "0.1.0"
PROFILE_PATTERN = re.compile(r"^[a-zA-Z0-9][a-zA-Z0-9._-]{0,63}$")
API_BASE = "https://www.googleapis.com/webmasters/v3"
INSPECTION_ENDPOINT = "https://searchconsole.googleapis.com/v1/urlInspection/index:inspect"
RequestCallable = Callable[[str, str, dict[str, Any] | None, Any, float], dict[str, Any]]
CHANGE_PERFORMANCE_MAX_URLS = 25


class GscQuotaExceeded(RuntimeError):
    """Search Console refused a request because the applicable quota was exhausted."""


def _now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _timestamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")


def validate_profile(profile: str) -> str:
    if not PROFILE_PATTERN.fullmatch(profile):
        raise ValueError("profile must use 1-64 letters, numbers, dots, underscores, or hyphens")
    return profile


def profile_dir(profile: str, *, runtime_root: Path | None = None) -> Path:
    root = runtime_root or RUNTIME_ROOT
    directory = root / "profiles" / validate_profile(profile)
    for candidate in (root.parent, root, root / "profiles", directory):
        if candidate.exists() and candidate.is_symlink():
            raise ValueError(f"Google credential path cannot contain symlinks: {candidate}")
    return directory


def binding_path(project_dir: Path) -> Path:
    path = project_dir / ".runtime/integrations/google.json"
    current = project_dir
    for part in (".runtime", "integrations"):
        if current.exists() and current.is_symlink():
            raise ValueError(f"GSC binding path cannot contain symlinks: {current}")
        current /= part
    if current.exists() and current.is_symlink():
        raise ValueError(f"GSC binding path cannot contain symlinks: {current}")
    if path.exists() and path.is_symlink():
        raise ValueError(f"GSC binding file cannot be a symlink: {path}")
    return path


def _write_private_json(path: Path, payload: dict[str, Any]) -> None:
    atomic_write_text(path, json.dumps(payload, ensure_ascii=False, indent=2) + "\n", mode=0o600)


def _load_google_auth() -> tuple[Any, Any, Any]:
    try:
        from google.auth.transport.requests import Request as AuthRequest
        from google.oauth2 import credentials as user_credentials
        from google.oauth2 import service_account
    except ImportError as exc:
        raise RuntimeError("Google authentication support is missing; run ./setup.sh") from exc
    return AuthRequest, user_credentials, service_account


def authenticate(
    profile: str,
    *,
    client_secret: Path | None = None,
    service_account_path: Path | None = None,
    open_browser: bool = True,
    runtime_root: Path | None = None,
) -> dict[str, Any]:
    profile = validate_profile(profile)
    if (client_secret is None) == (service_account_path is None):
        raise ValueError("choose exactly one of --client-secret or --service-account")
    directory = profile_dir(profile, runtime_root=runtime_root)
    directory.mkdir(parents=True, exist_ok=True, mode=0o700)
    if service_account_path is not None:
        _, _, service_account = _load_google_auth()
        source = service_account_path.expanduser().resolve()
        service_account.Credentials.from_service_account_file(str(source), scopes=SCOPES)
        destination = directory / "service-account.json"
        if source != destination.resolve():
            shutil.copyfile(source, destination)
        destination.chmod(0o600)
        (directory / "token.json").unlink(missing_ok=True)
        (directory / "client-secret.json").unlink(missing_ok=True)
        return {"profile": profile, "credential_type": "service_account", "path": str(destination)}

    try:
        from google_auth_oauthlib.flow import InstalledAppFlow
    except ImportError as exc:
        raise RuntimeError("Google OAuth support is missing; run ./setup.sh") from exc
    source = client_secret.expanduser().resolve() if client_secret else Path()
    try:
        client_payload = json.loads(source.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ValueError(f"invalid OAuth client secret file: {source}") from exc
    if "installed" not in client_payload:
        raise ValueError("OAuth client secret must be an installed/desktop application credential")
    destination = directory / "client-secret.json"
    _write_private_json(destination, client_payload)
    flow = InstalledAppFlow.from_client_secrets_file(str(destination), SCOPES)
    credentials = flow.run_local_server(port=0, open_browser=open_browser)
    atomic_write_text(directory / "token.json", credentials.to_json() + "\n", mode=0o600)
    (directory / "service-account.json").unlink(missing_ok=True)
    return {"profile": profile, "credential_type": "oauth", "path": str(directory / "token.json")}


def load_credentials(profile: str, *, refresh: bool = True, runtime_root: Path | None = None) -> Any:
    AuthRequest, user_credentials, service_account = _load_google_auth()
    directory = profile_dir(profile, runtime_root=runtime_root)
    service_path = directory / "service-account.json"
    if service_path.is_file():
        credentials = service_account.Credentials.from_service_account_file(str(service_path), scopes=SCOPES)
        if refresh and not credentials.valid:
            credentials.refresh(AuthRequest())
        return credentials
    token_path = directory / "token.json"
    client_path = directory / "client-secret.json"
    if not token_path.is_file() or not client_path.is_file():
        raise RuntimeError(f"GSC profile '{profile}' is not authenticated; run gsc auth first")
    credentials = user_credentials.Credentials.from_authorized_user_file(str(token_path), SCOPES)
    if refresh and not credentials.valid:
        if not credentials.refresh_token:
            raise RuntimeError(f"GSC profile '{profile}' has no refresh token; authenticate again")
        credentials.refresh(AuthRequest())
        atomic_write_text(token_path, credentials.to_json() + "\n", mode=0o600)
    return credentials


def api_request(
    method: str,
    url: str,
    body: dict[str, Any] | None,
    credentials: Any,
    timeout: float,
) -> dict[str, Any]:
    headers = {"Accept": "application/json", "Authorization": f"Bearer {credentials.token}"}
    data = None
    if body is not None:
        headers["Content-Type"] = "application/json"
        data = json.dumps(body).encode("utf-8")
    request = Request(url, data=data, headers=headers, method=method)
    try:
        raw = read_url(request, timeout=timeout)
    except HTTPError as exc:
        if exc.code == 429:
            raise GscQuotaExceeded("Search Console API quota exceeded") from exc
        if exc.code in {401, 403}:
            raise RuntimeError(f"Search Console API authorization failed with HTTP {exc.code}") from exc
        raise RuntimeError(f"Search Console API returned HTTP {exc.code}") from exc
    except (URLError, TimeoutError) as exc:
        raise RuntimeError(f"Search Console API request failed: {getattr(exc, 'reason', exc).__class__.__name__}") from exc
    if not raw:
        return {}
    try:
        payload = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise RuntimeError("Search Console API returned invalid JSON") from exc
    if not isinstance(payload, dict):
        raise RuntimeError("Search Console API returned a non-object JSON value")
    return payload


def list_properties(
    profile: str = "default",
    *,
    timeout: float = 20,
    requester: RequestCallable = api_request,
    runtime_root: Path | None = None,
) -> dict[str, Any]:
    credentials = (
        load_credentials(profile)
        if runtime_root is None
        else load_credentials(profile, runtime_root=runtime_root)
    )
    payload = requester("GET", f"{API_BASE}/sites", None, credentials, timeout)
    properties = [
        {"site_url": item.get("siteUrl", ""), "permission_level": item.get("permissionLevel", "")}
        for item in payload.get("siteEntry", [])
        if isinstance(item, dict) and item.get("siteUrl")
    ]
    return {
        "schema_version": SCHEMA_VERSION,
        "generated_at": _now(),
        "collection_status": "ok",
        "profile": profile,
        "properties": properties,
        "errors": [],
        "warnings": [],
    }


def property_covers_url(site_url: str, target_url: str) -> bool:
    target = urlsplit(validate_url(target_url))
    if site_url.startswith("sc-domain:"):
        domain = site_url.removeprefix("sc-domain:").strip().casefold().rstrip(".")
        hostname = (target.hostname or "").casefold().rstrip(".")
        return bool(domain) and (hostname == domain or hostname.endswith(f".{domain}"))
    prefix = urlsplit(site_url)
    if prefix.scheme not in {"http", "https"} or not prefix.hostname:
        return False
    if target.scheme.casefold() != prefix.scheme.casefold() or target.netloc.casefold() != prefix.netloc.casefold():
        return False
    prefix_path = prefix.path or "/"
    target_path = target.path or "/"
    return target_path == prefix_path.rstrip("/") or target_path.startswith(prefix_path)


def bind_property(
    project_dir: Path,
    site_url: str,
    *,
    profile: str = "default",
    timeout: float = 20,
    requester: RequestCallable = api_request,
    runtime_root: Path | None = None,
) -> dict[str, Any]:
    state = json.loads((project_dir / "state.json").read_text(encoding="utf-8"))
    project_url = state.get("project", {}).get("url", "")
    if not project_url:
        raise ValueError("project.url is missing")
    if runtime_root is None:
        available = list_properties(profile, timeout=timeout, requester=requester)["properties"]
    else:
        available = list_properties(
            profile,
            timeout=timeout,
            requester=requester,
            runtime_root=runtime_root,
        )["properties"]
    match = next((item for item in available if item["site_url"] == site_url), None)
    if not match:
        raise ValueError(f"GSC property is not accessible to profile '{profile}': {site_url}")
    if not property_covers_url(site_url, project_url):
        raise ValueError(f"GSC property does not cover project URL {project_url}: {site_url}")
    binding = {
        "schema_version": SCHEMA_VERSION,
        "profile": profile,
        "property": site_url,
        "permission_level": match.get("permission_level", ""),
        "project_url": project_url,
        "bound_at": _now(),
    }
    _write_private_json(binding_path(project_dir), binding)
    return binding


def load_binding(project_dir: Path) -> dict[str, Any]:
    path = binding_path(project_dir)
    if not path.is_file():
        raise RuntimeError("GSC property is not bound; run gsc properties and gsc bind first")
    try:
        binding = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise RuntimeError(f"invalid GSC binding: {path}") from exc
    if not binding.get("profile") or not binding.get("property"):
        raise RuntimeError(f"incomplete GSC binding: {path}")
    return binding


def _artifact(report: dict[str, Any], output_dir: Path, prefix: str) -> Path:
    output_dir.mkdir(parents=True, exist_ok=True, mode=0o700)
    path = output_dir / f"{prefix}-{_timestamp()}.json"
    report["manifest"] = {"path": str(path), "latest_path": str(output_dir / "latest.json")}
    _write_private_json(path, report)
    _write_private_json(output_dir / "latest.json", report)
    return path


def _search_rows(
    property_url: str,
    credentials: Any,
    body: dict[str, Any],
    timeout: float,
    requester: RequestCallable,
    *,
    paginate: bool,
) -> dict[str, Any]:
    endpoint = f"{API_BASE}/sites/{quote(property_url, safe='')}/searchAnalytics/query"
    rows: list[dict[str, Any]] = []
    metadata: dict[str, Any] = {}
    aggregation = ""
    start = 0
    while True:
        request_body = {**body, "rowLimit": 25000, "startRow": start}
        payload = requester("POST", endpoint, request_body, credentials, timeout)
        batch = [item for item in payload.get("rows", []) if isinstance(item, dict)]
        rows.extend(batch)
        metadata = payload.get("metadata", metadata)
        aggregation = payload.get("responseAggregationType", aggregation)
        if not paginate or len(batch) < 25000 or len(rows) >= 50000:
            break
        start += 25000
    return {
        "request": {key: value for key, value in body.items() if key not in {"startRow", "rowLimit"}},
        "rows": rows[:50000],
        "row_count": min(len(rows), 50000),
        "truncated": len(rows) >= 50000,
        "metadata": metadata,
        "response_aggregation_type": aggregation,
    }


def _date_windows(days: int, today: date | None = None) -> tuple[dict[str, str], dict[str, str]]:
    if not 1 <= days <= 90:
        raise ValueError("days must be between 1 and 90")
    search_console_today = today or datetime.now(ZoneInfo("America/Los_Angeles")).date()
    end = search_console_today - timedelta(days=3)
    start = end - timedelta(days=days - 1)
    previous_end = start - timedelta(days=1)
    previous_start = previous_end - timedelta(days=days - 1)
    return (
        {"startDate": start.isoformat(), "endDate": end.isoformat()},
        {"startDate": previous_start.isoformat(), "endDate": previous_end.isoformat()},
    )


def collect_performance(
    project_dir: Path,
    output_dir: Path,
    *,
    days: int = 28,
    compare: bool = True,
    timeout: float = 30,
    requester: RequestCallable = api_request,
    today: date | None = None,
) -> dict[str, Any]:
    binding = load_binding(project_dir)
    credentials = load_credentials(binding["profile"])
    current, previous = _date_windows(days, today)
    windows = [("current", current)]
    if compare:
        windows.append(("previous", previous))
    results: dict[str, Any] = {}
    dimensions = {
        "totals": ([], False),
        "date": (["date"], False),
        "date_page": (["date", "page"], True),
        "page": (["page"], True),
        "query": (["query"], True),
        "query_page": (["query", "page"], True),
        "device": (["device"], False),
        "country": (["country"], False),
    }
    for label, window in windows:
        results[label] = {}
        for name, (grouping, paginate) in dimensions.items():
            body: dict[str, Any] = {**window, "type": "web", "dataState": "final"}
            if grouping:
                body["dimensions"] = grouping
            results[label][name] = _search_rows(
                binding["property"], credentials, body, timeout, requester, paginate=paginate
            )
    report = {
        "schema_version": SCHEMA_VERSION,
        "collector_version": COLLECTOR_VERSION,
        "generated_at": _now(),
        "collection_status": "ok",
        "profile": binding["profile"],
        "property": binding["property"],
        "search_type": "web",
        "data_state": "final",
        "window_days": days,
        "compare": compare,
        "windows": results,
        "errors": [],
        "warnings": [],
    }
    _artifact(report, output_dir, "search-analytics")
    return report


def collect_change_performance(
    project_dir: Path,
    output_dir: Path,
    *,
    urls: list[str],
    changed_at: date,
    review_date: date,
    timeout: float = 30,
    requester: RequestCallable = api_request,
    today: date | None = None,
) -> dict[str, Any]:
    if review_date <= changed_at:
        raise ValueError("review_date must be after changed_at")
    final_end = (today or datetime.now(ZoneInfo("America/Los_Angeles")).date()) - timedelta(days=3)
    if review_date > final_end:
        raise ValueError(f"review_date {review_date.isoformat()} is newer than finalized GSC data through {final_end.isoformat()}")
    selected = list(dict.fromkeys(validate_url(url) for url in urls))
    if not selected:
        raise ValueError("at least one change URL is required")
    if len(selected) > CHANGE_PERFORMANCE_MAX_URLS:
        raise ValueError(f"change-scoped GSC refresh supports at most {CHANGE_PERFORMANCE_MAX_URLS} URLs")
    binding = load_binding(project_dir)
    credentials = load_credentials(binding["profile"])
    days = (review_date - changed_at).days
    previous_end = changed_at - timedelta(days=1)
    windows = {
        "previous": {
            "startDate": (previous_end - timedelta(days=days - 1)).isoformat(),
            "endDate": previous_end.isoformat(),
        },
        "current": {
            "startDate": (changed_at + timedelta(days=1)).isoformat(),
            "endDate": review_date.isoformat(),
        },
    }
    results: dict[str, Any] = {}
    for label, window in windows.items():
        results[label] = {
            name: _change_rows(binding["property"], credentials, window, selected, dimensions, timeout, requester)
            for name, dimensions in (
                ("page", ["page"]),
                ("date_page", ["date", "page"]),
                ("query_page", ["query", "page"]),
            )
        }
    report = {
        "schema_version": SCHEMA_VERSION,
        "collector_version": COLLECTOR_VERSION,
        "generated_at": _now(),
        "collection_status": "ok",
        "profile": binding["profile"],
        "property": binding["property"],
        "search_type": "web",
        "data_state": "final",
        "window_days": days,
        "compare": True,
        "scope": "change_urls",
        "urls": selected,
        "windows": results,
        "errors": [],
        "warnings": [],
    }
    _artifact(report, output_dir, "change-outcome-gsc")
    return report


def _change_rows(
    property_url: str,
    credentials: Any,
    window: dict[str, str],
    urls: list[str],
    dimensions: list[str],
    timeout: float,
    requester: RequestCallable,
) -> dict[str, Any]:
    rows = []
    truncated = False
    for url in urls:
        result = _search_rows(
            property_url,
            credentials,
            {
                **window,
                "type": "web",
                "dataState": "final",
                "dimensions": dimensions,
                "dimensionFilterGroups": [
                    {"filters": [{"dimension": "page", "operator": "equals", "expression": url}]}
                ],
            },
            timeout,
            requester,
            paginate=True,
        )
        rows.extend(result["rows"])
        truncated = truncated or bool(result["truncated"])
    return {
        "request": {**window, "type": "web", "dataState": "final", "dimensions": dimensions},
        "rows": rows,
        "row_count": len(rows),
        "truncated": truncated,
    }


def representative_urls(project_dir: Path, limit: int = 10) -> list[str]:
    if not 1 <= limit <= 100:
        raise ValueError("inspection limit must be between 1 and 100")
    state = json.loads((project_dir / "state.json").read_text(encoding="utf-8"))
    candidates: list[str] = [state.get("project", {}).get("url", "")]
    raw_path = project_dir / "audits/raw/latest.json"
    if raw_path.is_file() and not raw_path.is_symlink():
        try:
            raw = json.loads(raw_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            raw = {}
        pages = [item for item in raw.get("pages", []) if isinstance(item, dict)]
        priority = sorted(
            pages,
            key=lambda item: (
                not bool(item.get("error")),
                not bool(item.get("canonical_audit", {}).get("issues")),
            ),
        )
        for page in priority:
            candidates.extend([page.get("final_url", ""), page.get("url", "")])
    selected: list[str] = []
    for value in candidates:
        if not value or value in selected:
            continue
        try:
            selected.append(validate_url(value))
        except ValueError:
            continue
        if len(selected) >= limit:
            break
    return selected


def collect_inspection(
    project_dir: Path,
    output_dir: Path,
    *,
    urls: list[str] | None = None,
    limit: int = 10,
    timeout: float = 30,
    requester: RequestCallable = api_request,
) -> dict[str, Any]:
    binding = load_binding(project_dir)
    credentials = load_credentials(binding["profile"])
    targets = []
    for url in urls or representative_urls(project_dir, limit):
        normalized = validate_url(url)
        if normalized not in targets:
            targets.append(normalized)
        if len(targets) >= limit:
            break
    results: list[dict[str, Any]] = []
    errors: list[dict[str, Any]] = []
    warnings = [
        {
            "scope": "gsc_inspection",
            "code": "indexed_version_only",
            "message": "URL Inspection reports the Google-indexed version and is not a live URL test",
        }
    ]
    quota_exhausted = False
    for target in targets:
        if not property_covers_url(binding["property"], target):
            errors.append({"scope": "gsc_inspection", "url": target, "message": "URL is outside the bound property"})
            continue
        try:
            payload = requester(
                "POST",
                INSPECTION_ENDPOINT,
                {"inspectionUrl": target, "siteUrl": binding["property"], "languageCode": "en-US"},
                credentials,
                timeout,
            )
            results.append({"url": target, "inspection_result": payload.get("inspectionResult", {})})
        except GscQuotaExceeded as exc:
            quota_exhausted = True
            errors.append({"scope": "gsc_inspection", "url": target, "message": str(exc)})
            break
        except RuntimeError as exc:
            errors.append({"scope": "gsc_inspection", "url": target, "message": str(exc)})
    status = "ok" if not errors else ("partial" if results else "failed")
    report = {
        "schema_version": SCHEMA_VERSION,
        "collector_version": COLLECTOR_VERSION,
        "generated_at": _now(),
        "collection_status": status,
        "profile": binding["profile"],
        "property": binding["property"],
        "indexed_version_only": True,
        "limit": limit,
        "requested_urls": targets,
        "inspections": results,
        "quota_exhausted": quota_exhausted,
        "errors": errors,
        "warnings": warnings,
    }
    _artifact(report, output_dir, "inspection")
    return report


def collect_sitemaps(
    project_dir: Path,
    output_dir: Path,
    *,
    timeout: float = 30,
    requester: RequestCallable = api_request,
) -> dict[str, Any]:
    binding = load_binding(project_dir)
    credentials = load_credentials(binding["profile"])
    endpoint = f"{API_BASE}/sites/{quote(binding['property'], safe='')}/sitemaps"
    payload = requester("GET", endpoint, None, credentials, timeout)
    sitemaps = []
    for item in payload.get("sitemap", []):
        if not isinstance(item, dict):
            continue
        sitemaps.append(
            {
                "path": item.get("path", ""),
                "last_submitted": item.get("lastSubmitted", ""),
                "last_downloaded": item.get("lastDownloaded", ""),
                "pending": bool(item.get("isPending")),
                "sitemap_index": bool(item.get("isSitemapsIndex")),
                "type": item.get("type", ""),
                "errors": int(item.get("errors", 0) or 0),
                "warnings": int(item.get("warnings", 0) or 0),
                "contents": [
                    {"type": content.get("type", ""), "submitted": int(content.get("submitted", 0) or 0)}
                    for content in item.get("contents", [])
                    if isinstance(content, dict)
                ],
            }
        )
    report = {
        "schema_version": SCHEMA_VERSION,
        "collector_version": COLLECTOR_VERSION,
        "generated_at": _now(),
        "collection_status": "ok",
        "profile": binding["profile"],
        "property": binding["property"],
        "sitemaps": sitemaps,
        "errors": [],
        "warnings": [],
    }
    _artifact(report, output_dir, "sitemaps")
    return report


def collect_all(
    project_dir: Path,
    output_dir: Path,
    *,
    days: int = 28,
    inspection_limit: int = 10,
    inspection_urls: list[str] | None = None,
    timeout: float = 30,
    requester: RequestCallable = api_request,
) -> dict[str, Any]:
    try:
        binding = load_binding(project_dir)
    except RuntimeError as exc:
        report = {
            "schema_version": SCHEMA_VERSION,
            "collector_version": COLLECTOR_VERSION,
            "generated_at": _now(),
            "collection_status": "needs_auth",
            "profile": "",
            "property": "",
            "components": {},
            "errors": [],
            "warnings": [{"scope": "gsc", "code": "binding_required", "message": str(exc)}],
        }
        _artifact(report, output_dir, "gsc")
        return report
    components: dict[str, Any] = {}
    errors: list[dict[str, Any]] = []
    warnings: list[dict[str, Any]] = []
    collectors = (
        (
            "search_analytics",
            lambda: collect_performance(
                project_dir, output_dir / "search-analytics", days=days, compare=True, timeout=timeout, requester=requester
            ),
        ),
        ("sitemaps", lambda: collect_sitemaps(project_dir, output_dir / "sitemaps", timeout=timeout, requester=requester)),
        (
            "inspection",
            lambda: collect_inspection(
                project_dir,
                output_dir / "inspection",
                urls=inspection_urls,
                limit=inspection_limit,
                timeout=timeout,
                requester=requester,
            ),
        ),
    )
    for name, collector in collectors:
        try:
            components[name] = collector()
            errors.extend(components[name].get("errors", []))
            warnings.extend(components[name].get("warnings", []))
        except RuntimeError as exc:
            components[name] = {"collection_status": "failed", "errors": [{"scope": f"gsc_{name}", "message": str(exc)}]}
            errors.extend(components[name]["errors"])
    successful = [item for item in components.values() if item.get("collection_status") in {"ok", "partial"}]
    if len(successful) == len(components) and not errors:
        status = "ok"
    elif successful:
        status = "partial"
    elif errors and all("not authenticated" in item.get("message", "") for item in errors):
        status = "needs_auth"
        warnings.append({"scope": "gsc", "code": "authentication_required", "message": errors[0]["message"]})
        errors = []
    else:
        status = "failed"
    report = {
        "schema_version": SCHEMA_VERSION,
        "collector_version": COLLECTOR_VERSION,
        "generated_at": _now(),
        "collection_status": status,
        "profile": binding["profile"],
        "property": binding["property"],
        "components": components,
        "errors": errors,
        "warnings": warnings,
        "network_boundary": {
            "provider": "Google Search Console API",
            "target_site_requested": False,
            "credentials_persisted": True,
            "credentials_in_artifacts": False,
        },
    }
    _artifact(report, output_dir, "gsc")
    return report
