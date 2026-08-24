from __future__ import annotations

import json
import math
from datetime import date, timedelta
from pathlib import Path
from typing import Any

from seo_workbench import state
from seo_workbench.locks import project_lock
from seo_workbench.tech_audit import link_scope, normalize_url
from seo_workbench_tools.files import atomic_write_text


HISTORY_DAYS = 120
GSC_METRICS = ("clicks", "impressions", "ctr", "position")
BUSINESS_METRICS = (
    "organic_sessions",
    "engaged_sessions",
    "key_events",
    "organic_product_views",
    "organic_add_to_carts",
    "organic_checkouts",
    "organic_purchases",
    "organic_revenue",
    "revenue",
    "orders",
)


def ingest_daily_history(
    project_dir: Path,
    *,
    gsc_path: Path | None = None,
    business_path: Path | None = None,
    retain_days: int = HISTORY_DAYS,
) -> dict[str, Any]:
    if retain_days < 28:
        raise ValueError("statistics history must retain at least 28 days")
    project_url = normalize_url(str((state.load_state(project_dir).get("project") or {}).get("url", "")))
    if not project_url:
        raise ValueError("project.url must be an absolute HTTP(S) URL")

    sources = {
        "gsc": gsc_path or state.safe_project_path(project_dir, "audits/gsc/search-analytics/latest.json"),
        "business": business_path or state.safe_project_path(project_dir, "audits/business-signals/latest.json"),
    }
    artifacts = {name: _read_artifact(path) for name, path in sources.items()}
    incoming = {
        "gsc": _gsc_rows(artifacts["gsc"], project_url),
        "business": _business_rows(artifacts["business"], project_url),
    }
    incoming_coverage = {
        "gsc": _coverage_dates(artifacts["gsc"], nested="date_page"),
        "business": _coverage_dates(artifacts["business"]),
    }
    paths = {
        name: state.safe_project_path(project_dir, f"audits/statistics/history/{name}-page-daily.jsonl")
        for name in sources
    }
    results: dict[str, Any] = {}
    with project_lock(project_dir):
        for name, rows in incoming.items():
            combined = {(row["date"], row["url"]): row for row in _read_history(paths[name])}
            combined.update({(row["date"], row["url"]): row for row in rows})
            if combined:
                newest = max(date.fromisoformat(day) for day, _url in combined)
                cutoff = newest - timedelta(days=retain_days - 1)
                combined = {key: row for key, row in combined.items() if date.fromisoformat(key[0]) >= cutoff}
            selected = [combined[key] for key in sorted(combined)]
            _write_history(paths[name], selected)
            results[name] = {
                "path": str(paths[name]),
                "ingested_rows": len(rows),
                "stored_rows": len(selected),
                "start_date": selected[0]["date"] if selected else "",
                "end_date": selected[-1]["date"] if selected else "",
            }
        coverage_path = state.safe_project_path(project_dir, "audits/statistics/history/coverage.json")
        coverage = load_history_coverage(project_dir)
        for name, dates in incoming_coverage.items():
            selected = set(coverage.get(name) or []) | dates
            if selected:
                newest = max(date.fromisoformat(day) for day in selected)
                cutoff = newest - timedelta(days=retain_days - 1)
                selected = {day for day in selected if date.fromisoformat(day) >= cutoff}
            coverage[name] = sorted(selected)
            results[name]["covered_days"] = len(coverage[name])
        atomic_write_text(
            coverage_path,
            json.dumps({"schema_version": "statistics-coverage-v1", "sources": coverage}, indent=2) + "\n",
            mode=0o600,
        )
    return {
        "schema_version": "statistics-history-v1",
        "collection_status": "ok",
        "retention_days": retain_days,
        "sources": results,
        "privacy": "Aggregated date-by-page metrics only; no user, event, customer, or order identifiers are stored.",
    }


def load_daily_history(project_dir: Path, source: str) -> list[dict[str, Any]]:
    if source not in {"gsc", "business"}:
        raise ValueError("statistics history source must be gsc or business")
    return _read_history(state.safe_project_path(project_dir, f"audits/statistics/history/{source}-page-daily.jsonl"))


