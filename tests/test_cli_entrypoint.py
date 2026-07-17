from __future__ import annotations

import json
import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent


def test_repository_cli_launcher_uses_installed_console_script() -> None:
    completed = subprocess.run(
        [str(ROOT / "seo"), "--help"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        timeout=10,
        check=False,
    )
    assert completed.returncode == 0, completed.stderr
    assert "usage: seo-workbench" in completed.stdout


def test_repository_cli_launcher_anchors_working_directory() -> None:
    completed = subprocess.run(
        [str(ROOT / "seo"), "projects", "--json"],
        cwd=ROOT / "docs",
        capture_output=True,
        text=True,
        timeout=10,
        check=False,
    )
    assert completed.returncode == 0, completed.stderr
    assert "projects" in json.loads(completed.stdout)


def test_console_script_is_installed_in_project_environment() -> None:
    command = ROOT / ".venv/bin/seo-workbench"
    assert command.is_file()
    completed = subprocess.run(
        [str(command), "--help"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        timeout=10,
        check=False,
    )
    assert completed.returncode == 0, completed.stderr
