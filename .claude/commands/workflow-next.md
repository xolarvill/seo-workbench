# Workflow Next Command

编排层核心命令。读取状态 → 确定下一步 → 读取上游产出 → 调用工具 → 保存结果 → 推进状态。

## Usage

```
/workflow:next
```

无参数。完全由 `seo-workbench/state.json` 驱动。

## Process

### Step 0: 前置检查

1. 确认 `seo-workbench/state.json` 存在。如不存在: "请先执行 /workflow:init"
2. 读取 `seo-workbench/CLAUDE.md` 获取阶段定义
3. 读取 `seo-workbench/state.json`

### Step 1: 中断恢复检查

扫描所有阶段的所有步骤，查找 `status: "in_progress"` 的步骤。

如找到:
```
⚠️ 检测到上次中断:
  阶段: {phase}
  步骤: {step.label}
  中断时间: 未知（通过 lastAction 字段推测）

选择:
  1. 重试 — 重新执行该步骤
  2. 跳过 — 标记为 done，继续下一步
  3. 重置 — 标记为 pending，回到该步骤初始状态
```

根据用户选择：
- 重试 → 跳到该步骤的执行逻辑
- 跳过 → 标记 done，重新调用 workflow:next 找下一个 pending 步骤
- 重置 → 标记 pending，重新调用 workflow:next

### Step 2: 找到下一步

1. 确定 `currentPhase`
2. 如果是 INIT 阶段且 steps 尚未包含类型专属步骤: 根据 `project.type` 动态插入 (见下方「INIT 阶段步骤动态插入」)
3. 如果当前阶段所有步骤 done → 将阶段 status 设为 done，推进 `currentPhase` 到下一个
4. 在当前阶段中找到第一个 status=pending 的步骤

**INIT 阶段步骤动态插入:**

当 workflow:next 首次进入 INIT 阶段时，根据 `project.type` 在通用步骤后追加类型专属步骤:
- `shopify` → 追加 `verify-shopify-liquid-baseline`
- `shopify-headless` → 追加 `verify-headless-seo-baseline` + `verify-headless-deploy`
- `general` → 追加 `verify-general-baseline`
- `existing` → 不追加

步骤定义见 `seo-workbench/CLAUDE.md` 的 INIT 阶段章节。追加后立即写入 state.json，确保后续执行一致。

### Step 3: 检查上游依赖

在进入某个阶段前，检查 requiredInputs（定义在 seo-workbench/CLAUDE.md）：

- INIT → 无依赖
- STRATEGY → 检查 `seomachine/context/brand-voice.md` 和 `target-keywords.md` 存在且非空
- CONTENT_PRODUCTION → 检查 `strategy/briefs/` 下有至少 1 个文件
- QUALITY_REVIEW → 检查 contentQueue 中有至少 1 篇文章 status=published
- TECHNICAL_AUDIT → 无需严格依赖（可随时审计）
- OFF_PAGE → 建议 TECHNICAL_AUDIT 完成（不能跳过但可 deferred）
- MONITORING → 无依赖

如果依赖不满足: 提示缺失项，建议先完成上游阶段。

### Step 4: 执行当前步骤

根据当前阶段和步骤，调用对应工具。详细执行逻辑见 `seo-workbench/CLAUDE.md` 各阶段定义。

**`headless-precheck` 步骤 (仅 shopify-headless):**

如果当前步骤为 `headless-precheck`：
1. 检查 `project.type`：
   - 非 `shopify-headless` → 标记步骤为 done，跳过，继续 Step 2 找下一步
   - `shopify-headless` → 执行预检
2. 标记步骤 in_progress
3. 确定扫描页面:
   - 首页: `{project.url}/`
   - 产品页: 从 `project.url` 拼一个产品页路径，或提示用户提供一个核心产品 URL
   - Blog: 从 contentQueue 中取第一篇 status=published 的文章 URL；如无已发布文章则取第一篇 draft
4. 依次用 `WebFetch` 以 "Return the COMPLETE raw HTML" 为 prompt 拉取 3 个页面
5. 读取 `seo-workbench/CLAUDE.md` 末尾「Headless SEO 爬虫预检清单」章节的 15 项扫描清单
6. 逐页逐项扫描，判定 ✅/❌/⚠️/—
7. 按预检报告输出格式生成 `audits/headless-precheck.md`
8. 提取 300 字摘要（❌ 和 ⚠️ 项的列表），保存到 state.json 的 `notes` 字段中（供后续步骤注入使用）
9. 标记步骤 done

**平台上下文注入 (TECHNICAL_AUDIT 阶段):**

如果当前步骤属于 TECHNICAL_AUDIT 阶段且不是 `headless-precheck`，从 `state.json` 的 `project` 字段构建平台上下文，注入 Skill 调用。

如果 `audits/headless-precheck.md` 存在且步骤为 `technical-audit` 或 `schema` 或 `images`：从文件中提取「传递给后续步骤的摘要」章节，**优先使用具体发现替换通用提示**。提取方法见 `seo-workbench/CLAUDE.md` TECHNICAL_AUDIT 阶段"平台上下文注入规则"表中的「有预检报告时」列。

