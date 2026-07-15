from __future__ import annotations

import argparse
import json
import os
import re
import signal
import shutil
import subprocess
import sys
import tempfile
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit
from seo_workbench_tools.browser_runtime import browser_executable
from seo_workbench_tools.network_boundary import guarded_proxy, inspect_target, sensitive_query_key, validate_url


ROOT = Path(__file__).resolve().parent.parent
DEFAULT_OUTPUT_DIR = Path("projects/default/audits/performance")
RUNNER_PATH = Path(__file__).with_name("lighthouse_runner.mjs")
LOCAL_NODE = ROOT / ".runtime/bin/node"
REQUIRED_REPORT_KEYS = {
    "schema_version",
    "runner_version",
    "lighthouse_version",
    "generated_at",
    "collection_status",
    "url",
    "form_factor",
    "runs_requested",
    "runs_succeeded",
    "aggregate",
    "environment",
    "errors",
    "warnings",
    "artifacts",
}


def slugify(value: str) -> str:
    parsed = urlsplit(value)
    if parsed.scheme in {"http", "https"} and parsed.hostname:
        value = f"{parsed.hostname}{parsed.path}"
    slug = re.sub(r"[^a-zA-Z0-9]+", "-", value).strip("-").lower()
    return slug[:80] or "page"


def write_private(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary_path: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w",
            encoding="utf-8",
            dir=path.parent,
            prefix=f".{path.name}.",
            suffix=".tmp",
            delete=False,
        ) as handle:
            temporary_path = Path(handle.name)
            handle.write(content)
        temporary_path.chmod(0o600)
        temporary_path.replace(path)
    finally:
        if temporary_path and temporary_path.exists():
            temporary_path.unlink()


def node_command() -> str:
    configured = os.environ.get("SEO_WORKBENCH_NODE", "").strip()
    candidates = [Path(configured).expanduser()] if configured else []
    candidates.append(LOCAL_NODE)
    if node := shutil.which("node"):
        candidates.append(Path(node))
    for candidate in candidates:
        if not candidate.is_file() or not os.access(candidate, os.X_OK):
            continue
        completed = subprocess.run(
            [str(candidate), "-p", "process.versions.node"],
            capture_output=True,
            text=True,
            timeout=5,
            check=False,
        )
        match = re.match(r"^(\d+)\.(\d+)", completed.stdout.strip())
        if completed.returncode == 0 and match and (int(match.group(1)), int(match.group(2))) >= (22, 19):
            return str(candidate)
    raise RuntimeError("Node >=22.19 is required for Lighthouse; run ./setup.sh")


def preflight_target(url: str, timeout: float, allow_private: bool) -> dict[str, Any]:
    del timeout
    return inspect_target(url, allow_private)


def parse_runner_output(stdout: str) -> dict[str, Any]:
    try:
        report = json.loads(stdout)
    except json.JSONDecodeError as exc:
        raise RuntimeError(f"Lighthouse runner returned invalid JSON: {exc}") from exc
    if not isinstance(report, dict):
        raise RuntimeError("Lighthouse runner returned a non-object JSON value")
    missing = sorted(REQUIRED_REPORT_KEYS - report.keys())
    if missing:
        raise RuntimeError(f"Lighthouse report missing keys: {', '.join(missing)}")
    if report.get("collection_status") not in {"ok", "partial", "failed"}:
        raise RuntimeError("Lighthouse runner returned an invalid collection_status")
    for field in ("errors", "warnings"):
        if not isinstance(report.get(field), list) or any(not isinstance(item, dict) for item in report[field]):
            raise RuntimeError(f"Lighthouse runner returned an invalid {field} field")
    return report


def terminate_recorded_chrome(pid_path: Path) -> None:
    try:
        pid = int(pid_path.read_text(encoding="utf-8").strip())
    except (OSError, ValueError):
        return
    kill = os.kill if os.name == "nt" else os.killpg
    try:
        kill(pid, signal.SIGTERM)
        deadline = time.monotonic() + 3
        while time.monotonic() < deadline:
            try:
                kill(pid, 0)
            except ProcessLookupError:
                return
            time.sleep(0.1)
        kill(pid, signal.SIGKILL)
    except (ProcessLookupError, PermissionError):
        pass
    finally:
        pid_path.unlink(missing_ok=True)


