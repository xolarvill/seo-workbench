# Skills 能力归属与一级目录迁移

日期：2026-10-29（Asia/Shanghai）。本次执行已批准计划的第 2、3 步。来源基线见 [skill-sources.md](skill-sources.md)，逐文件迁移表见 [skill-layout-migration.json](skill-layout-migration.json)。

## 能力归属决定（第 2 步）

所有可调用方法统一为 `skills/<能力名>/SKILL.md`。来源继续由文件清单和许可证记录，不再承担目录分类。64 个原技能正文形成 60 个唯一入口；六份原入口正文保存为配套参考，新增 site-audit 和 seo 两份 Workbench 入口。

| 主入口 | 合并的材料 | 负责范围 |
|---|---|---|
| site-audit | Claude SEO 的 seo-audit 与 SEO Machine 的 seo-audit | 多页面／全站诊断的范围、证据清点、专项组合和整体优先级；根据任务选择专项，不安装原调度器 |
| page-audit | 现有 page-audit 与 Claude SEO 的 seo-page | 一个 URL 的页面／内容／竞争审阅及技术检查；仅技术问题可使用该模式，不强制开展竞争研究 |
| schema | 现有 schema 与 SEO Machine 的 schema-markup | 结构化数据检测、校验、生成和不同站点栈的实现方式 |
| programmatic-seo | SEO Machine 的 programmatic-seo 与 Claude SEO 的 seo-programmatic | 数据驱动页面的选型、模板、数据质量、链接和上线后的索引诊断 |
| seo | 保留原 seo 的范围导航职责，原调度正文转为来源参考 | 将宽泛 SEO 问题路由到明确能力；使用 Workbench 的现有采集与证据契约 |

以下互补能力继续独立：project-context 管项目事实与边界，product-marketing-context 管营销定位；content-strategy 管内容组合与商业方向，topic-cluster-planning 管页面归属与集群，seo-cluster 管查询分组方法；copy-editing 管营销文案编辑，reader-experience-review 管文章的读者理解。它们的名称相近不等于方法相同。

现有其他入口保留名称，直接迁入一级目录。frontmatter 的 name 与目录名统一，包括 technical-audit 原来的 seo-technical 标识。growth-lead 改成标准的 `skills/growth-lead/SKILL.md`。

## 文件迁移决定（第 3 步）

- 配套 references、assets、LICENSE 随所属能力迁移；合并模块的参考材料放入主入口的 references，保留原文、来源与独立许可证。
- 原 SEO Machine 的 11 份专家材料和 24 份流程文档移到 `third_party/skill-history/seomachine/`。这次只改变位置及路径引用，专业方法整理留给第 4 步；这些文档仍是方法参考，不是已安装执行器。
- 将已存在的相对链接按旧目标与新位置重新计算；更新当前文档、工作流和交接提示的路径。原先缺失的工具引用仍按缺口登记，由第 5 步处理。
- 保持既有核心技能的路径，使现有 CLI/workflow 调用方尽量无需变更。旧外围路径不保留重复 SKILL.md 或软链接；迁移表承担历史路径查询。
- 来源清单保留稳定 ID、原始上游路径、首次本地记录与旧路径；更新当前路径、owner、内容指纹和引用关系。保留原文件后增加主入口时，原记录指向参考文件，新主入口单独登记为 Workbench 组合方法。

本轮不改写作配方、不接收新的上游正文、不新增采集器、不改业务项目状态。所有原文件都有唯一去向；历史报告中的原路径作为当时记录保留，可通过本迁移表查询当前位置。

## 验收与回滚

迁移前已添加三个结构回归，并确认旧布局全部失败：一级入口与唯一 name、来源记录及文件保存、既有本地依赖的目标保全。独立只读基线会话能选用现有方法，但为全站诊断同时读取两份 seo-audit；它识别了旧执行配方的边界，本轮不将这个样本描述为行为失败。

迁移后核对 364 个原文件的去向、60 个入口、来源 ID 和哈希；检查迁移前有效的本地引用未失效，运行相关状态／API 回归与显式项目 validate。对站点、单页、schema、程序化页面场景做只读方法选取检查。结构验证不代表已完成网站诊断或写作质量升级。

第 2 步与第 3 步分别提交。回滚采用对应 commit 的 revert；项目私有技能与业务数据不参与迁移。

### 本次执行结果

