from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
from contextlib import contextmanager
from datetime import datetime, timezone
from importlib.metadata import version
from pathlib import Path
from typing import Any

from seo_workbench_tools.files import atomic_write_text
from seo_workbench_tools.runtime_signals import detect_tags, detect_technologies
from seo_workbench_tools.technology_architecture import analyze_architecture


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
ENRICHED_DETECTOR_VERSION = "0.2.0"


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


def _normalize_wappalyzer_results(
    results: dict[str, Any],
    requested_urls: list[str],
    scan_mode: str,
) -> dict[str, Any]:
    pages = []
    for result_url, detected in results.items():
        technologies = []
        for name, details in sorted(detected.items(), key=lambda item: item[0].casefold()):
            technologies.append(
                {
                    "name": name,
                    "version": details.get("version", ""),
                    "confidence": details.get("confidence"),
                    "categories": details.get("categories", []),
                    "groups": details.get("groups", []),
                }
            )
        pages.append(
            {
                "url": result_url,
                "final_url": result_url,
                "fingerprint_inputs": ["response_headers", "set_cookie", "raw_html", "script_sources", "robots", "dns"],
                "technologies": technologies,
            }
        )
    missing_count = max(0, len(requested_urls) - len(pages))
    errors = (
        [{"scope": "technology", "error": f"balanced detector omitted {missing_count} requested URL(s)"}]
        if missing_count
        else []
    )
    return {
        "schema_version": "1.0",
        "detector_version": ENRICHED_DETECTOR_VERSION,
        "provider": "wappalyzer-next",
        "provider_version": version("wappalyzer"),
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "collection_status": "failed" if not pages else "partial" if errors else "ok",
        "scan_mode": scan_mode,
        "pages": pages,
        "errors": errors,
        "warnings": [],
    }


def _page_asset_urls(page: dict[str, Any]) -> list[str]:
    return list(
        dict.fromkeys(
            [
                str(item.get("url", ""))
                for item in page.get("resources", [])
                if item.get("url")
            ]
            + [
                str(item.get("href", ""))
                for item in page.get("links", [])
                if item.get("href")
            ]
        )
    )


def enrich_with_page_evidence(report: dict[str, Any], evidence_pages: list[dict[str, Any]]) -> dict[str, Any]:
    report_pages = report.setdefault("pages", [])
    by_url = {
        str(value): page
        for page in report_pages
        for value in (page.get("url"), page.get("final_url"))
        if value
    }
    aggregate_tags: dict[str, dict[str, Any]] = {}
    for evidence_page in evidence_pages:
        page = by_url.get(str(evidence_page.get("url", ""))) or by_url.get(str(evidence_page.get("final_url", "")))
        if page is None:
            page = {
                "url": evidence_page.get("url", ""),
                "final_url": evidence_page.get("final_url", ""),
                "fingerprint_inputs": [],
                "technologies": [],
            }
            report_pages.append(page)
        assets = _page_asset_urls(evidence_page)
        detections = detect_technologies(assets)
        existing = {str(item.get("name", "")).casefold() for item in page.get("technologies", [])}
        fallback = []
        for item in detections:
            if item["name"].casefold() in existing:
                continue
            page.setdefault("technologies", []).append(item)
            existing.add(item["name"].casefold())
            fallback.append(item)
        if assets:
            page["fingerprint_inputs"] = sorted(set(page.get("fingerprint_inputs", [])) | {"asset_urls"})
        page["fallback_detections"] = fallback
        tags = detect_tags(assets)
        page["tag_audit"] = {
            "status": "detected" if tags else "not_detected_in_static_assets",
            "detected": tags,
            "evidence_quality": "static asset URLs only; runtime, interaction, consent, and route-specific tags remain unverified",
        }
        for tag in tags:
            aggregate_tags.setdefault(tag["name"], tag)
    report["tag_audit"] = {
        "status": "detected" if aggregate_tags else "not_detected_in_static_assets",
        "detected": [aggregate_tags[name] for name in sorted(aggregate_tags)],
        "evidence_quality": "static asset URLs only; use rendered evidence for runtime requests",
    }
    return report


