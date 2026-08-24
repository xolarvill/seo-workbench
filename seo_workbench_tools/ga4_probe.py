from __future__ import annotations

import json
import re
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Callable
from urllib.error import HTTPError, URLError
from urllib.parse import urlsplit
from urllib.request import Request
from zoneinfo import ZoneInfo

from seo_workbench import state
from seo_workbench_tools.files import atomic_write_text
from seo_workbench_tools.http_transport import read_url


ROOT = Path(__file__).resolve().parent.parent
RUNTIME_ROOT = ROOT / ".runtime/google"
SCOPES = ("https://www.googleapis.com/auth/analytics.readonly",)
SCHEMA_VERSION = "1.0"
COLLECTOR_VERSION = "0.1.0"
PROFILE_PATTERN = re.compile(r"^[a-zA-Z0-9][a-zA-Z0-9._-]{0,63}$")
PROPERTY_PATTERN = re.compile(r"^[0-9]{1,20}$")
PRIVATE_LANDING_PATH = re.compile(
    r"^/(?:[a-z]{2}(?:-[a-z]{2})?/)?(?:admin|account|cart|checkouts?|orders?|payments?)(?:/|$)",
    re.IGNORECASE,
)
ADMIN_API_BASE = "https://analyticsadmin.googleapis.com/v1beta"
DATA_API_BASE = "https://analyticsdata.googleapis.com/v1beta"
TOKEN_URI = "https://oauth2.googleapis.com/token"
RequestCallable = Callable[[str, str, dict[str, Any] | None, Any, float], dict[str, Any]]
COMMERCE_EVENTS = ("view_item", "add_to_cart", "begin_checkout", "purchase")


class Ga4QuotaExceeded(RuntimeError):
    """GA4 refused a request because the applicable quota was exhausted."""


def _now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _timestamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")


def validate_profile(profile: str) -> str:
    if not isinstance(profile, str) or not PROFILE_PATTERN.fullmatch(profile):
        raise ValueError("profile must match [a-zA-Z0-9][a-zA-Z0-9._-]{0,63}")
    return profile


def validate_property(property_id: str) -> str:
    if not isinstance(property_id, str) or not PROPERTY_PATTERN.fullmatch(property_id):
        raise ValueError("GA4 property must be a numeric property ID")
    return property_id


def profile_dir(profile: str, *, runtime_root: Path | None = None) -> Path:
    profile = validate_profile(profile)
    root = runtime_root or RUNTIME_ROOT
    directory = root / "profiles" / profile
    for candidate in (root.parent, root, root / "profiles", directory):
        if candidate.is_symlink():
            raise ValueError(f"Google credential path cannot contain symlinks: {candidate}")
    return directory


def binding_path(project_dir: Path) -> Path:
    return state.safe_project_path(project_dir, ".runtime/integrations/google-ga4.json")


def _write_private_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    atomic_write_text(path, json.dumps(payload, ensure_ascii=False, indent=2) + "\n", mode=0o600)


def _load_google_auth() -> tuple[Any, Any]:
    try:
        from google.auth.transport.requests import Request as AuthRequest
        from google.oauth2 import credentials as user_credentials
    except ImportError as exc:
        raise RuntimeError("Google authentication support is missing; run ./setup.sh") from exc
    return AuthRequest, user_credentials


