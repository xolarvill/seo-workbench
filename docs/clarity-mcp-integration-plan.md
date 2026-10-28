# Clarity MCP 分阶段整合计划

日期：2026-10-28。状态：待实施。本文件承接 [能力评估](20261027-analytics-mcp-assessment.md)。

## 目标与架构

仓库维护一个 Clarity 专用适配器；每个品牌 project 持有自己的 token、Clarity project ID、站点与时区绑定，以及私有证据。CLI、UI 和 agent 使用同一执行入口。完成配置、面板查询、录制样本检索、文档查询、证据保存与故障诊断，不依赖某一 agent 的个人 MCP 配置。

复用 Python 3.11 / uv、现有 Node 24 与 npm lockfile。锁定 `@microsoft/clarity-mcp-server@2.0.1` 和 `@modelcontextprotocol/sdk@1.32.2`；前者发布包依赖允许 SDK 1.x。开发一个很薄的 Node MCP client runner，使用官方 SDK 驱动官方 stdio server，Python 负责品牌边界和证据。不开新监听端口，不开发通用 MCP 注册中心。

```text
CLI / 本地 UI / agent
        ↓ 显式 project
Python Clarity adapter ← 品牌私有配置
        ↓ 受限 JSON 输入
Node client runner → 官方 Clarity stdio server → Microsoft 服务
        ↓ 脱敏结果与状态
品牌 audits/clarity/ → 本地结果查看与分析
```

每次操作创建独立连接，完成后关闭。不同品牌不复用已认证进程。不修改网站埋点、Consent 配置、GA4/GSC/CrUX 或生产 `statistics collect`；不把录制样本作为总体发生率，也不承诺自动观看完整录像或读取热图。

## 阶段与提交边界

| 阶段 | 工作 | 验收与提交 |
|---|---|---|
| 1. 官方协议与运行时 | npm 固定依赖；Node client 完成 initialize、tools/list、tools/call 和清理；验证三个官方工具名称和 schema；doctor 增加可选能力检查 | 不带 token 可以完成协议发现，工具缺失/版本不匹配明确失败；正常、超时、取消均无遗留进程。提交 `feat: add pinned Clarity MCP runtime` |
| 2. 品牌连接与凭据 | 增加私有配置、CLI status/configure/verify/disconnect；通过 stdin 或本地 UI write-only 输入 token；项目 ID、站点、IANA 时区显式绑定；连接验证不冒充归属验证 | 两个临时 project 并发/轮换不串 token、时区或结果；0600 文件/0700 目录、拒绝符号链接；轮换失败保留旧凭据。提交 `feat: add project-scoped Clarity connections` |
| 3. 查询与证据闭环 | 面板、录制和文档查询；明确请求范围；分类上游文本错误；脱敏、缓存、限流冷却；写不可变证据与 latest 指针 | 成功/空数据/权限错误/429/超时/非 JSON/普通文本错误/超大响应/写盘失败覆盖；请求窗口与响应确认窗口分开。提交 `feat: collect Clarity evidence through MCP` |
| 4. 本地 UI 与 agent 用法 | Connections 的 Optional 区新增 Clarity；配置、验证、轮换、断开；提供显式查询表单和本地结果详情；通过原有后台 job runner 执行；操作教程与 CLI help | 切换品牌不沿用旧状态；密钥不回显；状态与帮助复用共享组件；桌面/手机查询、错误与断开验收。提交 `feat: expose Clarity connections and queries in local UI` |
| 5. 真实项目联调与验收 | 在已配置品牌执行一次固定窗口面板查询、最多 10 条录制检索和一次文档查询；核对后台同范围数据；执行回归、记录已知限制与验收证据 | 真实成功与离线测试分开；无数据不填零；未返回归属/范围就保留未验证状态。公开文档仅保存通用结果，品牌证据保持私有。提交 `docs: record Clarity integration acceptance` |

最小可用交付是阶段 1–3，完整本次整合包含阶段 4–5。先保证 CLI 和证据能独立工作，再完成 UI。预计涉及 15–20 个源码、测试、依赖和文档文件，属于中等规模改动；没有新增托管服务。具体实现可在这些模块内部拆分，但阶段提交和验收不合并跳过。