```
从 state.json 读取:
  project.type = "shopify-headless" | "shopify" | "general" | "existing"
  project.platform = { framework, hosting, cms } | null

根据 project.type 构建注入片段:
  - shopify → "这是一个 Shopify Liquid 站。关注: App拖慢速度、重复产品URL、theme.liquid Schema输出"
  - shopify-headless → "这是一个 Shopify Headless 站 (框架: {framework}, 托管: {hosting}, CMS: {cms})。{优先使用 audits/headless-precheck.md 的具体发现；如不存在则使用通用提示}"
  - general → "这是一个通用 CMS 站。关注: 爬虫兼容性、URL结构、Schema、图片"
  - existing → 同 general，加 "这是一个已有站的改造项目"

步骤-注入映射表见 seo-workbench/CLAUDE.md TECHNICAL_AUDIT 阶段"平台上下文注入规则"。
```

**通用执行模式:**

1. 标记步骤 status: pending → in_progress，更新 state.json
2. 从产出目录读取上游上下文（按 Handoff 规则提取摘要）
3. 构建平台上下文 (如适用), 拼入 Skill prompt
4. 调用对应 Skill：
   - `Skill("superseo:keyword-deep-dive")` — 关键词深潜
   - `Skill("superseo:topic-cluster-planning")` — 集群规划
   - `Skill("superseo:content-brief")` — 内容简报
   - `Skill("superseo:write-content")` — 写文章
   - `Skill("superseo:page-audit")` — 页面审计
   - `Skill("superseo:eeat-audit")` — E-E-A-T 审计
   - `Skill("superseo:semantic-gap-analysis")` — 语义缺口
   - `Skill("superseo:linkbuilding")` — 外链策略
   - `Skill("claude-seo:seo-technical")` — 技术审计
   - `Skill("claude-seo:seo-schema")` — Schema
   - `Skill("claude-seo:seo-sitemap")` — Sitemap
   - `Skill("claude-seo:seo-images")` — 图片SEO
   - `Skill("claude-seo:seo-backlinks")` — 外链审计
   - `Skill("claude-seo:seo-drift")` — 漂移
   - `Skill("claude-seo:seo-geo")` — AI 搜索可见性

   **重要**: 在调用 Skill 前，将上游上下文摘要 + 平台上下文 (如适用) 拼入 prompt。如果 Skill 不支持传参，则在调用前向用户说明上下文，然后调用。

5. 等待 Skill 执行完成
6. 提取关键结论，写入对应产出文件
7. 更新 state.json：
   - 步骤 status: in_progress → done
   - `lastAction`: 描述刚完成的操作
   - `nextAction`: 描述下一步要做什么
   - 如适用：更新 `contentQueue`, `keywords`, `cluster`

### Step 5: 输出下一步提示

```
✅ 完成: {刚完成的步骤描述}

📄 产出: {产出文件路径}

👉 下一步: {nextAction描述}
   执行 /workflow:next 继续
```

## 特殊处理

### CONTENT_PRODUCTION 阶段的文章选择

从 `contentQueue` 中找第一篇 `status: "planned"` 的文章。如果多篇都是 planned，按数组顺序取第一个（Hub 优先）。

调用 write-content 前，读取:
- `strategy/briefs/{slug}.md` — 该文章的简报
- `seo-workbench/state.json` 的 `keywords` — 目标关键词
- `seo-workbench/state.json` 的 `cluster` — 集群上下文

将这些内容作为背景信息注入到 `Skill("superseo:write-content")` 的 prompt 中。

文章产出后:
- 写入 `content/drafts/{slug}.md`
- contentQueue 中该文章 status: planned → draft
- 下一篇文章自动排队

### 用户发布后标记

用户告知某篇文章已发布后：
- contentQueue 中该文章 status: draft → published
- 记录实际 URL
- QUALITY_REVIEW 阶段会自动发现新 published 的文章

发布目标根据 `project.type`:
- `shopify` (Liquid): 发布到 Shopify Blog
- `shopify-headless`: 发布到 Headless CMS (Sanity / Contentful / Strapi)
- `general`: 发布到对应 CMS

### INIT 阶段特殊处理

INIT 阶段的步骤是引导性的，不是自动执行的：
- `config-brand-voice`: 检查文件是否存在，提示用户编辑
- `config-target-keywords`: 检查文件是否存在，提示用户编辑
- `verify-shopify-liquid-baseline`: (type=shopify) 引导用户手动检查 Shopify 后台设置
- `verify-headless-seo-baseline`: (type=shopify-headless) 展示 Headless SEO 基线检查清单，引导用户逐项确认。检查清单根据 `platform.framework` + `platform.hosting` 从 `seo-workbench/CLAUDE.md` 末尾「Headless 平台检查清单」章节选取
- `verify-headless-deploy`: (type=shopify-headless) 展示部署检查清单，引导用户逐项确认
- `verify-general-baseline`: (type=general) 引导用户检查 CMS/建站平台基础设置

每个步骤由用户确认"已完成"后标记 done。不自动写配置文件。

## 中断安全

每次修改 state.json 时：
1. 先 Read 最新内容
2. 修改字段
3. Write 完整覆写

确保 JSON 格式始终有效。
