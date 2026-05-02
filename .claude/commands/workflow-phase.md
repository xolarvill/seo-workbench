# Workflow Phase Command

跳转到指定阶段。用于跳过、回退或重做某个阶段。

## Usage

```
/workflow:phase <phase>
```

phase 可选值: `init`, `strategy`, `content-production`, `quality-review`, `technical-audit`, `off-page`, `monitoring`

特殊值:
- `reset` — 显示如何完全重置项目

## Process

### Step 1: 验证阶段名称

确认传入的阶段名在 phaseOrder 中。如不在，列出可用阶段。

### Step 2: 检查上游依赖

根据 seo-workbench/CLAUDE.md 中定义的 requiredInputs，检查目标阶段的上游依赖：

```
跳转到 STRATEGY
  ✅ seomachine/context/brand-voice.md 存在
  ✅ seomachine/context/target-keywords.md 存在

跳转到 CONTENT_PRODUCTION
  ✅ strategy/briefs/ 下有 5 个简报文件
  → 可以跳转

跳转到 QUALITY_REVIEW
  ⚠️ contentQueue 中尚无 published 文章
  → 建议先完成 CONTENT_PRODUCTION 阶段的文章发布
  → 是否仍要跳转？[是/否]
```

### Step 3: 执行跳转

1. 更新 state.json: `currentPhase` = 目标阶段
2. 将目标阶段 status 设为 `in_progress`
3. 将该阶段所有步骤重置为 `pending`（除非用户指定保留进度）
4. 设置 `nextAction` 为该阶段第一步的描述
5. 设置 `lastAction` = "跳转到 {phase} 阶段"

### Step 4: 输出

```
✅ 已跳转到 {phase} 阶段

该阶段包含 {n} 个步骤:
  1. {step1.label} [pending]
  2. {step2.label} [pending]
  ...

👉 执行 /workflow:next 开始
```

## 特殊场景

### 跳转到前面已完成的阶段

```
/workflow:phase strategy
```

```
⚠️ STRATEGY 阶段之前已完成。

选择:
  1. 重新执行 — 重置所有步骤为 pending，重新来过
  2. 继续之前的进度 — 保留已完成的步骤，从第一个 pending 开始
  3. 取消
```

### 重置整个项目

```
/workflow:phase reset
```

```
⚠️ 这将删除所有进度并重置项目。状态文件和产出文件不会删除，但所有状态标记会重置。

确认重置？输入 "reset {project.name}" 确认。
```

确认后:
1. 将 state.json 重置为模板初始状态（保留 project 字段）
2. 所有阶段 status → pending
3. 所有步骤 status → pending
4. contentQueue 中所有文章 status → planned
5. 不删除任何产出文件（strategy/ content/ audits/ 保留）

### 跳转到一个被跳过的阶段

如果用户从 STRATEGY 直接跳到 TECHNICAL_AUDIT（跳过了 CONTENT_PRODUCTION 和 QUALITY_REVIEW），中间阶段的 status 保持为 pending（不会被标记为 done）。这允许用户后续回来补做。
