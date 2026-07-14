from __future__ import annotations

import argparse
import json
import sys
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from typing import Any
from urllib.parse import urljoin, urlparse

from seo_workbench_tools.page_probe import fetch
from seo_workbench_tools import page_probe


AI_CRAWLERS = {
    "gptbot",
    "chatgpt-user",
    "claudebot",
    "perplexitybot",
    "bytespider",
    "google-extended",
    "ccbot",
}


def site_root(url: str) -> str:
    parsed = urlparse(url)
    if not parsed.scheme or not parsed.netloc:
        raise ValueError("url must include scheme and host")
    return f"{parsed.scheme}://{parsed.netloc}/"


def parse_robots(text: str) -> dict[str, Any]:
    sitemaps = []
    rules = []
    groups: dict[str, list[dict[str, str]]] = {}
    current_agents: list[str] = []
    for line in text.splitlines():
        clean = line.split("#", 1)[0].strip()
        if not clean or ":" not in clean:
            continue
        key, value = clean.split(":", 1)
        key = key.strip().lower()
        value = value.strip()
        if key == "sitemap":
            sitemaps.append(value)
        elif key in {"user-agent", "allow", "disallow", "crawl-delay"}:
            rules.append({"directive": key, "value": value})
            if key == "user-agent":
                current_agents = [value.lower()]
                groups.setdefault(value.lower(), [])
            else:
                for agent in current_agents or ["*"]:
                    groups.setdefault(agent, []).append({"directive": key, "value": value})
    ai_crawler_rules = {
        agent: directives
        for agent, directives in groups.items()
        if agent in AI_CRAWLERS or any(token in agent for token in AI_CRAWLERS)
    }
    return {"sitemaps": sitemaps, "rules": rules, "groups": groups, "ai_crawler_rules": ai_crawler_rules}


def parse_sitemap_xml(xml_text: str) -> dict[str, Any]:
    root = ET.fromstring(xml_text)
    ns = root.tag.split("}", 1)[0] + "}" if root.tag.startswith("{") else ""
    def alternates(node: ET.Element) -> list[dict[str, str]]:
        return [
            {"hreflang": link.attrib.get("hreflang", "").lower(), "href": link.attrib.get("href", "")}
            for link in node.iter()
            if link.tag.endswith("link") and link.attrib.get("rel") == "alternate" and link.attrib.get("hreflang")
        ]

    if root.tag.endswith("sitemapindex"):
        entries = [
            {
                "loc": loc.text.strip(),
                "lastmod": (sitemap.find(f"{ns}lastmod").text or "").strip() if sitemap.find(f"{ns}lastmod") is not None else "",
                "alternates": alternates(sitemap),
            }
            for sitemap in root.findall(f".//{ns}sitemap")
            if (loc := sitemap.find(f"{ns}loc")) is not None and loc.text
        ]
        return {
            "type": "sitemapindex",
            "urls": [entry["loc"] for entry in entries],
            "entries": entries,
        }
    if root.tag.endswith("urlset"):
        entries = [
            {
                "loc": loc.text.strip(),
                "lastmod": (url.find(f"{ns}lastmod").text or "").strip() if url.find(f"{ns}lastmod") is not None else "",
                "alternates": alternates(url),
            }
            for url in root.findall(f".//{ns}url")
            if (loc := url.find(f"{ns}loc")) is not None and loc.text
        ]
        return {
            "type": "urlset",
            "urls": [entry["loc"] for entry in entries],
            "entries": entries,
        }
    return {"type": "unknown", "urls": [], "entries": []}


def parse_lastmod(value: str) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00")).astimezone(timezone.utc)
    except ValueError:
        try:
            return datetime.strptime(value[:10], "%Y-%m-%d").replace(tzinfo=timezone.utc)
        except ValueError:
            return None


def freshness(entries: list[dict[str, str]]) -> dict[str, Any]:
    dates = [date for entry in entries if (date := parse_lastmod(entry.get("lastmod", "")))]
    if not dates:
        return {
            "oldest_lastmod": "",
            "newest_lastmod": "",
            "days_since_newest": None,
            "days_since_oldest": None,
            "stale_percentage": 0,
            "has_lastmod": False,
        }
    today = datetime.now(timezone.utc)
    oldest = min(dates)
    newest = max(dates)
    stale = sum(1 for date in dates if (today - date).days > 365)
    return {
        "oldest_lastmod": oldest.date().isoformat(),
        "newest_lastmod": newest.date().isoformat(),
        "days_since_newest": (today - newest).days,
        "days_since_oldest": (today - oldest).days,
        "stale_percentage": round((stale / len(entries)) * 100, 2) if entries else 0,
        "has_lastmod": True,
    }


def hreflang_codes(entries: list[dict[str, Any]]) -> list[str]:
    return sorted({alt["hreflang"] for entry in entries for alt in entry.get("alternates", []) if alt.get("hreflang")})


def fetch_sitemap(url: str, timeout: float, sample_limit: int) -> dict[str, Any]:
    try:
        fetched = fetch(url, timeout)
        parsed = parse_sitemap_xml(fetched["html"])
        urls = parsed["urls"]
        return {
            "url": url,
            "status": fetched["status"],
            "final_url": fetched["final_url"],
            "type": parsed["type"],
            "url_count": len(urls),
            "sample_urls": urls[:sample_limit],
            "sample_entries": parsed["entries"][:sample_limit],
            "freshness": freshness(parsed["entries"]),
            "hreflang_codes": hreflang_codes(parsed["entries"]),
        }
    except (RuntimeError, ET.ParseError) as exc:
        return {"url": url, "error": str(exc)}


