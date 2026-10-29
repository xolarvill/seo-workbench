---
name: backlinks
description: "Backlink profile analysis: referring domains, anchor text distribution, suspicious-link review, competitor gap analysis. Uses provider exports and the Workbench DataForSEO collectors. Use when user says backlinks, link profile, referring domains, anchor text, toxic links, link gap, link building, disavow, or backlink audit."
user-invokable: true
argument-hint: "<url>"
license: MIT
compatibility: "Workbench backlink import/status and paid DataForSEO collect/gap; other providers require supplied evidence or a verified connector."
metadata:
  author: AgriciDaniel
  version: "1.9.6"
  category: seo
---

# Backlink Profile Analysis

## Choose the available evidence

Start with existing project snapshots and `./seo --project example-store backlinks status --json`. Check provider, target domain, capture date, row limits and completeness before choosing a comparison. Read [Workbench operations](../seo/references/workbench-operations.md) for current execution boundaries.

Workbench supports importing a provider export and collecting paid DataForSEO snapshots or competitor intersections. Inspect command help before collection:

```bash
./seo backlinks import --help
./seo backlinks collect --help
./seo backlinks gap --help
```

Import accepts `--from-file`, `--source`, optional `--captured-at`, and `--complete`. Mark complete only when the export actually covers the requested provider scope. Paid collection requires `--confirm-paid`; use the user's existing spending authorization and bounded row limits. Other providers, including Moz, Bing and Common Crawl, require an actual supplied dataset or an available connector. See [source selection](../seo/references/free-backlink-sources.md).

## Analysis framework

Choose the sections needed for the request and supported by the input:

1. **Profile overview:** backlinks, referring domains, follow attributes, domain concentration and comparable snapshot trends. Preserve provider definitions; domain- and page-level counts describe different populations.
2. **Anchor distribution:** classify branded, URL, generic, exact-match, partial-match and other natural anchors. Examine concentrated or repeated commercial anchors in their source-page context; a percentage alone does not establish manipulation.
3. **Referring-domain quality:** inspect topic relevance, source-page purpose, editorial placement, geography where observed, and domain concentration. Keep provider rank/spam metrics labeled with provider and scale. TLD or country alone does not establish quality.
4. **Suspicious-link review:** investigate sitewide placements, link farms, paid patterns, irrelevant mass submissions and concentrated keyword anchors. Read [backlink quality](../seo/references/backlink-quality.md) for investigative patterns; apply project evidence rules to its source heuristics. Verify a representative source page before escalation. Do not invent authority/toxicity scores or auto-generate a disavow action.
5. **Linked destination pages:** identify link magnets, relevant destinations with little observed coverage, and linked URLs returning real errors. Check destination content and a relevant replacement before proposing a redirect.
6. **Competitor gaps:** compare source domains within comparable provider coverage. Separate sources shared with competitors, competitor-only observed sources, and target-only observed sources. Rank outreach candidates by topic fit, attainable placement and evidence quality. Missing from a partial export means unobserved.
7. **New/lost links:** only two complete same-provider snapshots can establish disappearance from that provider's coverage. An unavailable or JavaScript-dependent source page cannot prove link removal. Distinguish provider discovery dates from publication dates.

## Deliverable and checks

Report source scope, actual observations, prioritized opportunities and a short evidence gap for any requested section that could not be observed. Use source-level metrics rather than a synthetic weighted health score. For each actionable link, retain the source URL, destination URL, observed anchor/rel when available, capture date and reason for action.

Check summary counts against the underlying dataset, preserve provider differences, and separate a failed fetch from an absent link. A reciprocal relationship warrants contextual review rather than an automatic spam finding. Store project reports using the project's report naming convention; use the existing report workflow when a report artifact is requested.
