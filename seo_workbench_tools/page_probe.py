from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import dataclass, field
from html.parser import HTMLParser
from time import perf_counter
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import urljoin
from urllib.request import Request, urlopen


USER_AGENT = "SEO-Workbench/0.1 (+https://github.com/seo-workbench)"
PLACEHOLDER_ALTS = {"alt", "title", "icon", "image", "photo", "picture", "img"}
HEADER_KEYS = {
    "cache-control": "cache_control",
    "strict-transport-security": "hsts",
    "x-frame-options": "x_frame_options",
    "x-content-type-options": "x_content_type_options",
    "content-security-policy": "csp",
    "referrer-policy": "referrer_policy",
    "server": "server",
    "x-cache": "x_cache",
    "x-robots-tag": "x_robots_tag",
    "content-length": "content_length",
    "content-encoding": "content_encoding",
}


@dataclass
class SeoParser(HTMLParser):
    base_url: str
    title_parts: list[str] = field(default_factory=list)
    headings: dict[str, list[str]] = field(default_factory=lambda: {f"h{i}": [] for i in range(1, 7)})
    metas: dict[str, str] = field(default_factory=dict)
    links: list[dict[str, str]] = field(default_factory=list)
    images: list[dict[str, str]] = field(default_factory=list)
    json_ld_raw: list[str] = field(default_factory=list)
    text_parts: list[str] = field(default_factory=list)
    _tag_stack: list[str] = field(default_factory=list)
    _capture_script: bool = False
    _script_parts: list[str] = field(default_factory=list)

    def __post_init__(self) -> None:
        HTMLParser.__init__(self)

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        tag = tag.lower()
        attr = {k.lower(): v or "" for k, v in attrs}
        if tag not in {"area", "base", "br", "col", "embed", "hr", "img", "input", "link", "meta", "source", "track", "wbr"}:
            self._tag_stack.append(tag)

        if tag == "meta":
            key = attr.get("name") or attr.get("property")
            if key:
                self.metas[key.lower()] = attr.get("content", "")
        elif tag == "link":
            rel = attr.get("rel", "").lower()
            href = attr.get("href", "")
            if rel and href:
                self.links.append({"rel": rel, "href": urljoin(self.base_url, href)})
        elif tag == "a" and attr.get("href"):
            self.links.append({"rel": "anchor", "href": urljoin(self.base_url, attr["href"])})
        elif tag == "img":
            self.images.append(
                {
                    "src": urljoin(self.base_url, attr.get("src", "")),
                    "alt": attr.get("alt", ""),
                    "width": attr.get("width", ""),
                    "height": attr.get("height", ""),
                    "loading": attr.get("loading", ""),
                }
            )
        elif tag == "script" and attr.get("type", "").lower() == "application/ld+json":
            self._capture_script = True
            self._script_parts = []

    def handle_endtag(self, tag: str) -> None:
        tag = tag.lower()
        if tag == "script" and self._capture_script:
            self.json_ld_raw.append("".join(self._script_parts).strip())
            self._capture_script = False
            self._script_parts = []
        if self._tag_stack:
            self._tag_stack.pop()

    def handle_data(self, data: str) -> None:
        text = " ".join(data.split())
        if not text:
            return
        current = self._tag_stack[-1] if self._tag_stack else ""
        if self._capture_script:
            self._script_parts.append(data)
        elif current == "title":
            self.title_parts.append(text)
        elif current in self.headings:
            self.headings[current].append(text)
        elif current not in {"script", "style", "noscript"}:
            self.text_parts.append(text)


def _schema_type(value: Any) -> Any:
    if isinstance(value, dict):
        return value.get("@type")
    if isinstance(value, list):
        return [_schema_type(item) for item in value]
    return None


def _schema_dicts(value: Any) -> list[dict[str, Any]]:
    if isinstance(value, dict):
        items = [value]
        for child in value.values():
            items.extend(_schema_dicts(child))
        return items
    if isinstance(value, list):
        items = []
        for child in value:
            items.extend(_schema_dicts(child))
        return items
    return []


def _schema_types(value: Any) -> list[str]:
    types = []
    for item in _schema_dicts(value):
        schema_type = item.get("@type")
        if isinstance(schema_type, str):
            types.append(schema_type)
        elif isinstance(schema_type, list):
            types.extend(str(entry) for entry in schema_type if entry)
    return types