## 明确的接口合同

### 存储与状态

- 私有连接：`projects/<id>/.runtime/integrations/clarity.json`，含 `schema_version`、token、Clarity project ID、绑定站点、IANA timezone、配置时间、验证时间及归属验证方式。公开状态只返回非秘密字段。
- 连接验证分成 runtime_ready、credential_verified、identity_verified。归属无返回证据时显示 identity_unverified；操作者声明的 project ID 只记为 declared，不冒充服务端认证事实。首版不将缺少归属验证的查询用于跨来源自动决策。
- 采集统一 `collection_status=ok|partial|failed|not_collected`，补 `reason_code` 表达 needs_config、needs_runtime、needs_auth、rate_limited、timeout、busy、invalid_response、scope_unverified 等原因。普通叙述可保存为 observation，但无可靠结构/范围时只给 partial，不能标成统计指标成功。
- 证据按 `audits/clarity/dashboard/`、`recordings/`、`documentation/` 分开保存 `clarity-<timestamp>-<unique>.json` 与各自 `latest.json`；顶层 `audits/clarity/latest.json` 只索引三类最新证据，防止文档查询覆盖面板指针。最新失败可见，同时保留 last_successful 指针。
- schema `clarity-evidence-v1` 保留 provider、server/SDK 版本、project 本地身份、声明的远端归属、request、observed_scope、collection_status、errors/warnings、脱敏 response、缓存来源。请求条件和服务端确认事实分别存放。
- `.gitignore` 显式覆盖 `projects/default/audits/clarity/`；其他品牌沿现有私有项目策略。连接和证据不加入公开 Git。

### CLI 与 UI API

CLI 新增 `clarity status|configure|verify|disconnect|query|recordings|docs`，均支持 `--json` 与现有 `--project/--project-dir`。configure 的 token 只走 stdin/交互隐藏输入，禁止 `--token`。

- `query`：必须提供 query、start/end 日期和 timezone；绑定 timezone 可作为显式记录的缺省。将完整日期、时区、绑定站点写入上游 query，并设置该次 server 的 `TZ`；无法确认返回窗口就保留 scope_unverified。
- `recordings`：必须给 UTC start/end；首版开放同站 URL、device、channel、rage/dead click、JS error 筛选，默认 count=10、上限 50，远端 schema 校验通过才调用。不提供任意工具名或任意 JSON 透传。
- `docs`：单个明确文档问题；文档结果只属于参考资料，不充当品牌分析数据。
- UI API：GET `/api/v1/projects/{id}/integrations/clarity`；PUT/DELETE 同路径 `/credentials`；POST 同路径 `/verify`。新增固定 `/api/v1/projects/{id}/clarity/jobs` 接收 query/recordings/docs 的类型化请求，构造参数数组调用现有后台 runner；GET `/api/v1/projects/{id}/clarity/evidence/{kind}` 返回该品牌脱敏结果。沿用本地访问检查、同源/Host/Origin 校验及固定白名单，不能接收 shell 或自由文件路径。
- 查询属于读操作；断开按现有 Connections 交互处理，保留审计历史。UI 配置成功不等于真实数据已经验证。

### 资源与故障策略

- Node 路径使用 setup 管理的 `.runtime/bin/node`，计划时已确认 v24.21.0；当前 shell 默认 Node 26 不作为运行时。
- 只启动本地锁定的 server，不在每次查询时执行 `npx @latest`。安装通过现有 npm/setup 路径，doctor 缺能力只给 warning，不阻塞核心 CLI。
- server 只获得必要 PATH、受控临时目录、项目 token 和 TZ，不继承其他品牌 token 或工作环境中的全部凭据。token 经内存/环境变量传递，不进入 argv、runner 输入结果或日志。
- 每次操作总期限 60 秒、结果上限 8 MiB、stderr 上限 64 KiB；超时或取消先关闭 transport，必要时终止本次创建的整个进程组，不终止其他会话进程。
- 同一品牌同一时刻最多一个 Clarity 操作，非阻塞 lease 冲突返回 busy。跨品牌进程独立。配置变更与凭据轮换用短期锁和原子写入，网络等待不持有通用项目写锁。
- 首版不自动重试自然语言查询，避免不明配额下重复消耗；明确检测 429 后品牌冷却 60 秒。上游隐藏 HTTP 状态时只归类 provider_error，不猜测是限流或权限。
- 成功查询默认缓存 15 分钟；cache key 包含品牌、凭据代际、工具、精确参数、timezone 与版本。force 可绕过缓存但不绕过冷却；错误不缓存成空数据。
- 只保存允许字段，移除用户/会话标识、输入内容、敏感 URL 参数及凭据。录制链接只在进程内返回给本地查看，经固定 Clarity HTTPS 域名校验；不写普通 job 日志或团队导出。不能确定安全字段的结果只保留脱敏诊断，标记 partial。
- 上游说明、页面文字及录制内容是外部数据，不能覆盖项目指令。