- 第 2 步归属与迁移决定提交为 `f80ef1f`。第 3 步保留全部 364 个原文件及其稳定来源 ID，增加两份 Workbench 组合入口，当前清单覆盖 366 个文件。
- 60 个 SKILL.md 均位于同一目录层级，frontmatter name 与目录名一致且唯一；索引直接链接全部入口。
- 11 份专家方法、24 份流程文档迁入来源参考区；六份被合并的原入口保留在对应主能力的 references。许可证和 FLOW 的细分归属随记录保留。
- 原来有效的 218 处字面本地依赖，其迁移目标全部存在。按原文件与原目标核对迁移后的候选清单，没有新增缺失字面目标。旧缺口继续由清单记录。
- 28 项结构、状态、workspace 和关键词交接回归通过；显式项目 validate 返回 ok=true，保留既有 project_dir.missing 目录 warning。两个新增入口通过 skill-creator 的结构校验。
- 暂存时发现原有不带根锚点的忽略规则会漏收 39 个新位置文件；新增回归先复现，再将三处上游 clone 目录规则限定在仓库根目录，保证迁移参考材料和许可证进入 Git。
- 两个独立只读会话覆盖全站诊断和三个专项场景：单 URL 技术检查、静态 JSON-LD 实现规划、生成页面的规划与诊断。均从当前入口找到相关正文／参考，并按请求跳过联网、采集和写入。单页技术模式没有扩展到 SERP 研究。
- 独立架构复核未发现可行动问题。该抽样验证选取与范围控制，不代表完成任何站点审计或后续写作规则升级。

实际运行的回归命令：

```bash
.venv/bin/python -m pytest tests/test_skill_layout.py tests/test_state_workflow.py \
  tests/test_ui.py::test_workspace_does_not_schedule_an_agent_step \
  tests/test_keyword_workspace.py::test_stage_progression_and_handoff_paths -q
./seo --project hexcal validate --json
```

本次输出：`28 passed`；来源清单、索引与迁移记录的本地链接检查通过。新增的目录约束回归以当前来源清单为准，原迁移表只用于核对来源 ID 和路径历史，允许后续维护更新当前路径与入口数量。

## 全部入口的归属表

