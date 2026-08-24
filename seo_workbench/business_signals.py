from __future__ import annotations

import csv
import json
import math
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any

from seo_workbench import state
from seo_workbench.tech_audit import link_scope, normalize_url
from seo_workbench_tools.files import atomic_write_text


METRICS = (
    "organic_sessions",
    "engaged_sessions",
    "key_events",
    "conversions",
    "organic_product_views",
    "organic_add_to_carts",
    "organic_checkouts",
    "organic_purchases",
    "organic_revenue",
    "revenue",
    "orders",
)
WINDOWS = ("previous", "current")


def import_business_signals(
    project_dir: Path,
    source_path: Path,
    *,
    now: datetime | None = None,
) -> tuple[dict[str, Any], Path]:
    rows = _source_rows(source_path)
    observed_metrics = [
        metric
        for metric in METRICS
        if any(metric in row and str(row.get(metric, "")).strip() != "" for row in rows)
    ]
    project_url = normalize_url(str((state.load_state(project_dir).get("project") or {}).get("url", "")))
    if not project_url:
        raise ValueError("project.url must be an absolute HTTP(S) URL")

    windows: dict[str, dict[str, Any]] = {}
    for name in WINDOWS:
        selected = [row for row in rows if str(row.get("window", "")).strip().lower() == name]
        if not selected:
            raise ValueError(f"business signals have no {name} rows")
        dates = {(_day(row.get("start_date"), "start_date"), _day(row.get("end_date"), "end_date")) for row in selected}
        if len(dates) != 1:
            raise ValueError(f"business signal {name} rows must share one date window")
        start, end = dates.pop()
        if start > end:
            raise ValueError(f"business signal {name} start_date cannot be after end_date")
        window_metrics = [
            metric
            for metric in observed_metrics
            if any(metric in row and str(row.get(metric, "")).strip() != "" for row in selected)
        ]
        aggregated: dict[str, dict[str, float]] = {}
        for row in selected:
            url = normalize_url(str(row.get("url", "")))
            if not url or link_scope(url, project_url)[1] not in {"same_host", "subdomain"}:
                raise ValueError(f"business signal URL is outside the project site family: {row.get('url', '')}")
            totals = aggregated.setdefault(url, {metric: 0.0 for metric in window_metrics})
            for metric in window_metrics:
                totals[metric] += _number(
                    row.get(metric, 0),
                    metric,
                    allow_negative=metric in {"organic_revenue", "revenue"},
                )
        windows[name] = {
            "request": {"startDate": start.isoformat(), "endDate": end.isoformat(), "dimensions": ["page"]},
            "rows": [
                {"url": url, **{metric: round(value, 4) for metric, value in totals.items()}}
                for url, totals in sorted(aggregated.items())
            ],
        }

    generated_at = (now or datetime.now(timezone.utc)).astimezone(timezone.utc)
    report = {
        "schema_version": "business-signals-v2",
        "collection_status": "ok",
        "generated_at": generated_at.isoformat(),
        "metrics": observed_metrics,
        "windows": windows,
        "source": {"path": str(source_path), "format": source_path.suffix.lower().lstrip(".") or "json"},
        "privacy": "Aggregated page-level data only; no user, event, customer, or order identifiers are stored.",
    }
    output_dir = state.safe_project_path(project_dir, "audits/business-signals")
    output_dir.mkdir(parents=True, exist_ok=True)
    path = output_dir / f"business-signals-{generated_at.strftime('%Y%m%dT%H%M%S%fZ')}.json"
    _write(path, report)
    _write(output_dir / "latest.json", report)
    return report, path


def _source_rows(path: Path) -> list[dict[str, Any]]:
    try:
        if path.suffix.lower() == ".csv":
            with path.open(encoding="utf-8-sig", newline="") as handle:
                rows = list(csv.DictReader(handle))
        else:
            payload = json.loads(path.read_text(encoding="utf-8"))
            rows = payload.get("rows") if isinstance(payload, dict) else payload
    except FileNotFoundError as exc:
        raise FileNotFoundError(f"business signal source not found: {path}") from exc
    except json.JSONDecodeError as exc:
        raise ValueError(f"invalid business signal JSON: {exc.msg}") from exc
    if not isinstance(rows, list) or not rows or any(not isinstance(row, dict) for row in rows):
        raise ValueError("business signal source must contain a non-empty row list")
    if not any(any(metric in row for metric in METRICS) for row in rows):
        raise ValueError(f"business signal source must include at least one metric: {', '.join(METRICS)}")
    invalid_window = next(
        (row.get("window") for row in rows if str(row.get("window", "")).strip().lower() not in WINDOWS),
        None,
    )
    if invalid_window is not None:
        raise ValueError(f"business signal window must be previous or current: {invalid_window}")
    return rows


def _day(value: Any, field: str) -> date:
    try:
        return date.fromisoformat(str(value))
    except ValueError as exc:
        raise ValueError(f"business signal {field} must be YYYY-MM-DD") from exc


def _number(value: Any, field: str, *, allow_negative: bool = False) -> float:
    try:
        number = float(value or 0)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"business signal {field} must be numeric") from exc
    if not math.isfinite(number) or (number < 0 and not allow_negative):
        raise ValueError(f"business signal {field} must be a valid finite number")
    return number


def _write(path: Path, report: dict[str, Any]) -> None:
    atomic_write_text(path, json.dumps(report, ensure_ascii=False, indent=2) + "\n", mode=0o600)
