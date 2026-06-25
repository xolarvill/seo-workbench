from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


DEFAULT_OUTPUT_DIR = Path("seo-workbench/audits/rendered")
VIEWPORTS = {
    "desktop_1920x1080": {"width": 1920, "height": 1080},
    "tablet_768x1024": {"width": 768, "height": 1024},
    "mobile_375x812": {"width": 375, "height": 812},
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
            const resources = performance.getEntriesByType('resource').map((entry) => ({
                name: entry.name.slice(0, 180),
                initiatorType: entry.initiatorType,
                transferSize: entry.transferSize || 0,
                duration: Math.round(entry.duration || 0),
            }));
            const nav = performance.getEntriesByType('navigation')[0];
            return {
                url: location.href,
                title: document.title,
                viewport: vp,
                h1: [...document.querySelectorAll('h1')].map((h) => h.innerText.trim()).filter(Boolean),
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
                    largest: resources.sort((a, b) => b.transferSize - a.transferSize).slice(0, 10),
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
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        try:
            for url in urls:
                page_report = {"url": url, "viewports": {}}
                for viewport_name, viewport in VIEWPORTS.items():
                    context = browser.new_context(viewport=viewport)
                    page = context.new_page()
                    console_errors: list[str] = []
                    page.on("console", lambda msg: console_errors.append(msg.text) if msg.type == "error" else None)
                    try:
                        page.goto(url, wait_until="domcontentloaded", timeout=int(timeout * 1000))
                        page.wait_for_timeout(wait_ms)
                        prefix = f"{slugify(url)}-{viewport_name}"
                        full_path = output_dir / f"{prefix}-full.png"
                        fold_path = output_dir / f"{prefix}-fold.png"
                        page.screenshot(path=str(full_path), full_page=True, timeout=int(timeout * 1000))
                        page.screenshot(path=str(fold_path), full_page=False, timeout=int(timeout * 1000))
                        data = analyze_page(page)
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
    path = output_dir / f"rendered-{slugify(urls[0])}-{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}.json"
    path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
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
