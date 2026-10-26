# 本地 SEO skills 的发现、路由与执行诊断

日期：2026-10-26。范围：仓库共享指令、三个来源的能力保存、默认技能映射、持续任务入口与验收边界。本文是仓库级诊断；店铺数据、私有会话记录和业务报告不随本文公开。

后续状态：用户已批准取消next调度；入口与运行层退役见 [当前架构](agent-skill-routing-design.md)。下文保留诊断时的实现观察，不作为当前命令教程。

## 结论与事实纠正

仓库明确要求本地 skills 优先，但没有可靠地把这一偏好转换为每次相关任务开始时的主动选择。当前实现更接近“保存三家能力并接入部分核心模块”，而不是完整整合三家的工作流程。

先前诊断以一次实际读取作为“使用过”的证据。用户纠正：该次任务是用户主动强调使用本地技能之后才读取的。因此该样本只能证明技能能够被读取，以及部分框架被使用，不能证明 agent 自发发现、主动选择或跨会话稳定调用。此次诊断没有可用于计算自主调用率的对照样本。

上下文竞争可能加重漏读，但没有足够证据将上下文长度、压缩或截断认定为根因。发现、接续与验收的结构缺口则可从当前实现验证。

## 当前能力与入口

截至诊断时，`skills/` 有63个名为 `SKILL.md` 的文件，默认 `workflows/seo_full.json` 映射16个不同技能文件。计数不包括其他命名的 command 和 agent 文档，也不代表全部技能都应该在每次任务中执行。

| 来源 | 已有整合 | 外围能力 |
|---|---|---|
| SuperSEO | 关键词研究、话题集群、brief、写作、页面与内容质量 | 旧文改进、访谈、精选摘要等额外流程 |
| Claude SEO | 技术审计、schema、sitemap、图片、漂移、外链 | `claude-seo-extra/` 中的专项模块 |
| SEO Machine | 保留了生产线命令、编辑／内链／元数据等专家材料 | 整组材料没有接入默认状态机执行器 |

这与 [能力保留说明](capability-preservation.md) 一致：SEO Machine 被明确列为保留的生产线材料。目录保全与运行整合是两件不同的事。

## 已验证的结构性发现

### P1：偏好指令没有形成任务入口

`AGENTS.md` 明确要求 local CLI 和 skills first；`CLAUDE.md` 委托共享指令，没有相互矛盾的默认执行器。但根指令的 Skill Modules 只突出4项，缺少按任务选择主技能与专项能力的完整入口。

仓库没有 `.agents/skills` 或 `.claude/skills` 注册目录；本次会话的可用技能清单也没有列出仓库全部技能。这是当前观察，不能外推成所有 agent runtime 的固定行为。普通 `skills/` 目录的存在不应被当作已经自动激活。

### P1：默认步骤不能覆盖持续工作

`seo_workbench/state.py::current_step` 只查看当前阶段的 pending/in_progress steps。在一个已有持续内容工作的运行项目上，`next` 返回 `step:null`、`pending:false`，不再返回 skill，而 status 仍提示审阅内容队列。

这不代表项目没有工作，也不应通过重置阶段制造待办。它说明当前技能发现依赖一次性阶段步骤，缺少与日常任务、内容队列和工作区交接的接续。

已有局部入口值得复用：`keyword_workspace.py::keyword_handoff` 返回 deep-dive 技能和上下文；`content_briefs.py` 在brief导出时提示使用内容技能。它们尚不能覆盖全部任务。

### P1：读取、执行与验收没有区分

`workflow.next_contract` 返回 skill/context/output；`cli.cmd_next` 输出路径，不执行技能。`validation.validate_workflow` 验证映射和路径存在；`state.update_step` 更新状态和历史，不验收专业产物。

因此，validate通过与技能没有做完整可以同时成立。工具记录中的路径字符串、实际文件读取、部分框架应用、完整步骤验收必须分别判断。当前抽样也存在已读技能但未完成完整SERP观察的明确披露。

### P2：保留材料存在适配债务

`improve-content/SKILL.md` 仍要求约2%关键词密度；SEO Machine 的 `commands/write.md` 仍要求2000字以上和1–2%密度。现行 `write-content` 则明确拒绝机械字数和密度目标。

Claude SEO extra 的审计模块还引用旧脚本、旧专家名称和500页抓取流程，不能直接替代Workbench受控采集器。上述材料可以提炼成熟方法，但不能原样升级为可执行默认能力。

### P2：上下文布局不利于发现

诊断时根 AGENTS.md 为127行、18,159字节，运行边界细则占比较大，技能入口靠后。全局技能说明也会竞争注意力。改进应让入口更早、更短，按需展开正文；不能据此声称已经证明发生过上下文截断。

## 后续方向与验证边界

按发现与选择、来源适配、持续任务接续、产物验收分层改进，详见 [跨会话技能调用设计](agent-skill-routing-design.md)。本文不表示这些改进已经实现。

复查应使用没有明确点名技能的真实任务，并同时检查是否主动选择、是否实际读取、是否合理缩减流程、是否交付证据。仅观察显式要求“使用本地技能”的任务，无法验收自主发现。

## 代码与文档证据

- [共享指令](../AGENTS.md)、[Claude适配入口](../CLAUDE.md)、[技能索引](../skills/README.md)。
- [默认工作流](../workflows/seo_full.json)、[步骤契约](../seo_workbench/workflow.py)、[状态转换](../seo_workbench/state.py)。
- [CLI](../seo_workbench/cli.py)、[结构校验](../seo_workbench/validation.py)、[关键词交接](../seo_workbench/keyword_workspace.py)、[内容brief](../seo_workbench/content_briefs.py)。

诊断阶段的运行项目 `validate --json` 与 `doctor --json` 总体通过；这只说明当时结构与环境检查结果，不证明自主调用、完整专业执行或全部历史审计健康。