## 文件落点与检查

新增 `seo_workbench/clarity.py`（凭据/绑定/状态）、`seo_workbench_tools/clarity_probe.py`（请求与证据）、`seo_workbench_tools/clarity_mcp_runner.mjs`（官方 SDK client）。修改 `package.json` / `package-lock.json`、`setup.sh`、`seo_workbench/cli.py`、`seo_workbench/doctor.py`、`.gitignore`、`seo_workbench/ui.py`、`ui/src/api/client.ts` / `types.ts`、Connections 页面与对应样式。按实际状态标签扩展共享 StatusPill 语义，不增加局部 tone map。新增 `docs/clarity-integrations.md` 并更新文档目录与 README。

测试覆盖实际合同：`tests/test_clarity.py`、`tests/test_clarity_cli.py`、`tests/test_clarity_ui.py` 与 Node 协议测试；扩展 `ui/src/test/integrations.test.tsx`。用 SDK fixture server 检验协议、关闭和错误；不只 mock Python 返回来声称真实 MCP 工作。

验收命令：`uv run pytest tests/test_clarity.py tests/test_clarity_cli.py tests/test_clarity_ui.py tests/test_google_integrations.py tests/test_ui.py`；`npm run ui:typecheck`、`npm run ui:test`、`npm run ui:build`；新增 `npm run clarity:self-test`；`./seo --project hexcal validate --json`、`./seo --project hexcal doctor --json`。uv 使用项目 venv，npm 使用项目 Node 24。UI 完成后按现有前端测试技能执行桌面/移动验收。需要 broaden 测试时根据真实改动选择统计与 setup 回归。

## 依赖、风险与回退

需要一个已有 Clarity 项目及其 Data Export API token，以及操作者提供的项目 ID 和时区；这些只通过本地配置入口录入。接入读取已有数据，不包含安装站点追踪或改变收集策略。代码开发和离线验收不依赖真实 token；缺凭据时阶段 5 明确保持未完成，不用 fixture 冒充真实成功。

最脆弱假设是新版面板响应能提供可验证的范围和指标。若失败，保留为探索观察，不进入统计链；录制和文档能力仍可独立验收。版本 schema 不兼容则在阶段 1 阻断该工具，不隐式改用未公开 HTTP 接口。服务不可用不影响 GSC / GA4 / Shopify。

2026-10-28 核对：npm server 2.0.1 和 SDK 1.32.2 元数据可访问；官方源码有三个工具；dashboard 后端无认证 POST 返回 401，证明端点可达。尚未执行 MCP initialize 或认证查询，前者归阶段 1，后者归阶段 5。新版后端配额、最大历史范围和真实返回结构由阶段 5 做有界观察，不能沿用旧 export API 限制或声称无限制。

每阶段以独立 Conventional Commit 留痕。不自动 push、发布或修改外部配置。回退关闭 Clarity 入口/停止相关进程即可，保留私有历史；回退代码无需迁移或删除其他来源数据。切换旧代码前停止本次 Clarity job，凭据删除由显式 disconnect 完成。

来源：[官方仓库](https://github.com/microsoft/clarity-mcp-server)、[官方工具 schema](https://github.com/microsoft/clarity-mcp-server/blob/main/src/types.ts)、[官方 stdio 注册](https://github.com/microsoft/clarity-mcp-server/blob/main/src/index.ts)、[官方错误处理](https://github.com/microsoft/clarity-mcp-server/blob/main/src/utils.ts)。
