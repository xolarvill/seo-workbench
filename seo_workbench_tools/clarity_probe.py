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
COLLECTOR_VERSION = "1.2.0"
DEVICES = {"Mobile", "PC", "Tablet"}
CHANNELS = {"OrganicSearch", "Direct", "Email", "Display", "Social", "PaidSearch", "Other", "Affiliate", "Referral", "Video", "Audio", "SMS", "AITools", "PaidAITools"}
SAFE_KEYS = set("data result results metrics metric metricName metricValue information value values count total totalCount sessions sessionCount totalSessionCount totalBotSessionCount distinctUsers distantUserCount users pageViews pageviews average percentage rate scrollDepth engagementTime activeTime totalTime deadClickCount rageClickCount scriptErrorCount quickBackCount browser Browser device Device deviceType country Country channel Channel source Source medium Medium campaign Campaign url URL pageUrl entryUrl exitUrl startDate endDate start end timezone dateRange scope metadata title description text answer response observation documentation content snippets citations links duration sessionDuration pageCount pagesCount clickCount summary insights rows columns type label name unit date error status message recordingUrl recordingLink sessionUrl recordingLinkUrl".split())
IDENTIFIER = re.compile(r"token|secret|password|email|user.?id|session.?id|recording.?id|(^id$)|enteredtext|input|client.?id|visitor|ipaddress", re.I)
SAFE_NORMALIZED = {re.sub(r"[^a-z]", "", key.lower()) for key in SAFE_KEYS} | {"totalsessions", "totalusers", "dataerrortype", "timestamp", "totalduration", "activeduration", "sessionclickcount", "timeline", "fid", "cls", "lcp", "score", "referrerurl", "pageloadtime"}
# Exact aliases observed in official dashboard responses; arbitrary keys stay excluded.
SAFE_NORMALIZED |= {"homepageurl", "startdateutc", "enddateutc", "totalpageviews", "avgscrolldepthpercent",
                    "totaldeadclicks", "totalrageclicks", "totalquickbackclicks", "totalexcessivescrolls"}


def clean_text(value: str) -> str:
    value = re.sub(r"eyJ[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+", "[redacted-token]", value)
    value = re.sub(r"[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}", "[redacted-email]", value, flags=re.I)
    def clean_url(match):
        raw = match.group(0)
        try:
            parts = urlsplit(raw)
        except ValueError:
            return "[invalid-url]"
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
                for k, v in value.items() if re.sub(r"[^a-z]", "", k.lower()) in SAFE_NORMALIZED and not IDENTIFIER.search(k)
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


def _source_page(query: str, explicit: str | None = None) -> str | None:
    # Compatibility for the exact wording used by the first affected caller.
    # Other prose is not a contract parser: callers should use --source-page.
    match = re.search(r"Source page must be exactly (https://[^\s]+)", query, re.I)
    return explicit or (match.group(1).rstrip(".") if match else None)