def import_credentials(
    profile: str,
    payload: dict[str, Any],
    *,
    runtime_root: Path | None = None,
) -> dict[str, Any]:
    """Store a GA4 analytics.readonly token as an authorized-user token file.

    The source file may use either the ga4.json shape (access_token,
    refresh_token, scopes, app_client_id) or the standard authorized-user
    shape (token, refresh_token, client_id, client_secret). Client secrets are
    required for refresh; a shared OAuth client from the same profile's
    client-secret.json is reused when present.
    """
    profile = validate_profile(profile)
    if not isinstance(payload, dict):
        raise ValueError("GA4 credentials must be a JSON object")

    token = payload.get("access_token") or payload.get("token")
    refresh_token = payload.get("refresh_token")
    scopes = payload.get("scopes") or list(SCOPES)
    client_id = payload.get("app_client_id") or payload.get("client_id") or ""
    client_secret = payload.get("client_secret") or ""
    expiry_ms = payload.get("expires_at_ms") or payload.get("expiry")
    if not isinstance(token, str) or not token:
        raise ValueError("GA4 credentials require an access_token")
    if not isinstance(refresh_token, str) or not refresh_token:
        raise ValueError("GA4 credentials require a refresh_token")

    directory = profile_dir(profile, runtime_root=runtime_root)
    directory.mkdir(parents=True, exist_ok=True, mode=0o700)
    client_path = directory / "client-secret.json"
    if not client_secret:
        # The GA4 token typically comes from the same Google OAuth app as the
        # GSC profile. Reuse a shared client-secret.json from any profile.
        candidates = [client_path]
        if runtime_root is not None and isinstance(runtime_root, Path):
            profiles_root = runtime_root / "profiles"
        else:
            profiles_root = RUNTIME_ROOT / "profiles"
        if profiles_root.is_dir() and not profiles_root.is_symlink():
            for candidate_profile in sorted(profiles_root.iterdir(), key=lambda item: item.name.casefold()):
                if candidate_profile.is_dir() and not candidate_profile.is_symlink():
                    candidates.append(candidate_profile / "client-secret.json")
        for candidate in candidates:
            if not candidate.is_file() or candidate.is_symlink():
                continue
            try:
                shared = json.loads(candidate.read_text(encoding="utf-8"))
                installed = shared.get("installed", shared.get("web", {}))
                client_id = client_id or installed.get("client_id", "")
                client_secret = installed.get("client_secret", "")
                if client_secret:
                    break
            except (OSError, json.JSONDecodeError):
                continue

    expiry: datetime | None = None
    if isinstance(expiry_ms, (int, float)):
        expiry = datetime.fromtimestamp(expiry_ms / 1000, tz=timezone.utc)
    elif isinstance(expiry_ms, str):
        try:
            expiry = datetime.fromisoformat(expiry_ms.replace("Z", "+00:00"))
        except ValueError:
            expiry = None
    elif expiry_ms is None:
        expiry = None

    stored = {
        "schema_version": SCHEMA_VERSION,
        "channel": "ga4",
        "profile": profile,
        "token": token,
        "refresh_token": refresh_token,
        "token_uri": TOKEN_URI,
        "client_id": client_id,
        "client_secret": client_secret,
        "scopes": [str(scope) for scope in scopes if isinstance(scope, str)],
        "expiry": expiry.isoformat() if expiry else None,
        "imported_at": _now(),
    }
    _write_private_json(directory / "ga4-token.json", stored)
    return {"profile": profile, "credential_type": "oauth", "path": str(directory / "ga4-token.json")}


