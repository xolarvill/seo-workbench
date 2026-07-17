---
name: headless-precheck
description: Use for Shopify Headless raw HTML prechecks before technical audit. Runs local evidence collection, then writes a concise risk report from the JSON bundle.
---

# Headless Precheck

Run machine evidence first:

```bash
./seo evidence
```

For raw/rendered comparison, run:

```bash
./seo evidence --rendered
```

Read `audits/raw/latest.json`. It mirrors the timestamped evidence bundle and includes `manifest.path`.

Check:

- raw HTML title, meta description, canonical, robots meta, H1
- JSON-LD presence and parse errors
- image alt and dimension stats
- robots.txt and sitemap discovery
- hreflang consistency if present
- static resource cache headers
- whether body text appears in raw HTML
- `headless_audit.critical`, `headless_audit.warnings`, and per-page raw/rendered diffs when rendered evidence exists
- raw/rendered mismatches for title, meta description, canonical, robots meta, H1, JSON-LD types/count, links, and images

Write:

```text
audits/headless-precheck.md
```

Include critical findings first, then warnings, then the evidence JSON path from `manifest.path`.
