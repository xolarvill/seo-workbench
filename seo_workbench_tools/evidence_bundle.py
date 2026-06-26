from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from seo_workbench_tools import page_probe, robots_sitemap_probe


DEFAULT_OUTPUT_DIR = Path("projects/default/audits/raw")
RESOURCE_SAMPLE_PER_TYPE = 5


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
            if kind in by_type and resource.get("url") and resource["url"] not in by_type[kind]:
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


def collect(url: str, extra_pages: list[str], timeout: float, sample_limit: int) -> dict[str, Any]:
    pages = []
    for page_url in [url, *extra_pages]:
        try:
            pages.append(page_probe.probe(page_url, timeout))
        except RuntimeError as exc:
            pages.append({"url": page_url, "error": str(exc)})

    try:
        site = robots_sitemap_probe.probe(url, timeout, sample_limit)
    except (RuntimeError, ValueError) as exc:
        site = {"url": url, "error": str(exc)}

    bundle = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "seed_url": url,
        "pages": pages,
        "site": site,
    }
    bundle["hreflang_audit"] = hreflang_audit(pages, site)
    bundle["resource_cache_audit"] = resource_cache_audit(pages, timeout)
    return bundle


def write_bundle(bundle: dict[str, Any], output_dir: Path) -> Path:
    output_dir.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    path = output_dir / f"evidence-{slugify(bundle['seed_url'])}-{timestamp}.json"
    path.write_text(json.dumps(bundle, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return path


def _self_test() -> None:
    assert slugify("https://Example.com/a?b=1") == "https-example-com-a-b-1"
    path = write_bundle({"seed_url": "https://example.com", "pages": [], "site": {}}, Path("/tmp/seo-workbench-test-raw"))
    assert path.exists()
    path.unlink()
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
    argp.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    argp.add_argument("--print", action="store_true", dest="print_json", help="Print JSON instead of writing a file")
    argp.add_argument("--self-test", action="store_true")
    args = argp.parse_args(argv)

    if args.self_test:
        _self_test()
        return 0
    if not args.url:
        argp.error("url is required unless --self-test is used")

    bundle = collect(args.url, args.page, args.timeout, args.sample_limit)
    if args.print_json:
        json.dump(bundle, sys.stdout, ensure_ascii=False, indent=2)
        sys.stdout.write("\n")
        return 0

    path = write_bundle(bundle, args.output_dir)
    print(path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
