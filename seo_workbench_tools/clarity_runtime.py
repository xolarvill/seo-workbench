"""Bounded, isolated subprocess transport for the pinned Clarity MCP client."""
from __future__ import annotations

import json
import os
import selectors
import signal
import subprocess
import time
import threading
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
SERVER_VERSION = "2.0.1"
SDK_VERSION = "1.32.2"
MAX_OUTPUT = 8 * 1024 * 1024


def runtime_status() -> dict[str, Any]:
    node = ROOT / ".runtime/bin/node"
    installed = {}
    for name in ("@microsoft/clarity-mcp-server", "@modelcontextprotocol/sdk"):
        try:
            installed[name] = json.loads((ROOT / "node_modules" / name / "package.json").read_text())["version"]
        except (OSError, ValueError, KeyError):
            installed[name] = None
    version_ok = False
    if node.is_file():
        try:
            result = subprocess.run([str(node), "--version"], capture_output=True, timeout=5, text=True)
            version_ok = result.returncode == 0 and result.stdout.startswith("v24.")
        except (OSError, subprocess.TimeoutExpired):
            pass
    return {"runtime_ready": version_ok and installed == {
        "@microsoft/clarity-mcp-server": SERVER_VERSION, "@modelcontextprotocol/sdk": SDK_VERSION,
    }, "server_version": installed["@microsoft/clarity-mcp-server"], "sdk_version": installed["@modelcontextprotocol/sdk"]}


def _execute(command: list[str], request: dict[str, Any], *, timeout: float = 60) -> dict[str, Any]:
    environment = {"PATH": str(ROOT / ".runtime/bin"), "TZ": "UTC"}
    process = subprocess.Popen(command, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                               env=environment, cwd=ROOT, start_new_session=True)
    output = bytearray()
    stderr_size = 0
    previous_signal = None
    if threading.current_thread() is threading.main_thread():
        previous_signal = signal.getsignal(signal.SIGTERM)
        def terminate(_signum, _frame):
            raise SystemExit(143)
        signal.signal(signal.SIGTERM, terminate)
    try:
        assert process.stdin and process.stdout and process.stderr
        pending_input = memoryview(json.dumps(request).encode())
        if len(pending_input) > 32768:
            return {"ok": False, "reason_code": "invalid_request"}
        os.set_blocking(process.stdin.fileno(), False)
        with selectors.DefaultSelector() as selector:
            selector.register(process.stdin, selectors.EVENT_WRITE, "stdin")
            selector.register(process.stdout, selectors.EVENT_READ, "stdout")
            selector.register(process.stderr, selectors.EVENT_READ, "stderr")
            deadline = time.monotonic() + timeout
            while selector.get_map():
                remaining = deadline - time.monotonic()
                if remaining <= 0:
                    return {"ok": False, "reason_code": "timeout"}
                for key, _ in selector.select(min(remaining, 0.2)):
                    if key.data == "stdin":
                        try:
                            written = os.write(key.fd, pending_input[:4096])
                        except BrokenPipeError:
                            return {"ok": False, "reason_code": "mcp_error"}
                        pending_input = pending_input[written:]
                        if not pending_input:
                            selector.unregister(process.stdin)
                            process.stdin.close()
                        continue
                    chunk = os.read(key.fd, 65536)
                    if not chunk:
                        selector.unregister(key.fileobj)
                    elif key.data == "stdout":
                        output.extend(chunk)
                    else:
                        stderr_size += len(chunk)
                    if len(output) > MAX_OUTPUT or stderr_size > 65536:
                        return {"ok": False, "reason_code": "response_too_large"}
            process.wait(timeout=max(0.01, deadline - time.monotonic()))
        try:
            result = json.loads(output)
            if not isinstance(result, dict) or not isinstance(result.get("ok"), bool):
                raise ValueError()
            if process.returncode and result.get("ok"):
                return {"ok": False, "reason_code": "mcp_error"}
            return result
        except (ValueError, UnicodeError):
            return {"ok": False, "reason_code": "invalid_response"}
    except subprocess.TimeoutExpired:
        return {"ok": False, "reason_code": "timeout"}
    finally:
        if previous_signal is not None:
            signal.signal(signal.SIGTERM, previous_signal)
        # The group belongs to this call only; also catches orphaned grandchildren.
        try:
            os.killpg(process.pid, signal.SIGTERM)
        except ProcessLookupError:
            pass
        try:
            process.wait(timeout=1)
        except subprocess.TimeoutExpired:
            pass
        try:
            os.killpg(process.pid, signal.SIGKILL)
        except ProcessLookupError:
            pass
        process.wait()
        for stream in (process.stdin, process.stdout, process.stderr):
            if stream:
                stream.close()


def call(tool: str, arguments: dict[str, Any] | None = None, *, token: str = "", timezone: str = "UTC") -> dict[str, Any]:
    if not runtime_status()["runtime_ready"]:
        return {"ok": False, "reason_code": "needs_runtime"}
    return _execute([str(ROOT / ".runtime/bin/node"), str(ROOT / "seo_workbench_tools/clarity_mcp_runner.mjs")],
                    {"tool": tool, "arguments": arguments or {}, "token": token, "timezone": timezone})
