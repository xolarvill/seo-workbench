from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.parse import parse_qsl, urlsplit, urlunsplit
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from seo_workbench_tools import page_probe, robots_sitemap_probe
from seo_workbench_tools.files import atomic_write_text
from seo_workbench_tools.headless import build_headless_audit
from seo_workbench_tools.network_boundary import sensitive_query_key


DEFAULT_OUTPUT_DIR = Path("projects/default/audits/raw")
RESOURCE_SAMPLE_PER_TYPE = 5
SCHEMA_VERSION = "1.0"
COLLECTOR_VERSION = "0.6.0"
STATIC_SUFFIXES = {
    ".avif", ".css", ".gif", ".ico", ".jpeg", ".jpg", ".js", ".json", ".map", ".mp3", ".mp4",
    ".pdf", ".png", ".svg", ".ttf", ".webm", ".webp", ".woff", ".woff2", ".xml", ".zip",
}


def slugify(value: str) -> str:
    slug = re.sub(r"[^a-zA-Z0-9]+", "-", value).strip("-").lower()
    return slug[:80] or "site"


def hreflang_audit(pages: list[dict[str, Any]], site: dict[str, Any]) -> dict[str, Any]:
    html_codes = sorted(
        {
            link["hreflang"]
            for page in pages
            for link in page.get("links", [])
            if "alternate" in link.get("rel", "") and link.get("hreflang")
        }
    )
    sitemap_codes = sorted({code for sitemap in site.get("sitemaps", []) for code in sitemap.get("hreflang_codes", [])})
    issues = []

    def regional(codes: list[str]) -> bool:
        return any("-" in code for code in codes if code != "x-default")

    if html_codes and sitemap_codes and regional(html_codes) != regional(sitemap_codes):
        issues.append("格式不一致: HTML 和 sitemap 的 hreflang 区域限定格式不同")
    if sitemap_codes and "x-default" not in sitemap_codes:
        issues.append("sitemap 缺少 x-default")
    if sitemap_codes and not any(code == "en" or code.startswith("en-") for code in sitemap_codes):
        issues.append("sitemap 缺少显式 en alternate")
    if html_codes and sitemap_codes and len(html_codes) != len(sitemap_codes):
        issues.append(f"HTML 有 {len(html_codes)} 种语言, sitemap 有 {len(sitemap_codes)} 种")

    return {
        "html_hreflang_codes": html_codes,
        "sitemap_hreflang_codes": sitemap_codes,
        "issues": issues,
        "missing_x_default_in_sitemap": bool(sitemap_codes) and "x-default" not in sitemap_codes,
        "missing_en_explicit_in_sitemap": bool(sitemap_codes) and not any(code == "en" or code.startswith("en-") for code in sitemap_codes),
    }


def head_headers(url: str, timeout: float) -> dict[str, str]:
    try:
        with urlopen(Request(url, method="HEAD", headers={"User-Agent": page_probe.USER_AGENT}), timeout=timeout) as response:
            return page_probe.response_headers(response.headers)
    except HTTPError as exc:
        return page_probe.response_headers(exc.headers)
    except URLError:
        return {}


def resource_cache_audit(pages: list[dict[str, Any]], timeout: float) -> dict[str, Any]:
    html_cache_control = next((page.get("headers", {}).get("cache_control", "") for page in pages if page.get("headers")), "")
    by_type: dict[str, list[str]] = {"style": [], "script": [], "image": []}
    for page in pages:
        for resource in page.get("resources", []):
            kind = resource.get("type", "")
            if kind == "style":
                kind = "style"
            if (
                kind in by_type
                and resource.get("url", "").startswith(("http://", "https://"))
                and resource["url"] not in by_type[kind]
            ):
                by_type[kind].append(resource["url"])

    sampled = [url for urls in by_type.values() for url in urls[:RESOURCE_SAMPLE_PER_TYPE]]
    checked = []
    issues = []
    no_cache = 0
    immutable = 0
    for url in sampled:
        headers = head_headers(url, timeout)
        cache_control = headers.get("cache_control", "")
        checked.append({"url": url, "cache_control": cache_control})
        if not cache_control:
            no_cache += 1
            issues.append(f"{url} 缺少 Cache-Control")
        if "immutable" in cache_control.lower():
            immutable += 1
    if "no-store" in html_cache_control.lower():
        issues.append(f"HTML 页面响应 cache-control: {html_cache_control}")

    return {
        "checked_urls": len(checked),
        "no_cache_control": no_cache,
        "has_immutable": immutable,
        "html_cache_control": html_cache_control,
        "resources": checked,
        "issues": issues,
    }


