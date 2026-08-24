from __future__ import annotations

import json
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

from seo_workbench import state
from seo_workbench.tech_audit import load_tech_issues


SCHEMA_VERSION = "1.0"
DIFF_VERSION = "0.1.0"
AUDIT_KINDS = ("raw", "technology", "performance", "crux", "gsc", "tech-audit")
EXPECTED_CONTRACTS = {
    "raw": {"schema_version": "1.0", "collector_version": "0.6.0"},
    # Technology has two provider-specific detector contracts. Snapshot identity
    # already requires matching detector/provider versions before comparison.
    "technology": {"schema_version": "1.0"},
    "performance": {"schema_version": "1.0", "runner_version": "0.1.0"},
    "crux": {"schema_version": "1.0", "collector_version": "0.1.0"},
    "gsc": {"schema_version": "1.0", "collector_version": "0.1.0"},
    "tech-audit": {"schema_version": "1.0", "collector_version": "0.1.0"},
}
PERFORMANCE_METRICS = (
    "first-contentful-paint",
    "largest-contentful-paint",
    "speed-index",
    "total-blocking-time",
    "cumulative-layout-shift",
    "interactive",
)


def _kind_root(project_dir: Path, kind: str) -> Path:
    if kind not in AUDIT_KINDS:
        raise ValueError(f"unsupported audit kind: {kind}")
    return state.safe_project_path(project_dir, Path("audits") / kind)


def _atomic_write_json(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w", encoding="utf-8", dir=path.parent, prefix=f".{path.name}.", suffix=".tmp", delete=False
        ) as handle:
            temporary = Path(handle.name)
            json.dump(data, handle, ensure_ascii=False, indent=2)
            handle.write("\n")
        temporary.chmod(0o600)
        temporary.replace(path)
    finally:
        if temporary and temporary.exists():
            temporary.unlink()


def _load(path: Path) -> dict[str, Any]:
    data = state.read_json(path)
    if not isinstance(data, dict):
        raise ValueError(f"audit snapshot must be a JSON object: {path}")
    return data


def _snapshot_patterns(project_dir: Path, kind: str) -> list[Path]:
    if kind == "raw":
        return list(_kind_root(project_dir, kind).glob("evidence-*.json"))
    if kind == "technology":
        return list(_kind_root(project_dir, kind).glob("technology-*.json"))
    if kind == "performance":
        return list(_kind_root(project_dir, kind).glob("performance-*/summary.json"))
    if kind == "crux":
        return list(_kind_root(project_dir, kind).glob("crux-*.json"))
    if kind == "gsc":
        return list(_kind_root(project_dir, kind).glob("gsc-*.json"))
    if kind == "tech-audit":
        return list(_kind_root(project_dir, kind).glob("tech-audit-*.json"))
    raise ValueError(f"unsupported audit kind: {kind}")


def _snapshot_sort_key(path: Path) -> tuple[float, str]:
    try:
        raw_generated_at = str(_load(path).get("generated_at", ""))
        generated_at = datetime.fromisoformat(raw_generated_at.replace("Z", "+00:00"))
        if generated_at.tzinfo is None:
            generated_at = generated_at.replace(tzinfo=timezone.utc)
        timestamp = generated_at.timestamp()
    except (OSError, ValueError, json.JSONDecodeError):
        timestamp = path.stat().st_mtime
    return timestamp, str(path)


def snapshots(project_dir: Path, kind: str) -> list[Path]:
    audit_root = _kind_root(project_dir, kind).resolve()
    return sorted(
        (
            path
            for path in _snapshot_patterns(project_dir, kind)
            if path.is_file() and path.resolve().is_relative_to(audit_root)
        ),
        key=_snapshot_sort_key,
    )


def _explicit_snapshot(project_dir: Path, kind: str, path: Path) -> Path:
    if path.is_symlink():
        raise ValueError(f"explicit snapshot cannot be a symlink: {path}")
    resolved = path.resolve()
    audit_root = _kind_root(project_dir, kind).resolve()
    if not resolved.is_relative_to(audit_root):
        raise ValueError(f"explicit snapshots must stay inside {audit_root}: {path}")
    if not resolved.is_file():
        raise FileNotFoundError(f"audit snapshot not found: {path}")
    return resolved