def load_history_coverage(project_dir: Path) -> dict[str, list[str]]:
    path = state.safe_project_path(project_dir, "audits/statistics/history/coverage.json")
    if not path.exists():
        return {"gsc": [], "business": []}
    if path.is_symlink():
        raise ValueError(f"statistics coverage cannot be a symlink: {path}")
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ValueError(f"invalid statistics coverage: {path}") from exc
    sources = payload.get("sources") if isinstance(payload, dict) else {}
    return {
        name: [str(day) for day in (sources or {}).get(name, [])]
        for name in ("gsc", "business")
    }


def _read_artifact(path: Path) -> dict[str, Any]:
    if path.is_symlink() or not path.is_file():
        raise FileNotFoundError(f"statistics source artifact not found: {path}")
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ValueError(f"invalid statistics source artifact: {path}") from exc
    if not isinstance(payload, dict) or payload.get("collection_status") != "ok":
        raise ValueError(f"statistics source artifact is incomplete: {path}")
    return payload


def _gsc_rows(report: dict[str, Any], project_url: str) -> list[dict[str, Any]]:
    rows: dict[tuple[str, str], dict[str, Any]] = {}
    for window in (report.get("windows") or {}).values():
        evidence = (window or {}).get("date_page") or {}
        if evidence.get("truncated"):
            raise ValueError("GSC date-page evidence is truncated; refusing partial statistics history")
        for source in evidence.get("rows") or []:
            keys = source.get("keys") or []
            if len(keys) < 2:
                continue
            day = _day(keys[0])
            url = _url(keys[1], project_url)
            record = {"date": day, "url": url}
            record.update({metric: _number(source.get(metric), metric) for metric in GSC_METRICS})
            rows[(day, url)] = record
    return [rows[key] for key in sorted(rows)]


def _business_rows(report: dict[str, Any], project_url: str) -> list[dict[str, Any]]:
    rows: dict[tuple[str, str], dict[str, Any]] = {}
    for window in (report.get("windows") or {}).values():
        for source in (window or {}).get("daily_rows") or []:
            day = _day(source.get("date"))
            url = _url(source.get("url"), project_url)
            record = rows.setdefault((day, url), {"date": day, "url": url})
            for metric in BUSINESS_METRICS:
                if metric in source:
                    record[metric] = _number(
                        source.get(metric),
                        metric,
                        allow_negative=metric in {"organic_revenue", "revenue"},
                    )
    return [rows[key] for key in sorted(rows)]


def _coverage_dates(report: dict[str, Any], *, nested: str = "") -> set[str]:
    covered: set[str] = set()
    for window in (report.get("windows") or {}).values():
        evidence = ((window or {}).get(nested) or {}) if nested else (window or {})
        request = evidence.get("request") or {}
        try:
            start = date.fromisoformat(str(request.get("startDate") or ""))
            end = date.fromisoformat(str(request.get("endDate") or ""))
        except ValueError as exc:
            raise ValueError("statistics daily evidence must preserve exact request dates") from exc
        if start > end:
            raise ValueError("statistics daily evidence start date cannot be after end date")
        covered.update((start + timedelta(days=offset)).isoformat() for offset in range((end - start).days + 1))
    if not covered:
        raise ValueError("statistics daily evidence has no covered dates")
    return covered


def _read_history(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    if path.is_symlink():
        raise ValueError(f"statistics history cannot be a symlink: {path}")
    rows = []
    for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        if not line.strip():
            continue
        try:
            row = json.loads(line)
        except json.JSONDecodeError as exc:
            raise ValueError(f"invalid statistics history line {line_number}: {path}") from exc
        if not isinstance(row, dict):
            raise ValueError(f"invalid statistics history line {line_number}: expected an object")
        rows.append(row)
    return rows


def _write_history(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    atomic_write_text(path, "".join(json.dumps(row, ensure_ascii=False) + "\n" for row in rows), mode=0o600)


def _day(value: Any) -> str:
    try:
        return date.fromisoformat(str(value)).isoformat()
    except ValueError as exc:
        raise ValueError(f"statistics history date must be YYYY-MM-DD: {value}") from exc


def _url(value: Any, project_url: str) -> str:
    url = normalize_url(str(value or ""))
    if not url or link_scope(url, project_url)[1] not in {"same_host", "subdomain"}:
        raise ValueError(f"statistics history URL is outside the project site family: {value}")
    return url


def _number(value: Any, metric: str, *, allow_negative: bool = False) -> float:
    try:
        number = float(value or 0)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"statistics history metric must be numeric: {metric}") from exc
    if not math.isfinite(number) or (number < 0 and not allow_negative):
        raise ValueError(f"statistics history metric is invalid: {metric}")
    return number
