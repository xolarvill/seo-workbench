# SEO 迭代闭环

这套流程把“发现问题、修改、复查、继续经营”连接起来。CLI 和项目文件是事实来源；所有评价都保留数据来源和窗口，不把同时发生的变化写成因果。

## 1. 采集搜索基线

```bash
./seo --project <id> statistics collect --json
```

已配置 GSC、GA4 和 Shopify 时，`statistics collect` 是生产入口：先采集 finalized GSC，再用同一个截止日采集两个业务来源、合并日历史并刷新 Portfolio。Search Analytics 同时保存 query、page、query-page、date-page、device 和 country。query-page 用于识别查询由哪个页面承接以及是否出现多页面信号；date-page 用于置信区间和趋势；country 只作为独立市场切片。只需要 GSC 的诊断运行仍可单独使用 `gsc collect`。

## 2. 记录上线改动

```bash
./seo --project <id> changes add \
  --url https://example.com/page \
  --type content \
  --hypothesis "更完整的选型信息会提升合格自然点击" \
  --metric clicks --metric ctr --metric conversions \
  --changed-at 2026-08-01 --review-date 2026-08-29 --json
```

支持的搜索指标是 `clicks`、`impressions`、`ctr`、`position`；可选业务指标包括 `organic_sessions`、`key_events`、`conversions`、GA4 Organic Search 商业漏斗、`organic_revenue` 以及 Shopify 全渠道 `revenue` / `orders`。`key_events` 是 GA4 属性中已配置为 key event 的事件计数，不等同于购买或外部导入的 `conversions`。变更台账位于 `strategy/seo-changes.jsonl`。

## 3. 可选：采集或导入聚合业务信号

GA4 与 Shopify 项目可分别采集只读、页面级聚合数据，再写入同一业务信号产物：

```bash
./seo --project <id> ga4 collect --end-date <GSC-endDate> --json
./seo --project <id> shopify-orders collect --end-date <GSC-endDate> --json
./seo --project <id> business-signals collect --json
```

GA4 提供自然搜索 landing page 的 sessions、key events，以及事件次数口径的 view item → add to cart → begin checkout → purchase 和 purchase revenue。这是 Organic Search landing-page-associated 聚合，不是用户路径或因果归因；标准电商事件的 tracking coverage 从全渠道检查，不能用“自然搜索无 purchase”推断埋点失效。Shopify 提供按 product handle 聚合的折后、退款后商品净额（不含税与运费），不做渠道归因。两边必须使用相同、互不重叠的完整窗口与相同时区，否则拒绝合并；要进入 Pages 的同一比较面，`--end-date` 还必须与最新 GSC 的 `endDate` 完全一致。GA4 未指定截止日时默认保留两个完整处理日。产物只保留页面级聚合值和币种，不保留用户、事件或订单标识符。

生产运行不要手工串联以上三个命令；统一使用：

```bash
./seo --project <id> statistics collect --json
```

该入口还会维护 120 天私有日历史、检查测量口径断点，并只在全部质量闸门通过后刷新 Pages。完整准备、指标方法和恢复规则见 [统计学 SEO 操作手册](统计学SEO操作手册.md)。

CRM 或其他来源继续通过页面级前后窗口 CSV/JSON 导入：

```csv
window,start_date,end_date,url,organic_sessions,conversions,revenue
previous,2026-07-04,2026-07-31,https://example.com/page,100,4,500
current,2026-08-02,2026-08-29,https://example.com/page,140,7,900
```

```bash
./seo --project <id> business-signals import \
  --from-file business-signals.csv --json
```

输入必须包含 `previous` 和 `current`，同一窗口内日期必须一致，URL 必须属于当前项目站点。不要导入用户、事件或订单标识符。所有业务产物以 `0600` 保存到 `audits/business-signals/`。

## 4. 到期后评价改动

```bash
./seo --project <id> changes list --due --json
./seo --project <id> changes evaluate <change_id> --refresh-gsc --json
./seo --project <id> changes status <change_id> reviewed --note "reviewed evidence" --json
```

`--refresh-gsc` 只读采集不超过 25 个变更 URL 的页面和 query-page 数据；更大变更集需使用显式的全属性 GSC 产物。前窗口结束于变更前一天，后窗口开始于变更后一天并结束于计划复查日。评价只在窗口可比且所有变更 URL 都有观测时给出 `winning`、`no_change` 或 `regressing`；未观测到的页面和缺失业务证据返回 `insufficient_data`，不会补成 0。结果是描述性前后证据，库存、价格、促销、需求和其他同期变更仍可能参与结果。

Pages 中的单 URL 复盘通过现有后台任务队列执行，不占用 HTTP 请求。多 URL 变更使用 CLI 和显式 GSC 产物复盘。

## 5. 用 Pages 经营全站页面

