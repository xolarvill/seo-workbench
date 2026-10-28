# Clarity 首次使用诊断：连接成功与分析就绪之间的缺口

日期：2026-10-28。状态：P0适配层修复已实施；保留原诊断证据。P1板块测量核查仍是独立工作，未改网站埋点。

## 已确认的根因

1. `seo_workbench_tools/clarity_probe.py` 的白名单不保留上游 `query` 字段。真实面板响应包含自然语言查询说明，描述站点、日期、时区、排除机器人以及唯一会话口径，但持久化时丢失了这部分来源上下文。它是 provider description，不能冒充结构化执行计划或独立归属证明。
2. `collect()` 只尝试读取 `payload.scope`，随后把所有非文档结果无条件标为 `partial / scope_unverified`。确定性 fixture 已复现：即使返回完整 scope，observed_scope 已保存，结果仍然是 scope_unverified。这是状态分类逻辑缺口，不是服务认证失败的证据。
3. 文档查询 HTTP500 与面板、录制是独立操作。首次使用方只查看旧证据，尚未运行新查询就按用户的“遇到问题即暂停”要求停下；暂停是遵循指令，不能说成一次新的数据查询失败。
4. 现有MCP接入和GA4固定报表尚不等于板块级效果分析。MCP目前暴露面板、录制、文档三个工具，没有独立的热图导出操作；本地GA4 collector按落地页、渠道及电商事件聚合，没有首页板块曝光/点击归属的查询合同。代码缺少这些报表不证明站点不存在相应自定义事件，需单独只读核查。

## 推荐修复顺序

### P0：保留上下文并拆开状态

- 保存脱敏 `provider_query_description`，保留指标含义、URL、日期、timezone、bot policy；与 request 条件分别记录。
- 分别描述 transport、scope、identity、capability。对范围可记录 provider_described / structured_match / unknown / mismatch；自然语言说明不升级为独立验证。
- 修正 observed_scope 已存在仍无条件 scope_unverified 的分支；只有服务端结构字段与请求实际一致才记录 structured_match。归属仍未知时独立保留 identity 未验证，不假称整体已核实。
- 按项目规则，未确认范围的证据继续是 partial；补充可用性字段和解释，而不是简单把 partial 改为 ok。
- 文档500只影响 documentation；本次数据任务是否可执行由相应工具与任务所需字段决定。用户明确要求遇到问题停下时仍须暂停，不能由工具擅自取消该指令。
- 回归：query描述不丢失；字段脱敏；匹配/不匹配/缺失scope；identity未知；文档失败但面板成功；指标字段未知时不可把被过滤后的空对象当完整可分析数据。更新缓存身份，避免复用旧白名单产生的证据。

### P1：核实当前可读的数据，再决定补测量

- 检查目标项目已有Clarity热图、Smart events和GA4事件/自定义维度。已有证据优先，不能仅因默认collector未采集就新增埋点。
- 首轮可通过Clarity官方界面的scroll/click map及CSV导出，记录精确URL、日期、设备、布局版本和过滤条件；如果MCP不能提供这些字段，明确走人工导入路径，不把平均scroll depth解释为某板块曝光人数。
- 读取GA4 page_referrer只能观察首页到文章的导航线索；它不能区分首页Blog区域、导航栏或其他同目标链接。板块归属必须来自可识别的事件参数或对应点击热图。
- 若现有数据缺失，再提出独立的站点测量改动：板块曝光事件、板块点击事件及稳定section_id。明确曝光触发条件、去重单位、目标URL、设备和consent边界；实施前经过该站点的授权与发布验收，不能回填不存在的历史。
- 同一漏斗使用相同来源与统计单位。不要将GA4点击数直接除以Clarity看到人数作为正式CTR。

### P2：恢复分析时的证据表

每个板块分别记录曝光可观测性、点击可观测性、后续行为、设备、样本与布局范围及结论置信度。缺证据记无法判断，不能写“零点击所以删除”。文档检索故障可以用官方公开资料替代，不要求等待该可选工具恢复后才能使用健康的面板工具。

## 本轮验证与边界

- P0修复验收：107项后端回归、11项相关前端用例、UI类型检查与构建通过；项目validate通过，保留原有可选browser证据缺失警告。桌面和手机浏览器均验证范围说明展示、文档失败隔离、面板查询入口可用，无页面错误或横向溢出。
- 修复后的固定日期只读查询返回transport_status=ok、capability_status=available、scope_status=provider_described；保留partial及operator_declared身份状态，没有将自然语言范围说明升级为独立核实。
- 一次固定窗口、只读面板诊断成功，dataErrorType=0；上游query描述有URL、日期、UTC及非机器人唯一会话口径。
- 独立临时fixture证明已存在scope仍被标scope_unverified，且query被sanitize丢弃。
- 没有重新执行文档查询；HTTP500引用此前真实不可变证据。没有核实网站当前所有事件，也没有完成首页板块分析或任何删改判断。
- 本报告为仓库能力诊断，不包含品牌token、会话链接或私有统计值。

来源：[官方MCP工具](https://github.com/microsoft/clarity-mcp-server/blob/main/src/index.ts)、[Clarity scroll maps](https://learn.microsoft.com/en-us/clarity/heatmaps/scroll-maps)、[Clarity Smart events](https://learn.microsoft.com/en-us/clarity/setup-and-installation/smart-events)、[GA4 enhanced measurement](https://support.google.com/analytics/answer/9216061?hl=en)。
