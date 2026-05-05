# SEO Workbench — 编排引擎

本文件定义 SEO Workbench 的状态机、阶段规则、Handoff 机制和错误处理。所有 workflow 命令（`workflow-init`, `workflow-next`, `workflow-status`, `workflow-phase`）以此文件为权威参考。

## 架构概览

```
用户 → /workflow:next  →  读取 state.json
                              │
                              ├─ 确定当前阶段和下一步
                              ├─ 从产出目录读取上游上下文
                              ├─ 调用对应 Skill/工具
                              ├─ 保存产出到对应目录
                              └─ 更新 state.json
```

三个已有工具包的 Skill 映射：
- **SuperSEO**: `superseo:keyword-deep-dive`, `superseo:topic-cluster-planning`, `superseo:content-brief`, `superseo:write-content`, `superseo:page-audit`, `superseo:eeat-audit`, `superseo:semantic-gap-analysis`, `superseo:improve-content`, `superseo:featured-snippet-optimizer`, `superseo:linkbuilding`
- **SEO Machine**: 斜杠命令在 `.claude/commands/` 下 (`/research`, `/write`, `/optimize`, 等)，可通过读取命令文件并执行其逻辑来调用
- **Claude SEO**: `claude-seo:seo-technical`, `claude-seo:seo-schema`, `claude-seo:seo-sitemap`, `claude-seo:seo-images`, `claude-seo:seo-page`, `claude-seo:seo-audit`, `claude-seo:seo-backlinks`, `claude-seo:seo-drift`, `claude-seo:seo-google`, `claude-seo:seo-ecommerce`, `claude-seo:seo-geo`

## 文件路径约定

```
seo-workbench/
├── CLAUDE.md                  ← 本文件
├── state.json                 ← 运行时状态（从 templates/state.json 复制而来）
├── templates/state.json       ← 模板
├── strategy/                  ← SuperSEO 产出
│   ├── keyword-dives/         ←   关键词深潜结果
│   ├── briefs/                ←   内容简报
│   └── cluster-plan.md        ←   集群规划
├── content/                   ← SEO Machine / SuperSEO write-content 产出
│   └── drafts/                ←   文章草稿
└── audits/                    ← SuperSEO + Claude SEO 审计产出
```

## 状态机：6 阶段流程

```
INIT → STRATEGY → CONTENT_PRODUCTION → QUALITY_REVIEW → TECHNICAL_AUDIT → OFF_PAGE → MONITORING
```

每个阶段有明确的：
- `requiredInputs`: 进入该阶段前必须存在的上游文件
- `steps`: 该阶段内的步骤列表
- `tools`: 完成步骤需调用的工具
- `outputs`: 完成后产出的文件
- `nextPhase`: 完成后自动进入的下一阶段

### 阶段 0: INIT

**目标**: 配置好所有上下文文件，验证技术基线。

**通用步骤** (所有项目类型):

1. `config-brand-voice` — 引导用户确认/创建 `seomachine/context/brand-voice.md`
   - 如果文件存在且非空：展示内容摘要，询问是否需要修改
   - 如果文件不存在：提供品牌声音模板，引导用户填充

2. `config-target-keywords` — 引导用户确认/创建 `seomachine/context/target-keywords.md`
   - 列出 5-10 个核心品类词 + 5-10 个信息型词

**类型专属步骤** (根据 `project.type` 动态加入):

| project.type | 步骤 ID | 步骤描述 |
|-------------|---------|---------|
| `shopify` | `verify-shopify-liquid-baseline` | 验证 Shopify Liquid 技术基线 (域名/HTTPS/GSC/robots/theme.liquid) |
| `shopify-headless` | `verify-headless-seo-baseline` | 验证 Headless SEO 基线 (MetaFunction/JSON-LD组件/sitemap/robots/404) |
| `shopify-headless` | `verify-headless-deploy` | 验证部署配置 (域名/HTTPS/CDN/GSC) — 根据 platform.hosting 展开不同检查项 |
| `general` | `verify-general-baseline` | 验证通用 CMS/建站平台检查 |
| `existing` | (无额外步骤) | 跳过基线验证 |

