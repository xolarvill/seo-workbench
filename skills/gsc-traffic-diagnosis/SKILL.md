---
name: gsc-traffic-diagnosis
description: Use when GSC clicks, impressions, CTR or rankings drop or fluctuate, or when query and page regex filters are needed to isolate affected directories, markets or search intent.
---

# GSC 流量变化诊断

先定位变化集中在哪里，再选择能区分假设的检查。适用于整站、目录、单页的搜索表现排查；不是自动改写、删页或提交索引的授权。

方法改编自 [CoderJeffLee 原帖](https://x.com/CoderJeffLee/status/2122132239286927503)。读取 [来源与采用边界](references/source-notes.md) 了解原帖、官方补充和本地适配的区别；需要筛选时读取 [SEO 正则工具箱](references/regex-cookbook.md)。

## 先建立可比基线

读取 [Google 集成](../../docs/reference/google-integrations.md)、[统计口径](../../docs/reference/统计学SEO操作手册.md) 和 [结果闭环](../../docs/reference/SEO迭代闭环.md)。优先复用有效的当前项目证据。确需补采且任务授权时，纯搜索诊断使用：

```bash
./seo --project example-store gsc performance --days 28 --compare --json
```

跨来源生产统计用现有 `statistics collect`。先查命令 help；GSC CLI 当前没有 regex、country 或 device 筛选参数。正则在 GSC 后台或已有导出上应用，不虚构 CLI 参数。独立 country、device 汇总不能拼成某 URL 在某国某设备的查询证据；需要这种联合切片时用后台筛选或明确的联合维度导出。

保留 property、搜索类型、两窗起止、数据时区、finalized 状态、国家/设备/搜索外观筛选和覆盖情况。比较等长完整窗口；按需补同比检查季节性。跨测量口径断点或数据不完整时先标记不可比，不解释为真实下滑。

## 按范围缩小假设

在「网页」按绝对点击损失排序，同时看百分比和原始点击；先分清少数大页拖累还是普遍下降，再在相同范围看曝光、CTR 和平均位置。

| 范围 | 优先检查 | 能推进判断的证据 |
|---|---|---|
| 首页、商品、博客等一起下降 | 搜索状态面板/数据异常、上线时间、抓取与索引、模板和渲染；再查内容质量 | 多模板 URL 的同窗查询损失，以及可复现的技术或内容问题；更新时间重合只能形成假设 |
| 某目录/模板下降 | 目录筛选后检查损失集中度；抽查共用模板的正文、TDK、canonical 和索引 | 多个代表页的实际输出与变更记录；模板正常后再检查选题批次、写法、时效性 |
| 少量页面下降 | 精确 URL → 查询 → 目标国家/设备，优先丢失点击最多的词 | 当地当前 SERP 的页面类型、竞争者、信息时效；没有历史 SERP 时不能声称谁取代了谁 |

曝光下降可能涉及需求、可见性或索引；CTR 下降可能涉及结果外观、查询组合或排名；平均位置是聚合值，须看相同查询/市场/设备，避免组合变化冒充排名变化。查询行只有可观测子集，保留其与页面总点击的覆盖差额。

页面曾有曝光或进入前排不证明内容质量已过关。Review、Best、Alternatives 类页面反复波动时，可检查实测证据、主题覆盖、支持页和有效内链，再与同站同类页及当前竞品对照。DR 不是 Google 指标；不据此推定内容容忍度，也不把“主题权威不足”当已证实原因。

## 验证与交付

技术假设转交 [technical-audit](../technical-audit/SKILL.md)，SERP 意图问题转交 [keyword-deep-dive](../keyword-deep-dive/SKILL.md)，主题支撑问题转交 [topic-cluster-planning](../topic-cluster-planning/SKILL.md)，只展开当前证据指向的分支。

URL Inspection API 描述已索引版本；后台实时测试与当前 raw/rendered HTML 是不同证据。确认缺陷、修复并验证实际输出后，才按授权另行处理索引请求；不因排名下滑就批量 reindex。

诊断交付写清：影响范围与绝对损失、指标变化、按证据排序的假设、反证/缺口、最小下一步、复查日期和负责人。按项目报告规范保存，附原始证据路径及置信度。多页面 CTR 异常进入行动队列前走现有 FDR 流程；普通正则分组不是显著性检验，前后变化不是因果。