def snapshot_pair(
    project_dir: Path,
    kind: str,
    baseline_path: Path | None = None,
    current_path: Path | None = None,
) -> tuple[Path | None, Path | None]:
    if bool(baseline_path) != bool(current_path):
        raise ValueError("--from and --to must be used together")
    if baseline_path and current_path:
        baseline = _explicit_snapshot(project_dir, kind, baseline_path)
        current = _explicit_snapshot(project_dir, kind, current_path)
        if baseline == current:
            raise ValueError("baseline and current snapshots must be different files")
        if _snapshot_identity(kind, _load(baseline)) != _snapshot_identity(kind, _load(current)):
            raise ValueError(f"explicit {kind} snapshots must have the same audit identity")
        return baseline, current
    found = snapshots(project_dir, kind)
    if not found:
        return None, None
    if len(found) == 1:
        return None, found[0]
    current = found[-1]
    try:
        current_identity = _snapshot_identity(kind, _load(current))
    except (OSError, ValueError, json.JSONDecodeError):
        return found[-2], current
    matching = []
    for path in found[:-1]:
        try:
            if _snapshot_identity(kind, _load(path)) == current_identity:
                matching.append(path)
        except (OSError, ValueError, json.JSONDecodeError):
            continue
    return (matching[-1] if matching else None), current


def _snapshot_identity(kind: str, snapshot: dict[str, Any]) -> tuple[Any, ...]:
    if kind == "raw":
        pages = snapshot.get("pages", [])
        url = snapshot.get("seed_url") or next((_page_key(page) for page in pages if _page_key(page)), "")
        return (url, snapshot.get("schema_version"), snapshot.get("collector_version"))
    if kind == "technology":
        pages = snapshot.get("pages", [])
        url = next((_page_key(page) for page in pages if _page_key(page)), "")
        return (
            url,
            snapshot.get("schema_version"),
            snapshot.get("detector_version"),
            snapshot.get("provider"),
            snapshot.get("provider_version"),
        )
    if kind == "performance":
        return (
            snapshot.get("requested_url") or snapshot.get("url"),
            snapshot.get("final_url"),
            snapshot.get("schema_version"),
            snapshot.get("runner_version"),
            snapshot.get("lighthouse_version"),
            snapshot.get("form_factor"),
            snapshot.get("runs_requested"),
            _nested(snapshot, "environment.browser_version", ""),
        )
    if kind == "crux":
        query_identity = tuple(
            sorted(
                (
                    item.get("form_factor"),
                    item.get("effective_scope"),
                    item.get("effective_value", ""),
                )
                for item in snapshot.get("queries", [])
            )
        )
        return (
            snapshot.get("requested_url"),
            snapshot.get("schema_version"),
            snapshot.get("collector_version"),
            query_identity,
        )
    if kind == "gsc":
        search = snapshot.get("components", {}).get("search_analytics", {})
        return (
            snapshot.get("property"),
            snapshot.get("schema_version"),
            snapshot.get("collector_version"),
            search.get("search_type"),
            search.get("data_state"),
            search.get("window_days"),
            search.get("compare"),
        )
    if kind == "tech-audit":
        return (
            snapshot.get("seed_url"),
            snapshot.get("schema_version"),
            snapshot.get("collector_version"),
        )
    raise ValueError(f"unsupported audit kind: {kind}")


def _contract_comparability(kind: str, baseline: dict[str, Any], current: dict[str, Any]) -> tuple[bool, list[str]]:
    warnings = []
    for field, expected in EXPECTED_CONTRACTS[kind].items():
        before = baseline.get(field)
        after = current.get(field)
        if before != expected or after != expected:
            warnings.append(f"{kind} {field} must be {expected!r}: {before!r} -> {after!r}")
    return not warnings, warnings


def _change(
    scope: str,
    field: str,
    before: Any,
    after: Any,
    classification: str = "change",
    key: str = "",
    significant: bool = True,
    delta: float | None = None,
    delta_percent: float | None = None,
) -> dict[str, Any]:
    item: dict[str, Any] = {
        "scope": scope,
        "field": field,
        "before": before,
        "after": after,
        "classification": classification,
        "significant": significant,
    }
    if key:
        item["key"] = key
    if delta is not None:
        item["delta"] = round(delta, 4)
    if delta_percent is not None:
        item["delta_percent"] = round(delta_percent, 2)
    return item


