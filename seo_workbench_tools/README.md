# SEO Workbench Tools

Python 胶水工具层，用于给 TECHNICAL_AUDIT 阶段提供可复查的机器证据。

## 常用入口

按 `seo-workbench/state.json` 自动采集：

```bash
env UV_CACHE_DIR=.uv-cache uv run --python 3.11 python -m seo_workbench_tools.workflow_evidence
```

输出：

```text
seo-workbench/audits/raw/
```

## 单独调用

```bash
env UV_CACHE_DIR=.uv-cache uv run --python 3.11 python -m seo_workbench_tools.page_probe https://example.com/page
env UV_CACHE_DIR=.uv-cache uv run --python 3.11 python -m seo_workbench_tools.robots_sitemap_probe https://example.com
env UV_CACHE_DIR=.uv-cache uv run --python 3.11 python -m seo_workbench_tools.evidence_bundle https://example.com --page https://example.com/products/foo
```

当前只采集 raw HTML、robots.txt 和 sitemap。需要渲染后 DOM 证据时再加 Playwright。
