"""Read-only Clarity queries with private, project-scoped evidence."""
from __future__ import annotations

import hashlib
import json
import re
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Callable
from urllib.parse import urlsplit, urlunsplit
from uuid import uuid4
from zoneinfo import ZoneInfo

from filelock import FileLock, Timeout

from seo_workbench import clarity, state
from seo_workbench_tools.clarity_runtime import call, SERVER_VERSION, SDK_VERSION

TOOLS = {"query": ("dashboard", "query-analytics-dashboard"), "recordings": ("recordings", "list-session-recordings"),
         "docs": ("documentation", "query-documentation-resources")}
DEVICES = {"Mobile", "PC", "Tablet"}
CHANNELS = {"OrganicSearch", "Direct", "Email", "Display", "Social", "PaidSearch", "Other", "Affiliate", "Referral", "Video", "Audio", "SMS", "AITools", "PaidAITools"}
SAFE_KEYS = set("data result results metrics metric metricName metricValue information value values count total totalCount sessions sessionCount totalSessionCount totalBotSessionCount distinctUsers distantUserCount users pageViews pageviews average percentage rate scrollDepth engagementTime activeTime totalTime deadClickCount rageClickCount scriptErrorCount quickBackCount browser Browser device Device deviceType country Country channel Channel source Source medium Medium campaign Campaign url URL pageUrl entryUrl exitUrl startDate endDate start end timezone dateRange scope metadata title description text answer response observation documentation content snippets citations links duration sessionDuration pageCount pagesCount clickCount summary insights rows columns type label name unit date error status message recordingUrl recordingLink sessionUrl recordingLinkUrl".split())
IDENTIFIER = re.compile(r"token|secret|password|email|user.?id|session.?id|recording.?id|(^id$)|enteredtext|input|client.?id|visitor|ipaddress", re.I)


def clean_text(value: str) -> str:
    value = re.sub(r"eyJ[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+", "[redacted-token]", value)
    value = re.sub(r"[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}", "[redacted-email]", value, flags=re.I)
    def clean_url(match):
        raw = match.group(0)
        parts = urlsplit(raw)
        if (parts.hostname or "").endswith("clarity.ms") or (parts.hostname or "").endswith("clarity.microsoft.com"):
            if "/recording/" in parts.path or "/recordings/" in parts.path or "/player/" in parts.path:
                return "[private-recording-link]"
        if re.search(r"/(account|orders?|checkouts?|customers?|admin|cart)(/|$)", parts.path, re.I):
            return "[private-page]"
        return urlunsplit((parts.scheme, parts.hostname or "", parts.path, "", ""))
    return re.sub(r"https?://[^\s<>\"\)]+", clean_url, value)[:16000]


def sanitize(value: Any, *, kind: str, key: str = "", depth: int = 0) -> Any:
    if depth > 15:
        return None
    if isinstance(value, dict):
        return {k: sanitize(v, kind=kind, key=k, depth=depth + 1)
                for k, v in value.items() if k in SAFE_KEYS and not IDENTIFIER.search(k)
                and not (kind == "recordings" and re.search(r"recording|sessionUrl|text|name|title|description|message", k, re.I))}
    if isinstance(value, list):
        return [sanitize(item, kind=kind, key=key, depth=depth + 1) for item in value[:1000]]
    if isinstance(value, str):
        return clean_text(value)
    if value is None or isinstance(value, (int, float, bool)):
        return value
    return None


def _utc(value: str) -> datetime:
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
        if parsed.tzinfo is None or parsed.utcoffset() != timedelta(0):
            raise ValueError()
        return parsed
    except ValueError:
        raise ValueError("Recordings require explicit UTC ISO timestamps") from None


