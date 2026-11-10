# 统计学 SEO 操作手册

这套能力的目标不是给某一个 operation task 找理由，而是长期回答三类问题：全站机会在哪里、观察到的变化有多可信、已上线动作是否值得继续。统计结果是带条件的决策证据，不是排名公式，也不把同期变化写成因果。

## 最低运行条件

| 准备 | 最低要求 | 当前系统已有 | 相对当前系统的额外准备 |
|---|---|---|---|
| GSC | 项目绑定可读取目标 property；Search Analytics 有 page、query-page、date-page | 已有只读 OAuth / service account、property binding、28 天前后窗 | 保持授权有效；若重新授权、换 property 或修改搜索类型，要登记测量口径变化 |
| GA4 | 独立 `analytics.readonly` profile；绑定正确 property；有 landing page、date 维度 | 已有只读采集和项目绑定 | 确认站点时区与 Shopify 一致；key event 定义变化时登记；不能把 key events 写成购买 |
| Shopify | 规范 `*.myshopify.com` 域名；至少 `read_orders`；店铺时区和币种可读 | 已有项目级只读连接和产品级聚合 | 保持 app 安装和 scope；商品 handle 变化、币种或时区变化时登记；收入只作全渠道商业背景 |
| 日期可比性 | GSC、GA4、Shopify 使用完全相同的两个 28 天窗口 | `statistics collect` 自动以 finalized GSC 截止日为共同截止日 | 不再分别运行后直接人工拼接；临时导入必须自己保证窗口完全一致 |
| 日级历史 | 至少覆盖本次前后窗口；每个日期明确记录“已请求”，即使某页无行 | 私有 JSONL、GSC page 与 page-device sidecar、覆盖清单、120 天保留、重复运行覆盖同日同 URL（或同日同 URL 同 device） | 每日或至少每周稳定运行一次，避免历史过期；备份时保留 `audits/statistics/history/` |
| 口径台账 | 埋点、同意模式、property、币种、时区、模板等会改变数据含义的日期可追溯 | 已有 `measurement-regimes.jsonl` 与比较闸门 | 操作者必须在变更发生时登记；未知断点会让统计区间看起来精确但含义错误 |
| 变更与验证台账 | SEO 上线动作有 URL、时间、假设、指标；技术修复有 fingerprint 和 verified 日期 | 已有 changes ledger 和 technical issue ledger | 不能只在聊天或报告中记动作；否则系统只能描述趋势，不能做 change-scoped 复盘 |
| 人工决策边界 | 合并、重定向、发布、接受风险仍需人工确认 | 已有 Pages / Content / Audit 工作区边界 | 每周审阅统计建议及其数据状态；不得把 `insufficient_data` 当作无效果 |

其中真正新增的日常责任只有三项：稳定运行统一采集、及时登记测量口径变化、把上线动作写入既有变更台账。其余凭据、项目隔离、技术问题台账和人工确认路径都沿用当前系统。

## 一次性投产检查

```bash
./seo --project <id> validate --json
./seo --project <id> statistics regime list --json
./seo --project <id> statistics collect --json
```

第一次成功运行后检查：

- `collection_status` 是 `ok`；`partial` 只允许由已登记的测量断点造成，不能作为正常成功忽略；
- `common_finalized_end_date` 有值，GSC、GA4、Shopify、business、history、portfolio 各步骤都完成；
- `audits/statistics/history/coverage.json` 的 GSC 和 business 覆盖本次完整前后窗口；
- `audits/content-portfolio/latest.json` 是 `content-portfolio-v4`；
- 私有 GSC、GA4、Shopify、business、statistics 文件权限为 `0600`，凭据和访客、事件、客户、订单标识符没有进入产物；
- Pages 与 Overview 能显示统计证据，业务指标带币种，缺失观测显示 `Not observed`。
- 新增 Statistics 页（侧栏）可直接触发 `statistics collect`（白名单动作），并只读展示采集状态、日历史覆盖和测量口径台账；点击驱动、区间、趋势、转位矩阵、CTR 基准、技术效应均在此聚合展示。

## 正常运行与恢复

日常只运行一个生产入口：

```bash
./seo --project <id> statistics collect --json
```

