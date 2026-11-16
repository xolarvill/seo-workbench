# every-app / OpenSEO 全部技能与本地方法对照

执行确认（2026-11-16）：用户在 V2 基础上明确保留 ai-visibility-audit、ai-prompt-research、reverse-engineer-seo 独立入口，其余按 V2 执行。以下 V2 中这三项的合并建议已被该决定取代；实施与验证见 [执行记录](history/20261116-openseo-method-adoption.md)。

## V2 归属复核（2026-11-16，Asia/Shanghai）

本节取代下文及聊天 V1 的归属建议；下文保留为原始研究依据。只评审，不创建或修改技能。复核标准是任务输入、决策、输出和调用触发能否自洽，而非优先减少入口数或强求每个来源都有整合去处。

主要修正：建议新增一个关键词机会发现能力；不新增三个来源同名入口。keyword-deep-dive 明确要求一个目标词，topic-cluster-planning 面向 hub/spoke，seo-dataforseo 面向供应商操作，均不能完整承接“尚不知道选什么词”的任务。已有 content-strategy 含买家阶段研究，但输出是内容组合，不应承担整个词池发现和覆盖验证。新的 keyword-research 负责候选发现和机会筛选，单词深研、聚类、目标登记分别调用既有技能，不复制它们的规则。

| 原 skill | V2 去向／处置 | 原因与边界 |
|---|---|---|
| seo-audit | 整合 site-audit | 增加机会比较和取舍；不要求每次审计做全市场研究，不与 seo-plan 重复编路线图 |
| ai-visibility-audit | 整合 seo-geo | 主诊断方法改为回答与引用证据驱动；不只是往旧评分配方后追加检查项 |
| ai-prompt-research | 整合 seo-geo 的 citation-research 参考 | 问法发现与可见性诊断是同一领域内不同模式；保留研究与跟踪隔离 |
| seo-report | 选择性吸收进既有报告规范，不进 reader-experience-review | 保存、摘要、版本和分享属于交付契约；表达入口只负责表达，不承载报告存储规则 |
| keyword-research | 建议新增 keyword-research 主入口 | 种子、产品、受众或 GSC 输入到候选机会集，有独立于单词深研的输入和交付 |
| keyword-clustering | 选择性整合 seo-cluster | 本地已有核心方法；补小集合简化、existing/new/defer 映射即可，不把多 URL 展现直接判作蚕食 |
| competitive-landscape | 选择性整合 competitive-landscape | 已有同类能力；补搜索竞争者分类与胜出主题，不重复导入整套流程 |
| competitor-analysis | 整合 competitive-landscape 的单站分析模式 | 当前以多站比较为主，需要显式单站模式，并让竞对登记和 GEO 矩阵按任务适用，而非强制补齐 |
| link-prospecting | 整合 linkbuilding 的页面级 prospecting 参考 | 相同获链目标下增加可执行交付；与 backlinks 的现状分析分工不变，准备草稿不等于发送 |
| local-seo | 主要整合 seo-maps；网站专项继续调用 seo-local | GBP、评论和网格属平台观测；用地点身份和实际结果覆盖约束结论，不导入未找到按 21 的实测排名假象 |
| seo-project-setup | 拆分：项目事实到 project-context、定位到 product-marketing-context、账号接入到现有集成文档 | 原技能跨三种职责；一个总技能硬接会使上下文维护承担授权和采集操作 |
| seo-coach | 不单独整合；仅在确有缺口时补 seo 的解释示例 | 当前路由已覆盖选方法；固定开场访谈、每轮追问和强制短条目没有必要导入 |
| reverse-engineer-seo | 整合 competitive-landscape 的单站模式参考 | 研究竞争模式而非编排本站计划；seo-plan 消费其结果，不共同维护两份方法 |
| competitor-strategy | 整合 seo-plan 的竞对驱动规划参考 | 归属正确，但应复用 competitive-landscape、新 keyword-research 与 linkbuilding，不复制各自采集步骤 |
| customer-keywords | 整合拟新增 keyword-research 的客户任务模式 | 与种子发现共享候选集和筛选输出；客户事实从定位读取，SERP 核实人群与任务，不另立用户画像技能 |
| free-tool | 整合 free-tool-strategy 的搜索验证与规格参考 | 既有能力目标一致；补实际结果、差异、输入输出与成本，不能只凭零外链解释排名 |
| keyword-gap | 整合拟新增 keyword-research 的竞对缺口模式 | 是选词的输入方式，不要求每次开展完整竞争格局；样本集合差标候选，核实覆盖后才谈缺口 |
| money-pages | 主要整合 seo-plan 的 SaaS 商业页面优先级参考 | 原任务是选哪些页先建或重做，不是写比较页；执行才交 seo-competitor-pages/competitor-alternatives，删除以搜索量×CPC当收益的判断 |
| rank-on-ai | 选择性整合 seo-geo 的短样本观测模式 | 区分提及、推荐与引用，复用同一证据日志；不增加独立排名体系，不从轨迹推断模型内部因果 |
| chatgpt-business-setup | 暂缓整套引入；事实一致性检查可补 seo-geo 参考 | 平台认领与发布依赖另行验证的产品资格和操作；不能把整个 onboarding 改名后塞成 GEO 子任务 |
| seo-manager-agent | 不进专业 skill；check-in 方法供现有周报参考，调度按运行环境另配 | 专业分析与云端常驻执行不是一个能力，文档不能提供未接入的宿主与连接器 |