| 原入口 | 统一入口 | 处理 |
|---|---|---|
| `skills/backlinks/SKILL.md` | `skills/backlinks/SKILL.md` | 原位保留 |
| `skills/claude-seo-extra/seo-audit/SKILL.md` | `skills/site-audit/SKILL.md` | 保留原文为参考 |
| `skills/claude-seo-extra/seo-cluster/SKILL.md` | `skills/seo-cluster/SKILL.md` | 迁移 |
| `skills/claude-seo-extra/seo-competitor-pages/SKILL.md` | `skills/seo-competitor-pages/SKILL.md` | 迁移 |
| `skills/claude-seo-extra/seo-content/SKILL.md` | `skills/seo-content/SKILL.md` | 迁移 |
| `skills/claude-seo-extra/seo-dataforseo/SKILL.md` | `skills/seo-dataforseo/SKILL.md` | 迁移 |
| `skills/claude-seo-extra/seo-ecommerce/SKILL.md` | `skills/seo-ecommerce/SKILL.md` | 迁移 |
| `skills/claude-seo-extra/seo-flow/SKILL.md` | `skills/seo-flow/SKILL.md` | 迁移 |
| `skills/claude-seo-extra/seo-geo/SKILL.md` | `skills/seo-geo/SKILL.md` | 迁移 |
| `skills/claude-seo-extra/seo-google/SKILL.md` | `skills/seo-google/SKILL.md` | 迁移 |
| `skills/claude-seo-extra/seo-hreflang/SKILL.md` | `skills/seo-hreflang/SKILL.md` | 迁移 |
| `skills/claude-seo-extra/seo-image-gen/SKILL.md` | `skills/seo-image-gen/SKILL.md` | 迁移 |
| `skills/claude-seo-extra/seo-local/SKILL.md` | `skills/seo-local/SKILL.md` | 迁移 |
| `skills/claude-seo-extra/seo-maps/SKILL.md` | `skills/seo-maps/SKILL.md` | 迁移 |
| `skills/claude-seo-extra/seo-page/SKILL.md` | `skills/page-audit/SKILL.md` | 保留原文为参考 |
| `skills/claude-seo-extra/seo-plan/SKILL.md` | `skills/seo-plan/SKILL.md` | 迁移 |
| `skills/claude-seo-extra/seo-programmatic/SKILL.md` | `skills/programmatic-seo/SKILL.md` | 保留原文为参考 |
| `skills/claude-seo-extra/seo-sxo/SKILL.md` | `skills/seo-sxo/SKILL.md` | 迁移 |
| `skills/claude-seo-extra/seo/SKILL.md` | `skills/seo/SKILL.md` | 保留原文为参考 |
| `skills/content-brief/SKILL.md` | `skills/content-brief/SKILL.md` | 原位保留 |
| `skills/drift/SKILL.md` | `skills/drift/SKILL.md` | 原位保留 |
| `skills/eeat-audit/SKILL.md` | `skills/eeat-audit/SKILL.md` | 原位保留 |
| `skills/expert-interview/SKILL.md` | `skills/expert-interview/SKILL.md` | 原位保留 |
| `skills/featured-snippet-optimizer/SKILL.md` | `skills/featured-snippet-optimizer/SKILL.md` | 原位保留 |
| `skills/headless-precheck/SKILL.md` | `skills/headless-precheck/SKILL.md` | 原位保留 |
| `skills/images/SKILL.md` | `skills/images/SKILL.md` | 原位保留 |
| `skills/improve-content/SKILL.md` | `skills/improve-content/SKILL.md` | 原位保留 |
| `skills/keyword-deep-dive/SKILL.md` | `skills/keyword-deep-dive/SKILL.md` | 原位保留 |
| `skills/linkbuilding/SKILL.md` | `skills/linkbuilding/SKILL.md` | 原位保留 |
| `skills/page-audit/SKILL.md` | `skills/page-audit/SKILL.md` | 原位保留 |
| `skills/project-context/SKILL.md` | `skills/project-context/SKILL.md` | 原位保留 |
| `skills/reader-experience-review/SKILL.md` | `skills/reader-experience-review/SKILL.md` | 原位保留 |
| `skills/schema/SKILL.md` | `skills/schema/SKILL.md` | 原位保留 |
| `skills/semantic-gap-analysis/SKILL.md` | `skills/semantic-gap-analysis/SKILL.md` | 原位保留 |
| `skills/seo-machine-pipeline/skills/ab-test-setup/SKILL.md` | `skills/ab-test-setup/SKILL.md` | 迁移 |
| `skills/seo-machine-pipeline/skills/analytics-tracking/SKILL.md` | `skills/analytics-tracking/SKILL.md` | 迁移 |
| `skills/seo-machine-pipeline/skills/competitor-alternatives/SKILL.md` | `skills/competitor-alternatives/SKILL.md` | 迁移 |
| `skills/seo-machine-pipeline/skills/content-strategy/SKILL.md` | `skills/content-strategy/SKILL.md` | 迁移 |
| `skills/seo-machine-pipeline/skills/copy-editing/SKILL.md` | `skills/copy-editing/SKILL.md` | 迁移 |
| `skills/seo-machine-pipeline/skills/copywriting/SKILL.md` | `skills/copywriting/SKILL.md` | 迁移 |
| `skills/seo-machine-pipeline/skills/email-sequence/SKILL.md` | `skills/email-sequence/SKILL.md` | 迁移 |
| `skills/seo-machine-pipeline/skills/form-cro/SKILL.md` | `skills/form-cro/SKILL.md` | 迁移 |
| `skills/seo-machine-pipeline/skills/free-tool-strategy/SKILL.md` | `skills/free-tool-strategy/SKILL.md` | 迁移 |
| `skills/seo-machine-pipeline/skills/growth-lead-SKILL.md` | `skills/growth-lead/SKILL.md` | 迁移 |
| `skills/seo-machine-pipeline/skills/launch-strategy/SKILL.md` | `skills/launch-strategy/SKILL.md` | 迁移 |
| `skills/seo-machine-pipeline/skills/marketing-ideas/SKILL.md` | `skills/marketing-ideas/SKILL.md` | 迁移 |
| `skills/seo-machine-pipeline/skills/marketing-psychology/SKILL.md` | `skills/marketing-psychology/SKILL.md` | 迁移 |
| `skills/seo-machine-pipeline/skills/onboarding-cro/SKILL.md` | `skills/onboarding-cro/SKILL.md` | 迁移 |
| `skills/seo-machine-pipeline/skills/page-cro/SKILL.md` | `skills/page-cro/SKILL.md` | 迁移 |
| `skills/seo-machine-pipeline/skills/paid-ads/SKILL.md` | `skills/paid-ads/SKILL.md` | 迁移 |
| `skills/seo-machine-pipeline/skills/paywall-upgrade-cro/SKILL.md` | `skills/paywall-upgrade-cro/SKILL.md` | 迁移 |
| `skills/seo-machine-pipeline/skills/popup-cro/SKILL.md` | `skills/popup-cro/SKILL.md` | 迁移 |
| `skills/seo-machine-pipeline/skills/pricing-strategy/SKILL.md` | `skills/pricing-strategy/SKILL.md` | 迁移 |
| `skills/seo-machine-pipeline/skills/product-marketing-context/SKILL.md` | `skills/product-marketing-context/SKILL.md` | 迁移 |
| `skills/seo-machine-pipeline/skills/programmatic-seo/SKILL.md` | `skills/programmatic-seo/SKILL.md` | 迁移 |
| `skills/seo-machine-pipeline/skills/referral-program/SKILL.md` | `skills/referral-program/SKILL.md` | 迁移 |
| `skills/seo-machine-pipeline/skills/schema-markup/SKILL.md` | `skills/schema/SKILL.md` | 保留原文为参考 |
| `skills/seo-machine-pipeline/skills/seo-audit/SKILL.md` | `skills/site-audit/SKILL.md` | 保留原文为参考 |
| `skills/seo-machine-pipeline/skills/signup-flow-cro/SKILL.md` | `skills/signup-flow-cro/SKILL.md` | 迁移 |
| `skills/seo-machine-pipeline/skills/social-content/SKILL.md` | `skills/social-content/SKILL.md` | 迁移 |
| `skills/sitemap/SKILL.md` | `skills/sitemap/SKILL.md` | 原位保留 |
| `skills/technical-audit/SKILL.md` | `skills/technical-audit/SKILL.md` | 原位保留 |
| `skills/topic-cluster-planning/SKILL.md` | `skills/topic-cluster-planning/SKILL.md` | 原位保留 |
| `skills/write-content/SKILL.md` | `skills/write-content/SKILL.md` | 原位保留 |