def prepare(binding: dict, action: str, *, query: str = "", start: str = "", end: str = "", timezone_name: str | None = None,
            url: str | None = None, device: str | None = None, channel: str | None = None,
            rage_click: bool = False, dead_click: bool = False, js_error: bool = False, count: int = 10) -> tuple[dict, str]:
    if action not in TOOLS:
        raise ValueError("Unsupported Clarity operation")
    tz = timezone_name or binding["timezone"]
    try:
        ZoneInfo(tz)
    except (ValueError, KeyError):
        raise ValueError("Invalid IANA timezone") from None
    if action in ("query", "docs") and (not query.strip() or len(query) > 2000):
        raise ValueError("Clarity query must be 1–2000 characters")
    if query != clean_text(query):
        raise ValueError("Remove credentials, private URLs and sensitive query parameters from the query")
    if action == "docs":
        return {"query": query}, tz
    if action == "query":
        try:
            first, last = date.fromisoformat(start), date.fromisoformat(end)
        except ValueError:
            raise ValueError("Dashboard dates must use YYYY-MM-DD") from None
        if first > last:
            raise ValueError("Clarity start must not be after end")
        return {"query": f"{query}\nWebsite: {binding['site_url']}. Date range: {start} through {end} inclusive. Timezone: {tz}. Use only this range and website."}, tz
    if _utc(start) >= _utc(end):
        raise ValueError("Clarity start must be before end")
    if not 1 <= count <= 50 or device and device not in DEVICES or channel and channel not in CHANNELS:
        raise ValueError("Invalid Clarity count, device or channel")
    target = url or binding["site_url"]
    parts, site = urlsplit(target), urlsplit(binding["site_url"])
    if parts.scheme != "https" or parts.hostname != site.hostname or parts.username or parts.password or parts.query or parts.fragment or parts.port not in (None, 443):
        raise ValueError("Recording URL must be a clean HTTPS URL on this project's site")
    filters: dict[str, Any] = {"date": {"start": start, "end": end},
                               "visitedUrls": [{"url": target, "operator": "isExactly" if url else "startsWith"}]}
    if device:
        filters["deviceType"] = [device]
    if channel:
        filters["channel"] = [channel]
    if rage_click:
        filters["rageClickPresent"] = True
    if dead_click:
        filters["deadClickPresent"] = True
    if js_error:
        filters["javascriptErrors"] = [""]
    return {"filters": filters, "sortBy": "SessionStart_DESC", "count": count}, "UTC"


def read_evidence(project_dir: Path, kind: str) -> dict:
    if kind not in {"dashboard", "recordings", "documentation"}:
        raise ValueError("Unsupported Clarity evidence kind")
    target = state.safe_project_path(project_dir, f"audits/clarity/{kind}/latest.json")
    return json.loads(target.read_text()) if target.exists() else {"collection_status": "not_collected"}


def _save(project_dir: Path, kind: str, report: dict) -> dict:
    root = f"audits/clarity/{kind}"
    relative = f"{root}/clarity-{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')}-{uuid4().hex[:8]}.json"
    report["manifest"] = {"path": relative, "latest_path": f"{root}/latest.json"}
    with clarity.project_lock(project_dir):
        clarity.private_write(project_dir, relative, report)
        clarity.private_write(project_dir, f"{root}/latest.json", report)
        if report["collection_status"] == "ok":
            clarity.private_write(project_dir, f"{root}/last_successful.json", report)
        pointer = state.safe_project_path(project_dir, "audits/clarity/latest.json")
        index = json.loads(pointer.read_text()) if pointer.exists() else {"schema_version": "clarity-index-v1", "sources": {}}
        index["sources"][kind] = {"path": relative, "collection_status": report["collection_status"], "generated_at": report["generated_at"]}
        clarity.private_write(project_dir, "audits/clarity/latest.json", index)
    return report