建议在每天 GSC finalized 数据可用后运行；如果团队没有每日调度，至少每周运行一次。该命令重复执行是安全的：日历史以 `date + URL` 更新，运行清单保留每一步状态。无需为此新增常驻服务；使用现有 cron、launchd 或 CI 在项目目录调用即可。

| 状态 | 含义 | 操作 |
|---|---|---|
| `ok` | 三个来源窗口一致、历史写入且 Portfolio 已刷新 | 进入 Pages / Overview 审阅 |
| `partial` | 数据已采集，但比较跨越已登记的不可比口径变化 | 查看 regime 记录；等待窗口完全越过断点，或只读独立来源证据 |
| `failed` | 某一步未完成，后续 Portfolio 不作为新证据刷新 | 查看 `steps` 中首个 failed；修复授权、scope、时区、截断或网络后重跑同一命令 |

不要手动删除旧历史来“修复”失败。错误数据若来自错误 property 或错误口径，应先登记断点；若确需纠正私有历史，先备份并按明确日期、来源做受控修复。

## 必须登记的测量变化

默认会打断可比性的例子包括：更换 GSC property、GA4 property 或 stream；调整 consent banner；新增或移除 GA4 key event；改变跨域跟踪；更换 Shopify 店铺时区、币种或商品 handle 规则。

```bash
./seo --project <id> statistics regime add \
  --source ga4 \
  --effective-at 2026-08-17 \
  --metric key_events \
  --description "Changed GA4 key-event configuration" \
  --json
```

只有经验证不改变前后含义的记录才使用 `--comparable-across`。描述必须写事实，不写“应该没影响”之类的猜测。

## 指标、原理与产品位置

