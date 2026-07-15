from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from seo_workbench_tools.files import atomic_write_text


DEFAULT_OUTPUT_DIR = Path("projects/default/audits/technology")
HELPER_DIR = Path(__file__).with_name("technology_detector")
LOCAL_DETECTOR = Path(__file__).resolve().parent.parent / ".runtime/bin/technology-detector"
REQUIRED_REPORT_KEYS = {
    "schema_version",
    "detector_version",
    "provider",
    "provider_version",
    "generated_at",
    "collection_status",
    "pages",
    "errors",
    "warnings",
}
MAX_TECHNOLOGY_URLS = 10


def slugify(value: str) -> str:
    slug = re.sub(r"[^a-zA-Z0-9]+", "-", value).strip("-").lower()
    return slug[:80] or "site"


def urls_from_state(data: dict[str, Any]) -> list[str]:
    seed = data.get("project", {}).get("url", "")
    urls = [seed] if seed else []
    for item in data.get("contentQueue", []):
        url = item.get("url") or item.get("publishedUrl") or item.get("published_url")
        if url and item.get("status") in {"published", "draft"} and url not in urls:
            urls.append(url)
    return urls


def detector_command() -> tuple[list[str], Path | None]:
    configured = os.environ.get("SEO_WORKBENCH_TECH_DETECTOR", "").strip()
    if configured:
        path = Path(configured).expanduser()
        if not path.is_file():
            raise RuntimeError(f"SEO_WORKBENCH_TECH_DETECTOR does not point to a file: {path}")
        if not os.access(path, os.X_OK):
            raise RuntimeError(f"SEO_WORKBENCH_TECH_DETECTOR is not executable: {path}")
        return [str(path)], None

    if LOCAL_DETECTOR.is_file() and os.access(LOCAL_DETECTOR, os.X_OK):
        return [str(LOCAL_DETECTOR)], None

    go = shutil.which("go")
    if not go:
        raise RuntimeError("Go is required for technology detection; install Go or set SEO_WORKBENCH_TECH_DETECTOR")
    if not (HELPER_DIR / "go.mod").is_file():
        raise RuntimeError(f"technology detector helper is missing: {HELPER_DIR}")
    return [go, "run", "."], HELPER_DIR


def parse_detector_output(stdout: str) -> dict[str, Any]:
    try:
        report = json.loads(stdout)
    except json.JSONDecodeError as exc:
        raise RuntimeError(f"technology detector returned invalid JSON: {exc}") from exc
    if not isinstance(report, dict):
        raise RuntimeError("technology detector returned a non-object JSON value")
    missing = sorted(REQUIRED_REPORT_KEYS - report.keys())
    if missing:
        raise RuntimeError(f"technology detector report missing keys: {', '.join(missing)}")
    if report.get("collection_status") not in {"ok", "partial", "failed"}:
        raise RuntimeError("technology detector returned an invalid collection_status")
    for field in ("pages", "errors", "warnings"):
        if not isinstance(report.get(field), list):
            raise RuntimeError(f"technology detector returned a non-list {field} field")
        if any(not isinstance(item, dict) for item in report[field]):
            raise RuntimeError(f"technology detector returned a non-object item in {field}")
    return report


def collect(urls: list[str], timeout: float = 20, allow_private: bool = False) -> dict[str, Any]:
    if timeout <= 0:
        raise ValueError("timeout must be greater than zero")
    unique_urls = list(dict.fromkeys(url for url in urls if url))
    if not unique_urls:
        raise ValueError("at least one URL is required for technology detection")
    omitted_urls = max(0, len(unique_urls) - MAX_TECHNOLOGY_URLS)
    unique_urls = unique_urls[:MAX_TECHNOLOGY_URLS]
    command, cwd = detector_command()
    for url in unique_urls:
        command.extend(["-url", url])
    command.extend(["-timeout", f"{timeout}s"])
    if allow_private:
        command.append("-allow-private")
    try:
        completed = subprocess.run(
            command,
            cwd=cwd,
            capture_output=True,
            text=True,
            timeout=max(60, int(timeout * len(unique_urls)) + 60),
            check=False,
        )
    except subprocess.TimeoutExpired as exc:
        raise RuntimeError(f"technology detector timed out after {exc.timeout}s") from exc
    if completed.returncode != 0:
        detail = completed.stderr.strip() or completed.stdout.strip() or f"exit code {completed.returncode}"
        raise RuntimeError(f"technology detector failed: {detail}")
    report = parse_detector_output(completed.stdout)
    if omitted_urls:
        report["warnings"].append(
            {
                "scope": "technology",
                "message": f"limited technology fingerprinting to {MAX_TECHNOLOGY_URLS} representative URLs; omitted {omitted_urls}",
            }
        )
    return report


def write_report(report: dict[str, Any], output_dir: Path) -> Path:
    output_dir.mkdir(parents=True, exist_ok=True)
    seed_url = next((page.get("url", "") for page in report.get("pages", []) if page.get("url")), "site")
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
    path = output_dir / f"technology-{slugify(seed_url)}-{timestamp}.json"
    report["manifest"] = {
        "path": str(path),
        "latest_path": str(output_dir / "latest.json"),
        "schema_version": report.get("schema_version", "1.0"),
        "collection_status": report.get("collection_status", ""),
    }
    content = json.dumps(report, ensure_ascii=False, indent=2) + "\n"
    atomic_write_text(path, content)
    atomic_write_text(output_dir / "latest.json", content)
    return path


def collect_from_state(state_path: Path, timeout: float, output_dir: Path, allow_private: bool = False) -> Path:
    data = json.loads(state_path.read_text(encoding="utf-8"))
    urls = urls_from_state(data)
    if not urls:
        raise ValueError(f"missing project.url in {state_path}")
    report = collect(urls, timeout, allow_private=allow_private)
    report["state_path"] = str(state_path)
    return write_report(report, output_dir)


def main(argv: list[str] | None = None) -> int:
    argp = argparse.ArgumentParser(description="Detect website technologies with the local Go/Wappalyzer helper.")
    argp.add_argument("url", nargs="?", help="URL to inspect")
    argp.add_argument("--page", action="append", default=[], help="Extra URL to inspect; repeatable")
    argp.add_argument("--state", type=Path, default=None, help="Read project and content URLs from a state file")
    argp.add_argument("--timeout", type=float, default=20)
    argp.add_argument("--allow-private", action="store_true", help="Allow a trusted private or loopback target")
    argp.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    argp.add_argument("--print", action="store_true", dest="print_json")
    args = argp.parse_args(argv)

    try:
        if args.state:
            data = json.loads(args.state.read_text(encoding="utf-8"))
            urls = urls_from_state(data)
        else:
            urls = [args.url, *args.page] if args.url else []
        report = collect(urls, args.timeout, allow_private=args.allow_private)
        if args.print_json:
            json.dump(report, sys.stdout, ensure_ascii=False, indent=2)
            sys.stdout.write("\n")
            return 0
        print(write_report(report, args.output_dir))
        return 0
    except (OSError, RuntimeError, ValueError, json.JSONDecodeError) as exc:
        raise SystemExit(str(exc)) from exc


if __name__ == "__main__":
    raise SystemExit(main())
