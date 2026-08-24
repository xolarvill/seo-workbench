# SEO Workbench 协同工作流指南

SEO Workbench 把站点资料、工作流状态、审计证据和内容文档放进同一个本地项目。CLI 是执行入口，agent 读取本地 skill 完成判断和写作，可选 UI 用来查看结果和编辑 Markdown。

开始前先读 [SEO 基础知识与证据模型](SEO基础知识与证据模型.md)。需要定位展示、点击、商品和收入分别在哪一层变化时，再读 [SEO 增长诊断与拆解](SEO增长诊断与拆解.md)。本文只讲如何操作 Workbench。

## 一个站点对应一个项目

不同站点的资料放在不同目录：

```text
projects/
├── default/
├── industrial-supplier/
└── shopify-store/
```

项目目录包含公开业务背景、策略、内容草稿和本地审计。凭据、token、GSC 数据及其他私密运行信息保存在被 Git 忽略的 `.runtime/` 和审计目录中。

列出已有项目：

```bash
./seo projects --json
```

初始化普通站点：

```bash
./seo --project my-site init general \
  --name "My Site" \
  --url "https://example.com" \
  --description "网站服务的客户和业务范围"
```

Shopify Liquid 使用 `shopify`，Hydrogen 或其他 Headless Shopify 使用 `shopify-headless`。已经有状态文件的项目可以使用 `existing`，不要用 `--force` 覆盖仍有价值的资料。

## 两条并行链路

Workbench 有工作流和证据两条链路。工作流记录接下来该做什么，证据记录网站现在是什么状态。

```text
业务资料和目标
      │
      ├── 工作流：战略 → 内容 → 质量 → 技术 → 外链 → 监测
      │
      └── 证据：raw → rendered → technology → Lighthouse → CrUX → GSC
```

工作流不会自动替你完成专业判断。`next` 返回步骤和对应的本地 skill，agent 读取 skill、项目上下文和证据后执行，再显式更新状态。

```bash
./seo --project my-site status --json
./seo --project my-site next --json
./seo --project my-site step start
./seo --project my-site step done
```

需要跳过不适用的步骤时使用 `step skip` 并在项目笔记中说明原因。不要为了让进度条变绿而跳过仍未确认的工作。

## 第一次基线采集

普通巡检从原始响应和代表路由开始：

```bash
./seo --project my-site evidence --json
```

JavaScript 站点、移动端可能跳转的站点，或原始 HTML 内容很少时，增加浏览器渲染：

```bash
./seo --project my-site evidence --rendered --json
```

默认会从同一主机的内部链接中选择少量代表路由，避免把一次基础巡检变成无边界爬虫。只检查项目首页时使用 `--crawl-limit 0`。

技术栈识别默认采用 balanced 模式：

```bash
./seo --project my-site technology --json
```

需要可重复的响应头、Cookie 和原始 HTML 检查时使用：

```bash
./seo --project my-site technology --scan-mode fast --json
```

技术检测结果用于理解交付、前端、内容、商务、分析和合规层。未检测到某项技术，只代表它没有出现在本次观察证据中。

## 性能证据分开采集

Lighthouse 提供可控环境中的实验室诊断：

```bash
./seo --project my-site performance --json
./seo --project my-site performance --form-factor desktop --json
```

默认进行五次顺序运行并保存完整结果。查看中位表现和运行波动，确认每次最终 URL 一致后再比较。

CrUX 提供真实 Chrome 用户的当前值和历史趋势：

```bash
./seo --project my-site crux --json
```

页面没有足够数据时可能回退到 origin；整个站点流量不足时返回 `no_data`。这两种状态都不等于性能合格或不合格。

## GSC 是显式的只读证据

首次使用需要由用户完成授权和 property 绑定。配置方法见 [Google integrations](google-integrations.md)。完成后运行：

```bash
./seo --project my-site gsc collect --json
```

这会采集完整时间窗口的 Search Analytics 对比、Sitemap 状态和少量代表 URL 的已索引版本。它不会提交 Sitemap、请求索引或执行 live test。

没有认证时，普通证据采集仍应继续。`needs_auth` 是需要用户处理的配置状态，不是网站故障。

## 一次组合采集

环境和 Google 集成都准备好后，可以显式组合采集器：

```bash
./seo --project my-site evidence \
  --rendered \
  --technology \
  --performance \
  --crux \
  --gsc \
  --json
```

每个采集器独立返回 `collection_status`、`errors` 和 `warnings`。一个外部 API 失败，不应抹掉已经成功取得的原始和渲染证据。