def _summary(changes: list[dict[str, Any]]) -> dict[str, int]:
    return {
        "changes": len(changes),
        "regressions": sum(item["classification"] == "regression" and item["significant"] for item in changes),
        "improvements": sum(item["classification"] == "improvement" and item["significant"] for item in changes),
    }


def _page_key(page: dict[str, Any]) -> str:
    return str(page.get("url") or page.get("final_url") or "")


def _nested(data: dict[str, Any], path: str, default: Any = None) -> Any:
    value: Any = data
    for part in path.split("."):
        if not isinstance(value, dict):
            return default
        value = value.get(part, default)
    return value


def _numeric_classification(before: Any, after: Any, lower_is_better: bool) -> str:
    if not isinstance(before, (int, float)) or not isinstance(after, (int, float)) or before == after:
        return "change"
    improved = after < before if lower_is_better else after > before
    return "improvement" if improved else "regression"


def compare_raw(baseline: dict[str, Any], current: dict[str, Any]) -> tuple[list[dict[str, Any]], list[str], bool]:
    comparable, warnings = _contract_comparability("raw", baseline, current)
    if baseline.get("collection_status") == "failed" or current.get("collection_status") == "failed":
        comparable = False
        warnings.append("raw snapshot collection failed")
    changes: list[dict[str, Any]] = []
    before_pages = {_page_key(page): page for page in baseline.get("pages", []) if _page_key(page)}
    after_pages = {_page_key(page): page for page in current.get("pages", []) if _page_key(page)}
    for url in sorted(before_pages.keys() | after_pages.keys()):
        before = before_pages.get(url)
        after = after_pages.get(url)
        if before is None or after is None:
            changes.append(_change("page", "presence", bool(before), bool(after), key=url))
            continue
        old_error = before.get("error")
        new_error = after.get("error")
        if old_error or new_error:
            if old_error != new_error:
                classification = "change"
                if bool(old_error) != bool(new_error):
                    classification = "improvement" if not new_error else "regression"
                changes.append(_change("page", "collection_error", old_error, new_error, classification, key=url))
            continue
        fields = (
            "status",
            "final_url",
            "title",
            "meta_description",
            "canonical",
            "robots_meta",
            "h1",
            "word_count",
            "robots_meta_audit.indexable",
            "canonical_audit.issues",
            "schema_audit.schema_types_found",
            "image_stats.missing_alt",
            "image_stats.missing_dimensions",
            "link_summary.anchor_count",
            "link_summary.internal_count",
        )
        for field in fields:
            old_value = _nested(before, field)
            new_value = _nested(after, field)
            if field == "schema_audit.schema_types_found":
                old_value = sorted(old_value or [])
                new_value = sorted(new_value or [])
            if old_value == new_value:
                continue
            classification = "change"
            if field == "status":
                old_ok = isinstance(old_value, int) and 200 <= old_value < 400
                new_ok = isinstance(new_value, int) and 200 <= new_value < 400
                if old_ok != new_ok:
                    classification = "improvement" if new_ok else "regression"
            elif field in {"image_stats.missing_alt", "image_stats.missing_dimensions"}:
                classification = _numeric_classification(old_value, new_value, lower_is_better=True)
            elif field == "canonical_audit.issues":
                classification = _numeric_classification(len(old_value or []), len(new_value or []), lower_is_better=True)
            elif field == "robots_meta_audit.indexable" and isinstance(new_value, bool):
                classification = "improvement" if new_value else "regression"
            elif field in {"title", "meta_description", "canonical", "h1"} and bool(old_value) != bool(new_value):
                classification = "improvement" if new_value else "regression"
            changes.append(_change("page", field, old_value, new_value, classification, key=url))

    old_errors = len(baseline.get("errors", []))
    new_errors = len(current.get("errors", []))
    if old_errors != new_errors:
        changes.append(
            _change(
                "audit",
                "error_count",
                old_errors,
                new_errors,
                _numeric_classification(old_errors, new_errors, lower_is_better=True),
            )
        )
    if not comparable:
        for item in changes:
            item["classification"] = "change"
    return changes, warnings, comparable


