---
name: seo-geo
description: Diagnose a page's AI-search access, answer usefulness and brand-fact consistency from observed evidence. Use for AI crawler or page-level GEO questions; use ai-prompt-research to discover questions and ai-visibility-audit to audit brand visibility across actual answers.
user-invokable: true
license: MIT
---

# AI search page diagnosis

Establish the page, user job, platform/market and decision served. Reuse project context and eligible raw/rendered observations through [Workbench operations](../seo/references/workbench-operations.md).

## Choose the task

- Question discovery or selecting an observation set: [ai-prompt-research](../ai-prompt-research/SKILL.md).
- Brand recommendations, mentions and cited sources across observed answers: [ai-visibility-audit](../ai-visibility-audit/SKILL.md).
- This page's access, content or factual diagnosis: continue here. For a broad market comparison use [competitive-landscape](../competitive-landscape/SKILL.md).

A direct page review does not require running all three methods.

## Inspect actual access

Use eligible page, robots and rendered evidence. Record status, final URL, date and access condition. A failed/challenged fetch cannot prove missing content. Distinguish training crawlers, search crawlers and user-triggered retrieval; verify current owning platform documentation before recommending a directive. Do not infer live-search access from a training opt-out or recommend allowing every crawler.

A robots permission does not prove successful retrieval or future citation. A missing llms.txt alone is not a defect, compliance failure or reason to prioritize a change.

## Inspect the answer and facts

Read the relevant main content and, when available, the actual prompt/answer and cited alternatives. Check whether the page answers the user's job with accurate, self-contained facts, useful examples, prices/policies where relevant and visible supporting sources. Inspect headings, internal discovery, public availability and rendered dependency only where they affect the job.

Use [reader-experience-review](../reader-experience-review/SKILL.md) during authorized drafting. Do not enforce a universal answer length, citation percentage, readiness score, schema advantage or fixed passage formula. Original research and tools are candidates when the audience needs them, not compulsory tactics.

For brand-fact consistency, compare dated answers with the owning product/policy pages. Quote conflicting official versions and leave resolution with the owner. No visible citation means provenance unknown, not proven model memory. Profile claiming, account verification and publishing are separate tasks requiring verified platform operations.

## Deliver

Give the supported page diagnosis, concrete change, mechanism and uncertainty, with URL/date/platform and eligibility attached. Separate observed access/content issues from visibility hypotheses. If no worthwhile change is established, say so. Do not invent AI demand, ranking, traffic or conversion gains.

For comparable answer observations retain [citation research](references/citation-research.md) as the shared evidence format; discovery is owned by ai-prompt-research and interpretation by ai-visibility-audit.

Original claude-seo provenance remains in [source inventory](../../docs/skill-sources.json); the current evidence-led adaptation and selected every-app methods are recorded in [adoptions](../../docs/skill-upstream-adoptions.json).
