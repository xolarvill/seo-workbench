from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path
from zipfile import ZipFile


def test_package_extension_builds_rooted_zip_and_checksum(tmp_path: Path) -> None:
    dist = tmp_path / "extension"
    output = tmp_path / "release"
    manifest = {
        "manifest_version": 3,
        "name": "SEO Workbench",
        "version": "0.1.0",
        "side_panel": {"default_path": "sidepanel.html"},
        "background": {"service_worker": "service-worker.js"},
        "permissions": ["activeTab", "scripting", "sidePanel", "storage"],
        "host_permissions": ["http://127.0.0.1/*", "http://localhost/*"],
    }
    files = {
        "manifest.json": json.dumps(manifest),
        "sidepanel.html": "<main>SEO Workbench</main>",
        "service-worker.js": "void 0;",
        "sidepanel.js": "void 0;",
        "icons/icon-16.png": "16",
        "icons/icon-32.png": "32",
        "icons/icon-48.png": "48",
        "icons/icon-128.png": "128",
    }
    for relative, content in files.items():
        path = dist / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")

    subprocess.run(
        [sys.executable, "scripts/package_extension.py", "--dist", str(dist), "--output", str(output), "--expect-version", "0.1.0"],
        check=True,
    )

    archive = output / "seo-workbench-chrome-v0.1.0.zip"
    checksum = output / f"{archive.name}.sha256"
    with ZipFile(archive) as bundle:
        assert set(bundle.namelist()) == set(files)
    assert checksum.read_text(encoding="utf-8").endswith(f"  {archive.name}\n")

    mismatch = subprocess.run(
        [sys.executable, "scripts/package_extension.py", "--dist", str(dist), "--output", str(output), "--expect-version", "9.9.9"],
        text=True,
        capture_output=True,
    )
    assert mismatch.returncode == 2
    assert "does not match tag version" in mismatch.stderr
    assert "Traceback" not in mismatch.stderr

    (dist / ".env").write_text("SECRET=value", encoding="utf-8")
    unsafe = subprocess.run(
        [sys.executable, "scripts/package_extension.py", "--dist", str(dist), "--output", str(output)],
        text=True,
        capture_output=True,
    )
    assert unsafe.returncode == 2
    assert "unexpected files: .env" in unsafe.stderr
