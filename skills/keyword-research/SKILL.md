---
name: keyword-research
description: Discover and prioritize keyword opportunities from a product, audience, seed topics, first-party queries or competitor coverage. Use before a target query is chosen; use keyword-deep-dive for detailed research of one known query and seo-cluster to group an existing set.
---

# Keyword opportunity research

Turn a business question into a bounded, evidence-backed candidate set and a page recommendation. Discovery does not select strategic targets automatically.

## Start with the decision

Read project context and the [keyword register contract](../../docs/reference/keyword-context-maintenance.md), then the selected project's target register and linked decisions. Establish audience, job, market/language, product fit and whether the user wants discovery, a competitor gap or prioritization of existing queries. Reuse adequate research and the existing keyword pool; ask only for essential missing facts.

## Choose a discovery mode

- **Seeds / existing demand:** use product categories, problems and available GSC query-page observations. Distinguish current impressions from unexplored demand. Near-ranking filters are diagnostics, not universal selection thresholds.
- **Customer task:** record who searches, what they want to accomplish and the language they actually use. Label website/model inference separately from supplied positioning. Generate alternatives and questions, then inspect SERPs to verify that the results serve this customer and job.
- **Competitor gap:** use comparable provider-scoped ranking sets or supplied exports. Match market, ranking depth, date and result type; record pagination, limits and coverage. A keyword missing from a sampled set is a candidate gap, not proof the site has no ranking. Validate decisive gaps with a targeted lookup; unavailable evidence stays unknown.

Read [provider selection](../seo-dataforseo/SKILL.md) only when provider data is needed and [Google evidence](../seo-google/SKILL.md) for first-party reads. Discover actual operations through [Workbench operations](../seo/references/workbench-operations.md); no OpenSEO MCP connection is assumed.

## Evaluate and hand off

Normalize duplicate phrasing without merging distinct intent. Preserve exact queries and provenance. Filter by business and audience fit before volume; keep meaningful niche terms with unavailable volume as exploratory candidates. A missing metric is not zero; KD zero is interpreted according to the provider's contract.

Inspect current, applicable SERPs for the candidates whose intent or feasibility decides the shortlist. Note page types, competitors and existing intended owners. Group close variants provisionally without adding overlapping volume buckets as independent demand. Use [seo-cluster](../seo-cluster/SKILL.md) when page-level grouping needs substantive work; a tiny set can use a simple map. Use [keyword-deep-dive](../keyword-deep-dive/SKILL.md) for disputed or high-value individual queries.

Deliver a shortlist plus rejected/deferred candidates with reasons: query/family, customer job, evidence date/market/source, metrics if observed, existing/proposed page, main uncertainty and recommended next action. Distinguish retain, strengthen, create, further research and do not target. No CTR, conversion or revenue forecast without the required evidence.

Save in the existing task artifact. Use the keyword pool's current CLI operations when operational persistence is requested; do not invent synchronization. When this authorized task actually selects or removes a strategic target, update the maintained register through [project-context](../project-context/SKILL.md) with decision links and history. A research-only request leaves targets unchanged.

The current keyword collector applies source-specific filters and a diagnostic score. Read its help and input coverage before use; zero returned candidates does not mean zero source queries or no demand. For niche opportunities inspect the underlying observations and retain meaningful exploratory candidates instead of treating the collector's thresholds or score as strategic approval.

## Source

Adapted from OpenSEO keyword-research and every-app customer-keywords / keyword-gap; fixed revisions and local source IDs are recorded in [the adoption ledger](../../docs/skill-upstream-adoptions.json). Local evidence, authorization and lifecycle rules govern execution.
