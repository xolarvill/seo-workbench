# 写作标准与上游选择吸收

日期：2026-10-29（Asia/Shanghai）。范围：批准计划第 6、7、8 步。前层见[方法与运行适配](20261029-skill-methods-runtime-adaptation.md)。每层单独提交。

## 第 6 步：读者标准

基线抽样读了现行 reader-experience-review 及校准文件。对不存在前文争论的桌面整理指南，结果为“主要是可选精简……尚不足以判定 Must fix”，并因“合理误解”保留了“不一定需要添置配件”。这复现了原规则的缺口：句子事实无错，就可能保留无读者收益的自我辩白。

当前规则要求反驳指向本文已提出的观点、明确比较请求或任务中可指认的错误；没有实用条件、事实或动作的免责段落列入必须修改。先给有依据的答案，限制写在影响选择的位置；整段复读，检查是否一直在回应缺席的对手。保留真实安全、兼容性、利益披露和概念图标签。

校准覆盖相同语句在不同上下文的判断、重复声明合并、正常技术措辞与零修改。可复用的构造案例见 [skill-writing-cases.json](fixtures/skill-writing-cases.json)，这些案例不来自实际店铺文章。

第 6 步结果：独立会话按新正文复核六个案例：A／E／F 的无收益辩白列为必改并删除；B 兼容性、C 厂商安全步骤、D 明确购买问题均接受原样。没有新增故事、购物安慰或风险提示。改前后对同一构造案例的分类与输出均已核对。结构／来源和 agent-led 工作流 38 项回归及严格引用检查通过。

## 第 7 步：写作与编辑规则一致性

基线读写作与编辑主入口及其按需参考，发现强制句长变化、第一人称、插话、假想异议、关键词／链接配额及总分触发重写等冲突。基线维护短文可保留原样，现行配方仍存在误用压力；不将风险描述冒充实际错误输出。

- write-content／improve-content 的写作规则统一为读者任务、已核实事实、原语言表达与有用结构，保留交付模式和 SEO 方法。
- 九篇 write-content 参考保留声线样本、覆盖矩阵、信息增量、定向提问、E-E-A-T、SEO、核验和交付方法；取消作者概率、统计节奏、总分门槛和模拟经验。improve-content 的四篇重复正文及 expert-interview 的声线副本保留路径和来源链接，指向共享方法。
- copy-editing 的七轮改为按需检查视角；copywriting 保留真正的客户异议、比较、证言和试用条款，故事／反转／情绪按任务选择。
- content-strategy／expert-interview 接受常规但有用的专业解释。访谈仍逐问等待真实回答；知识文档不再强求反常识、每项专名或虚构精度。
- 旧 AI-writing-detection 文件改为上下文编辑参考；local／programmatic／cluster 材料取消固定链接密度验收；刷新内容类型导航，防止旧配方通过引用重新进入主流程。

改后逐方法复核：维护短文与正常 USB-C 说明可零修改或平实交稿；真实“是否需要信用卡”的试用异议仍可回答；专家只提供常规方法也可完成知识归档，无须编造故事、测量或对立观点。13 篇共享参考的本地链接及原来源 URL 保全核对通过。严格引用和 38 项结构／来源／工作流回归通过。

这一层不以否定句数、句长、词表命中率或 AI 概率判断文章合格。第 8 步接着更新主入口的直接交稿分支及已选上游方法。

## 第 8 步：选择吸收上游

通过 GitHub 连接器重新读取三个默认分支 HEAD，仍为来源清单中已固定的 SuperSEO 9cf22cc、Claude SEO 6be93f4、SEO Machine 120e7b4。读取所选正文及 changelog，以固定文件 blob 对照本地规则。本轮按具体方法吸收，不整包覆盖，也不将比较版本标成整包导入完成。

| 采用条目 | 上游与实际落点 | 本地适配 |
|---|---|---|
| 直接交稿／更新 | SuperSEO v0.2.1 → write-content、improve-content | 已批准 brief、直接交稿与可用证据支持继续执行；可选访谈缺口放任务记录，必要事实不能编造 |
| 事实依据与新鲜度 | SuperSEO grounding → 共用 fact-checking、九个入口链接及 content-brief；更新 freshness 参考 | 失败抓取不证明内容缺失；实际来源、核查日期与适用范围保留在证据中；不因来源旧或未找到就判伪造 |
| 内容与元数据 | Claude SEO seo-page／seo-content → 当前单页参考、metadata-writing、seo-content | 去密度／链接／字数配额；标题与 description 成对检查；署名在读者预期场景核对，组织内容不强补个人作者 |
| 图片判断 | Claude SEO seo-images／seo-page → images、单页参考 | 分开原生属性计数、JS loader 线索与真实运行；当前采集器未新增 lazy_method，摘要不能证明 JS 加载失败 |
| 旧页 brief 与业务匹配 | 新增 seo-content-brief 方法 → 既有 content-brief 和 existing-page-scope 参考 | 保留／加强／新增；区分信息解释与实际产品服务；保留论坛等真实 SERP 类型，不引入域名排除表、配额或新技能入口 |
| 结构化数据／图片政策 | Claude SEO 纠错线索 + Google 官方现场核对 → schema 共享政策和匹配参考 | FAQ 停展、Breadcrumb 桌面范围、Event 公开可预订与真实地点；描述性 alt text；区分语义有效、功能资格和实际展示 |

