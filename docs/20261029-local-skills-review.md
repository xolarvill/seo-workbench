# 本地 skills 主动发现、写作质量与上游更新复审

审阅日期：2026-10-29（Asia/Shanghai）。范围：仓库指令、技能索引、技能正文、引用路径、CLI/API 契约及三个原始上游。此次交付为审阅与升级建议，未修改技能行为。

## 结论

上次改造完成了最关键的入口调整：agent 可以从当前目标主动选择本地方法，不再由旧阶段决定下一步。当前问题集中在方法正文的一致性、外围引用的完整性和写作标准。继续增加禁用词，对解决“免责式写法”的帮助有限；应当明确每段话服务的读者问题，并把不必要的防御性表达列入正文审阅标准。

优先处理三个问题：

1. 把 reader-experience-review 已有的“隐形争论”判断落实为可执行的删改标准，同时同步 write-content、improve-content 与实际会被选读的编辑材料。
2. 清理固定密度、刻意模仿人类节奏、强制反常识开场等互相冲突的配方。
3. 修复外围技能的引用，并记录上游版本和本地改动，之后按内容选择升级。

## 1. 上次改动的复核

### 当前可直接验证的结果

| 检查项 | 当前结果 | 依据 |
|---|---|---|
| 主动发现入口 | 已实现 | AGENTS 开头要求先读 skills/README，再按目标选读正文；索引允许组合和继续搜索 |
| 去除阶段调度 | 已实现 | next 命令被拒绝；status 提供 skill_index；workspace 不再输出 next |
| 接续已有工作 | 有明确规则 | 指令要求恢复决定、产物、证据与缺口，旧步骤完成不等于研究完成 |
| 局部审稿的入口 | 已实现 | 索引单列 reader-experience-review；write-content 和 improve-content 均要求交稿前使用 |
| 三来源材料的可发现性 | 核心入口清楚，外围较弱 | SEO Machine 主要按来源介绍，营销/CRO 等具体任务缺少直接索引行 |
| 全部正文的适配 | 尚未完成 | 固定密度、旧工具路径和强制拟人化规则仍在 |
| validate 对方法的检查 | 仅覆盖结构契约 | validation.py 检查工作流映射和路径，不检查专业方法是否完整应用、文风是否合格 |

本次重新运行：

```bash
.venv/bin/python -m pytest tests/test_state_workflow.py \
  tests/test_ui.py::test_workspace_does_not_schedule_an_agent_step \
  tests/test_keyword_workspace.py::test_stage_progression_and_handoff_paths -q
./seo --project hexcal validate --json
```

结果：23 项测试通过；显式项目 validate 为 ok=true，另有一项 project_dir.missing 目录 warning。未指定项目的 validate 指向尚未初始化的 default，因此返回 state.not_found；不能用这个调用判断已有项目的结构状态。

2026-10-26 的[验收记录](20261026-agent-led-workbench-acceptance.md)还保存了两个未点名技能的独立会话抽样。本次复核了现行实现和该记录，没有重新做独立会话实验。当前证据支持“入口改造仍然成立”；尚不足以给出日常自主调用率或写作改善幅度。后续应从真实交付抽样检查实际选读与应用情况。

### 仍存在的发现与应用缺口

- 本地 skills 通过仓库指令被发现，本会话的全局技能清单并未自动列出仓库的全部方法。跨 agent 的关键仍是执行 AGENTS 的读索引规则。
- `growth-lead-SKILL.md` 是非标准文件名。当前索引建议寻找 SKILL.md，按这种方式搜索会漏掉它；应改成标准目录入口或显式列出。
- 4 个 SEO Machine 技能正文有 **25 处失效的相对 Markdown 引用**，对应 20 个不同目标：analytics-tracking、paid-ads、email-sequence、referral-program 指向未保留的 `../../tools/REGISTRY.md` 或 `../../tools/integrations/*.md`。这是实际文件缺失，不包含示例网址和占位链接。
- Claude SEO 外围模块仍引用 `scripts/fetch_page.py`、`scripts/google_auth.py`、`skills/seo/references/...` 等原仓库位置。适用方法可以提炼，命令不能直接照用；更新上游后还会出现 `${CLAUDE_PLUGIN_ROOT}` 依赖。

## 2. 当前技能分类

仓库级共有 **63 个标准 SKILL.md，加 1 个 growth-lead-SKILL.md，共 64 个技能正文**；另保留 **11 份专家方法、24 份流程文档**。专家和流程不是已安装的执行器。项目目录另有 3 个店铺专属 SKILL.md，独立计数，不扩展到其他店铺。

### 2.1 核心入口：20 个

目录均为 `skills/<名称>/SKILL.md`。

