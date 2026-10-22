"""Rule-specific issue identities. Observations never define operator identity."""
from __future__ import annotations

import hashlib
import json
from typing import Any

IDENTITY_VERSION = "technical-identity-v2"
# Empty tuples deliberately mean one issue per rule/source URL. Changing group
# members, timings, sizes, status variants, or declarations remain observations.
IDENTITY_FIELDS = {
    **{rule: () for rule in (
        "HTTP_4XX", "HTTP_5XX", "BROKEN_INTERNAL_LINK", "REDIRECT_CHAIN", "REDIRECT_LOOP",
        "MISSING_TITLE", "DUPLICATE_TITLE", "MISSING_META_DESCRIPTION", "DUPLICATE_META_DESCRIPTION",
        "MISSING_H1", "MULTIPLE_H1", "MISSING_CANONICAL", "CANONICAL_CONFLICT",
        "ACCIDENTAL_NOINDEX", "BLOCKED_BY_ROBOTS", "SITEMAP_NOINDEX", "CRAWLED_NOT_IN_SITEMAP",
        "ORPHAN_CANDIDATE", "HIGH_CRAWL_DEPTH", "NO_INTERNAL_INLINKS", "SLOW_RESPONSE", "LARGE_HTML",
        "DUPLICATE_CONTENT_HASH",
    )},
    "CANONICAL_TO_NON_200": ("declared_canonical",),
    "CROSS_DOMAIN_CANONICAL": ("canonical",),
    "SITEMAP_NON_200": ("sitemap_url",),
    "SITEMAP_NOT_CRAWLED": ("url",),
    "HREFLANG_INVALID_CODE": ("hreflang", "href"),
    "HREFLANG_MISSING_RETURN_LINK": ("target_url",),
    "HREFLANG_TO_NON_200": ("href",),
    "HTTP_HTTPS_MIX": ("target_url",),
    "WWW_NON_WWW_MIX": ("target_host",),
}
URL_FIELDS = {"declared_canonical", "canonical", "sitemap_url", "url", "href", "target_url"}
# A bounded page recheck cannot establish graph, group, sitemap, target-page,
# intent, or rendered completeness. Those rules need later comparable audits.
LOCAL_CONFIRM_RULES = {
    "HTTP_4XX", "HTTP_5XX", "MISSING_TITLE", "MISSING_META_DESCRIPTION", "MISSING_H1",
    "MULTIPLE_H1", "MISSING_CANONICAL", "CROSS_DOMAIN_CANONICAL", "HREFLANG_INVALID_CODE",
    "SLOW_RESPONSE", "LARGE_HTML", "HTTP_HTTPS_MIX", "WWW_NON_WWW_MIX",
}


def issue_identity(issue: dict[str, Any]) -> dict[str, Any] | None:
    from seo_workbench.tech_audit import normalize_url
    rule = str(issue.get("rule_id", ""))
    if rule not in IDENTITY_FIELDS:
        return None
    evidence = issue.get("evidence") or {}
    url = normalize_url(str(issue.get("url", "")))
    if not url and rule not in {"SITEMAP_NON_200", "SITEMAP_NOT_CRAWLED"}:
        return None
    identity: dict[str, Any] = {"version": IDENTITY_VERSION, "rule_id": rule, "url": url}
    for field in IDENTITY_FIELDS[rule]:
        value = str(evidence.get(field, ""))
        if field in URL_FIELDS:
            normalized = normalize_url(value, url)
            value = normalized if normalized or rule != "HREFLANG_INVALID_CODE" else value.strip()
        elif field in {"target_host", "hreflang"}:
            value = value.lower().strip()
        if not value and rule != "HREFLANG_INVALID_CODE":
            return None
        identity[field] = value
    return identity


def identity_fingerprint(identity: dict[str, Any]) -> str:
    return hashlib.sha256(json.dumps(identity, sort_keys=True, ensure_ascii=False).encode()).hexdigest()
