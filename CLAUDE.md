# SEO Tools Workspace

本工作区包含三套开源 SEO 工具包和一个编排层，覆盖 SEO 全链路：战略规划 → 内容生产 → 质量审查 → 技术审计。

## 目录结构

```
SEO tools/
├── CLAUDE.md                          ← 本文件
├── superseo-skills/                   ← SuperSEO: 内容战略顾问 (11个skills)
├── seomachine/                        ← SEO Machine: 内容生产流水线 (24个commands + 11个agents)
├── claude-seo/                        ← Claude SEO: 全站技术审计平台 (24个skills)
├── seo-workbench/                     ← 编排层: 串联三工具的状态机工作流
│   ├── CLAUDE.md                      ←   编排引擎定义 (阶段、Handoff、错误处理)
│   ├── templates/state.json           ←   状态文件模板
│   ├── state.json                     ←   运行时状态 (由 /workflow:init 创建)
│   ├── strategy/                      ←   战略产出 (关键词深潜、集群、简报)
│   ├── content/                       ←   内容产出 (草稿)
│   └── audits/                        ←   审计产出 (技术审计、页面审计、E-E-A-T)
├── .claude/commands/                  ← 自定义命令
│   ├── workflow-init.md               ←   初始化项目
│   ├── workflow-next.md               ←   推进下一步 (核心命令)
│   ├── workflow-status.md             ←   查看进度
│   └── workflow-phase.md              ←   跳转阶段
├── SEO工具链协同工作流指南.md           ← 通用教程
├── 从0到1新站SEO建设教程.md            ← 新站教程
├── Shopify从0到1-SEO建设进阶教程.md      ← Shopify (Liquid) 进阶教程
└── Shopify-Hydrogen-Headless-SEO指南.md  ← Shopify (Hydrogen/Headless) 指南
```

## 日常使用

**如果你要按工作流推进 SEO 任务:**

```
/workflow:status     查看当前进度
/workflow:next       执行下一步 (日常只需要这个)
/workflow:phase xxx  跳转到指定阶段
```

**如果你要单独调用某个工具:**

SuperSEO (内容策略):  `Skill("superseo:keyword-deep-dive")`, `Skill("superseo:content-brief")`, 等
SEO Machine (内容生产): `/research`, `/write`, `/optimize`, 等 (在 seomachine 工作区)
Claude SEO (技术审计): `Skill("claude-seo:seo-technical")`, `Skill("claude-seo:seo-schema")`, 等

**如果你是第一次用:**

1. 根据技术栈选择教程：`Shopify从0到1-SEO建设进阶教程.md` (Liquid 电商站) / `Shopify-Hydrogen-Headless-SEO指南.md` (Headless 电商站) / `从0到1新站SEO建设教程.md` (通用站)
2. 执行 `/workflow:init shopify --name "项目名" --url "https://你的网站.com"`
3. 跟着 `/workflow:next` 一步步走

## 编排层工作原理

`/workflow:next` 驱动一个 6 阶段状态机 (INIT → STRATEGY → CONTENT_PRODUCTION → QUALITY_REVIEW → TECHNICAL_AUDIT → OFF_PAGE → MONITORING)。每步自动:
1. 从 state.json 读取进度
2. 从产出目录读取上游上下文
3. 调用对应的 Skill 工具
4. 保存结果并更新状态

详见 `seo-workbench/CLAUDE.md`。

## 重要原则

- `/workflow:next` 一次只推进一个步骤，完成后暂停让你 review
- 不自动发布内容到线上（产出草稿，需手动 review 后发布）
- 编排层不修改三个工具包本身，只调用它们
- 不要在没有执行 `/workflow:init` 的情况下直接使用 workflow 命令
