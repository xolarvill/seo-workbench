from __future__ import annotations

import importlib.util
import shutil
import sys
from pathlib import Path
from typing import Any

from seo_workbench import state
from seo_workbench.validation import validate_project


def _check(name: str, ok: bool, detail: str = "", severity: str = "error") -> dict[str, Any]:
    return {"name": name, "ok": ok, "severity": severity, "detail": detail}


def _latest(pattern_dir: Path, pattern: str) -> str:
    matches = sorted(pattern_dir.glob(pattern), key=lambda item: item.stat().st_mtime, reverse=True)
    return str(matches[0]) if matches else ""


def run_doctor(project_dir: Path, workflow_path: Path) -> dict[str, Any]:
    checks: list[dict[str, Any]] = []
    version_ok = sys.version_info[:2] == (3, 11)
    checks.append(_check("python_3_11", version_ok, f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}", "warning"))
    uv_path = shutil.which("uv")
    checks.append(_check("uv_available", bool(uv_path), uv_path or "uv not found", "warning"))

    checks.append(_check("project_dir", project_dir.exists(), str(project_dir)))
    state_path = state.state_path(project_dir)
    checks.append(_check("state_file", state_path.exists(), str(state_path)))

    validation = validate_project(project_dir, workflow_path)
    checks.append(_check("workflow_contract", validation["ok"], f"{len(validation['issues'])} validation issue(s)"))

    raw_dir = project_dir / "audits/raw"
    rendered_dir = project_dir / "audits/rendered"
    checks.append(_check("raw_evidence_dir", raw_dir.exists(), str(raw_dir), "warning"))
    latest_raw = _latest(raw_dir, "evidence-*.json") if raw_dir.exists() else ""
    checks.append(_check("latest_raw_evidence", bool(latest_raw), latest_raw or "no evidence bundle found", "warning"))

    checks.append(_check("rendered_evidence_dir", rendered_dir.exists(), str(rendered_dir), "warning"))
    latest_rendered = _latest(rendered_dir, "rendered-*.json") if rendered_dir.exists() else ""
    checks.append(_check("latest_rendered_evidence", bool(latest_rendered), latest_rendered or "no rendered evidence found", "info"))
    playwright = importlib.util.find_spec("playwright") is not None
    checks.append(_check("playwright_optional", playwright, "installed" if playwright else "not installed; rendered evidence is optional", "info"))

    hard_fail = any((not check["ok"]) and check["severity"] == "error" for check in checks)
    return {
        "ok": not hard_fail and validation["ok"],
        "checks": checks,
        "validation": validation,
    }
