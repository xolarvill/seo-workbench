---
name: competitive-landscape
description: Use when analyzing a site's competitive landscape, comparing visibility with named competitors, or deciding where a site is behind or ahead across content, links, technical access and AI citations. Use competitor-alternatives or seo-competitor-pages when the task is to build a comparison or alternatives page.
---

# Competitive Landscape

Build a bounded, evidence-backed view of how a site compares with a small set of competitors. This is an observation and synthesis method, not a full audit of every competitor and not a scored health check.

## Read when

- The user asks "who are our competitors", "how do we compare", "where are we losing", "竞对分析", "竞争格局" or "我们和竞对差在哪".
- A strategy, content or GEO decision needs a competitor baseline rather than a single-page comparison.

If the requested output is a comparison or alternatives page, use [competitor-alternatives](../competitor-alternatives/SKILL.md) or [seo-competitor-pages](../seo-competitor-pages/SKILL.md) instead. This skill answers "what is the landscape", not "what should the comparison page say".

## Method

1. **Scope and entry check.** Confirm the target site, market/language, the decision this analysis serves and what evidence is already available. If the task is a page comparison, stop and route to the page skills.
2. **Competitor register.** Start from the user's named competitors, then observed SERP results, similar products and any provider-scoped gap set. Keep 3–5 and record why each is included, keyword overlap and the observation date. Maintain `context/competitors.md`.
3. **Target baseline and competitor observations.** Use the project's own collectors for the target. Observe competitors only at bounded public surfaces (home, about, pricing, sitemap/robots, a few representative pages). Use [backlinks](../backlinks/SKILL.md) gap only when a comparable provider export exists.
4. **GEO comparison.** Run the same question set against the target and competitors using [the citation research method](../seo-geo/references/citation-research.md). Record platform, date, locale, session/model and whether each brand appeared or was cited.
5. **Synthesize.** Compare content and citability, links and mentions, technical access, keyword and intent coverage, and AI citation visibility qualitatively. Name the largest gap and the strongest lead. Do not collapse them into one weighted score.
6. **Deliver and log.** Write the report with the five-section project format; include the step log, evidence dates and gaps. A 30/90-day plan is optional and belongs to [seo-plan](../seo-plan/SKILL.md) when requested.

Follow [the analysis workflow](references/analysis-workflow.md) for the step table, commands, artifacts and skip conditions. Use [the report template](references/report-template.md) only when a starting structure helps; it is not a completion gate.

## Completion contract

A run is complete when:

- `context/competitors.md` is current, or the report states it was reused unchanged;
- every competitor claim has a URL, date and source, or is marked `not_observed`;
- the GEO matrix uses the same questions for the target and competitors, and records unavailable platforms as `not_observed`;
- the report names the biggest gap and strongest lead with evidence pointers;
- the run log records each step as done, skipped or unavailable, with the reason.

Do not invent authority, toxicity or traffic numbers; do not present an estimate as a provider measurement; do not run a full competitor crawl.

## Source

Method adapted from [Boom-Caoq/geo-seo-competitor-lens](https://github.com/Boom-Caoq/geo-seo-competitor-lens) at commit `49deea6cd227ed46e20edfe8138e60f1709505f2` (MIT). The competitor register, cross-site GEO matrix and qualitative comparison are retained; the 0–100 scorecard and unverified authority estimates are not. See [the decision record](../../docs/history/20261111-competitive-landscape-skill.md).
