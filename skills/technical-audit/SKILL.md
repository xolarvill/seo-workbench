---
name: seo-technical
description: >
  Technical SEO audit across 9 categories: crawlability, indexability, security,
  URL structure, mobile, Core Web Vitals, structured data, JavaScript rendering,
  and IndexNow protocol. Use when user says "technical SEO", "crawl issues",
  "robots.txt", "Core Web Vitals", "site speed", or "security headers".
user-invokable: true
argument-hint: "[url]"
license: MIT
metadata:
  author: AgriciDaniel
  version: "1.9.6"
  category: seo
---

# Technical SEO Audit

## Categories

### 1. Crawlability
- robots.txt: exists, valid, not blocking important resources
- XML sitemap: exists, referenced in robots.txt, valid format
- Noindex tags: intentional vs accidental
- Crawl depth: important pages within 3 clicks of homepage
- JavaScript rendering: check if critical content requires JS execution
- Crawl budget: for large sites (>10k pages), efficiency matters

#### Non-search crawler management

Training, retrieval, assistant, archive, and search crawlers may use different tokens and policies. These change over time. Before recommending a rule, verify the operator's current official documentation and distinguish it from Google Search crawling. Treat `robots.txt` as a crawl preference, not authentication, copyright enforcement, or proof that content will disappear from an index.

### 2. Indexability
- Canonical tags: self-referencing, no conflicts with noindex
- Duplicate content: near-duplicates, parameter URLs, www vs non-www
- Low-value or duplicate pages: judge purpose, uniqueness, task completion, and index demand, not minimum word counts
- Pagination: sequential pages remain reachable with crawlable links; do not rely on `rel=next/prev` as an indexing signal
- Hreflang: correct for multi-language/multi-region sites
- Index bloat: unnecessary pages consuming crawl budget

### 3. Security
- HTTPS: enforced, valid SSL certificate, no mixed content
- Security headers:
  - Content-Security-Policy (CSP)
  - Strict-Transport-Security (HSTS)
  - X-Frame-Options
  - X-Content-Type-Options
  - Referrer-Policy
- HSTS preload: check preload list inclusion for high-security sites

### 4. URL Structure
- Clean URLs: descriptive, hyphenated, no query parameters for content
- Hierarchy: logical folder structure reflecting site architecture
- Redirects: no chains (max 1 hop), 301 for permanent moves
- URL complexity: flag unstable identifiers, duplicate parameters, excessive nesting, or operational limits; length alone is not an SEO defect
- Trailing slashes: consistent usage

### 5. Mobile Optimization
- Responsive design: viewport meta tag, responsive CSS
- Touch targets and spacing: test real mobile usability and Lighthouse accessibility findings; do not fail every control against one universal pixel rule
- Text readability: test viewport, zoom, contrast, wrapping, and representative devices; do not require one universal base font size
- No horizontal scroll
- Mobile-first indexing: compare mobile and desktop content, links, metadata, structured data, images, and final URLs. Use the rendered mobile profile and do not assume a desktop-only check represents Google Search.

### 6. Core Web Vitals
- **LCP** (Largest Contentful Paint): target <2.5s
- **INP** (Interaction to Next Paint): target <200ms
  - INP replaced FID on March 12, 2024. FID was fully removed from all Chrome tools (CrUX API, PageSpeed Insights, Lighthouse) on September 9, 2024. Do NOT reference FID anywhere.
- **CLS** (Cumulative Layout Shift): target <0.1
- Evaluation uses 75th percentile of real user data
- Use the local `crux` command for real-user field data when its API key is configured

### 7. Structured Data
- Detection: JSON-LD (preferred), Microdata, RDFa
- Validation against Google's supported types
- See schema skill for full analysis

### 8. JavaScript Rendering
- Check if content visible in initial HTML vs requires JS
- Identify client-side rendered (CSR) vs server-side rendered (SSR)
- Identify SPA frameworks (React, Vue, Angular) as architecture evidence, then test raw/rendered parity before calling them an indexing issue
- Verify dynamic rendering setup if applicable

#### JavaScript SEO: Canonical & Indexing Guidance (December 2025)

Google updated its JavaScript SEO documentation in December 2025 with critical clarifications:

1. **Canonical conflicts:** If a canonical tag in raw HTML differs from one injected by JavaScript, Google may use EITHER one. Ensure canonical tags are identical between server-rendered HTML and JS-rendered output.
2. **noindex with JavaScript:** If raw HTML contains `<meta name="robots" content="noindex">` but JavaScript removes it, Google MAY still honor the noindex from raw HTML. Serve correct robots directives in the initial HTML response.
3. **Non-200 status codes:** Google does NOT render JavaScript on pages returning non-200 HTTP status codes. Any content or meta tags injected via JS on error pages will be invisible to Googlebot.
4. **Structured data in JavaScript:** Product, Article, and other structured data injected via JS may face delayed processing. For time-sensitive structured data (especially e-commerce Product markup), include it in the initial server-rendered HTML.