def compare_technology(baseline: dict[str, Any], current: dict[str, Any]) -> tuple[list[dict[str, Any]], list[str], bool]:
    comparable, warnings = _contract_comparability("technology", baseline, current)
    for field in ("provider", "provider_version"):
        if baseline.get(field) != current.get(field):
            comparable = False
            warnings.append(f"technology {field} differs")
    if baseline.get("collection_status") == "failed" or current.get("collection_status") == "failed":
        comparable = False
        warnings.append("technology snapshot collection failed")
    changes: list[dict[str, Any]] = []
    before_pages = {_page_key(page): page for page in baseline.get("pages", []) if _page_key(page)}
    after_pages = {_page_key(page): page for page in current.get("pages", []) if _page_key(page)}
    for url in sorted(before_pages.keys() | after_pages.keys()):
        before_page = before_pages.get(url)
        after_page = after_pages.get(url)
        if before_page is None or after_page is None:
            changes.append(_change("page", "presence", bool(before_page), bool(after_page), key=url))
            continue
        old_error = before_page.get("error")
        new_error = after_page.get("error")
        if old_error or new_error:
            if old_error != new_error:
                classification = "change"
                if bool(old_error) != bool(new_error):
                    classification = "improvement" if not new_error else "regression"
                changes.append(_change("page", "collection_error", old_error, new_error, classification, key=url))
            continue
        before_apps = {
            str(item.get("name")): str(item.get("version", ""))
            for item in before_page.get("technologies", [])
            if item.get("name")
        }
        after_apps = {
            str(item.get("name")): str(item.get("version", ""))
            for item in after_page.get("technologies", [])
            if item.get("name")
        }
        for name in sorted(before_apps.keys() | after_apps.keys()):
            if name not in before_apps:
                changes.append(_change("technology", "presence", False, True, key=f"{url}::{name}"))
            elif name not in after_apps:
                changes.append(_change("technology", "presence", True, False, key=f"{url}::{name}"))
            elif before_apps[name] != after_apps[name]:
                changes.append(_change("technology", "version", before_apps[name], after_apps[name], key=f"{url}::{name}"))
    if not comparable:
        for item in changes:
            item["classification"] = "change"
    return changes, warnings, comparable


def _performance_comparability(baseline: dict[str, Any], current: dict[str, Any]) -> tuple[bool, list[str]]:
    comparable, warnings = _contract_comparability("performance", baseline, current)
    if baseline.get("collection_status") == "failed" or current.get("collection_status") == "failed":
        warnings.append("performance snapshot collection failed")
    for field, before, after in (
        ("requested_url", baseline.get("requested_url") or baseline.get("url"), current.get("requested_url") or current.get("url")),
        ("final_url", baseline.get("final_url"), current.get("final_url")),
        ("lighthouse_version", baseline.get("lighthouse_version"), current.get("lighthouse_version")),
        ("form_factor", baseline.get("form_factor"), current.get("form_factor")),
        ("runs_requested", baseline.get("runs_requested"), current.get("runs_requested")),
        (
            "browser_version",
            _nested(baseline, "environment.browser_version", ""),
            _nested(current, "environment.browser_version", ""),
        ),
    ):
        if not before or not after:
            warnings.append(f"performance {field} is missing")
        elif before != after:
            warnings.append(f"performance {field} differs: {before!r} -> {after!r}")
    if baseline.get("runs_succeeded", 0) < 3 or current.get("runs_succeeded", 0) < 3:
        warnings.append("performance comparison requires at least 3 successful runs in both snapshots")
    if _nested(baseline, "aggregate.high_variance", False) or _nested(current, "aggregate.high_variance", False):
        warnings.append("performance snapshot has high variance")
    old_benchmark = _nested(baseline, "environment.benchmark_index")
    new_benchmark = _nested(current, "environment.benchmark_index")
    if not isinstance(old_benchmark, (int, float)) or not old_benchmark or not isinstance(new_benchmark, (int, float)):
        warnings.append("performance benchmark_index is missing")
    else:
        if abs(new_benchmark - old_benchmark) / old_benchmark > 0.2:
            warnings.append("performance benchmark_index differs by more than 20%")
    return comparable and not warnings, warnings


