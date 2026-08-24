# Technical SEO Audit

`tech-audit` 是项目级、确定性的 Screaming Frog 风格技术审计闭环。它面向中小型站点，不替代通用爬虫，也不把所有页面强制交给浏览器。

## 闭环

```text
抓取站点 -> URL inventory -> 技术规则 -> 可追溯快照 -> GSC 页面流量
       -> audit-diff -> priority -> action queue -> 定时/飞书通知
```

CLI 是唯一 source of truth，所有命令都支持 `--json`。后台的 Technical audit 页面只调用同一组 project-scoped action，不复制抓取或规则判断。

## 命令

```bash
# 默认普通 HTTP 抓取，最多 1000 个 URL
./seo --project example-store tech-audit run --json

# 继续处理上一批次保存的剩余队列；每批最多仍为 1000 个 URL
./seo --project example-store tech-audit continue --json

# 启用同站子域名抓取；外部链接仍进入 link inventory，但不抓取
./seo --project example-store tech-audit run --include-subdomains --json

# 对疑似 CSR/空壳页面抽样做 Playwright 渲染，最多 5 个页面
./seo --project example-store tech-audit run --rendered --render-limit 5 --json

# 先刷新只读 GSC，再做技术审计
./seo --project example-store tech-audit run --refresh-gsc --json

# 比较最近两个技术审计快照
./seo --project example-store tech-audit diff --json
# 或纳入现有多证据 diff
./seo --project example-store audit-diff --kind tech-audit --json

./seo --project example-store tech-audit rules --json
./seo --project example-store tech-audit status --json

# 查看问题责任与处理状态；verified 只能由可比的后续完整审计写入
./seo --project example-store tech-audit issues list --status open --json
./seo --project example-store tech-audit issues status <fingerprint> planned --owner seo --note "scheduled" --json
./seo --project example-store tech-audit issues status <fingerprint> fixed --owner seo --note "deployed" --json

# 限定在最新 inventory 中已抓取的 same-host/subdomain 页面，可单个或批量重爬
./seo --project example-store tech-audit recrawl \
  --url https://example.com/missing-a --url https://example.com/missing-b --json
```

`--include-subdomains` 将同一根域名的子域列为 `host_relation=subdomain` 并允许抓取；否则它们仍作为 `internal_external=External` 出现在 link inventory 中。外部链接永远不会被默认抓取。

默认 HTTP 请求使用可配置的 Chrome-like User-Agent、Accept、Accept-Language、缓存和升级请求头；默认并发为 2、请求间隔为 1 秒、失败退避为 1 秒。可针对站点 WAF 进一步放慢：

```bash
./seo --project example-store tech-audit run --concurrency 1 --delay 2 --json
```

收到 `Retry-After` 时会遵守服务端给出的秒数或 HTTP 日期。HTTP 429 会记录为 `crawl_status=rate_limited`，带有 Cloudflare/CloudFront/Akamai 或挑战证据的 403/503 会记录为 `blocked_by_waf`；这些响应保留在原始证据和 URL inventory 中，但不会被当成真实 404/普通 HTTP 4xx，也不会生成页面 metadata 缺失问题。真实 404 仍然生成 `HTTP_4XX` 和 broken-link 规则命中。浏览器请求头不能替代 Cookie、JavaScript challenge、站点 allowlist 或 Shopify web-bot authentication；遇到持续拦截时，应优先配置站点侧放行，再提高并发。

HTML title 取文档中第一个 `<title>`；页脚支付图标等内嵌 SVG 的 `<title>` 只作为图形可访问名称，不会覆盖页面标题。

## Technical audit viewer

UI 的 Technical audit 页面默认读取 `latest.json` 指向的最新完整 crawl snapshot，包含三个服务端分页数据集：

Technical audit UI 分为 Summary、Schedule 和 URL inventory 三个独立子 tab；Issues 保留在 URL inventory 查看器内部，不再重复占用侧边栏层级。

