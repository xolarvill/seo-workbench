from __future__ import annotations

import importlib.util
import re
import shutil
import subprocess
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


def _go_version(go_path: str) -> tuple[bool, str]:
    try:
        completed = subprocess.run([go_path, "version"], capture_output=True, text=True, timeout=5, check=False)
    except (OSError, subprocess.TimeoutExpired) as exc:
        return False, str(exc)
    detail = completed.stdout.strip() or completed.stderr.strip()
    match = re.search(r"\bgo(\d+)\.(\d+)", detail)
    compatible = completed.returncode == 0 and bool(match) and (int(match.group(1)), int(match.group(2))) >= (1, 25)
    return compatible, detail or "unable to read Go version"


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
    technology_dir = project_dir / "audits/technology"
    checks.append(_check("raw_evidence_dir", raw_dir.exists(), str(raw_dir), "warning"))
    latest_raw = _latest(raw_dir, "evidence-*.json") if raw_dir.exists() else ""
    checks.append(_check("latest_raw_evidence", bool(latest_raw), latest_raw or "no evidence bundle found", "warning"))

    checks.append(_check("rendered_evidence_dir", rendered_dir.exists(), str(rendered_dir), "warning"))
    latest_rendered = _latest(rendered_dir, "rendered-*.json") if rendered_dir.exists() else ""
    checks.append(_check("latest_rendered_evidence", bool(latest_rendered), latest_rendered or "no rendered evidence found", "info"))
    playwright = importlib.util.find_spec("playwright") is not None
    checks.append(_check("playwright_optional", playwright, "installed" if playwright else "not installed; rendered evidence is optional", "info"))

    go_path = shutil.which("go")
    checks.append(_check("go_optional", bool(go_path), go_path or "not installed; technology detection is optional", "info"))
    if go_path:
        go_compatible, go_detail = _go_version(go_path)
        checks.append(_check("go_1_25", go_compatible, go_detail, "warning"))
    helper_dir = Path(__file__).resolve().parent.parent / "seo_workbench_tools/technology_detector"
    helper_ok = (helper_dir / "go.mod").is_file() and (helper_dir / "main.go").is_file()
    checks.append(_check("technology_detector_helper", helper_ok, str(helper_dir), "warning"))
    checks.append(_check("technology_evidence_dir", technology_dir.exists(), str(technology_dir), "info"))
    latest_technology = _latest(technology_dir, "technology-*.json") if technology_dir.exists() else ""
    checks.append(_check("latest_technology_evidence", bool(latest_technology), latest_technology or "no technology evidence found", "info"))

    hard_fail = any((not check["ok"]) and check["severity"] == "error" for check in checks)
    return {
        "ok": not hard_fail and validation["ok"],
        "checks": checks,
        "validation": validation,
    }