建议实施顺序：先定义 keyword-research 与现有单词深研、聚类、登记的边界并验证选路；随后修订 GEO 证据方法，再补单站竞对模式、工具规格与审计取舍。相同能力内的模式按需选择，不增加强制前置流程。新入口、模式及文档修改均须在实施时维护来源映射、检查链接、运行适用 validate 和真实任务路径；本次表格不是实施已经通过的证明。

核查依据：本轮重读本地 keyword-deep-dive、competitive-landscape、seo-plan、project-context、seo、seo-competitor-pages、free-tool-strategy、topic-cluster-planning、seo-dataforseo、reader-experience-review 的正文及现有目录、来源与迁移说明；上游方法沿用下文固定版本，不声称重新核验平台产品状态。

观察日期：2026-11-15，Asia/Shanghai。范围：方法评估；未安装、改写技能或调用 OpenSEO 付费工具。

## 结论

值得学习。完整评估后的重点是 GEO 引用证据链、客户与搜索意图校验、竞对页面类型拆解、免费工具可开发规格、审计机会取舍。多数能力已有本地归属，应在原入口内吸收方法，不整包导入，也不为同名能力创建第二入口。本记录是建议，不是已批准实施的工作清单。

## 方法与覆盖

核对 every-app 作者页、两个仓库的完整递归树（均 truncated=false），取得 12 个核心与 9 个实验技能的全部 SKILL.md 正文，比较方法、输入、交付及边界；seo-report 的 HTML/CSS 模板代码不作实现审计。对照本地技能正文、来源维护说明与目录迁移记录。未执行这 21 项专业工作流，也未完整审阅全部附属文件和产品实现。

归属与标签分开：open-seo 与 seo-party-skills 均归 every-app；实验仓库 README 明确称其不是 official OpenSEO skills。Community 标签不构成排除评估的理由。此版替换初版只评 12 项的范围，纳入 every-app 全部 21 项。Browse 总数显示 22，不等于 every-app 作者页的 21；本次“全部”指该组织在上述两个 SEO 技能目录中的全部技能，未将未识别的其他目录条目冒称已读。

固定观察版本（经 GitHub 连接器完整树和文件正文核对）：