def _performance_delta(
    field: str,
    before: Any,
    after: Any,
    comparable: bool,
    higher_is_better: bool,
) -> dict[str, Any] | None:
    if not isinstance(before, (int, float)) or not isinstance(after, (int, float)) or before == after:
        return None
    delta = after - before
    delta_percent = (delta / before * 100) if before else None
    threshold = 2.0 if field == "performance_score" else (0.01 if field == "cumulative-layout-shift" else max(50.0, abs(before) * 0.05))
    significant = abs(delta) >= threshold
    classification = "change"
    if comparable and significant:
        improved = delta > 0 if higher_is_better else delta < 0
        classification = "improvement" if improved else "regression"
    return _change(
        "performance",
        field,
        before,
        after,
        classification,
        significant=significant,
        delta=delta,
        delta_percent=delta_percent,
    )


def compare_performance(baseline: dict[str, Any], current: dict[str, Any]) -> tuple[list[dict[str, Any]], list[str], bool]:
    comparable, warnings = _performance_comparability(baseline, current)
    changes = []
    score_change = _performance_delta(
        "performance_score",
        _nested(baseline, "aggregate.performance_score.median"),
        _nested(current, "aggregate.performance_score.median"),
        comparable,
        higher_is_better=True,
    )
    if score_change:
        changes.append(score_change)
    for metric in PERFORMANCE_METRICS:
        metric_change = _performance_delta(
            metric,
            _nested(baseline, f"aggregate.metrics.{metric}.median"),
            _nested(current, f"aggregate.metrics.{metric}.median"),
            comparable,
            higher_is_better=False,
        )
        if metric_change:
            changes.append(metric_change)
    return changes, warnings, comparable


def _number(value: Any) -> float | None:
    try:
        return float(value) if value is not None else None
    except (TypeError, ValueError):
        return None


def compare_crux(baseline: dict[str, Any], current: dict[str, Any]) -> tuple[list[dict[str, Any]], list[str], bool]:
    comparable, warnings = _contract_comparability("crux", baseline, current)
    if baseline.get("collection_status") not in {"ok", "partial"} or current.get("collection_status") not in {"ok", "partial"}:
        comparable = False
        warnings.append("CrUX comparison requires successful field-data snapshots")
    before_queries = {item.get("form_factor"): item for item in baseline.get("queries", [])}
    after_queries = {item.get("form_factor"): item for item in current.get("queries", [])}
    if set(before_queries) != set(after_queries):
        comparable = False
        warnings.append("CrUX form factors differ")
    changes: list[dict[str, Any]] = []
    rating_rank = {"good": 0, "needs_improvement": 1, "poor": 2}
    for form_factor in sorted(before_queries.keys() & after_queries.keys()):
        before = before_queries[form_factor]
        after = after_queries[form_factor]
        if (before.get("effective_scope"), before.get("effective_value")) != (
            after.get("effective_scope"),
            after.get("effective_value"),
        ):
            comparable = False
            warnings.append(f"CrUX effective scope differs for {form_factor}")
            continue
        before_metrics = _nested(before, "current.summary.metrics", {})
        after_metrics = _nested(after, "current.summary.metrics", {})
        for metric in sorted(set(before_metrics) | set(after_metrics)):
            old_value = _number(before_metrics.get(metric, {}).get("p75"))
            new_value = _number(after_metrics.get(metric, {}).get("p75"))
            if old_value is not None and new_value is not None and old_value != new_value:
                minimum = 0.01 if metric == "cumulative_layout_shift" else 50.0
                significant = abs(new_value - old_value) >= max(minimum, abs(old_value) * 0.05)
                classification = "change"
                if comparable and significant:
                    classification = "improvement" if new_value < old_value else "regression"
                changes.append(
                    _change(
                        "crux",
                        f"{metric}.p75",
                        old_value,
                        new_value,
                        classification,
                        key=form_factor,
                        significant=significant,
                        delta=new_value - old_value,
                        delta_percent=((new_value - old_value) / old_value * 100) if old_value else None,
                    )
                )
            old_rating = before_metrics.get(metric, {}).get("rating")
            new_rating = after_metrics.get(metric, {}).get("rating")
            if old_rating != new_rating and old_rating in rating_rank and new_rating in rating_rank:
                classification = "change"
                if comparable:
                    classification = "regression" if rating_rank[new_rating] > rating_rank[old_rating] else "improvement"
                changes.append(
                    _change(
                        "crux",
                        f"{metric}.rating",
                        old_rating,
                        new_rating,
                        classification,
                        key=form_factor,
                    )
                )
    if not comparable:
        for item in changes:
            item["classification"] = "change"
    return changes, warnings, comparable