def load_credentials(profile: str, *, refresh: bool = True, runtime_root: Path | None = None) -> Any:
    AuthRequest, user_credentials = _load_google_auth()
    directory = profile_dir(profile, runtime_root=runtime_root)
    token_path = directory / "ga4-token.json"
    if not token_path.is_file() or token_path.is_symlink():
        raise RuntimeError(f"GA4 profile '{profile}' is not authenticated; import ga4 credentials first")
    stored = json.loads(token_path.read_text(encoding="utf-8"))
    token = stored.get("token") or ""
    refresh_token = stored.get("refresh_token") or ""
    client_id = stored.get("client_id") or ""
    client_secret = stored.get("client_secret") or ""
    scopes = stored.get("scopes") or list(SCOPES)
    expiry = None
    if stored.get("expiry"):
        try:
            expiry = datetime.fromisoformat(str(stored["expiry"]))
            if expiry.tzinfo is not None:
                expiry = expiry.astimezone(timezone.utc).replace(tzinfo=None)
        except ValueError:
            expiry = None
    credentials = user_credentials.Credentials(
        token=token,
        refresh_token=refresh_token,
        token_uri=stored.get("token_uri") or TOKEN_URI,
        client_id=client_id,
        client_secret=client_secret,
        scopes=scopes,
        expiry=expiry,
    )
    if refresh and not credentials.valid:
        if not credentials.refresh_token:
            raise RuntimeError(f"GA4 profile '{profile}' has no refresh token; import credentials again")
        credentials.refresh(AuthRequest())
        stored["token"] = credentials.token
        stored["expiry"] = credentials.expiry.isoformat() if credentials.expiry else None
        _write_private_json(token_path, stored)
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
            raise Ga4QuotaExceeded("GA4 API quota exceeded") from exc
        if exc.code in {401, 403}:
            raise RuntimeError(f"GA4 API authorization failed with HTTP {exc.code}") from exc
        raise RuntimeError(f"GA4 API returned HTTP {exc.code}") from exc
    except (URLError, TimeoutError) as exc:
        raise RuntimeError(f"GA4 API request failed: {getattr(exc, 'reason', exc).__class__.__name__}") from exc
    if not raw:
        return {}
    try:
        payload = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise RuntimeError("GA4 API returned invalid JSON") from exc
    if not isinstance(payload, dict):
        raise RuntimeError("GA4 API returned a non-object JSON value")
    return payload


def list_properties(
    profile: str = "default",
    *,
    timeout: float = 20,
    requester: RequestCallable = api_request,
    runtime_root: Path | None = None,
) -> dict[str, Any]:
    credentials = load_credentials(profile, runtime_root=runtime_root)
    payload = requester("GET", f"{ADMIN_API_BASE}/accountSummaries", None, credentials, timeout)
    properties: list[dict[str, Any]] = []
    for account in payload.get("accountSummaries") or []:
        account_id = str(account.get("account", "")).split("/")[-1]
        account_name = str(account.get("displayName", ""))
        for item in account.get("propertySummaries") or []:
            property_id = str(item.get("property", "")).split("/")[-1]
            properties.append(
                {
                    "property_id": property_id,
                    "display_name": str(item.get("displayName", "")),
                    "account_id": account_id,
                    "account_name": account_name,
                }
            )
    return {"profile": profile, "properties": properties}


def bind_property(
    project_dir: Path,
    property_id: str,
    *,
    profile: str = "default",
    timeout: float = 20,
    requester: RequestCallable = api_request,
    runtime_root: Path | None = None,
) -> dict[str, Any]:
    property_id = validate_property(property_id)
    available = list_properties(profile, timeout=timeout, requester=requester, runtime_root=runtime_root)[
        "properties"
    ]
    match = next((item for item in available if item["property_id"] == property_id), None)
    if not match:
        raise ValueError(f"GA4 property is not accessible to profile '{profile}': {property_id}")
    binding = {
        "schema_version": SCHEMA_VERSION,
        "channel": "ga4",
        "profile": profile,
        "property": property_id,
        "display_name": match.get("display_name", ""),
        "bound_at": _now(),
    }
    _write_private_json(binding_path(project_dir), binding)
    return binding


def load_binding(project_dir: Path) -> dict[str, Any]:
    path = binding_path(project_dir)
    if not path.is_file():
        raise RuntimeError("GA4 property is not bound; import credentials and bind a property first")
    try:
        binding = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise RuntimeError(f"invalid GA4 binding: {path}") from exc
    if not binding.get("profile") or not binding.get("property"):
        raise RuntimeError(f"incomplete GA4 binding: {path}")
    return binding


