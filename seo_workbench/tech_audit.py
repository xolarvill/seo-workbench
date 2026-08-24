"""Deterministic, project-scoped technical SEO crawl and issue inventory."""

from __future__ import annotations

import asyncio
import hashlib
import json
import math
import re
import shutil
import time
import urllib.robotparser
import xml.etree.ElementTree as ET
from dataclasses import asdict, dataclass, replace
from datetime import datetime, timedelta, timezone
from email.message import Message
from email.utils import parsedate_to_datetime
from functools import lru_cache
from html.parser import HTMLParser
from pathlib import Path
from typing import Any, Iterable, Literal
from urllib.error import HTTPError, URLError
from urllib.parse import parse_qsl, quote, urlencode, urljoin, urlsplit, urlunsplit
from urllib.request import HTTPRedirectHandler, Request, build_opener

from seo_workbench import state
from seo_workbench.locks import project_lock
from seo_workbench.shopify_crawler import ShopifyCrawlerAccess, read_crawler_access
from seo_workbench.tech_issues import load_issue_register, sync_issue_register
from seo_workbench_tools.files import atomic_write_text
from seo_workbench_tools.network_boundary import inspect_target, sensitive_query_key


SCHEMA_VERSION = "1.0"
COLLECTOR_VERSION = "0.1.0"
TECH_AUDIT_ROOT = "audits/tech-audit"
CONFIG_FINGERPRINT_VERSION = "v2-semantic"
CONFIG_FINGERPRINT_FIELDS = (
    "include_subdomains",
    "load_sitemap",
    "sitemap_urls",
    "max_sitemaps",
    "high_depth",
    "slow_response_ms",
    "large_html_bytes",
    "rendered",
)
_REMAINING_QUEUE_CACHE: dict[tuple[str, int], tuple[list[dict[str, Any]], bool]] = {}
TECH_AUDIT_HISTORY_RETENTION = 3
DEFAULT_CONCURRENCY = 2
DEFAULT_REQUEST_DELAY = 1.0
DEFAULT_BACKOFF = 1.0
DEFAULT_USER_AGENT = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"
MAX_GROUP_EVIDENCE_URLS = 10
RETRYABLE_STATUS = {408, 425, 429, *range(500, 600)}
BLOCKED_CRAWL_STATUSES = {"rate_limited", "blocked_by_waf"}
TRACKING_PARAMETERS = {"fbclid", "gclid", "dclid", "msclkid", "_gl", "ref"}
LOGOUT_RE = re.compile(r"/(?:logout|log-out|signout|sign-out)(?:/|$)", re.I)
CALENDAR_RE = re.compile(r"/(?:calendar|calendars|events?)/", re.I)
LANGUAGE_RE = re.compile(r"^(?:x-default|[a-z]{2,3}(?:-[a-z0-9]{2,8})*)$")


def _semantic_config_fingerprint(config: CrawlConfig) -> str:
    """Fingerprint only the fields that change rule evaluation.

    Collection parameters (crawl limits, concurrency, timeouts, private-network
    access) affect coverage but not which rules fire, so they must not invalidate
    issue presence comparisons between audits.
    """
    payload = {field: getattr(config, field) for field in CONFIG_FINGERPRINT_FIELDS}
    return hashlib.sha256(json.dumps(payload, sort_keys=True, default=list).encode()).hexdigest()


@dataclass(frozen=True)
class CrawlConfig:
    max_urls: int = 1000
    concurrency: int = DEFAULT_CONCURRENCY
    request_delay: float = DEFAULT_REQUEST_DELAY
    retries: int = 2
    backoff: float = DEFAULT_BACKOFF
    timeout: float = 15.0
    user_agent: str = DEFAULT_USER_AGENT
    include_subdomains: bool = False
    load_sitemap: bool = True
    sitemap_urls: tuple[str, ...] = ()
    max_sitemaps: int = 20
    max_redirects: int = 10
    high_depth: int = 3
    slow_response_ms: int = 1000
    large_html_bytes: int = 500_000
    allow_private: bool = False
    rendered: bool = False
    render_limit: int = 5
    render_wait_ms: int = 2500

    def __post_init__(self) -> None:
        if self.max_urls < 1:
            raise ValueError("max_urls must be at least 1")
        if self.concurrency < 1:
            raise ValueError("concurrency must be at least 1")
        if self.request_delay < 0 or self.retries < 0 or self.backoff < 0 or self.timeout <= 0:
            raise ValueError("delay, retries, backoff, and timeout must be non-negative, with timeout positive")
        if self.max_sitemaps < 1 or self.max_redirects < 1:
            raise ValueError("max_sitemaps and max_redirects must be at least 1")
        if self.render_limit < 0 or self.render_wait_ms < 0:
            raise ValueError("render_limit and render_wait_ms must be non-negative")


ViewerDataset = Literal["pages", "links", "issues"]
ViewerDirection = Literal["asc", "desc"]


TECH_AUDIT_VIEW_COLUMNS: dict[str, tuple[dict[str, Any], ...]] = {
    "pages": (
        {"id": "url", "label": "URL", "default": True},
        {"id": "internal_external", "label": "Type", "default": True},
        {"id": "status_code", "label": "Status", "default": True},
        {"id": "indexability", "label": "Indexability", "default": True},
        {"id": "title", "label": "Title", "default": True},
        {"id": "meta_description", "label": "Meta description", "default": True},
        {"id": "meta_keywords", "label": "Meta keywords", "default": True},
        {"id": "h1", "label": "H1", "default": True},
        {"id": "h2", "label": "H2", "default": True},
        {"id": "crawl_depth", "label": "Depth", "default": True},
        {"id": "inlink_count", "label": "Inlinks", "default": True},
        {"id": "outlink_count", "label": "Outlinks", "default": True},
        {"id": "response_time_ms", "label": "Response time", "default": True},
        {"id": "crawl_status", "label": "Crawl status", "default": False},
        {"id": "final_url", "label": "Final URL", "default": False},
        {"id": "content_type", "label": "Content type", "default": False},
        {"id": "response_size", "label": "Response size", "default": False},
        {"id": "canonical", "label": "Canonical", "default": False},
        {"id": "hreflang", "label": "Hreflang", "default": False},
        {"id": "redirect_chain", "label": "Redirect chain", "default": False},
        {"id": "redirect_loop", "label": "Redirect loop", "default": False},
        {"id": "html_content_hash", "label": "Content hash", "default": False},
        {"id": "gsc_clicks", "label": "GSC clicks", "default": False},
        {"id": "gsc_impressions", "label": "GSC impressions", "default": False},
        {"id": "priority", "label": "Priority", "default": False},
    ),
    "links": (
        {"id": "url", "label": "URL", "default": True},
        {"id": "internal_external", "label": "Type", "default": True},
        {"id": "host_relation", "label": "Host relation", "default": True},
        {"id": "crawled", "label": "Crawled", "default": True},
        {"id": "status_code", "label": "Status", "default": True},
        {"id": "final_url", "label": "Final URL", "default": True},
        {"id": "indexability", "label": "Indexability", "default": True},
        {"id": "source_count", "label": "Sources", "default": True},
        {"id": "anchor_texts", "label": "Anchor text", "default": True},
        {"id": "rel", "label": "Rel", "default": True},
        {"id": "excluded_reason", "label": "Excluded reason", "default": True},
    ),
    "issues": (
        {"id": "rule_id", "label": "Rule", "default": True},
        {"id": "title", "label": "Issue", "default": True},
        {"id": "severity", "label": "Severity", "default": True},
        {"id": "category", "label": "Category", "default": True},
        {"id": "url", "label": "URL", "default": True},
        {"id": "priority_tier", "label": "Priority", "default": True},
        {"id": "priority", "label": "Score", "default": True},
        {"id": "workflow_status", "label": "Workflow status", "default": True},
        {"id": "owner", "label": "Owner", "default": False},
        {"id": "gsc_clicks", "label": "GSC clicks", "default": True},
        {"id": "gsc_impressions", "label": "GSC impressions", "default": True},
        {"id": "click_delta", "label": "Click change", "default": True},
        {"id": "remediation_guidance", "label": "Remediation", "default": False},
    ),
}


@dataclass(frozen=True)
class TechAuditViewQuery:
    dataset: ViewerDataset
    query: str = ""
    status_codes: tuple[int, ...] = ()
    indexability: str = ""
    host_relation: str = ""
    rule_id: str = ""
    category: str = ""
    severity: str = ""
    priority_tier: str = ""
    sort: str = "url"
    direction: ViewerDirection = "asc"
    limit: int = 50
    offset: int = 0
    run_id: str = ""
    template: str = ""

    def __post_init__(self) -> None:
        if self.dataset not in TECH_AUDIT_VIEW_COLUMNS:
            raise ValueError("dataset must be pages, links, or issues")
        if self.direction not in {"asc", "desc"}:
            raise ValueError("direction must be asc or desc")
        if self.limit < 1 or self.limit > 200:
            raise ValueError("limit must be between 1 and 200")
        if self.offset < 0:
            raise ValueError("offset must be non-negative")
        allowed = {
            "pages": {"url", "status_code", "priority", "response_time_ms", "crawl_depth", "inlink_count", "outlink_count", "title"},
            "links": {"url", "status_code", "source_count", "host_relation"},
            "issues": {"url", "rule_id", "severity", "priority", "click_delta", "title", "workflow_status", "owner"},
        }[self.dataset]
        if self.sort not in allowed:
            raise ValueError(f"unsupported sort field for {self.dataset}: {self.sort}")


@dataclass(frozen=True)
class TechAuditViewResult:
    dataset: ViewerDataset
    snapshot: dict[str, Any]
    columns: tuple[dict[str, Any], ...]
    rows: list[dict[str, Any]]
    total: int
    offset: int
    limit: int

    def as_dict(self) -> dict[str, Any]:
        return {
            "ok": True,
            "dataset": self.dataset,
            "snapshot": self.snapshot,
            "columns": list(self.columns),
            "rows": self.rows,
            "pagination": {"offset": self.offset, "limit": self.limit, "total": self.total},
        }


class CrawlHtmlParser(HTMLParser):
    """Small HTML parser for deterministic metadata and link inventory."""

    def __init__(self, base_url: str) -> None:
        super().__init__(convert_charrefs=True)
        self.base_url = base_url
        self.title = ""
        self.meta: dict[str, str] = {}
        self.headings: dict[str, list[str]] = {"h1": [], "h2": []}
        self.canonical_values: list[str] = []
        self.hreflang: list[dict[str, str]] = []
        self.links: list[dict[str, Any]] = []
        self._captures: list[dict[str, Any]] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        tag = tag.lower()
        attr = {key.lower(): value or "" for key, value in attrs}
        if tag == "base" and attr.get("href"):
            self.base_url = urljoin(self.base_url, attr["href"])
        if tag == "meta":
            name = (attr.get("name") or attr.get("property") or "").strip().lower()
            if name and name not in self.meta:
                self.meta[name] = attr.get("content", "").strip()
        elif tag == "link" and attr.get("href"):
            href = urljoin(self.base_url, attr["href"])
            rel = tuple(sorted(part.lower() for part in attr.get("rel", "").split() if part))
            if "canonical" in rel:
                self.canonical_values.append(href)
            if "alternate" in rel and attr.get("hreflang"):
                self.hreflang.append({"hreflang": attr["hreflang"].strip().lower(), "href": href})
        elif tag == "a" and attr.get("href"):
            link = {
                "raw_url": attr["href"],
                "href": urljoin(self.base_url, attr["href"]),
                "rel": list(dict.fromkeys(attr.get("rel", "").lower().split())),
                "anchor_text": "",
            }
            self.links.append(link)
            self._captures.append({"tag": "a", "value": link, "text": []})
        if tag in {"title", "h1", "h2"}:
            self._captures.append({"tag": tag, "value": None, "text": []})

    def handle_endtag(self, tag: str) -> None:
        tag = tag.lower()
        for index in range(len(self._captures) - 1, -1, -1):
            capture = self._captures[index]
            if capture["tag"] != tag:
                continue
            text = " ".join(" ".join(capture["text"]).split())
            if tag == "title" and not self.title:
                self.title = text
            elif tag in self.headings and text:
                self.headings[tag].append(text)
            elif tag == "a":
                capture["value"]["anchor_text"] = text
            self._captures.pop(index)
            break

    def handle_data(self, data: str) -> None:
        if not data:
            return
        for capture in self._captures:
            capture["text"].append(data)


class _NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, request: Request, fp: Any, code: int, msg: str, headers: Message, newurl: str) -> None:
        return None


_OPENER = build_opener(_NoRedirect())


def normalize_url(value: str, base_url: str = "") -> str:
    """Normalize crawl URLs and remove fragments/tracking noise."""
    if not value:
        return ""
    absolute = urljoin(base_url, value) if base_url else value
    try:
        parsed = urlsplit(absolute)
        port = parsed.port
    except ValueError:
        return ""
    if parsed.scheme.lower() not in {"http", "https"} or not parsed.hostname:
        return ""
    if parsed.username or parsed.password:
        return ""
    host = parsed.hostname.lower()
    netloc = host
    if port and not ((parsed.scheme.lower() == "http" and port == 80) or (parsed.scheme.lower() == "https" and port == 443)):
        netloc = f"{host}:{port}"
    query_items = []
    for key, item in parse_qsl(parsed.query, keep_blank_values=True):
        if key.lower().startswith("utm_") or key.lower() in TRACKING_PARAMETERS:
            continue
        query_items.append((key, item))
    query_items.sort()
    path = parsed.path or "/"
    if path != "/":
        path = re.sub(r"/{2,}", "/", path).rstrip("/") or "/"
        path = quote(path, safe="/%:@!$&'()*+,;=~-._")
    return urlunsplit((parsed.scheme.lower(), netloc, path, urlencode(query_items), ""))


def page_template(url: str) -> str:
    parts = [part for part in urlsplit(url).path.split("/") if part]
    if parts and LANGUAGE_RE.fullmatch(parts[0]):
        parts = parts[1:]
    if not parts:
        return "home"
    if parts[0] == "products":
        return "product"
    if parts[0] == "collections":
        return "collection"
    if parts[0] == "pages":
        return "page"
    if parts[0] == "blogs":
        return "article" if len(parts) >= 3 else "blog"
    return parts[0]


def page_type(url: str) -> str:
    template = page_template(url)
    return template if template in {"home", "product", "collection", "article", "page"} else "other"


def _root_domain(host: str) -> str:
    labels = host.lower().strip(".").split(".")
    if len(labels) <= 2:
        return ".".join(labels)
    if len(labels[-1]) == 2 and labels[-2] in {"co", "com", "net", "org", "ac", "gov"}:
        return ".".join(labels[-3:])
    return ".".join(labels[-2:])


def link_scope(url: str, seed_url: str) -> tuple[str, str]:
    host = (urlsplit(url).hostname or "").lower()
    seed_host = (urlsplit(seed_url).hostname or "").lower()
    if host == seed_host:
        return "Internal", "same_host"
    if _root_domain(host) == _root_domain(seed_host):
        return "External", "subdomain"
    return "External", "external"


