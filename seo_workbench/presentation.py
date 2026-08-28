from __future__ import annotations

import json
import os
import re
import tempfile
import textwrap
from collections import Counter
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from seo_workbench import state
from seo_workbench.report_archive import list_report_archive
from seo_workbench.seo_changes import list_changes
from seo_workbench_tools.files import atomic_write_text


PRESENTATION_DIR = "reports/presentations"
PRESENTATION_SCHEMA = "seo-presentation-v1"
DEFAULT_MAX_STATISTICS_AGE_HOURS = 72
MAX_FINALIZED_LAG_DAYS = 3
MIN_HISTORY_DAYS = 28
FRIDAY_START_HOUR = 16
PRESENTATION_PATTERN = re.compile(r"^(?P<year>\d{4})_week_(?P<week>\d{2})\.pdf$")


class PresentationNotReadyError(ValueError):
    def __init__(self, status: dict[str, Any]) -> None:
        self.status = status
        failed = [check["label"] for check in status.get("checks", []) if not check.get("passed") and check.get("required")]
        detail = ", ".join(failed) or "data requirements"
        super().__init__(f"presentation data gate blocked: {detail}")


def presentation_pdf_path(project_dir: Path, year: int, week: int) -> Path:
    return state.safe_project_path(project_dir, f"{PRESENTATION_DIR}/{year}_week_{week:02d}.pdf")


def presentation_manifest_path(project_dir: Path, year: int, week: int) -> Path:
    return state.safe_project_path(project_dir, f"{PRESENTATION_DIR}/{year}_week_{week:02d}.json")


def presentation_due(project_dir: Path, *, now: datetime | None = None) -> bool:
    local_now = (now or datetime.now().astimezone()).astimezone()
    if local_now.weekday() != 4 or local_now.hour < FRIDAY_START_HOUR:
        return False
    iso = local_now.date().isocalendar()
    return not presentation_pdf_path(project_dir, iso.year, iso.week).is_file()


def presentation_status(
    project_dir: Path,
    *,
    now: datetime | None = None,
    year: int | None = None,
    week: int | None = None,
    max_statistics_age_hours: int = DEFAULT_MAX_STATISTICS_AGE_HOURS,
) -> dict[str, Any]:
    local_now = (now or datetime.now().astimezone()).astimezone()
    now_utc = local_now.astimezone(timezone.utc)
    target_year, target_week = _target_week(local_now.date(), year=year, week=week)
    stats_path = state.safe_project_path(project_dir, "audits/statistics/latest.json")
    portfolio_path = state.safe_project_path(project_dir, "audits/content-portfolio/latest.json")
    stats = _optional_json(stats_path)
    portfolio = _optional_json(portfolio_path)
    checks: list[dict[str, Any]] = []

    stats_status = str(stats.get("collection_status") or "not_collected")
    checks.append(_check(
        "statistics_status",
        "Statistics collection",
        stats_status in {"ok", "partial"},
        f"status={stats_status}; partial results remain labelled in the deck" if stats else "latest statistics snapshot is missing",
    ))

    completed_at = _parse_datetime(stats.get("completed_at"))
    age_hours = round(max(0.0, (now_utc - completed_at).total_seconds() / 3600), 1) if completed_at else None
    fresh = completed_at is not None and age_hours is not None and age_hours <= max_statistics_age_hours
    checks.append(_check(
        "statistics_fresh",
        "Statistics freshness",
        fresh,
        f"completed {age_hours}h ago (limit {max_statistics_age_hours}h)" if age_hours is not None else "statistics completed_at is missing or invalid",
    ))

    finalized_end = _parse_date(stats.get("common_finalized_end_date"))
    finalized_lag = (local_now.date() - finalized_end).days if finalized_end else None
    finalized_ready = finalized_end is not None and 0 <= finalized_lag <= MAX_FINALIZED_LAG_DAYS
    checks.append(_check(
        "finalized_window",
        "Finalized GSC end date",
        finalized_ready,
        f"{finalized_end.isoformat()} ({finalized_lag}d behind report date)" if finalized_end else "common_finalized_end_date is missing",
    ))

    history = ((stats.get("steps") or {}).get("history") or {}).get("sources") or {}
    gsc_days = _int(((history.get("gsc") or {}).get("covered_days")))
    business_days = _int(((history.get("business") or {}).get("covered_days")))
    history_ready = min(gsc_days, business_days) >= MIN_HISTORY_DAYS
    checks.append(_check(
        "history_coverage",
        "Daily history coverage",
        history_ready,
        f"GSC {gsc_days}d / business {business_days}d (minimum {MIN_HISTORY_DAYS}d)",
    ))

    portfolio_status = str(portfolio.get("collection_status") or "not_collected")
    portfolio_step_status = str((((stats.get("steps") or {}).get("portfolio") or {}).get("status")) or "not_collected")
    portfolio_ready = portfolio_status in {"ok", "partial"} and portfolio_step_status in {"ok", "partial"}
    checks.append(_check(
        "portfolio_snapshot",
        "Portfolio snapshot",
        portfolio_ready,
        f"portfolio={portfolio_status}; statistics step={portfolio_step_status}" if portfolio else "latest portfolio snapshot is missing",
    ))

    ready = all(check["passed"] for check in checks if check["required"])
    warnings = [str(item) for item in stats.get("warnings") or [] if item]
    if stats_status == "partial" and not warnings:
        warnings.append("statistics collection is partial")
    status = "ready" if ready and stats_status == "ok" and not warnings else "ready_with_warnings" if ready else "blocked"
    artifact = _latest_artifact(project_dir, target_year, target_week)
    return {
        "schema_version": PRESENTATION_SCHEMA,
        "status": status,
        "ready": ready,
        "report_date": local_now.date().isoformat(),
        "target_week": {"year": target_year, "week": target_week},
        "max_statistics_age_hours": max_statistics_age_hours,
        "statistics": {
            "status": stats_status,
            "completed_at": stats.get("completed_at"),
            "age_hours": age_hours,
            "common_finalized_end_date": finalized_end.isoformat() if finalized_end else None,
        },
        "checks": checks,
        "warnings": warnings,
        "artifact": artifact,
    }


