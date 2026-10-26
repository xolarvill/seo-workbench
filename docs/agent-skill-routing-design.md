# 跨会话主动选择本地 SEO skills

日期：2026-10-26。状态：设计提案，未实施。依据：[技能整合诊断](20261026-local-skill-integration-diagnosis.md)。本次文档迁移和同步已获授权；下列运行行为改动需要单独进入实施。

## 目标与判断

目标是让从仓库开始工作的 agent，在用户没有点名技能时，也会根据任务主动读取和组合本地成熟方法，并交付可检查的结果。优化目标是任务质量与适当流程，不是读取数量、调用率或所有步骤的机械完成率。

推荐以仓库指令和任务索引作为跨会话入口，保留 agent 对任务、证据与投入的判断；CLI补足发现提示，产物记录负责追溯。最小可用版本只改入口与索引，不先建设自动分类器、模型服务或新任务数据库。

前提：会话能够读取仓库共享指令和文件。若运行环境不加载项目指令，仓库本身无法保证 agent 执行；此时以独立冷启动验收识别适配问题，再补该环境的薄入口。不要声称任何模型、任意聊天或压缩后的会话都可被仓库强制约束。

```text
用户当前任务 + 项目现有上下文
                |
        AGENTS.md 简短选择规则
                |
       skills/README.md 任务索引
                |
    主技能 + 必要专项 + 项目约束
                |
        既有证据与产物 + 完成边界

next / 工作区交接 ----> 同一任务索引
```

## 选择规则

将以下要求置于AGENTS开头，先于长篇采集细则：每次实质SEO任务开始或切换任务类型时，先查看任务索引，选择当前主技能并读取正文；缺少证据、特定平台或专项问题时再补相应模块。技能路径、来源、适用条件和可跳过条件由索引说明。

不要求每条消息重读、不为一处措辞修正启动完整SERP研究。对于同一任务已经加载且仍可访问的正文，可直接续接；压缩后无法确认规则时重新读取最小必要部分。此前研究是否可复用，以目标、市场、日期、范围和证据质量判断，不能只看存在一个brief文件。

开始时用一句话说明选择与用途；结束时在正常交付中说明关键产物和缺口。用户不需要额外批准技能选择。当前用户授权优先，其次为仓库与项目约束；项目技能补充店铺事实和交付形式，不替代通用研究、写作与验收方法。遇到技能旧规则与现行约束冲突，按现行约束执行并标记冲突。

## 任务索引与灵活组合

`skills/README.md` 是唯一人工任务路由索引，按读者任务组织；工作流继续保留阶段映射，不另建第二套阶段状态。索引只给短描述和路径，不预加载63份正文。

| 当前任务 | 主流程 | 需要时补充 |
|---|---|---|
| 关键词机会、意图、现有owner | keyword-deep-dive | semantic-gap-analysis、项目证据 |
| 话题群结构、去重、内链分工 | topic-cluster-planning | keyword-deep-dive、项目交付技能 |
| 起草前的研究与写作规格 | content-brief | expert-interview，若独有经验确有缺口 |
| 已批准brief的新稿 | write-content | reader-experience-review、生产审阅 |
| 实质改写旧文 | improve-content，经适配后可执行 | page-audit，若诊断尚未完成 |
| 仅审读、局部精修 | reader-experience-review | 有具体缺口才升级为改稿或审计 |
| 内容生产审阅 | content-production-review，拟新增适配模块 | schema、项目发布检查 |
| 技术问题或受控审计 | technical-audit | schema、sitemap、images；按任务限定范围 |
| 内容可信度与覆盖 | eeat-audit、semantic-gap-analysis，按问题选主项 | page-audit |
| 外链与周期监测 | backlinks、linkbuilding、drift，按问题选主项 | 同源可比证据 |
| 电商、国际化或其他专项 | 先定位对应专项并检查适配状态 | reference模块只提炼方法，不直接执行旧命令 |
| CLI／UI功能开发或采集器修复 | 工程流程 | 仅当解释SEO规则或修改专业契约时读相关SEO技能 |

允许先后组合，也允许只执行适用步骤。没有SERP访问就如实交付“站内证据与候选来源研究”，标记SERP观察未完成；不能将其写成完整deep dive，也不能为了打勾伪造观察。

## 三来源能力适配

在技能索引中区分 `ready`（已按Workbench边界适配，可执行）和 `reference`（保留材料，只供方法提炼）。状态表示兼容性，不表示来源声誉、SEO效果或已完成用户任务。专项状态不明时按reference处理，明确具体阻碍后再适配。

第一批处理当前高频内容链：