def collection_status(bundle: dict[str, Any]) -> str:
    errors = bundle.get("errors", [])
    pages = bundle.get("pages", [])
    successful_pages = [
        page
        for page in pages
        if not page.get("error") and 200 <= int(page.get("status", 0) or 0) < 400
    ]
    failed_pages = [
        page
        for page in pages
        if page.get("error") or not 200 <= int(page.get("status", 0) or 0) < 400
    ]
    site_failed = bool(bundle.get("site", {}).get("error"))
    if not successful_pages and site_failed:
        return "failed"
    if errors or failed_pages or site_failed:
        return "partial"
    return "ok"


def performance_confidence(report: dict[str, Any]) -> float:
    if report.get("collection_status") not in {"ok", "partial"}:
        return 0.0
    if report.get("runs_succeeded", 0) < 3:
        return 0.6
    if report.get("aggregate", {}).get("high_variance"):
        return 0.7
    return 0.9


def _route_template(url: str) -> str:
    path = urlsplit(url).path
    segments = []
    for segment in path.split("/"):
        if re.fullmatch(r"\d+", segment):
            segments.append("{id}")
        elif re.fullmatch(r"[0-9a-fA-F-]{24,}", segment):
            segments.append("{token}")
        else:
            segments.append(segment)
    return "/".join(segments)


def discover_page_urls(
    seed_url: str,
    pages: list[dict[str, Any]],
    rendered: dict[str, Any] | None,
    limit: int,
) -> list[str]:
    if limit <= 0:
        return []
    seed = urlsplit(seed_url)
    existing = {
        urlunsplit((*urlsplit(str(value))[:4], ""))
        for page in pages
        for value in (page.get("url"), page.get("final_url"))
        if value
    }
    candidates = []
    for page in pages:
        candidates.extend(page.get("link_summary", {}).get("sample_internal", []))
    for page in (rendered or {}).get("pages", []):
        for view in page.get("viewports", {}).values():
            if not view.get("error"):
                candidates.extend(view.get("link_summary", {}).get("sample_internal", []))

    normalized = set()
    for raw in candidates:
        try:
            parsed = urlsplit(str(raw))
        except ValueError:
            continue
        if parsed.scheme not in {"http", "https"} or parsed.hostname != seed.hostname:
            continue
        if Path(parsed.path).suffix.casefold() in STATIC_SUFFIXES:
            continue
        if any(sensitive_query_key(key) for key, _ in parse_qsl(parsed.query, keep_blank_values=True)):
            continue
        candidate = urlunsplit((parsed.scheme, parsed.netloc, parsed.path or "/", parsed.query, ""))
        if candidate not in existing:
            normalized.add(candidate)

    selected = []
    templates = set()
    for candidate in sorted(normalized, key=lambda item: (bool(urlsplit(item).query), item.count("/"), item)):
        template = _route_template(candidate)
        if template in templates:
            continue
        templates.add(template)
        selected.append(candidate)
        if len(selected) >= limit:
            break
    return selected


def _duplicate_groups(pages: list[dict[str, Any]], field: str) -> list[dict[str, Any]]:
    grouped: dict[str, list[str]] = {}
    for page in pages:
        value = " ".join(str(page.get(field, "")).split())
        if value:
            grouped.setdefault(value, []).append(str(page.get("url", "")))
    return [
        {"value": value, "urls": urls, "count": len(urls)}
        for value, urls in sorted(grouped.items())
        if len(urls) > 1
    ]


def route_sample_audit(pages: list[dict[str, Any]], discovered_urls: list[str]) -> dict[str, Any]:
    successful = [page for page in pages if not page.get("error") and 200 <= int(page.get("status", 200) or 0) < 400]
    raw_shell_pages = sum(
        not page.get("content_audit", {}).get("has_body_text_in_raw_html", False)
        and not page.get("link_summary", {}).get("anchor_count", 0)
        for page in successful
    )
    duplicate_titles = _duplicate_groups(successful, "title")
    duplicate_descriptions = _duplicate_groups(successful, "meta_description")
    shell_ratio = raw_shell_pages / len(successful) if successful else 0.0
    possible_spa_shell = len(successful) >= 2 and shell_ratio >= 0.8 and bool(duplicate_titles or duplicate_descriptions)
    return {
        "sampled_pages": len(successful),
        "discovered_pages": len(discovered_urls),
        "discovered_urls": discovered_urls,
        "raw_shell_pages": raw_shell_pages,
        "raw_shell_ratio": round(shell_ratio, 3),
        "duplicate_title_groups": duplicate_titles,
        "duplicate_description_groups": duplicate_descriptions,
        "possible_spa_shell": possible_spa_shell,
    }


