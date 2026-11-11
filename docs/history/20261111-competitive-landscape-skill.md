# 竞对格局分析能力与流程

- 日期：2026-11-11（Asia/Shanghai）
- 范围：新增站点级竞对分析入口与流程，扩展现有 AI 引用研究；不采集竞对全站数据，不接入新 provider，不修改任何站点。
- 原因：本地已有逐词 SERP、外链 gap 和对比页制作，但没有把“竞对是谁、差在哪、AI 引用被谁拿走”串起来的站点级方法。外部仓库 [Boom-Caoq/geo-seo-competitor-lens](https://github.com/Boom-Caoq/geo-seo-competitor-lens) 的登记、GEO 对照和定性结论可以复用，其评分卡与外链估算不能直接照搬。

## 采纳与拒绝

采纳三项：

1. 竞对登记：用户指定优先，其次 SERP、相似产品和 provider 作用域 gap；保持 3–5 家，记录入选依据、关键词重叠、观察日期和地区，落在 `projects/<id>/context/competitors.md`。
2. 跨站 GEO 对照：目标与竞对使用同一组问题，按平台、日期、地区、会话/模型记录是否出现、是否被引用，以及引用来源类型；不可用平台记 `not_observed`。
3. 定性综合：按内容可引用性、链接与提及、技术可访问、关键词与意图、AI 引用可见性五项对比，指出最大缺口和最强领先；30/90 天计划保留为可选后续，不固定输出。

拒绝三项：

1. 0–100 加权评分卡。它把不同证据维度压成一个总分，和仓库“source-level metrics rather than a synthetic weighted health score”的规则冲突。
2. 无 provider 的外链域名数、dofollow 占比和权威分估算。没有可比导出时只能记录公开可观察线索，不能把估算写成测量。
3. 固定七段输出。报告继续使用项目的五段格式；模板只作可选起点，不作完成门槛。

同时修正 [seo-plan](../../skills/seo-plan/SKILL.md) 的 “Estimate their domain authority”，改为观察公开权威信号并指向本入口，避免同一个仓库里出现两套互相矛盾的竞对方法。

## 文件

- [SKILL.md](../../skills/competitive-landscape/SKILL.md)：canonical 入口、触发条件、六步方法、完成契约和来源。
- [analysis-workflow.md](../../skills/competitive-landscape/references/analysis-workflow.md)：步骤表、命令、产物、跳过条件、完成检查和 run log。
- [report-template.md](../../skills/competitive-landscape/references/report-template.md)：可选五段模板与竞对登记、观测、GEO 矩阵。
- [citation-research.md](../../skills/seo-geo/references/citation-research.md)：保留原四步，新增竞对扩展矩阵和不合成 score 的边界。
- [skills/README.md](../../skills/README.md)、[AGENTS.md](../../AGENTS.md)：索引与任务路由。
- [skill-upstream-adoptions.json](../skill-upstream-adoptions.json)：登记上游 commit，并记录评分卡与整包导入被拒绝。

## 验证

- `python3 scripts/skill_inventory.py refresh`：412 个受维护文件，`ok=true`。
- `python3 scripts/skill_inventory.py check --strict-active`：通过，无缺失字面路径。
- `.venv/bin/pytest tests/test_skill_layout.py -q`：6 passed。
- `./seo --project hexcal validate --json`：`ok=true`；仅保留既有 `projects/hexcal/audits/browser` 缺失警告，与本次改动无关。
- `git diff --check`：通过。

## 边界

本轮没有新增采集器、provider 连接、评分模型或 `workflows/*.json`。`./seo evidence` 仍是 project-scoped，竞对只能做有界公开观测；`backlinks gap` 只在已有可比 provider 导出且用户授权付费时使用，最多 3 家。没有运行真实竞对分析，因此本记录不声称任何竞对结论、引用率或排名变化。