def _image_extension(src: str) -> str:
    path = src.split("?", 1)[0].rsplit("/", 1)[-1]
    return path.rsplit(".", 1)[-1].lower() if "." in path else "unknown"


def image_stats(images: list[dict[str, str]]) -> dict[str, Any]:
    formats: dict[str, int] = {}
    stats = {
        "total": len(images),
        "with_descriptive_alt": 0,
        "with_placeholder_alt": 0,
        "missing_alt": 0,
        "has_dimensions": 0,
        "missing_dimensions": 0,
        "format_distribution": formats,
        "without_lazy_loading": 0,
        "tracking_pixels": 0,
    }
    for image in images:
        src = image.get("src", "")
        alt = image.get("alt", "").strip()
        width = image.get("width", "")
        height = image.get("height", "")
        formats[_image_extension(src)] = formats.get(_image_extension(src), 0) + 1
        if not alt:
            stats["missing_alt"] += 1
        elif alt.lower() in PLACEHOLDER_ALTS:
            stats["with_placeholder_alt"] += 1
        else:
            stats["with_descriptive_alt"] += 1
        if width and height:
            stats["has_dimensions"] += 1
        else:
            stats["missing_dimensions"] += 1
        if image.get("loading", "").lower() not in {"lazy", "eager"}:
            stats["without_lazy_loading"] += 1
        if (width == "1" and height == "1") or "facebook.com/tr" in src or "/tr?" in src:
            stats["tracking_pixels"] += 1
    return stats


def schema_audit(schema: list[dict[str, Any]]) -> dict[str, Any]:
    types_found: list[str] = []
    missing_name = []
    empty_blocks = 0
    duplicate_context = False
    no_type_declared = False
    for block in schema:
        if not block.get("valid"):
            continue
        data = block["data"]
        if data in ({}, []):
            empty_blocks += 1
        block_types = _schema_types(data)
        types_found.extend(block_types)
        if not block_types:
            no_type_declared = True
        dicts = _schema_dicts(data)
        if sum(1 for item in dicts if "@context" in item) > 1:
            duplicate_context = True
        for item in dicts:
            schema_type = item.get("@type")
            if schema_type and not item.get("name"):
                if isinstance(schema_type, list):
                    missing_name.extend(str(entry) for entry in schema_type)
                else:
                    missing_name.append(str(schema_type))
    return {
        "schema_types_found": sorted(set(types_found)),
        "empty_blocks": empty_blocks,
        "missing_name_field": sorted(set(missing_name)),
        "duplicate_context": duplicate_context,
        "no_type_declared": no_type_declared,
        "inline_schema_count": len(schema),
    }


def content_audit(html: str, headings: dict[str, list[str]], word_count: int, html_bytes: int) -> dict[str, Any]:
    heading_levels = [int(match) for match in re.findall(r"<h([1-6])\b", html, flags=re.I)]
    hierarchy_valid = not any(curr - prev > 1 for prev, curr in zip(heading_levels, heading_levels[1:]))
    h1_blocks = re.findall(r"<h1\b[^>]*>(.*?)</h1>", html, flags=re.I | re.S)
    body_match = re.search(r"<body\b[^>]*>(.*?)</body>", html, flags=re.I | re.S)
    body_text = re.sub(r"<[^>]+>", " ", body_match.group(1) if body_match else html)
    body_text = " ".join(body_text.split())
    return {
        "h1_count": len(headings["h1"]),
        "h1_empty": any(not re.sub(r"<[^>]+>", "", block).strip() for block in h1_blocks),
        "h2_count": len(headings["h2"]),
        "heading_hierarchy_valid": hierarchy_valid,
        "word_count": word_count,
        "thin_content": word_count < 300,
        "text_to_html_ratio": round((word_count * 5) / html_bytes, 4) if html_bytes else 0,
        "has_body_text_in_raw_html": len(body_text) >= 50,
    }


