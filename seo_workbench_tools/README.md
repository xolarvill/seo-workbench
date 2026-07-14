# SEO Workbench Tools

Python 胶水工具层，用于给 TECHNICAL_AUDIT 阶段提供可复查的机器证据。

## 常用入口

按 `projects/default/state.json` 自动采集：

```bash
env UV_CACHE_DIR=.uv-cache uv run --frozen --python 3.11 python -m seo_workbench evidence
```

输出：

```text
projects/default/audits/raw/
```

## 单独调用

```bash
env UV_CACHE_DIR=.uv-cache uv run --python 3.11 python -m seo_workbench_tools.page_probe https://example.com/page
env UV_CACHE_DIR=.uv-cache uv run --python 3.11 python -m seo_workbench_tools.robots_sitemap_probe https://example.com
env UV_CACHE_DIR=.uv-cache uv run --python 3.11 python -m seo_workbench_tools.evidence_bundle https://example.com --page https://example.com/products/foo
env UV_CACHE_DIR=.uv-cache uv run --python 3.11 --extra rendered python -m seo_workbench_tools.rendered_probe https://example.com
env UV_CACHE_DIR=.uv-cache uv run --python 3.11 --extra rendered python -m seo_workbench evidence --rendered --json
```

## 证据内容

`evidence_bundle` 当前包含：

- 顶层：schema_version、collector_version、collection_status、manifest、errors、warnings、source_confidence
- 页面级：status、final_url、headers、security_headers_audit、page_type、title/meta/canonical、canonical_audit、robots_meta_audit、h1-h6、Open Graph/Twitter、content_audit、schema/schema_audit、images/image_stats、link_summary、resources
- 站点级：robots.txt、robots user-agent groups、AI crawler directives、sitemap URL、sitemap lastmod freshness、sitemap hreflang、sitemap sample URL audit
- 汇总级：hreflang_audit、resource_cache_audit、headless_audit
- 渲染级：viewport screenshots、above_fold、mobile touch targets、horizontal overflow、rendered images、fonts、resource timing、raw/rendered SEO diffs

Every written bundle is saved as a timestamped `evidence-*.json` file and mirrored to:

```text
projects/default/audits/raw/latest.json
```

`rendered_probe` 需要 Playwright 浏览器环境：

```bash
env UV_CACHE_DIR=.uv-cache uv run --python 3.11 --extra rendered playwright install chromium
```