def _first_row(report: dict[str, Any], path: str) -> dict[str, Any]:
    rows = _nested(report, path, [])
    return rows[0] if isinstance(rows, list) and rows and isinstance(rows[0], dict) else {}


def compare_gsc(baseline: dict[str, Any], current: dict[str, Any]) -> tuple[list[dict[str, Any]], list[str], bool]:
    comparable, warnings = _contract_comparability("gsc", baseline, current)
    if baseline.get("collection_status") not in {"ok", "partial"} or current.get("collection_status") not in {"ok", "partial"}:
        comparable = False
        warnings.append("GSC comparison requires successful composite snapshots")
    if baseline.get("property") != current.get("property"):
        comparable = False
        warnings.append("GSC property differs")
    before_search = _nested(baseline, "components.search_analytics", {})
    after_search = _nested(current, "components.search_analytics", {})
    for field in ("search_type", "data_state", "window_days", "compare"):
        if before_search.get(field) != after_search.get(field):
            comparable = False
            warnings.append(f"GSC Search Analytics {field} differs")
    changes: list[dict[str, Any]] = []
    before_totals = _first_row(before_search, "windows.current.totals.rows")
    after_totals = _first_row(after_search, "windows.current.totals.rows")
    for field, lower_is_better in (("clicks", False), ("impressions", False), ("ctr", False), ("position", True)):
        old_value = _number(before_totals.get(field))
        new_value = _number(after_totals.get(field))
        if old_value is None or new_value is None or old_value == new_value:
            continue
        significant = abs(new_value - old_value) >= (0.01 if field == "ctr" else max(1.0, abs(old_value) * 0.05))
        classification = "change"
        if comparable and significant:
            classification = _numeric_classification(old_value, new_value, lower_is_better)
        changes.append(
            _change(
                "gsc_search_analytics",
                field,
                old_value,
                new_value,
                classification,
                significant=significant,
                delta=new_value - old_value,
                delta_percent=((new_value - old_value) / old_value * 100) if old_value else None,
            )
        )

    before_inspections = {
        item.get("url"): item.get("inspection_result", {})
        for item in _nested(baseline, "components.inspection.inspections", [])
        if item.get("url")
    }
    after_inspections = {
        item.get("url"): item.get("inspection_result", {})
        for item in _nested(current, "components.inspection.inspections", [])
        if item.get("url")
    }
    inspection_fields = (
        "verdict",
        "coverageState",
        "robotsTxtState",
        "indexingState",
        "pageFetchState",
        "googleCanonical",
        "userCanonical",
        "lastCrawlTime",
    )
    for url in sorted(before_inspections.keys() | after_inspections.keys()):
        before_status = before_inspections.get(url, {}).get("indexStatusResult", {})
        after_status = after_inspections.get(url, {}).get("indexStatusResult", {})
        if url not in before_inspections or url not in after_inspections:
            changes.append(_change("gsc_inspection", "presence", url in before_inspections, url in after_inspections, key=url))
            continue
        for field in inspection_fields:
            if before_status.get(field) != after_status.get(field):
                classification = "change"
                if comparable and field == "verdict":
                    classification = "improvement" if after_status.get(field) == "PASS" else "regression"
                changes.append(
                    _change(
                        "gsc_inspection",
                        field,
                        before_status.get(field),
                        after_status.get(field),
                        classification,
                        key=url,
                    )
                )

    before_sitemaps = {item.get("path"): item for item in _nested(baseline, "components.sitemaps.sitemaps", []) if item.get("path")}
    after_sitemaps = {item.get("path"): item for item in _nested(current, "components.sitemaps.sitemaps", []) if item.get("path")}
    for path in sorted(before_sitemaps.keys() | after_sitemaps.keys()):
        before_sitemap = before_sitemaps.get(path)
        after_sitemap = after_sitemaps.get(path)
        if before_sitemap is None or after_sitemap is None:
            changes.append(_change("gsc_sitemap", "presence", bool(before_sitemap), bool(after_sitemap), key=path))
            continue
        before_submitted = sum(item.get("submitted", 0) for item in before_sitemap.get("contents", []))
        after_submitted = sum(item.get("submitted", 0) for item in after_sitemap.get("contents", []))
        for field, old_value, new_value, lower_is_better in (
            ("errors", before_sitemap.get("errors", 0), after_sitemap.get("errors", 0), True),
            ("warnings", before_sitemap.get("warnings", 0), after_sitemap.get("warnings", 0), True),
            ("pending", before_sitemap.get("pending", False), after_sitemap.get("pending", False), True),
            ("submitted", before_submitted, after_submitted, False),
        ):
            if old_value == new_value:
                continue
            classification = "change"
            if comparable:
                classification = _numeric_classification(int(old_value), int(new_value), lower_is_better)
            changes.append(_change("gsc_sitemap", field, old_value, new_value, classification, key=path))
    if not comparable:
        for item in changes:
            item["classification"] = "change"
    return changes, warnings, comparable


