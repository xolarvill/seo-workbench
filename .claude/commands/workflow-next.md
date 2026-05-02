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
2. 如果当前阶段所有步骤 done → 将阶段 status 设为 done，推进 `currentPhase` 到下一个
3. 在当前阶段中找到第一个 status=pending 的步骤

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

**通用执行模式:**

1. 标记步骤 status: pending → in_progress，更新 state.json
2. 从产出目录读取上游上下文（按 Handoff 规则提取摘要）
3. 调用对应 Skill：
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

   **重要**: 在调用 Skill 前，将上游上下文摘要拼入 prompt。如果 Skill 不支持传参，则在调用前向用户说明上下文，然后调用。

4. 等待 Skill 执行完成
5. 提取关键结论，写入对应产出文件
6. 更新 state.json：
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

用户告知某篇文章已发布到 Shopify Blog 后：
- contentQueue 中该文章 status: draft → published
- 记录实际 URL
- QUALITY_REVIEW 阶段会自动发现新 published 的文章

### INIT 阶段特殊处理

INIT 阶段的步骤是引导性的，不是自动执行的：
- `config-brand-voice`: 检查文件是否存在，提示用户编辑
- `config-target-keywords`: 检查文件是否存在，提示用户编辑
- `verify-shopify-baseline`: 引导用户手动检查 Shopify 后台设置

每个步骤由用户确认"已完成"后标记 done。不自动写配置文件。

## 中断安全

每次修改 state.json 时：
1. 先 Read 最新内容
2. 修改字段
3. Write 完整覆写

确保 JSON 格式始终有效。
