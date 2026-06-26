---
name: headless-precheck
description: Use for Shopify Headless raw HTML prechecks before technical audit. Runs local evidence collection, then writes a concise risk report from the JSON bundle.
---

# Headless Precheck

Run machine evidence first:

```bash
env UV_CACHE_DIR=.uv-cache uv run --frozen --python 3.11 python -m seo_workbench evidence
```

Read the newest JSON under `audits/raw/`.

Check:

- raw HTML title, meta description, canonical, robots meta, H1
- JSON-LD presence and parse errors
- image alt and dimension stats
- robots.txt and sitemap discovery
- hreflang consistency if present
- static resource cache headers
- whether body text appears in raw HTML

Write:

```text
audits/headless-precheck.md
```

Include critical findings first, then warnings, then the evidence JSON path.