def compare_tech_audit(
    project_dir: Path,
    baseline_path: Path,
    current_path: Path,
    baseline: dict[str, Any],
    current: dict[str, Any],
) -> tuple[list[dict[str, Any]], list[str], bool]:
    comparable, warnings = _contract_comparability("tech-audit", baseline, current)
    if baseline.get("collection_status") == "failed" or current.get("collection_status") == "failed":
        comparable = False
        warnings.append("technical audit snapshot collection failed")
    if baseline.get("config_fingerprint") != current.get("config_fingerprint"):
        comparable = False
        warnings.append("technical audit crawl configuration differs")
    if baseline.get("summary", {}).get("stopped_by_limit") or current.get("summary", {}).get("stopped_by_limit"):
        warnings.append("one technical audit snapshot stopped at max_urls")
    before = {item.get("fingerprint"): item for item in load_tech_issues(project_dir, baseline_path) if item.get("fingerprint")}
    after = {item.get("fingerprint"): item for item in load_tech_issues(project_dir, current_path) if item.get("fingerprint")}
    changes: list[dict[str, Any]] = []
    for fingerprint in sorted(before.keys() | after.keys()):
        old = before.get(fingerprint)
        new = after.get(fingerprint)
        if old is None:
            changes.append(_change("issue", "presence", False, True, "regression", key=f"{new.get('rule_id')}:{new.get('url')}"))
        elif new is None:
            changes.append(_change("issue", "presence", True, False, "improvement", key=f"{old.get('rule_id')}:{old.get('url')}"))
        elif old.get("priority", {}).get("score") != new.get("priority", {}).get("score"):
            changes.append(_change("issue", "priority_score", old.get("priority", {}).get("score"), new.get("priority", {}).get("score"), key=f"{new.get('rule_id')}:{new.get('url')}"))
    old_count = baseline.get("summary", {}).get("issues", len(before))
    new_count = current.get("summary", {}).get("issues", len(after))
    if old_count != new_count:
        changes.append(_change("audit", "issue_count", old_count, new_count, _numeric_classification(old_count, new_count, lower_is_better=True)))
    if not comparable:
        for item in changes:
            item["classification"] = "change"
    return changes, warnings, comparable


COMPARATORS: dict[str, Callable[[dict[str, Any], dict[str, Any]], tuple[list[dict[str, Any]], list[str], bool]]] = {
    "raw": compare_raw,
    "technology": compare_technology,
    "performance": compare_performance,
    "crux": compare_crux,
    "gsc": compare_gsc,
}


def _validate_snapshot(kind: str, path: Path, snapshot: dict[str, Any]) -> None:
    if kind in {"raw", "technology"} and not isinstance(snapshot.get("pages"), list):
        raise ValueError(f"{kind} snapshot is missing pages: {path}")
    if kind == "technology" and not snapshot.get("provider"):
        raise ValueError(f"technology snapshot is missing provider: {path}")
    if kind == "performance":
        if not snapshot.get("lighthouse_version") or not isinstance(snapshot.get("aggregate"), dict):
            raise ValueError(f"performance snapshot has an invalid contract: {path}")
    if kind == "crux" and not isinstance(snapshot.get("queries"), list):
        raise ValueError(f"CrUX snapshot has an invalid contract: {path}")
    if kind == "gsc" and not isinstance(snapshot.get("components"), dict):
        raise ValueError(f"GSC snapshot has an invalid contract: {path}")
    if kind == "tech-audit" and not isinstance(snapshot.get("artifacts"), dict):
        raise ValueError(f"technical audit snapshot has an invalid contract: {path}")