- 保留SuperSEO研究→集群→brief→写作路径；修正 `improve-content` 的密度／字数配额，与现行write-content和项目约束对齐。检查强制逐题访谈／重复确认，已有事实或授权时续接。
- 新建 `skills/content-production-review/SKILL.md`，提炼SEO Machine editor、internal-linker、meta-creator、seo-optimizer、cro-analyst的成熟检查：任务完成度、事实、owner与内链、元信息一致性和合适的下一步。禁止机械字数／密度、虚构经验、所有文章强插CTA和未经授权发布；不恢复旧slash executor。标明具体来源文件及归属许可。
- Claude SEO核心继续使用Workbench采集和证据契约；专项模块先列reference及原因，不一口气激活旧脚本、500页爬取或旧专家编排。首次有对应任务时做针对性适配，适配改动单独commit并验证。

来源原文保留归属；ready模块负责现行契约。修改一条共享质量标准时，同步检查全部ready模块，不要求把归档原文全部改写为运行说明。

## 持续任务入口

修改 `seo_workbench/cli.py::cmd_next` 与 `workflow.py` 的交接构建：不论是否存在pending step，都返回只读 `guidance`，包含 `skill_index: skills/README.md` 和存在时的项目AGENTS路径；有步骤时保留既有skill/context/output契约。

`pending:false` 继续仅表示当前阶段没有待办步骤，不暗示队列为空或所有工作结束。guidance提示查看现有内容队列、最近交付和用户当前要求，由agent选择任务；不自动选中或修改某个队列项、不切阶段、不启动抓取或发布。

`keyword_workspace.py` 与 `content_briefs.py` 的handoff补同一索引引用；索引的任务判断优先于“新稿／修订／发布准备全部映射write-content”的笼统fallback。初期不新增自然语言分类CLI，避免同义词规则代替agent判断。

## 产物验收与证据

在既有报告／brief／审阅产物中增加简短的“方法与边界”：主技能路径、采用步骤、复用证据、未完成项与理由。逐篇共用方法时在话题群manifest或总报告记录一次，篇目只写差异；不创建单独全局调用日志，不重复内容队列状态。

结构校验只验证索引路径、工作流映射及契约形状，不能证明模型已经读懂技能。专业验收检查实际产物与证据：有无query／owner、来源与观察范围、已核事实、内链依据、必要的读者体验审阅。缺少真实SERP观察应可见为未完成，已有有效观察则可以复用。

## 分层施工与验收

每层一个或一组独立Conventional Commit，先完成必要层，再扩大范围；每层都同步个人main和公司工作分支。

1. **入口与任务索引。** 修改AGENTS.md、skills/README.md和CLAUDE.md的薄适配引用。先做无用户技能提示的冷启动演练；若仍需提醒，修入口，不增加复杂运行层。
2. **高频能力适配。** 修改improve-content，新增content-production-review及必要来源说明，检查write-content与审阅规则冲突。用一份已有稿件做局部审阅，证明不会强制全文重写、字数配额或发布。
3. **持续任务交接。** 修改workflow.py、cli.py、keyword_workspace.py、content_briefs.py，补tests/test_state_workflow.py及现有相应handoff测试。验证有pending、无pending、有队列、无队列、无项目AGENTS均可用，且没有状态写入或新采集。
4. **方法记录与专业验收。** 更新相关ready技能的产物契约和必要模板。缺证据、复用证据、仅局部修订、用户限制范围均必须能如实记录，不把步骤省略自动判为失败。

预计累计超过8个文件，按层限制变更；不添加服务、依赖、密钥、账户或模型API。

验收提示不出现skills、skill名或“按工作流执行”：关键词机会、旧文更新、只做段落审读、仅诊断某技术问题各一次；另补当前阶段没有pending的情况。每个独立会话记录首次动作是否自主选读、选择是否合适、产物是否越界。该人工行为验收是实施阶段的必要证据，单元测试不能替代。

命令验证按改动层级运行：`./seo --project <id> validate --json`；第3层运行 `.venv/bin/python -m pytest tests/test_state_workflow.py` 和改到的handoff模块既有测试；所有层运行 `git diff --check`。不为纯文档修改新增镜像式测试。

## 双分支交付与回滚

本工作会话已核实origin为个人远端、hexcal为公司远端，当前公司分支为 `codex/hexcal-asset-library`；以后每轮重新核对，不把地址写死进执行器。

先在公司工作分支按层提交公共改动，获取两远端最新状态；切个人main并fast-forward到origin/main，只cherry-pick该层共享提交，验证后push origin main；再回公司分支，验证并push当前公司分支。最终留在公司分支。出现冲突逐项保留两分支差异，不整枝合并、不推送无关历史或店铺私有数据。

已同步层的回滚使用各分支对应提交的revert，按相同顺序推送；不force push，不触碰店铺证据或阶段状态。公共文档与流程问题留docs，实际业务交付继续留所属项目。
