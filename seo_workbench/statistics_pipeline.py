from __future__ import annotations

import json
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any

from seo_workbench import state
from seo_workbench.business_signals_merge import collect_business_signals
from seo_workbench.content_portfolio import analyze_content_portfolio
from seo_workbench.statistics_history import ingest_daily_history
from seo_workbench_tools import ga4_probe, gsc_probe, shopify_orders_probe
from seo_workbench_tools.files import atomic_write_text


def collect_statistics(
    project_dir: Path,
    *,
    days: int = 28,
    timeout: float = 30,
    today: date | None = None,
) -> tuple[dict[str, Any], Path]:
    """Collect comparable finalized evidence and refresh statistical guidance."""
    started = datetime.now(timezone.utc)
    steps: dict[str, dict[str, Any]] = {}
    active_step = "gsc"
    common_end = ""
    try:
        gsc = gsc_probe.collect_performance(
            project_dir,
            state.safe_project_path(project_dir, "audits/gsc/search-analytics"),
            days=days,
            compare=True,
            timeout=timeout,
            today=today,
        )
        _require_ok(gsc, "GSC")
        steps["gsc"] = _step(gsc)
        current_request = (((gsc.get("windows") or {}).get("current") or {}).get("page") or {}).get("request") or {}
        common_end_date = date.fromisoformat(str(current_request.get("endDate") or ""))
        common_end = common_end_date.isoformat()

        active_step = "ga4"
        ga4 = ga4_probe.collect(
            project_dir,
            state.safe_project_path(project_dir, "audits/ga4"),
            days=days,
            compare=True,
            timeout=timeout,
            end_date=common_end_date,
        )
        _require_ok(ga4, "GA4")
        steps["ga4"] = _step(ga4)

        active_step = "shopify"
        shopify = shopify_orders_probe.collect_orders(
            project_dir,
            days=days,
            timeout=timeout,
            end_date=common_end_date,
        )
        _require_ok(shopify, "Shopify")
        steps["shopify"] = _step(shopify)

        active_step = "business"
        business, business_path = collect_business_signals(project_dir)
        _require_comparable_windows(gsc, business)
        steps["business"] = {"status": "ok", "path": str(business_path)}
        active_step = "history"
        history = ingest_daily_history(project_dir)
        steps["history"] = {"status": "ok", "sources": history["sources"]}
        active_step = "portfolio"
        portfolio, portfolio_path = analyze_content_portfolio(project_dir)
        warnings = []
        if not portfolio.get("comparability", {}).get("comparable"):
            warnings.append("GSC measurement regime changed inside the comparison range")
        if not portfolio.get("source", {}).get("business_comparable"):
            warnings.append("business measurement regime changed inside the comparison range")
        steps["portfolio"] = {
            "status": "partial" if warnings else "ok",
            "path": str(portfolio_path),
            "count": portfolio.get("count", 0),
        }
        report = _report(
            started,
            "partial" if warnings else "ok",
            steps,
            common_end=common_end,
            warnings=warnings,
        )
    except (FileNotFoundError, RuntimeError, ValueError) as exc:
        steps[active_step] = {"status": "failed", "error": str(exc)}
        report = _report(started, "failed", steps, common_end=common_end, error=str(exc))
    return report, _write_report(project_dir, report)


def _require_ok(report: dict[str, Any], label: str) -> None:
    if report.get("collection_status") != "ok":
        raise RuntimeError(f"{label} collection did not complete")


def _require_comparable_windows(gsc: dict[str, Any], business: dict[str, Any]) -> None:
    for name in ("previous", "current"):
        gsc_request = (((gsc.get("windows") or {}).get(name) or {}).get("page") or {}).get("request") or {}
        business_request = ((business.get("windows") or {}).get(name) or {}).get("request") or {}
        if (gsc_request.get("startDate"), gsc_request.get("endDate")) != (
            business_request.get("startDate"),
            business_request.get("endDate"),
        ):
            raise ValueError(f"GSC and business {name} windows are not comparable")


def _step(report: dict[str, Any]) -> dict[str, Any]:
    return {
        "status": "ok",
        "path": str((report.get("manifest") or {}).get("path") or ""),
        "warning_count": len(report.get("warnings") or []),
    }


def _report(
    started: datetime,
    status: str,
    steps: dict[str, dict[str, Any]],
    *,
    common_end: str = "",
    error: str = "",
    warnings: list[str] | None = None,
) -> dict[str, Any]:
    return {
        "schema_version": "statistics-run-v1",
        "collection_status": status,
        "started_at": started.isoformat(),
        "completed_at": datetime.now(timezone.utc).isoformat(),
        "common_finalized_end_date": common_end,
        "steps": steps,
        "errors": [error] if error else [],
        "warnings": warnings or [],
        "privacy": "Run metadata and aggregate evidence paths only; no credentials or visitor/order identifiers.",
    }


def _write_report(project_dir: Path, report: dict[str, Any]) -> Path:
    output_dir = state.safe_project_path(project_dir, "audits/statistics")
    output_dir.mkdir(parents=True, exist_ok=True, mode=0o700)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
    path = output_dir / f"statistics-run-{stamp}.json"
    payload = json.dumps(report, ensure_ascii=False, indent=2) + "\n"
    atomic_write_text(path, payload, mode=0o600)
    atomic_write_text(output_dir / "latest.json", payload, mode=0o600)
    return path
