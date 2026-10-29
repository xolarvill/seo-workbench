---
name: seo-google
description: >
  Use Google Search Console, CrUX and GA4 evidence for search performance,
  indexed-version inspection, field Core Web Vitals and organic traffic analysis.
  Routes collection through installed Workbench commands and identifies when an
  optional Google API needs a verified connector or supplied input.
user-invokable: true
argument-hint: "[command] [url|property]"
license: MIT
metadata:
  author: AgriciDaniel
  version: "1.9.6"
  category: seo
---

# Google SEO evidence

## Current execution

Use the project-bound interfaces below. Read [authentication and binding](references/auth-setup.md) for setup and [Workbench operations](../seo/references/workbench-operations.md) for shared collection/report behavior. Existing artifacts may already answer the question.

| Need | Installed Workbench operation |
|---|---|
| Production search/business comparison | `./seo --project example-store statistics collect --json` |
| Finalized search comparison | `./seo --project example-store gsc performance --days 28 --compare --json` |
| Indexed-version URL inspection | `./seo --project example-store gsc inspect --url https://example.com/ --json` |
| Submitted sitemap status | `./seo --project example-store gsc sitemaps --json` |
| Composite GSC evidence | `./seo --project example-store gsc collect --json` |
| Current/history field CWV | `./seo --project example-store crux --json` |
| Lighthouse diagnostics | `./seo --project example-store performance --json` |
| Standalone GA4 aggregates | `./seo --project example-store ga4 collect --json` |

Read command-specific help to set an exact window or collection scope. Run network collection when it is needed for the authorized task; the table is an interface map rather than a fixed sequence.

## Interpret the sources

**CrUX and Lighthouse:** Keep field and lab evidence separate. CrUX defaults to aggregate, mobile and desktop records with 40 history periods, preserving URL-to-origin fallback and `no_data`. Compare effective scope and form factor before interpreting trends. CrUX supplies performance verdicts; Lighthouse helps identify resource, rendering and third-party diagnostics. A missing field record does not become a lab-derived field verdict. See [API concepts](references/pagespeed-crux-api.md) for source background; current collector contracts govern execution.

**Search Console:** Use finalized query/page data for clicks, impressions, CTR and position, with the exact date range and exposed population. Query opportunities such as high-impression pages or queries near the first page require intent and landing-page ownership review. URL Inspection describes Google's indexed version; it is not a live page test. Sitemap status is a separate observation. See [Search Console concepts](references/search-console-api.md).

**GA4:** Preserve property, date range, channel grouping and metric definitions. Standalone GA4 defaults to two complete processing days before today. Production comparisons use `statistics collect` to align GA4 and Shopify with the finalized GSC end date. Standard commerce funnel coverage is checked across channels; zero organic purchases alone cannot establish broken tracking. See [GA4 concepts](references/ga4-data-api.md).

## Optional Google API inputs

YouTube, NLP/entity extraction, Keyword Planner, Knowledge Graph and Web Risk methods require a verified available connector or supplied API/export output. They are not registered Workbench subcommands. Inspect connector schemas, identity, pricing/quota and actual capability before choosing a call. Useful source references are [YouTube](references/youtube-api.md), [NLP](references/nlp-api.md), [Keyword Planner](references/keyword-planner-api.md) and [supplementary APIs](references/supplementary-apis.md).

Use video results to examine topic/format coverage, NLP output as an attributed machine interpretation, and Keyword Planner data with its market/language/time settings. Entity extraction alone does not establish expertise or factual accuracy. Preserve model/index and scope with any supplied metrics.

Indexing submission is a separate write workflow. GSC inspection and sitemap reads do not submit URLs. For a requested indexing action, inspect the existing content indexing workflow and the platform's current eligibility before proposing an operation; [Indexing API background](references/indexing-api.md) does not install a submission executor or grant permission.

## Deliverable and failures

Attach exact property, requested/effective URL, dates, collection status and evidence pointers to findings. Save reports under the current project's report convention. Presentation generation uses the existing reports command and readiness gate.

Handle `needs_auth` or `needs_config` through the local setup flow. Preserve successful components of partial collection. For quotas/rate limits use collector retry behavior; avoid repeated broad collection. A provider's unavailable dataset, absent property permission or failed request remains distinct from a measured zero.
