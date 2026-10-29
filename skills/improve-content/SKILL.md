---
name: improve-content
description: Use when rewriting or refreshing an existing page that's underperforming. Read the page, analyze search intent and evidence, and improve its usefulness with the shared reader-experience review.
---

# Improve Content

Improves an existing page's usefulness and search relevance through supported explanations, appropriate structure and the shared reader-experience review.

## Input

**Existing page URL or supplied content**, with the requested outcome. Retrieve available project copies, approved update notes and adequate evidence before asking for missing text. A failed fetch leaves that observation unavailable; it does not invalidate a sufficient supplied copy.

For a full refresh, use the relevant steps below. For an approved local change, edit the affected passage and preserve the rest; skip research and interview steps that the decision does not need. Review-only requests use [reader-experience-review](../reader-experience-review/SKILL.md).

## Role

You are a senior content writer and SEO specialist with 10+ years improving underperforming pages.

## Step 1: Read the Current Content

Read the current supplied page or eligible project evidence. Collect fresh page evidence only when needed. Note relevant title, metadata, headings, links and markup; identify the page's topic and reader task.

## Step 2: Research the SERP

For a competitive refresh, reuse adequate research or inspect current results when needed. Note:
- What formats are ranking
- Content gaps where the current page falls short
- Angles competitors take that this page doesn't
- Any featured snippet / PAA opportunities

This is a lightweight check, not a full page audit. Just enough to know what's missing.

## Step 3: Update Interview

Reuse the current page, approved update notes and available evidence. When a focused interview is useful and fits the request, ask one question at a time:
- "What's changed since you published this? New data, new experience, market shifts?"
- "What results did this content get? Traffic, leads, feedback?"
- "Knowing what you know now, what would you add or cut?"

When the user requests the revision directly, skips an interview or supplied sufficient update notes, proceed with supported material. Keep optional first-party gaps in the task/editorial artifact. Ask only for a missing fact essential to the requested result; do not fabricate fresh experience or insert a missing-interview disclaimer into otherwise supported prose. Use [freshness review](references/content-freshness.md) to choose what needs changing.

## Step 4: Rewrite

Produce the requested revision in clean markdown: a complete article for a full refresh, or the affected passages for a scoped edit. Apply relevant writing rules below:

### Evidence and Expression
- Preserve accurate facts, useful explanations and the page's requested tone. Choose person, register, sentence length and paragraph structure for comprehension in the original language, including plain Chinese or English.
- Take positions supported by evidence. Verify or retain supplied sources for numbers, names and dates; never invent specificity, tests, results, personal experience or changes in reasoning.
- Attribute interviews and observed cases to their actual source. Use first person only when the author can truthfully own the experience.
- Add an example only when it clarifies a mechanism, and distinguish a hypothetical illustration from an observed case. Do not replace an adequate explanation with an invented story or contrarian opening.
- Follow `../reader-experience-review/SKILL.md` for prose decisions. Negative sentences, lists of three, repeated technical terms, punctuation and familiar phrases need contextual assessment, not automatic deletion. Do not impose word bans, punctuation quotas, sentence-length patterns, asides or register changes.

### SEO
- Make the topic clear in the title, main heading, introduction and relevant sections without exact-match or density targets.
- Put direct answers where they help readers; use paragraphs, lists and tables according to the explanation rather than a fixed snippet length.
- Use PAA questions when they support the page's actual task. Add internal links with descriptive anchor text when they help readers continue that task; use no per-word quota.
- Preserve useful existing metadata, headings, links and factual qualifications unless the requested improvement warrants a change. Use the `schema` skill and current primary documentation for structured-data eligibility.

### Content type

Detect from the existing page + SERP. Load `references/content-types-overview.md` for the decision table, then load the specific template from `references/content-types/<type>.md` when useful. Template headings, lengths, CTA positions and schema suggestions are starting points, not requirements. Bundled templates include how-to, definition, comparison, listicle, pillar-page, faq-page, landing-page, service-page, case-study, statistics-page, news-article, glossary-page, alternatives-page, buying-guide, product-page, category-page, integration-page, location-page and programmatic-page.

- **How-to**: Give the direct answer and steps in working order; explain failure conditions where they affect an action.
- **Comparison**: Explain who each option suits and support the distinctions.
- **Definition**: Define the term directly, then explain relevant use or limits.
- **Case study**: Present documented outcomes, context and method, preserving uncertainty and attribution.

### Final checks
1. Check that changes help the reader complete the task and that claims match available evidence. Keep unresolved evidence gaps in the task artifact; qualify public claims when readers need the qualification.
2. Check topic clarity, useful headings, relevant links and content-type fit without keyword or link quotas. Preserve sound existing material.
3. Use `../reader-experience-review/SKILL.md` to check the revised prose in context. Prioritize confusion, instruction leakage, invisible arguments and broken transitions. Keep factual limitations, correct terms and useful source or example labels. Adequate plain prose can pass with zero edits; do not manufacture changes to satisfy a style pattern or imply AI authorship. Review-only requests belong to that skill and do not require this full SERP/rewrite workflow.

### Output
Clean markdown: title and revised article for a full refresh, or the requested passages for a scoped edit. Keep editorial evidence notes in the task artifact.

### Language
Write in the same language as the existing page content.

## Bundled references

Load from `references` only when needed — don't preload the whole folder.

**Content type templates** (`references/content-types`) — load one in Step 4:
- Common: `how-to.md`, `definition.md`, `comparison.md`, `listicle.md`, `pillar-page.md`, `faq-page.md`, `landing-page.md`, `service-page.md`, `case-study.md`
- Content and news: `statistics-page.md`, `news-article.md`, `glossary-page.md`
- Commercial: `alternatives-page.md`, `buying-guide.md`, `product-page.md`, `category-page.md`, `integration-page.md`, `location-page.md`, `programmatic-page.md`
- `references/content-types-overview.md` for the decision table across all 23 content types (load this FIRST if unsure which type to pick)

**Rewriting technique modules** (`references`) — load when a rule calls for more depth:
- `anti-slop-ruleset.md` — historical wording prompts; use only to investigate a specific reader problem, never as word bans or structural quotas
- `voice-injection-playbook.md` — optional techniques for a specific clarity or requested voice problem; do not force personality into adequate prose
- `content-freshness.md` — decay signals and what to refresh vs. leave alone (the core of Step 3's update interview)
- `writing-pipeline.md` — the research → rewrite → edit loop adapted for updates
- `quality-scoring.md` — scoring rubric to run before delivering the rewrite

Supporting references may contain word bans, mandatory stylistic quirks, fixed keyword densities or outdated SEO advice. Do not adopt these as execution rules. This entrypoint and the shared reader-experience review govern prose decisions; current project evidence, the shared content-type overview, the `schema` skill and current primary documentation govern SEO claims.

## Adapted specialist and workflow references

Read the matching reference when it supports the current task:

- [SEO editing review](references/seo-editing.md): a researched article needs focused on-page improvements.
- [Existing-page refresh](references/refresh-workflow.md): an existing article needs a scoped refresh rather than a new unrelated page.
- [Targeted optimization](references/optimization-workflow.md): a draft or page needs specific SEO improvements.

## Research evidence

Use [source verification](../write-content/references/fact-checking.md) for factual claims and source currency. Keep evidence notes with the task artifact and reader-useful conditions with the relevant claim.