def _is_private_hostname(host: str) -> bool:
    import ipaddress

    if host in {"localhost", "localhost.localdomain"} or host.endswith(".local"):
        return True
    try:
        return not ipaddress.ip_address(host).is_global
    except ValueError:
        return False


def _excluded_url_reason(url: str) -> str:
    parsed = urlsplit(url)
    if parsed.scheme not in {"http", "https"}:
        return "non_http_scheme"
    if _is_private_hostname(parsed.hostname or ""):
        return "private_or_localhost"
    if LOGOUT_RE.search(parsed.path) or any(key.lower() in {"logout", "signout"} for key, _ in parse_qsl(parsed.query)):
        return "logout_url"
    if CALENDAR_RE.search(parsed.path) or any(key.lower() in {"date", "month", "year", "start", "end"} for key, _ in parse_qsl(parsed.query)):
        return "calendar_parameter_trap"
    query = parse_qsl(parsed.query, keep_blank_values=True)
    keys = [key.lower() for key, _ in query]
    if len(query) > 3 or len(keys) != len(set(keys)):
        return "parameter_trap"
    if any(key in {"session", "sessionid", "sid", "token", "auth"} or sensitive_query_key(key) for key in keys):
        return "sensitive_parameter"
    for key, value in query:
        if key.lower() in {"page", "offset", "start"} and value.isdigit() and (int(value) > 100 or int(value) > 10000):
            return "pagination_trap"
    return ""


def _validate_seed(seed_url: str, allow_private: bool) -> str:
    normalized = normalize_url(seed_url)
    if not normalized:
        raise ValueError("project URL must be an absolute HTTP(S) URL")
    reason = _excluded_url_reason(normalized)
    if reason and reason != "private_or_localhost":
        raise ValueError(f"project URL is not crawlable: {reason}")
    inspect_target(normalized, allow_private)
    return normalized


def _load_crawler_access(project_dir: Path, seed_url: str) -> ShopifyCrawlerAccess | None:
    try:
        return read_crawler_access(project_dir, seed_url)
    except FileNotFoundError:
        return None


def _charset(content_type: str) -> str:
    match = re.search(r"charset=([\w.-]+)", content_type, re.I)
    return match.group(1) if match else "utf-8"


def _headers(message: Message) -> dict[str, str]:
    return {str(key).lower(): str(value) for key, value in message.items()}


def _retry_after_seconds(headers: dict[str, str]) -> float | None:
    value = headers.get("retry-after", "").strip()
    if not value:
        return None
    if value.isdigit():
        return float(value)
    try:
        retry_at = parsedate_to_datetime(value)
    except (TypeError, ValueError, OverflowError):
        return None
    if retry_at.tzinfo is None:
        retry_at = retry_at.replace(tzinfo=timezone.utc)
    return max(0.0, (retry_at - datetime.now(timezone.utc)).total_seconds())


def _classify_response(status: int | None, headers: dict[str, str], body: bytes) -> str:
    if status is None:
        return "fetch_error"
    if status == 429:
        return "rate_limited"
    if status in {403, 503}:
        sample = body[:16_384].decode("utf-8", "replace").casefold()
        server = headers.get("server", "").casefold()
        if (
            "cf-mitigated" in headers
            or any(key.startswith("cf-") for key in headers)
            or server in {"cloudflare", "cloudfront", "akamai"}
            or any(marker in sample for marker in ("local_rate_limited", "challenge-platform", "bot detected", "access denied"))
        ):
            return "blocked_by_waf"
    if 200 <= status < 400:
        return "ok"
    if 400 <= status < 600:
        return "http_error"
    return "fetch_error"


def _request_once(url: str, config: CrawlConfig, crawler_access: ShopifyCrawlerAccess | None = None) -> dict[str, Any]:
    started = time.perf_counter()
    headers = {
        "User-Agent": config.user_agent,
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.9",
        "Cache-Control": "no-cache",
        "Pragma": "no-cache",
        "Upgrade-Insecure-Requests": "1",
    }
    if crawler_access:
        headers.update(crawler_access.headers_for(url))
    request = Request(
        url,
        headers=headers,
    )
    try:
        with _OPENER.open(request, timeout=config.timeout) as response:
            body = response.read()
            headers = _headers(response.headers)
            elapsed_ms = round((time.perf_counter() - started) * 1000)
            return {"status": int(response.status), "url": response.geturl(), "headers": headers, "body": body, "elapsed_ms": elapsed_ms}
    except HTTPError as exc:
        body = exc.read()
        headers = _headers(exc.headers)
        elapsed_ms = round((time.perf_counter() - started) * 1000)
        return {"status": int(exc.code), "url": exc.geturl(), "headers": headers, "body": body, "elapsed_ms": elapsed_ms}
    except (OSError, URLError) as exc:
        raise RuntimeError(f"fetch failed: {exc}") from exc


async def _fetch(url: str, seed_url: str, config: CrawlConfig, crawler_access: ShopifyCrawlerAccess | None = None) -> dict[str, Any]:
    chain = [url]
    visited = {url}
    attempts = 0
    errors: list[str] = []
    while len(chain) <= config.max_redirects + 1:
        response: dict[str, Any] | None = None
        for retry in range(config.retries + 1):
            attempts += 1
            if config.request_delay:
                await asyncio.sleep(config.request_delay)
            try:
                response = await asyncio.to_thread(_request_once, chain[-1], config, crawler_access)
            except RuntimeError as exc:
                errors.append(str(exc))
                if retry >= config.retries:
                    return {"requested_url": url, "status": None, "final_url": chain[-1], "redirect_chain": chain, "redirect_loop": False, "attempts": attempts, "errors": errors}
                await asyncio.sleep(config.backoff * (2**retry))
                continue
            if response["status"] not in RETRYABLE_STATUS or retry >= config.retries:
                break
            await asyncio.sleep(max(config.backoff * (2**retry), _retry_after_seconds(response["headers"]) or 0.0))
        if response is None:
            return {"requested_url": url, "status": None, "final_url": chain[-1], "redirect_chain": chain, "redirect_loop": False, "attempts": attempts, "errors": errors}
        status = int(response["status"])
        location = response["headers"].get("location", "")
        if status not in range(300, 400) or not location:
            return {"requested_url": url, "final_url": chain[-1], "redirect_chain": chain, "redirect_loop": False, "attempts": attempts, "errors": errors, **response}
        next_url = normalize_url(location, chain[-1])
        if not next_url:
            return {"requested_url": url, "final_url": chain[-1], "redirect_chain": chain, "redirect_loop": False, "attempts": attempts, "errors": [*errors, "redirect location is not HTTP(S)"], **response}
        _, relation = link_scope(next_url, seed_url)
        if relation == "external":
            return {"requested_url": url, "final_url": next_url, "redirect_chain": [*chain, next_url], "redirect_loop": False, "redirect_to_external": True, "attempts": attempts, "errors": errors, **response}
        if next_url in visited:
            return {"requested_url": url, "final_url": next_url, "redirect_chain": [*chain, next_url], "redirect_loop": True, "attempts": attempts, "errors": errors, **response}
        visited.add(next_url)
        chain.append(next_url)
    return {"requested_url": url, "final_url": chain[-1], "redirect_chain": chain, "redirect_loop": False, "redirect_limit_exceeded": True, "attempts": attempts, "errors": [*errors, "redirect limit exceeded"]}


def _parse_html(html: str, base_url: str) -> dict[str, Any]:
    parser = CrawlHtmlParser(base_url)
    parser.feed(html)
    return {
        "title": parser.title,
        "meta_description": parser.meta.get("description", ""),
        "meta_keywords": parser.meta.get("keywords", ""),
        "h1": parser.headings["h1"],
        "h2": parser.headings["h2"],
        "canonical": parser.canonical_values[0] if parser.canonical_values else "",
        "canonical_values": parser.canonical_values,
        "hreflang": parser.hreflang,
        "meta_robots": parser.meta.get("robots", ""),
        "outlinks": parser.links,
    }


def _parse_robots(text: str, user_agent: str) -> tuple[urllib.robotparser.RobotFileParser, dict[str, Any]]:
    parser = urllib.robotparser.RobotFileParser()
    parser.set_url("https://invalid.local/robots.txt")
    parser.parse(text.splitlines())
    rules: list[dict[str, str]] = []
    groups: dict[str, list[dict[str, str]]] = {}
    current: list[str] = []
    sitemaps: list[str] = []
    for raw in text.splitlines():
        line = raw.split("#", 1)[0].strip()
        if ":" not in line:
            continue
        key, value = (part.strip() for part in line.split(":", 1))
        key = key.lower()
        if key == "sitemap":
            sitemaps.append(value)
        elif key in {"user-agent", "allow", "disallow", "crawl-delay"}:
            rules.append({"directive": key, "value": value})
            if key == "user-agent":
                current = [value.lower()]
                groups.setdefault(value.lower(), [])
            else:
                for agent in current or ["*"]:
                    groups.setdefault(agent, []).append({"directive": key, "value": value})
    return parser, {"sitemaps": sitemaps, "rules": rules, "groups": groups, "user_agent": user_agent}


def _xml_entries(text: str) -> tuple[str, list[dict[str, str]]]:
    root = ET.fromstring(text)
    root_name = root.tag.rsplit("}", 1)[-1].lower()
    node_name = "sitemap" if root_name == "sitemapindex" else "url" if root_name == "urlset" else ""
    entries: list[dict[str, str]] = []
    for node in list(root):
        if node.tag.rsplit("}", 1)[-1].lower() != node_name:
            continue
        loc = next((child.text or "" for child in list(node) if child.tag.rsplit("}", 1)[-1].lower() == "loc"), "").strip()
        if loc:
            entries.append({"loc": loc})
    return (root_name if root_name in {"sitemapindex", "urlset"} else "unknown", entries)


async def _fetch_sitemaps(
    seed_url: str,
    robots: dict[str, Any],
    config: CrawlConfig,
    output_root: Path,
    crawler_access: ShopifyCrawlerAccess | None = None,
) -> tuple[list[dict[str, Any]], list[dict[str, str]]]:
    candidates = list(dict.fromkeys([*config.sitemap_urls, *robots.get("sitemaps", []), urljoin(seed_url, "sitemap.xml")])) if config.load_sitemap else list(config.sitemap_urls)
    queue = [normalize_url(item, seed_url) for item in candidates]
    queue = [
        item for item in queue
        if item and (link_scope(item, seed_url)[1] == "same_host" or (link_scope(item, seed_url)[1] == "subdomain" and config.include_subdomains))
    ]
    seen: set[str] = set()
    entry_urls: set[str] = set()
    sitemap_records: list[dict[str, Any]] = []
    entries: list[dict[str, str]] = []
    while queue and len(seen) < config.max_sitemaps:
        sitemap_url = queue.pop(0)
        if sitemap_url in seen:
            continue
        seen.add(sitemap_url)
        try:
            result = await _fetch(sitemap_url, seed_url, config, crawler_access)
            status = result.get("status")
            body = result.get("body", b"")
            text = body.decode(_charset(result.get("headers", {}).get("content-type", "")), "replace")
            sitemap_type, parsed_entries = _xml_entries(text) if status == 200 else ("unknown", [])
            raw_path = ""
            if body:
                sitemap_file = output_root / "raw" / "sitemaps" / f"{hashlib.sha1(sitemap_url.encode()).hexdigest()[:16]}.xml"
                sitemap_file.parent.mkdir(parents=True, exist_ok=True)
                sitemap_file.write_bytes(body)
                raw_path = sitemap_file.relative_to(output_root).as_posix()
            sitemap_records.append({"url": sitemap_url, "final_url": result.get("final_url", sitemap_url), "status_code": status, "type": sitemap_type, "entry_count": len(parsed_entries), "raw_path": raw_path, "error": result.get("errors", [])})
            if sitemap_type == "sitemapindex":
                queue.extend(normalize_url(item["loc"], sitemap_url) for item in parsed_entries if normalize_url(item["loc"], sitemap_url))
            elif sitemap_type == "urlset":
                for item in parsed_entries:
                    target = normalize_url(item["loc"], sitemap_url)
                    relation = link_scope(target, seed_url)[1] if target else "external"
                    allowed = relation == "same_host" or (relation == "subdomain" and config.include_subdomains)
                    if target and allowed and target not in entry_urls and len(entries) < config.max_urls:
                        entries.append({"url": target, "sitemap_url": sitemap_url})
                        entry_urls.add(target)
        except (ET.ParseError, RuntimeError) as exc:
            sitemap_records.append({"url": sitemap_url, "status_code": None, "type": "unknown", "entry_count": 0, "error": [str(exc)]})
    return sitemap_records, entries


def _page_id(url: str) -> str:
    return f"page_{hashlib.sha1(url.encode()).hexdigest()[:16]}"


def _page_error_page(url: str, depth: int, source: str, reason: str) -> dict[str, Any]:
    return {
        "page_id": _page_id(url), "url": url, "final_url": url, "scope": "Internal", "host_relation": "same_host",
        "status_code": None, "content_type": "", "response_time_ms": None, "response_size": 0, "crawl_depth": depth,
        "inlinks": [], "inlink_count": 0, "outlinks": [], "outlink_count": 0, "anchor_text": [], "rel": [],
        "title": "", "meta_description": "", "meta_keywords": "", "h1": [], "h2": [], "canonical": "",
        "canonical_values": [], "hreflang": [], "meta_robots": "", "x_robots_tag": "", "indexability": {"status": "unknown", "indexable": None},
        "html_content_hash": "", "redirect_chain": [url], "redirect_loop": False, "crawl_sources": [source], "crawl_status": "fetch_error", "error": reason,
    }