**workflow:next 执行 INIT 时**:
- 始终先执行通用步骤，再执行类型专属步骤
- 步骤根据 `project.type` 动态插入 state.json 的 `phases.INIT.steps`
- `verify-headless-seo-baseline` 和 `verify-headless-deploy` 的具体检查项定义见本文档末尾「Headless 平台检查清单」章节

**输出**: 已验证的品牌声音文件、目标关键词列表、技术基线确认

**进入下一阶段**: 所有步骤 status=done → currentPhase = STRATEGY

### 阶段 1: STRATEGY

**目标**: 确定内容战略——打什么词、建什么集群、每篇怎么写。

**requiredInputs**: brand-voice.md 和 target-keywords.md 已确认存在

**步骤**:

1. `keyword-dive-product` — 对核心品类关键词做深潜
   - 工具: `Skill("superseo:keyword-deep-dive")`
   - 用户需提供 1-3 个核心品类词（如 "organic baby pajamas"）
   - 将深潜结果摘要写入 `strategy/keyword-dives/product-{keyword}.md`
   - 更新 state.json 的 `keywords` 数组

2. `keyword-dive-info` — 对信息型关键词做深潜
   - 工具: `Skill("superseo:keyword-deep-dive")`
   - 用户需提供 3-5 个信息型词（如 "what should newborn wear to sleep"）
   - 将深潜结果摘要写入 `strategy/keyword-dives/info-{keyword}.md`
   - 更新 state.json 的 `keywords` 数组

3. `cluster-plan` — 话题集群规划
   - 工具: `Skill("superseo:topic-cluster-planning")`
   - 以上两步的关键词作为种子输入
   - 产出 Hub + 8-12 Spoke 架构，写入 `strategy/cluster-plan.md`
   - 更新 state.json 的 `cluster` 字段
   - 更新 state.json 的 `contentQueue` 数组（Hub 排第一，Spoke 按发布优先级排）

4. `content-briefs` — 为每篇计划文章生成内容简报
   - 工具: `Skill("superseo:content-brief")`
   - 遍历 `contentQueue` 中每篇文章
   - 每个简报写入 `strategy/briefs/{文章slug}.md`
   - 简报包含：标题建议、H2 结构、必备要点、目标字数、内容类型

**输出**: `strategy/cluster-plan.md`, `strategy/briefs/*.md`, `strategy/keyword-dives/*.md`

**进入下一阶段**: 所有步骤 status=done → currentPhase = CONTENT_PRODUCTION

### 阶段 2: CONTENT_PRODUCTION

**目标**: 逐篇产出高质量草稿。按 contentQueue 顺序，一次一篇。

**requiredInputs**: `strategy/briefs/` 目录下有至少 1 个简报文件

**步骤**: 动态生成。每次 `/workflow:next` 执行：
1. 从 `contentQueue` 找到第一篇 `status: planned` 的文章
2. 读取对应的 `strategy/briefs/{slug}.md`
3. 读取 `seo-workbench/state.json` 中的 `keywords` 和 `cluster` 字段作为上下文
4. 调用 `Skill("superseo:write-content")`，将简报内容作为 prompt 上下文注入
5. 产出草稿 → `content/drafts/{slug}.md`
6. 更新 contentQueue 中该文章 status: planned → draft
7. 检查是否所有文章 status=draft：若是，标记 CONTENT_PRODUCTION 阶段 status=done

**注意事项**:
- 写的是 Shopify Blog 文章，不是产品描述。信息型、教育型内容为主
- 不自动发布到 Shopify。产出草稿后提示用户 review 并手动发布
- 用户发布后，手动告知 workflow，将该文章标记为 published

**输出**: `content/drafts/*.md`

**进入下一阶段**: 所有 contentQueue 中的文章 status 至少为 draft（或 published）→ currentPhase = QUALITY_REVIEW

### 阶段 3: QUALITY_REVIEW

**目标**: 对已发布的内容做深度质检。

**requiredInputs**: `content/drafts/` 目录下至少有 1 篇文章 status 为 published

**步骤**:

