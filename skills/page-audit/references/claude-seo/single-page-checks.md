---
name: seo-page
description: >
  Analyze one supplied URL across on-page elements, content quality, technical
  metadata, schema, images and performance evidence. Use for a requested
  single-page SEO review, not every supplied URL or content-only wording task.
user-invokable: true
argument-hint: "[url]"
license: MIT
metadata:
  author: AgriciDaniel
  version: "1.9.6"
  category: seo
---

## Workbench reference context

Preserved source method for [page-audit](../../SKILL.md). Read relevant sections for the current question; the canonical entrypoint governs scope and Workbench execution. Original slash commands, agent names and scripts describe the source environment.

# Single Page Analysis

## What to Analyze

### On-Page SEO
- Title tag: accurately identifies the page's topic and offer, with useful distinction from other pages; character counts and truncation are diagnostics, not pass/fail quotas
- Meta description: summarizes supported page-specific value. Check whether it merely repeats the title and adds a generic CTA; propose the missing useful detail rather than treating phrase overlap as automatic failure. See [metadata writing](../metadata-writing.md).
- H1: exactly one, matches page intent, includes keyword
- H2-H6: logical hierarchy (no skipped levels), descriptive
- URL: short, descriptive, hyphenated, no parameters
- Internal links: useful destinations and descriptive anchors; confirm an orphan claim only with sufficient eligible same-site coverage
- External links: to authoritative sources, reasonable count

### Content Quality
- Coverage of the reader's task; do not infer thinness from word count alone
- Readability in the page's actual language and audience; scores are optional diagnostics, not quality verdicts
- Topic wording and relevant entities used naturally, with no density or variation quota; inspect unnatural repetition in context
- E-E-A-T: evidence quality, accurate claims and appropriate responsibility/attribution. A personal byline is useful where expected, not mandatory for every brand or service page; identity cannot substitute for useful content
- Content freshness: publication date, last updated date

### Technical Elements
- Canonical tag: present, self-referencing or correct
- Meta robots: index/follow unless intentionally blocked
- Open Graph: og:title, og:description, og:image, og:url
- Twitter Card: twitter:card, twitter:title, twitter:description
- Hreflang: if multi-language, correct implementation

### Schema Markup
- Detect all types (JSON-LD preferred)
- Validate required properties
- Identify missing opportunities
- Follow the canonical [schema skill](../../../schema/SKILL.md) for current type-specific eligibility and rich-result rules; do not infer eligibility from this historical checklist

### Images
- Alt text: describes the subject, context or function as needed; decorative alternatives may be empty, with no keyword quota
- File size: flag >200KB (warning), >500KB (critical)
- Format: recommend WebP/AVIF over JPEG/PNG
- Dimensions: width/height set for CLS prevention
- Lazy loading: inspect native and JavaScript implementations. Missing `loading="lazy"` alone is not a failure; raw `data-src`/lazysizes clues do not prove successful runtime loading. Current raw `without_lazy_loading` and rendered native counts cannot classify JS behavior. Use [images](../../../images/SKILL.md) and targeted DOM/network observation when necessary; otherwise mark behavior unconfirmed

### Core Web Vitals (reference only, not measurable from HTML alone)
- Flag potential LCP issues (huge hero images, render-blocking resources)
- Flag potential INP issues (heavy JS, no async/defer)
- Flag potential CLS issues (missing image dimensions, injected content)

These are diagnostic hypotheses. Performance verdicts require CrUX field evidence under current Workbench rules; lab or crawler observations cannot establish a performance problem. Apply local response-evidence eligibility rules before reporting missing metadata, image attributes or content; unavailable/challenge HTML cannot prove absence.

## Output

### Page Score Card

The historical scorecard below is optional. Do not run or invent a default scorer. If a score is explicitly requested, disclose its heuristic method and evidence coverage; unknown inputs stay unknown and the score is not a Google metric.
```
Overall Score: XX/100

On-Page SEO:     XX/100  ████████░░
Content Quality: XX/100  ██████████
Technical:       XX/100  ███████░░░
Schema:          XX/100  █████░░░░░
Images:          XX/100  ████████░░
```

### Issues Found
Organized by priority: Critical -> High -> Medium -> Low

### Recommendations
Specific, actionable improvements with expected impact

### Schema Suggestions
Ready-to-use JSON-LD code for detected opportunities

## DataForSEO Integration (Optional)

If DataForSEO MCP tools are available, use `serp_organic_live_advanced` for real SERP positions and `backlinks_summary` for backlink data and spam scores.

## Error Handling

| Scenario | Action |
|----------|--------|
| URL unreachable (DNS failure, connection refused) | Report the error clearly. Do not guess page content. Suggest the user verify the URL and try again. |
| Page requires authentication (401/403) | Report that the page is behind authentication. Suggest the user provide the rendered HTML directly or a publicly accessible URL. |
| JavaScript-rendered content (empty body in HTML) | Note that key content may be rendered client-side. Analyze the available HTML and flag that results may be incomplete. Suggest using a browser-rendered snapshot if available. |
