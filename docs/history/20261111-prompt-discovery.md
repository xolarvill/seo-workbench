# GEO prompt 反推法引入

- 日期：2026-11-11（Asia/Shanghai）
- 范围：只把“让 AI 反推用户会怎么问”的 prompt discovery 步骤引入 [citation-research.md](../../skills/seo-geo/references/citation-research.md)，并更新 [seo-geo/SKILL.md](../../skills/seo-geo/SKILL.md) 的参考索引。不引入文章里的工具页优先、AI referral 渠道、Cloudflare 放行或 FAQ/schema 建议。
- 原因：现有方法从分析师构造的 prompt 开始，缺少从模型侧获取真实问法变体的发散步骤。用户提供的公开帖子（@geektao0319，2026-11-03，转述 @gefei55 的分享）给出三步反推流程；只采纳其“生成候选问法”的做法，不采纳其样本数据、页面类型结论或因果表述。

## 采纳内容

- 新增可选 Prompt discovery 四步：2–3 个模型、fresh session、10–15 条原始问法；记录 model/date/locale/session；去重聚类；用 GSC、站内搜索、销售或客服语言、社区真实表达验证并标注 provenance；冻结 6–12 条 observation set。
- 明确 model-generated prompts 是假设，不是需求；不得据此推断 ranking、traffic 或 conversion；模型的内容建议是待验证候选，不是 content brief。
- Method 第 1 步改为从 frozen observation set 构造 prompt；第 4 步记录 discovery 与 observed demand 的来源差异；Deliverable 增加 prompt discovery log 和 frozen prompt/task matrix。

## 边界

- 没有新增采集器、provider、评分模型或 `workflows/*.json`。
- 没有引入文章中的 1,350/436 样本、“文章 AI 流量为 0”、10+ FAQ、FAQPage/HowTo schema、AI referral 渠道或 Cloudflare 配置建议。
- 反推法只做候选生成；真实需求仍需 GSC、站内搜索、客户语言或社区证据。没有运行真实站点观测，因此本记录不声称任何引用率、流量或排名变化。

## 文件

- [citation-research.md](../../skills/seo-geo/references/citation-research.md)：新增可选 Prompt discovery，调整 Method 与 Deliverable。
- [seo-geo/SKILL.md](../../skills/seo-geo/SKILL.md)：参考索引补充 prompt discovery。
- [skill-sources.json](../skill-sources.json) 与 [skill-sources.md](../skill-sources.md)：刷新指纹与依赖记录。

## 验证

- `python3 scripts/skill_inventory.py refresh`：412 个受维护文件，`ok=true`。
- `python3 scripts/skill_inventory.py check --strict-active`：通过，无缺失字面路径。
- `.venv/bin/pytest tests/test_skill_layout.py tests/test_skill_inventory.py tests/test_skill_methods.py -q`：16 passed。
- `./seo --project hexcal validate --json`：`ok=true`；仅保留既有 `projects/hexcal/audits/browser` 缺失警告，与本次改动无关。
- `git diff --check`：通过。