1. `page-audits` — 逐篇对已发布页面做 7 维审计
   - 工具: `Skill("superseo:page-audit")`
   - 遍历 contentQueue 中 status=published 的文章
   - 每个审计报告写入 `audits/page-audit-{slug}.md`

2. `eeat-audit` — E-E-A-T 专项审计（核心页面）
   - 工具: `Skill("superseo:eeat-audit")`
   - 对 Hub 页 + 最重要的 2-3 篇 Spoke 做审计
   - 审计报告写入 `audits/eeat-{slug}.md`

3. `semantic-gap` — 语义缺口分析
   - 工具: `Skill("superseo:semantic-gap-analysis")`
   - 仅对有排名数据、排名在 4-10 的页面执行
   - 如果没有排名数据则跳过此步骤
   - 分析报告写入 `audits/semantic-gap-{slug}.md`

**输出**: `audits/page-audit-*.md`, `audits/eeat-*.md`, `audits/semantic-gap-*.md`

**进入下一阶段**: 所有步骤 status=done → currentPhase = TECHNICAL_AUDIT

### 阶段 4: TECHNICAL_AUDIT

**目标**: 全站技术基础排查，建立 SEO 漂移基线。

**requiredInputs**: 站点 URL 在 state.json 中已配置

**步骤**:

0. `headless-precheck` — Headless SEO 爬虫预检（仅 shopify-headless，其他类型自动跳过）
   - 工具: `WebFetch`（以无 JS 方式拉取原始 HTML，模拟搜索引擎爬虫）
   - 目标页面: 首页 + 1个核心产品页 + 1篇Blog文章（从 state.json 的 contentQueue 中取已发布文章）
   - 对照 Headless 风险清单逐页扫描 15 项
   - 产出 `audits/headless-precheck.md`
   - 此步骤产出会作为后续 `technical-audit` 和 `schema` 步骤的上下文注入

1. `technical-audit` — 全站技术审计 (9维度)
   - 工具: `Skill("claude-seo:seo-technical")`
   - 审计报告写入 `audits/technical-audit.md`

2. `schema` — Schema 部署与验证
   - 工具: `Skill("claude-seo:seo-schema")`
   - 验证 9 种必需的 Schema 类型是否齐全
   - 缺失的生成 JSON-LD 代码，放置在 `audits/schema-report.md`

3. `sitemap` — Sitemap 生成与提交
   - 工具: `Skill("claude-seo:seo-sitemap")`
   - 产出写入 `audits/sitemap-report.md`

4. `images` — 图片 SEO 检查
   - 工具: `Skill("claude-seo:seo-images")`
   - 产出写入 `audits/images-report.md`

5. `drift-baseline` — 建立 SEO 漂移基线
   - 工具: `Skill("claude-seo:seo-drift")`
   - 对核心页面建立基线，后续改版时用于对比

**平台上下文注入规则:**

当 `project.type = "shopify-headless"` 时，在调用 Skill 前将以下上下文拼入 prompt。

如果 `headless-precheck` 步骤已完成（`audits/headless-precheck.md` 存在），**优先使用预检报告中的具体发现**替换通用提示：

| 步骤 | 注入内容（无预检报告时） | 注入内容（有预检报告时） |
|------|----------------------|------------------------|
| `technical-audit` | "这是一个 Shopify Headless 站（框架: {platform.framework}, 托管: {platform.hosting}, CMS: {platform.cms}）。审计时额外关注：流式SSR兼容性、筛选参数canonical、分页SEO、JS bundle大小、CMS内容SSR渲染、自定义路由重复。" | 从 `audits/headless-precheck.md` 提取 ❌/⚠️ 项摘要，格式: "预检已发现以下问题，请纳入审计结论并评估严重程度：[问题1], [问题2]..." |
| `schema` | "Headless 站，Schema 程序化生成。检查 `<script type='application/ld+json'>` 输出。" | 从预检报告提取 Schema 相关发现，格式: "预检扫描发现：首页缺失 WebSite Schema / 产品页 JSON-LD Product 未找到（疑似 Suspense）/ ... 。请验证这些问题并生成修复代码。" |
| `sitemap` | "Sitemap 由开发者自定义实现，验证 XML 完整性和 URL 覆盖率。" | 不变（sitemap 检查与预检无关） |
| `images` | "图片通过 {platform.framework} 的 Image 组件渲染。检查 alt、尺寸、CDN 格式转换。" | 从预检报告提取图片相关发现，格式: "预检扫描发现：产品页 N/M 张图片缺少 alt / Blog 页图片无尺寸属性。请重点审计这些页面并给出修复建议。" |