def prepare(binding: dict, action: str, *, query: str = "", start: str = "", end: str = "", timezone_name: str | None = None, source_page: str | None = None,
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
        source_page = _source_page(query, source_page)
        source_clause = ""
        if source_page:
            page, site = urlsplit(source_page), urlsplit(binding["site_url"])
            if source_page != clean_text(source_page) or page.scheme != "https" or page.hostname != site.hostname or page.username or page.password or page.query or page.fragment or page.port not in (None, 443):
                raise ValueError("Click source page must be a clean same-site HTTPS URL")
            source_clause = f"\nClick events must occur on exactly {source_page}. EntryUrl and session VisitedUrl filters are not substitutes. Return unavailable if event-page scope cannot be established."
        try:
            first, last = date.fromisoformat(start), date.fromisoformat(end)
        except ValueError:
            raise ValueError("Dashboard dates must use YYYY-MM-DD") from None
        if first > last:
            raise ValueError("Clarity start must not be after end")
        return {"query": f"{query}\nWebsite: {binding['site_url']}. Date range: {start} through {end} inclusive. Timezone: {tz}. Use only this range and website.{source_clause}"}, tz
    if _utc(start) >= _utc(end):
        raise ValueError("Clarity start must be before end")
    if not 1 <= count <= 50 or device and device not in DEVICES or channel and channel not in CHANNELS:
        raise ValueError("Invalid Clarity count, device or channel")
    target = url or binding["site_url"]
    parts, site = urlsplit(target), urlsplit(binding["site_url"])
    if target != clean_text(target) or parts.scheme != "https" or parts.hostname != site.hostname or parts.username or parts.password or parts.query or parts.fragment or parts.port not in (None, 443):
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


def recording_links(payload: Any) -> list[str]:
    """Validated links for the transient local viewer, never for persisted evidence."""
    found: list[str] = []
    def visit(value, depth=0):
        if depth > 15 or len(found) >= 50:
            return
        if isinstance(value, dict):
            for item in value.values():
                visit(item, depth + 1)
        elif isinstance(value, list):
            for item in value[:1000]:
                visit(item, depth + 1)
        elif isinstance(value, str):
            for link in re.findall(r'https://[^\s<>"\)]+', value):
                try:
                    parts = urlsplit(link)
                    valid = parts.hostname in {"clarity.ms", "www.clarity.ms", "clarity.microsoft.com", "www.clarity.microsoft.com"} and not parts.username and not parts.password and parts.port in (None, 443)
                except ValueError:
                    continue
                if valid and re.search(r"/(player|recordings?)/", parts.path) and link not in found:
                    found.append(link)
    visit(payload)
    return found[:50]


def _persist(project_dir: Path, kind: str, report: dict) -> dict:
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
        index["sources"][kind] = {"path": relative, "collection_status": report["collection_status"], "generated_at": report["generated_at"],
                                  **{key: report[key] for key in ("transport_status", "scope_status", "identity_status", "capability_status") if key in report}}
        clarity.private_write(project_dir, "audits/clarity/latest.json", index)
    return report


def _save(project_dir: Path, kind: str, report: dict) -> dict:
    try:
        return _persist(project_dir, kind, report)
    except (OSError, ValueError):
        # Storage failures must not become tracebacks or claims of saved evidence.
        report.pop("manifest", None)
        report.update(collection_status="failed", reason_code="evidence_write_failed", errors=["Clarity evidence could not be saved"])
        return report


def _observations(value: Any, kind: str) -> bool:
    """Metadata and filtered empty objects are not observed metrics or samples."""
    if isinstance(value, dict):
        excluded = {"scope", "metadata", "daterange", "dataerrortype", "query", "date", "startdate", "enddate", "timezone", "siteurl"}
        return any(_observations(item, kind) for key, item in value.items() if re.sub(r"[^a-z]", "", key.lower()) not in excluded)
    if isinstance(value, list):
        return any(_observations(item, kind) for item in value)
    if isinstance(value, str):
        return bool(value.strip()) if kind != "dashboard" else bool(re.fullmatch(r"-?\d+(?:\.\d+)?%?", value))
    return isinstance(value, (int, float)) and not isinstance(value, bool)


def _omitted_numeric_fields(value: Any, depth: int = 0) -> int:
    """Count unsupported numeric leaves without recording unknown names or values."""
    if depth > 15:
        return 0
    if isinstance(value, list):
        return sum(_omitted_numeric_fields(item, depth + 1) for item in value[:1000])
    if not isinstance(value, dict):
        return 0
    count = 0
    for key, item in value.items():
        if IDENTIFIER.search(key):
            continue
        if re.sub(r"[^a-z]", "", key.lower()) not in SAFE_NORMALIZED:
            count += int(isinstance(item, (int, float)) and not isinstance(item, bool))
        else:
            count += _omitted_numeric_fields(item, depth + 1)
    return count


def _scope_quality(report: dict, payload: Any, action: str, binding: dict, options: dict, arguments: dict, tz: str) -> None:
    if action == "docs":
        report.update(scope_status="not_applicable", identity_status="not_applicable")
        return
    expected = {"startDate": options["start"], "endDate": options["end"], "timezone": tz, "site_url": binding["site_url"]}
    if action == "recordings":
        expected["filters"] = arguments["filters"]
    report["requested_scope"] = expected
    supplied = payload.get("scope") if isinstance(payload, dict) else None
    description = payload.get("query") if isinstance(payload, dict) else None
    if isinstance(description, str) and description.strip():
        report["provider_query_description"] = clean_text(description.replace(binding["token"], "[redacted-token]"))
        report["scope_status"] = "provider_described"
    if not isinstance(supplied, dict) or not supplied:
        return
    observed = {key: supplied[key] for key in expected if key in supplied}
    # Accept explicit URL aliases only as field names; never infer hostname aliases.
    if "site_url" not in observed:
        for alias in ("url", "website"):
            if alias in supplied:
                observed["site_url"] = supplied[alias]
                break
    report["observed_scope"] = {
        key: sanitize(value, kind=TOOLS[action][0]) if key != "site_url" else clean_text(str(value))
        for key, value in observed.items()
    }
    checks = {}
    for key, wanted in expected.items():
        if key not in observed:
            checks[key] = "unknown"
            continue
        actual = observed[key]
        if action == "recordings" and key in ("startDate", "endDate"):
            try:
                matched = _utc(actual) == _utc(wanted)
            except (ValueError, TypeError, AttributeError):
                matched = False
        elif key == "site_url":
            matched = isinstance(actual, str) and actual.rstrip("/") == wanted.rstrip("/")
        else:
            matched = actual == wanted
        checks[key] = "match" if matched else "mismatch"
    report["scope_checks"] = checks
    if "mismatch" in checks.values():
        report["scope_status"] = "mismatch"
    elif all(value == "match" for value in checks.values()):
        report["scope_status"] = "structured_match"


def _classify(report: dict, payload: Any, safe: Any, action: str, error: str | None) -> None:
    report["capability_status"] = "available"
    explicit_empty = isinstance(payload, list) and not payload or isinstance(payload, dict) and payload.get("data") == []
    if not _observations(safe, TOOLS[action][0]) and not explicit_empty:
        report.update(collection_status="partial", reason_code="unsupported_response", capability_status="unsupported_response")
        report["warnings"].append("The response has no recognized observations after redaction; it is not zero data")
        return
    if action == "docs" and not error:
        report.update(collection_status="ok", reason_code="reference_only")
        return
    scope_status = report["scope_status"]
    reason = {"mismatch": "scope_mismatch", "structured_match": "identity_unverified", "provider_described": "scope_provider_described"}.get(scope_status, "scope_incomplete" if report.get("observed_scope") is not None else "scope_unverified")
    report.update(collection_status="partial", reason_code="unstructured_response" if error else reason)
    report["warnings"].append("Remote project identity has not been independently verified")
    if scope_status == "provider_described":
        report["warnings"].append("Provider-described scope is explanatory text, not independent execution verification")
    if scope_status == "mismatch":
        report["warnings"].append("Provider scope conflicts with the request; do not use these observations for that window or site")
    if scope_status == "structured_match":
        report["warnings"].append("Structured match covers the explicit scope_checks fields, not every natural-language query condition")
    report["warnings"].append("Exploratory evidence; do not merge into statistics or infer overall rates from recordings")


def collect(project_dir: Path, action: str, *, caller: Callable = call, force: bool = False, transient_sink: Callable | None = None, **options) -> dict:
    if action not in TOOLS:
        raise ValueError("Unsupported Clarity operation")
    kind, tool = TOOLS[action]
    report: dict[str, Any] = {"schema_version": "clarity-evidence-v1", "provider": "microsoft-clarity-mcp",
        "server_version": SERVER_VERSION, "sdk_version": SDK_VERSION, "collector_version": COLLECTOR_VERSION, "generated_at": clarity.now(),
        "collection_status": "not_collected", "reason_code": "needs_config", "errors": [], "warnings": [], "cache_hit": False,
        "observed_scope": None, "identity_verified": False, "transport_status": "not_collected",
        "scope_status": "not_applicable" if action == "docs" else "unknown",
        "identity_status": "not_applicable" if action == "docs" else "operator_declared", "capability_status": "not_collected"}
    try:
        binding = clarity.load(project_dir)
    except (ValueError, OSError):
        return _save(project_dir, kind, report)
    arguments, tz = prepare(binding, action, **options)
    report.update(project_id=binding["project_id"], site_url=binding["site_url"], identity_source="operator_declared",
                  request={"tool": tool, "arguments": arguments, "timezone": tz})
    source_page = _source_page(options.get("query", ""), options.get("source_page")) if action == "query" else None
    if source_page:
        # Retain the task contract even if the provider fails before returning data.
        report["requested_scope"] = {"startDate": options["start"], "endDate": options["end"],
                                     "timezone": tz, "site_url": binding["site_url"], "source_page_url": source_page}
    cache_key = hashlib.sha256(json.dumps([str(project_dir.resolve()), binding["generation"], SERVER_VERSION, SDK_VERSION, COLLECTOR_VERSION, tool, arguments, tz], sort_keys=True).encode()).hexdigest()
    report["cache_key"] = cache_key
    try:
        with clarity.operation_lock(project_dir):
            try:
                clarity.check_cooldown(project_dir)
            except ValueError:
                report.update(reason_code="rate_limited", collection_status="not_collected")
                return _save(project_dir, kind, report)
            cache = state.safe_project_path(project_dir, f"audits/clarity/{kind}/latest.json")
            if not force and cache.exists():
                previous = json.loads(cache.read_text())
                if previous.get("collector_version") == COLLECTOR_VERSION and previous.get("cache_key") == cache_key and previous.get("capability_status") == "available" and previous.get("scope_status") != "mismatch" and previous.get("collection_status") in ("ok", "partial") and previous.get("response") is not None and datetime.fromisoformat(previous["generated_at"]) > datetime.now(timezone.utc) - timedelta(minutes=15):
                    return {**previous, "cache_hit": True}
            raw = caller(tool, arguments, token=binding["token"], timezone=tz)
            if isinstance(raw.get("http_status"), int):
                report["http_status"] = raw["http_status"]
            payload, error = clarity.interpret(raw)
            report["transport_status"] = "ok" if raw.get("ok") and error in (None, "unstructured_response") else "failed"
            if clarity.load(project_dir)["generation"] != binding["generation"]:
                report.update(collection_status="failed", reason_code="connection_changed", errors=["Connection changed during query; result discarded"])
                return _save(project_dir, kind, report)
            if error and error != "unstructured_response":
                report["capability_status"] = "unavailable"
                report.update(collection_status="not_collected" if error in ("needs_runtime", "needs_auth", "busy") else "failed", reason_code=error, errors=[error])
                if error == "rate_limited":
                    clarity.record_cooldown(project_dir)
                return _save(project_dir, kind, report)
            safe = sanitize(payload, kind=kind)
            if action == "recordings" and transient_sink:
                transient_sink({"links": recording_links(payload), "generation": binding["generation"], "created_at": clarity.now(), "cache_key": cache_key})
            report["response"] = safe
            if kind == "dashboard":
                omitted = _omitted_numeric_fields(payload)
                report["response_projection"] = {"omitted_numeric_fields": omitted}
                if omitted:
                    report["warnings"].append("Unsupported numeric fields were omitted by the safety allowlist; the saved response is incomplete")
            report["response_shape"] = "list" if isinstance(payload, list) else "object"
            _scope_quality(report, payload, action, binding, options, arguments, tz)
            _classify(report, payload, safe, action, error)
            if source_page:
                report["requested_scope"]["source_page_url"] = source_page
                description = report.get("provider_query_description", "")
                entry_substitution = bool(re.search(r"\bEntryUrl\s*=", description, re.I))
                report["scope_checks"] = {**report.get("scope_checks", {}), "click_source_page": "mismatch" if entry_substitution else "unknown"}
                report.update(collection_status="partial", capability_status="unsupported_scope",
                              reason_code="click_source_scope_conflict" if entry_substitution else "click_source_scope_unverified")
                if entry_substitution:
                    report["scope_status"] = "mismatch"
                report["warnings"].append("Click-event source page is not established. EntryUrl/session VisitedUrl cannot attribute clicks to a page or section; do not use these counts for that attribution")
            return _save(project_dir, kind, report)
    except Timeout:
        report.update(reason_code="busy")
        # Do not race the running operation's latest pointer.
        return report
    except (OSError, ValueError, RuntimeError):
        report.update(collection_status="failed", reason_code="collection_error", errors=["Clarity collection could not complete"])
        return _save(project_dir, kind, report)
