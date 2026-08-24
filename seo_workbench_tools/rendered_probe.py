from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from seo_workbench_tools.browser_runtime import browser_executable
from seo_workbench_tools.files import atomic_output_path, atomic_write_text
from seo_workbench_tools.runtime_signals import detect_tags, detect_technologies


DEFAULT_OUTPUT_DIR = Path("projects/default/audits/rendered")
VIEWPORTS = {
    "desktop_1920x1080": {"width": 1920, "height": 1080},
    "tablet_768x1024": {"width": 768, "height": 1024},
    "mobile_375x812": {"width": 375, "height": 812},
}
MOBILE_USER_AGENT = "Mozilla/5.0 (Linux; Android 11; moto g power (2022)) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/149.0.0.0 Mobile Safari/537.36"


def context_options(viewport_name: str, viewport: dict[str, int]) -> dict[str, Any]:
    options: dict[str, Any] = {"viewport": viewport}
    if viewport_name.startswith("mobile_"):
        options.update({"user_agent": MOBILE_USER_AGENT, "is_mobile": True, "device_scale_factor": 1.75})
    return options


def summarize_runtime_report(report: dict[str, Any]) -> dict[str, Any]:
    technologies = set()
    analytics_tags = set()
    navigation_variants = []
    for page in report.get("pages", []):
        profiles = {}
        for name, view in page.get("viewports", {}).items():
            if view.get("error"):
                continue
            final_url = view.get("url", "")
            if final_url:
                profiles[name] = final_url
            technologies.update(item.get("name", "") for item in view.get("technology_signals", []) if item.get("name"))
            analytics_tags.update(item.get("name", "") for item in view.get("analytics_audit", {}).get("detected", []) if item.get("name"))
        final_urls = sorted(set(profiles.values()))
        navigation_variants.append(
            {
                "requested_url": page.get("url", ""),
                "profiles": profiles,
                "final_urls": final_urls,
                "varies": len(final_urls) > 1,
            }
        )
    return {
        "technologies": sorted(technologies),
        "analytics_tags": sorted(analytics_tags),
        "navigation_variants": navigation_variants,
    }


def slugify(value: str) -> str:
    slug = re.sub(r"[^a-zA-Z0-9]+", "-", value).strip("-").lower()
    return slug[:80] or "page"


