from __future__ import annotations

import re
from typing import Any
from urllib.parse import urlsplit


TECHNOLOGY_RULES = (
    ("Vue.js", (r"(?:^|[/._-])vue(?:-vendor|\.runtime|\.global|[._-])", r"\bdata-v-[0-9a-f]+"), ["JavaScript frameworks"]),
    ("React", (r"(?:^|[/._-])react(?:-vendor|\.production|[._-])",), ["JavaScript frameworks"]),
    ("Next.js", (r"/_next/static/", r"\b__next_data__\b"), ["Web frameworks"]),
    ("Nuxt", (r"/_nuxt/", r"\b__nuxt__\b"), ["Web frameworks"]),
    ("Angular", (r"\bng-version=", r"(?:^|[/._-])angular(?:-vendor|[._-])"), ["JavaScript frameworks"]),
    ("Swiper", (r"(?:^|[/._-])swiper(?:-vendor|\.bundle|[._-])",), ["JavaScript libraries"]),
    ("AOS", (r"(?:^|[/._-])aos(?:-vendor|[._-])",), ["JavaScript libraries"]),
    ("jQuery", (r"(?:^|[/._-])jquery(?:\.min|[._-])",), ["JavaScript libraries"]),
)

TAG_RULES = (
    ("Google Tag Manager", (r"googletagmanager\.com/gtm\.js", r"\bgtm-[a-z0-9]+\b")),
    ("Google Analytics", (r"googletagmanager\.com/gtag/js", r"google-analytics\.com/(?:g/collect|analytics\.js)", r"\bgtag\s*\(")),
    ("Google Ads", (r"googleadservices\.com", r"googlesyndication\.com", r"\baw-[a-z0-9]+\b")),
    ("Baidu Analytics", (r"hm\.baidu\.com/(?:hm\.js|hm\.gif)", r"\b_hmt\b")),
    ("Matomo Analytics", (r"matomo\.js", r"piwik\.js", r"\b_paq\b")),
)


def sanitize_evidence_url(raw: str) -> str:
    try:
        parsed = urlsplit(raw)
    except ValueError:
        return raw.split("?", 1)[0].split("#", 1)[0]
    if parsed.scheme not in {"http", "https"} or not parsed.hostname:
        return raw.split("?", 1)[0].split("#", 1)[0]
    host = parsed.hostname
    if ":" in host and not host.startswith("["):
        host = f"[{host}]"
    if parsed.port:
        host = f"{host}:{parsed.port}"
    return f"{parsed.scheme}://{host}{parsed.path or '/'}"


def _matches(patterns: tuple[str, ...], urls: list[str], html: str) -> list[str]:
    evidence = []
    for url in urls:
        if any(re.search(pattern, url, flags=re.IGNORECASE) for pattern in patterns):
            evidence.append(sanitize_evidence_url(url))
    if html and any(re.search(pattern, html, flags=re.IGNORECASE) for pattern in patterns):
        evidence.append("rendered_dom_or_inline_script")
    return sorted(set(evidence))


def detect_tags(asset_urls: list[str], html: str = "") -> list[dict[str, Any]]:
    safe_urls = [sanitize_evidence_url(str(url)) for url in asset_urls if url]
    detected = []
    for name, patterns in TAG_RULES:
        evidence = _matches(patterns, safe_urls, html)
        if evidence:
            detected.append({"name": name, "evidence": evidence})
    return detected


def detect_technologies(asset_urls: list[str], html: str = "") -> list[dict[str, Any]]:
    safe_urls = [sanitize_evidence_url(str(url)) for url in asset_urls if url]
    detected = []
    for name, patterns, categories in TECHNOLOGY_RULES:
        evidence = _matches(patterns, safe_urls, html)
        if evidence:
            detected.append(
                {
                    "name": name,
                    "version": "",
                    "confidence": 90,
                    "categories": categories,
                    "groups": ["Web development"],
                    "detection_source": "explicit_asset_or_runtime_fallback",
                    "evidence": evidence,
                }
            )
    for tag in detect_tags(safe_urls, html):
        detected.append(
            {
                "name": tag["name"],
                "version": "",
                "confidence": 90,
                "categories": ["Analytics" if "Analytics" in tag["name"] else "Advertising"],
                "groups": ["Marketing"],
                "detection_source": "explicit_asset_or_runtime_fallback",
                "evidence": tag["evidence"],
            }
        )
    return detected