| 要添加的指标 | 统计学原理 | 为什么添加、意义是什么 | 添加到哪 | 具体展示形式 | 是否需要新增数据 |
|---|---|---|---|---|---|
| 点击变化拆解 | 周报 headline 优先使用同一 date-page history 的点击变化；page rows 与 query-page 联集仅做 `clicks = impressions × CTR` 对称拆解 | 区分日期页历史的总览、完整 page rows 汇总与可观测查询子集的结构驱动；coverage 和未归属 remainder 必须保留，不推断匿名/隐藏查询的原因 | Portfolio 全站与 Page 详情 | date-page headline、完整 page clicks、observed query-page clicks、两窗口 coverage、full/observed/remainder change；exposure effect、CTR effect 仅属于 query-page 子集 | 否；使用现有 GSC date-page、page 与 query-page 前后窗 |
| 查询组合集中度 | Top-N share、Herfindahl-Hirschman Index、有效查询数 | 判断流量是否过度依赖少数查询，指导防守、扩词和内容组合治理 | Overview、Portfolio、Page 详情 | Top 1/3/10 share、HHI、effective query count | 否；使用 GSC query-page |
| 排名带迁移 | 将平均位置分桶，并比较相同 query-page 单元的带间迁移 | 找到 4–10、11–20 等最可能通过补内容和内链突破的曝光，而不是对所有低排名一视同仁 | Portfolio 与 Page 详情 | 各排名带 impressions；主要迁移路径 | 否 |
| 查询所有权集中度 | URL 份额和 HHI | 区分真正的多页面承接、品牌/语言变体与潜在 cannibalization；只触发人工合并审查 | Query conflicts、Page 详情 | owner URL、share、HHI、总 impressions | 否 |
| 同站 CTR 机会 | 同一 property、相近平均位置页面的 leave-one-page-out 基准；Beta 平滑；双侧 z 检验；Benjamini-Hochberg FDR | 用本站现实表现替代行业通用 CTR 曲线；在多页面扫描时控制误报，估计可恢复点击而不夸大 | Pages `CTR opportunity`、Portfolio 汇总、Page 详情 | expected/actual CTR、raw p、FDR q、仅 FDR 显著的 recoverable clicks | 否；需要足够 GSC impressions，低样本返回不足 |
| 搜索变化置信度 | 7 日 moving-block bootstrap，500 次确定性重采样 | 保留周内自相关，给出变化区间和方向概率；把“看起来上涨”与“可信上涨”分开 | Pages `Evidence`、Overview、Page 详情 | 点击变化 95% 区间、上涨/下降概率、weak/moderate/strong | 是；需要 GSC date-page 日级数据和完整覆盖 |
| 8 周趋势与异常 | 周汇总 Theil–Sen 斜率；最新残差用 MAD 标准化 | 对促销尖峰和极端日更稳健，发现长期滑坡或异常周，不把一次波动当趋势 | Pages `8-week trend`、Overview、Page 详情 | 每周斜率、latest anomaly score、异常标记 | 是；依赖连续日历史，初期可能不足 |
| 有机落地页参与质量 | engaged sessions / sessions 的 Wilson 区间；key events / session 描述比率 | 区分搜索点击增长与落地后质量，提醒“流量涨了但参与下降”；不声称购买归因 | Overview、Page 详情 | sessions、engagement rate 及区间、key events/session；显示口径警告 | 是；需要 GA4 date + landing page 的聚合日数据 |
| GSC 与 GA4 一致性 | 每日 `log(organic sessions / GSC clicks)` 的中位数与 MAD | 识别埋点、同意模式、canonical/landing 归一化或数据处理变化；它是测量健康检查，不是排名指标 | Pages `GSC↔GA4`、Overview、Page 详情 | 当前中位比率、相对历史偏移、possible measurement break | 是；需要同日 GSC 和 GA4 日数据 |
| 商业价值 × 搜索机会 | 归一化全渠道产品净收入/订单和 GSC 搜索机会的透明组合，不做渠道归因 | 在同等 SEO 机会中优先审阅商业价值较高页面，同时避免把 Shopify 收入说成 SEO 收入 | Portfolio、Page 详情 | 收入、订单、币种、机会分量及排序解释 | 是；需要 Shopify date + product handle 聚合；无需订单标识 |
| 单次 SEO 变更结果 | 变更日前后 block bootstrap；CTR 用 Wilson 差异；完整历史时可加匹配未变更页面的描述性 DiD | 检查预设指标方向是否有统计支持；防止仅凭前后两点宣称成功 | Change outcome、Pages Review | winning/no_change/regressing/insufficient_data；区间、方向概率、matched controls；`causal=false` | 需要既有 change ledger；匹配对照还需要足够未变更同类页面历史 |
| 技术规则修复关联 | 同一 verified rule 至少 6 个修复；14 日前后 block bootstrap；sign-flip 检验；规则间 BH-FDR | 回答某类已验证修复是否通常伴随搜索改善，帮助安排下一批技术债；不宣称因果 | Overview technical effects、Page 详情 | rule、样本数、平均变化、区间、p/q、association 标识 | 需要既有技术 issue verification 历史和完整 GSC 日历史 |

冲突提升按候选身份而非参数化 PDP URL 计数：完整技术审计可用时，优先使用同站实际 `final_url`；未改变候选时再使用同站 canonical。商品 URL 忽略参数。`site:` 查询和项目名称完全匹配的查询仍保留在原始 query-page/top-query 证据中，但不会提升为冲突；所有冲突只要求人工审查，不会自动写入 canonical 或 redirect。

## 解释纪律

- `not_observed` 不是 0；`insufficient_data` 不是无效果；`partial` 不是完整成功。
- FDR 显著只说明在当前模型和观测窗口下误报得到控制，不说明改动造成了结果。
- GSC 点击、GA4 organic sessions 和 Shopify 全渠道收入是三种不同事实，不能互相替代或相加。
- GA4 key events 取决于属性配置，不等于购买；Shopify revenue 不做自然搜索渠道归因。
- 自动 decision 只使用通过可比性、覆盖和多重检验闸门的结果；发布、合并和重定向仍由人决定。

## 维护节奏

- 每次采集：查看运行状态、共同截止日和源警告。
- 每周：审阅 Pages 的高机会、高置信变化、异常和测量一致性；为实际采用的动作建立 change record。
- 每次埋点或平台配置变更：当天登记 measurement regime。
- 每月：验证 Google/Shopify 只读授权、scope、时区、币种和历史覆盖；抽查私有文件权限。
- 每次复盘：把报告写入 `projects/<id>/reports/`，引用具体产物、窗口、统计状态和下一复查日。
