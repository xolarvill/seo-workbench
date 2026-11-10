# docs/ 清理：删除过期计划与验收记录

日期：2026-11-10。状态：已执行（删除 10 个文档，修复全部入链）。

## 结论

`docs/` 原有 42 个 Markdown，混着运行契约、教程、来源留痕和一次性验收记录。本轮删掉 10 个不再描述现行契约的文档，把根目录降到 32 个，并修好所有入链。保留的四类文档各有明确职责：运行契约（AGENTS 路由指向）、来源与迁移留痕、中文教程、仍在维护的来源记录。

## 方法与覆盖

判定标准只有一条：**文档是否仍在描述现行的契约或方法**。

- 过期或已被覆盖（4 个）：`clarity-mcp-integration-plan.md`（五阶段已执行完，内容落在 `clarity-integrations.md` 与验收记录里）、`crawl-reliability-pilot.md`（重爬契约已在 `technical-audit.md`）、`capability-preservation.md`（来源归属与 `skill-sources.md`、`skill-layout-migration.json` 重叠）、`hexcal-blog-migration.md`（飞书适配器按旧残留处理，见"边界"）。
- 一次性验收与评估（6 个）：`20261026-agent-led-workbench-acceptance.md`、`20261026-local-skill-integration-diagnosis.md`、`20261027-analytics-mcp-assessment.md`、`20261028-clarity-mcp-acceptance.md`、`20261028-clarity-usage-diagnosis.md`、`agent-skill-routing-design.md`。它们的结论都已进入 AGENTS.md、`clarity-integrations.md` 或现行技能记录；结论留在这些文档里，过程不再单独留档。

保留：12 个运行契约文档、`skill-sources.md` 与 `20261029-skill-layout-migration.md` 两个来源留痕、10 篇中文教程、5 个 `20261029-*` 技能记录、`20261104-keyword-context-maintenance-acceptance.md`（项目报告引用它）、`20261110-agent-instruction-structure.md`。

## 证据

- 入链修复：`README.md:162` 的 pilot 链接改指 `technical-audit.md` 的重爬契约；`README.md:260` 与 `docs/README.md` 删除 6 条对应条目；`docs/20261029-local-skills-review.md:40` 去掉指向已删验收记录的链接；`docs/skill-layout-migration.json` 的 `existing_local_dependencies` 从 218 条降到 217 条。
- 全仓链接检查（README、AGENTS、CLAUDE、docs 下 36 个 md）：0 条真实断链；仅剩 `docs/keyword-context-maintenance.md` 两处 `YYYYMMDD` 占位示例，属预期。
- 全仓检索 10 个文件名：无残留引用（`cli.py`、`feishu_gateway.py` 等代码不受影响）。
- `pytest tests/test_skill_layout.py tests/test_skill_methods.py` 通过（技能清单与迁移边不依赖已删文档）。

## 边界

- `hexcal-blog-migration.md` 是 `content import-hexcal`、`feishu_gateway.py`、`templates/hexcal-feishu-profile.json` 的手册。删除后这些代码暂时**没有根目录文档**；按"飞书是旧残留"的现行判断先当历史处理，代码本身未动。
- 本轮只删除与修链，没有搬目录：`docs/` 仍是平铺，教程与历史记录还和契约文档挤在一起。是否拆 `guides/`、`history/` 子目录另议。
- `docs/skill-sources.md` 仍引用 5 个 `20261029-*` 技能记录；它们描述现行技能布局，故保留。

## 后续

- 决定 `docs/` 是否按 `guides/`（10 篇教程）与 `history/`（技能记录与验收）分层，若分层需同步改 README、`docs/README.md` 与 `skill-sources.md` 的链接。
- 处理 hexcal 适配器：要么补一份简短适配器文档，要么连代码一起清理，避免长期"有代码无文档"。
- 在 `AGENTS.md` 的仓库形状一节写明项目级文档的落点（`projects/<id>/reports/`、`context/`、`strategy/`），根 `docs/` 只放仓库级内容。