对于 `project.type = "shopify"` (Liquid) 或 `general`，注入对应平台上下文（Liquid 关注 App 拖慢速度、重复 URL 等；通用站关注 CMS 框架），无需预检。

**输出**: `audits/technical-audit.md`, `audits/schema-report.md`, `audits/sitemap-report.md`, `audits/images-report.md`, 漂移基线数据

**进入下一阶段**: 所有步骤 status=done → currentPhase = OFF_PAGE

### 阶段 5: OFF_PAGE

**目标**: 外链策略规划与首次外链审计。

**步骤**:

1. `linkbuilding-strategy` — 外链建设策略
   - 工具: `Skill("superseo:linkbuilding")`
   - 策略写入 `strategy/linkbuilding-plan.md`

2. `backlinks-audit` — 首次外链审计
   - 工具: `Skill("claude-seo:seo-backlinks")`
   - 审计报告写入 `audits/backlinks-report.md`

**输出**: `strategy/linkbuilding-plan.md`, `audits/backlinks-report.md`

**进入下一阶段**: 所有步骤 status=done → currentPhase = MONITORING

### 阶段 6: MONITORING

**目标**: 周期性复查（每月一次建议）。

**步骤**: 用户按需触发
1. `technical-recheck` — 技术复查
2. `drift-compare` — 漂移对比
3. `backlinks-recheck` — 外链复查

不自动进入任何下一阶段（持续循环）。

## Handoff 上下文传递规则

当从步骤 A 推进到步骤 B 时，`workflow:next` 必须携带上游产出作为上下文。规则：

1. **提取而非搬运**: 从上游产出文件提取结构化摘要（300-500字），而非将整个文件塞入下个 prompt
2. **提取要点**: 关键词、搜索意图、目标字数、核心角度、竞品差距
3. **注入方式**: 在调用 Skill 前，将摘要拼入 skill 的 prompt 参数中

### 关键 Handoff 链

```
STRATEGY.keyword-dives → STRATEGY.cluster-plan:
  传递: 关键词列表 + 每个词的意图和难度

STRATEGY.cluster-plan → STRATEGY.content-briefs:
  传递: Hub主题 + Spoke列表 + 每篇的定位和关键词

STRATEGY.briefs → CONTENT_PRODUCTION (每篇文章):
  传递: 完整简报内容（标题、大纲、要点、字数、内容类型）

CONTENT_PRODUCTION.draft → QUALITY_REVIEW.page-audits:
  传递: 文章URL（如已发布）+ 目标关键词 + 搜索意图

QUALITY_REVIEW.* → TECHNICAL_AUDIT:
  传递: 审计中发现的页面级技术问题摘要

TECHNICAL_AUDIT → OFF_PAGE:
  传递: 站点技术健康评分、已修复/待修复问题
```

## 错误处理与中断恢复

### 中断检测
`workflow:next` 启动时：
1. 扫描所有阶段的所有步骤
2. 查找 `status: in_progress` 的步骤
3. 如有，提示: "检测到上次中断于 [phase] → [step]。选择: [重试 / 跳过(标记为done) / 重置(标记为pending)]"

### Skill 调用失败
1. 如果 Skill tool 返回错误或不可用：提示用户手动执行对应操作
2. 提供手动标记进度的方式：告知用户可以手动编辑 state.json 将步骤标记为 done
3. 不阻塞整体流程：用户可以选择跳过当前步骤继续

### 上游依赖缺失
进入某个阶段前，检查 requiredInputs：
- 文件不存在 → 提示缺失了什么，建议回到上游阶段
- 文件存在但内容为空 → 标记为警告，询问是否继续