def _artifact(report: dict[str, Any], output_dir: Path, prefix: str) -> Path:
    output_dir.mkdir(parents=True, exist_ok=True, mode=0o700)
    path = output_dir / f"{prefix}-{_timestamp()}.json"
    report["manifest"] = {"path": str(path), "latest_path": str(output_dir / "latest.json")}
    _write_private_json(path, report)
    _write_private_json(output_dir / "latest.json", report)
    return path


def _date_windows(
    days: int,
    today: date | None = None,
    end_date: date | None = None,
) -> tuple[dict[str, str], dict[str, str]]:
    if not 1 <= days <= 90:
        raise ValueError("days must be between 1 and 90")
    analytics_today = today or datetime.now(ZoneInfo("UTC")).date()
    end = end_date or analytics_today - timedelta(days=2)
    start = end - timedelta(days=days - 1)
    previous_end = start - timedelta(days=1)
    previous_start = previous_end - timedelta(days=days - 1)
    return (
        {"startDate": start.isoformat(), "endDate": end.isoformat()},
        {"startDate": previous_start.isoformat(), "endDate": previous_end.isoformat()},
    )


def _report_rows(
    property_id: str,
    credentials: Any,
    body: dict[str, Any],
    timeout: float,
    requester: RequestCallable,
) -> list[dict[str, Any]]:
    """Run one GA4 report and convert dimension/metric cells to plain rows."""
    rows: list[dict[str, Any]] = []
    offset = 0
    while True:
        payload = requester(
            "POST",
            f"{DATA_API_BASE}/properties/{property_id}:runReport",
            {**body, "limit": 10000, "offset": offset},
            credentials,
            timeout,
        )
        metadata = payload.get("metadata") or {}
        if payload.get("samplingMetadatas") or metadata.get("samplingMetadatas"):
            raise RuntimeError("GA4 returned sampled data; refusing partial business evidence")
        metric_headers = [str(item.get("name", "")) for item in payload.get("metricHeaders") or []]
        batch = payload.get("rows") or []
        for item in batch:
            dimension_values = [str(cell.get("value", "")) for cell in item.get("dimensionValues") or []]
            metric_values = [float(cell.get("value") or 0) for cell in item.get("metricValues") or []]
            rows.append(
                {
                    "keys": dimension_values,
                    "metrics": {name: value for name, value in zip(metric_headers, metric_values)},
                }
            )
        row_count = int(payload.get("rowCount") or len(rows))
        if row_count > 50000:
            raise RuntimeError("GA4 report exceeded the 50,000-row safety limit")
        if not batch or len(rows) >= row_count:
            break
        offset = len(rows)
    return rows


def _public_landing_rows(rows: list[dict[str, Any]], *, dated: bool = False) -> list[dict[str, Any]]:
    """Remove query strings and non-public commerce paths before persistence."""
    grouped: dict[tuple[str, ...], dict[str, float]] = {}
    for row in rows:
        keys = row.get("keys") or []
        path_index = 1 if dated else 0
        raw = str(keys[path_index]) if len(keys) > path_index else ""
        path = urlsplit(raw).path if raw.startswith(("/", "http://", "https://")) else ""
        if not path or PRIVATE_LANDING_PATH.search(path):
            continue
        raw_day = str(keys[0])
        day = f"{raw_day[:4]}-{raw_day[4:6]}-{raw_day[6:]}" if dated and len(raw_day) == 8 else raw_day
        public_keys = (day, path) if dated else (path,)
        metrics = grouped.setdefault(public_keys, {})
        for name, value in (row.get("metrics") or {}).items():
            metrics[str(name)] = metrics.get(str(name), 0.0) + float(value or 0)
    return [{"keys": list(keys), "metrics": metrics} for keys, metrics in sorted(grouped.items())]


def _commerce_event_coverage(rows: list[dict[str, Any]]) -> dict[str, Any]:
    observed = sorted(
        {
            str((row.get("keys") or [""])[0])
            for row in rows
            if row.get("keys") and float((row.get("metrics") or {}).get("eventCount") or 0) > 0
        }
        & set(COMMERCE_EVENTS)
    )
    missing = [event for event in COMMERCE_EVENTS if event not in observed]
    return {
        "status": "complete" if not missing else "partial" if observed else "not_observed",
        "scope": "all_channels",
        "observed_events": observed,
        "missing_events": missing,
    }


