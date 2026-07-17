from __future__ import annotations

import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode, urlsplit
from urllib.request import Request, urlopen

from seo_workbench_tools.files import atomic_write_text
from seo_workbench_tools.network_boundary import validate_url


ROOT = Path(__file__).resolve().parent.parent
DEFAULT_OUTPUT_DIR = Path("projects/default/audits/crux")
API_KEY_PATH = ROOT / ".runtime/google/crux-api-key"
CURRENT_ENDPOINT = "https://chromeuxreport.googleapis.com/v1/records:queryRecord"
HISTORY_ENDPOINT = "https://chromeuxreport.googleapis.com/v1/records:queryHistoryRecord"
SCHEMA_VERSION = "1.0"
COLLECTOR_VERSION = "0.1.0"
DEFAULT_FORM_FACTORS = ("aggregate", "mobile", "desktop")
FORM_FACTORS = {
    "aggregate": None,
    "mobile": "PHONE",
    "desktop": "DESKTOP",
    "tablet": "TABLET",
}
METRICS = (
    "largest_contentful_paint",
    "interaction_to_next_paint",
    "cumulative_layout_shift",
    "first_contentful_paint",
    "experimental_time_to_first_byte",
)
CWV_METRICS = {
    "largest_contentful_paint": (2500.0, 4000.0),
    "interaction_to_next_paint": (200.0, 500.0),
    "cumulative_layout_shift": (0.1, 0.25),
}


class CruxNoData(RuntimeError):
    """The API has no record for the requested URL/origin and form factor."""


def _now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _timestamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")


def _slug(url: str) -> str:
    parsed = urlsplit(url)
    value = f"{parsed.hostname or 'site'}{parsed.path or '/'}"
    slug = "-".join(filter(None, (part.casefold() for part in __import__("re").split(r"[^a-zA-Z0-9]+", value))))
    return slug[:80] or "site"


def api_key() -> str:
    value = os.environ.get("SEO_WORKBENCH_CRUX_API_KEY", "").strip()
    if value:
        return value
    try:
        value = API_KEY_PATH.read_text(encoding="utf-8").strip()
    except OSError:
        value = ""
    if not value:
        raise RuntimeError(
            "CrUX API key is missing; set SEO_WORKBENCH_CRUX_API_KEY or write it to .runtime/google/crux-api-key"
        )
    return value