- `pages`：URL Inventory，展示 URL、Internal/External、状态码、indexability、title、description、keywords、H1/H2、深度、inlinks/outlinks、响应指标，并可选择更多技术字段。
- `links`：Link Inventory，默认只展示主域和已启用子域（Site family），展示 host relation、是否已抓取、状态、final URL、来源、anchor text、rel 和 excluded reason。选择 External 或 All hosts 后可查看外链；External 只读，不触发请求。
- `issues`：Issues，展示规则命中、severity、category、URL、priority、GSC 指标、历史点击变化和 remediation。
- `issues` 同时展示 workflow status、owner 和 verification status。人工可设 `open`、`planned`、`fixed`、`accepted`；`accepted` 必须记录决策说明，人工不能直接设为 `verified`。

查询 API：

```text
GET /api/v1/projects/{project_id}/tech-audit/view
  ?dataset=pages|links|issues
  &q=&status=&indexability=&host_relation=&rule_id=&category=
  &severity=&priority_tier=&sort=&direction=asc|desc
  &run_id=<audit-run-id>
  &limit=50&offset=0
```

`limit` 支持 1–200；响应包含 `snapshot`、数据集列定义、当前页 `rows` 和 `pagination.total`。非法数据集、排序字段、方向或状态码会返回 400。行详情使用：

```text
GET /api/v1/projects/{project_id}/tech-audit/view/detail
  ?dataset=pages&key=<url-or-issue-fingerprint>&run_id=<audit-run-id>
```

`GET /api/v1/projects/{project_id}/tech-audit` 同时返回完整 audit 的 `history`。URL、Link 和 Issue 视图带上 `run_id` 后只读取该次运行的快照；不带时继续读取 `latest.json`。已结束的 run 可通过 `DELETE /api/v1/projects/{project_id}/tech-audit/history/{run_id}` 删除；删除当前 latest 会自动把稳定指针恢复到最近保留的快照，运行中的 run 会返回 409。

详情抽屉聚合 HTTP 响应、indexability、metadata、canonical/hreflang、redirect、inlinks/outlinks、确定性规则 evidence、GSC clicks/impressions/CTR/position、上期点击变化、最近一次手动重爬和现有 audit diff。前端只保存当前项目/数据集的列显示偏好到浏览器 localStorage，不保存服务端 Saved View。

服务端按最新快照与台账文件的修改时间缓存紧凑查看投影；文件变化后自动失效。列表行不重复携带完整 issue evidence，完整证据只在打开详情时读取。搜索输入会短暂合并后再查询，避免每次按键重新扫描大型快照。

表格选择状态可跨分页保留；“选择筛选结果”和重爬最多 1,000 个 URL。只有 URL Inventory 中已经实际抓取的 same-host 或启用子域后的 subdomain 页面可以重爬。External Link Inventory 行永远不能发起重爬。

## 快照与数据层

每次完整运行保存到 `projects/<id>/audits/tech-audit/runs/<run_id>/`。后台单页/批量重爬保存到 `audits/tech-audit/recrawls/<run_id>/`，并更新 `latest-recrawl.json`；它不会覆盖完整 crawl 的 `latest.json`，也不会重新计算完整技术规则。Summary 只显示 404 数量，URL Inventory 可筛选 404 并执行单个或批量重爬；已恢复页面会从 404 结果中移除，其他页面继续使用最近一次完整 crawl 的 issue 结果。

每次完整运行保存：

- `raw/site.json`：robots.txt 解析、Sitemap 响应与状态。
- `raw/pages/<page_id>.html` 与 `.json`：单页原始 HTML、headers、redirect chain、响应指标。
- `normalized/inventory.jsonl`：已抓取 URL 的规范化记录，包括 status、indexability、title、description、keywords、H1/H2、canonical、hreflang、depth、inlinks/outlinks、content hash。
- `normalized/link-inventory.jsonl`：所有发现的 HTTP(S) 链接，明确 `Internal/External`、同站子域关系、是否抓取和来源；外部链接不需要有响应码。
- `normalized/issues.jsonl`：规则命中和结构化 evidence。
- `normalized/action-groups.jsonl`：先按 fingerprint 去重，再按 rule + page template 聚合的执行队列。
- `normalized/gsc-page-metrics.json`：与 URL 匹配的 Search Analytics 页面级 clicks、impressions、CTR、position 及上期点击变化。
- `normalized/remaining-queue.jsonl`：本批次尚未抓取的唯一站内/允许子域 URL，可由 `tech-audit continue` 继续消费。
- `summary.json`、`run.json`：运行状态和聚合摘要。