def collect(
    project_dir: Path,
    output_dir: Path,
    *,
    days: int = 28,
    compare: bool = True,
    timeout: float = 30,
    requester: RequestCallable = api_request,
    today: date | None = None,
    end_date: date | None = None,
) -> dict[str, Any]:
    binding = load_binding(project_dir)
    credentials = load_credentials(binding["profile"])
    property_metadata = requester(
        "GET",
        f"{ADMIN_API_BASE}/properties/{binding['property']}",
        None,
        credentials,
        timeout,
    )
    property_time_zone = str(property_metadata.get("timeZone") or "")
    if not property_time_zone:
        raise RuntimeError("GA4 property metadata did not include a time zone")
    current, previous = _date_windows(
        days,
        today or datetime.now(ZoneInfo(property_time_zone)).date(),
        end_date,
    )
    windows = [("current", current)]
    if compare:
        windows.append(("previous", previous))
    results: dict[str, Any] = {}
    base_metrics = [
        {"name": "sessions"},
        {"name": "totalUsers"},
        {"name": "engagedSessions"},
        {"name": "keyEvents"},
        {"name": "itemViewEvents"},
        {"name": "addToCarts"},
        {"name": "checkouts"},
        {"name": "ecommercePurchases"},
        {"name": "purchaseRevenue"},
    ]
    dimensions = {
        "landing_page": (["landingPage"], False),
        "landing_page_organic": (
            ["landingPage"],
            True,
        ),
        "landing_page_organic_daily": (
            ["date", "landingPage"],
            True,
        ),
        "channel": (["sessionDefaultChannelGroup"], False),
    }
    for label, window in windows:
        results[label] = {**window}
        for name, (grouping, organic_only) in dimensions.items():
            body: dict[str, Any] = {
                "dateRanges": [window],
                "dimensions": [{"name": group} for group in grouping],
                "metrics": base_metrics,
                "limit": 10000,
            }
            if organic_only:
                body["dimensionFilter"] = {
                    "filter": {
                        "fieldName": "sessionDefaultChannelGroup",
                        "stringFilter": {"matchType": "EXACT", "value": "Organic Search"},
                    }
                }
            rows = _report_rows(
                binding["property"], credentials, body, timeout, requester
            )
            results[label][name] = (
                _public_landing_rows(rows, dated=name.endswith("_daily"))
                if name.startswith("landing_page")
                else rows
            )
        event_rows = _report_rows(
            binding["property"],
            credentials,
            {
                "dateRanges": [window],
                "dimensions": [{"name": "eventName"}],
                "metrics": [{"name": "eventCount"}],
                "dimensionFilter": {
                    "filter": {
                        "fieldName": "eventName",
                        "inListFilter": {"values": list(COMMERCE_EVENTS)},
                    }
                },
            },
            timeout,
            requester,
        )
        results[label]["commerce_event_coverage"] = _commerce_event_coverage(event_rows)
    report = {
        "schema_version": SCHEMA_VERSION,
        "collector_version": COLLECTOR_VERSION,
        "generated_at": _now(),
        "collection_status": "ok",
        "profile": binding["profile"],
        "property": binding["property"],
        "property_display_name": binding.get("display_name", ""),
        "property_time_zone": property_time_zone,
        "scope": "ga4",
        "window_days": days,
        "compare": compare,
        "windows": results,
        "errors": [],
        "warnings": [],
        "network_boundary": {
            "provider": "Google Analytics Data API",
            "target_site_requested": False,
            "credentials_persisted": True,
            "credentials_in_artifacts": False,
        },
    }
    _artifact(report, output_dir, "ga4")
    return report
