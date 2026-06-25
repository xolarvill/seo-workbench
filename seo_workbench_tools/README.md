# SEO Workbench Tools

Run with the project uv environment:

```bash
env UV_CACHE_DIR=.uv-cache uv run --python 3.11 python -m seo_workbench_tools.evidence_bundle https://example.com
```

Use `evidence_bundle` before technical audit steps. It writes JSON evidence to:

```text
seo-workbench/audits/raw/
```

Available probes:

```bash
python -m seo_workbench_tools.page_probe https://example.com/page
python -m seo_workbench_tools.robots_sitemap_probe https://example.com
python -m seo_workbench_tools.evidence_bundle https://example.com --page https://example.com/products/foo
python -m seo_workbench_tools.workflow_evidence
```

Skipped: rendered DOM checks. Add Playwright only when raw HTML evidence cannot answer a Headless SEO question.