def collect(
    url: str,
    extra_pages: list[str],
    timeout: float,
    sample_limit: int,
    rendered: bool = False,
    rendered_output_dir: Path | None = None,
    project_type: str = "",
    technology: bool = False,
    technology_output_dir: Path | None = None,
    performance: bool = False,
    performance_output_dir: Path | None = None,
    performance_runs: int = 5,
    performance_form_factor: str = "mobile",
    crawl_limit: int = 0,
) -> dict[str, Any]:
    if crawl_limit < 0 or crawl_limit > 20:
        raise ValueError("crawl_limit must be between 0 and 20")
    errors = []
    warnings = []
    pages = []
    for page_url in [url, *extra_pages]:
        try:
            page = page_probe.probe(page_url, timeout)
            pages.append(page)
            if not 200 <= int(page.get("status", 0) or 0) < 400:
                warnings.append(
                    {
                        "scope": "page",
                        "url": page_url,
                        "message": f"raw page evidence used HTTP status {page.get('status', 'unknown')}",
                    }
                )
        except RuntimeError as exc:
            errors.append({"scope": "page", "url": page_url, "error": str(exc)})
            pages.append({"url": page_url, "error": str(exc)})

    try:
        site = robots_sitemap_probe.probe(url, timeout, sample_limit)
    except (RuntimeError, ValueError) as exc:
        errors.append({"scope": "site", "url": url, "error": str(exc)})
        site = {"url": url, "error": str(exc)}

    bundle = {
        "schema_version": SCHEMA_VERSION,
        "collector_version": COLLECTOR_VERSION,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "seed_url": url,
        "pages": pages,
        "site": site,
        "errors": errors,
        "warnings": warnings,
        "source_confidence": {
            "raw_html": 0.95,
            "robots_sitemap": 0.9 if not site.get("error") else 0.0,
            "resource_headers": 0.7,
            "rendered_dom": 0.0,
            "technology_fingerprints": 0.0,
            "performance_lab": 0.0,
        },
    }
    rendered_report = None
    if rendered:
        rendered_output_dir = rendered_output_dir or DEFAULT_OUTPUT_DIR.parent / "rendered"
        try:
            from seo_workbench_tools.rendered_probe import capture

            rendered_report = capture([url, *extra_pages], rendered_output_dir, timeout=max(timeout, 30), wait_ms=2500)
            bundle["rendered"] = rendered_report
            bundle["source_confidence"]["rendered_dom"] = 0.85
        except Exception as exc:
            errors.append({"scope": "rendered", "url": url, "error": str(exc)})
            warnings.append({"scope": "rendered", "message": "rendered evidence unavailable; install the rendered extra and Chromium"})

    discovered_urls = discover_page_urls(url, pages, rendered_report, crawl_limit)
    for page_url in discovered_urls:
        try:
            pages.append(page_probe.probe(page_url, timeout))
        except RuntimeError as exc:
            errors.append({"scope": "discovery", "url": page_url, "error": str(exc)})
            pages.append({"url": page_url, "error": str(exc)})
    bundle["discovery"] = {
        "enabled": crawl_limit > 0,
        "limit": crawl_limit,
        "discovered_count": len(discovered_urls),
        "urls": discovered_urls,
        "source": "raw and rendered internal-link samples",
    }
    bundle["route_sample_audit"] = route_sample_audit(pages, discovered_urls)
    if bundle["route_sample_audit"]["possible_spa_shell"]:
        warnings.append(
            {
                "scope": "route_sample",
                "message": "representative routes reuse thin raw HTML and duplicate metadata; possible shared SPA shell",
            }
        )
    bundle["hreflang_audit"] = hreflang_audit(pages, site)
    bundle["resource_cache_audit"] = resource_cache_audit(pages, timeout)
    if bundle["resource_cache_audit"].get("issues"):
        warnings.extend({"scope": "resource_cache", "message": issue} for issue in bundle["resource_cache_audit"]["issues"])

    if technology:
        technology_output_dir = technology_output_dir or DEFAULT_OUTPUT_DIR.parent / "technology"
        try:
            from seo_workbench_tools.technology_probe import collect as collect_technologies
            from seo_workbench_tools.technology_probe import enrich_with_runtime_evidence
            from seo_workbench_tools.technology_probe import write_report as write_technology_report

            technology_urls = [page.get("url", "") for page in pages if page.get("url")]
            technology_report = collect_technologies(technology_urls, timeout=max(timeout, 20))
            enrich_with_runtime_evidence(technology_report, bundle)
            write_technology_report(technology_report, technology_output_dir)
            bundle["technology_audit"] = technology_report
            if technology_report.get("collection_status") in {"ok", "partial"}:
                bundle["source_confidence"]["technology_fingerprints"] = 0.85
            errors.extend(technology_report.get("errors", []))
            warnings.extend(technology_report.get("warnings", []))
        except Exception as exc:
            errors.append({"scope": "technology", "url": url, "error": str(exc)})
            warnings.append({"scope": "technology", "message": "technology evidence unavailable; install Go and verify the detector module"})

    if performance:
        performance_output_dir = performance_output_dir or DEFAULT_OUTPUT_DIR.parent / "performance"
        try:
            from seo_workbench_tools.performance_probe import collect as collect_performance

            performance_report = collect_performance(
                url,
                performance_output_dir,
                runs=performance_runs,
                form_factor=performance_form_factor,
                timeout=max(timeout, 45),
            )
            bundle["performance_audit"] = performance_report
            bundle["source_confidence"]["performance_lab"] = performance_confidence(performance_report)
            errors.extend(performance_report.get("errors", []))
            warnings.extend(performance_report.get("warnings", []))
        except Exception as exc:
            errors.append({"scope": "performance", "url": url, "error": str(exc)})
            warnings.append({"scope": "performance", "message": "performance evidence unavailable; run ./setup.sh and verify Lighthouse"})

    bundle["headless_audit"] = build_headless_audit(bundle, rendered_report, project_type)
    bundle["collection_status"] = collection_status(bundle)
    return bundle


