# AGENTS.md 任务路由与汇报合同

## 结论

`AGENTS.md` 从 136 行、63 条平铺规则改为 99 行：`Start` 4 条 → `Task routing` 13 行表 → 三组守则（证据与断言 / 收集 / 数据、秘密与界面）→ `Reporting` 5 节合同 → 仓库形状与命令。`CLAUDE.md` 从 26 行收到 19 行，只保留指针和两条日常命令。目标是让 agent 先按任务找到 owner 文档，再用少量守则兜底，而不是逐条读完一份手册；汇报按固定结构产出。

## 方法与覆盖

- 基线：读取 `AGENTS.md`、`CLAUDE.md`、`README.md`、`docs/README.md`；对 63 条 Working Rules 逐条判定"留 / 合并 / 外移 / 删"，并以只读方式确认每条规则的 owner 文档是否存在（`docs/reference/technical-audit.md`、`docs/reference/google-integrations.md`、`docs/reference/统计学SEO操作手册.md`、`docs/reference/SEO迭代闭环.md`、`docs/reference/shopify-integrations.md`、`docs/reference/clarity-integrations.md`、`docs/reference/browser-runtime.md`、`docs/reference/UI状态Pill规范.md`、`docs/reference/UI帮助气泡规范.md`、`docs/skill-sources.md` 等）。
- 报告实况：`projects/*/reports/` 共 16 份子报告、141 个一二级标题；结论、方法、证据、边界、后续五个概念都存在，但节名分别出现 摘要、结论先行、判断与建议、证据台账、证据红线、跟进日期 等变体，合同据此固定为 `结论 / 方法与覆盖 / 证据 / 边界 / 后续`。
- 逐主题确认后才落盘：汇报合同 → 骨架 → 入口与技能 → 命令与仓库形状 → 证据与收集 → 集成与数据 → 统计、结果与页面。每批先给处理表，确认后再执行。

## 变更清单

删除（过时或重复）：

- Daily Commands 与 init 示例，`README.md` 的 Quick start 和 Common commands 已有。
- 飞书符号与飞书适配器限制，属旧残留，默认不参与。
- "第三方仓库非运行时依赖"声明，已由"不恢复外部依赖"兜底。
- Lighthouse "browser resolved by `setup.sh`"，该说法不准确：`setup.sh` 只在 `--local-browser` 时安装 Chromium，运行时浏览器由 `seo_workbench_tools/browser_runtime.py` 解析。
- `CLAUDE.md` 的"不要 git pull 第三方目录"，第三方仓库已不是运行时依赖。

外移：

- uv 回退命令 → `README.md` → `Setup requirements`。
- 性能、渲染、技术鉴定的重复细则由 Task routing 指向各 owner 文档；`AGENTS.md` 只保留会改变结论的边界和默认值。

保留但压缩为条款：证据资格不等于严重度、`not_observed` 不等于 0、逐指标 `insufficient_data`、FDR、指纹验证、有效内链、页面只读台账、`guarded_proxy`、凭证 `0600`、分层提交。

## 证据

- 文件：`AGENTS.md` 99 行；`CLAUDE.md` 19 行；`README.md` 新增 uv 回退 5 行。
- 提交：`30b1f40` 路由与守则（含 README 外移）、`1f5b7d3` 汇报合同、`ce1ba76` Claude 薄适配、本记录所在提交。
- 链接检查：解析 `AGENTS.md`、`CLAUDE.md` 的全部相对链接，0 断链。
- `validate --json`：默认项目未初始化时报 `state.not_found`（`projects/default/state.json`），与本次文档变更无关；`./seo` 在本机未安装，实际以 `.venv/Scripts/python.exe -m seo_workbench` 执行。

## 边界

- 未改 `skills/`；工作树中 `skills/README.md`、`skills/keyword-deep-dive/SKILL.md`、`skills/project-context/SKILL.md` 的未提交改动属于其他工作，未纳入本次提交。
- 存量 16 份子报告与周报不回改，合同只约束新报告。
- 时区仍按项目各自记录（`default` 为 UTC、`neational` 为 Asia/Shanghai），合同只要求写明时区，不统一取值。
- 未测量 agent 的实际遵守率；本次只验证结构、链接和命令入口。

## 后续

- 下一份新报告按 5 节写；若某节长期为空，再评估合并，不预先删节。
- owner 文档改名或迁移时同步更新 Task routing 表。
- 新增证据源或界面时，先在 routing 表登记"先读 / 绝不许"，再决定是否进入守则。
