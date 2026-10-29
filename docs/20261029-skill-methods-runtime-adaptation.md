# 专家方法整理与运行引用适配

日期：2026-10-29（Asia/Shanghai）。范围：已批准计划第 4、5 步。第 2、3 步见[能力归属和目录迁移](20261029-skill-layout-migration.md)，来源与历史见[来源参考](skill-sources.md)。

## 第 4 步：方法归属与来源保存

原有 11 份专家材料与 24 份流程文档逐项登记在 [skill-method-adaptations.json](skill-method-adaptations.json)。其中 34 份整理为当前能力的按需参考，scrub 仅保留历史。

- 编辑、内容审阅、元数据、SEO 编辑、内链、关键词分布、集群、标题、转化与表现方法分别挂在对应的主入口下。
- 研究、brief 到写作、旧文更新、内容日历、落地页和再利用流程改成输入、专业判断和交付物的参考；不复制原环境的命令执行链。
- 发布流程整理为当前平台的交付准备和状态核对，保留 WordPress 原文作为来源，不暗示 Workbench 已安装 WordPress 执行器。
- 每份适配参考记录使用条件、主入口和历史原文；清单通过 derived_from／adapted_by 保留双向关联。原文内容指纹单独核对。
- scrub 的字符处理和水印主张不构成阅读质量标准，不设置新的自动清理环节。后续写作标准改造独立进行。

主入口仍为 60 个；这一步只接入参考材料，不创建并列执行器、任务调度器或另一个状态数据库。

本层校验：`tests/test_skill_layout.py`、`tests/test_skill_methods.py`、`tests/test_skill_inventory.py` 共 11 项通过；来源清单覆盖 401 个文件，35 份历史原文的 SHA-256 保全检查通过。另增加本地维护脚本，刷新和检查指纹、来源关联及路径关系，不依赖临时脚本或外部服务。

## 第 5 步：运行与引用适配

| 定位 | 根因 | 当前处理 |
|---|---|---|
| 四个营销技能的 25 处 tools 引用 | 来源包的工具指南未随方法引入，MCP 勾选表也不能证明当前连接 | 分别提供分析、广告、邮件和推荐计划的数据输入要求；按当前工具发现实际接口 |
| Google、外链、DataForSEO、集群、电商、SXO 和图片方法 | 专业方法与原项目的脚本、扩展安装器、全局目录及成本账本混在一起 | 保留分析方法，使用已核对 help 的 Workbench 操作；未实现的接口使用真实连接或明确导出输入 |
| 营销上下文 | 写死 Claude 专属位置，可能跨店铺使用 | 解析到当前项目 context，优先复用已有 context／strategy |
| Local／Maps／Schema 与 FLOW 参考 | 目录迁移后仍沿用来源仓库布局，部分目标从未引入 | 修复实际本地路径；未引入的 FLOW 文档改为标明当前替代方法，保留来源许可；lock 更新为本地指纹 |
| 局部 meta 与现成文章交接 | 新的按需参考接到仍默认运行完整研究／创作的主入口 | 增加 metadata-only 和 delivery 模式，复用现有输入，按任务执行导入或校验 |
| 来源维护脚本 | 最新历史未刷新、内容变化标记不可恢复、缺失材料可能中断扫描 | 使用真实 Git 历史和首次 blob，单列未提交修改；缺失材料返回错误；增加临时 Git 仓库回归 |

共享执行契约见 [Workbench operations](../skills/seo/references/workbench-operations.md)，已从技能索引和相关方法接入。主入口仍为 60 个；来源清单覆盖 406 个文件。35 份历史专家／流程原文保持原指纹。原始来源 ID、固定上游比较版本和许可声明均保留。

## 校验与行为抽样

- 先增加严格引用回归，确认旧材料会失败，再完成适配；最终活跃材料严格引用检查通过。
- 结构、来源保全、专业方法归属、维护工具及原有 agent-led 工作流回归共 **38 项通过**。
- 显式项目 validate 为 `ok=true`，保留既有 `project_dir.missing` warning：缺少可选 browser evidence 目录。
- 核对所用命令的本地 help；FLOW 本地 lock 与所列文件 SHA-256 一致。
- 独立架构审阅发现并修正来源历史字段问题；安全审阅未发现阻断问题。复核文件路径、固定 argv 子进程、项目凭证与付费／发布边界。
- 三个只读调用抽样覆盖“局部润色＋meta”“无供应商连接的邮件分析”“现成草稿导入及交接”。抽样识别并修正两个模式冲突，复核后均能按请求复用输入、选择参考和确定操作。这是方法选择及指令一致性抽样，没有执行真实导入或平台发布，也不代表日常自主调用率。

本轮未更换固定上游版本。写作风格及免责式表达的统一改造仍属于后续步骤。

## 验证方法

使用项目 venv 运行结构与专业方法归属回归；来源清点脚本只读取本地文本、文件指纹和 Git 记录，不执行来源材料里的命令。

```bash
.venv/bin/python scripts/skill_inventory.py check --strict-active
.venv/bin/python -m pytest tests/test_skill_layout.py tests/test_skill_methods.py \
  tests/test_skill_inventory.py tests/test_state_workflow.py \
  tests/test_ui.py::test_workspace_does_not_schedule_an_agent_step \
  tests/test_keyword_workspace.py::test_stage_progression_and_handoff_paths -q
./seo --project hexcal validate --json
```

两个步骤分别 commit，保留可回滚记录；未运行外部采集、发布或消息发送。
