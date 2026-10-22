from __future__ import annotations

import argparse
import os
import json
import re
from contextlib import contextmanager
from datetime import datetime, timezone
from importlib.metadata import version

from filelock import FileLock, Timeout
from seo_workbench_tools.files import atomic_write_text
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
LOCAL_BROWSERS = ROOT / ".runtime/playwright"


def prepare_browser_environment() -> None:
    os.environ.setdefault("PLAYWRIGHT_BROWSERS_PATH", str(LOCAL_BROWSERS))


def browser_executable(driver=None) -> str:
    prepare_browser_environment()
    configured = os.environ.get("CHROME_PATH", "").strip()
    if configured:
        path = Path(configured).expanduser()
        if path.is_file() and os.access(path, os.X_OK):
            return str(path)
        raise RuntimeError(f"CHROME_PATH does not point to an executable file: {path}")

    # Match the installed Playwright revision; never choose an arbitrary old
    # browser directory or silently launch the user's daily Chrome application.
    try:
        import playwright
        package = Path(playwright.__file__).parent / "driver/package"
        metadata = json.loads((package / "browsers.json").read_text())
        spec = next(item for item in metadata["browsers"] if item["name"] == "chromium-headless-shell")
        browser_root = os.environ.get("PLAYWRIGHT_BROWSERS_PATH", str(LOCAL_BROWSERS))
        root = package / ".local-browsers" if browser_root == "0" else Path(browser_root).expanduser()
        shell = root / f"chromium_headless_shell-{spec['revision']}"
        for name in ("chrome-headless-shell", "headless_shell", "chrome-headless-shell.exe", "headless_shell.exe"):
            for path in sorted(shell.glob(f"*/{name}")):
                if path.is_file() and os.access(path, os.X_OK):
                    return str(path)
        os.environ.setdefault("PLAYWRIGHT_BROWSERS_PATH", str(root))
        if driver is not None:
            path = Path(driver.chromium.executable_path)
        else:
            from playwright.sync_api import sync_playwright
            with sync_playwright() as temporary_driver:
                path = Path(temporary_driver.chromium.executable_path)
        if path.is_file() and os.access(path, os.X_OK):
            return str(path)
    except (ImportError, OSError, ValueError, KeyError, StopIteration):
        pass
    raise RuntimeError("Matching Playwright Chromium is missing; run ./setup.sh --local-browser, or explicitly set CHROME_PATH")


@contextmanager
def browser_lease():
    """One browser workload at a time, shared with Lighthouse processes."""
    from seo_workbench.state import safe_project_path
    directory = safe_project_path(ROOT, ".runtime/browser-control")
    directory.mkdir(parents=True, exist_ok=True, mode=0o700)
    try:
        with FileLock(str(safe_project_path(ROOT, ".runtime/browser-control/workload.lock")), timeout=0):
            yield
    except Timeout as exc:
        raise RuntimeError("browser workload already running; retry after it completes") from exc


def failure_details(exc: Exception, stage: str) -> dict:
    # Parse only process metadata. Launch exceptions can contain full command
    # lines and URLs, so their raw text must not enter diagnostic artifacts.
    message = str(exc)
    pid = re.search(r"(?:pid=|pid\s+)(\d+)", message)
    signal = re.search(r"signal[=:]\s*([A-Z0-9]+)", message)
    exit_code = re.search(r"exitCode[=:]\s*(-?\d+)", message)
    classification = "permission_denied" if any(x in message for x in ("EPERM", "Operation not permitted", "Permission denied")) else "browser_failure"
    return {"stage": stage, "classification": classification, "error_type": type(exc).__name__, "browser_pid": int(pid[1]) if pid else None, "exit_signal": signal[1] if signal else None, "exit_code": int(exit_code[1]) if exit_code else None}


@contextmanager
def managed_browser(driver, diagnostic_path: Path):
    record = {"schema_version": "browser-runtime-v1", "started_at": datetime.now(timezone.utc).isoformat(), "collector_pid": os.getpid(), "collector_parent_pid": os.getppid(), "playwright_version": version("playwright"), "status": "starting", "renderer_crashes": 0}
    browser = None
    closing = False
    stage = "resolve"
    primary_failure = False
    try:
        with browser_lease():
            record["executable"] = browser_executable(driver)
            stage = "launch"
            browser = driver.chromium.launch(headless=True, executable_path=record["executable"])
            try:
                record.update(status="running", browser_version=browser.version)
                def disconnected(*_):
                    if not closing:
                        record.update(status="unexpected_exit", classification="browser_disconnected")
                browser.on("disconnected", disconnected)
                try:
                    cdp = browser.new_browser_cdp_session()
                    processes = cdp.send("SystemInfo.getProcessInfo")
                    record["processes"] = [{"pid": p["id"], "type": p["type"]} for p in processes.get("processInfo", [])]
                    cdp.detach()
                except Exception:
                    record["process_metadata_status"] = "unavailable"
                atomic_write_text(diagnostic_path, json.dumps(record, indent=2) + "\n", mode=0o600)
                stage = "collection"
                yield browser, record
            finally:
                closing = True
                if browser.is_connected():
                    for context in browser.contexts:
                        try:
                            context.close()
                        except Exception:
                            record["cleanup_warning"] = "context_close_failed"
                    try:
                        browser.close()
                    except Exception:
                        record["cleanup_warning"] = "browser_close_failed"
                        record["status"] = "cleanup_failed"
            if record["status"] == "running":
                record["status"] = "ok" if not record["renderer_crashes"] else "renderer_crash"
    except BaseException as exc:
        primary_failure = True
        record.update(status="failed", **failure_details(exc, stage))
        raise
    finally:
        record["finished_at"] = datetime.now(timezone.utc).isoformat()
        try:
            atomic_write_text(diagnostic_path, json.dumps(record, indent=2) + "\n", mode=0o600)
        except OSError:
            if not primary_failure:
                raise


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Resolve the browser used by SEO Workbench probes.")
    parser.add_argument("--print", action="store_true", dest="print_path")
    args = parser.parse_args(argv)
    try:
        path = browser_executable()
    except RuntimeError as exc:
        parser.exit(1, f"{exc}\n")
    if args.print_path:
        print(path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