## 从审计结果形成任务

agent 应先读取稳定的 `latest.json` 指针，再按需要打开不可变快照：

```text
audits/raw/latest.json
audits/technology/latest.json
audits/performance/latest.json
audits/crux/latest.json
audits/gsc/latest.json
audits/content-portfolio/latest.json
```

报告至少区分三类内容：

- 已确认的问题，证据能够直接证明故障；
- 有根据的推断，需要额外验证才能归因；
- 当前缺口，本次采集没有足够数据。

技术栈名称本身不是问题。只有 raw/rendered 差异、网络请求、性能归因或配置证据能把某项技术与具体影响连接起来。

## Keywords 持续闭环

一级导航 **Keywords** 不是新的任务库。它在读取时联合以下事实源：

- `strategy/keyword-pool.jsonl`：人工决策和关键词采集字段；
- `audits/gsc/search-analytics/latest.json`：当前观察到的 query 表现；
- `audits/keywords/dataforseo/latest.json`：按需付费采集的市场量、CPC、付费竞争度、意图、趋势和 SERP；
- `strategy/keyword-dives/*.md`：agent 深潜结果；
- `content/blog-pipeline.jsonl` 与 `state.contentQueue`：生产状态和 Content ID；
- `audits/content-portfolio/latest.json`：目标页面、query ownership 和最新 Statistics 投影。

GSC 中尚未进入关键词池的 query 先显示为只读候选。Query 保留 GSC 观察到的原始表达和 exact-query 指标；Keyword 保存长期策略决策；Cluster 汇总已归属的相关 keyword/query；Target URL 指定计划承接页面。首次写入 `decision`、cluster、目标 URL、Content item 或 note 时，Workbench 才把该 query 物化到 `keyword-pool.jsonl`，不会复制整份 GSC 数据。人工字段只有 `decision`、`cluster_ref`、`target_url`、`target_content_id`、`note` 和由系统写入的 `updated_at`。`discovered → researched → mapped → in_production → live → measured` 阶段根据 research、Content、Portfolio 和 GSC 自动推导，不能人工改写；同一 Cluster 任一已归属 query 获得可比较 GSC 证据时，Cluster 聚合可进入 measured，但缺失 query 仍不解释为零。

日常操作顺序：

1. 在 **Opportunity Pool** 筛选 `unreviewed`，结合 priority 与 GSC impressions 决定 prioritize、hold 或 drop。
2. 在单行抽屉或批量栏设置现有 cluster、同域 URL/站内路径和现有 Content ID。抽屉将 Strategy 与 Query evidence 分区，分别展示 exact-query 和 Cluster 聚合，避免把观察值当成人工字段。**Topic Map** 每个 Cluster 只显示一行，用于发现未归属、多个计划目标、多个 Content item、同一 query 多 URL 竞争和缺少内容承接的簇。
3. 在 **Research** 打开已有 deep-dive。缺少文档时使用 **Agent deep dive**；UI 复制基于 `skills/keyword-deep-dive/SKILL.md` 的请求并打开 Codex，不预先创建空 Markdown。商业/交易意图写入稳定的 `strategy/keyword-dives/product-<slug>.md`，其他意图写入 `info-<slug>.md`。
4. 从关键词进入 Content 生产，上线后从目标 URL 进入 Pages；Pages 的 top query 和 ownership conflict 也能返回 Keywords。
5. 用现有 **Refresh statistics** 采集 GSC/GA4/Shopify 聚合证据，再查看 measured 阶段。Workbench 不保存第二份关键词指标。

批量操作可选择当前页或全部筛选结果，单次上限 1,000 条。Workbench 会先验证所有 cluster、Content ID 和 target URL，再在一个项目锁内按 file revision 原子写入；任一字段非法则整批不写，并发修改返回冲突并要求重新检查。未知 JSONL 字段、Feishu `source_record` 和历史 string/list `cluster_ref` 均保留。缺少 GSC、Portfolio 或业务证据表示 `not observed`，不能解释为零流量、未收录或没有页面。

Semrush 与 Google Ads 仍通过现有文件采集命令进入同一关键词池，不需要外部关键词数据库或常驻 SERP 服务：

```bash
./seo --project my-site keywords collect \
  --google-ads-csv google-ads.csv \
  --semrush-xlsx semrush.xlsx --json
```