def run_runner(command: list[str], timeout: int, chrome_pid_path: Path) -> subprocess.CompletedProcess[str]:
    process = subprocess.Popen(command, cwd=ROOT, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    try:
        stdout, stderr = process.communicate(timeout=timeout)
    except subprocess.TimeoutExpired as exc:
        process.terminate()
        try:
            process.communicate(timeout=10)
        except subprocess.TimeoutExpired:
            process.kill()
            process.communicate()
        terminate_recorded_chrome(chrome_pid_path)
        raise RuntimeError(f"Lighthouse runner timed out after {exc.timeout}s") from exc
    return subprocess.CompletedProcess(command, process.returncode, stdout, stderr)


def collect(
    url: str,
    output_dir: Path,
    runs: int = 5,
    form_factor: str = "mobile",
    timeout: float = 45,
    allow_private: bool = False,
) -> dict[str, Any]:
    if runs != 1 and not 3 <= runs <= 9:
        raise ValueError("runs must be 1 for a smoke test or between 3 and 9 for analysis")
    if form_factor not in {"mobile", "desktop"}:
        raise ValueError("form_factor must be mobile or desktop")
    if timeout < 1 or timeout > 180:
        raise ValueError("timeout must be between 1 and 180 seconds")
    if not RUNNER_PATH.is_file():
        raise RuntimeError(f"Lighthouse runner is missing: {RUNNER_PATH}")

    url = validate_url(url)
    preflight = preflight_target(url, timeout, allow_private)
    node = node_command()
    chrome = browser_executable()
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
    run_dir = output_dir / f"performance-{slugify(url)}-{form_factor}-{timestamp}"
    run_dir.mkdir(parents=True, exist_ok=False, mode=0o700)
    process_timeout = max(120, int((timeout + 60) * runs))
    with guarded_proxy(allow_private) as proxy_server:
        command = [
            node,
            str(RUNNER_PATH),
            "--url",
            url,
            "--output-dir",
            str(run_dir),
            "--runs",
            str(runs),
            "--form-factor",
            form_factor,
            "--chrome-path",
            chrome,
            "--proxy-server",
            proxy_server,
            "--max-wait-for-load",
            str(int(timeout * 1000)),
        ]
        completed = run_runner(command, process_timeout, run_dir / ".chrome.pid")
    if not completed.stdout.strip():
        detail = completed.stderr.strip() or f"exit code {completed.returncode}"
        raise RuntimeError(f"Lighthouse runner failed: {detail}")

    report = parse_runner_output(completed.stdout)
    if completed.returncode not in {0, 1}:
        detail = completed.stderr.strip() or f"exit code {completed.returncode}"
        raise RuntimeError(f"Lighthouse runner failed: {detail}")
    for item in report["errors"]:
        item.setdefault("scope", "performance")
        item.setdefault("url", url)
    for item in report["warnings"]:
        item.setdefault("scope", "performance")
        item.setdefault("url", url)
    report["preflight"] = preflight
    report["manifest"] = {
        "path": str(run_dir / "summary.json"),
        "latest_path": str(output_dir / "latest.json"),
        "run_dir": str(run_dir),
        "schema_version": report.get("schema_version", "1.0"),
        "collection_status": report.get("collection_status", ""),
    }
    content = json.dumps(report, ensure_ascii=False, indent=2) + "\n"
    write_private(run_dir / "summary.json", content)
    write_private(output_dir / "latest.json", content)
    return report


def collect_from_state(
    state_path: Path,
    output_dir: Path,
    runs: int = 5,
    form_factor: str = "mobile",
    timeout: float = 45,
    allow_private: bool = False,
) -> Path:
    data = json.loads(state_path.read_text(encoding="utf-8"))
    url = data.get("project", {}).get("url", "")
    if not url:
        raise ValueError(f"missing project.url in {state_path}")
    report = collect(url, output_dir, runs, form_factor, timeout, allow_private)
    report["state_path"] = str(state_path)
    path = Path(report["manifest"]["path"])
    content = json.dumps(report, ensure_ascii=False, indent=2) + "\n"
    write_private(path, content)
    write_private(Path(report["manifest"]["latest_path"]), content)
    return path


def main(argv: list[str] | None = None) -> int:
    argp = argparse.ArgumentParser(description="Run repeated local Lighthouse performance analysis.")
    argp.add_argument("url", nargs="?", help="URL to inspect")
    argp.add_argument("--state", type=Path, help="Read the project URL from a state file")
    argp.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    argp.add_argument("--runs", type=int, default=5)
    argp.add_argument("--form-factor", choices=["mobile", "desktop"], default="mobile")
    argp.add_argument("--timeout", type=float, default=45)
    argp.add_argument("--allow-private", action="store_true")
    argp.add_argument("--print", action="store_true", dest="print_json")
    args = argp.parse_args(argv)
    try:
        if args.state:
            data = json.loads(args.state.read_text(encoding="utf-8"))
            url = data.get("project", {}).get("url", "")
        else:
            url = args.url or ""
        if not url:
            raise ValueError("a URL or --state with project.url is required")
        report = collect(url, args.output_dir, args.runs, args.form_factor, args.timeout, args.allow_private)
        if args.print_json:
            json.dump(report, sys.stdout, ensure_ascii=False, indent=2)
            sys.stdout.write("\n")
        else:
            print(report["manifest"]["path"])
        return 0 if report["collection_status"] != "failed" else 1
    except (OSError, RuntimeError, ValueError, json.JSONDecodeError) as exc:
        raise SystemExit(str(exc)) from exc


if __name__ == "__main__":
    raise SystemExit(main())
