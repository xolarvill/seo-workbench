from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from seo_workbench_tools import page_probe, robots_sitemap_probe


DEFAULT_OUTPUT_DIR = Path("seo-workbench/audits/raw")


def slugify(value: str) -> str:
    slug = re.sub(r"[^a-zA-Z0-9]+", "-", value).strip("-").lower()
    return slug[:80] or "site"


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

    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "seed_url": url,
        "pages": pages,
        "site": site,
    }


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