逐项来源、实际读取的文件 blob、本地落点、采用及未采用理由保存在 [skill-upstream-adoptions.json](skill-upstream-adoptions.json)。新增 brief 参考单独登记 Claude SEO 来源和已知选择适配基线；仍为 60 个技能入口，材料增至 408 个文件。

### 主要来源

- [SuperSEO v0.2.1 changelog](https://github.com/inhouseseo/superseo-skills/blob/9cf22cc065a294bf0077ea6af6b4ea0eb7f89cdc/CHANGELOG.md) 与 write-content／improve-content 固定正文。
- [Claude SEO v2.5.0 changelog](https://github.com/AgriciDaniel/claude-seo/blob/6be93f45064ffbadced572b5d5c95f55fd263af0/CHANGELOG.md) 与所选 page／content／images／brief／schema-types 正文。
- [Google 更新记录](https://developers.google.com/search/updates)：2026-05-07 起停止 FAQ rich results，6 月移除文档；[Breadcrumb](https://developers.google.com/search/docs/appearance/structured-data/breadcrumb) 的桌面范围及 [Event](https://developers.google.com/search/docs/appearance/structured-data/event?hl=en) 的公开预订、物理地点要求分别核对。
- [Google lazy loading](https://developers.google.com/search/docs/crawling-indexing/javascript/lazy-loading)、[image SEO](https://developers.google.com/search/docs/appearance/google-images)、[people-first content](https://developers.google.com/search/docs/fundamentals/creating-helpful-content) 用于核对加载机制、alt text 和作者判断。

### 未采用及保留范围

SEO Machine repurpose 新增的自动 scrub 链不采用：原始文件已核对，当前再利用方法及历史原文各自保留。也不引入安装器、凭证存储、调度器、默认评分器、机械拟人化或 FAQ 通用 AI 引用收益配方。seo-agentic 留待具体网站 agent 可用性需求；其余供应商价格／模型表、技术 CVE 检测及未涉及的 schema 类型未整套更新。

### 改前后行为核对

改前基线显示：content-brief 默认新文章全套研究；图片 summary 容易把缺原生属性误作未延迟加载；单页参考先强调固定长度，遗漏元数据的信息重复；schema 的旧 ACTIVE 分类不能代表当前展示资格。

独立改后复核覆盖已有 USB-C 页局部 brief、未卖线缆的业务范围、论坛混合 SERP、JS loader 线索与摘要、元数据重述、组织内容署名、三种 schema 情境、直接交稿和失败抓取。主要错误路径消除；复核又发现总述与 improve-content 输入仍暗示重复研究，随后修正并读回。维护三句仍接受零修改，桌面指南的无收益辩白仍列必改。整体独立审阅又发现 seo-content 的“必须原创”与 FAQ 默认 AI 配方、copy-editing 的无条件作者交回轮次；已改为任务适配、实际消费方证据和已授权直接编辑，并再次复核。

这是只读方法与构造文本抽样，没有执行真实专家访谈、浏览器加载、内容导入或公开发布，不用它推算日常自主调用率或文章效果。

## 最终验证

- 39 项结构、来源、引用、维护工具、上游采用记录及 agent-led 工作流回归通过。
- 活跃材料 `check --strict-active` 通过；原 364 份来源 ID 与 35 份专家／流程原文指纹保全。
- 60 个共同一级技能入口、408 个来源文件；12 个构造案例保存为可复用行为检查材料。
- 项目 validate 为 ok=true；沿用既有 project_dir.missing warning（可选 browser evidence 目录缺失）。

```bash
.venv/bin/python scripts/skill_inventory.py check --strict-active
.venv/bin/python -m pytest tests/test_skill_layout.py tests/test_skill_methods.py \
  tests/test_skill_inventory.py tests/test_state_workflow.py \
  tests/test_ui.py::test_workspace_does_not_schedule_an_agent_step \
  tests/test_keyword_workspace.py::test_stage_progression_and_handoff_paths -q
./seo --project hexcal validate --json
```