def compare_kind(
    project_dir: Path,
    kind: str,
    baseline_path: Path | None = None,
    current_path: Path | None = None,
) -> dict[str, Any]:
    baseline_path, current_path = snapshot_pair(project_dir, kind, baseline_path, current_path)
    base = {
        "kind": kind,
        "baseline_path": str(baseline_path) if baseline_path else "",
        "current_path": str(current_path) if current_path else "",
        "comparable": False,
        "warnings": [],
        "changes": [],
        "summary": {"changes": 0, "regressions": 0, "improvements": 0},
    }
    if current_path is None:
        return {**base, "status": "no_data", "warnings": [f"no {kind} snapshots found"]}
    if baseline_path is None:
        return {**base, "status": "no_baseline", "warnings": [f"only one {kind} snapshot found"]}
    try:
        baseline = _load(baseline_path)
        current = _load(current_path)
        _validate_snapshot(kind, baseline_path, baseline)
        _validate_snapshot(kind, current_path, current)
        if kind == "tech-audit":
            changes, warnings, comparable = compare_tech_audit(project_dir, baseline_path, current_path, baseline, current)
        else:
            changes, warnings, comparable = COMPARATORS[kind](baseline, current)
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        return {**base, "status": "failed", "warnings": [str(exc)]}
    return {
        **base,
        "status": "ok",
        "baseline_generated_at": baseline.get("generated_at", ""),
        "current_generated_at": current.get("generated_at", ""),
        "comparable": comparable,
        "warnings": warnings,
        "changes": changes,
        "summary": _summary(changes),
    }


def create_diff(
    project_dir: Path,
    kind: str = "all",
    baseline_path: Path | None = None,
    current_path: Path | None = None,
) -> tuple[dict[str, Any], Path]:
    if kind != "all" and kind not in AUDIT_KINDS:
        raise ValueError(f"unsupported audit kind: {kind}")
    if kind == "all" and (baseline_path or current_path):
        raise ValueError("--from and --to require a single --kind")
    project_state = state.load_state(project_dir)
    kinds = AUDIT_KINDS if kind == "all" else (kind,)
    comparisons = {
        item: compare_kind(project_dir, item, baseline_path if item == kind else None, current_path if item == kind else None)
        for item in kinds
    }
    statuses = [comparison["status"] for comparison in comparisons.values()]
    if all(status == "ok" for status in statuses):
        collection_status = "ok"
    elif any(status == "ok" for status in statuses):
        collection_status = "partial"
    elif any(status == "failed" for status in statuses):
        collection_status = "failed"
    else:
        collection_status = "no_baseline"
    aggregate = {
        "changes": sum(item["summary"]["changes"] for item in comparisons.values()),
        "regressions": sum(item["summary"]["regressions"] for item in comparisons.values()),
        "improvements": sum(item["summary"]["improvements"] for item in comparisons.values()),
    }
    generated_at = datetime.now(timezone.utc)
    output_dir = state.safe_project_path(project_dir, "audits/diffs")
    output_path = output_dir / f"audit-diff-{generated_at.strftime('%Y%m%dT%H%M%S%fZ')}.json"
    report = {
        "schema_version": SCHEMA_VERSION,
        "diff_version": DIFF_VERSION,
        "generated_at": generated_at.isoformat(),
        "collection_status": collection_status,
        "project": {
            "path": str(project_dir),
            "name": _nested(project_state, "project.name", ""),
            "url": _nested(project_state, "project.url", ""),
        },
        "requested_kind": kind,
        "comparisons": comparisons,
        "summary": aggregate,
        "errors": [
            {"kind": item, "error": "; ".join(comparison["warnings"])}
            for item, comparison in comparisons.items()
            if comparison["status"] == "failed"
        ],
        "warnings": [
            {"kind": item, "message": warning}
            for item, comparison in comparisons.items()
            for warning in comparison["warnings"]
            if comparison["status"] != "failed"
        ],
        "manifest": {"path": str(output_path), "latest_path": str(output_dir / "latest.json")},
    }
    _atomic_write_json(output_path, report)
    _atomic_write_json(output_dir / "latest.json", report)
    return report, output_path