## 项目类型差异

### Shopify 新站 (Liquid)
- INIT 阶段额外步骤: 验证 Shopify 技术基线 (theme.liquid/GSC/域名/robots)
- STRATEGY 阶段强调: 品类词+信息型词双线、商业调研型内容(Best X / X vs Y)
- TECHNICAL_AUDIT 阶段额外关注: 重复产品URL、Schema(Product/Offer/AggregateRating)、图片SEO
- CONTENT_PRODUCTION 产出: 发布到 Shopify Blog（非 WordPress）
- 教程: `Shopify从0到1-SEO建设进阶教程.md`

### Shopify 新站 (Hydrogen / Headless)
- INIT 阶段额外步骤: 验证 Hydrogen SEO 基线 (MetaFunction/JSON-LD组件/sitemap resource route/robots resource route/404状态码)
- STRATEGY 阶段: 与 Liquid 相同
- TECHNICAL_AUDIT 阶段额外关注: 流式SSR兼容性、分页SEO、筛选参数canonical、JS bundle大小、hydration开销、Headless CMS内容SSR验证
- CONTENT_PRODUCTION 产出: 发布到 Headless CMS（Sanity/Contentful/Strapi），非 Shopify Blog
- 教程: `Shopify-Hydrogen-Headless-SEO指南.md`

### 通用新站
- INIT 阶段: 跳过 Shopify 技术基线验证，替换为通用 CMS/建站平台检查
- CONTENT_PRODUCTION 产出: 可与 SEO Machine 的 WordPress 发布流程对接

### 已有站改造
- 跳过 INIT 中的品牌配置（假设已有）
- STRATEGY 前加入现状分析步骤: `Skill("superseo:page-audit")` 对现有核心页面
- 优先进入 QUALITY_REVIEW 和 TECHNICAL_AUDIT 阶段

## Headless 平台检查清单

以下清单在 INIT 阶段 type=shopify-headless 时使用。workflow:next 根据 `platform.framework` + `platform.hosting` 组合选择对应的检查清单，展示给用户逐项确认。

### Hydrogen + Oxygen

**verify-headless-seo-baseline (SEO 基线检查):**
- [ ] `root.tsx` 的 `MetaFunction` 完整（title / description / canonical / OG site_name / Twitter Card）
- [ ] 每个产品 route (`products.$handle`) 有独立 `MetaFunction`（title 含产品名+品类+品牌, description 来自产品描述前 155 字符）
- [ ] 每个集合 route (`collections.$handle`) 有独立 `MetaFunction`
- [ ] 每个 Blog 文章 route (`blog.$slug`) 有独立 `MetaFunction`（含作者和发布日期）
- [ ] 静态页 route (`pages.$handle`) 有独立 `MetaFunction`
- [ ] JSON-LD 组件不在 React `<Suspense>` 边界内（确保首帧 HTML 输出）
- [ ] 产品页有 `ProductJsonLd` 组件（`name`, `description`, `image`, `offers` 含 price/availability, `brand`）
- [ ] 产品页有 `AggregateRating` JSON-LD（需对接 Judge.me / Stamped.io API）
- [ ] 全站有 `BreadcrumbList` JSON-LD 组件
- [ ] `root.tsx` 有 `Organization` JSON-LD（Logo + 联系信息 + sameAs 社交链接）
- [ ] `root.tsx` 有 `WebSite` + `SearchAction` JSON-LD
- [ ] 筛选/排序参数页 canonical 指向清洁 URL 或 noindex
- [ ] `/search` 页面 noindex
- [ ] `/cart`、`/account`、`/checkout` 路径不可爬取

**verify-headless-deploy (部署检查):**
- [ ] `/sitemap.xml` resource route 返回 200 + 完整 XML（含首页、产品、集合、Blog、静态页）
- [ ] `/robots.txt` resource route 返回 200 + 包含 Sitemap 链接
- [ ] 404 页面返回 404 状态码（非 200）
- [ ] 主域名 301 重定向到首选版本（www ↔ non-www）
- [ ] HTTP 自动 302/301 到 HTTPS（Oxygen 默认处理，确认）
- [ ] GSC 已验证（DNS TXT 或 HTML 文件上传至 `public/`）
- [ ] GA4 已注入（root.tsx 中）
- [ ] Oxygen 部署 hook 或 CI 配置完成