def collect(project_dir: Path, action: str, *, caller: Callable = call, force: bool = False, **options) -> dict:
    if action not in TOOLS:
        raise ValueError("Unsupported Clarity operation")
    kind, tool = TOOLS[action]
    report: dict[str, Any] = {"schema_version": "clarity-evidence-v1", "provider": "microsoft-clarity-mcp",
        "server_version": SERVER_VERSION, "sdk_version": SDK_VERSION, "generated_at": clarity.now(),
        "collection_status": "not_collected", "reason_code": "needs_config", "errors": [], "warnings": [], "cache_hit": False,
        "observed_scope": None, "identity_verified": False}
    try:
        binding = clarity.load(project_dir)
    except (ValueError, OSError):
        return _save(project_dir, kind, report)
    arguments, tz = prepare(binding, action, **options)
    report.update(project_id=binding["project_id"], site_url=binding["site_url"], identity_source="operator_declared",
                  request={"tool": tool, "arguments": arguments, "timezone": tz})
    cache_key = hashlib.sha256(json.dumps([str(project_dir.resolve()), binding["generation"], SERVER_VERSION, SDK_VERSION, tool, arguments, tz], sort_keys=True).encode()).hexdigest()
    report["cache_key"] = cache_key
    lock_path = state.safe_project_path(project_dir, ".runtime/clarity/operation.lock")
    lock_path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    try:
        with FileLock(str(lock_path), timeout=0):
            lock_path.chmod(0o600)
            cool = state.safe_project_path(project_dir, ".runtime/clarity/cooldown.json")
            if cool.exists() and datetime.fromisoformat(json.loads(cool.read_text())["until"]) > datetime.now(timezone.utc):
                report.update(reason_code="rate_limited", collection_status="not_collected")
                return _save(project_dir, kind, report)
            cache = state.safe_project_path(project_dir, f"audits/clarity/{kind}/latest.json")
            if not force and cache.exists():
                previous = json.loads(cache.read_text())
                if previous.get("cache_key") == cache_key and previous.get("collection_status") in ("ok", "partial") and previous.get("response") is not None and datetime.fromisoformat(previous["generated_at"]) > datetime.now(timezone.utc) - timedelta(minutes=15):
                    return {**previous, "cache_hit": True}
            raw = caller(tool, arguments, token=binding["token"], timezone=tz)
            payload, error = clarity.interpret(raw)
            if clarity.load(project_dir)["generation"] != binding["generation"]:
                report.update(collection_status="failed", reason_code="connection_changed", errors=["Connection changed during query; result discarded"])
                return _save(project_dir, kind, report)
            if error and error != "unstructured_response":
                report.update(collection_status="not_collected" if error in ("needs_runtime", "needs_auth", "busy") else "failed", reason_code=error, errors=[error])
                if error == "rate_limited":
                    clarity.private_write(project_dir, ".runtime/clarity/cooldown.json", {"until": (datetime.now(timezone.utc) + timedelta(seconds=60)).isoformat()})
                return _save(project_dir, kind, report)
            safe = sanitize(payload, kind=kind)
            report["response"] = safe
            report["response_shape"] = "list" if isinstance(payload, list) else "object"
            report["warnings"].append("Remote project identity has not been independently verified")
            # Only provider-confirmed range metadata can establish observed scope.
            scope = payload.get("scope") if isinstance(payload, dict) else None
            if isinstance(scope, dict) and all(scope.get(key) for key in ("startDate", "endDate", "timezone")):
                report["observed_scope"] = sanitize(scope, kind=kind)
            if action == "docs" and safe and not error:
                report.update(collection_status="ok", reason_code="reference_only")
            else:
                report.update(collection_status="partial", reason_code="unstructured_response" if error else "scope_unverified")
                report["warnings"].append("Exploratory evidence; do not merge into statistics or infer overall rates from recordings")
            return _save(project_dir, kind, report)
    except Timeout:
        report.update(reason_code="busy")
        # Do not race the running operation's latest pointer.
        return report
    except (OSError, ValueError, RuntimeError):
        report.update(collection_status="failed", reason_code="collection_error", errors=["Clarity collection could not complete"])
        return _save(project_dir, kind, report)