def analyze_page(page: Any) -> dict[str, Any]:
    return page.evaluate(
        """() => {
            const vp = {width: window.innerWidth, height: window.innerHeight};
            const foldY = vp.height * 0.75;
            const visibleBox = (el) => {
                if (!el) return null;
                const r = el.getBoundingClientRect();
                if (r.width <= 0 || r.height <= 0) return null;
                return {x: Math.round(r.x), y: Math.round(r.y), width: Math.round(r.width), height: Math.round(r.height)};
            };
            const first = (selectors) => {
                for (const sel of selectors) {
                    const el = document.querySelector(sel);
                    const box = visibleBox(el);
                    if (box) return {selector: sel, tag: el.tagName, text: (el.innerText || el.alt || '').trim().slice(0, 120), box, above_fold: box.y < foldY};
                }
                return null;
            };
            const imgs = [...document.querySelectorAll('img')].map((img) => {
                const box = visibleBox(img);
                return {
                    src: (img.currentSrc || img.src || '').slice(0, 180),
                    alt: (img.alt || '').slice(0, 120),
                    loading: img.loading || '',
                    fetchpriority: img.fetchPriority || '',
                    srcset: !!img.getAttribute('srcset'),
                    width_attr: img.getAttribute('width') || '',
                    height_attr: img.getAttribute('height') || '',
                    box,
                    above_fold: !!box && box.y < vp.height,
                };
            });
            const links = [...document.querySelectorAll('a, button, [role="button"]')].slice(0, 80).map((el) => {
                const box = visibleBox(el);
                return {
                    tag: el.tagName,
                    text: (el.innerText || '').trim().slice(0, 80),
                    box,
                    too_small: !!box && (box.width < 48 || box.height < 48),
                    above_fold: !!box && box.y < vp.height,
                };
            }).filter((item) => item.box);
            const safeUrl = (raw) => {
                try {
                    const url = new URL(raw, location.href);
                    return `${url.origin}${url.pathname}`.slice(0, 240);
                } catch {
                    return String(raw || '').split(/[?#]/, 1)[0].slice(0, 240);
                }
            };
            const resources = performance.getEntriesByType('resource').map((entry) => ({
                name: safeUrl(entry.name),
                initiatorType: entry.initiatorType,
                transferSize: entry.transferSize || 0,
                duration: Math.round(entry.duration || 0),
            }));
            const nav = performance.getEntriesByType('navigation')[0];
            const meta = (name) => {
                const el = document.querySelector(`meta[name="${name}"], meta[property="${name}"]`);
                return el ? el.getAttribute('content') || '' : '';
            };
            const schemaBlocks = [...document.querySelectorAll('script[type="application/ld+json"]')].map((script) => {
                try {
                    return JSON.parse(script.textContent || '{}');
                } catch {
                    return null;
                }
            }).filter(Boolean);
            const collectTypes = (value, out = []) => {
                if (!value || typeof value !== 'object') return out;
                if (Array.isArray(value)) {
                    value.forEach((item) => collectTypes(item, out));
                    return out;
                }
                if (value['@type']) {
                    if (Array.isArray(value['@type'])) out.push(...value['@type'].map(String));
                    else out.push(String(value['@type']));
                }
                Object.values(value).forEach((child) => collectTypes(child, out));
                return out;
            };
            const origin = location.origin;
            const anchorHrefs = [...document.querySelectorAll('a[href]')].map((a) => a.href).filter(Boolean);
            const internal = [...new Set(anchorHrefs.filter((href) => href.startsWith(origin)))];
            const external = [...new Set(anchorHrefs.filter((href) => !href.startsWith(origin)))];
            const bodyText = (document.body ? document.body.innerText || '' : '').trim();
            return {
                url: location.href,
                user_agent: navigator.userAgent,
                html_lang: document.documentElement.lang || '',
                title: document.title,
                meta_description: meta('description'),
                meta_keywords: meta('keywords'),
                canonical: (document.querySelector('link[rel="canonical"]') || {}).href || '',
                robots_meta: meta('robots'),
                viewport_meta: (document.querySelector('meta[name="viewport"]') || {}).content || '',
                schema_types: [...new Set(collectTypes(schemaBlocks))].sort(),
                schema_count: schemaBlocks.length,
                has_body_text: bodyText.length >= 50,
                viewport: vp,
                h1: [...document.querySelectorAll('h1')].map((h) => h.innerText.trim()).filter(Boolean),
                h2: [...document.querySelectorAll('h2')].map((h) => h.innerText.trim()).filter(Boolean),
                link_summary: {
                    anchor_count: anchorHrefs.length,
                    internal_count: internal.length,
                    external_count: external.length,
                    sample_internal: internal.slice(0, 20),
                    sample_external: external.slice(0, 20),
                },
                above_fold: {
                    h1: first(['h1']),
                    primary_cta: first(['a[href*="collection"]', 'a[href*="product"]', 'button', '[role="button"]', '[class*="cta" i]', '[class*="button" i]']),
                    nav: first(['nav', 'header nav', '[class*="nav" i]']),
                    hero_image: first(['[class*="hero" i] img', 'main img', 'section img']),
                },
                mobile: {
                    has_horizontal_scroll: document.documentElement.scrollWidth > document.documentElement.clientWidth + 1,
                    small_touch_targets: links.filter((item) => item.too_small).slice(0, 20),
                },
                images: {
                    total: imgs.length,
                    without_alt: imgs.filter((img) => !img.alt.trim()).length,
                    without_dimensions: imgs.filter((img) => !img.width_attr || !img.height_attr).length,
                    lazy_loaded: imgs.filter((img) => img.loading === 'lazy').length,
                    srcset_used: imgs.filter((img) => img.srcset).length,
                    above_fold: imgs.filter((img) => img.above_fold).slice(0, 12),
                },
                fonts: [...document.querySelectorAll('link[rel="stylesheet"], link[rel="preload"], style')].map((el) => {
                    const text = el.href || el.textContent || '';
                    if (!/font|@font-face|googleapis|typekit/i.test(text)) return null;
                    return {tag: el.tagName, href: (el.href || '').slice(0, 180), has_font_face: /@font-face/i.test(text)};
                }).filter(Boolean).slice(0, 20),
                resources: {
                    total: resources.length,
                    by_type: resources.reduce((acc, item) => {
                        acc[item.initiatorType] = (acc[item.initiatorType] || 0) + 1;
                        return acc;
                    }, {}),
                    largest: [...resources].sort((a, b) => b.transferSize - a.transferSize).slice(0, 10),
                    items: resources.slice(0, 200),
                },
                timing: nav ? {
                    dom_content_loaded_ms: Math.round(nav.domContentLoadedEventEnd),
                    load_event_ms: Math.round(nav.loadEventEnd),
                    transfer_size: nav.transferSize || 0,
                } : {},
            };
        }"""
    )


