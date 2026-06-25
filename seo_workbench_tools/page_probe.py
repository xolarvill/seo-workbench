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


@dataclass
class SeoParser(HTMLParser):
    base_url: str
    title_parts: list[str] = field(default_factory=list)
    headings: dict[str, list[str]] = field(default_factory=lambda: {"h1": [], "h2": []})
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


def parse_html(html: str, base_url: str) -> dict[str, Any]:
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
    canonical = next((link["href"] for link in parser.links if link["rel"] == "canonical"), "")
    return {
        "title": " ".join(parser.title_parts).strip(),
        "meta_description": parser.metas.get("description", ""),
        "canonical": canonical,
        "robots_meta": parser.metas.get("robots", ""),
        "h1": parser.headings["h1"],
        "h2": parser.headings["h2"],
        "images": parser.images,
        "links": parser.links,
        "schema": schema,
        "word_count": len(re.findall(r"\w+", text)),
    }


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
            "elapsed_ms": round((perf_counter() - started) * 1000),
            "html": body.decode(exc.headers.get_content_charset() or "utf-8", "replace"),
            "html_bytes": len(body),
        }
    except URLError as exc:
        raise RuntimeError(f"fetch failed: {exc.reason}") from exc


def probe(url: str, timeout: float = 15) -> dict[str, Any]:
    fetched = fetch(url, timeout)
    parsed = parse_html(fetched.pop("html"), fetched["final_url"])
    return {"url": url, **fetched, "redirected": fetched["final_url"] != url, **parsed}


def _self_test() -> None:
    html = """<!doctype html><title>Test</title><meta name="description" content="Desc">
    <link rel="canonical" href="/x"><h1>Hello</h1><h2>Sub</h2>
    <script type="application/ld+json">{"@type":"Article","headline":"Hello"}</script>
    <img src="/a.jpg" alt="A"><a href="/b">B</a><p>One two three.</p>"""
    result = parse_html(html, "https://example.com/page")
    assert result["title"] == "Test"
    assert result["meta_description"] == "Desc"
    assert result["canonical"] == "https://example.com/x"
    assert result["h1"] == ["Hello"]
    assert result["schema"][0]["type"] == "Article"
    assert result["images"][0]["src"] == "https://example.com/a.jpg"
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
