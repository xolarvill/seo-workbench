import sys

from seo_workbench_tools.clarity_runtime import _execute


def test_timeout_cleans_up_owned_subprocess():
    result = _execute([sys.executable, "-c", "import time; time.sleep(30)"], {}, timeout=0.1)
    assert result == {"ok": False, "reason_code": "timeout"}


def test_invalid_and_oversized_output_are_failures():
    assert _execute([sys.executable, "-c", "print('not json')"], {})["reason_code"] == "invalid_response"
    result = _execute([sys.executable, "-c", "print('x' * (9 * 1024 * 1024))"], {})
    assert result["reason_code"] == "response_too_large"


def test_subprocess_does_not_inherit_secrets(monkeypatch):
    monkeypatch.setenv("OTHER_BRAND_TOKEN", "private")
    script = 'import json,os; print(json.dumps({"ok": "OTHER_BRAND_TOKEN" not in os.environ}))'
    assert _execute([sys.executable, "-c", script], {}) == {"ok": True}