def enrich_with_runtime_evidence(report: dict[str, Any], evidence_bundle: dict[str, Any]) -> dict[str, Any]:
    rendered = evidence_bundle.get("rendered", {})
    if not rendered:
        return report
    report_pages = report.setdefault("pages", [])
    by_url = {
        str(value): page
        for page in report_pages
        for value in (page.get("url"), page.get("final_url"))
        if value
    }
    aggregate_tags = {
        item.get("name", ""): item
        for item in report.get("tag_audit", {}).get("detected", [])
        if item.get("name")
    }
    for runtime_page in rendered.get("pages", []):
        target = by_url.get(str(runtime_page.get("url", "")))
        if target is None:
            target = next(
                (
                    by_url.get(str(view.get("url", "")))
                    for view in runtime_page.get("viewports", {}).values()
                    if by_url.get(str(view.get("url", ""))) is not None
                ),
                None,
            )
        if target is None:
            continue
        existing = {str(item.get("name", "")).casefold() for item in target.get("technologies", [])}
        runtime_tags = {
            item.get("name", ""): item
            for item in target.get("tag_audit", {}).get("detected", [])
            if item.get("name")
        }
        profile_navigation = {}
        for profile, view in runtime_page.get("viewports", {}).items():
            if view.get("error"):
                continue
            if view.get("url"):
                profile_navigation[profile] = view["url"]
            for item in view.get("technology_signals", []):
                name = str(item.get("name", ""))
                if name and name.casefold() not in existing:
                    target.setdefault("technologies", []).append(item)
                    existing.add(name.casefold())
            for item in view.get("analytics_audit", {}).get("detected", []):
                if item.get("name"):
                    runtime_tags.setdefault(item["name"], item)
                    aggregate_tags.setdefault(item["name"], item)
        target["fingerprint_inputs"] = sorted(
            set(target.get("fingerprint_inputs", [])) | {"rendered_dom", "runtime_javascript", "network_requests"}
        )
        target["runtime_evidence"] = {
            "generated_at": rendered.get("generated_at", ""),
            "profile_navigation": profile_navigation,
        }
        target["tag_audit"] = {
            "status": "detected" if runtime_tags else "not_detected_during_observation",
            "detected": [runtime_tags[name] for name in sorted(runtime_tags)],
            "evidence_quality": "static assets plus rendered runtime observation; interactions and consent-state changes remain unverified",
        }
    report["tag_audit"] = {
        "status": "detected" if aggregate_tags else "not_detected_during_observation",
        "detected": [aggregate_tags[name] for name in sorted(aggregate_tags)],
        "evidence_quality": "static assets plus rendered runtime observation; interactions and consent-state changes remain unverified",
    }
    report["runtime_evidence"] = {
        "generated_at": rendered.get("generated_at", ""),
        "summary": rendered.get("runtime_summary", {}),
    }
    report["architecture_analysis"] = analyze_architecture(report)
    return report


def _collect_page_evidence(urls: list[str], timeout: float, allow_private: bool) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    from seo_workbench_tools import page_probe
    from seo_workbench_tools.network_boundary import guarded_proxy

    pages = []
    warnings = []
    with guarded_proxy(allow_private) as proxy_url, _proxy_environment(proxy_url):
        for url in urls:
            try:
                pages.append(page_probe.probe(url, timeout))
            except RuntimeError as exc:
                warnings.append({"scope": "technology_fallback", "url": url, "message": str(exc)})
    return pages, warnings


@contextmanager
def _proxy_environment(proxy_url: str):
    keys = ("HTTP_PROXY", "HTTPS_PROXY", "http_proxy", "https_proxy", "NO_PROXY", "no_proxy")
    original = {key: os.environ.get(key) for key in keys}
    os.environ.update(
        {
            "HTTP_PROXY": proxy_url,
            "HTTPS_PROXY": proxy_url,
            "http_proxy": proxy_url,
            "https_proxy": proxy_url,
            "NO_PROXY": "",
            "no_proxy": "",
        }
    )
    try:
        yield
    finally:
        for key, value in original.items():
            if value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = value