DataForSEO 使用 REST v3，不引入 SDK。单个关键词可在抽屉中确认后采集 Keyword Overview 和 depth-10 Live SERP；Volume、CPC、付费搜索 Competition、Intent、12 个月趋势和 SERP 结果保存在独立 evidence artifact，Score 仍是 Workbench 的 `priority_score`。这两条接口均按请求计费，所以不随页面加载或 Statistics refresh 自动运行；缺少 provider evidence 显示为未采集，而不是零。

## 内容战略和生产

内容工作通过项目上下文和本地 skill 完成，不再使用旧项目的 slash command。agent 可以从当前步骤发现相应 skill：

```bash
./seo --project my-site next --json
```

常用 skill 包括：

- `keyword-deep-dive`，分析一个查询的意图、结果类型和竞争环境；
- `content-brief`，把搜索结果、受众任务和一手资料需求整理成写作简报；
- `write-content`，根据简报和品牌资料形成草稿；
- `page-audit`，检查已发布页面与用户任务、搜索结果和技术证据的差距；
- `technical-audit`，综合 raw、rendered、technology、performance、CrUX 和 GSC。

适合交给 agent 的请求：

> 读取 `my-site` 项目的当前状态、上下文和最新证据。执行 next 返回的 skill，把结果写入对应的项目目录，并说明哪些结论来自实测、哪些需要人工资料。

内容简报不要把竞品字数当成目标。它应明确用户任务、页面类型、必须回答的问题、第一方证据、内部链接和转化路径。

## 审计差异和上线复查

大改版、主题更新、依赖更新或 SEO 修复前后都应保存快照：

```bash
./seo --project my-site audit-diff --json
./seo --project my-site audit-diff --kind performance --json
```

Workbench 会拒绝部分不可比数据，例如 Lighthouse 最终 URL 不同、CrUX 实际范围不同或 GSC property 和窗口不同。此时应调整采集范围，不要强行输出回归结论。

## 可选 UI

```bash
./seo --project my-site ui
```

UI 监听本机地址，展示项目、证据、工作流和 Markdown 文件。它调用同一套受限 CLI 动作，不接收任意 shell 命令。

Keywords 与 Pages 是日常经营入口。Keywords 处理 query 的筛选、研究、归属和阶段；Pages 处理 URL 的动作与复盘。先运行 `./seo --project my-site pages refresh --json`，再打开 `Actions → Now`。`Review` 收纳到期变更和待复验技术问题，`Watch` 保留监测和等数据页面；`All pages` 和 `Query conflicts` 用于追查证据。轻动作只更新现有本地台账，发布、重定向、重爬和站点修改仍回到 Content 或 Audit 并经原确认流程。

UI 打开时，agent 仍然使用相同的 `./seo --project ...` 命令和项目文件。文件监听器会把新的审计和文档显示出来。编辑器使用 revision 检查，避免静默覆盖 agent 或用户的并发修改。

## 推荐工作节奏

频率应跟业务变化绑定：

| 触发条件 | 建议动作 |
|---|---|
| 新项目或第一次接手 | doctor、raw、rendered、technology、Lighthouse，配置后补 CrUX 和 GSC |
| 发布重要模板或迁移 | 发布前后采集同一批代表 URL，并运行 audit diff |
| 新内容上线 | 检查状态码、canonical、内部链接和 Sitemap，随后观察 GSC 完整数据窗口 |
| 性能改造 | Lighthouse 定位和回归，CrUX 或 RUM 观察真实用户趋势 |
| 流量异常 | 先确认 GSC 数据范围，再检查技术 diff、页面变化、查询和设备分布 |
| 定期维护 | 选择与站点更新频率匹配的周期，不要求所有站点固定每月全量审计 |

## 环境和安全检查

```bash
./setup.sh --check
./seo --project my-site doctor --json
./seo --project my-site validate --json
```

`doctor` 检查运行环境、可选依赖、Google 配置和最新证据，不会自动打开 OAuth 登录。凭据、token 和私有项目数据留在本地，不应复制进报告、日志或 Git。

## 场景教程

- [从 0 到 1 新站 SEO 建设教程](从0到1新站SEO建设教程.md)
- [自建普通网站 SEO 指南](自建普通网站SEO指南.md)
- [Shopify Liquid SEO 指南](Shopify从0到1-SEO建设进阶教程.md)
- [Shopify Hydrogen SEO 指南](Shopify-Hydrogen-Headless-SEO指南.md)
- [WooCommerce B2B SEO 指南](WooCommerce-B2B-SEO指南.md)
