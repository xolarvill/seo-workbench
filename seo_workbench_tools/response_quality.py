"""Separate response observations from evidence usable by SEO rules."""
from __future__ import annotations

import re
from typing import Any


def response_quality(
    status: int | None,
    content_type: str = "",
    *,
    body: bytes | None = None,
    headers: dict[str, str] | None = None,
    crawl_status: str = "",
) -> dict[str, Any]:
    headers = headers or {}
    sample = (body or b"")[:16_384].lower()
    challenge = (
        headers.get("cf-mitigated", "").lower() == "challenge"
        or (b"<title>just a moment" in sample and bool(re.search(rb"<script\b[^>]*>[^<]*window\._cf_chl_opt\s*=", sample)))
        or (b"<title>just a moment" in sample and b"/challenge-platform/" in sample)
        or sample.strip().startswith(b"local_rate_limited")
        or (status in {403, 503} and any(marker in sample for marker in (b"challenge-platform", b"bot detected", b"access denied")))
    )
    unavailable = {"rate_limited", "blocked_by_waf", "fetch_error", "parse_error", "blocked_by_robots"}
    reason = (
        "rate_limited" if status == 429 else
        "blocked_by_waf" if challenge else
        crawl_status if crawl_status in unavailable else
        "fetch_error" if status is None else ""
    )
    if reason:
        return {"status": "unavailable", "reason": reason, "http_eligible": False, "html_eligible": False}
    html = status == 200 and content_type.lower().startswith(("text/html", "application/xhtml"))
    if html and body is not None and not body.strip():
        return {"status": "unavailable", "reason": "empty_response", "http_eligible": True, "html_eligible": False}
    return {"status": "eligible" if html else "http_only", "reason": "", "http_eligible": True, "html_eligible": html}
