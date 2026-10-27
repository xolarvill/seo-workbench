# Analytics MCP 接入评估

日期：2026-10-27。状态：研究完成，接入建议尚未实施。

## 结论

保留现有 GA4 / GSC / Shopify 确定性采集链；优先为 Clarity 增加可选的官方 MCP 适配能力。MCP 负责工具接入，Workbench 负责项目边界、证据持久化、错误分类和可比性。给某个 agent 安装 MCP 不等于项目 CLI、UI 和报告已经具备该能力。

本次使用 `think` 做架构评估，并阅读本地 `analytics-tracking` 方法中的决策导向与数据质量原则。没有安装服务、配置凭据、调用私有分析数据或修改统计链。

## 当前项目

- `seo_workbench_tools/ga4_probe.py` 已通过 `analytics.readonly` OAuth 调用 Google Analytics Admin / Data API；不是单纯 API key 集成。它包含 token 刷新、property 绑定、报告分页、抽样拒绝、聚合和私有路径清理。
- `seo_workbench/statistics_pipeline.py` 选择 finalized GSC 截止日，对齐 GA4 / Shopify，再经过 business 可比性检查写入 history 和 Portfolio。
- `docs/google-integrations.md` 规定凭据私有存储与来源隔离。当前工程代码没有 Clarity collector 或 MCP 适配实现。

## API、凭据与 MCP

API 提供数据和操作；API key / OAuth token 是认证材料；MCP 是向 agent 暴露工具及其参数的协议。三者并非替代关系。MCP server 仍需凭据，并通常调用供应商 API。

MCP 的增益在于工具发现、标准调用接口及供应商维护的现成工具。数据范围、权限、配额与查询结果质量仍由后端决定。增加进程、协议和依赖也会增加失败点，不能以采用 MCP 作为稳健性的证明。

## 官方能力核对

### Google Analytics

`google/mcp` 是入口目录，Analytics 链接到 `googleanalytics/google-analytics-mcp`。其 README 标注 Experimental，使用同一组 Admin / Data API，要求 ADC 和 `analytics.readonly`。提供 property 信息、普通报告、实时报告、自定义维度与指标、漏斗报告等工具；部分写工具需显式启用及 edit scope。

相较本项目固定报表，MCP 可补交互探索，例如实时流量和自定义查询。但这不是新的底层数据权限；也不应将其漏斗报告与本项目 landing-page-associated event-count funnel 混用。现有 OAuth 文件能否直接作为该服务 ADC 输入需要单独验证。

### Clarity

2025-06-04 博客描述旧的 Data Export 包装方式。当前 main 的 package.json 为 2.0.2；本次实时读取 npm latest 为 **2.0.1**，并下载检查了发布 tarball，未执行其中代码。发布包包含：

- `query-analytics-dashboard`：自然语言查询分析面板。
- `list-session-recordings`：按日期、URL、设备、渠道、dead click / rage click、JS 错误等筛选录制。
- `query-documentation-resources`：查询官方文档。

发布包调用 `https://clarity.microsoft.com/mcp/dashboard/query`、`/recordings/sample` 和 `/documentation/query`；本地 server 使用 stdio。这些 HTTP 后端地址不能据此当作远程 MCP 握手地址。

这为项目增加行为诊断与录制样本检索的实际入口；不能据此宣称可自动观看完整录像、读取完整热图，或已经获得完整历史统计。

传统 Data Export API 文档规定：每项目每天 10 次、最近 24 / 48 / 72 小时、最多 3 维、1,000 行且无分页。这是旧 export endpoint 的限制。新版 MCP 后端的配额和完整历史能力尚未验证，既不能照搬旧限制，也不能推断无限制。

## 推荐接入边界

1. 先做可选 Clarity provider，固定官方包版本；从项目私有 runtime 读取 token，经子进程环境变量传入 `CLARITY_API_TOKEN`，避免出现在命令参数、对话和证据中。项目绑定必须检查实际返回的归属证据，归属不可验证时明确保留缺口。
2. 先支持显式日期 / 时区 / URL / 设备的面板查询，以及有数量上限的录制筛选。最小试点只完成一次查询、一次录制检索和证据保存；不先建设通用 MCP 市场或任意命令执行入口。
3. 适配结果写入项目私有 `audits/clarity/`，保留不可变快照和 `latest.json`，记录 provider / 包版本、工具参数、原始脱敏响应、实际返回窗口、范围与 collection_status。响应不确认窗口或范围时，不把请求文本冒充实际证据。
4. 上游 `tryAsync` 将缺 token 与 HTTP 错误转成普通文本，未可靠设置结构化错误。Workbench 必须将这类结果识别为失败；设置超时、有限重试、429 冷却、缓存和进程清理，不把任意文本解析成成功指标。
5. 录制返回可能包含用户或会话标识、带查询参数的 URL。默认只保存允许的聚合字段与脱敏样本摘要；录制链接只用于有权限的私有查看，不进入公开文档、通用 history 或团队导出。
6. Clarity 先作为独立行为诊断来源。录制是筛选样本，不能用作总体问题发生率；不能与 GA4 sessions 直接相加、替代 CrUX 的性能裁决，或绕过 statistics 的 finalized 日期及 comparability gate。
7. GA4 官方 MCP 作为后续可选的探索工具。只有具体需求超出现有固定报表时再接；不在本次重写生产统计链。

## 实施前需要验证的事实

- 凭据：Clarity 目标项目的 Data Export token，由本地 write-only 配置入口提供；现有 Google OAuth 继续维持。没有必要为此增加 Google edit 权限。
- 联调：本次验证了官方仓库及 npm 发布物可访问，未验证带认证的服务调用。当前会话也没有现成可调用的 Clarity / Analytics MCP 工具。
- 最脆弱假设：新版面板能返回足以核实指标、日期与时区的结果。若只返回解释文本，则仅保留探索用途，不能进入定期统计。
- 验收应覆盖成功 / 无数据 / 无权限 / 无 token / 429 / 超时 / 普通文本错误 / 非 JSON 结果、项目隔离、时区、凭据与录制脱敏、子进程退出，以及现有统计链回归。修改 CLI / state 合同后运行 `./seo validate --json`。
- 关闭可选 provider 即可回退；保留历史证据。无需迁移现有 GA4 / GSC / Shopify 数据。

## 来源

- [Google MCP 目录](https://github.com/google/mcp)
- [Google Analytics MCP](https://github.com/googleanalytics/google-analytics-mcp)
- [Clarity 2025 年介绍](https://clarity.microsoft.com/blog/introducing-the-microsoft-clarity-mcp-server-a-smarter-way-to-fetch-analytics-with-ai/)
- [Clarity MCP 官方实现](https://github.com/microsoft/clarity-mcp-server)
- [发布包元数据](https://registry.npmjs.org/@microsoft%2fclarity-mcp-server/latest)
- [Clarity API 调用实现](https://github.com/microsoft/clarity-mcp-server/blob/main/src/tools.ts)
- [Clarity 错误处理](https://github.com/microsoft/clarity-mcp-server/blob/main/src/utils.ts)
- [传统 Data Export API](https://learn.microsoft.com/en-us/clarity/setup-and-installation/clarity-data-export-api)

后续：实施时先重新核对锁定版本与官方契约，再通过本地凭据做有界联调；本报告是接入评估，不是已经通过联调的实施验收。