### Hydrogen + Vercel / 自托管

**基础检查** = Hydrogen + Oxygen 的全部项目 +

**额外检查:**
- [ ] Vercel/自建 CDN 域名配置（首选域 / HTTPS / SSL 证书）
- [ ] CDN 缓存策略：HTML 页面短缓存（`Cache-Control: public, max-age=60, stale-while-revalidate=3600`），静态资源长缓存（`max-age=31536000, immutable`）
- [ ] 服务器地理位置接近主要客户（如不在 CDN 后）
- [ ] SSR 渲染性能监控已配置（Sentry / Logflare / Vercel Analytics）
- [ ] 图片优化方案已配置（Hydrogen `<Image>` 依赖 Oxygen CDN 参数——自托管需额外方案如 Sharp）

### Next.js + Shopify

**verify-headless-seo-baseline (SEO 基线检查):**
- [ ] App Router: 每个 route 有 `generateMetadata` 或 `metadata` export
- [ ] Pages Router: 每个页面有 `<Head>` 或 `NextSeo` 组件
- [ ] JSON-LD 通过 `dangerouslySetInnerHTML` 或独立组件渲染（不依赖 useEffect）
- [ ] RSC Streaming: 关键 SEO 标签和 JSON-LD 不在 Suspense 边界内
- [ ] Product / Collection / Blog / 静态页 JSON-LD 完整（同 Hydrogen 标准）
- [ ] 筛选/排序参数 canonical 处理
- [ ] `/search` 等内部页 noindex

**verify-headless-deploy (部署检查):**
- [ ] `next-sitemap` 或 App Router `sitemap.ts` 生成完整 sitemap
- [ ] App Router `robots.ts` 或 Pages Router `robots.txt` 正确输出
- [ ] 产品页 ISR `revalidate` 时间合理（建议 3600s，高频更新产品 600s）
- [ ] 404 页面返回 404 状态码
- [ ] Vercel/Netlify/自托管 域名与 HTTPS 配置
- [ ] `next/image` 组件: alt 从产品数据动态填充, sizes 属性正确, 格式自动转换 (WebP/AVIF)
- [ ] GSC + GA4 已配置

### 所有 Headless 路线的通用检查项

以下与 framework 无关，所有 headless 站都需要:

- [ ] Headless CMS 中的内容在页面首次 HTML 中呈现（非客户端 fetch）
- [ ] Blog 文章有作者署名和简介（CMS 字段 → HTML 输出）
- [ ] 发布日期和更新日期在页面中可见（`<time>` 标签 + `dateTime` 属性）
- [ ] 每篇 Blog 文章有 Article JSON-LD（作者、发布日期、修改日期、主图）
- [ ] 站点有 About 页、Contact 页、隐私政策、退换货政策（CMS 管理或静态路由）
- [ ] 核心产品页有至少 300 字描述（来自 Shopify 产品数据或 CMS 增强）
- [ ] 核心集合页有至少 300 字品类描述（从 CMS 获取，渲染在集合页底部）
- [ ] 所有产品图片有描述性 Alt Text
- [ ] 首屏图片 `loading="eager" fetchpriority="high"`，其余 `loading="lazy"`
- [ ] 所有图片有明确尺寸或 `aspectRatio`（防止 CLS）
- [ ] OG 社交分享图至少 1200×630，所有核心页面设置

## Headless SEO 爬虫预检清单

以下 15 项由 TECHNICAL_AUDIT 的 `headless-precheck` 步骤在原始 HTML（无 JS 渲染）中逐页扫描。格式模仿搜索引擎爬虫视角。

### 页面样本

预检至少覆盖:
- 首页 (`/`)
- 1 个核心产品页 (从 state.json 的 contentQueue 中取已发布的交易型文章目标 URL，或用户指定)
- 1 篇 Blog 文章 (从 state.json 的 contentQueue 中取 status=published 的信息型文章目标 URL)

