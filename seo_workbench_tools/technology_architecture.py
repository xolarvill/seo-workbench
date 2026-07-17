from __future__ import annotations

from collections import defaultdict
from typing import Any


LAYER_RULES = {
    "delivery": ("cdn", "hosting", "web server", "reverse proxy", "performance"),
    "commerce": ("ecommerce", "payment", "shopping cart", "buy now pay later"),
    "frontend": ("javascript", "ui framework", "css framework", "development", "web framework"),
    "acquisition_data": ("analytics", "advertising", "tag manager", "marketing automation", "personalisation"),
    "trust_compliance": ("reviews", "cookie compliance", "security", "authentication"),
    "content_metadata": ("cms", "seo", "miscellaneous", "rich text editor"),
}


def _technology_items(report: dict[str, Any]) -> list[dict[str, Any]]:
    unique: dict[str, dict[str, Any]] = {}
    for page in report.get("pages", []):
        for technology in page.get("technologies", []):
            name = str(technology.get("name", "")).strip()
            if name:
                unique.setdefault(name.casefold(), technology)
    return sorted(unique.values(), key=lambda item: str(item.get("name", "")).casefold())


def _layers(technologies: list[dict[str, Any]]) -> dict[str, list[str]]:
    grouped: dict[str, set[str]] = defaultdict(set)
    for technology in technologies:
        name = str(technology.get("name", ""))
        categories = [str(category).casefold() for category in technology.get("categories", [])]
        category_text = " | ".join(categories)
        matched = False
        for layer, needles in LAYER_RULES.items():
            if any(needle in category_text for needle in needles):
                grouped[layer].add(name)
                matched = True
        if not matched:
            grouped["other"].add(name)
    return {layer: sorted(names) for layer, names in grouped.items() if names}


def _performance_context(performance: dict[str, Any] | None) -> tuple[str, list[str]]:
    if not performance:
        return "unknown", []
    aggregate = performance.get("aggregate", {})
    score = aggregate.get("performance_score", {}).get("median")
    metrics = aggregate.get("metrics", {})
    evidence = []
    if score is not None:
        evidence.append(f"Lighthouse median performance score: {score}")
    lcp = metrics.get("largest-contentful-paint", {}).get("median")
    tbt = metrics.get("total-blocking-time", {}).get("median")
    if lcp is not None:
        evidence.append(f"Lighthouse median LCP: {round(float(lcp))} ms")
    if tbt is not None:
        evidence.append(f"Lighthouse median TBT: {round(float(tbt))} ms")
    if score is None:
        return "unknown", evidence
    if float(score) < 50:
        return "high", evidence
    if float(score) < 90:
        return "medium", evidence
    return "low", evidence


def analyze_architecture(
    report: dict[str, Any],
    *,
    performance: dict[str, Any] | None = None,
) -> dict[str, Any]:
    technologies = _technology_items(report)
    layers = _layers(technologies)
    names = {str(item.get("name", "")).casefold(): str(item.get("name", "")) for item in technologies}

    commerce = layers.get("commerce", [])
    frontend = layers.get("frontend", [])
    acquisition = layers.get("acquisition_data", [])
    delivery = layers.get("delivery", [])
    trust = layers.get("trust_compliance", [])
    platform = names.get("shopify", commerce[0] if commerce else "")
    cdn = names.get("cloudflare", delivery[0] if delivery else "")

    summary_parts = []
    if platform:
        summary_parts.append(f"{platform}-managed commerce")
    if cdn:
        summary_parts.append(f"edge delivery through {cdn}")
    if frontend:
        summary_parts.append(f"client enhancement using {', '.join(frontend[:5])}")
    if acquisition:
        summary_parts.append(f"{len(acquisition)} detected acquisition/data integrations")
    summary = "; ".join(summary_parts) or "Insufficient technology evidence to characterize the architecture."

    framework_names = {
        name
        for name in frontend
        if any(token in name.casefold() for token in ("react", "preact", "vue", "angular", "emotion", "goober"))
    }
    performance_risk, performance_evidence = _performance_context(performance)
    if performance_risk == "unknown" and technologies:
        integration_count = len(frontend) + len(acquisition)
        performance_risk = "high" if integration_count >= 10 else "medium" if integration_count >= 5 else "unknown"
        performance_evidence = [
            f"{len(frontend)} frontend and {len(acquisition)} acquisition/data technologies detected; validate with Lighthouse and field data"
        ]

    seo_impacts = [
        {
            "area": "crawl_and_rendering",
            "risk": "medium" if framework_names else "unknown",
            "conclusion": (
                "Multiple client frameworks or CSS-in-JS runtimes increase rendering complexity; the stack alone does not prove CSR or an indexing defect."
                if framework_names
                else "No framework evidence was detected; absence of a fingerprint is not evidence of server-rendered delivery."
            ),
            "evidence": sorted(framework_names) or frontend,
            "checks": ["compare raw and rendered title, canonical, robots, H1, body, links, and schema", "verify non-200 responses do not depend on JavaScript"],
        },
        {
            "area": "performance",
            "risk": performance_risk,
            "conclusion": (
                "Frontend and third-party architecture can materially affect LCP, INP/TBT, and crawl rendering cost; use measured evidence rather than technology count alone."
                if technologies or performance_evidence
                else "No measured performance or technology evidence is available; performance impact remains unknown."
            ),
            "evidence": performance_evidence,
            "checks": ["attribute transfer and main-thread time by owner", "remove, delay, or consent-gate non-essential integrations", "re-run comparable multi-run Lighthouse tests"],
        },
        {
            "area": "analytics_consent",
            "risk": "medium" if acquisition else "unknown",
            "conclusion": (
                "Detected analytics, advertising, or automation integrations require consent-order, duplicate-event, and data-quality validation."
                if acquisition
                else "No analytics or advertising integration was detected; runtime, consent-gated, and route-specific tags remain unverified."
            ),
            "evidence": acquisition + trust,
            "checks": ["verify tags do not fire before the applicable consent state", "deduplicate purchase and conversion events", "test consent behavior by region"],
        },
        {
            "area": "commerce_search_features",
            "risk": "medium" if commerce else "unknown",
            "conclusion": (
                "Detected commerce or payment integrations make product schema, regional availability, price, review provenance, and checkout continuity priority validation areas."
                if commerce
                else "No commerce or payment integration was detected; commerce search-feature eligibility remains unverified."
            ),
            "evidence": commerce,
            "checks": ["validate Product and Merchant listings markup against visible regional content", "verify review markup ownership and eligibility", "keep crawlable product facts outside payment widgets"],
        },
    ]

    inputs = sorted(
        {
            signal
            for page in report.get("pages", [])
            for signal in page.get("fingerprint_inputs", [])
        }
    )
    full_runtime = any(signal in inputs for signal in ("runtime_javascript", "rendered_dom", "network_requests"))
    return {
        "summary": summary,
        "layers": layers,
        "seo_impacts": seo_impacts,
        "evidence_quality": {
            "scan_mode": report.get("scan_mode", "fast"),
            "fingerprint_inputs": inputs,
            "runtime_browser_signals": full_runtime,
            "limitation": (
                "Technology fingerprints indicate presence, not whether a component is active on every template or whether it caused a measured SEO issue."
                if full_runtime
                else (
                    "Balanced detection adds script, robots, and DNS signals but can still miss runtime JavaScript, DOM, XHR, and interaction-only technologies."
                    if report.get("scan_mode") == "balanced"
                    else "Fast detection uses response headers, cookies, and raw HTML; it can miss runtime JavaScript, DOM, XHR, and interaction-only technologies."
                )
            ),
        },
    }