| 类别 | 技能 | 用途 |
|---|---|---|
| 项目上下文 | project-context | 受众、定位、品牌声音、事实与证据 |
| 研究与结构 | keyword-deep-dive、topic-cluster-planning、semantic-gap-analysis | 意图、关键词机会、内容归属、集群与覆盖缺口 |
| 写作准备 | content-brief、expert-interview | 写作范围、提纲、第一手知识提取 |
| 写作与改稿 | write-content、improve-content、reader-experience-review | 新稿、旧文更新、逐段阅读体验审阅 |
| 内容诊断 | page-audit、eeat-audit、featured-snippet-optimizer | 页面价值、可信度、结果格式与简短答案 |
| 技术 | technical-audit、headless-precheck、schema、sitemap、images | 抓取、渲染、结构化数据、站点地图与图片 |
| 变化监测 | drift | 比较可比快照并识别变化 |
| 外链 | backlinks、linkbuilding | 外链证据与获取策略 |

来源构成：11 个 SuperSEO 方法、6 个 Claude SEO 适配入口、3 个 Workbench 本地方法（project-context、headless-precheck、reader-experience-review）。

### 2.2 Claude SEO 专项：18 个

目录为 `skills/claude-seo-extra/<名称>/SKILL.md`。

| 类别 | 技能 |
|---|---|
| 总览、规划与框架 | seo、seo-audit、seo-plan、seo-flow |
| 页面、内容与架构 | seo-page、seo-content、seo-cluster、seo-competitor-pages、seo-programmatic |
| 电商、国际化、本地与体验 | seo-ecommerce、seo-hreflang、seo-local、seo-maps、seo-sxo |
| AI 搜索与图片生成 | seo-geo、seo-image-gen |
| 数据源方法 | seo-google、seo-dataforseo |

这些是专项参考材料。尤其 seo-audit 的旧脚本、专家调度和大规模抓取配方，需要经过 Workbench 采集与授权规则适配。

### 2.3 SEO Machine：26 个

标准目录为 `skills/seo-machine-pipeline/skills/<名称>/SKILL.md`；growth-lead 为前述非标准文件。

| 类别 | 技能 |
|---|---|
| 内容与文案 | product-marketing-context、content-strategy、copywriting、copy-editing |
| 转化与实验 | page-cro、form-cro、popup-cro、signup-flow-cro、onboarding-cro、paywall-upgrade-cro、ab-test-setup |
| SEO 与竞品页面 | seo-audit、programmatic-seo、schema-markup、competitor-alternatives |
| 传播与获客 | email-sequence、social-content、paid-ads |
| 增长与商业策略 | growth-lead、launch-strategy、pricing-strategy、referral-program、free-tool-strategy、marketing-ideas、marketing-psychology |

11 份专家方法：editor、seo-optimizer、meta-creator、internal-linker、keyword-mapper、content-analyzer、cro-analyst、headline-generator、cluster-strategist、landing-page-optimizer、performance。

24 份流程文档按用途分组：

- 研究：research、research-gaps、research-topics、research-performance、research-trending、research-serp、research-ai-citations、priorities。
- 内容生产：article、write、rewrite、optimize、analyze-existing、cluster、content-calendar、performance-review。
- 落地页：landing-research、landing-write、landing-audit、landing-competitor、landing-publish。
- 交付与再利用：publish-draft、repurpose、scrub。

### 2.4 项目专属：3 个

当前为 hexcal-topic-cluster、hexcal-material-library、hexcal-feishu-reporting，分别服务该店铺的话题群、素材库与飞书汇报。它们补充业务事实和交付方式；通用研究和写作质量仍由共享方法承担。

## 3. “免责式写法”的具体成因

### 3.1 reader-experience-review 已经抓到了问题，但删改门槛不够明确

现有正文明确检查 invisible arguments 和 unnecessary self-justification，也写了“用有依据的主张代替宣布遵守每条内部禁令”。这部分应保留。

目前的判断仍允许“plausible misunderstanding”作为反驳一个未引入观点的理由，范围较宽；Must fix 主要列出泄漏、严重跳跃、误导和病句。一个事实无错、逻辑完整的防御性段落，很容易被归为可保留的 caution 或轻微风格偏好。校准示例也更充分地解释了怎样保留谨慎说明，较少覆盖那种通篇都在预防追责的文章。

建议加入明确的处理规则：

1. **先确定读者此刻的任务。** 新增限制或反驳应能指向该任务中的具体选择、操作或理解。
2. **反驳要有对象。** 原文已提出、用户明确要求比较、或有可指认的常见错误时才处理；“可以想象有人会误会”不足以添加一段辩白。
3. **把限制写成可用条件。** 直接说明适用范围和检查方法；不要求读者先理解作者没有承诺什么。
4. **删除无读者收益的自证。** 同一范围已在来源、条件或图注中交代，正文再宣布“不能证明”“不构成保证”应删除或合并。
5. **通读整篇的说话对象。** 单句都有依据，但连续多段都在纠正未出现的观点，仍需重写衔接和主张。