### 15 项扫描清单

每项判定 ✅ 通过 / ❌ 未通过 / ⚠️ 部分通过 / — 不适用，必须附 HTML 证据。

| # | 检查项 | 判定逻辑 |
|---|--------|---------|
| 1 | **Title 存在且合理** | `<title>` 标签存在，长度 30-65 字符，非默认模板值 |
| 2 | **Meta Description 存在** | `<meta name="description">` 存在，长度 70-155 字符 |
| 3 | **Canonical 正确** | `<link rel="canonical">` 存在，指向自身 URL（非带参数版本），绝对路径 |
| 4 | **Robots meta 正确** | 内容页为 `index, follow` 或无 robots meta（默认 index）；搜索/购物车/账号页为 `noindex` |
| 5 | **OG 标签完整** | `og:title` + `og:description` + `og:image` + `og:type` 均存在，`og:image` 为绝对 URL |
| 6 | **JSON-LD 存在且 JSON 有效** | 至少 1 个 `<script type="application/ld+json">` 存在，JSON.parse 不报错 |
| 7 | **JSON-LD 类型完整** | 首页: Organization + WebSite；产品页: Product (+ Offer + AggregateRating)；Blog 页: Article |
| 8 | **正文在原始 HTML 中** | 正文首段文字在原始 HTML 中出现（非仅客户端渲染）；搜索关键词可定位到正文内容 |
| 9 | **无 Suspense fallback 残留** | 原始 HTML 中不含 "Loading..." / "Skeleton" / 空白占位符等 Suspense fallback 文本 |
| 10 | **H1 唯一且有意义** | 恰好 1 个 `<h1>`，内容非空、非 "Untitled"、非站点名 |
| 11 | **图片有 alt** | 正文/产品区域中 ≥80% 的 `<img>` 有非空 `alt` 属性 |
| 12 | **图片有尺寸** | 正文/产品区域中 ≥80% 的 `<img>` 有 `width` + `height` 或 `style="aspect-ratio:..."` |
| 13 | **作者与日期可见** (Blog 页) | `<time>` 标签或文本日期 + 作者名在 HTML 中出现 |
| 14 | **内部链接存在** (Blog 页) | Blog 正文中有 ≥2 个指向站内产品或其他 Blog 的 `<a>` 链接 |
| 15 | **CMS 内容完整渲染** | Headless CMS 的内容（正文/作者/日期/富文本）均在原始 HTML 中完整出现 |

### 预检报告输出格式

`audits/headless-precheck.md`:

```markdown
# Headless SEO 爬虫预检报告

> 扫描时间: {timestamp}
> 平台: {platform.framework} + {platform.hosting}, CMS: {platform.cms}
> 扫描页面: URL1, URL2, URL3

## 汇总

| 状态 | 数量 |
|------|------|
| ✅ 通过 | N |
| ❌ 未通过 | N |
| ⚠️ 部分通过 | N |
| — 不适用 | N |

## 逐页详情

### {页面标题} ({URL})

| # | 检查项 | 状态 | 证据 |
|---|--------|------|------|
| 1 | Title | ✅ | "{实际title文本}" — {长度} chars, HTML line {N} |
| 2 | Meta Description | ❌ | 未找到 `<meta name="description">` |
| ... | ... | ... | ... |

## 关键发现

### 阻塞级 (❌)
- [ ] 问题1: 影响 + 证据
- [ ] 问题2: 影响 + 证据

### 警告级 (⚠️)
- [ ] 问题1: 影响 + 证据

## 传递给后续步骤的摘要

(300字以内，用于注入 technical-audit 和 schema skill 的 prompt)
```

## 状态更新规范

每次修改 state.json 必须：
1. 先用 Read 读取最新内容
2. 修改相关字段
3. 用 Write 写回（不是 Edit，是完整覆写，确保 JSON 格式正确）
4. 必须更新的字段: `lastAction`, `nextAction`, 对应步骤的 `status`
5. 可选更新的字段: `contentQueue`, `keywords`, `cluster`, `notes`