def generate_weekly_presentation(
    project_dir: Path,
    *,
    now: datetime | None = None,
    year: int | None = None,
    week: int | None = None,
    max_statistics_age_hours: int = DEFAULT_MAX_STATISTICS_AGE_HOURS,
) -> tuple[dict[str, Any], Path]:
    local_now = (now or datetime.now().astimezone()).astimezone()
    status = presentation_status(
        project_dir,
        now=local_now,
        year=year,
        week=week,
        max_statistics_age_hours=max_statistics_age_hours,
    )
    if not status["ready"]:
        raise PresentationNotReadyError(status)

    target_year = int(status["target_week"]["year"])
    target_week = int(status["target_week"]["week"])
    week_start = date.fromisocalendar(target_year, target_week, 1)
    week_friday = week_start + timedelta(days=4)
    period_end = min(week_friday, local_now.date()) if (target_year, target_week) == local_now.date().isocalendar()[:2] else week_friday
    payload = _build_payload(
        project_dir,
        status=status,
        year=target_year,
        week=target_week,
        period_start=week_start,
        period_end=period_end,
        generated_at=datetime.now(timezone.utc),
    )

    output_dir = state.safe_project_path(project_dir, PRESENTATION_DIR)
    output_dir.mkdir(parents=True, exist_ok=True, mode=0o700)
    pdf_path = presentation_pdf_path(project_dir, target_year, target_week)
    manifest_path = presentation_manifest_path(project_dir, target_year, target_week)
    temp_path = _temporary_path(output_dir, pdf_path.name)
    try:
        _render_pdf(payload, temp_path, project_dir)
        os.chmod(temp_path, 0o600)
        os.replace(temp_path, pdf_path)
    finally:
        Path(temp_path).unlink(missing_ok=True)

    manifest = {
        "schema_version": PRESENTATION_SCHEMA,
        "generated_at": payload["generated_at"],
        "report_date": status["report_date"],
        "period": {"start": week_start.isoformat(), "end": period_end.isoformat()},
        "week": {"year": target_year, "week": target_week},
        "readiness": status["status"],
        "statistics": status["statistics"],
        "sources": payload["sources"],
        "analysis": _manifest_analysis(payload.get("analysis") or {}),
        "pages": 4,
        "privacy": "Aggregate source summaries only; no credentials, customer identifiers, or order identifiers.",
    }
    atomic_write_text(manifest_path, json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", mode=0o600)
    result = {
        "schema_version": PRESENTATION_SCHEMA,
        "generated_at": payload["generated_at"],
        "report_date": status["report_date"],
        "period": manifest["period"],
        "week": manifest["week"],
        "readiness": status["status"],
        "path": _relative(project_dir, pdf_path),
        "manifest_path": _relative(project_dir, manifest_path),
        "pages": 4,
    }
    return result, pdf_path


def _build_payload(
    project_dir: Path,
    *,
    status: dict[str, Any],
    year: int,
    week: int,
    period_start: date,
    period_end: date,
    generated_at: datetime,
) -> dict[str, Any]:
    project = (state.load_state(project_dir).get("project") or {})
    stats = _optional_json(state.safe_project_path(project_dir, "audits/statistics/latest.json"))
    portfolio = _optional_json(state.safe_project_path(project_dir, "audits/content-portfolio/latest.json"))
    business = _optional_json(state.safe_project_path(project_dir, "audits/business-signals/latest.json"))
    crux = _optional_json(state.safe_project_path(project_dir, "audits/crux/latest.json"))
    performance = _optional_json(state.safe_project_path(project_dir, "audits/performance/latest.json"))
    tech = _optional_json(state.safe_project_path(project_dir, "audits/tech-audit/latest.json"))
    archive = list_report_archive(project_dir)
    weekly = next((item for item in archive["weekly"] if item["year"] == year and item["week"] == week), None)
    weekly_text = _read_project_file(project_dir, str(weekly["path"])) if weekly else ""
    changes = [
        item for item in list_changes(project_dir).get("changes", [])
        if _in_period(item.get("changed_at"), period_start, period_end)
    ]
    queue = [item for item in (state.load_state(project_dir).get("contentQueue") or []) if isinstance(item, dict)]
    stats_data = portfolio.get("statistics") or {}
    current_business = (business.get("windows") or {}).get("current") or {}
    current_rows = current_business.get("rows") or []
    decomp = stats_data.get("click_change_decomposition") or {}
    confidence = stats_data.get("search_change_confidence") or {}
    trend = stats_data.get("search_trend") or {}
    ranking = stats_data.get("ranking_opportunity") or {}
    query = stats_data.get("query_portfolio") or {}
    analysis = _analysis_summary(stats_data)
    clicks = analysis["headline"]
    source_paths = {
        "statistics": "audits/statistics/latest.json",
        "portfolio": "audits/content-portfolio/latest.json",
        "business": "audits/business-signals/latest.json",
        "crux": "audits/crux/latest.json",
        "performance": "audits/performance/latest.json",
        "technical_audit": "audits/tech-audit/latest.json",
        "weekly_work": str(weekly["path"]) if weekly else "",
        "seo_changes": "strategy/seo-changes.jsonl",
    }
    sources = {
        name: {
            "path": path,
            "status": _source_status(project_dir, path),
            "generated_at": _optional_json(state.safe_project_path(project_dir, path)).get("generated_at", "") if path.endswith(".json") else "",
        }
        for name, path in source_paths.items()
        if path
    }
    return {
        "schema_version": PRESENTATION_SCHEMA,
        "generated_at": generated_at.isoformat(),
        "project": {"name": str(project.get("name") or "SEO project"), "url": str(project.get("url") or "")},
        "period": {"start": period_start.isoformat(), "end": period_end.isoformat()},
        "week": {"year": year, "week": week},
        "readiness": status,
        "sources": sources,
        "analysis": analysis,
        "kpis": {
            "current_clicks": _number(clicks.get("current")),
            "previous_clicks": _number(clicks.get("previous")),
            "click_change": _number(clicks.get("change")),
            "current_ctr": _number((confidence.get("ctr") or {}).get("current", {}).get("estimate")),
            "current_queries": _int((query.get("current") or {}).get("observed_query_count")),
            "ranking_opportunity_impressions": _number(ranking.get("positions_4_20_impressions")),
            "weekly_clicks": [float(value) for value in trend.get("weekly_clicks") or [] if _is_number(value)],
            "funnel": {metric: _sum_rows(current_rows, metric) for metric in (
                "organic_sessions", "organic_product_views", "organic_add_to_carts", "organic_checkouts", "organic_purchases", "organic_revenue"
            )},
            "top_drivers": [
                {key: item.get(key) for key in ("query", "url", "click_change")}
                for item in (decomp.get("top_drivers") or [])[:5]
                if isinstance(item, dict)
            ],
        },
        "weekly_work": {
            "found": bool(weekly),
            "checked": int((weekly or {}).get("checked", 0)),
            "total": int((weekly or {}).get("total", 0)),
            "carry_over": int((weekly or {}).get("carry_over", 0)),
            "activities": _weekly_activities(weekly_text),
        },
        "seo_changes": {
            "count": len(changes),
            "status_counts": dict(Counter(str(item.get("status") or "unknown") for item in changes)),
            "items": [
                {"type": item.get("change_type", "other"), "status": item.get("status", "unknown"), "hypothesis": _clean_text(item.get("hypothesis", ""), 120)}
                for item in changes[:6]
            ],
        },
        "content": {"count": len(queue), "status_counts": dict(Counter(str(item.get("status") or "unknown") for item in queue))},
        "technical": _technical_summary(tech),
        "crux": _crux_summary(crux),
        "performance": {"status": performance.get("collection_status", "not_collected"), "generated_at": performance.get("generated_at", "")},
        "insights": _insights(stats_data, business, status, analysis),
    }


def _analysis_summary(stats: dict[str, Any]) -> dict[str, Any]:
    decomp = stats.get("click_change_decomposition") or {}
    observation = stats.get("query_observation")
    if isinstance(observation, dict) and observation:
        previous = observation.get("previous") or {}
        current = observation.get("current") or {}
        full_previous = _number(previous.get("full_page_clicks"))
        full_current = _number(current.get("full_page_clicks"))
        boundary = str(observation.get("attribution_boundary") or "Query-page coverage is incomplete; no cause is inferred.")
        clicks = {
            "status": str(observation.get("status") or "not_observed"),
            "basis": "full_page_rows" if full_previous is not None or full_current is not None else "not_observed",
            "previous": full_previous,
            "current": full_current,
            "change": _number(observation.get("full_click_change")),
        }
        query_observation = {
            "status": str(observation.get("status") or "not_observed"),
            "basis": "page_rows_vs_query_page_rows",
            "previous": previous,
            "current": current,
            "observed_query_click_change": _number(observation.get("observed_query_click_change")),
            "unattributed_click_change": _number(observation.get("unattributed_click_change")),
            "boundary": boundary,
        }
    else:
        clicks = {
            "status": "legacy",
            "basis": "not_observed_legacy",
            "previous": None,
            "current": None,
            "change": None,
        }
        query_observation = {
            "status": "legacy",
            "basis": "page_rows_vs_query_page_rows",
            "previous": {"full_page_clicks": None, "observed_query_page_clicks": _number(decomp.get("previous_observed_clicks")), "coverage_ratio": None, "unattributed_click_remainder": None},
            "current": {"full_page_clicks": None, "observed_query_page_clicks": _number(decomp.get("current_observed_clicks")), "coverage_ratio": None, "unattributed_click_remainder": None},
            "observed_query_click_change": _number(decomp.get("observed_click_change")),
            "unattributed_click_change": None,
            "boundary": "Legacy portfolio lacks full-page/query coverage fields; full-page headline is unavailable and query-page data is structural context only.",
        }

    confidence = stats.get("search_change_confidence") or {}
    confidence_change = confidence.get("click_change") or {}
    confidence_summary = {
        "status": confidence.get("status", "not_observed"),
        "direction": confidence_change.get("direction"),
        "ci95": confidence_change.get("ci95"),
        "evidence_grade": confidence.get("evidence_grade"),
    }
    trend = stats.get("search_trend") or {}
    trend_summary = {
        "status": trend.get("status", "not_observed"),
        "direction": trend.get("direction"),
        "weeks": trend.get("weeks"),
        "weekly_clicks": [float(value) for value in trend.get("weekly_clicks") or [] if _is_number(value)][-8:],
        "normalized_slope": _number(trend.get("normalized_slope")),
        "latest_anomaly": trend.get("latest_anomaly"),
        "latest_anomaly_score": _number(trend.get("latest_anomaly_score")),
    }
    date_page_previous = _number(confidence_change.get("previous"))
    date_page_current = _number(confidence_change.get("current"))
    date_page_change = _number(confidence_change.get("observed"))
    if confidence_summary["status"] == "ok" and None not in (date_page_previous, date_page_current, date_page_change):
        clicks.update(
            basis="full_date_page_history",
            status="ok",
            previous=date_page_previous,
            current=date_page_current,
            change=date_page_change,
        )
    headline = {
        "basis": clicks["basis"],
        "status": clicks["status"],
        "previous": clicks["previous"],
        "current": clicks["current"],
        "change": clicks["change"],
    }
    driver_items = [
        {key: item.get(key) for key in ("query", "url", "click_change")}
        for item in (decomp.get("top_drivers") or [])[:5]
        if isinstance(item, dict)
    ]
    return {
        "headline": headline,
        "headline_basis": headline["basis"],
        "verdict": {
            "search_change_direction": confidence_summary["direction"],
            "search_change_status": confidence_summary["status"],
            "evidence_grade": confidence_summary["evidence_grade"],
            "trend_direction": trend_summary["direction"],
            "click_basis": headline["basis"],
        },
        "clicks": clicks,
        "query_observation": query_observation,
        "search_confidence": confidence_summary,
        "trend": trend_summary,
        "query_drivers": {
            "basis": "observed query-page subset",
            "coverage": {
                "previous": query_observation["previous"].get("coverage_ratio"),
                "current": query_observation["current"].get("coverage_ratio"),
            },
            "items": driver_items,
            "boundary": query_observation["boundary"],
        },
    }


def _manifest_analysis(analysis: dict[str, Any]) -> dict[str, Any]:
    clicks = analysis.get("clicks") or {}
    headline = analysis.get("headline") or clicks
    query_observation = analysis.get("query_observation") or clicks.get("query_observation") or {}
    observed = {
        "previous": (query_observation.get("previous") or {}).get("observed_query_page_clicks"),
        "current": (query_observation.get("current") or {}).get("observed_query_page_clicks"),
        "change": query_observation.get("observed_query_click_change"),
    }
    coverage = {
        "previous": (query_observation.get("previous") or {}).get("coverage_ratio"),
        "current": (query_observation.get("current") or {}).get("coverage_ratio"),
    }
    remainder = {
        "previous": (query_observation.get("previous") or {}).get("unattributed_click_remainder"),
        "current": (query_observation.get("current") or {}).get("unattributed_click_remainder"),
        "change": query_observation.get("unattributed_click_change"),
    }
    confidence = analysis.get("search_confidence") or {}
    trend = analysis.get("trend") or {}
    drivers = analysis.get("query_drivers") or {}
    driver_items = [item for item in drivers.get("items") or [] if isinstance(item, dict)]
    return {
        "headline": {
            "basis": headline.get("basis"),
            "status": headline.get("status"),
            "previous": headline.get("previous"),
            "current": headline.get("current"),
            "change": headline.get("change"),
        },
        "headline_basis": headline.get("basis"),
        "verdict": analysis.get("verdict") or {},
        "clicks": {
            "status": clicks.get("status"),
            "basis": clicks.get("basis"),
            "previous": clicks.get("previous"),
            "current": clicks.get("current"),
            "change": clicks.get("change"),
            "observed_query_page": observed,
            "coverage": coverage,
            "unattributed_remainder": remainder,
            "boundary": clicks.get("boundary"),
        },
        "query_observation": {
            "status": query_observation.get("status"),
            "basis": query_observation.get("basis"),
            "previous": query_observation.get("previous") or {},
            "current": query_observation.get("current") or {},
            "observed_query_click_change": query_observation.get("observed_query_click_change"),
            "unattributed_click_change": query_observation.get("unattributed_click_change"),
            "boundary": query_observation.get("boundary"),
        },
        "search_confidence": confidence,
        "trend": {
            key: trend.get(key)
            for key in ("status", "direction", "weeks", "normalized_slope", "latest_anomaly", "latest_anomaly_score")
        },
        "query_drivers": {
            "basis": drivers.get("basis"),
            "coverage": coverage,
            "count": len(driver_items),
            "urls": [
                {"url": item.get("url"), "click_change": item.get("click_change")}
                for item in driver_items
                if item.get("url")
            ],
            "boundary": drivers.get("boundary"),
        },
    }


def _render_pdf(payload: dict[str, Any], output_path: Path, project_dir: Path) -> None:
    config_dir = state.safe_project_path(project_dir, ".runtime/presentation/matplotlib")
    config_dir.mkdir(parents=True, exist_ok=True, mode=0o700)
    os.environ.setdefault("MPLCONFIGDIR", str(config_dir))
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
        from matplotlib import font_manager
        from matplotlib.backends.backend_pdf import PdfPages
    except ImportError as exc:
        raise ValueError("presentation PDF generation requires the optional dependency: uv sync --extra presentation") from exc

    font_name, has_cjk = _font_choice(font_manager)
    colors = {
        "navy": "#102a43", "ink": "#123b63", "muted": "#7189a2", "canvas": "#f5f8fc",
        "surface": "#ffffff", "blue": "#126bff", "green": "#10b981", "amber": "#f59e0b", "red": "#ef4444",
        "line": "#d9e3f0", "soft": "#edf3fb",
    }
    with plt.rc_context({"font.family": font_name, "axes.unicode_minus": False}):
        with PdfPages(str(output_path), metadata={"Title": f"{payload['project']['name']} SEO weekly presentation", "Author": "SEO Workbench"}) as pdf:
            _render_cover(plt, pdf, payload, colors, has_cjk)
            _render_search(plt, pdf, payload, colors, has_cjk)
            _render_business(plt, pdf, payload, colors, has_cjk)
            _render_sources(plt, pdf, payload, colors, has_cjk)


def _render_cover(plt: Any, pdf: Any, payload: dict[str, Any], colors: dict[str, str], has_cjk: bool) -> None:
    fig = _page(plt, payload, colors, "Executive view", "SEO OPERATIONS WEEKLY PRESENTATION", 1, has_cjk)
    name = _display(payload["project"]["name"], has_cjk)
    period = payload["period"]
    fig.text(.06, .78, name, fontsize=28, weight="bold", color=colors["navy"])
    fig.text(.06, .735, f"Week {payload['week']['week']:02d} - {period['start']} -> {period['end']}", fontsize=13, color=colors["muted"])
    kpis = payload["kpis"]
    analysis = payload.get("analysis") or {}
    click_analysis = analysis.get("clicks") or {}
    delta = kpis["click_change"]
    delta_label = "No data" if delta is None else f"{delta:+,.0f}"
    delta_color = colors["green"] if isinstance(delta, (int, float)) and delta > 0 else colors["red"] if isinstance(delta, (int, float)) and delta < 0 else colors["muted"]
    _card(fig, .06, .53, .2, .14, "28d organic clicks", _num_label(kpis["current_clicks"]), f"vs { _num_label(kpis['previous_clicks']) } previous window", colors["blue"], colors)
    if click_analysis.get("basis") == "full_date_page_history":
        change_label, change_detail = "Date-page change", "full date x page history; descriptive"
    elif click_analysis.get("basis") == "full_page_rows":
        change_label, change_detail = "Full-page change", "page rows fallback; descriptive"
    else:
        change_label, change_detail = "Observed-query change", "query-page subset; not a headline"
    _card(fig, .28, .53, .2, .14, change_label, delta_label, change_detail, delta_color, colors)
    _card(fig, .50, .53, .2, .14, "Current CTR", _pct_label(kpis["current_ctr"]), f"{_num_label(kpis['current_queries'])} observed queries", colors["green"], colors)
    _card(fig, .72, .53, .22, .14, "Opportunity band", _num_label(kpis["ranking_opportunity_impressions"]), "impressions in positions 4-20", colors["amber"], colors)
    _section_text(fig, .06, .43, "What moved", [_display(item, has_cjk) for item in payload["insights"][:4]], colors)
    readiness = payload["readiness"]
    readiness_label = str(readiness["status"]).replace("_", " ").title()
    readiness_color = colors["green"] if readiness["status"] == "ready" else colors["amber"] if readiness["ready"] else colors["red"]
    _card(fig, .62, .25, .32, .16, "Data gate", readiness_label, _display(_gate_detail(readiness), has_cjk), readiness_color, colors)
    _footer(fig, payload, colors, 1, has_cjk)
    pdf.savefig(fig)
    plt.close(fig)


def _render_search(plt: Any, pdf: Any, payload: dict[str, Any], colors: dict[str, str], has_cjk: bool) -> None:
    fig = _page(plt, payload, colors, "Search visibility", "SEARCH PERFORMANCE", 2, has_cjk)
    click_analysis = (payload.get("analysis") or {}).get("query_observation") or {}
    values = payload["kpis"]["weekly_clicks"][-8:]
    ax = fig.add_axes((.06, .47, .56, .32), facecolor=colors["surface"])
    ax.set_title("8-week click trend", loc="left", color=colors["ink"], fontsize=13, pad=12, weight="bold")
    if values:
        ax.plot(range(1, len(values) + 1), values, color=colors["blue"], linewidth=2.5, marker="o", markersize=5)
        ax.fill_between(range(1, len(values) + 1), values, [min(values)] * len(values), color=colors["blue"], alpha=.08)
        ax.set_xticks(range(1, len(values) + 1), [f"W-{len(values) - index - 1}" if index < len(values) - 1 else "Now" for index in range(len(values))])
        ax.set_ylim(bottom=0)
        ax.grid(axis="y", color=colors["line"], linewidth=.7)
        ax.tick_params(colors=colors["muted"], labelsize=9)
    else:
        ax.text(.5, .5, "No weekly click series", ha="center", va="center", color=colors["muted"])
        ax.set_axis_off()
    for spine in ax.spines.values():
        spine.set_visible(False)
    _card(fig, .67, .61, .27, .15, "Current clicks", _num_label(payload["kpis"]["current_clicks"]), "28-day finalized window", colors["blue"], colors)
    _card(fig, .67, .43, .27, .15, "Current CTR", _pct_label(payload["kpis"]["current_ctr"]), "GSC confidence estimate", colors["green"], colors)
    _card(fig, .06, .24, .27, .14, "Ranking pool", _num_label(payload["kpis"]["ranking_opportunity_impressions"]), "positions 4-20 impressions", colors["amber"], colors)
    coverage = (click_analysis.get("current") or {}).get("coverage_ratio")
    coverage_detail = f"page-vs-query coverage: {_pct_label(coverage)}" if _is_number(coverage) else "page-vs-query coverage unavailable"
    _card(fig, .36, .24, .27, .14, "Observed queries", _num_label(payload["kpis"]["current_queries"]), coverage_detail, colors["blue"], colors)
    drivers = []
    for item in payload["kpis"]["top_drivers"][:4]:
        drivers.append(f"{_display(item.get('query') or 'query', has_cjk)}: {_num_label(item.get('click_change'))} clicks")
    _section_text(fig, .67, .28, "Observed-query drivers", drivers or ["No driver rows observed"], colors, size=10)
    _footer(fig, payload, colors, 2, has_cjk)
    pdf.savefig(fig)
    plt.close(fig)


def _render_business(plt: Any, pdf: Any, payload: dict[str, Any], colors: dict[str, str], has_cjk: bool) -> None:
    fig = _page(plt, payload, colors, "Business context and delivery", "SEO -> BUSINESS CONTEXT -> OPERATIONS", 3, has_cjk)
    funnel = payload["kpis"]["funnel"]
    labels = ["Sessions", "Product views", "Add to carts", "Checkouts", "Purchases"]
    values = [funnel.get(key) for key in ("organic_sessions", "organic_product_views", "organic_add_to_carts", "organic_checkouts", "organic_purchases")]
    ax = fig.add_axes((.12, .49, .37, .29), facecolor=colors["surface"])
    ax.set_title("Organic landing-page funnel", loc="left", color=colors["ink"], fontsize=13, pad=12, weight="bold")
    numeric = [value if isinstance(value, (int, float)) else 0 for value in values]
    if any(numeric):
        bars = ax.barh(labels[::-1], numeric[::-1], color=[colors["blue"], colors["green"], colors["amber"], "#8b5cf6", colors["red"]][::-1])
        ax.set_xlim(left=0)
        ax.grid(axis="x", color=colors["line"], linewidth=.7)
        ax.tick_params(colors=colors["muted"], labelsize=9)
        for bar, value in zip(bars, numeric[::-1]):
            ax.text(bar.get_width() + max(numeric) * .02, bar.get_y() + bar.get_height() / 2, _num_label(value), va="center", fontsize=9, color=colors["ink"])
    else:
        ax.text(.5, .5, "No business rows observed", ha="center", va="center", color=colors["muted"])
        ax.set_axis_off()
    for spine in ax.spines.values():
        spine.set_visible(False)
    _card(fig, .54, .62, .19, .16, "Organic revenue", _money_label(funnel.get("organic_revenue"), payload), "all-channel context only", colors["green"], colors)
    _card(fig, .75, .62, .19, .16, "Weekly work", f"{payload['weekly_work']['checked']}/{payload['weekly_work']['total']}", "checked items in archive", colors["blue"], colors)
    _card(fig, .54, .43, .19, .16, "SEO changes", _num_label(payload["seo_changes"]["count"]), "changed in this report week", colors["amber"], colors)
    _card(fig, .75, .43, .19, .16, "Content queue", _num_label(payload["content"]["count"]), "current items", colors["blue"], colors)
    activities = [_display(item, has_cjk) for item in payload["weekly_work"]["activities"][:3]]
    changes = [_display(item["hypothesis"], has_cjk) for item in payload["seo_changes"]["items"][:3]]
    _section_text(fig, .06, .24, "This week's delivery", activities or ["No weekly work archive found"], colors, size=10)
    _section_text(fig, .52, .24, "Change ledger", changes or ["No SEO changes recorded in this period"], colors, size=10)
    _footer(fig, payload, colors, 3, has_cjk)
    pdf.savefig(fig)
    plt.close(fig)


def _render_sources(plt: Any, pdf: Any, payload: dict[str, Any], colors: dict[str, str], has_cjk: bool) -> None:
    fig = _page(plt, payload, colors, "Sources and caveats", "EVIDENCE REGISTER", 4, has_cjk)
    fig.text(.06, .79, "What this deck can and cannot say", fontsize=18, weight="bold", color=colors["navy"])
    _section_text(fig, .06, .67, "Interpretation rules", [
        "GSC, GA4 and Shopify windows are aligned by the finalized GSC end date.",
        "Organic business signals are landing-page associated; Shopify product value is not SEO revenue attribution.",
        "Partial, incomparable, insufficient-data and not-observed states stay visible; missing values are not zero.",
        "SEO changes and weekly work are descriptive operating context, not proof of causal impact.",
    ], colors, size=10)
    for index, (name, source) in enumerate(payload["sources"].items()):
        column = index // 4
        row = index % 4
        status = str(source.get("status") or "not observed")
        color = colors["green"] if status == "ok" else colors["amber"] if status in {"partial", "incomparable"} else colors["muted"]
        _card(fig, .06 + column * .46, .30 - row * .08, .41, .07, name.replace("_", " ").title(), status, _display(source.get("path") or "", has_cjk), color, colors, compact=True)
    _footer(fig, payload, colors, 4, has_cjk)
    pdf.savefig(fig)
    plt.close(fig)


def _page(plt: Any, payload: dict[str, Any], colors: dict[str, str], title: str, kicker: str, page: int, has_cjk: bool) -> Any:
    fig = plt.figure(figsize=(13.333, 7.5), facecolor=colors["canvas"])
    fig.text(.06, .925, kicker, fontsize=9, weight="bold", color=colors["blue"], va="top")
    fig.text(.06, .87, title, fontsize=22, weight="bold", color=colors["navy"], va="top")
    fig.text(.94, .925, f"{payload['week']['year']} / W{payload['week']['week']:02d}", fontsize=9, color=colors["muted"], ha="right", va="top")
    return fig


def _footer(fig: Any, payload: dict[str, Any], colors: dict[str, str], page: int, has_cjk: bool) -> None:
    fig.text(.06, .035, f"SEO Workbench - generated {payload['generated_at'][:16].replace('T', ' ')} UTC", fontsize=8, color=colors["muted"])
    fig.text(.94, .035, f"{page} / 4", fontsize=8, color=colors["muted"], ha="right")


def _card(fig: Any, x: float, y: float, width: float, height: float, label: str, value: str, detail: str, accent: str, colors: dict[str, str], compact: bool = False) -> None:
    ax = fig.add_axes((x, y, width, height), facecolor=colors["surface"])
    ax.set_xticks([])
    ax.set_yticks([])
    for spine in ax.spines.values():
        spine.set_color(colors["line"])
        spine.set_linewidth(.8)
    ax.axvline(0, color=accent, linewidth=4)
    ax.text(.08, .76 if not compact else .73, label, fontsize=8 if compact else 9, color=colors["muted"], transform=ax.transAxes)
    ax.text(.08, .43 if not compact else .25, value, fontsize=16 if not compact else 9, weight="bold", color=colors["ink"], transform=ax.transAxes, va="center")
    if not compact:
        ax.text(.08, .13, detail, fontsize=8, color=colors["muted"], transform=ax.transAxes)
    else:
        ax.text(.98, .48, detail, fontsize=7, color=colors["muted"], transform=ax.transAxes, ha="right", va="center")
    ax.set_axis_off()


def _section_text(fig: Any, x: float, y: float, title: str, items: list[str], colors: dict[str, str], *, size: int = 11) -> None:
    fig.text(x, y, title, fontsize=11, weight="bold", color=colors["ink"])
    cursor = y - .045
    for item in items:
        lines = textwrap.wrap(item, width=66) or [item]
        fig.text(x, cursor, "- " + lines[0], fontsize=size, color=colors["muted"], va="top")
        cursor -= .032
        for continuation in lines[1:]:
            fig.text(x + .018, cursor, continuation, fontsize=size, color=colors["muted"], va="top")
            cursor -= .027


def _font_choice(font_manager: Any) -> tuple[str, bool]:
    for family in ("PingFang SC", "Hiragino Sans GB", "Noto Sans CJK SC", "Source Han Sans SC"):
        try:
            path = font_manager.findfont(family, fallback_to_default=False)
            return font_manager.FontProperties(fname=path).get_name(), True
        except (ValueError, OSError):
            continue
    return "DejaVu Sans", False


def _target_week(today: date, *, year: int | None, week: int | None) -> tuple[int, int]:
    if (year is None) != (week is None):
        raise ValueError("year and week must be supplied together")
    if year is None:
        iso = today.isocalendar()
        return iso.year, iso.week
    try:
        date.fromisocalendar(year, week, 1)
    except ValueError as exc:
        raise ValueError(f"invalid ISO week: {year}-W{week:02d}") from exc
    return year, week


def _check(code: str, label: str, passed: bool, detail: str, *, required: bool = True) -> dict[str, Any]:
    return {"code": code, "label": label, "passed": bool(passed), "required": required, "detail": detail}


def _latest_artifact(project_dir: Path, year: int, week: int) -> dict[str, Any] | None:
    target = presentation_pdf_path(project_dir, year, week)
    if target.is_file() and not target.is_symlink():
        manifest = _optional_json(presentation_manifest_path(project_dir, year, week))
        return {"path": _relative(project_dir, target), "manifest_path": _relative(project_dir, presentation_manifest_path(project_dir, year, week)), "size": target.stat().st_size, "generated_at": manifest.get("generated_at", ""), "week": {"year": year, "week": week}}
    root = state.safe_project_path(project_dir, PRESENTATION_DIR)
    candidates = [path for path in root.glob("*_week_*.pdf") if path.is_file() and not path.is_symlink()]
    if not candidates:
        return None
    latest = max(candidates, key=lambda path: path.stat().st_mtime)
    match = PRESENTATION_PATTERN.match(latest.name)
    return {"path": _relative(project_dir, latest), "size": latest.stat().st_size, "generated_at": "", "week": {"year": int(match.group("year")), "week": int(match.group("week"))} if match else None}


def _optional_json(path: Path) -> dict[str, Any]:
    if not path.is_file() or path.is_symlink():
        return {}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError, json.JSONDecodeError):
        return {}
    return payload if isinstance(payload, dict) else {}