**Best practice:** Serve critical SEO elements (canonical, meta robots, structured data, title, meta description) in the initial server-rendered HTML rather than relying on JavaScript injection.

### 9. IndexNow Protocol
- Check if site supports IndexNow for Bing, Yandex, Naver
- Supported by search engines other than Google
- Recommend implementation for faster indexing on non-Google engines

### Architecture and Technology Impact

- Read `audits/technology/latest.json` and its `architecture_analysis` together with raw, rendered, performance, and diff evidence.
- Group detected technology into delivery, commerce, frontend, acquisition/data, trust/compliance, and content layers.
- Explain the architecture as evidence-backed inferences, not as a list of brand names.
- Assess four SEO relationships: crawl/rendering parity, measured performance ownership, consent/analytics integrity, and commerce search-feature eligibility.
- Treat a detected technology as presence evidence only. Do not claim it is active on every template or caused a measured issue without network, rendering, or Lighthouse attribution.
- State the scan mode. Fast mode uses response headers, cookies, and raw HTML. Balanced mode adds scripts, robots, and DNS but can still miss runtime JavaScript, DOM, XHR, interaction-only, gated, or route-specific technologies.
- Treat fallback detections as evidence only when their explicit asset/runtime evidence is present. Read `tag_audit.evidence_quality`; “not detected during observation” is not a claim that a tag or platform is absent site-wide.
- Compare rendered `profile_navigation` and Lighthouse requested/final URL. A mobile viewport with a desktop user agent is not valid evidence for UA-specific mobile routing.
- When sitemap discovery is unavailable, use the bounded representative-route sample and inspect `route_sample_audit` for shared SPA shells and duplicate metadata; do not extrapolate it into a complete crawl.

## Output

### Technical Score: XX/100

The score is an internal prioritization aid, not a Google score or ranking-factor total. Evidence, severity, affected templates, and business impact take precedence.

### Category Breakdown
| Category | Status | Score |
|----------|--------|-------|
| Crawlability | pass/warn/fail | XX/100 |
| Indexability | pass/warn/fail | XX/100 |
| Security | pass/warn/fail | XX/100 |
| URL Structure | pass/warn/fail | XX/100 |
| Mobile | pass/warn/fail | XX/100 |
| Core Web Vitals | pass/warn/fail | XX/100 |
| Structured Data | pass/warn/fail | XX/100 |
| JS Rendering | pass/warn/fail | XX/100 |
| IndexNow | pass/warn/fail | XX/100 |

### Architecture Impact
- Architecture summary and layer map
- Evidence quality and scan limitations
- SEO impact by crawl/rendering, performance, analytics/consent, and commerce search features
- Verification actions that distinguish a stack inference from a confirmed defect

### Critical Issues (fix immediately)
### High Priority (fix within 1 week)
### Medium Priority (fix within 1 month)
### Low Priority (backlog)

## DataForSEO Integration (Optional)

Use the local raw/rendered collectors, technology detector, Lighthouse runner, CrUX, GSC, and immutable audit artifacts first. If DataForSEO tools are explicitly available, use them only as supplementary evidence and label their collection scope. Do not replace the Workbench baseline or diff identity with an external score.

## Google Evidence Integration (Optional)

- Run `./seo crux --json` for current CrUX field data and 40 weekly history periods. Read `audits/crux/latest.json`; keep its page/origin effective scope and form factor attached to every conclusion.
- Run `./seo gsc collect --json` after authentication and property binding. Read `audits/gsc/latest.json` for finalized Search Analytics, Sitemap status, and bounded URL Inspection evidence.
- Use `./seo evidence --crux --gsc --json` only when the user explicitly requests Google evidence or the project is configured for it. These integrations are not part of the default raw crawl.
- Treat `needs_config` and `needs_auth` as user handoffs. Continue the raw/rendered/technology/Lighthouse audit and state exactly which Google evidence is unavailable.
- Lighthouse is reproducible lab evidence, CrUX is aggregated real-user field evidence, and GSC is Google Search evidence. Do not combine them into a single score or claim that one disproves the others.
- CrUX `no_data` commonly means insufficient eligible Chrome traffic. Use Lighthouse as a lab diagnostic, not as fabricated field data.
- GSC URL Inspection reports only the version in Google's index, not a live crawl. Do not claim current live indexability from it alone.

## Error Handling

| Scenario | Action |
|----------|--------|
| URL unreachable | Report connection error with status code. Suggest verifying URL, checking DNS resolution, and confirming the site is publicly accessible. |
| robots.txt not found | Note that no robots.txt was detected at the root domain. Recommend creating one with appropriate directives. Continue audit on remaining categories. |
| HTTPS not configured | Flag as a critical issue. Report whether HTTP is served without redirect, mixed content exists, or SSL certificate is missing/expired. |
| Core Web Vitals data unavailable | Note that CrUX data is not available (common for low-traffic sites). Suggest using Lighthouse lab data as a proxy and recommend increasing traffic before re-testing. |