def _collect_balanced(urls: list[str], timeout: float, allow_private: bool) -> dict[str, Any]:
    try:
        from wappalyzer import Wappalyzer
    except ImportError as exc:
        raise RuntimeError("balanced technology detection is unavailable; run ./setup.sh or use --scan-mode fast") from exc
    from seo_workbench_tools.network_boundary import guarded_proxy, inspect_target

    for url in urls:
        inspect_target(url, allow_private)
    with guarded_proxy(allow_private) as proxy_url, _proxy_environment(proxy_url):
        with Wappalyzer(scan_type="balanced", workers=min(3, len(urls)), timeout=max(1, int(timeout))) as scanner:
            results = scanner.analyze_many(urls)
    return _normalize_wappalyzer_results(results, urls, "balanced")


def collect(
    urls: list[str],
    timeout: float = 20,
    allow_private: bool = False,
    scan_mode: str = "balanced",
) -> dict[str, Any]:
    if timeout <= 0:
        raise ValueError("timeout must be greater than zero")
    unique_urls = list(dict.fromkeys(url for url in urls if url))
    if not unique_urls:
        raise ValueError("at least one URL is required for technology detection")
    if scan_mode not in {"fast", "balanced"}:
        raise ValueError("scan_mode must be 'fast' or 'balanced'")
    omitted_urls = max(0, len(unique_urls) - MAX_TECHNOLOGY_URLS)
    unique_urls = unique_urls[:MAX_TECHNOLOGY_URLS]
    if scan_mode == "balanced":
        report = _collect_balanced(unique_urls, timeout, allow_private)
    else:
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
        report["scan_mode"] = "fast"
    if omitted_urls:
        report["warnings"].append(
            {
                "scope": "technology",
                "message": f"limited technology fingerprinting to {MAX_TECHNOLOGY_URLS} representative URLs; omitted {omitted_urls}",
            }
        )
    evidence_pages, fallback_warnings = _collect_page_evidence(unique_urls, timeout, allow_private)
    enrich_with_page_evidence(report, evidence_pages)
    report["warnings"].extend(fallback_warnings)
    report["architecture_analysis"] = analyze_architecture(report)
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


def collect_from_state(
    state_path: Path,
    timeout: float,
    output_dir: Path,
    allow_private: bool = False,
    scan_mode: str = "balanced",
) -> Path:
    data = json.loads(state_path.read_text(encoding="utf-8"))
    urls = urls_from_state(data)
    if not urls:
        raise ValueError(f"missing project.url in {state_path}")
    report = collect(urls, timeout, allow_private=allow_private, scan_mode=scan_mode)
    raw_evidence_path = output_dir.parent / "raw/latest.json"
    if raw_evidence_path.is_file():
        try:
            raw_evidence = json.loads(raw_evidence_path.read_text(encoding="utf-8"))
            if raw_evidence.get("seed_url") == urls[0]:
                enrich_with_runtime_evidence(report, raw_evidence)
        except (OSError, json.JSONDecodeError):
            pass
    performance_path = output_dir.parent / "performance/latest.json"
    performance = None
    if performance_path.is_file():
        try:
            performance = json.loads(performance_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            pass
    report["architecture_analysis"] = analyze_architecture(report, performance=performance)
    report["state_path"] = str(state_path)
    return write_report(report, output_dir)


def main(argv: list[str] | None = None) -> int:
    argp = argparse.ArgumentParser(description="Detect website technologies with the local Go/Wappalyzer helper.")
    argp.add_argument("url", nargs="?", help="URL to inspect")
    argp.add_argument("--page", action="append", default=[], help="Extra URL to inspect; repeatable")
    argp.add_argument("--state", type=Path, default=None, help="Read project and content URLs from a state file")
    argp.add_argument("--timeout", type=float, default=20)
    argp.add_argument("--scan-mode", choices=("fast", "balanced"), default="balanced")
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
        report = collect(urls, args.timeout, allow_private=args.allow_private, scan_mode=args.scan_mode)
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