def capture(urls: list[str], output_dir: Path, timeout: float, wait_ms: int) -> dict[str, Any]:
    try:
        from playwright.sync_api import sync_playwright
    except ImportError as exc:
        raise RuntimeError("playwright is not installed; run `uv sync` first") from exc

    output_dir.mkdir(parents=True, exist_ok=True)
    report: dict[str, Any] = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "pages": [],
    }
    executable_path = browser_executable()
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True, executable_path=executable_path)
        try:
            for url in urls:
                page_report = {"url": url, "viewports": {}}
                for viewport_name, viewport in VIEWPORTS.items():
                    context = browser.new_context(**context_options(viewport_name, viewport))
                    page = context.new_page()
                    console_errors: list[str] = []
                    page.on("console", lambda msg: console_errors.append(msg.text) if msg.type == "error" else None)
                    try:
                        page.goto(url, wait_until="domcontentloaded", timeout=int(timeout * 1000))
                        page.wait_for_timeout(wait_ms)
                        prefix = f"{slugify(url)}-{viewport_name}"
                        full_path = output_dir / f"{prefix}-full.png"
                        fold_path = output_dir / f"{prefix}-fold.png"
                        with atomic_output_path(full_path) as temporary:
                            page.screenshot(path=str(temporary), type="png", full_page=True, timeout=int(timeout * 1000))
                        with atomic_output_path(fold_path) as temporary:
                            page.screenshot(path=str(temporary), type="png", full_page=False, timeout=int(timeout * 1000))
                        data = analyze_page(page)
                        asset_urls = [item.get("name", "") for item in data.get("resources", {}).get("items", [])]
                        rendered_html = page.content()
                        data["technology_signals"] = detect_technologies(asset_urls, rendered_html)
                        detected_tags = detect_tags(asset_urls, rendered_html)
                        data["analytics_audit"] = {
                            "status": "detected" if detected_tags else "not_detected_during_observation",
                            "detected": detected_tags,
                            "evidence_quality": "runtime resources and rendered DOM after the configured wait; no interactions or consent-state changes",
                        }
                        data["navigation"] = {
                            "requested_url": url,
                            "final_url": data.get("url", ""),
                            "redirected": data.get("url", "") != url,
                            "profile": viewport_name,
                        }
                        data["screenshots"] = {"full": str(full_path), "fold": str(fold_path)}
                        data["console_errors"] = console_errors[:20]
                        page_report["viewports"][viewport_name] = data
                    except Exception as exc:
                        page_report["viewports"][viewport_name] = {"error": str(exc)}
                    finally:
                        context.close()
                report["pages"].append(page_report)
        finally:
            browser.close()
    report["runtime_summary"] = summarize_runtime_report(report)
    path = output_dir / f"rendered-{slugify(urls[0])}-{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}.json"
    atomic_write_text(path, json.dumps(report, ensure_ascii=False, indent=2) + "\n")
    report["output_path"] = str(path)
    return report


def _self_test() -> None:
    assert slugify("https://Example.com/products/A?x=1") == "https-example-com-products-a-x-1"
    assert set(VIEWPORTS) == {"desktop_1920x1080", "tablet_768x1024", "mobile_375x812"}


def main(argv: list[str] | None = None) -> int:
    argp = argparse.ArgumentParser(description="Capture rendered screenshots and viewport evidence with Playwright.")
    argp.add_argument("url", nargs="?", help="URL to inspect")
    argp.add_argument("--page", action="append", default=[], help="Extra URL to inspect; repeatable")
    argp.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    argp.add_argument("--timeout", type=float, default=30)
    argp.add_argument("--wait-ms", type=int, default=2500)
    argp.add_argument("--print", action="store_true", dest="print_json")
    argp.add_argument("--self-test", action="store_true")
    args = argp.parse_args(argv)

    if args.self_test:
        _self_test()
        return 0
    if not args.url:
        argp.error("url is required unless --self-test is used")

    try:
        result = capture([args.url, *args.page], args.output_dir, args.timeout, args.wait_ms)
    except RuntimeError as exc:
        raise SystemExit(str(exc)) from exc

    if args.print_json:
        json.dump(result, sys.stdout, ensure_ascii=False, indent=2)
        sys.stdout.write("\n")
    else:
        print(result["output_path"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