def _read_project_file(project_dir: Path, relative: str) -> str:
    if not relative:
        return ""
    path = state.safe_project_path(project_dir, relative)
    if not path.is_file() or path.is_symlink():
        return ""
    try:
        return path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        return ""


def _source_status(project_dir: Path, relative: str) -> str:
    path = state.safe_project_path(project_dir, relative)
    if not path.is_file() or path.is_symlink():
        return "not_observed"
    payload = _optional_json(path) if path.suffix == ".json" else {}
    return str(payload.get("collection_status") or "ok") if path.suffix == ".json" else "ok"


def _technical_summary(payload: dict[str, Any]) -> dict[str, Any]:
    summary = payload.get("summary") or {}
    return {key: summary.get(key) for key in ("pages", "successful_pages", "issues", "issue_actions", "new_high_impact_actions", "error_count", "collection_status") if summary.get(key) is not None} | {"status": payload.get("collection_status", "not_collected")}


def _crux_summary(payload: dict[str, Any]) -> dict[str, Any]:
    summary = payload.get("summary") or {}
    result: dict[str, Any] = {"status": payload.get("collection_status", "not_collected")}
    for scope in ("aggregate", "mobile", "desktop"):
        item = summary.get(scope) or {}
        metrics = item.get("metrics") or {}
        lcp = metrics.get("largest_contentful_paint") or {}
        if lcp:
            result[scope] = {"core_web_vitals": item.get("core_web_vitals"), "lcp_p75": lcp.get("p75"), "lcp_rating": lcp.get("rating")}
    return result