def post_json(endpoint: str, body: dict[str, Any], key: str, timeout: float) -> dict[str, Any]:
    request = Request(
        f"{endpoint}?{urlencode({'key': key})}",
        data=json.dumps(body).encode("utf-8"),
        headers={"Accept": "application/json", "Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urlopen(request, timeout=timeout) as response:
            payload = json.load(response)
    except HTTPError as exc:
        if exc.code == 404:
            raise CruxNoData("CrUX has no data for this scope and form factor") from exc
        detail = f"CrUX API returned HTTP {exc.code}"
        if exc.code == 429:
            detail += " (rate limit exceeded)"
        raise RuntimeError(detail) from exc
    except (URLError, TimeoutError) as exc:
        raise RuntimeError(f"CrUX API request failed: {getattr(exc, 'reason', exc).__class__.__name__}") from exc
    if not isinstance(payload, dict):
        raise RuntimeError("CrUX API returned a non-object JSON value")
    return payload


def _p75(metric: dict[str, Any], *, history: bool = False) -> Any:
    if history:
        values = metric.get("percentilesTimeseries", {}).get("p75s", [])
        return values[-1] if isinstance(values, list) and values else None
    return metric.get("percentiles", {}).get("p75")


def classify(metric: str, value: Any) -> str:
    if metric not in CWV_METRICS or value is None:
        return "unknown"
    try:
        number = float(value)
    except (TypeError, ValueError):
        return "unknown"
    good, poor = CWV_METRICS[metric]
    if number <= good:
        return "good"
    if number <= poor:
        return "needs_improvement"
    return "poor"


def summarize_record(payload: dict[str, Any], *, history: bool = False) -> dict[str, Any]:
    record = payload.get("record", {})
    metrics = record.get("metrics", {}) if isinstance(record, dict) else {}
    summaries: dict[str, Any] = {}
    for name, metric in metrics.items():
        if not isinstance(metric, dict):
            continue
        value = _p75(metric, history=history)
        item: dict[str, Any] = {"p75": value, "rating": classify(name, value)}
        if history:
            values = metric.get("percentilesTimeseries", {}).get("p75s", [])
            if isinstance(values, list):
                numeric = [float(value) for value in values if value is not None]
                if len(numeric) >= 2:
                    item["first_p75"] = numeric[0]
                    item["delta"] = round(numeric[-1] - numeric[0], 4)
        summaries[name] = item
    ratings = [summaries.get(name, {}).get("rating", "unknown") for name in CWV_METRICS]
    known = [rating for rating in ratings if rating != "unknown"]
    if len(known) < len(CWV_METRICS):
        overall = "unknown"
    elif "poor" in known:
        overall = "poor"
    elif "needs_improvement" in known:
        overall = "needs_improvement"
    else:
        overall = "good"
    return {
        "key": record.get("key", {}) if isinstance(record, dict) else {},
        "metrics": summaries,
        "core_web_vitals": overall,
        "collection_periods": record.get("collectionPeriods", []) if history and isinstance(record, dict) else [],
        "url_normalization": payload.get("urlNormalizationDetails", {}),
    }


def _request_body(scope: str, value: str, form_factor: str, *, history: bool) -> dict[str, Any]:
    body: dict[str, Any] = {scope: value, "metrics": list(METRICS)}
    api_factor = FORM_FACTORS[form_factor]
    if api_factor:
        body["formFactor"] = api_factor
    if history:
        body["collectionPeriodCount"] = 40
    return body


def _query(
    endpoint: str,
    scope: str,
    value: str,
    form_factor: str,
    key: str,
    timeout: float,
    requester: Callable[[str, dict[str, Any], str, float], dict[str, Any]],
    *,
    history: bool,
) -> dict[str, Any]:
    return requester(endpoint, _request_body(scope, value, form_factor, history=history), key, timeout)


def collect(
    url: str,
    output_dir: Path,
    *,
    form_factors: tuple[str, ...] | list[str] = DEFAULT_FORM_FACTORS,
    timeout: float = 15,
    key: str | None = None,
    requester: Callable[[str, dict[str, Any], str, float], dict[str, Any]] = post_json,
) -> dict[str, Any]:
    url = validate_url(url)
    if not 1 <= timeout <= 120:
        raise ValueError("timeout must be between 1 and 120 seconds")
    selected = tuple(dict.fromkeys(form_factors))
    if not selected or any(item not in FORM_FACTORS for item in selected):
        raise ValueError("form_factors must contain aggregate, mobile, desktop, or tablet")
    key = key or api_key()
    origin = f"{urlsplit(url).scheme}://{urlsplit(url).netloc}"
    queries: list[dict[str, Any]] = []
    errors: list[dict[str, Any]] = []
    warnings: list[dict[str, Any]] = []

    for form_factor in selected:
        effective_scope = "url"
        effective_value = url
        fallback_reason = ""
        try:
            current = _query(CURRENT_ENDPOINT, "url", url, form_factor, key, timeout, requester, history=False)
        except CruxNoData:
            effective_scope = "origin"
            effective_value = origin
            fallback_reason = "page_data_unavailable"
            try:
                current = _query(
                    CURRENT_ENDPOINT, "origin", origin, form_factor, key, timeout, requester, history=False
                )
                warnings.append(
                    {
                        "scope": "crux",
                        "form_factor": form_factor,
                        "code": "origin_fallback",
                        "message": "Page-level CrUX data unavailable; origin data was used",
                    }
                )
            except CruxNoData:
                queries.append(
                    {
                        "form_factor": form_factor,
                        "requested_scope": "url",
                        "effective_scope": "none",
                        "fallback_reason": "page_and_origin_data_unavailable",
                        "collection_status": "no_data",
                        "current": {},
                        "history": {},
                    }
                )
                continue
            except RuntimeError as exc:
                errors.append({"scope": "crux", "form_factor": form_factor, "message": str(exc)})
                continue
        except RuntimeError as exc:
            errors.append({"scope": "crux", "form_factor": form_factor, "message": str(exc)})
            continue

        history_payload: dict[str, Any] = {}
        history_status = "ok"
        try:
            history_payload = _query(
                HISTORY_ENDPOINT,
                effective_scope,
                effective_value,
                form_factor,
                key,
                timeout,
                requester,
                history=True,
            )
        except CruxNoData:
            history_status = "no_data"
            warnings.append(
                {
                    "scope": "crux",
                    "form_factor": form_factor,
                    "code": "history_unavailable",
                    "message": "CrUX history is unavailable for the effective scope",
                }
            )
        except RuntimeError as exc:
            history_status = "failed"
            errors.append({"scope": "crux_history", "form_factor": form_factor, "message": str(exc)})
        queries.append(
            {
                "form_factor": form_factor,
                "requested_scope": "url",
                "effective_scope": effective_scope,
                "effective_value": effective_value,
                "fallback_reason": fallback_reason,
                "collection_status": "ok" if history_status in {"ok", "no_data"} else "partial",
                "current": {"summary": summarize_record(current), "raw": current},
                "history": {
                    "collection_status": history_status,
                    "summary": summarize_record(history_payload, history=True) if history_payload else {},
                    "raw": history_payload,
                },
            }
        )

    successful = [item for item in queries if item.get("current")]
    no_data = [item for item in queries if item.get("collection_status") == "no_data"]
    if successful and errors:
        status = "partial"
    elif successful:
        status = "ok"
    elif no_data and not errors:
        status = "no_data"
    else:
        status = "failed"
    report: dict[str, Any] = {
        "schema_version": SCHEMA_VERSION,
        "collector_version": COLLECTOR_VERSION,
        "generated_at": _now(),
        "collection_status": status,
        "requested_url": url,
        "queries": queries,
        "summary": {
            item["form_factor"]: item.get("current", {}).get("summary", {}) for item in successful
        },
        "network_boundary": {
            "provider": "chromeuxreport.googleapis.com",
            "target_site_requested": False,
            "credentials_persisted": False,
        },
        "errors": errors,
        "warnings": warnings,
    }
    output_dir.mkdir(parents=True, exist_ok=True, mode=0o700)
    path = output_dir / f"crux-{_slug(url)}-{_timestamp()}.json"
    report["manifest"] = {"path": str(path), "latest_path": str(output_dir / "latest.json")}
    content = json.dumps(report, ensure_ascii=False, indent=2) + "\n"
    atomic_write_text(path, content, mode=0o600)
    atomic_write_text(output_dir / "latest.json", content, mode=0o600)
    return report


def collect_from_state(
    state_path: Path,
    output_dir: Path,
    *,
    url: str | None = None,
    form_factors: tuple[str, ...] | list[str] = DEFAULT_FORM_FACTORS,
    timeout: float = 15,
) -> Path:
    data = json.loads(state_path.read_text(encoding="utf-8"))
    target = url or data.get("project", {}).get("url", "")
    if not target:
        raise ValueError(f"missing project.url in {state_path}")
    report = collect(target, output_dir, form_factors=form_factors, timeout=timeout)
    return Path(report["manifest"]["path"])


def main(argv: list[str] | None = None) -> int:
    import argparse

    parser = argparse.ArgumentParser(description="Collect Chrome UX Report field performance evidence.")
    parser.add_argument("url")
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--form-factor", action="append", choices=tuple(FORM_FACTORS))
    parser.add_argument("--timeout", type=float, default=15)
    parser.add_argument("--print", action="store_true", dest="print_json")
    args = parser.parse_args(argv)
    try:
        report = collect(
            args.url,
            args.output_dir,
            form_factors=args.form_factor or DEFAULT_FORM_FACTORS,
            timeout=args.timeout,
        )
    except (RuntimeError, ValueError) as exc:
        if args.print_json:
            json.dump({"ok": False, "error": str(exc)}, sys.stdout, ensure_ascii=False, indent=2)
            print()
            return 1
        raise SystemExit(str(exc)) from exc
    if args.print_json:
        json.dump(report, sys.stdout, ensure_ascii=False, indent=2)
        print()
    return 0 if report["collection_status"] != "failed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
