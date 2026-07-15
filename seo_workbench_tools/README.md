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
env UV_CACHE_DIR=.uv-cache uv run --frozen --python 3.11 python -m seo_workbench technology --json
env UV_CACHE_DIR=.uv-cache uv run --frozen --python 3.11 python -m seo_workbench evidence --technology --json
env UV_CACHE_DIR=.uv-cache uv run --frozen --python 3.11 python -m seo_workbench performance --json
env UV_CACHE_DIR=.uv-cache uv run --frozen --python 3.11 python -m seo_workbench evidence --performance --json
env UV_CACHE_DIR=.uv-cache uv run --frozen --python 3.11 python -m seo_workbench --project example-store audit-diff --json
```

## 证据内容

`evidence_bundle` 当前包含：

- 顶层：schema_version、collector_version、collection_status、manifest、errors、warnings、source_confidence
- 页面级：status、final_url、headers、security_headers_audit、page_type、title/meta/canonical、canonical_audit、robots_meta_audit、h1-h6、Open Graph/Twitter、content_audit、schema/schema_audit、images/image_stats、link_summary、resources
- 站点级：robots.txt、robots user-agent groups、AI crawler directives、sitemap URL、sitemap lastmod freshness、sitemap hreflang、sitemap sample URL audit
- 汇总级：hreflang_audit、resource_cache_audit、headless_audit
- 渲染级：viewport screenshots、above_fold、mobile touch targets、horizontal overflow、rendered images、fonts、resource timing、raw/rendered SEO diffs
- 技术栈：Wappalyzer headers/cookies/raw-HTML fingerprints、technology categories、version、description、CPE、provider version
- 性能：Lighthouse performance score、FCP、LCP、Speed Index、TBT、CLS、TTI、benchmark index、跨运行波动与代表结果

Every written bundle is saved as a timestamped `evidence-*.json` file and mirrored to:

```text
projects/default/audits/raw/latest.json
```

`rendered_probe` 需要 Playwright 浏览器环境：

```bash
env UV_CACHE_DIR=.uv-cache uv run --python 3.11 --extra rendered playwright install chromium
```

`technology_probe` 需要 Go 1.25+，指纹依赖固定在 `seo_workbench_tools/technology_detector/go.mod` 和 `go.sum`：

```bash
go version
env UV_CACHE_DIR=.uv-cache uv run --frozen --python 3.11 python -m seo_workbench_tools.technology_probe https://example.com --print
```

如需使用预编译 helper，可设置 `SEO_WORKBENCH_TECH_DETECTOR=/absolute/path/to/binary`。

探针默认拒绝本机、私网和 link-local 地址；只对明确可信的开发或内网站点使用 `technology --allow-private`。报告中的 `fingerprint_inputs` 表示该页面送入指纹引擎的信号类型，不代表每项技术分别命中了哪一种信号。

`performance_probe` 使用 `package-lock.json` 固定的 Lighthouse，并复用 setup 解析到的系统 Chrome 或项目 Chromium。默认 5 次顺序运行，最多 9 次；不要在同一机器上并发运行多个性能任务：

```bash
env UV_CACHE_DIR=.uv-cache uv run --frozen --python 3.11 python -m seo_workbench_tools.performance_probe https://example.com --runs 5
```

完整 LHR 与 HTML 保存在 `projects/default/audits/performance/performance-*/`，稳定指针是 `projects/default/audits/performance/latest.json`。
默认情况下，所有 Chrome 请求都通过本地 `network_boundary` 代理逐连接验证 DNS/IP；报告写盘前会脱敏 URL userinfo 和 token、secret、signature 等敏感查询值。`--allow-private` 会放开该网络边界，只能用于可信目标。

`audit-diff` 自动比较当前项目最近两份 raw、technology 和 performance 不可变记录。结果保存到 `projects/<id>/audits/diffs/`；缺少第二份记录时会返回 `no_baseline`，不会伪造变化结论。
