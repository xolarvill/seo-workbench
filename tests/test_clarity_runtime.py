import sys
import os
import signal
import subprocess
import time

from seo_workbench_tools.clarity_runtime import _execute


def test_timeout_cleans_up_owned_subprocess():
    result = _execute([sys.executable, "-c", "import time; time.sleep(30)"], {}, timeout=0.1)
    assert result == {"ok": False, "reason_code": "timeout"}
    result = _execute([sys.executable, "-c", "import time; time.sleep(30)"], {"token": "x" * 20000}, timeout=0.1)
    assert result == {"ok": False, "reason_code": "timeout"}


def test_invalid_and_oversized_output_are_failures():
    assert _execute([sys.executable, "-c", "print('not json')"], {})["reason_code"] == "invalid_response"
    result = _execute([sys.executable, "-c", "print('x' * (9 * 1024 * 1024))"], {})
    assert result["reason_code"] == "response_too_large"


def test_subprocess_does_not_inherit_secrets(monkeypatch):
    monkeypatch.setenv("OTHER_BRAND_TOKEN", "private")
    script = 'import json,os; print(json.dumps({"ok": "OTHER_BRAND_TOKEN" not in os.environ}))'
    assert _execute([sys.executable, "-c", script], {}) == {"ok": True}


def test_parent_sigterm_cleans_detached_runner(tmp_path):
    marker = tmp_path / "child.pid"
    child = f"import os,time; open({str(marker)!r}, 'w').write(str(os.getpid())); time.sleep(30)"
    parent = f"from seo_workbench_tools.clarity_runtime import _execute; import sys; _execute([sys.executable, '-c', {child!r}], {{}})"
    process = subprocess.Popen([sys.executable, "-c", parent])
    try:
        deadline = time.monotonic() + 5
        while not marker.exists() and time.monotonic() < deadline:
            time.sleep(0.02)
        assert marker.exists()
        child_pid = int(marker.read_text())
        process.send_signal(signal.SIGTERM)
        process.wait(timeout=4)
        try:
            os.kill(child_pid, 0)
        except ProcessLookupError:
            pass
        else:
            raise AssertionError("owned runner survived parent cancellation")
    finally:
        if process.poll() is None:
            process.kill()
            process.wait()
