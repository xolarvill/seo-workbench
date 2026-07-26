#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile, ZipInfo


REQUIRED_FILES = {
    "manifest.json",
    "sidepanel.html",
    "service-worker.js",
    "icons/icon-16.png",
    "icons/icon-32.png",
    "icons/icon-48.png",
    "icons/icon-128.png",
}
LOOPBACK_HOSTS = {"http://127.0.0.1/*", "http://localhost/*"}


def validate(dist: Path, expected_version: str | None) -> tuple[str, list[Path]]:
    if not dist.is_dir() or dist.is_symlink():
        raise ValueError(f"extension build directory is missing or unsafe: {dist}")
    manifest_path = dist / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    version = str(manifest.get("version", ""))
    if manifest.get("manifest_version") != 3 or manifest.get("name") != "SEO Workbench":
        raise ValueError("manifest must identify SEO Workbench as Manifest V3")
    if manifest.get("side_panel", {}).get("default_path") != "sidepanel.html":
        raise ValueError("manifest side panel entry is invalid")
    if manifest.get("background", {}).get("service_worker") != "service-worker.js":
        raise ValueError("manifest service worker entry is invalid")
    if not re.fullmatch(r"\d+(?:\.\d+){0,3}", version):
        raise ValueError(f"invalid Chrome extension version: {version}")
    if expected_version and version != expected_version:
        raise ValueError(f"manifest version {version} does not match tag version {expected_version}")
    missing = sorted(path for path in REQUIRED_FILES if not (dist / path).is_file())
    if missing:
        raise ValueError(f"extension build is incomplete: {', '.join(missing)}")
    if set(manifest.get("host_permissions", [])) != LOOPBACK_HOSTS:
        raise ValueError("extension host permissions must remain loopback-only")
    files = sorted(path for path in dist.rglob("*") if path.is_file())
    if any(path.is_symlink() for path in files):
        raise ValueError("extension package cannot contain symlinks")
    if any(path.suffix == ".map" for path in files):
        raise ValueError("extension package cannot contain source maps")
    return version, files


def package(dist: Path, output: Path, expected_version: str | None = None) -> tuple[Path, Path]:
    version, files = validate(dist, expected_version)
    output.mkdir(parents=True, exist_ok=True)
    archive = output / f"seo-workbench-chrome-v{version}.zip"
    with ZipFile(archive, "w", ZIP_DEFLATED, compresslevel=9) as bundle:
        for path in files:
            info = ZipInfo(path.relative_to(dist).as_posix(), date_time=(1980, 1, 1, 0, 0, 0))
            info.compress_type = ZIP_DEFLATED
            info.external_attr = 0o644 << 16
            bundle.writestr(info, path.read_bytes())
    checksum = output / f"{archive.name}.sha256"
    digest = hashlib.sha256(archive.read_bytes()).hexdigest()
    checksum.write_text(f"{digest}  {archive.name}\n", encoding="utf-8")
    return archive, checksum


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate and package the SEO Workbench Chrome extension.")
    parser.add_argument("--dist", type=Path, default=Path("extension/dist"))
    parser.add_argument("--output", type=Path, default=Path("dist/releases"))
    parser.add_argument("--expect-version")
    args = parser.parse_args()
    try:
        archive, checksum = package(args.dist, args.output, args.expect_version)
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        print(f"extension package failed: {exc}", file=sys.stderr)
        return 2
    print(archive)
    print(checksum)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