安全、兼容性、利益披露等事实应保留在读者需要作决定的位置，并说清楚读者应当怎么做。

### 3.2 写作主技能仍在制造另一种模板感

`write-content/SKILL.md:77–106` 仍要求：dramatically 变化句长、不允许连续三句长度相似、主动插入旁白和跑题、禁止三项并列改用两项或四项。这些是固定的模仿手段，与 reader-experience-review 的“不要强制人类怪癖”冲突。

`improve-content/SKILL.md:60–61` 仍要求约 2% 关键词密度、每千字 3–5 条内链及固定摘要长度；write-content 已移除了密度和链接配额。两条常用生产路径标准不一致。

`write-content/references/voice-injection-playbook.md:135–145` 鼓励以“多数指南哪里错了”表达观点；SEO Machine 的 editor 要求每篇 2–3 个有名字和细节的小故事，并偏好挑衅或反常识开场。copy-editing 则有专门的反对意见处理。它们在真实异议、访谈和故事存在时有用，默认套用会把文章写成对假想对手的回应。

这是技能层面的诱因分析；本轮没有把这些规则与某篇已发布文章建立因果对应。

### 3.3 建议的写作标准

主写作与编辑入口共同遵循以下顺序：读者问题 → 有依据的回答 → 必要解释或例子 → 影响操作的条件。词表与句式提示作为查阅线索，不能强迫文章表现某种“人类节奏”。

以下是构造的校准例句，未摘自实际文章：

| 原句 | 建议写法 | 理由 |
|---|---|---|
| “这不是为了追求社交媒体上完美的桌面，也不是说所有人都需要添置配件。” | “先把每天要用的物品放进顺手的位置，再决定要添什么。” | 给出行动，删掉读者没提出的动机争论 |
| “这些建议并不构成对任何显示器兼容性的保证。” | “下单前核对支架的 VESA 孔距、承重范围和显示器去底座重量。” | 把宽泛辩白改成可执行检查；具体产品仍需核对自身要求 |
| “USB-C 插口不一定支持视频输出。” | 保留；需要时补充查哪里确认 | 这直接影响连接选择，否定句本身没有问题 |
| 每个例子后重复“我们没有测试这个配置” | 在确有混淆风险的位置标明“布局示例”，并准确标注资料来源 | 提供真实信息，不把内部审稿记录写进每一段 |

## 4. 上游更新核查

通过 GitHub 连接器读取默认分支提交，并按固定 SHA 比对正文。共比对 **61 个有上游对应的技能正文**：SuperSEO 11、Claude SEO 24（18 个外围加 6 个核心适配）、SEO Machine 26；另比对 SEO Machine 11 份专家材料和 24 份流程文档。Workbench 原生方法不计入上游比对。

本地缺少技能 vendor 基线 SHA 清单，因此以下“有差异”包含本地适配和上游后续修改，不能全部算作落后更新。参考文件仅对本次议题所需内容做了抽查，没有逐文件认证整套 references。

| 来源 | 核查的上游版本 | 对比结果 |
|---|---|---|
| SuperSEO | v0.2.1，2026-09-03；`9cf22cc065a294bf0077ea6af6b4ea0eb7f89cdc` | 11 正文中 1 相同、10 有差异；差异混合了本地规则改进和未吸收更新 |
| Claude SEO | 正文标注 v2.5.0，发布于 2026-10-22；默认分支 `6be93f45064ffbadced572b5d5c95f55fd263af0` | 24 个对应正文均有差异；本地不少材料仍标注 1.9.6 |
| SEO Machine | 默认分支 2026-10-23；`120e7b46dc07c98382cd4f68ac5b6515ab9f2604` | 26 技能正文、11 专家材料相同；24 流程中 23 相同，repurpose 有差异 |

### 4.1 SuperSEO：选择吸收执行方式和事实依据规则