def parse_html(html: str, base_url: str, html_bytes: int | None = None) -> dict[str, Any]:
    parser = SeoParser(base_url=base_url)
    parser.feed(html)

    schema = []
    for raw in parser.json_ld_raw:
        try:
            parsed = json.loads(raw)
            schema.append({"valid": True, "type": _schema_type(parsed), "data": parsed})
        except json.JSONDecodeError as exc:
            schema.append({"valid": False, "error": str(exc), "raw": raw[:500]})

    text = " ".join(parser.text_parts)
    word_count = len(re.findall(r"\w+", text))
    byte_count = html_bytes if html_bytes is not None else len(html.encode("utf-8"))
    canonical = next((link["href"] for link in parser.links if link["rel"] == "canonical"), "")
    schema_summary = schema_audit(schema)
    return {
        "title": " ".join(parser.title_parts).strip(),
        "meta_description": parser.metas.get("description", ""),
        "canonical": canonical,
        "robots_meta": parser.metas.get("robots", ""),
        "h1": parser.headings["h1"],
        "h2": parser.headings["h2"],
        "images": parser.images,
        "image_stats": image_stats(parser.images),
        "links": parser.links,
        "schema": schema,
        "schema_audit": schema_summary,
        "word_count": word_count,
        "content_audit": content_audit(html, parser.headings, word_count, byte_count),
    }


def response_headers(headers: Any) -> dict[str, str]:
    return {out_key: headers.get(in_key, "") for in_key, out_key in HEADER_KEYS.items()}


def fetch(url: str, timeout: float) -> dict[str, Any]:
    started = perf_counter()
    request = Request(url, headers={"User-Agent": USER_AGENT})
    try:
        with urlopen(request, timeout=timeout) as response:
            body = response.read()
            return {
                "status": response.status,
                "final_url": response.geturl(),
                "content_type": response.headers.get("content-type", ""),
                "headers": response_headers(response.headers),
                "elapsed_ms": round((perf_counter() - started) * 1000),
                "html": body.decode(response.headers.get_content_charset() or "utf-8", "replace"),
                "html_bytes": len(body),
            }
    except HTTPError as exc:
        body = exc.read()
        return {
            "status": exc.code,
            "final_url": exc.geturl(),
            "content_type": exc.headers.get("content-type", ""),
            "headers": response_headers(exc.headers),
            "elapsed_ms": round((perf_counter() - started) * 1000),
            "html": body.decode(exc.headers.get_content_charset() or "utf-8", "replace"),
            "html_bytes": len(body),
        }
    except URLError as exc:
        raise RuntimeError(f"fetch failed: {exc.reason}") from exc


def probe(url: str, timeout: float = 15) -> dict[str, Any]:
    fetched = fetch(url, timeout)
    parsed = parse_html(fetched.pop("html"), fetched["final_url"], fetched["html_bytes"])
    return {"url": url, **fetched, "redirected": fetched["final_url"] != url, **parsed}


def _self_test() -> None:
    html = """<!doctype html><title>Test</title><meta name="description" content="Desc">
    <link rel="canonical" href="/x"><h1>Hello</h1><h2>Sub</h2>
    <script type="application/ld+json">{"@type":"Article","headline":"Hello"}</script>
    <img src="/a.webp" alt="A real image" width="10" height="20" loading="lazy">
    <img src="https://facebook.com/tr?id=1" alt="" width="1" height="1"><a href="/b">B</a><p>One two three.</p>"""
    result = parse_html(html, "https://example.com/page")
    assert result["title"] == "Test"
    assert result["meta_description"] == "Desc"
    assert result["canonical"] == "https://example.com/x"
    assert result["h1"] == ["Hello"]
    assert result["schema"][0]["type"] == "Article"
    assert result["schema_audit"]["schema_types_found"] == ["Article"]
    assert result["images"][0]["src"] == "https://example.com/a.webp"
    assert result["image_stats"]["with_descriptive_alt"] == 1
    assert result["image_stats"]["tracking_pixels"] == 1
    assert result["content_audit"]["h1_count"] == 1
    assert result["word_count"] >= 4


def main(argv: list[str] | None = None) -> int:
    argp = argparse.ArgumentParser(description="Fetch one URL and emit SEO evidence as JSON.")
    argp.add_argument("url", nargs="?", help="URL to inspect")
    argp.add_argument("--timeout", type=float, default=15)
    argp.add_argument("--self-test", action="store_true")
    args = argp.parse_args(argv)

    if args.self_test:
        _self_test()
        return 0
    if not args.url:
        argp.error("url is required unless --self-test is used")

    try:
        result = probe(args.url, args.timeout)
    except RuntimeError as exc:
        raise SystemExit(str(exc)) from exc

    json.dump(result, sys.stdout, ensure_ascii=False, indent=2)
    sys.stdout.write("\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
