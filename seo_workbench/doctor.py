from __future__ import annotations

import importlib.util
import json
import os
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


def _module_available(name: str) -> bool:
    try:
        return importlib.util.find_spec(name) is not None
    except (ImportError, ModuleNotFoundError):
        return False


def _latest(pattern_dir: Path, pattern: str) -> str:
    root = pattern_dir.resolve()
    matches = sorted(
        (
            item
            for item in pattern_dir.glob(pattern)
            if item.is_file() and not item.is_symlink() and item.resolve().is_relative_to(root)
        ),
        key=lambda item: item.stat().st_mtime,
        reverse=True,
    )
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


def _command_version(command: list[str]) -> tuple[bool, str]:
    try:
        completed = subprocess.run(command, capture_output=True, text=True, timeout=5, check=False)
    except (OSError, subprocess.TimeoutExpired) as exc:
        return False, str(exc)
    detail = completed.stdout.strip() or completed.stderr.strip()
    return completed.returncode == 0, detail or "version command returned no output"


def _ui_session_detail(session_path: Path) -> tuple[bool, str]:
    if not session_path.is_file() or session_path.is_symlink():
        return False, "UI is not running"
    try:
        session = state.read_json(session_path)
        pid = int(session.get("pid", 0))
        if pid <= 0:
            return False, "invalid UI session manifest"
        os.kill(pid, 0)
        return True, f"active at {session.get('base_url', 'local address')}"
    except ProcessLookupError:
        return False, "stale UI session manifest"
    except PermissionError:
        return True, "UI process exists"
    except (OSError, TypeError, ValueError, json.JSONDecodeError) as exc:
        return False, f"invalid UI session manifest: {exc}"


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

    ui_modules = all(_module_available(name) for name in ("fastapi", "uvicorn", "watchfiles"))
    checks.append(_check("ui_python_support", ui_modules, "installed" if ui_modules else "not installed; run ./setup.sh", "info"))
    ui_index = state.ROOT / "ui/dist/index.html"
    checks.append(_check("ui_frontend_assets", ui_index.is_file(), str(ui_index) if ui_index.is_file() else "not built; run ./setup.sh", "info"))
    ui_active, ui_detail = _ui_session_detail(state.ROOT / ".runtime/ui/session.json")
    checks.append(_check("ui_session", ui_active, ui_detail, "info"))

    raw_dir = state.safe_project_path(project_dir, "audits/raw")
    browser_dir = state.safe_project_path(project_dir, "audits/browser")
    rendered_dir = state.safe_project_path(project_dir, "audits/rendered")
    technology_dir = state.safe_project_path(project_dir, "audits/technology")
    performance_dir = state.safe_project_path(project_dir, "audits/performance")
    crux_dir = state.safe_project_path(project_dir, "audits/crux")
    gsc_dir = state.safe_project_path(project_dir, "audits/gsc")
    diff_dir = state.safe_project_path(project_dir, "audits/diffs")
    checks.append(_check("raw_evidence_dir", raw_dir.exists(), str(raw_dir), "warning"))
    checks.append(_check("browser_evidence_dir", browser_dir.exists(), str(browser_dir), "info"))
    checks.append(_check("crux_evidence_dir", crux_dir.exists(), str(crux_dir), "info"))
    checks.append(_check("gsc_evidence_dir", gsc_dir.exists(), str(gsc_dir), "info"))
    latest_raw = _latest(raw_dir, "evidence-*.json") if raw_dir.exists() else ""
    checks.append(_check("latest_raw_evidence", bool(latest_raw), latest_raw or "no evidence bundle found", "warning"))
    latest_browser = browser_dir / "latest.json"
    browser_status = ""
    if latest_browser.is_file() and not latest_browser.is_symlink():
        try:
            browser_status = state.read_json(latest_browser).get("collection_status", "")
        except (OSError, ValueError, json.JSONDecodeError):
            browser_status = "invalid"
    checks.append(
        _check(
            "latest_browser_evidence",
            browser_status in {"complete", "partial"},
            f"{latest_browser} ({browser_status})" if browser_status else "not collected; the Chrome extension is optional",
            "info",
        )
    )

    checks.append(_check("rendered_evidence_dir", rendered_dir.exists(), str(rendered_dir), "warning"))
    latest_rendered = _latest(rendered_dir, "rendered-*.json") if rendered_dir.exists() else ""
    checks.append(_check("latest_rendered_evidence", bool(latest_rendered), latest_rendered or "no rendered evidence found", "info"))
    playwright = importlib.util.find_spec("playwright") is not None
    checks.append(_check("playwright_optional", playwright, "installed" if playwright else "not installed; rendered evidence is optional", "info"))
    wappalyzer = importlib.util.find_spec("wappalyzer") is not None
    checks.append(
        _check(
            "wappalyzer_balanced",
            wappalyzer,
            "installed" if wappalyzer else "not installed; run ./setup.sh or use technology --scan-mode fast",
            "warning",
        )
    )
    from seo_workbench_tools import crux_probe, gsc_probe

    crux_key_env = bool(os.environ.get("SEO_WORKBENCH_CRUX_API_KEY", "").strip())
    crux_key_file = crux_probe.API_KEY_PATH.is_file()
    checks.append(
        _check(
            "crux_api_key",
            crux_key_env or crux_key_file,
            "configured via environment" if crux_key_env else (str(crux_probe.API_KEY_PATH) if crux_key_file else "not configured"),
            "info",
        )
    )
    latest_crux_path = state.safe_project_path(project_dir, "audits/crux/latest.json")
    latest_crux_status = ""
    if latest_crux_path.is_file() and not latest_crux_path.is_symlink():
        try:
            latest_crux_status = state.read_json(latest_crux_path).get("collection_status", "")
        except (OSError, ValueError, json.JSONDecodeError):
            latest_crux_status = "invalid"
    checks.append(
        _check(
            "latest_crux_evidence",
            latest_crux_status in {"ok", "partial", "no_data"},
            f"{latest_crux_path} ({latest_crux_status})" if latest_crux_status else "no CrUX evidence found",
            "info",
        )
    )

    google_auth = _module_available("google.auth")
    google_oauth = _module_available("google_auth_oauthlib")
    checks.append(
        _check(
            "google_auth_support",
            google_auth and google_oauth,
            "installed" if google_auth and google_oauth else "not installed; run ./setup.sh",
            "info",
        )
    )
    try:
        binding_file = gsc_probe.binding_path(project_dir)
        binding_ok = binding_file.is_file() and not binding_file.is_symlink()
        binding_detail = str(binding_file) if binding_ok else "not bound"
    except ValueError as exc:
        binding_file = project_dir / ".runtime/integrations/google.json"
        binding_ok = False
        binding_detail = str(exc)
    checks.append(_check("gsc_property_binding", binding_ok, binding_detail, "info"))
    if binding_ok and google_auth and google_oauth:
        try:
            binding = gsc_probe.load_binding(project_dir)
            credentials = gsc_probe.load_credentials(binding["profile"], refresh=False)
            refreshable = bool(
                getattr(credentials, "valid", False)
                or getattr(credentials, "refresh_token", None)
                or getattr(credentials, "service_account_email", None)
            )
            credential_detail = f"profile {binding['profile']} ({'refreshable' if refreshable else 'reauthentication required'})"
        except (OSError, RuntimeError, ValueError) as exc:
            refreshable = False
            credential_detail = str(exc)
        checks.append(_check("gsc_credentials", refreshable, credential_detail, "info"))
    latest_gsc_path = state.safe_project_path(project_dir, "audits/gsc/latest.json")
    latest_gsc_status = ""
    if latest_gsc_path.is_file() and not latest_gsc_path.is_symlink():
        try:
            latest_gsc_status = state.read_json(latest_gsc_path).get("collection_status", "")
        except (OSError, ValueError, json.JSONDecodeError):
            latest_gsc_status = "invalid"
    checks.append(
        _check(
            "latest_gsc_evidence",
            latest_gsc_status in {"ok", "partial"},
            f"{latest_gsc_path} ({latest_gsc_status})" if latest_gsc_status else "no GSC evidence found",
            "info",
        )
    )

    go_path = shutil.which("go")
    checks.append(_check("go_optional", bool(go_path), go_path or "not installed; technology detection is optional", "info"))
    if go_path:
        go_compatible, go_detail = _go_version(go_path)
        checks.append(_check("go_1_25", go_compatible, go_detail, "warning"))
    helper_dir = Path(__file__).resolve().parent.parent / "seo_workbench_tools/technology_detector"
    helper_ok = (helper_dir / "go.mod").is_file() and (helper_dir / "main.go").is_file()
    checks.append(_check("technology_detector_helper", helper_ok, str(helper_dir), "warning"))
    compiled_detector = Path(__file__).resolve().parent.parent / ".runtime/bin/technology-detector"
    checks.append(_check("technology_detector_binary", compiled_detector.is_file(), str(compiled_detector), "info"))
    checks.append(_check("technology_evidence_dir", technology_dir.exists(), str(technology_dir), "info"))
    latest_technology = _latest(technology_dir, "technology-*.json") if technology_dir.exists() else ""
    checks.append(_check("latest_technology_evidence", bool(latest_technology), latest_technology or "no technology evidence found", "info"))

    from seo_workbench_tools import performance_probe

    try:
        node_path = performance_probe.node_command()
        node_ok, node_detail = _command_version([node_path, "--version"])
    except RuntimeError as exc:
        node_ok, node_detail = False, str(exc)
    checks.append(_check("node_lighthouse_runtime", node_ok, node_detail, "warning"))
    lighthouse_package = Path(__file__).resolve().parent.parent / "node_modules/lighthouse/package.json"
    if lighthouse_package.is_file():
        lighthouse_version = state.read_json(lighthouse_package).get("version", "unknown")
        lighthouse_ok = lighthouse_version == "13.4.0"
    else:
        lighthouse_version = "not installed; run ./setup.sh"
        lighthouse_ok = False
    checks.append(_check("lighthouse_13_4_0", lighthouse_ok, lighthouse_version, "warning"))
    try:
        chrome_path = performance_probe.browser_executable()
        chrome_ok = True
    except RuntimeError as exc:
        chrome_path = str(exc)
        chrome_ok = False
    checks.append(_check("performance_browser", chrome_ok, chrome_path, "warning"))
    checks.append(_check("performance_evidence_dir", performance_dir.exists(), str(performance_dir), "info"))
    latest_performance = state.safe_project_path(project_dir, "audits/performance/latest.json")
    if latest_performance.is_file():
        try:
            latest_performance_report = state.read_json(latest_performance)
            latest_performance_status = latest_performance_report.get("collection_status", "missing status")
            latest_performance_ok = (
                latest_performance_report.get("schema_version") == "1.0"
                and latest_performance_status in {"ok", "partial"}
            )
            latest_performance_detail = f"{latest_performance} ({latest_performance_status})"
        except (OSError, ValueError) as exc:
            latest_performance_ok = False
            latest_performance_detail = f"{latest_performance} ({exc})"
    else:
        latest_performance_ok = False
        latest_performance_detail = "no performance evidence found"
    checks.append(
        _check(
            "latest_performance_evidence",
            latest_performance_ok,
            latest_performance_detail,
            "warning",
        )
    )
    checks.append(_check("audit_diff_dir", diff_dir.exists(), str(diff_dir), "info"))
    latest_diff = state.safe_project_path(project_dir, "audits/diffs/latest.json")
    if latest_diff.is_file():
        try:
            diff_report = state.read_json(latest_diff)
            diff_status = diff_report.get("collection_status", "missing status")
            diff_ok = diff_report.get("schema_version") == "1.0" and diff_status in {"ok", "partial", "no_baseline"}
            diff_detail = f"{latest_diff} ({diff_status})"
        except (OSError, ValueError) as exc:
            diff_ok = False
            diff_detail = f"{latest_diff} ({exc})"
    else:
        diff_ok = False
        diff_detail = "no audit diff found"
    checks.append(_check("latest_audit_diff", diff_ok, diff_detail, "info"))

    hard_fail = any((not check["ok"]) and check["severity"] == "error" for check in checks)
    return {
        "ok": not hard_fail and validation["ok"],
        "checks": checks,
        "validation": validation,
    }