[v0.2.1 更新说明](https://github.com/inhouseseo/superseo-skills/blob/9cf22cc065a294bf0077ea6af6b4ea0eb7f89cdc/CHANGELOG.md)主要补充研究依据要求，以及自主运行时跳过写作确认和访谈的分支。

可吸收：

- 当用户已要求直接交稿时，内容类型选择不再卡住等待确认。当前本地 write-content 仍写着 Wait for confirmation。
- 无法补充访谈时，使用已有研究继续写，缺失的第一手材料记录给编辑或任务产物；不要求把缺口声明变成文章正文。
- 抓取失败时不猜测竞品内容；具体数字、名称、引用必须有实际来源。与本地既有事实规则合并即可。

不建议整包覆盖：上游仍保留固定密度、机械节奏和部分过强排名推断。本地 page-audit、content-brief、write-content 已做过重要修正，直接覆盖会退回旧规则。关于 FAQ/AI 引用的上游解释也应逐项核对当前官方资料后再适配。

### 4.2 Claude SEO：值得提炼的纠错较多

[v2.5.0 更新说明及历史](https://github.com/AgriciDaniel/claude-seo/blob/6be93f45064ffbadced572b5d5c95f55fd263af0/CHANGELOG.md)包含触发描述细化、关键词密度移除、图片加载识别、内容依据和外部数据处理等变化。

建议分项适配：

- **seo-page / seo-content**：移除密度目标，区分作者身份与实际内容质量，缩窄触发范围。
- **图片诊断**：识别常见 JS lazy loader，避免只看原生 loading 属性就判定未延迟加载。若本地采集缺少字段，应另做有证据的实现，不在方法里假装已能检测。
- **元数据审阅**：检查 description 是否只是重述 title 加模板 CTA，可用于改善批量生成的重复语气。
- **结构化数据与图片政策参考**：逐条核对官方状态和当前本地规则，吸收新增纠错，保留本地证据资格与字段采集边界。
- **输入信任与事实新鲜度**：提炼外部材料视作数据、事实附核查日期和来源的做法；仓库已有相应边界，避免每个文件重复铺设长警告。

新增的 `seo-content-brief` 有两个有用方法：区分旧页的“保留/加强/新增”，以及让选题符合网站实际能提供的产品或服务。可并入现有 content-brief。它仍带有分节字数、固定标题长度和竞品排除配方，不宜直接增加一个竞争入口。

新增 `seo-agentic` 面向网站是否便于外部 AI agent 浏览，涉及可访问性、访问策略和发现协议；它与“本项目 agent 是否主动读 skills”是两个课题。可在出现网站 agent 可用性需求时独立研究，本轮不列为优先升级。

不建议引入新一套安装器、凭证存储、调度器或默认评分系统。上游 humanize 的词语替换及字符清理也无法处理隐形争论，不应成为本项目的写作验收方法。

### 4.3 SEO Machine：当前没有必要做技能正文升级

[固定版本的技能目录](https://github.com/TheCraigHewitt/seomachine/tree/120e7b46dc07c98382cd4f68ac5b6515ab9f2604/.claude/skills)与本地 26 个技能正文一致，11 份专家材料也一致。

唯一流程差异是 [repurpose](https://github.com/TheCraigHewitt/seomachine/blob/120e7b46dc07c98382cd4f68ac5b6515ab9f2604/.claude/commands/repurpose.md)新增保存后自动执行 /scrub。它侧重字符清理、破折号与所谓水印，既不能处理读者关系，也依赖未安装的原执行链，不建议吸收。现有本地 scrub 材料本身也值得降级为历史参考，不能当作写作质量方法。

## 5. 建议的实施顺序与验收

| 层级 | 改动 | 验收 |
|---|---|---|
| P1：读者与写作标准 | 增强 reader-experience-review 的防御性表达判断；同步 write-content、improve-content、editor 和匹配的参考材料；移除机械拟人化与密度配额 | 用包含真实警告、隐形反驳、重复辩白、正常技术表达的短文检查；事实保留，非必要争论被删，正常文章可以零修改 |
| P2：发现与引用 | 给外围技能补简短任务入口；处理 growth-lead 命名；修复或明确替代 25 处失效引用；标明哪些材料是方法参考 | 不点名技能的任务抽样可找到方法、读到正文并完成适用部分；路径检查剔除示例网址，不能以读过文件代替完成方法 |
| P2：上游维护 | 增加来源仓库、固定 SHA、文件映射、本地改动说明和复核日期；按条目吸收 SuperSEO 与 Claude SEO 更新 | 逐项 diff 复核；保留本地修正；修改映射后运行 validate 和相关回归 |
| P3：新增能力 | 仅在业务需要时评估 agentic browsing 等专项 | 有明确问题、相应采集字段和可交付证据后再接入 |

写作验收应覆盖“同一句话放在不同上下文，处理结果不同”的案例；不能退回否定词数量、AI 概率、风险提示配额或每篇必须修改多少处。真实任务的选择依据、产物与缺口继续保存在原有任务材料中，无需全局技能调用计数或另建任务库。

实施时每层单独提交，先解决正文质量，再完善发现和上游维护。本次报告只交付诊断、分类和可审阅的升级范围。