- [open-seo 核心技能树](https://github.com/every-app/open-seo/tree/2df84ff91461cc55b6c8bb98f3ce0f195d2e463d/plugins/openseo/skills)：`2df84ff91461cc55b6c8bb98f3ce0f195d2e463d`，12 项。
- [seo-party-skills 实验技能树](https://github.com/every-app/seo-party-skills/tree/3134e53fc2a77e04eb7d63266ece1777d88757e0/skills)：`3134e53fc2a77e04eb7d63266ece1777d88757e0`，9 项。
- [作者页](https://seo.party/u/every-app)列出 21 项；[实验仓库 README](https://github.com/every-app/seo-party-skills/blob/3134e53fc2a77e04eb7d63266ece1777d88757e0/README.md)说明定位。SEO.party reviewed pin 与上述固定版本可能不同，不能混称同一版本。后续适配仍须维护来源映射与许可证。

## 能力映射

上游正文统一位于 [官方技能目录](https://github.com/every-app/open-seo/tree/main/plugins/openseo/skills)。

| 核心技能 | 本地归属 | 本轮判断 |
|---|---|---|
| seo-audit | [site-audit](../skills/site-audit/SKILL.md) | 补候选机会表、优先理由和最强落选项；不只列技术问题 |
| ai-visibility-audit | [seo-geo](../skills/seo-geo/SKILL.md) | 最高优先：实际回答、引用源核读、本站缺口、具体行动 |
| ai-prompt-research | [citation-research](../skills/seo-geo/references/citation-research.md) | 已有问法发现；可补品牌题分离、跨种子去重、研究与跟踪分离 |
| seo-report | [reader-experience-review](../skills/reader-experience-review/SKILL.md) 与既有报告规范 | 学摘要与证据分层，不另建写作入口或强制 HTML |
| keyword-research | [keyword-deep-dive](../skills/keyword-deep-dive/SKILL.md) 等 | 多词机会发现与单词深研有区别；先复用本地 GSC 和现有候选池 |
| keyword-clustering | [seo-cluster](../skills/seo-cluster/SKILL.md) | 已有 SERP 重叠与页面映射，无须新增入口 |
| competitive-landscape | [competitive-landscape](../skills/competitive-landscape/SKILL.md) | 已覆盖多站格局与证据边界 |
| competitor-analysis | [competitive-landscape](../skills/competitive-landscape/SKILL.md) 的单竞对模式 | 可补单站页面类型与胜出模式拆解，不必独立技能 |
| link-prospecting | [linkbuilding](../skills/linkbuilding/SKILL.md) | 补页面级候选、引用理由、公开联系路径及来源，优于泛战术列表 |
| local-seo | [seo-maps](../skills/seo-maps/SKILL.md)、[seo-local](../skills/seo-local/SKILL.md) | 有对应领域；可学先小网格再扩展的成本控制 |
| seo-project-setup | [project-context](../skills/project-context/SKILL.md) 等 | 已有持久上下文；借鉴只补当前任务必需缺口 |
| seo-coach | [seo](../skills/seo/SKILL.md) 与现有解释方式 | 属交互模式，无须另立能力入口 |

## 九项实验技能对照

原文均在上面的固定实验技能树下，路径为 `skills/<名称>/SKILL.md`。

| 实验技能 | 本地归属 | 值得吸收的方法及必要修正 |
|---|---|---|
| reverse-engineer-seo | [competitive-landscape](../skills/competitive-landscape/SKILL.md)、[seo-plan](../skills/seo-plan/SKILL.md) | 拆非品牌查询模式、页面族、制作方式与获链资产，再缩成本站第一张可做页面；抽样词覆盖占比不能称流量占比 |
| competitor-strategy | competitive-landscape → seo-plan | 同时看领导者与体量接近的竞对，把关键词、页面和获链主题连成起步计划；同类商家筛选不适用于所有搜索竞争者 |
| customer-keywords | [product-marketing-context](../skills/product-marketing-context/SKILL.md)、[content-strategy](../skills/content-strategy/SKILL.md)、keyword-deep-dive | 客户任务卡 → 候选词 → 指标 → SERP 是否服务同类客户 → 页面族；保留无量但有业务依据的探索候选 |
| free-tool | [free-tool-strategy](../skills/free-tool-strategy/SKILL.md) | 选一个有明确差异的工具，交付输入、输出、数据源、单位运行成本、URL、产品衔接及推广来源 |
| keyword-gap | competitive-landscape、keyword-deep-dive、seo-cluster | 竞对共有词 → 业务筛选 → 页面机会；100 条采样缺失不是本站前 100 名无排名 |
| money-pages | [seo-competitor-pages](../skills/seo-competitor-pages/SKILL.md)、seo-plan | 区分替代、对比、竞对价格与特定受众四类购买问题；先查已有页，再决定新建或重做；CPC 不等于 SEO 收益 |
| rank-on-ai | seo-geo / citation-research | 区分提及、实际推荐、未提及；核读被引列表和事实错误；当次首提顺序不称稳定 AI 排名 |
| chatgpt-business-setup | seo-geo + project-context 的品牌事实检查 | 品牌问题 → AI 与官网逐条核对 → 冲突/缺页 → 可复用资料和测试题；平台具体资格/界面须另核实 |
| seo-manager-agent | 现有统计、周报与运行调度机制 | 先真实跑一次 check-in 验证来源，再决定周期任务；保留过期、失败、未接入来源，沿用本地 finalized 窗口和门禁 |

## 完整评估后的重点发现

### 客户、意图和页面类型

customer-keywords 最值得学的是把客户与本次任务绑定，再用 SERP 检查是否跑偏：词面接近产品，也可能服务另一类人。本地 content-strategy 已问客户语言，keyword-deep-dive 已判断意图，可在交接处补“谁在完成什么任务，现有结果是否服务此人”。推断标明来源，不覆盖已批准定位或品牌要求。

reverse-engineer-seo 的增量是纵向拆解：页面族 → 非品牌查询模式 → 制作方式 → 获链资产 → 本站首个小版本。competitor-strategy 则组合成多站起步计划。本地竞争格局已有横向比较，可补这类纵向参考；不能从少量关键词或抓不到的页面推定全站模板，也不能把供应商 ETV 当真实流量。

free-tool 把研究推进到可开发规格。本地 free-tool-strategy 已有工具类型、买建选择、线索收集、维护成本，可补实际 SERP 候选对照、输入/输出样例、独有价值、数据成本和首批引用来源。保留业务与工程可行性判断，不靠评分相加自动决定。

money-pages 的四类购买问题适合补 SaaS 策略参考，不要求电商或内容站照建四类页。本地比较页技能已有结构和事实要求，值得补的是哪些页先做，以及已有页应重做还是新建。

### 需要修正后才能借鉴的配方

| 原文配方 | 问题 | 本地适配 |
|---|---|---|
| keyword-gap：本站取 100 条、竞对各 100 条，判本站前 100 名没排名 | 记录数与排名深度是两回事；未分页的集合差只能证明样本差 | 标候选缺口，分页或定向验证，保留覆盖边界 |
| money-pages：搜索量 × CPC，称广告主支付的点击价值 | 搜索次数不是点击次数，缺广告点击份额，也不是 SEO 收入 | 最多作非预测性比较指标，不能当总收益或唯一优先级 |
| free-tool：目标工具返回零外链，说不是靠链接取胜 | 供应商覆盖和单 URL 观测不能解释排名原因 | 只报该源未记录链接，不推导排名机制 |
| customer-keywords：无量词没有有量变体支撑就丢弃 | 会漏掉小众、初期和高价值需求 | 留探索区，结合客户语言与第一方观测 |
| rank-on-ai：按首提顺序排名，据搜索顺序推断内部先选品牌 | 顺序可描述，不是稳定搜索排名；轨迹不完整解释内部决策 | 记录当次推荐顺序，区分提及/推荐，不推断内部因果 |
| chatgpt-business-setup：无引用回答来自模型记忆 | 无可见引用不能确定生成来源 | 记未返回引用、来源未知，仍核对事实 |
| local-seo：未找到按 21 算平均名次 | 是截断展示假设，不是实测排名；稀疏结果尤其易误读 | 保留 not_found、resultsCount、失败状态，展示填充值单列 |
| 多项技能：KD=0 统一视为无数据 | 缺失编码取决于供应商契约 | 核实实际字段语义，不普遍把零转换为空 |

这些是方法逻辑评审，不是断言工具实现也有同样缺陷。rank-on-ai 与核心 ai-visibility-audit 对 API 回答、跟踪观测和排名的表述不同；适配优先保留平台、运行、样本边界。

### 交付与执行

seo-report 的摘要与全文分离、同主题同周期避免重复、公开分享单独授权，值得在既有报告流程中借鉴。seo-project-setup 的最小必需上下文与 coach 的单步解释可减少重复询问。外链公开联系路径附来源、地图 CID 身份匹配、小范围采集后按需扩展，适合补原能力参考。

seo-manager-agent 可学先交付一次真实周报，再启用用户请求的调度。其产品、套餐、地区、菜单和固定延迟未在本轮作为已核实事实；本地不能因此声称拥有云端常驻代理，也不能跳过统计与报告门禁。chatgpt-business-setup 的平台资格、字段和认领步骤也须另行从官方来源核实；本轮只评估品牌事实核对的方法，不提供已验证的平台操作指南。

## 原有四项建议与补充顺序

补充后的顺序建议：GEO 正文与观察链 → 客户意图方法 → 竞对纵向拆解 → 工具规格 → 审计取舍 → 外链候选。money-pages 作为 SaaS 专用参考；品牌事实检查可作为 GEO 子方法；周报调度只借鉴交付流程。本轮不修改技能本身。

1. **GEO 证据链。** 本地 seo-geo 正文仍包含 134–167 词、加权 citability/readiness 评分、固定平台引用比例及通用 llms.txt 建议。它们不应直接决定项目优先级。保留现有问法来源标记和冻结矩阵，补“回答 → 引用 URL → 核读页面 → 本站可行动差异”。分别统计成功回答、失败、品牌提及、本站引用；品牌问题与中性问题分开。验收应能从每项建议回溯原回答及读过的源页面，不靠准备度评分代替观测。
2. **审计机会比较。** 在原报告中保留候选、证据、业务相关性、成本和主要未知项；主结论精选少数行动，并解释最强落选项为何暂缓。按页面类型比较表现较强与较弱的同类页，保护已有赢家。采集规模按本地规则和任务调整，不照搬每类两页或固定候选数。验收看取舍能否被证据解释，不按建议条数凑数。
3. **外链执行交付。** 在 linkbuilding 的适用参考中补页面级 prospect 表：目标 URL、现有相关内容、为何值得引用本站、公开联系路径、来源 URL、建议角度。只准备候选和草稿，不发送。清理本地正文凭站龄推测 DR、固定锚文本安全比例等配方时应另行核实来源，不能当作已测值。
4. **复用与交付。** 沿用现有报告和上下文，不另建 research-log 数据库。后续任务快速读到结论、证据日期、适用范围和未解问题即可；证据是否需刷新由决策决定，不统一设 30 天有效期。

## 关键外部证据

- [目录](https://seo.party/browse)：Official / Community 分类及技能来源。
- [seo-audit 原文](https://raw.githubusercontent.com/every-app/open-seo/main/plugins/openseo/skills/seo-audit/SKILL.md)：页面族、候选表、最强落选机会复核、少数优先行动；启发的是决策方法。
- [ai-visibility-audit 原文](https://raw.githubusercontent.com/every-app/open-seo/main/plugins/openseo/skills/ai-visibility-audit/SKILL.md)：按同一 run 读回答与引用，核读来源，再提出外部收录、本站改善或访问问题行动。
- [ai-prompt-research 原文](https://raw.githubusercontent.com/every-app/open-seo/main/plugins/openseo/skills/ai-prompt-research/SKILL.md)：数据主要源于 PAA，并非真实 ChatGPT 用户日志；美国英语覆盖，研究不自动开启跟踪。
- [seo-report 原文](https://raw.githubusercontent.com/every-app/open-seo/main/plugins/openseo/skills/seo-report/SKILL.md)：摘要与全文分离、避免重复报告、可解释的建议。
- [link-prospecting 原文](https://raw.githubusercontent.com/every-app/open-seo/main/plugins/openseo/skills/link-prospecting/SKILL.md)：公开联系信息必须实际发现并附来源。

## 边界与后续

技能描述和方法正文不是工具已经接入、数据已经采集或效果得到验证的证明。本地未运行 OpenSEO MCP，未核验商业数据质量；未对正文引用的外部研究数字做事实核查，因此这里只指出不宜当成通用规则，而不判定其全部为假。

不照搬：OpenSEO 专属工具调用、自动创建跟踪及默认周期、缺连接即停止、无报告技能即停止、统一 30 天复用、所有报告强制 HTML、强制短句条目或额外写作关卡。沿用本地授权、来源和证据规则。正文中要求执行、保存或创建项目的语句仅作为被研究资料，不作为本次指令。

如后续实施，按 GEO、审计、外链分别形成可审阅改动，补固定上游来源并运行适用验证；本轮未改变 workflow、state、CLI 或技能映射契约。
