from __future__ import annotations

import hashlib
import json
import re
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any

from seo_workbench import state
from seo_workbench.locks import project_lock
from seo_workbench_tools.files import atomic_write_text


LEDGER_PATH = "context/measurement-regimes.jsonl"
SOURCES = ("gsc", "ga4", "shopify", "consent", "all")
METRIC_PATTERN = re.compile(r"^[a-z][a-z0-9_.-]{0,63}$")


def record_regime(
    project_dir: Path,
    *,
    source: str,
    effective_at: str | date,
    description: str,
    metrics: list[str] | None = None,
    breaks_comparability: bool = True,
    now: datetime | None = None,
) -> dict[str, Any]:
    if source not in SOURCES:
        raise ValueError(f"measurement source must be one of: {', '.join(SOURCES)}")
    day = _day(effective_at)
    description = description.strip()
    if not description:
        raise ValueError("measurement regime description is required")
    selected_metrics = list(dict.fromkeys(metric.strip().lower() for metric in metrics or [] if metric.strip()))
    invalid = next((metric for metric in selected_metrics if not METRIC_PATTERN.fullmatch(metric)), None)
    if invalid:
        raise ValueError(f"invalid measurement metric: {invalid}")
    identity = json.dumps([source, day.isoformat(), description], ensure_ascii=False, separators=(",", ":"))
    record = {
        "schema_version": "measurement-regime-v1",
        "id": f"reg-{day.strftime('%Y%m%d')}-{hashlib.sha256(identity.encode()).hexdigest()[:10]}",
        "created_at": (now or datetime.now(timezone.utc)).astimezone(timezone.utc).isoformat(),
        "effective_at": day.isoformat(),
        "source": source,
        "metrics": selected_metrics,
        "breaks_comparability": breaks_comparability,
        "description": description,
    }
    path = state.safe_project_path(project_dir, LEDGER_PATH)
    with project_lock(project_dir):
        records = _read(path)
        if any(item.get("id") == record["id"] for item in records):
            raise ValueError(f"measurement regime already exists: {record['id']}")
        _write(path, [*records, record])
    return record


def list_regimes(project_dir: Path) -> dict[str, Any]:
    records = _read(state.safe_project_path(project_dir, LEDGER_PATH))
    records.sort(key=lambda item: (str(item.get("effective_at", "")), str(item.get("id", ""))), reverse=True)
    return {
        "schema_version": "measurement-regime-list-v1",
        "collection_status": "ok",
        "count": len(records),
        "regimes": records,
    }


def comparison_breaks(
    project_dir: Path,
    *,
    start_date: str | date,
    end_date: str | date,
    sources: set[str],
) -> list[dict[str, Any]]:
    start, end = _day(start_date), _day(end_date)
    if start > end:
        raise ValueError("measurement comparison start date cannot be after end date")
    return [
        record
        for record in _read(state.safe_project_path(project_dir, LEDGER_PATH))
        if bool(record.get("breaks_comparability"))
        and str(record.get("source")) in {*sources, "all"}
        and start < _day(str(record.get("effective_at", ""))) <= end
    ]


def _day(value: str | date) -> date:
    if isinstance(value, date):
        return value
    try:
        return date.fromisoformat(value)
    except ValueError as exc:
        raise ValueError("measurement regime date must be YYYY-MM-DD") from exc


def _read(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    if path.is_symlink():
        raise ValueError(f"measurement regime ledger cannot be a symlink: {path}")
    records = []
    for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        if not line.strip():
            continue
        try:
            record = json.loads(line)
        except json.JSONDecodeError as exc:
            raise ValueError(f"invalid measurement regime ledger line {line_number}: {exc.msg}") from exc
        if not isinstance(record, dict):
            raise ValueError(f"invalid measurement regime ledger line {line_number}: expected an object")
        records.append(record)
    return records


def _write(path: Path, records: list[dict[str, Any]]) -> None:
    atomic_write_text(path, "".join(json.dumps(record, ensure_ascii=False) + "\n" for record in records))