def expand_sitemap_indexes(sitemaps: list[dict[str, Any]], timeout: float, sample_limit: int, max_sitemaps: int = 20) -> list[dict[str, Any]]:
    expanded = []
    seen = {sitemap.get("url", "") for sitemap in sitemaps}
    queue = [child for sitemap in sitemaps if sitemap.get("type") == "sitemapindex" for child in sitemap.get("sample_urls", [])]
    while queue and len(expanded) < max_sitemaps:
        child_url = queue.pop(0)
        if child_url in seen:
            continue
        seen.add(child_url)
        child = fetch_sitemap(child_url, timeout, sample_limit)
        expanded.append(child)
        if child.get("type") == "sitemapindex":
            queue.extend(child.get("sample_urls", []))
    return expanded


def audit_sitemap_sample(sitemaps: list[dict[str, Any]], timeout: float, sample_limit: int) -> dict[str, Any]:
    urls = []
    for sitemap in sitemaps:
        for url in sitemap.get("sample_urls", []):
            if url not in urls:
                urls.append(url)
    checked = []
    issues = []
    for url in urls[: min(sample_limit, 10)]:
        try:
            result = page_probe.probe(url, timeout)
            item = {
                "url": url,
                "status": result.get("status"),
                "final_url": result.get("final_url"),
                "redirected": result.get("redirected"),
                "robots_meta": result.get("robots_meta", ""),
            }
            if result.get("status") != 200:
                issues.append(f"{url} returned {result.get('status')}")
            if result.get("redirected"):
                issues.append(f"{url} redirects to {result.get('final_url')}")
            if not result.get("robots_meta_audit", {}).get("indexable", True):
                issues.append(f"{url} has noindex robots meta")
            checked.append(item)
        except RuntimeError as exc:
            checked.append({"url": url, "error": str(exc)})
            issues.append(f"{url} failed sample fetch: {exc}")
    return {"checked_urls": len(checked), "sampled": checked, "issues": issues}


def probe(url: str, timeout: float = 15, sample_limit: int = 50) -> dict[str, Any]:
    root = site_root(url)
    robots_url = urljoin(root, "robots.txt")
    robots = fetch(robots_url, timeout)
    parsed_robots = parse_robots(robots["html"]) if robots["status"] == 200 else {"sitemaps": [], "rules": [], "groups": {}, "ai_crawler_rules": {}}

    sitemap_urls = parsed_robots["sitemaps"] or [urljoin(root, "sitemap.xml")]
    sitemaps = [fetch_sitemap(sitemap_url, timeout, sample_limit) for sitemap_url in sitemap_urls]
    expanded = expand_sitemap_indexes(sitemaps, timeout, sample_limit)
    all_sitemaps = sitemaps + expanded

    return {
        "url": url,
        "site_root": root,
        "robots": {
            "url": robots_url,
            "status": robots["status"],
            "final_url": robots["final_url"],
            "sitemaps": parsed_robots["sitemaps"],
            "rules": parsed_robots["rules"],
            "groups": parsed_robots["groups"],
            "ai_crawler_rules": parsed_robots["ai_crawler_rules"],
        },
        "sitemaps": all_sitemaps,
        "sitemap_sample_audit": audit_sitemap_sample(all_sitemaps, timeout, sample_limit),
    }


def _self_test() -> None:
    robots = parse_robots("User-agent: *\nDisallow: /cart\nSitemap: https://example.com/sitemap.xml\n")
    assert robots["sitemaps"] == ["https://example.com/sitemap.xml"]
    assert robots["rules"][1] == {"directive": "disallow", "value": "/cart"}
    assert robots["groups"]["*"] == [{"directive": "disallow", "value": "/cart"}]

    urlset = parse_sitemap_xml(
        """<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
        <url><loc>https://example.com/a</loc><lastmod>2026-01-01</lastmod>
        <xhtml:link xmlns:xhtml="http://www.w3.org/1999/xhtml" rel="alternate" hreflang="en-us" href="https://example.com/a"/></url></urlset>"""
    )
    assert urlset["type"] == "urlset"
    assert urlset["urls"] == ["https://example.com/a"]
    assert urlset["entries"][0]["lastmod"] == "2026-01-01"
    assert hreflang_codes(urlset["entries"]) == ["en-us"]
    assert freshness(urlset["entries"])["has_lastmod"] is True


def main(argv: list[str] | None = None) -> int:
    argp = argparse.ArgumentParser(description="Fetch robots.txt and sitemap evidence as JSON.")
    argp.add_argument("url", nargs="?", help="Site URL to inspect")
    argp.add_argument("--timeout", type=float, default=15)
    argp.add_argument("--sample-limit", type=int, default=50)
    argp.add_argument("--self-test", action="store_true")
    args = argp.parse_args(argv)

    if args.self_test:
        _self_test()
        return 0
    if not args.url:
        argp.error("url is required unless --self-test is used")

    try:
        result = probe(args.url, args.timeout, args.sample_limit)
    except (RuntimeError, ValueError) as exc:
        raise SystemExit(str(exc)) from exc

    json.dump(result, sys.stdout, ensure_ascii=False, indent=2)
    sys.stdout.write("\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