`audits/tech-audit/tech-audit-*.json` 是可比较的快照索引，`latest.json` 是稳定指针；它们只引用上述分层文件，不承载整站原始数据。

历史管理只针对完整 crawl run；`recrawls/<run_id>/` 是针对已有 URL 的即时重爬证据，不会作为完整 audit 历史记录，也不会参与 run 删除。

完整 crawl 自动保留最近 3 个已结束 run；新 run 或 Continue 成功后会清理更早的完整 run。该策略不影响当前 latest、normalized 查询或 Continue，代价是旧 run 的历史和原始 HTML 不再保留；`recrawls/` 不计入这 3 个 run。

完全相同的 fingerprint 在写入前只保留一次；重复 title、description 或 content hash 的分组问题保留完整 `url_count`，但每条 issue 的 evidence 最多保存 10 个代表 URL。页面级 fingerprint 和验证历史仍是权威记录，Markdown 行动队列与 Pages 行动中心再按 rule + page template 聚合，避免把同一模板问题重复派发。快照中的 `new_high_impact` 只保存问题摘要，完整 evidence 继续以 `normalized/issues.jsonl` 为权威来源。

`summary` 会分别记录 `crawled_pages`、`discovered_unique` 和 `queued_remaining`。`discovered_unique` 是去重后的站内候选，不包含外链、图片 CDN 或其他 External Link Inventory 行；达到 `max_urls` 后不会丢弃队列。旧版本没有保存队列时，第一次 Continue 会根据上一快照中的 Sitemap 和已抓页面链接做一次 best-effort 恢复，并在 snapshot warnings 中明确标记。

## 规则与优先级

规则在 `seo_workbench/tech_audit.py` 中注册，每条都包含 `rule_id`、说明、默认严重级别、分类、evaluation input、evidence schema 和 remediation guidance。规则命中包含 fingerprint，不依赖 LLM。

基础优先级是确定性计算：

```text
technical severity × GSC page performance × historical click change × business URL heuristic
```

GSC 不可用时仍会生成技术问题，但会标记 `gsc_attributed=false`；这不是因果归因或订单预测。

问题台账保存在 `strategy/technical-issues.jsonl`。只有采集完整、配置指纹与基线一致的后续审计，才会把已不再出现的问题标记为 `verified`；部分抓取和不可比配置不会证明修复。再次出现的已验证问题会重新打开，仍被观察到的 `fixed` 问题会记录复验失败。

## 定时与飞书

后台页面可以保存 interval、Feishu role 和 profile；运行中的 crawl 会显示阶段、已处理 URL、发现数量和耗时，并每 2 秒刷新同一份 run 状态。Workbench 进程打开时会每 15 秒检查 due schedule，并调用同一条 `tech-audit run --scheduled --json`；关闭后台后仍可使用本机 cron/launchd：

```bash
./seo --project example-store tech-audit schedule set \
  --every-minutes 1440 --notify-role seo --profile example-store --json

# 由 cron/launchd 每 5 分钟调用；未到期时安全退出，不会重复运行
./seo --project example-store tech-audit run --scheduled --json
```

当定时配置包含 `notify_role` 时，只有新增的 `critical/high` 技术问题才通过 Workbench 内置的 Feishu adapter 通知；手动全量运行不隐式发送通知。Secret 不进入快照、JSON 输出或命令参数。

## 暂不做

首版不包含完整 Screaming Frog GUI、百万 URL 分布式抓取、全量 Playwright、登录/代理池/反爬、自动改站和 GSC 写入。需要这些能力时，应先用真实站点规模、失败率和队列吞吐证明当前项目边界不够。
