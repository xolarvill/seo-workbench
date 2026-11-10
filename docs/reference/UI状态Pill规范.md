# UI Status Pill 规范

所有工作台页面统一使用 `ui/src/components/StatusPill.tsx` 的 `StatusPill`，不要在页面组件中重新实现 pill 样式或 tone 映射。公共外观位于 `ui/src/styles/global.css`。

## 颜色语义

| Tone | 颜色 | 含义 |
| --- | --- | --- |
| `success` | 绿色 | 正常、可比、已验证、完成 |
| `warning` | 黄色 | 部分可用、需复核、趋势下降、重定向 |
| `danger` | 红色 | 错误、不可比、数据不足、阻断 |
| `info` | 蓝色 | 中性分类或辅助信息 |
| `neutral` | 灰色 | 未采集、未观察、无快照、未知 |

## Context 规则

- `context="http"`：2xx 为绿色，3xx 为黄色，4xx/5xx 为红色；非 HTTP 状态为灰色。
- `context="urgency"`：critical 红色，high 黄色，medium 蓝色，low 灰色。
- `context="evidence"`：ok/comparable/strong/stable 绿色，partial/decrease/anomaly 黄色，incomparable/insufficient_data/error 红色；not_observed/not_collected/no_snapshot 灰色。
- `context="status"`：approved/indexed/已完成或已验证为绿色，计划/复核/刷新/提交索引为黄色，阻断或失败（包括 indexing_issue）为红色，其他工作流状态为蓝色。
- Keywords 工作流状态沿用同一三色语义：`prioritize` / `researched` / `mapped` / `live` / `measured` 为绿色，`unreviewed` / `hold` / `discovered` / `in_production` 为黄色，`drop` 为红色。

数值涨跌使用同一语义：正向绿色、负向红色、零或无数据灰色。普通数量、日期和原始指标不应为了装饰强行着色。