```bash
./seo --project <id> pages refresh --json
./seo --project <id> ui
```

`pages refresh` 将 GSC 前后窗口、最新技术审计和已有线上内容 URL 合并为同站页面资产表。命令行 JSON 只返回数量、来源状态与产物路径；页面明细通过 Pages 分页查看，避免把整站数据打印到终端。`content portfolio` 保留为调用同一实现的兼容命令。GSC 出现不等于已确认收录，爬虫没发现也不等于页面不存在；缺失证据会标记为 `not_observed`，不会补成 0。

Pages 默认打开 `Actions → Now`：

- `Now`：到期内容操作、indexing issue、open/planned 技术问题和当前页面机会；
- `Review`：到期 SEO 变更和已修复但等待可比审计验证的技术问题；
- `Watch`：保卫、监测、等数据页面和尚未到复盘日的上线变更。

`All pages` 用于搜索、筛选和查看来源；`Query conflicts` 只显示至少两个不同 URL 且总 impressions 不低于 100 的查询所有权冲突。页面机会继续使用透明规则给出：

- `refresh`：点击出现明确衰减；
- `consolidate_review`：一个查询出现多个承接页面，需人工判断区分、合并或重定向；
- `improve_snippet`：首页位置但 CTR 明显偏低；
- `expand_and_link`：处于可突破位置，建议补足意图和内部链接；
- `defend` / `monitor`：保持或继续观察；
- `wait_for_data`：窗口不可比、内容太新或展示不足。

顶部来源状态会比较 Portfolio 与当前 GSC、技术审计文件的新鲜度；源证据更新后显示 `needs refresh`，但不会在读取页面时隐式重算。详情抽屉将前后窗口、绝对/相对变化、Top Queries、查询冲突 URL、技术可索引性与内容/变更历史分开呈现。没有观测到的窗口或字段继续显示 `Not observed`。

Pages 中可记录 SEO 变更、更新内容状态、指派技术问题，并在评价结果后人工确认复盘。这些操作只写现有本地台账；任务分组是实时投影，不另建任务库。发布、飞书推送、重爬、重定向和站点修改仍进入 Content 或 Audit 工作区并保留原确认。结果保存在 `audits/content-portfolio/`。同页筛选深链、项目切换和 SSE 领域更新会刷新当前投影；API 校验失败会显示服务端的具体原因，而不是通用错误码。

## 6. 关闭技术问题

```bash
./seo --project <id> tech-audit issues list --status open --json
./seo --project <id> tech-audit issues status <fingerprint> planned --owner seo --note "scheduled" --json
./seo --project <id> tech-audit issues status <fingerprint> fixed --owner seo --note "deployed" --json
./seo --project <id> tech-audit run --json
```

人工不能直接设置 `verified`。只有完整且配置可比的后续审计确认问题不再出现，系统才写入已验证；接受风险使用 `accepted` 并必须附决策说明。

## 7. 保存站外证据

外链 CSV/JSON 至少包含 `source_url` 和 `target_url`，可选 `anchor`、`follow`、`rel`、`status`、`first_seen`、`last_seen`：

```csv
source_url,target_url,anchor,follow,status
https://publisher.example/article,https://example.com/page,Product guide,true,active
```

```bash
./seo --project <id> backlinks import \
  --from-file backlinks.csv --source semrush --complete --json
./seo --project <id> backlinks status --source semrush --json
```

`--complete` 只应在导出确实代表该来源的完整快照时使用。只有同一来源的前后两份快照都完整，缺失链接才会被确认成 `lost`；否则只是 `missing_unconfirmed`。已知 404/410 目标来自最新技术审计并保留审计时间。Workbench 不推断 authority/toxicity 分数，不自动生成 disavow。

已配置项目私有 DataForSEO BYOK 凭证时，可显式确认付费后采集：

```bash
./seo --project <id> backlinks collect --confirm-paid --json
./seo --project <id> backlinks gap --competitor competitor-a.com \
  --competitor competitor-b.com --confirm-paid --json
```

`collect` 保留 provider 总量、实际采集量、请求次数与费用；达到 `--max-links` 上限时标记为截断，不得用于确认丢失。`gap` 最多比较 3 个竞争域名，仅在 anchor 与已有 keyword-to-page 映射完全一致时建议站内目标；其余保持 `not_mapped`，不自动外联。

## 产物与边界

- 私有 GSC、业务、结果和外链 JSON 使用 `0600`；稳定 `latest.json` 指向当前证据，时间戳文件保留历史。
- `audits/backlinks-report.md` 和存在基线后的 `audits/backlinks-recheck.md` 满足工作流交付入口，只包含聚合摘要和私有证据路径。
- 内容建议、变更评价和外链差异都不自动改站。发布、合并、重定向、接受风险和 disavow 仍需人工决策。