def _weekly_activities(content: str) -> list[str]:
    section = ""
    activities: list[str] = []
    for line in content.splitlines():
        if line.startswith("## "):
            section = line[3:].strip().lower()
            continue
        if section in {"实质工作", "work done", "substantive work"} and line.startswith("### "):
            value = re.sub(r"^###\s+", "", line).strip()
            value = re.sub(r"^\d+\.\s*", "", value)
            if value:
                activities.append(_clean_text(value, 150))
    return activities[:6]


def _insights(
    stats: dict[str, Any],
    business: dict[str, Any],
    readiness: dict[str, Any],
    analysis: dict[str, Any] | None = None,
) -> list[str]:
    insights: list[str] = []
    analysis = analysis or _analysis_summary(stats)
    clicks = analysis.get("clicks") or {}
    query_observation = analysis.get("query_observation") or {}
    delta = clicks.get("change")
    if _is_number(delta):
        direction = "up" if float(delta) > 0 else "down" if float(delta) < 0 else "flat"
        label = "date-page-history organic clicks" if clicks.get("basis") == "full_date_page_history" else "full-page organic clicks" if clicks.get("basis") == "full_page_rows" else "observed query-page clicks"
        insights.append(f"Comparable 28-day {label} were {direction} by {abs(float(delta)):,.0f}; this is descriptive, not causal.")
    elif clicks.get("status") in {"incomparable", "partial"}:
        insights.append("Full-page click change is not fully comparable; keep the query-page subset as structural context only.")
    coverage = (query_observation.get("current") or {}).get("coverage_ratio")
    if _is_number(coverage) and clicks.get("basis") in {"full_date_page_history", "full_page_rows"}:
        insights.append(f"Observed query-page rows cover {_pct_label(coverage)} of current page-row clicks; this coverage is separate from the date-page headline.")
    ranking = stats.get("ranking_opportunity") or {}
    if _is_number(ranking.get("positions_4_20_impressions")):
        insights.append(f"The 4-20 ranking band carried {_number_label(ranking['positions_4_20_impressions'])} impressions of near-page-one opportunity.")
    current = (business.get("windows") or {}).get("current") or {}
    revenue = _sum_rows(current.get("rows") or [], "organic_revenue")
    if _is_number(revenue):
        insights.append(f"Organic landing-page revenue context was {_money_label(revenue, {'currency': business.get('currency', 'USD')})}; it is not SEO revenue attribution.")
    if readiness.get("warnings"):
        insights.append("One or more evidence windows are partial or regime-sensitive; interpret business and trend comparisons with the caveats on page 4.")
    return insights or ["No comparable movement was observed in the available evidence."]