async def _crawl(
    seed_url: str,
    config: CrawlConfig,
    output_root: Path,
    start_urls: list[str] | None = None,
    known_urls: set[str] | None = None,
    status_path: Path | None = None,
    run_status: dict[str, Any] | None = None,
    crawler_access: ShopifyCrawlerAccess | None = None,
) -> dict[str, Any]:
    def update_progress(**values: Any) -> None:
        if status_path is None or run_status is None:
            return
        run_status.update(values)
        atomic_write_text(status_path, json.dumps(run_status, ensure_ascii=False, indent=2) + "\n")

    robots_url = urljoin(seed_url, "/robots.txt")
    robots_result = await _fetch(robots_url, seed_url, config, crawler_access)
    robots_body = robots_result.get("body", b"")
    robots_text = robots_body.decode(_charset(robots_result.get("headers", {}).get("content-type", "")), "replace")
    robots_parser, robots_data = _parse_robots(robots_text, config.user_agent)
    update_progress(phase="sitemap", sitemap_count=0, sitemap_entries=0, processed_urls=0, discovered_urls=0, error_count=0)
    sitemap_records, sitemap_entries = await _fetch_sitemaps(seed_url, robots_data, config, output_root, crawler_access)
    update_progress(phase="crawl", sitemap_count=len(sitemap_records), sitemap_entries=len(sitemap_entries), discovered_urls=0, queued_remaining=0)
    sitemap_urls = {entry["url"] for entry in sitemap_entries}
    pages: dict[str, dict[str, Any]] = {}
    inlinks: dict[str, list[dict[str, str]]] = {}
    initial_frontier = (
        [(url, 0, "manual") for url in start_urls]
        if start_urls is not None
        else [(seed_url, 0, "seed"), *((entry["url"], 0, "sitemap") for entry in sitemap_entries if entry["url"] != seed_url)]
    )
    frontier: list[tuple[str, int, str]] = []
    enqueued: set[str] = set(known_urls or ())
    frontier_urls: set[str] = set()
    for item in initial_frontier:
        if item[0] and item[0] not in frontier_urls:
            frontier_urls.add(item[0])
            enqueued.add(item[0])
            frontier.append(item)
    update_progress(discovered_urls=len(enqueued), queued_remaining=len(frontier))
    scheduled: set[str] = set()
    errors: list[dict[str, Any]] = []
    stopped_by_limit = False

    while frontier and len(pages) < config.max_urls:
        batch: list[tuple[str, int, str]] = []
        while frontier and len(batch) < config.concurrency and len(pages) + len(batch) < config.max_urls:
            item = frontier.pop(0)
            if item[0] in scheduled:
                continue
            scheduled.add(item[0])
            batch.append(item)
        if not batch:
            break
        results = await asyncio.gather(*(_fetch(item[0], seed_url, config, crawler_access) for item in batch), return_exceptions=True)
        for (url, depth, source), result in zip(batch, results):
            if isinstance(result, Exception):
                errors.append({"scope": "page", "url": url, "error": str(result)})
                pages[url] = _page_error_page(url, depth, source, str(result))
                continue
            if not robots_parser.can_fetch(config.user_agent, url):
                pages[url] = _page_error_page(url, depth, source, "blocked by robots.txt")
                pages[url]["crawl_status"] = "blocked_by_robots"
                pages[url]["indexability"] = {"status": "blocked_by_robots", "indexable": None}
                continue
            body = result.get("body", b"")
            final_url = normalize_url(str(result.get("final_url", url))) or url
            headers = result.get("headers", {})
            content_type = headers.get("content-type", "")
            crawl_status = _classify_response(result.get("status"), headers, body)
            blocked = crawl_status in BLOCKED_CRAWL_STATUSES
            html = body.decode(_charset(content_type), "replace")
            parsed = (
                {"title": "", "meta_description": "", "meta_keywords": "", "h1": [], "h2": [], "canonical": "", "canonical_values": [], "hreflang": [], "meta_robots": "", "outlinks": []}
                if blocked
                else _parse_html(html, final_url) if ("html" in content_type.lower() or body.lstrip().startswith(b"<"))
                else {"title": "", "meta_description": "", "meta_keywords": "", "h1": [], "h2": [], "canonical": "", "canonical_values": [], "hreflang": [], "meta_robots": "", "outlinks": []}
            )
            meta_robots = parsed["meta_robots"]
            x_robots = headers.get("x-robots-tag", "")
            directives = {item.strip().lower() for item in f"{meta_robots},{x_robots}".split(",") if item.strip()}
            indexable = not bool(directives & {"noindex", "none"})
            page = {
                "page_id": _page_id(url), "url": url, "final_url": final_url,
                "scope": link_scope(url, seed_url)[0], "host_relation": link_scope(url, seed_url)[1],
                "status_code": result.get("status"), "content_type": content_type,
                "response_time_ms": result.get("elapsed_ms"), "response_size": len(body), "crawl_depth": depth,
                "inlinks": [], "inlink_count": 0, "outlinks": [], "outlink_count": 0, "anchor_text": [], "rel": [],
                **{key: parsed[key] for key in ("title", "meta_description", "meta_keywords", "h1", "h2", "canonical", "canonical_values", "hreflang")},
                "meta_robots": meta_robots, "x_robots_tag": x_robots,
                "indexability": {"status": crawl_status if blocked else "indexable" if indexable else "noindex", "indexable": None if blocked else indexable, "directives": [] if blocked else sorted(directives)},
                "html_content_hash": "" if blocked else hashlib.sha256(body).hexdigest() if body else "",
                "redirect_chain": result.get("redirect_chain", [url]), "redirect_loop": bool(result.get("redirect_loop")),
                "redirect_to_external": bool(result.get("redirect_to_external")), "crawl_sources": [source], "crawl_status": crawl_status,
                "error": "; ".join(result.get("errors", [])), "_raw_body": body, "_raw_headers": headers,
            }
            for link in parsed["outlinks"]:
                normalized = normalize_url(link.get("href", ""), final_url)
                if not normalized:
                    continue
                internal_external, relation = link_scope(normalized, seed_url)
                excluded = _excluded_url_reason(normalized)
                allowed_relation = relation == "same_host" or (relation == "subdomain" and config.include_subdomains)
                outlink = {"url": normalized, "internal_external": internal_external, "host_relation": relation, "anchor_text": link.get("anchor_text", ""), "rel": link.get("rel", []), "excluded_reason": excluded or ("subdomain_disabled" if not allowed_relation and relation == "subdomain" else "external" if relation == "external" else "")}
                page["outlinks"].append(outlink)
                if relation != "external":
                    inlinks.setdefault(normalized, []).append({"source_url": url, "anchor_text": link.get("anchor_text", ""), "rel": " ".join(link.get("rel", []))})
                if not excluded and allowed_relation and normalized not in enqueued and depth + 1 <= config.max_urls:
                    enqueued.add(normalized)
                    frontier.append((normalized, depth + 1, "link"))
            pages[url] = page
            if page["error"]:
                errors.append({"scope": "page", "url": url, "error": page["error"]})
            if blocked:
                errors.append({"scope": "page", "url": url, "status": result.get("status"), "kind": crawl_status, "retry_after_seconds": _retry_after_seconds(headers)})
        update_progress(processed_urls=len(pages), discovered_urls=len(enqueued), queued_remaining=len(frontier), error_count=len(errors))
        if len(pages) >= config.max_urls and frontier:
            stopped_by_limit = True
    if frontier and len(pages) >= config.max_urls:
        stopped_by_limit = True
    for url, page in pages.items():
        page["inlinks"] = inlinks.get(url, [])
        page["inlink_count"] = len(page["inlinks"])
        page["outlink_count"] = len(page["outlinks"])
        page["anchor_text"] = sorted({item.get("anchor_text", "") for item in page["outlinks"] if item.get("anchor_text")})
        page["rel"] = sorted({rel for item in page["outlinks"] for rel in item.get("rel", [])})
    update_progress(phase="finalizing", processed_urls=len(pages), discovered_urls=len(enqueued), queued_remaining=len(frontier), error_count=len(errors))
    raw_dir = output_root / "raw" / "pages"
    raw_dir.mkdir(parents=True, exist_ok=True)
    for page in pages.values():
        body = page.pop("_raw_body", b"")
        headers = page.pop("_raw_headers", {})
        if body:
            (raw_dir / f"{page['page_id']}.html").write_bytes(body)
        atomic_write_text(raw_dir / f"{page['page_id']}.json", json.dumps({"url": page["url"], "status_code": page.get("status_code"), "crawl_status": page.get("crawl_status", "ok"), "final_url": page.get("final_url"), "headers": headers, "redirect_chain": page.get("redirect_chain", []), "response_time_ms": page.get("response_time_ms"), "response_size": page.get("response_size", 0), "html_path": f"raw/pages/{page['page_id']}.html" if body else ""}, ensure_ascii=False, indent=2) + "\n")
    raw_site = {"robots": {"url": robots_url, "status_code": robots_result.get("status"), "final_url": robots_result.get("final_url", robots_url), "headers": robots_result.get("headers", {}), "text": robots_text, "parsed": robots_data}, "sitemaps": sitemap_records}
    atomic_write_text(output_root / "raw/site.json", json.dumps(raw_site, ensure_ascii=False, indent=2) + "\n")
    remaining_queue = [{"url": url, "crawl_depth": depth, "crawl_source": source} for url, depth, source in frontier]
    _jsonl_write(output_root / "normalized/remaining-queue.jsonl", remaining_queue)
    update_progress(phase="processing", processed_urls=len(pages), discovered_urls=len(enqueued), queued_remaining=len(remaining_queue), error_count=len(errors))
    return {"pages": pages, "sitemap_records": sitemap_records, "sitemap_entries": sitemap_entries, "sitemap_urls": sitemap_urls, "robots": robots_data, "errors": errors, "stopped_by_limit": stopped_by_limit, "discovered_unique": len(enqueued), "queued_remaining": len(remaining_queue), "remaining_queue": remaining_queue}


def _group_values(pages: Iterable[dict[str, Any]], field: str) -> dict[str, list[dict[str, Any]]]:
    groups: dict[str, list[dict[str, Any]]] = {}
    for page in pages:
        value = page.get(field, "")
        if isinstance(value, list):
            continue
        value = " ".join(str(value).split())
        if value:
            groups.setdefault(value, []).append(page)
    return groups


def _known_page(pages_by_url: dict[str, dict[str, Any]], url: str) -> dict[str, Any] | None:
    if url in pages_by_url:
        return pages_by_url[url]
    return next((page for page in pages_by_url.values() if page.get("final_url") == url), None)


@dataclass(frozen=True)
class RuleDefinition:
    rule_id: str
    title: str
    description: str
    default_severity: str
    category: str
    evaluation_input: str
    evidence_schema: dict[str, str]
    remediation_guidance: str


def _rule(rule_id: str, title: str, description: str, severity: str, category: str, input_text: str, evidence: dict[str, str], remediation: str) -> RuleDefinition:
    return RuleDefinition(rule_id, title, description, severity, category, input_text, evidence, remediation)


RULES: dict[str, RuleDefinition] = {
    item.rule_id: item
    for item in (
        _rule("HTTP_4XX", "Internal URL returns 4xx", "A crawled internal URL returns a client error.", "high", "http", "page.status_code", {"status_code": "integer", "inlinks": "array"}, "Restore the URL or update/remove internal links."),
        _rule("HTTP_5XX", "Internal URL returns 5xx", "A crawled internal URL returns a server error.", "critical", "http", "page.status_code", {"status_code": "integer", "redirect_chain": "array"}, "Fix the upstream application/server failure and verify the URL."),
        _rule("BROKEN_INTERNAL_LINK", "Broken internal link", "An internal link points to a URL returning 4xx/5xx.", "high", "links", "page.status_code and page.inlinks", {"status_code": "integer", "source_urls": "array"}, "Repair the target or remove/replace the linking references."),
        _rule("REDIRECT_CHAIN", "Redirect chain", "The URL needs more than one redirect hop.", "medium", "http", "page.redirect_chain", {"redirect_chain": "array"}, "Link directly to the final canonical URL."),
        _rule("REDIRECT_LOOP", "Redirect loop", "Redirect processing revisits a URL.", "critical", "http", "page.redirect_loop", {"redirect_chain": "array"}, "Remove the conflicting redirect rules and test the full chain."),
        _rule("MISSING_TITLE", "Missing title", "An indexable HTML page has no title.", "high", "metadata", "page.title", {"status_code": "integer", "title": "string"}, "Add a unique, descriptive title for the page intent."),
        _rule("DUPLICATE_TITLE", "Duplicate title", "Multiple pages share the same non-empty title.", "medium", "metadata", "page.title group", {"title": "string", "urls": "array"}, "Write page-specific titles or consolidate duplicate URLs."),
        _rule("MISSING_META_DESCRIPTION", "Missing meta description", "An indexable HTML page has no meta description.", "medium", "metadata", "page.meta_description", {"meta_description": "string"}, "Add a useful summary aligned to the page intent."),
        _rule("DUPLICATE_META_DESCRIPTION", "Duplicate meta description", "Multiple pages share the same non-empty description.", "low", "metadata", "page.meta_description group", {"meta_description": "string", "urls": "array"}, "Make descriptions unique or consolidate duplicate pages."),
        _rule("MISSING_H1", "Missing H1", "An indexable HTML page has no H1.", "medium", "content", "page.h1", {"h1": "array"}, "Add one visible H1 describing the page topic."),
        _rule("MULTIPLE_H1", "Multiple H1 headings", "A page has more than one H1.", "low", "content", "page.h1", {"h1": "array"}, "Keep one primary H1 and demote other headings where appropriate."),
        _rule("MISSING_CANONICAL", "Missing canonical", "An indexable HTML page has no canonical link.", "medium", "indexability", "page.canonical", {"canonical": "string"}, "Declare the preferred absolute canonical URL."),
        _rule("CANONICAL_TO_NON_200", "Canonical points to non-200", "A canonical target is known to return something other than 200.", "high", "indexability", "page.canonical and target.status_code", {"declared_canonical": "string", "canonical_status_code": "integer"}, "Point the canonical at the live preferred URL."),
        _rule("CANONICAL_CONFLICT", "Conflicting canonical", "Multiple canonical declarations or a canonical target disagrees with its own declaration.", "high", "indexability", "page.canonical_values and target.canonical", {"canonical_values": "array", "target_canonical": "string"}, "Keep one canonical declaration and align the target's canonical signal."),
        _rule("CROSS_DOMAIN_CANONICAL", "Cross-domain canonical", "A canonical points outside the managed site family.", "high", "indexability", "page.canonical host", {"canonical": "string", "host_relation": "string"}, "Use a same-site canonical unless the cross-domain consolidation is deliberate."),
        _rule("ACCIDENTAL_NOINDEX", "Accidental noindex", "A linked or sitemap page is blocked from indexing by robots directives.", "high", "indexability", "page.indexability and page.inlinks", {"directives": "array", "inlinks": "array", "in_sitemap": "boolean"}, "Remove noindex when the page is intended to receive organic traffic."),
        _rule("BLOCKED_BY_ROBOTS", "Blocked by robots.txt", "A discovered URL was not fetched because robots.txt disallows it.", "high", "indexability", "robots.can_fetch", {"reason": "string"}, "Allow intentional SEO URLs in robots.txt and keep private areas blocked."),
        _rule("SITEMAP_NON_200", "Sitemap returns non-200", "A discovered sitemap cannot be fetched successfully.", "high", "sitemap", "sitemap.status_code", {"sitemap_url": "string", "status_code": "integer"}, "Restore the sitemap endpoint and verify its content type."),
        _rule("SITEMAP_NOINDEX", "Sitemap URL is noindex", "A URL listed in a sitemap is blocked by noindex.", "high", "sitemap", "sitemap entry and page.indexability", {"url": "string", "directives": "array"}, "Remove the URL from the sitemap or remove noindex from the page."),
        _rule("CRAWLED_NOT_IN_SITEMAP", "Crawled URL missing from sitemap", "A successful internal URL is not represented in the loaded sitemap set.", "low", "sitemap", "page.url and sitemap URLs", {"url": "string", "status_code": "integer"}, "Add important indexable URLs to the sitemap or confirm intentional exclusion."),
        _rule("SITEMAP_NOT_CRAWLED", "Sitemap URL not crawled", "A sitemap URL was not present in the crawl inventory.", "medium", "sitemap", "sitemap URLs and inventory", {"url": "string", "reason": "string"}, "Check crawl limits, robots rules, response errors, and URL validity."),
        _rule("ORPHAN_CANDIDATE", "Orphan candidate", "A sitemap URL has no crawled internal inlinks.", "medium", "links", "page.inlinks and sitemap membership", {"url": "string", "inlink_count": "integer", "in_sitemap": "boolean"}, "Add contextual internal links or confirm the page is intentionally isolated."),
        _rule("HREFLANG_INVALID_CODE", "Invalid hreflang code", "A hreflang value does not match the supported language-tag shape.", "medium", "internationalization", "page.hreflang.hreflang", {"hreflang": "string", "href": "string"}, "Use ISO-style language and optional region codes, or x-default."),
        _rule("HREFLANG_MISSING_RETURN_LINK", "Missing hreflang return link", "A known alternate page does not link back to the source language URL.", "medium", "internationalization", "page.hreflang and target.hreflang", {"source_url": "string", "target_url": "string"}, "Add reciprocal hreflang annotations on both pages."),
        _rule("HREFLANG_TO_NON_200", "Hreflang points to non-200", "A hreflang target is known to return something other than 200.", "high", "internationalization", "page.hreflang and target.status_code", {"href": "string", "status_code": "integer"}, "Point hreflang at live, indexable alternate URLs."),
        _rule("HIGH_CRAWL_DEPTH", "High crawl depth", "A URL is deeper than the configured crawl-depth threshold.", "medium", "architecture", "page.crawl_depth", {"crawl_depth": "integer", "threshold": "integer"}, "Add shorter internal paths from strong hub pages."),
        _rule("NO_INTERNAL_INLINKS", "No internal inlinks", "A crawled URL has no incoming internal links.", "medium", "links", "page.inlink_count", {"inlink_count": "integer"}, "Add a relevant contextual internal link or remove the orphan URL."),
        _rule("SLOW_RESPONSE", "Slow response", "A page response exceeds the configured response-time threshold.", "medium", "performance", "page.response_time_ms", {"response_time_ms": "integer", "threshold_ms": "integer"}, "Reduce server work, caching misses, and upstream latency."),
        _rule("LARGE_HTML", "Large HTML response", "An HTML response exceeds the configured byte threshold.", "low", "performance", "page.response_size", {"response_size": "integer", "threshold_bytes": "integer"}, "Reduce HTML payload and defer non-critical content."),
        _rule("HTTP_HTTPS_MIX", "HTTP/HTTPS mix", "A page contains an internal link using the opposite HTTP scheme.", "high", "architecture", "page.outlinks", {"source_url": "string", "target_url": "string"}, "Use one HTTPS URL family consistently."),
        _rule("WWW_NON_WWW_MIX", "WWW/non-WWW mix", "Internal links use both www and apex host variants.", "medium", "architecture", "page.outlinks", {"source_host": "string", "target_host": "string"}, "Choose one host variant and redirect/link to it consistently."),
        _rule("DUPLICATE_CONTENT_HASH", "Duplicate content", "Multiple crawled HTML pages share the same content hash.", "medium", "content", "page.html_content_hash group", {"content_hash": "string", "urls": "array"}, "Consolidate duplicates or make their content and canonical intent distinct."),
    )
}


