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

**目标**: 配置好所有上下文文件，验证 Shopify 技术基线。

**步骤**:
1. `config-brand-voice` — 引导用户确认/创建 `seomachine/context/brand-voice.md`
   - 如果文件存在且非空：展示内容摘要，询问是否需要修改
   - 如果文件不存在：提供 Shopify 电商品牌声音模板，引导用户填充
2. `config-target-keywords` — 引导用户确认/创建 `seomachine/context/target-keywords.md`
   - 列出 5-10 个核心品类词 + 5-10 个信息型词
3. `verify-shopify-baseline` — 验证 Shopify 技术基础
   - 确认只有一个主域名，其他域名 301 到主域
   - 确认 HTTPS 全站强制
   - 确认 GSC 已验证
   - 确认 robots.txt 未屏蔽重要内容
   - 工具: 读取 `seo-workbench/state.json` 中的 `project.url`，使用 WebFetch 检查

**输出**: 已验证的品牌声音文件、目标关键词列表、Shopify 技术基线确认

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

1. `technical-audit` — 全站技术审计 (9维度)
   - 工具: `Skill("claude-seo:seo-technical")`
   - 审计报告写入 `audits/technical-audit.md`

2. `schema` — Schema 部署与验证
   - 工具: `Skill("claude-seo:seo-schema")`
   - 验证 9 种 Shopify 必需的 Schema 类型是否齐全
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

## 状态更新规范

每次修改 state.json 必须：
1. 先用 Read 读取最新内容
2. 修改相关字段
3. 用 Write 写回（不是 Edit，是完整覆写，确保 JSON 格式正确）
4. 必须更新的字段: `lastAction`, `nextAction`, 对应步骤的 `status`
5. 可选更新的字段: `contentQueue`, `keywords`, `cluster`, `notes`