def _sum_rows(rows: list[Any], metric: str) -> float | None:
    values = [float(row[metric]) for row in rows if isinstance(row, dict) and _is_number(row.get(metric))]
    return round(sum(values), 2) if values else None


def _in_period(value: Any, start: date, end: date) -> bool:
    parsed = _parse_date(value)
    return parsed is not None and start <= parsed <= end


def _parse_datetime(value: Any) -> datetime | None:
    if not value:
        return None
    try:
        parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except ValueError:
        return None
    return parsed.replace(tzinfo=timezone.utc) if parsed.tzinfo is None else parsed


def _parse_date(value: Any) -> date | None:
    try:
        return date.fromisoformat(str(value))
    except (TypeError, ValueError):
        return None


def _relative(project_dir: Path, path: Path) -> str:
    return path.relative_to(project_dir).as_posix()


def _temporary_path(directory: Path, name: str) -> Path:
    handle, raw = tempfile.mkstemp(prefix=f".{name}.", suffix=".tmp", dir=directory)
    os.close(handle)
    return Path(raw)


def _clean_text(value: Any, limit: int) -> str:
    text = re.sub(r"[`*_]", "", str(value or ""))
    return textwrap.shorten(re.sub(r"\s+", " ", text).strip(), width=limit, placeholder="...")


def _display(value: Any, has_cjk: bool) -> str:
    text = str(value or "")
    return text if has_cjk else text.encode("ascii", "ignore").decode() or "Recorded activity"


def _gate_detail(status: dict[str, Any]) -> str:
    if status.get("warnings"):
        return str(status["warnings"][0])
    return "All required source checks passed"


def _is_number(value: Any) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool)


def _number(value: Any) -> float | None:
    return float(value) if _is_number(value) else None


def _int(value: Any) -> int:
    return int(value) if _is_number(value) else 0


def _num_label(value: Any) -> str:
    return "No data" if not _is_number(value) else f"{float(value):,.0f}"


def _number_label(value: Any) -> str:
    return _num_label(value)


def _pct_label(value: Any) -> str:
    return "No data" if not _is_number(value) else f"{float(value) * 100:.2f}%"


def _money_label(value: Any, payload: dict[str, Any]) -> str:
    if not _is_number(value):
        return "No data"
    currency = str(payload.get("currency") or payload.get("business", {}).get("currency") or "USD")
    return f"{currency} {float(value):,.0f}"