def _issue(
    rule_id: str,
    page: dict[str, Any] | None,
    evidence: dict[str, Any],
    severity: str | None = None,
    *,
    fingerprint_evidence: dict[str, Any] | None = None,
) -> dict[str, Any]:
    definition = RULES[rule_id]
    url = str((page or {}).get("url", ""))
    fingerprint = hashlib.sha256(
        json.dumps(
            {"rule_id": rule_id, "url": url, "evidence": fingerprint_evidence or evidence},
            sort_keys=True,
            ensure_ascii=False,
        ).encode()
    ).hexdigest()
    return {"rule_id": rule_id, "title": definition.title, "description": definition.description, "severity": severity or definition.default_severity, "category": definition.category, "page_id": (page or {}).get("page_id", ""), "url": url, "template": page_template(url) if url else "site", "evidence": evidence, "fingerprint": fingerprint, "remediation_guidance": definition.remediation_guidance}


def _group_issues(
    rule_id: str,
    field: str,
    value: str,
    grouped: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    urls = [str(item.get("url", "")) for item in grouped]
    full_evidence = {field: value, "urls": urls}
    evidence = {field: value, "url_count": len(urls), "urls": urls[:MAX_GROUP_EVIDENCE_URLS]}
    return [
        _issue(rule_id, page, evidence, fingerprint_evidence=full_evidence)
        for page in grouped
    ]


def evaluate_rules(pages: list[dict[str, Any]], sitemap_records: list[dict[str, Any]], sitemap_entries: list[dict[str, str]], config: CrawlConfig) -> list[dict[str, Any]]:
    issues: list[dict[str, Any]] = []
    pages_by_url = {page.get("url", ""): page for page in pages}
    sitemap_urls = {entry.get("url", "") for entry in sitemap_entries}
    html_pages = [page for page in pages if page.get("crawl_status") not in BLOCKED_CRAWL_STATUSES and (page.get("content_type", "").lower().startswith(("text/html", "application/xhtml")) or page.get("title") or page.get("h1") or page.get("html_content_hash"))]
    for page in pages:
        status = page.get("status_code")
        blocked = page.get("crawl_status") in BLOCKED_CRAWL_STATUSES
        if not blocked and status is not None and 400 <= int(status) < 500:
            issues.append(_issue("HTTP_4XX", page, {"status_code": status, "inlinks": page.get("inlinks", [])}))
            if page.get("inlink_count", 0):
                issues.append(_issue("BROKEN_INTERNAL_LINK", page, {"status_code": status, "source_urls": [item.get("source_url", "") for item in page.get("inlinks", [])]}))
        if not blocked and status is not None and 500 <= int(status) < 600:
            issues.append(_issue("HTTP_5XX", page, {"status_code": status, "redirect_chain": page.get("redirect_chain", [])}))
        if len(page.get("redirect_chain", [])) > 2:
            issues.append(_issue("REDIRECT_CHAIN", page, {"redirect_chain": page.get("redirect_chain", [])}))
        if page.get("redirect_loop"):
            issues.append(_issue("REDIRECT_LOOP", page, {"redirect_chain": page.get("redirect_chain", [])}))
        if page.get("error") == "blocked by robots.txt":
            issues.append(_issue("BLOCKED_BY_ROBOTS", page, {"reason": page.get("error", "")}))
    for page in html_pages:
        if page.get("indexability", {}).get("indexable") is not True:
            continue
        for rule_id, field in (("MISSING_TITLE", "title"), ("MISSING_META_DESCRIPTION", "meta_description"), ("MISSING_H1", "h1"), ("MISSING_CANONICAL", "canonical")):
            if not page.get(field):
                issues.append(_issue(rule_id, page, {field: page.get(field, []) if field == "h1" else page.get(field, ""), "status_code": page.get("status_code")}))
        if len(page.get("h1", [])) > 1:
            issues.append(_issue("MULTIPLE_H1", page, {"h1": page.get("h1", [])}))
        canonical_values = page.get("canonical_values", [])
        if len(canonical_values) > 1:
            issues.append(_issue("CANONICAL_CONFLICT", page, {"canonical_values": canonical_values}))
        canonical = normalize_url(page.get("canonical", ""), page.get("final_url", ""))
        if canonical:
            relation = link_scope(canonical, pages[0].get("url", "") if pages else page.get("url", ""))[1]
            if relation == "external":
                issues.append(_issue("CROSS_DOMAIN_CANONICAL", page, {"canonical": canonical, "host_relation": relation}))
            target = _known_page(pages_by_url, canonical)
            if target and target.get("crawl_status") not in BLOCKED_CRAWL_STATUSES and target.get("status_code") != 200:
                issues.append(_issue("CANONICAL_TO_NON_200", page, {"declared_canonical": canonical, "canonical_status_code": target.get("status_code")}))
            if target and target.get("canonical") and normalize_url(target.get("canonical", ""), target.get("final_url", "")) != canonical:
                issues.append(_issue("CANONICAL_CONFLICT", page, {"canonical_values": canonical_values, "target_canonical": target.get("canonical", "")}))
        if not page.get("indexability", {}).get("indexable", True) and (page.get("inlink_count", 0) or page.get("url") in sitemap_urls):
            issues.append(_issue("ACCIDENTAL_NOINDEX", page, {"directives": page.get("indexability", {}).get("directives", []), "inlinks": page.get("inlinks", []), "in_sitemap": page.get("url") in sitemap_urls}))
        if page.get("crawl_depth", 0) > config.high_depth:
            issues.append(_issue("HIGH_CRAWL_DEPTH", page, {"crawl_depth": page.get("crawl_depth", 0), "threshold": config.high_depth}))
        if page.get("url") != pages[0].get("url") and page.get("inlink_count", 0) == 0:
            issues.append(_issue("NO_INTERNAL_INLINKS", page, {"inlink_count": 0}))
        if page.get("url") in sitemap_urls and page.get("inlink_count", 0) == 0:
            issues.append(_issue("ORPHAN_CANDIDATE", page, {"url": page.get("url", ""), "inlink_count": 0, "in_sitemap": True}))
        if isinstance(page.get("response_time_ms"), int) and page["response_time_ms"] > config.slow_response_ms:
            issues.append(_issue("SLOW_RESPONSE", page, {"response_time_ms": page["response_time_ms"], "threshold_ms": config.slow_response_ms}))
        if page.get("response_size", 0) > config.large_html_bytes:
            issues.append(_issue("LARGE_HTML", page, {"response_size": page.get("response_size", 0), "threshold_bytes": config.large_html_bytes}))
        for alternate in page.get("hreflang", []):
            code = str(alternate.get("hreflang", ""))
            if not LANGUAGE_RE.fullmatch(code):
                issues.append(_issue("HREFLANG_INVALID_CODE", page, {"hreflang": code, "href": alternate.get("href", "")}))
            target_url = normalize_url(alternate.get("href", ""), page.get("final_url", ""))
            target = _known_page(pages_by_url, target_url)
            if target and target.get("crawl_status") not in BLOCKED_CRAWL_STATUSES and target.get("status_code") != 200:
                issues.append(_issue("HREFLANG_TO_NON_200", page, {"href": target_url, "status_code": target.get("status_code")}))
            if target:
                returns = {normalize_url(item.get("href", ""), target.get("final_url", "")) for item in target.get("hreflang", [])}
                if page.get("url") not in returns and page.get("final_url") not in returns:
                    issues.append(_issue("HREFLANG_MISSING_RETURN_LINK", page, {"source_url": page.get("url", ""), "target_url": target_url}))
        for outlink in page.get("outlinks", []):
            target_url = outlink.get("url", "")
            if outlink.get("host_relation") == "same_host" and urlsplit(target_url).scheme != urlsplit(page.get("url", "")).scheme:
                issues.append(_issue("HTTP_HTTPS_MIX", page, {"source_url": page.get("url", ""), "target_url": target_url}))
            if outlink.get("host_relation") in {"same_host", "subdomain"}:
                source_host = urlsplit(page.get("url", "")).hostname or ""
                target_host = urlsplit(target_url).hostname or ""
                if (source_host.startswith("www.") and not target_host.startswith("www.")) or (target_host.startswith("www.") and not source_host.startswith("www.")):
                    issues.append(_issue("WWW_NON_WWW_MIX", page, {"source_host": source_host, "target_host": target_host}))
    for field, rule_id in (("title", "DUPLICATE_TITLE"), ("meta_description", "DUPLICATE_META_DESCRIPTION")):
        for value, grouped in _group_values(html_pages, field).items():
            if len(grouped) > 1:
                issues.extend(_group_issues(rule_id, field, value, grouped))
    for value, grouped in _group_values(html_pages, "html_content_hash").items():
        if len(value) and len(grouped) > 1:
            issues.extend(_group_issues("DUPLICATE_CONTENT_HASH", "content_hash", value, grouped))
    for sitemap in sitemap_records:
        if sitemap.get("status_code") != 200:
            issues.append(_issue("SITEMAP_NON_200", None, {"sitemap_url": sitemap.get("url", ""), "status_code": sitemap.get("status_code")}))
    for entry in sitemap_entries:
        page = _known_page(pages_by_url, entry.get("url", ""))
        if not page:
            issues.append(_issue("SITEMAP_NOT_CRAWLED", None, {"url": entry.get("url", ""), "reason": "not in crawl inventory"}))
        elif page.get("indexability", {}).get("indexable") is False:
            issues.append(_issue("SITEMAP_NOINDEX", page, {"url": page.get("url", ""), "directives": page.get("indexability", {}).get("directives", [])}))
    if sitemap_entries:
        for page in html_pages:
            if page.get("status_code") == 200 and page.get("url") not in sitemap_urls:
                issues.append(_issue("CRAWLED_NOT_IN_SITEMAP", page, {"url": page.get("url", ""), "status_code": page.get("status_code")}))
    return list({str(issue.get("fingerprint", "")): issue for issue in issues}.values())


def _gsc_page_metrics(project_dir: Path) -> tuple[dict[str, dict[str, float]], dict[str, dict[str, float]], dict[str, Any]]:
    path = state.safe_project_path(project_dir, "audits/gsc/search-analytics/latest.json")
    if not path.is_file():
        return {}, {}, {"status": "not_available", "source": "audits/gsc/search-analytics/latest.json"}
    try:
        report = state.read_json(path)
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        return {}, {}, {"status": "invalid", "error": str(exc)}
    current = _metric_rows(report.get("windows", {}).get("current", {}).get("page", {}).get("rows", []))
    previous = _metric_rows(report.get("windows", {}).get("previous", {}).get("page", {}).get("rows", []))
    return current, previous, {"status": report.get("collection_status", "unknown"), "generated_at": report.get("generated_at", ""), "property": report.get("property", ""), "window_days": report.get("window_days", 0), "data_state": report.get("data_state", ""), "source": "audits/gsc/search-analytics/latest.json"}


def _metric_rows(rows: list[dict[str, Any]]) -> dict[str, dict[str, float]]:
    output: dict[str, dict[str, float]] = {}
    for row in rows:
        keys = row.get("keys", [])
        if not keys:
            continue
        url = normalize_url(str(keys[0]))
        if url:
            output[url] = {key: float(row.get(key, 0) or 0) for key in ("clicks", "impressions", "ctr", "position")}
    return output


def _business_importance(url: str) -> float:
    path = urlsplit(url).path.lower()
    if path == "/":
        return 1.5
    if any(token in path for token in ("/product", "/collection", "/pricing", "/contact", "/shop", "/checkout")):
        return 1.5
    if "/blog/" in path or "/article/" in path:
        return 1.0
    return 1.15


def prioritize_issues(issues: list[dict[str, Any]], current_gsc: dict[str, dict[str, float]], previous_gsc: dict[str, dict[str, float]]) -> list[dict[str, Any]]:
    weights = {"critical": 4.0, "high": 3.0, "medium": 2.0, "low": 1.0}
    for issue in issues:
        metrics = current_gsc.get(normalize_url(issue.get("url", "")), {})
        previous = previous_gsc.get(normalize_url(issue.get("url", "")), {})
        clicks = metrics.get("clicks", 0.0)
        impressions = metrics.get("impressions", 0.0)
        old_clicks = previous.get("clicks", 0.0)
        click_delta = clicks - old_clicks
        click_delta_percent = click_delta / old_clicks if old_clicks else 0.0
        performance = 1.0 + min(1.5, math.log1p(clicks) / 5 + math.log1p(impressions) / 20)
        historical = 1.0 + min(1.0, max(0.0, -click_delta_percent))
        business = _business_importance(issue.get("url", "")) if issue.get("url") else 1.0
        base = weights.get(issue.get("severity", "medium"), 2.0) * 15
        score = round(min(100.0, base * performance * historical * business), 2)
        tier = "critical" if score >= 75 else "high" if score >= 50 else "medium" if score >= 25 else "low"
        issue["priority"] = {"score": score, "tier": tier, "severity_weight": weights.get(issue.get("severity", "medium"), 2.0), "search_performance": {"clicks": clicks, "impressions": impressions, "ctr": metrics.get("ctr", 0.0), "position": metrics.get("position", 0.0)}, "historical_change": {"click_delta": round(click_delta, 2), "click_delta_percent": round(click_delta_percent, 4)}, "business_importance": business, "gsc_attributed": bool(metrics)}
    return sorted(issues, key=lambda item: (-item.get("priority", {}).get("score", 0), item.get("rule_id", ""), item.get("url", "")))


def _issue_summary(issue: dict[str, Any]) -> dict[str, Any]:
    return {
        key: issue.get(key)
        for key in (
            "fingerprint",
            "rule_id",
            "title",
            "severity",
            "category",
            "url",
            "priority",
            "remediation_guidance",
        )
    }


def _jsonl_write(path: Path, rows: Iterable[dict[str, Any]]) -> None:
    atomic_write_text(path, "".join(json.dumps(row, ensure_ascii=False, separators=(",", ":")) + "\n" for row in rows))


def _jsonl_read(path: Path) -> list[dict[str, Any]]:
    if not path.is_file():
        return []
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def _build_link_inventory(pages: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Materialize Internal/External discovery rows without fetching external URLs."""
    pages_by_url = {page.get("url", ""): page for page in pages}
    links: dict[str, dict[str, Any]] = {}
    for page in pages:
        for link in page.get("outlinks", []):
            url = str(link.get("url", ""))
            if not url:
                continue
            row = links.setdefault(
                url,
                {
                    "url": url,
                    "internal_external": link.get("internal_external", "External"),
                    "host_relation": link.get("host_relation", "external"),
                    "status_code": None,
                    "final_url": "",
                    "indexability": {"status": "not_crawled", "indexable": None},
                    "title": "",
                    "meta_description": "",
                    "meta_keywords": "",
                    "h1": [],
                    "h2": [],
                    "sources": [],
                    "anchor_texts": [],
                    "rel": [],
                    "excluded_reason": link.get("excluded_reason", ""),
                },
            )
            row["sources"].append(page.get("url", ""))
            if link.get("anchor_text"):
                row["anchor_texts"].append(link["anchor_text"])
            row["rel"].extend(link.get("rel", []))
    for url, row in links.items():
        page = pages_by_url.get(url)
        if page:
            for field in ("status_code", "final_url", "title", "meta_description", "meta_keywords", "h1", "h2"):
                row[field] = page.get(field, row[field])
            row["indexability"] = page.get("indexability", row["indexability"])
            row["excluded_reason"] = ""
        row["sources"] = sorted(set(row["sources"]))
        row["anchor_texts"] = sorted(set(row["anchor_texts"]))
        row["rel"] = sorted(set(row["rel"]))
    return [links[url] for url in sorted(links)]


def _relative_path(project_dir: Path, path: Path) -> str:
    return path.resolve().relative_to(project_dir.resolve()).as_posix()


@lru_cache(maxsize=32)
def _cached_snapshot(path: str, _modified_at: int) -> dict[str, Any]:
    return state.read_json(Path(path))


_RUN_ID_RE = re.compile(r"^[A-Za-z0-9_-]{1,128}$")


def _read_optional_json(path: Path) -> dict[str, Any]:
    if not path.is_file() or path.is_symlink():
        return {}
    try:
        value = state.read_json(path)
    except (OSError, ValueError, json.JSONDecodeError):
        return {}
    return value if isinstance(value, dict) else {}


def _tech_audit_history_records(project_dir: Path) -> list[dict[str, Any]]:
    root = state.safe_project_path(project_dir, TECH_AUDIT_ROOT)
    snapshots: dict[str, tuple[Path, dict[str, Any]]] = {}
    if root.is_dir() and not root.is_symlink():
        for path in root.glob("tech-audit-*.json"):
            if not path.is_file() or path.is_symlink():
                continue
            snapshot = _read_optional_json(path)
            run_id = str(snapshot.get("run_id", ""))
            if run_id and _RUN_ID_RE.fullmatch(run_id):
                snapshots[run_id] = (path, snapshot)

    statuses: dict[str, dict[str, Any]] = {}
    runs_root = root / "runs"
    if runs_root.is_dir() and not runs_root.is_symlink():
        for run_root in runs_root.iterdir():
            if not run_root.is_dir() or run_root.is_symlink() or not _RUN_ID_RE.fullmatch(run_root.name):
                continue
            status = _read_optional_json(run_root / "run.json")
            run_id = str(status.get("run_id", run_root.name))
            if run_id and _RUN_ID_RE.fullmatch(run_id):
                statuses[run_id] = status

    latest_path = root / "latest.json"
    latest = _read_optional_json(latest_path)
    latest_id = str(latest.get("run_id", ""))
    if latest_id and latest_id not in snapshots and _RUN_ID_RE.fullmatch(latest_id):
        snapshots[latest_id] = (latest_path, latest)

    records: list[dict[str, Any]] = []
    for run_id in set(snapshots) | set(statuses):
        snapshot_path, snapshot = snapshots.get(run_id, (None, {}))
        status = statuses.get(run_id, {})
        kind = str(snapshot.get("kind") or status.get("kind") or "tech-audit")
        if kind != "tech-audit":
            continue
        collection_status = str(snapshot.get("collection_status") or status.get("status") or "unknown")
        run_status = str(status.get("status") or collection_status)
        records.append(
            {
                "run_id": run_id,
                "kind": kind,
                "status": run_status,
                "collection_status": collection_status,
                "started_at": status.get("started_at", ""),
                "finished_at": status.get("finished_at"),
                "generated_at": snapshot.get("generated_at") or status.get("finished_at") or status.get("started_at", ""),
                "summary": snapshot.get("summary") if isinstance(snapshot.get("summary"), dict) else status.get("summary", {}),
                "continuation_of": snapshot.get("continuation_of") or status.get("continuation_of"),
                "active": run_status == "running",
                "snapshot_available": bool(snapshot_path and snapshot_path.is_file()),
                "_snapshot_path": snapshot_path,
            }
        )
    return sorted(records, key=lambda item: (str(item.get("generated_at", "")), str(item["run_id"])), reverse=True)


def tech_audit_history(project_dir: Path) -> list[dict[str, Any]]:
    """Return complete technical-audit runs without exposing filesystem paths."""
    return [{key: value for key, value in record.items() if not key.startswith("_")} for record in _tech_audit_history_records(project_dir)]


def _tech_audit_snapshot_path(project_dir: Path, run_id: str = "") -> Path:
    latest_path = state.safe_project_path(project_dir, f"{TECH_AUDIT_ROOT}/latest.json")
    if not run_id:
        return latest_path
    if not _RUN_ID_RE.fullmatch(run_id):
        raise ValueError("invalid technical audit run_id")
    record = next((item for item in _tech_audit_history_records(project_dir) if item["run_id"] == run_id), None)
    if record is None or not record.get("snapshot_available") or not record.get("_snapshot_path"):
        raise ValueError(f"technical audit run not found: {run_id}")
    return Path(record["_snapshot_path"])


def delete_tech_audit_run(project_dir: Path, run_id: str) -> dict[str, Any]:
    """Delete one completed full-crawl run and repair the stable latest pointer."""
    if not _RUN_ID_RE.fullmatch(run_id):
        raise ValueError("invalid technical audit run_id")
    root = state.safe_project_path(project_dir, TECH_AUDIT_ROOT)
    latest_path = root / "latest.json"
    with project_lock(project_dir):
        records = _tech_audit_history_records(project_dir)
        record = next((item for item in records if item["run_id"] == run_id), None)
        if record is None:
            raise ValueError(f"technical audit run not found: {run_id}")
        if record.get("active"):
            raise RuntimeError("cannot delete a running technical audit")

        latest = _read_optional_json(latest_path)
        was_latest = str(latest.get("run_id", "")) == run_id
        replacement = next(
            (item for item in records if item["run_id"] != run_id and item.get("snapshot_available") and item.get("_snapshot_path")),
            None,
        )
        replacement_snapshot = _read_optional_json(Path(replacement["_snapshot_path"])) if was_latest and replacement else {}

        snapshot_path = record.get("_snapshot_path")
        if snapshot_path and Path(snapshot_path).resolve() != latest_path.resolve() and Path(snapshot_path).is_file() and not Path(snapshot_path).is_symlink():
            Path(snapshot_path).unlink()
        run_root = root / "runs" / run_id
        if run_root.is_dir() and not run_root.is_symlink():
            shutil.rmtree(run_root)

        if was_latest:
            if replacement_snapshot:
                state.write_json(latest_path, replacement_snapshot)
            else:
                latest_path.unlink(missing_ok=True)

    _cached_snapshot.cache_clear()
    _page_issue_views.cache_clear()
    _link_views.cache_clear()
    return {"ok": True, "deleted_run_id": run_id, "latest_run_id": str(replacement_snapshot.get("run_id", "")) or None}


def prune_tech_audit_history(project_dir: Path, keep: int = TECH_AUDIT_HISTORY_RETENTION) -> list[str]:
    """Keep the newest completed full crawls and remove older run artifacts."""
    if keep < 1:
        raise ValueError("keep must be at least 1")
    completed = [
        record
        for record in _tech_audit_history_records(project_dir)
        if not record.get("active") and record.get("snapshot_available")
    ]
    deleted: list[str] = []
    for record in completed[keep:]:
        delete_tech_audit_run(project_dir, str(record["run_id"]))
        deleted.append(str(record["run_id"]))
    return deleted


def load_tech_snapshot(project_dir: Path, snapshot_path: Path | None = None) -> dict[str, Any]:
    path = snapshot_path or state.safe_project_path(project_dir, f"{TECH_AUDIT_ROOT}/latest.json")
    if not path.is_file():
        return {}
    return _cached_snapshot(str(path.resolve()), path.stat().st_mtime_ns)


def load_tech_issues(project_dir: Path, snapshot_path: Path | None = None) -> list[dict[str, Any]]:
    snapshot_path = snapshot_path or state.safe_project_path(project_dir, f"{TECH_AUDIT_ROOT}/latest.json")
    snapshot = load_tech_snapshot(project_dir, snapshot_path)
    issues_path = snapshot.get("artifacts", {}).get("issues_path", "")
    if not issues_path:
        return []
    path = state.safe_project_path(project_dir, issues_path)
    if not path.is_file():
        return []
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def load_tech_inventory(project_dir: Path, snapshot_path: Path | None = None) -> list[dict[str, Any]]:
    """Load the normalized URL inventory referenced by a technical audit snapshot."""
    snapshot_path = snapshot_path or state.safe_project_path(project_dir, f"{TECH_AUDIT_ROOT}/latest.json")
    snapshot = load_tech_snapshot(project_dir, snapshot_path)
    inventory_path = snapshot.get("artifacts", {}).get("inventory_path", "")
    if not inventory_path:
        return []
    path = state.safe_project_path(project_dir, inventory_path)
    if not path.is_file():
        return []
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def load_tech_links(project_dir: Path, snapshot_path: Path | None = None) -> list[dict[str, Any]]:
    """Load the normalized discovered-link inventory referenced by a snapshot."""
    snapshot_path = snapshot_path or state.safe_project_path(project_dir, f"{TECH_AUDIT_ROOT}/latest.json")
    snapshot = load_tech_snapshot(project_dir, snapshot_path)
    links_path = snapshot.get("artifacts", {}).get("link_inventory_path", "")
    if not links_path:
        return []
    path = state.safe_project_path(project_dir, links_path)
    if not path.is_file():
        return []
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def load_remaining_crawl_queue(project_dir: Path, snapshot_path: Path | None = None) -> tuple[list[dict[str, Any]], bool]:
    """Load the persisted queue, or recover a best-effort queue from an old capped snapshot."""
    snapshot_path = snapshot_path or state.safe_project_path(project_dir, f"{TECH_AUDIT_ROOT}/latest.json")
    if not snapshot_path.is_file():
        return [], False
    snapshot = load_tech_snapshot(project_dir, snapshot_path)
    queue_ref = snapshot.get("artifacts", {}).get("remaining_queue_path", "")
    if queue_ref:
        queue_path = state.safe_project_path(project_dir, queue_ref)
        if queue_path.is_file():
            return _jsonl_read(queue_path), False
    if not snapshot.get("summary", {}).get("stopped_by_limit"):
        return [], False
    cache_key = (str(snapshot_path.resolve()), snapshot_path.stat().st_mtime_ns)
    if cache_key in _REMAINING_QUEUE_CACHE:
        return _REMAINING_QUEUE_CACHE[cache_key]
    config = snapshot.get("config", {})
    include_subdomains = bool(config.get("include_subdomains"))
    max_depth = int(config.get("max_urls", 1000) or 1000)
    pages = load_tech_inventory(project_dir, snapshot_path)
    crawled = {normalize_url(str(page.get("url", ""))) for page in pages}
    recovered: dict[str, dict[str, Any]] = {}

    sitemap_ref = snapshot.get("artifacts", {}).get("sitemap_entries_path", "")
    sitemap_entries = _jsonl_read(state.safe_project_path(project_dir, sitemap_ref)) if sitemap_ref else []
    for entry in sitemap_entries:
        url = normalize_url(str(entry.get("url", "")))
        if url and url not in crawled and url not in recovered:
            relation = link_scope(url, snapshot.get("seed_url", ""))[1]
            if relation == "same_host" or (relation == "subdomain" and include_subdomains):
                recovered[url] = {"url": url, "crawl_depth": 0, "crawl_source": "recovered-sitemap"}
    for page in pages:
        depth = int(page.get("crawl_depth", 0) or 0) + 1
        if depth > max_depth:
            continue
        for link in page.get("outlinks", []):
            url = normalize_url(str(link.get("url", "")))
            relation = str(link.get("host_relation", ""))
            if not url or url in crawled or url in recovered or _excluded_url_reason(url):
                continue
            if relation == "same_host" or (relation == "subdomain" and include_subdomains):
                recovered[url] = {"url": url, "crawl_depth": depth, "crawl_source": "recovered-link"}
    result = (list(recovered.values()), True)
    if len(_REMAINING_QUEUE_CACHE) >= 32:
        _REMAINING_QUEUE_CACHE.pop(next(iter(_REMAINING_QUEUE_CACHE)))
    _REMAINING_QUEUE_CACHE[cache_key] = result
    return result


def _snapshot_summary(project_dir: Path, snapshot_path: Path | None = None) -> dict[str, Any]:
    try:
        snapshot = load_tech_snapshot(project_dir, snapshot_path)
    except (OSError, ValueError, json.JSONDecodeError):
        return {}
    return {key: snapshot.get(key) for key in ("generated_at", "run_id", "collection_status", "summary") if key in snapshot}


def _recrawl_pages(project_dir: Path) -> dict[str, dict[str, Any]]:
    path = state.safe_project_path(project_dir, f"{TECH_AUDIT_ROOT}/latest-recrawl.json")
    if not path.is_file():
        return {}
    try:
        report = state.read_json(path)
    except (OSError, ValueError, json.JSONDecodeError):
        return {}
    return {
        normalize_url(str(page.get("url", ""))): page
        for page in report.get("pages", [])
        if isinstance(page, dict) and normalize_url(str(page.get("url", "")))
    }


def _search_performance(page: dict[str, Any]) -> dict[str, Any]:
    value = page.get("search_performance")
    return value if isinstance(value, dict) else {"status": "not_found", "previous": {}}


def _issue_stats(issues: list[dict[str, Any]]) -> tuple[list[str], list[str], float, str]:
    issue_ids = list(dict.fromkeys(str(issue.get("rule_id", "")) for issue in issues if issue.get("rule_id")))
    severities = list(dict.fromkeys(str(issue.get("severity", "")) for issue in issues if issue.get("severity")))
    priority = max((float(issue.get("priority", {}).get("score", 0) or 0) for issue in issues), default=0.0)
    tier_order = {"critical": 4, "high": 3, "medium": 2, "low": 1}
    tier = max((str(issue.get("priority", {}).get("tier", "")) for issue in issues), key=lambda item: tier_order.get(item, 0), default="")
    return issue_ids, severities, priority, tier


def _page_view_row(page: dict[str, Any], issues: list[dict[str, Any]], recrawl: dict[str, Any] | None = None) -> dict[str, Any]:
    performance = _search_performance(page)
    previous = performance.get("previous") if isinstance(performance.get("previous"), dict) else {}
    issue_ids, severities, priority, priority_tier = _issue_stats(issues)
    return {
        "row_key": page.get("url", ""),
        "page_id": page.get("page_id", ""),
        "url": page.get("url", ""),
        "final_url": page.get("final_url", ""),
        "internal_external": page.get("scope", "Internal"),
        "host_relation": page.get("host_relation", "same_host"),
        "status_code": page.get("status_code"),
        "crawl_status": page.get("crawl_status", "ok"),
        "content_type": page.get("content_type", ""),
        "indexability": page.get("indexability", {"status": "unknown", "indexable": None}),
        "title": page.get("title", ""),
        "meta_description": page.get("meta_description", ""),
        "meta_keywords": page.get("meta_keywords", ""),
        "h1": page.get("h1", []),
        "h2": page.get("h2", []),
        "canonical": page.get("canonical", ""),
        "hreflang": page.get("hreflang", []),
        "meta_robots": page.get("meta_robots", ""),
        "x_robots_tag": page.get("x_robots_tag", ""),
        "redirect_chain": page.get("redirect_chain", []),
        "redirect_loop": bool(page.get("redirect_loop")),
        "crawl_depth": page.get("crawl_depth", 0),
        "inlink_count": page.get("inlink_count", 0),
        "outlink_count": page.get("outlink_count", 0),
        "anchor_text": page.get("anchor_text", []),
        "rel": page.get("rel", []),
        "response_time_ms": page.get("response_time_ms"),
        "response_size": page.get("response_size", 0),
        "html_content_hash": page.get("html_content_hash", ""),
        "issue_ids": issue_ids,
        "severities": severities,
        "issue_count": len(issues),
        "priority": round(priority, 2),
        "priority_tier": priority_tier,
        "search_performance": performance,
        "gsc_clicks": performance.get("clicks", 0),
        "gsc_impressions": performance.get("impressions", 0),
        "click_delta": round(float(performance.get("clicks", 0) or 0) - float(previous.get("clicks", 0) or 0), 2),
        "last_recrawl": {
            "status_code": recrawl.get("status_code"),
            "final_url": recrawl.get("final_url", ""),
        } if recrawl else None,
    }


def _link_view_row(link: dict[str, Any], page: dict[str, Any] | None = None) -> dict[str, Any]:
    indexability = link.get("indexability", {"status": "not_crawled", "indexable": None})
    return {
        "row_key": link.get("url", ""),
        "url": link.get("url", ""),
        "internal_external": link.get("internal_external", "External"),
        "host_relation": link.get("host_relation", "external"),
        "crawled": bool(page or link.get("status_code") is not None or link.get("final_url")),
        "status_code": link.get("status_code"),
        "final_url": link.get("final_url", ""),
        "indexability": indexability,
        "title": link.get("title", ""),
        "meta_description": link.get("meta_description", ""),
        "meta_keywords": link.get("meta_keywords", ""),
        "h1": link.get("h1", []),
        "h2": link.get("h2", []),
        "source_count": len(link.get("sources", [])),
        "sources": link.get("sources", []),
        "anchor_texts": link.get("anchor_texts", []),
        "rel": link.get("rel", []),
        "excluded_reason": link.get("excluded_reason", ""),
    }


def _issue_view_row(
    issue: dict[str, Any],
    page: dict[str, Any] | None = None,
    workflow: dict[str, Any] | None = None,
    *,
    include_evidence: bool = False,
) -> dict[str, Any]:
    priority = issue.get("priority") if isinstance(issue.get("priority"), dict) else {}
    performance = _search_performance(page or {})
    historical = priority.get("historical_change") if isinstance(priority.get("historical_change"), dict) else {}
    row = {
        "row_key": issue.get("fingerprint") or f"{issue.get('rule_id', '')}:{issue.get('url', '')}",
        "fingerprint": issue.get("fingerprint", ""),
        "rule_id": issue.get("rule_id", ""),
        "template": issue.get("template", ""),
        "title": issue.get("title", ""),
        "description": issue.get("description", ""),
        "severity": issue.get("severity", ""),
        "category": issue.get("category", ""),
        "url": issue.get("url", ""),
        "page_id": issue.get("page_id", ""),
        "priority": round(float(priority.get("score", 0) or 0), 2),
        "priority_tier": priority.get("tier", ""),
        "gsc_clicks": performance.get("clicks", priority.get("search_performance", {}).get("clicks", 0)),
        "gsc_impressions": performance.get("impressions", priority.get("search_performance", {}).get("impressions", 0)),
        "click_delta": historical.get("click_delta", 0),
        "remediation_guidance": issue.get("remediation_guidance", ""),
        "workflow_status": (workflow or {}).get("status", "open"),
        "owner": (workflow or {}).get("owner", ""),
        "verification_status": (workflow or {}).get("verification_status", "not_requested"),
    }
    if include_evidence:
        row["evidence"] = issue.get("evidence", {})
    return row


def _viewer_sort_value(row: dict[str, Any], field: str) -> tuple[bool, Any]:
    value = row.get(field)
    if isinstance(value, dict):
        value = value.get("status", "")
    if isinstance(value, list):
        value = ", ".join(str(item) for item in value)
    if value is None:
        return True, ""
    if isinstance(value, (int, float)):
        return False, value
    return False, str(value).casefold()


def _viewer_query_text(row: dict[str, Any]) -> str:
    values = [row.get("url", ""), row.get("title", ""), row.get("meta_description", ""), row.get("meta_keywords", ""), row.get("rule_id", ""), row.get("description", ""), row.get("remediation_guidance", ""), row.get("workflow_status", ""), row.get("owner", "")]
    values.extend(row.get("h1", []) if isinstance(row.get("h1"), list) else [])
    values.extend(row.get("h2", []) if isinstance(row.get("h2"), list) else [])
    return " ".join(str(value) for value in values).casefold()


def _modified_at(path: Path) -> int:
    try:
        return path.stat().st_mtime_ns
    except OSError:
        return 0


def _is_latest_snapshot(project_dir: Path, snapshot_path: Path) -> bool:
    return snapshot_path.resolve() == state.safe_project_path(project_dir, f"{TECH_AUDIT_ROOT}/latest.json").resolve()


def _load_view_rows(project_dir: Path, snapshot_path: Path, loader: Any) -> list[dict[str, Any]]:
    return loader(project_dir) if _is_latest_snapshot(project_dir, snapshot_path) else loader(project_dir, snapshot_path)


def _tech_view_key(project_dir: Path, snapshot_path: Path) -> tuple[str, str, int, int, int]:
    return (
        str(project_dir.resolve()),
        str(snapshot_path.resolve()),
        _modified_at(snapshot_path),
        _modified_at(state.safe_project_path(project_dir, "strategy/technical-issues.jsonl")),
        _modified_at(state.safe_project_path(project_dir, f"{TECH_AUDIT_ROOT}/latest-recrawl.json")),
    )


# ponytail: four active project projections; increase only if real multi-project churn shows cache misses.
@lru_cache(maxsize=4)
def _page_issue_views(
    project_path: str,
    snapshot_path: str,
    _snapshot_modified_at: int,
    _register_modified_at: int,
    _recrawl_modified_at: int,
) -> tuple[dict[str, Any], tuple[dict[str, Any], ...], tuple[dict[str, Any], ...]]:
    project_dir = Path(project_path)
    selected_snapshot = Path(snapshot_path)
    pages = _load_view_rows(project_dir, selected_snapshot, load_tech_inventory)
    page_by_url = {normalize_url(str(page.get("url", ""))): page for page in pages}
    issue_list = _load_view_rows(project_dir, selected_snapshot, load_tech_issues)
    issue_workflow = {
        str(record.get("fingerprint", "")): record
        for record in load_issue_register(project_dir)
    }
    issues_by_url: dict[str, list[dict[str, Any]]] = {}
    for issue in issue_list:
        url = normalize_url(str(issue.get("url", "")))
        if url:
            issues_by_url.setdefault(url, []).append(issue)
    recrawls = _recrawl_pages(project_dir) if _is_latest_snapshot(project_dir, selected_snapshot) else {}
    page_rows = tuple(
        _page_view_row(
            page,
            issues_by_url.get(normalize_url(str(page.get("url", ""))), []),
            recrawls.get(normalize_url(str(page.get("url", ""))), None),
        )
        for page in pages
    )
    issue_rows = tuple(
        _issue_view_row(
            issue,
            page_by_url.get(normalize_url(str(issue.get("url", "")))),
            issue_workflow.get(str(issue.get("fingerprint", ""))),
        )
        for issue in issue_list
    )
    snapshot = _snapshot_summary(project_dir) if _is_latest_snapshot(project_dir, selected_snapshot) else _snapshot_summary(project_dir, selected_snapshot)
    return snapshot, page_rows, issue_rows


@lru_cache(maxsize=4)
def _link_views(
    project_path: str,
    snapshot_path: str,
    _snapshot_modified_at: int,
) -> tuple[dict[str, Any], tuple[dict[str, Any], ...]]:
    project_dir = Path(project_path)
    selected_snapshot = Path(snapshot_path)
    pages = _load_view_rows(project_dir, selected_snapshot, load_tech_inventory)
    page_by_url = {normalize_url(str(page.get("url", ""))): page for page in pages}
    rows = tuple(
        _link_view_row(link, page_by_url.get(normalize_url(str(link.get("url", "")))))
        for link in _load_view_rows(project_dir, selected_snapshot, load_tech_links)
    )
    snapshot = _snapshot_summary(project_dir) if _is_latest_snapshot(project_dir, selected_snapshot) else _snapshot_summary(project_dir, selected_snapshot)
    return snapshot, rows


def query_tech_audit(project_dir: Path, query: TechAuditViewQuery) -> TechAuditViewResult:
    selected_snapshot = _tech_audit_snapshot_path(project_dir, query.run_id)
    project_path, snapshot_path, snapshot_modified_at, register_modified_at, recrawl_modified_at = _tech_view_key(project_dir, selected_snapshot)
    if query.dataset == "links":
        snapshot, cached_rows = _link_views(project_path, snapshot_path, snapshot_modified_at)
    else:
        snapshot, page_rows, issue_rows = _page_issue_views(
            project_path,
            snapshot_path,
            snapshot_modified_at,
            register_modified_at,
            recrawl_modified_at,
        )
        cached_rows = page_rows if query.dataset == "pages" else issue_rows
    rows = list(cached_rows)

    query_text = query.query.casefold().strip()
    if query_text:
        rows = [row for row in rows if query_text in _viewer_query_text(row)]
    if query.status_codes:
        rows = [row for row in rows if row.get("status_code") in query.status_codes]
    if query.indexability:
        rows = [row for row in rows if str(row.get("indexability", {}).get("status", "")).casefold() == query.indexability.casefold()]
    if query.host_relation.casefold() == "site_family":
        rows = [row for row in rows if str(row.get("host_relation", "")).casefold() in {"same_host", "subdomain"}]
    elif query.host_relation and query.host_relation.casefold() != "all":
        rows = [row for row in rows if str(row.get("host_relation", "")).casefold() == query.host_relation.casefold()]
    if query.rule_id:
        rows = [row for row in rows if str(row.get("rule_id", "")).casefold() == query.rule_id.casefold() or query.rule_id.casefold() in {str(value).casefold() for value in row.get("issue_ids", [])}]
    if query.template:
        rows = [row for row in rows if str(row.get("template", "")).casefold() == query.template.casefold()]
    if query.category:
        rows = [row for row in rows if str(row.get("category", "")).casefold() == query.category.casefold()]
    if query.severity:
        rows = [row for row in rows if str(row.get("severity", "")).casefold() == query.severity.casefold() or query.severity.casefold() in {str(value).casefold() for value in row.get("severities", [])}]
    if query.priority_tier:
        rows = [row for row in rows if str(row.get("priority_tier", "")).casefold() == query.priority_tier.casefold()]
    rows.sort(key=lambda row: _viewer_sort_value(row, query.sort), reverse=query.direction == "desc")
    total = len(rows)
    return TechAuditViewResult(query.dataset, snapshot, TECH_AUDIT_VIEW_COLUMNS[query.dataset], rows[query.offset : query.offset + query.limit], total, query.offset, query.limit)


def _load_latest_diff(project_dir: Path) -> dict[str, Any]:
    path = state.safe_project_path(project_dir, "audits/diffs/latest.json")
    if not path.is_file():
        return {}
    try:
        return state.read_json(path)
    except (OSError, ValueError, json.JSONDecodeError):
        return {}


def tech_audit_detail(project_dir: Path, dataset: ViewerDataset, key: str, run_id: str = "") -> dict[str, Any]:
    selected_snapshot = _tech_audit_snapshot_path(project_dir, run_id)
    pages = _load_view_rows(project_dir, selected_snapshot, load_tech_inventory)
    page_by_url = {normalize_url(str(page.get("url", ""))): page for page in pages}
    issues = _load_view_rows(project_dir, selected_snapshot, load_tech_issues)
    issues_by_url: dict[str, list[dict[str, Any]]] = {}
    for issue in issues:
        url = normalize_url(str(issue.get("url", "")))
        if url:
            issues_by_url.setdefault(url, []).append(issue)
    recrawls = _recrawl_pages(project_dir) if _is_latest_snapshot(project_dir, selected_snapshot) else {}
    normalized_key = normalize_url(key)
    if dataset == "pages":
        page = page_by_url.get(normalized_key)
        if not page:
            raise ValueError("page not found in latest technical audit")
        row = _page_view_row(page, issues_by_url.get(normalized_key, []), recrawls.get(normalized_key))
        row.update({"inlinks": page.get("inlinks", []), "outlinks": page.get("outlinks", []), "canonical_values": page.get("canonical_values", [])})
        related_issues = issues_by_url.get(normalized_key, [])
    elif dataset == "links":
        link = next((item for item in load_tech_links(project_dir) if normalize_url(str(item.get("url", ""))) == normalized_key), None)
        if not link:
            raise ValueError("link not found in latest technical audit")
        row = _link_view_row(link, page_by_url.get(normalized_key))
        related_issues = issues_by_url.get(normalized_key, [])
    else:
        issue = next((item for item in issues if str(item.get("fingerprint", "")) == key or (str(item.get("rule_id", "")) + ":" + str(item.get("url", ""))) == key), None)
        if not issue:
            raise ValueError("issue not found in latest technical audit")
        row = _issue_view_row(issue, page_by_url.get(normalize_url(str(issue.get("url", "")))))
        related_issues = [issue]
        normalized_key = normalize_url(str(issue.get("url", "")))
    diff = _load_latest_diff(project_dir).get("comparisons", {}).get("tech-audit", {}) if _is_latest_snapshot(project_dir, selected_snapshot) else {}
    changes = [item for item in diff.get("changes", []) if str(item.get("key", "")).endswith(f":{normalized_key}")]
    return {
        "ok": True,
        "dataset": dataset,
        "row": row,
        "issues": related_issues,
        "recrawl": recrawls.get(normalized_key),
        "diff": {"comparable": diff.get("comparable", False), "changes": changes, "warnings": diff.get("warnings", [])},
    }


def _issue_action_groups(issues: list[dict[str, Any]]) -> list[dict[str, Any]]:
    grouped: dict[tuple[str, str], dict[str, Any]] = {}
    for issue in issues:
        key = (str(issue.get("rule_id", "")), str(issue.get("template") or page_template(str(issue.get("url", "")))))
        action = grouped.setdefault(
            key,
            {
                "rule_id": key[0],
                "template": key[1] or "site",
                "title": issue.get("title", ""),
                "severity": issue.get("severity", ""),
                "category": issue.get("category", ""),
                "priority": issue.get("priority", {}),
                "remediation_guidance": issue.get("remediation_guidance", ""),
                "count": 0,
                "urls": [],
            },
        )
        action["count"] += 1
        url = str(issue.get("url", ""))
        if url and url not in action["urls"] and len(action["urls"]) < MAX_GROUP_EVIDENCE_URLS:
            action["urls"].append(url)
    return list(grouped.values())


def _write_issue_queue(project_dir: Path, generated_at: datetime, actions: list[dict[str, Any]]) -> Path:
    path = state.safe_project_path(project_dir, f"{TECH_AUDIT_ROOT}/action-queue-{generated_at.strftime('%Y%m%dT%H%M%SZ')}.md")
    lines = ["# Technical SEO Action Queue", "", f"Generated: {generated_at.isoformat()}", "", "Unique fingerprints are grouped by rule and page template; priority combines technical severity, GSC page performance, historical click change, and a URL business heuristic.", ""]
    if not actions:
        lines.append("- none")
    for action in actions[:50]:
        priority = action.get("priority", {})
        lines.extend([f"- [{priority.get('tier', 'low')}/{priority.get('score', 0)}] {action.get('rule_id')} · {action.get('template')} ({action.get('count')} issue(s))", f"  - {action.get('title')}: {action.get('remediation_guidance')}"])
        if action.get("urls"):
            lines.append(f"  - Examples: {', '.join(action['urls'][:3])}")
    atomic_write_text(path, "\n".join(lines) + "\n")
    return path


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _timestamp(value: datetime | None = None) -> str:
    return (value or _now()).strftime("%Y%m%dT%H%M%S%fZ")


def _finalize_tech_audit_run(
    project_dir: Path,
    *,
    seed_url: str,
    config: CrawlConfig,
    crawl: dict[str, Any],
    pages: list[dict[str, Any]],
    generated_at: datetime,
    run_id: str,
    run_root: Path,
    status_path: Path,
    status: dict[str, Any],
    baseline_issues: list[dict[str, Any]],
    baseline_config_fingerprint: str = "",
    baseline_config_fingerprint_version: str = "",
    sitemap_records: list[dict[str, Any]] | None = None,
    sitemap_entries: list[dict[str, str]] | None = None,
    continuation_of: str | None = None,
    batch_number: int = 1,
    queue_recovered: bool = False,
) -> tuple[dict[str, Any], Path]:
    sitemap_records = sitemap_records if sitemap_records is not None else crawl["sitemap_records"]
    sitemap_entries = sitemap_entries if sitemap_entries is not None else crawl["sitemap_entries"]
    current_gsc, previous_gsc, gsc_meta = _gsc_page_metrics(project_dir)
    for page in pages:
        metric = current_gsc.get(normalize_url(page.get("url", ""))) or current_gsc.get(normalize_url(page.get("final_url", "")))
        previous = previous_gsc.get(normalize_url(page.get("url", ""))) or previous_gsc.get(normalize_url(page.get("final_url", "")))
        page["search_performance"] = {"status": "available" if metric else "not_found", **(metric or {}), "previous": previous or {}}
    issues = prioritize_issues(evaluate_rules(pages, sitemap_records, sitemap_entries, config), current_gsc, previous_gsc)
    issue_actions = _issue_action_groups(issues)
    previous_fingerprints = {item.get("fingerprint") for item in baseline_issues}
    new_high = [item for item in issues if item.get("fingerprint") not in previous_fingerprints and item.get("priority", {}).get("tier") in {"critical", "high"}]
    new_high_actions = _issue_action_groups(new_high)
    normalized_dir = run_root / "normalized"
    normalized_dir.mkdir(parents=True, exist_ok=True)
    _jsonl_write(normalized_dir / "inventory.jsonl", pages)
    link_inventory = _build_link_inventory(pages)
    _jsonl_write(normalized_dir / "link-inventory.jsonl", link_inventory)
    _jsonl_write(normalized_dir / "issues.jsonl", issues)
    _jsonl_write(normalized_dir / "action-groups.jsonl", issue_actions)
    _jsonl_write(normalized_dir / "sitemap-entries.jsonl", sitemap_entries)
    atomic_write_text(normalized_dir / "gsc-page-metrics.json", json.dumps(gsc_meta, ensure_ascii=False, indent=2) + "\n")
    queue_path = _write_issue_queue(project_dir, generated_at, new_high_actions)
    remaining_queue = crawl.get("remaining_queue", [])
    rate_limited = sum(page.get("crawl_status") == "rate_limited" for page in pages)
    blocked_by_waf = sum(page.get("crawl_status") == "blocked_by_waf" for page in pages)
    collection_status = "partial" if crawl["errors"] or crawl["stopped_by_limit"] else "ok"
    config_fingerprint = _semantic_config_fingerprint(config)
    fingerprint_matches = (
        bool(baseline_config_fingerprint)
        and baseline_config_fingerprint == config_fingerprint
        and baseline_config_fingerprint_version == CONFIG_FINGERPRINT_VERSION
    )
    issue_register, issue_register_path = sync_issue_register(
        project_dir,
        issues,
        baseline_issues,
        run_id=run_id,
        verification_allowed=collection_status == "ok" and fingerprint_matches,
        verification_provisional=collection_status != "ok" and fingerprint_matches,
        now=generated_at,
    )
    summary = {
        "pages": len(pages),
        "crawled_pages": len(pages),
        "discovered_unique": int(crawl.get("discovered_unique", len(pages) + len(remaining_queue))),
        "queued_remaining": len(remaining_queue),
        "continuation_available": bool(remaining_queue),
        "queue_recovered": queue_recovered,
        "crawl_batch": batch_number,
        "link_inventory": len(link_inventory),
        "successful_pages": sum(1 for page in pages if page.get("status_code") == 200),
        "issues": len(issues),
        "issue_actions": len(issue_actions),
        "new_high_impact": len(new_high),
        "new_high_impact_actions": len(new_high_actions),
        "sitemap_entries": len(sitemap_entries),
        "error_count": len(crawl["errors"]),
        "rate_limited": rate_limited,
        "blocked_by_waf": blocked_by_waf,
        "stopped_by_limit": crawl["stopped_by_limit"],
        "gsc_status": gsc_meta.get("status", "not_available"),
        "issue_register": issue_register,
    }
    atomic_write_text(run_root / "summary.json", json.dumps(summary, ensure_ascii=False, indent=2) + "\n")
    warnings: list[str] = []
    if crawl["stopped_by_limit"]:
        warnings.append("crawl stopped at max_urls; use Continue crawl to process the persisted queue")
    if queue_recovered:
        warnings.append("remaining queue was reconstructed from the previous snapshot because that run predates queue persistence")
    if rate_limited:
        warnings.append(f"{rate_limited} URLs were rate limited with HTTP 429; SEO issue results are incomplete")
    if blocked_by_waf:
        warnings.append(f"{blocked_by_waf} URLs were blocked by a WAF; SEO issue results are incomplete")
    artifacts = {
        "run_dir": _relative_path(project_dir, run_root),
        "summary_path": _relative_path(project_dir, run_root / "summary.json"),
        "inventory_path": _relative_path(project_dir, normalized_dir / "inventory.jsonl"),
        "link_inventory_path": _relative_path(project_dir, normalized_dir / "link-inventory.jsonl"),
        "issues_path": _relative_path(project_dir, normalized_dir / "issues.jsonl"),
        "action_groups_path": _relative_path(project_dir, normalized_dir / "action-groups.jsonl"),
        "sitemap_entries_path": _relative_path(project_dir, normalized_dir / "sitemap-entries.jsonl"),
        "gsc_metrics_path": _relative_path(project_dir, normalized_dir / "gsc-page-metrics.json"),
        "remaining_queue_path": _relative_path(project_dir, run_root / "normalized/remaining-queue.jsonl"),
        "action_queue_path": _relative_path(project_dir, queue_path),
        "issue_register_path": _relative_path(project_dir, issue_register_path),
    }
    snapshot = {
        "schema_version": SCHEMA_VERSION,
        "collector_version": COLLECTOR_VERSION,
        "kind": "tech-audit",
        "generated_at": generated_at.isoformat(),
        "collection_status": collection_status,
        "seed_url": seed_url,
        "run_id": run_id,
        "config": asdict(config),
        "config_fingerprint": config_fingerprint,
        "config_fingerprint_version": CONFIG_FINGERPRINT_VERSION,
        "summary": summary,
        "new_high_impact": [_issue_summary(issue) for issue in new_high],
        "new_high_impact_actions": new_high_actions,
        "artifacts": artifacts,
        "errors": crawl["errors"],
        "warnings": warnings,
    }
    if continuation_of:
        snapshot["continuation_of"] = continuation_of
    snapshot_path = state.safe_project_path(project_dir, f"{TECH_AUDIT_ROOT}/tech-audit-{run_id}.json")
    state.write_json(snapshot_path, snapshot)
    state.write_json(state.safe_project_path(project_dir, f"{TECH_AUDIT_ROOT}/latest.json"), snapshot)
    status.update({"status": collection_status, "finished_at": _now().isoformat(), "summary": summary, "snapshot_path": _relative_path(project_dir, snapshot_path)})
    atomic_write_text(status_path, json.dumps(status, ensure_ascii=False, indent=2) + "\n")
    prune_tech_audit_history(project_dir)
    return {**snapshot, "snapshot_path": str(snapshot_path), "action_queue_path": str(queue_path)}, snapshot_path


def run_tech_audit(project_dir: Path, config: CrawlConfig) -> tuple[dict[str, Any], Path]:
    seed_url = _validate_seed(str(state.load_state(project_dir).get("project", {}).get("url", "")), config.allow_private)
    crawler_access = _load_crawler_access(project_dir, seed_url)
    generated_at = _now()
    run_id = _timestamp(generated_at)
    audit_root = state.safe_project_path(project_dir, TECH_AUDIT_ROOT)
    run_root = state.safe_project_path(project_dir, f"{TECH_AUDIT_ROOT}/runs/{run_id}")
    run_root.mkdir(parents=True, exist_ok=True)
    status_path = run_root / "run.json"
    status = {"schema_version": SCHEMA_VERSION, "run_id": run_id, "kind": "tech-audit", "status": "running", "started_at": generated_at.isoformat(), "config": asdict(config)}
    atomic_write_text(status_path, json.dumps(status, ensure_ascii=False, indent=2) + "\n")
    baseline_path = audit_root / "latest.json"
    baseline_snapshot = state.read_json(baseline_path) if baseline_path.is_file() else {}
    baseline_issues = load_tech_issues(project_dir, baseline_path) if baseline_path.is_file() else []
    try:
        crawl = asyncio.run(_crawl(seed_url, config, run_root, status_path=status_path, run_status=status, crawler_access=crawler_access))
        pages = list(crawl["pages"].values())
        if config.rendered and config.render_limit and pages:
            candidates = [page["url"] for page in pages if page.get("status_code") == 200 and (not page.get("title") or not page.get("h1") or not page.get("outlinks"))][: config.render_limit]
            if seed_url not in candidates:
                candidates.insert(0, seed_url)
            try:
                from seo_workbench_tools.rendered_probe import capture

                rendered = capture(candidates[: config.render_limit], run_root / "rendered", timeout=config.timeout, wait_ms=config.render_wait_ms)
                for rendered_page in rendered.get("pages", []):
                    view = rendered_page.get("viewports", {}).get("desktop_1920x1080", {})
                    page = next((item for item in pages if item.get("url") == rendered_page.get("url")), None)
                    if not page or view.get("error"):
                        continue
                    page["rendered"] = {"profile": "desktop_1920x1080", "url": view.get("url", ""), "title": view.get("title", ""), "meta_description": view.get("meta_description", ""), "meta_keywords": view.get("meta_keywords", ""), "canonical": view.get("canonical", ""), "meta_robots": view.get("robots_meta", ""), "h1": view.get("h1", []), "h2": view.get("h2", [])}
                    for key in ("title", "meta_description", "meta_keywords", "canonical", "meta_robots", "h1", "h2"):
                        if page.get(key) in ("", [] ) and page["rendered"].get(key) not in ("", []):
                            page[key] = page["rendered"][key]
                status["rendered"] = {"status": "ok", "pages": len(rendered.get("pages", [])), "path": rendered.get("output_path", "")}
            except (ImportError, RuntimeError) as exc:
                crawl["errors"].append({"scope": "rendered", "error": str(exc)})
                status["rendered"] = {"status": "not_available", "error": str(exc)}
        return _finalize_tech_audit_run(
            project_dir,
            seed_url=seed_url,
            config=config,
            crawl=crawl,
            pages=pages,
            generated_at=generated_at,
            run_id=run_id,
            run_root=run_root,
            status_path=status_path,
            status=status,
            baseline_issues=baseline_issues,
            baseline_config_fingerprint=str(baseline_snapshot.get("config_fingerprint", "")),
            baseline_config_fingerprint_version=str(baseline_snapshot.get("config_fingerprint_version", "")),
        )
    except Exception as exc:
        status.update({"status": "failed", "finished_at": _now().isoformat(), "error": str(exc)})
        atomic_write_text(status_path, json.dumps(status, ensure_ascii=False, indent=2) + "\n")
        raise


def continue_tech_audit(project_dir: Path, config: CrawlConfig | None = None) -> tuple[dict[str, Any], Path]:
    latest_path = state.safe_project_path(project_dir, f"{TECH_AUDIT_ROOT}/latest.json")
    if not latest_path.is_file():
        raise ValueError("no technical audit snapshot is available to continue")
    snapshot = state.read_json(latest_path)
    queue, queue_recovered = load_remaining_crawl_queue(project_dir, latest_path)
    if not queue:
        raise ValueError("no remaining crawl queue; run a new full crawl to discover more URLs")
    stored = snapshot.get("config", {})
    if config is None:
        values = {field: stored[field] for field in CrawlConfig.__dataclass_fields__ if field in stored}
        values["sitemap_urls"] = tuple(values.get("sitemap_urls", ()))
        config = CrawlConfig(**values)
    old_pages = load_tech_inventory(project_dir, latest_path)
    known_urls = {normalize_url(str(page.get("url", ""))) for page in old_pages if normalize_url(str(page.get("url", "")))}
    queue = [item for item in queue if normalize_url(str(item.get("url", ""))) not in known_urls]
    if not queue:
        raise ValueError("remaining crawl queue contains no new URLs; run a new full crawl to discover more URLs")
    seed_url = _validate_seed(str(snapshot.get("seed_url") or state.load_state(project_dir).get("project", {}).get("url", "")), config.allow_private)
    crawler_access = _load_crawler_access(project_dir, seed_url)
    generated_at = _now()
    run_id = _timestamp(generated_at)
    run_root = state.safe_project_path(project_dir, f"{TECH_AUDIT_ROOT}/runs/{run_id}")
    run_root.mkdir(parents=True, exist_ok=True)
    status_path = run_root / "run.json"
    status = {"schema_version": SCHEMA_VERSION, "run_id": run_id, "kind": "tech-audit", "status": "running", "started_at": generated_at.isoformat(), "config": asdict(config), "continuation_of": snapshot.get("run_id"), "queue_recovered": queue_recovered}
    atomic_write_text(status_path, json.dumps(status, ensure_ascii=False, indent=2) + "\n")
    baseline_issues = load_tech_issues(project_dir, latest_path)
    try:
        crawl = asyncio.run(_crawl(seed_url, config, run_root, start_urls=[str(item["url"]) for item in queue], known_urls=known_urls, status_path=status_path, run_status=status, crawler_access=crawler_access))
        pages_by_url = {normalize_url(str(page.get("url", ""))): page for page in old_pages if normalize_url(str(page.get("url", "")))}
        pages_by_url.update({normalize_url(str(page.get("url", ""))): page for page in crawl["pages"].values() if normalize_url(str(page.get("url", "")))})
        crawl["pages"] = pages_by_url
        inlinks: dict[str, list[dict[str, str]]] = {}
        for source in pages_by_url.values():
            for link in source.get("outlinks", []):
                if link.get("host_relation") != "external":
                    inlinks.setdefault(str(link.get("url", "")), []).append({"source_url": source.get("url", ""), "anchor_text": link.get("anchor_text", ""), "rel": " ".join(link.get("rel", []))})
        for page in pages_by_url.values():
            page["inlinks"] = inlinks.get(page.get("url", ""), [])
            page["inlink_count"] = len(page["inlinks"])
        crawl["discovered_unique"] = len(pages_by_url) + len(crawl.get("remaining_queue", []))
        old_run_dir = state.safe_project_path(project_dir, str(snapshot.get("artifacts", {}).get("run_dir", ""))) if snapshot.get("artifacts", {}).get("run_dir") else None
        old_site = state.read_json(old_run_dir / "raw/site.json") if old_run_dir and (old_run_dir / "raw/site.json").is_file() else {}
        old_sitemap_records = old_site.get("sitemaps", []) if isinstance(old_site, dict) else []
        old_sitemap_entries = _jsonl_read(state.safe_project_path(project_dir, str(snapshot.get("artifacts", {}).get("sitemap_entries_path", "")))) if snapshot.get("artifacts", {}).get("sitemap_entries_path") else []
        sitemap_entries_by_url = {str(item.get("url", "")): item for item in [*old_sitemap_entries, *crawl.get("sitemap_entries", [])] if item.get("url")}
        crawl["sitemap_records"] = [*old_sitemap_records, *crawl.get("sitemap_records", [])]
        crawl["sitemap_entries"] = list(sitemap_entries_by_url.values())
        batch_number = int(snapshot.get("summary", {}).get("crawl_batch", 1) or 1) + 1
        return _finalize_tech_audit_run(
            project_dir,
            seed_url=seed_url,
            config=config,
            crawl=crawl,
            pages=list(pages_by_url.values()),
            generated_at=generated_at,
            run_id=run_id,
            run_root=run_root,
            status_path=status_path,
            status=status,
            baseline_issues=baseline_issues,
            baseline_config_fingerprint=str(snapshot.get("config_fingerprint", "")),
            baseline_config_fingerprint_version=str(snapshot.get("config_fingerprint_version", "")),
            continuation_of=str(snapshot.get("run_id", "")) or None,
            batch_number=batch_number,
            queue_recovered=queue_recovered,
        )
    except Exception as exc:
        status.update({"status": "failed", "finished_at": _now().isoformat(), "error": str(exc)})
        atomic_write_text(status_path, json.dumps(status, ensure_ascii=False, indent=2) + "\n")
        raise


def recrawl_urls(project_dir: Path, urls: Iterable[str], config: CrawlConfig | None = None) -> tuple[dict[str, Any], Path]:
    """Re-crawl a bounded set of pages already captured in the latest inventory."""
    inventory = load_tech_inventory(project_dir)
    crawlable = {
        normalize_url(str(page.get("url", ""))): page
        for page in inventory
        if page.get("host_relation", "same_host") in {"same_host", "subdomain"} and normalize_url(str(page.get("url", "")))
    }
    selected = list(dict.fromkeys(normalize_url(str(url)) for url in urls if normalize_url(str(url))))
    if not selected:
        raise ValueError("at least one URL is required")
    if len(selected) > 1_000:
        raise ValueError("recrawl supports at most 1000 URLs per run")
    unknown = [url for url in selected if url not in crawlable]
    if unknown:
        raise ValueError(f"only already-crawled internal or subdomain URLs may be re-crawled: {unknown[0]}")

    base_config = config or CrawlConfig(max_urls=len(selected), load_sitemap=False)
    crawl_config = replace(base_config, max_urls=len(selected), load_sitemap=False, rendered=False)
    seed_url = _validate_seed(str(state.load_state(project_dir).get("project", {}).get("url", "")), crawl_config.allow_private)
    crawler_access = _load_crawler_access(project_dir, seed_url)
    generated_at = _now()
    run_id = _timestamp(generated_at)
    audit_root = state.safe_project_path(project_dir, TECH_AUDIT_ROOT)
    run_root = state.safe_project_path(project_dir, f"{TECH_AUDIT_ROOT}/recrawls/{run_id}")
    run_root.mkdir(parents=True, exist_ok=True)
    status_path = run_root / "run.json"
    status = {"schema_version": SCHEMA_VERSION, "run_id": run_id, "kind": "tech-audit-recrawl", "status": "running", "started_at": generated_at.isoformat(), "target_urls": selected, "config": asdict(crawl_config)}
    atomic_write_text(status_path, json.dumps(status, ensure_ascii=False, indent=2) + "\n")
    try:
        crawl = asyncio.run(_crawl(seed_url, crawl_config, run_root, start_urls=selected, status_path=status_path, run_status=status, crawler_access=crawler_access))
        pages = list(crawl["pages"].values())
        current_gsc, previous_gsc, gsc_meta = _gsc_page_metrics(project_dir)
        for page in pages:
            metric = current_gsc.get(normalize_url(page.get("url", ""))) or current_gsc.get(normalize_url(page.get("final_url", "")))
            previous = previous_gsc.get(normalize_url(page.get("url", ""))) or previous_gsc.get(normalize_url(page.get("final_url", "")))
            page["search_performance"] = {"status": "available" if metric else "not_found", **(metric or {}), "previous": previous or {}}
        normalized_dir = run_root / "normalized"
        normalized_dir.mkdir(parents=True, exist_ok=True)
        _jsonl_write(normalized_dir / "inventory.jsonl", pages)
        link_inventory = _build_link_inventory(pages)
        _jsonl_write(normalized_dir / "link-inventory.jsonl", link_inventory)
        atomic_write_text(normalized_dir / "gsc-page-metrics.json", json.dumps(gsc_meta, ensure_ascii=False, indent=2) + "\n")
        collection_status = "partial" if crawl["errors"] else "ok"
        summary = {
            "targets": len(selected),
            "pages": len(pages),
            "successful_pages": sum(1 for page in pages if page.get("status_code") == 200),
            "still_404": sum(1 for page in pages if page.get("status_code") == 404),
            "rate_limited": sum(page.get("crawl_status") == "rate_limited" for page in pages),
            "blocked_by_waf": sum(page.get("crawl_status") == "blocked_by_waf" for page in pages),
            "error_count": len(crawl["errors"]),
        }
        atomic_write_text(run_root / "summary.json", json.dumps(summary, ensure_ascii=False, indent=2) + "\n")
        report = {
            "schema_version": SCHEMA_VERSION,
            "collector_version": COLLECTOR_VERSION,
            "kind": "tech-audit-recrawl",
            "generated_at": generated_at.isoformat(),
            "collection_status": collection_status,
            "seed_url": seed_url,
            "run_id": run_id,
            "target_urls": selected,
            "summary": summary,
            "pages": pages,
            "artifacts": {
                "run_dir": _relative_path(project_dir, run_root),
                "summary_path": _relative_path(project_dir, run_root / "summary.json"),
                "inventory_path": _relative_path(project_dir, normalized_dir / "inventory.jsonl"),
                "link_inventory_path": _relative_path(project_dir, normalized_dir / "link-inventory.jsonl"),
                "gsc_metrics_path": _relative_path(project_dir, normalized_dir / "gsc-page-metrics.json"),
            },
            "errors": crawl["errors"],
        }
        snapshot_path = audit_root / f"recrawl-{run_id}.json"
        state.write_json(snapshot_path, report)
        state.write_json(audit_root / "latest-recrawl.json", report)
        status.update({"status": collection_status, "finished_at": _now().isoformat(), "summary": summary, "snapshot_path": _relative_path(project_dir, snapshot_path)})
        atomic_write_text(status_path, json.dumps(status, ensure_ascii=False, indent=2) + "\n")
        return {**report, "snapshot_path": str(snapshot_path)}, snapshot_path
    except Exception as exc:
        status.update({"status": "failed", "finished_at": _now().isoformat(), "error": str(exc)})
        atomic_write_text(status_path, json.dumps(status, ensure_ascii=False, indent=2) + "\n")
        raise


def schedule_path(project_dir: Path) -> Path:
    return state.safe_project_path(project_dir, ".runtime/tech-audit/schedule.json")


def set_schedule(project_dir: Path, every_minutes: int, *, notify_role: str = "", profile: str = "") -> dict[str, Any]:
    if every_minutes < 1:
        raise ValueError("every_minutes must be at least 1")
    path = schedule_path(project_dir)
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {"schema_version": "tech-audit-schedule-v1", "enabled": True, "every_minutes": every_minutes, "notify_role": notify_role, "profile": profile, "updated_at": _now().isoformat(), "next_run_at": _now().isoformat()}
    atomic_write_text(path, json.dumps(payload, ensure_ascii=False, indent=2) + "\n", mode=0o600)
    return payload


def load_schedule(project_dir: Path) -> dict[str, Any]:
    path = schedule_path(project_dir)
    if not path.is_file():
        return {"enabled": False}
    try:
        return state.read_json(path)
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        raise ValueError(f"invalid technical audit schedule: {exc}") from exc


def disable_schedule(project_dir: Path) -> dict[str, Any]:
    payload = load_schedule(project_dir)
    payload.update({"enabled": False, "updated_at": _now().isoformat()})
    path = schedule_path(project_dir)
    path.parent.mkdir(parents=True, exist_ok=True)
    atomic_write_text(path, json.dumps(payload, ensure_ascii=False, indent=2) + "\n", mode=0o600)
    return payload


def mark_schedule_run(project_dir: Path, *, now: datetime | None = None) -> dict[str, Any]:
    payload = load_schedule(project_dir)
    current = now or _now()
    payload["last_run_at"] = current.isoformat()
    payload["next_run_at"] = (current + timedelta(minutes=int(payload.get("every_minutes", 1440)))).isoformat()
    path = schedule_path(project_dir)
    atomic_write_text(path, json.dumps(payload, ensure_ascii=False, indent=2) + "\n", mode=0o600)
    return payload


def schedule_due(payload: dict[str, Any], *, now: datetime | None = None) -> bool:
    if not payload.get("enabled"):
        return False
    value = str(payload.get("next_run_at", ""))
    if not value:
        return True
    try:
        next_run = datetime.fromisoformat(value.replace("Z", "+00:00"))
        if next_run.tzinfo is None:
            next_run = next_run.replace(tzinfo=timezone.utc)
    except ValueError:
        return True
    return next_run <= (now or _now())


def _self_test() -> None:
    assert normalize_url("HTTPS://Example.com/a/?utm_source=x#frag") == "https://example.com/a"
    assert link_scope("https://shop.example.com/a", "https://www.example.com/") == ("External", "subdomain")
    parsed = _parse_html('<title>T</title><meta name="keywords" content="a,b"><h1>One</h1><a href="/x" rel="nofollow"> X </a>', "https://example.com/")
    assert parsed["title"] == "T" and parsed["meta_keywords"] == "a,b" and parsed["outlinks"][0]["anchor_text"] == "X"


if __name__ == "__main__":
    _self_test()