def write_bundle(bundle: dict[str, Any], output_dir: Path) -> Path:
    output_dir.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
    path = output_dir / f"evidence-{slugify(bundle['seed_url'])}-{timestamp}.json"
    bundle["manifest"] = {
        "path": str(path),
        "latest_path": str(output_dir / "latest.json"),
        "schema_version": bundle.get("schema_version", SCHEMA_VERSION),
        "collection_status": bundle.get("collection_status", ""),
    }
    content = json.dumps(bundle, ensure_ascii=False, indent=2) + "\n"
    atomic_write_text(path, content)
    atomic_write_text(output_dir / "latest.json", content)
    return path


def _self_test() -> None:
    assert slugify("https://Example.com/a?b=1") == "https-example-com-a-b-1"
    path = write_bundle({"seed_url": "https://example.com", "pages": [], "site": {}}, Path("/tmp/seo-workbench-test-raw"))
    assert path.exists()
    assert (path.parent / "latest.json").exists()
    path.unlink()
    (path.parent / "latest.json").unlink()
    assert hreflang_audit(
        [{"links": [{"rel": "alternate", "hreflang": "en-us"}]}],
        {"sitemaps": [{"hreflang_codes": ["en-us"]}]},
    )["issues"] == ["sitemap 缺少 x-default"]


def main(argv: list[str] | None = None) -> int:
    argp = argparse.ArgumentParser(description="Collect page, robots, and sitemap evidence into one JSON bundle.")
    argp.add_argument("url", nargs="?", help="Seed URL to inspect")
    argp.add_argument("--page", action="append", default=[], help="Extra page URL to include; repeatable")
    argp.add_argument("--timeout", type=float, default=15)
    argp.add_argument("--sample-limit", type=int, default=50)
    argp.add_argument("--crawl-limit", type=int, default=0, help="Discover and raw-probe up to this many representative internal routes")
    argp.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    argp.add_argument("--rendered", action="store_true")
    argp.add_argument("--performance", action="store_true")
    argp.add_argument("--performance-runs", type=int, default=5)
    argp.add_argument("--performance-form-factor", choices=["mobile", "desktop"], default="mobile")
    argp.add_argument("--print", action="store_true", dest="print_json", help="Print JSON instead of writing a file")
    argp.add_argument("--self-test", action="store_true")
    args = argp.parse_args(argv)

    if args.self_test:
        _self_test()
        return 0
    if not args.url:
        argp.error("url is required unless --self-test is used")

    bundle = collect(
        args.url,
        args.page,
        args.timeout,
        args.sample_limit,
        rendered=args.rendered,
        performance=args.performance,
        performance_runs=args.performance_runs,
        performance_form_factor=args.performance_form_factor,
        crawl_limit=args.crawl_limit,
    )
    if args.print_json:
        json.dump(bundle, sys.stdout, ensure_ascii=False, indent=2)
        sys.stdout.write("\n")
        return 0

    path = write_bundle(bundle, args.output_dir)
    print(path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
