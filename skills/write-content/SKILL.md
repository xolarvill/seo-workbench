---
name: write-content
description: Write a complete SEO article, or prepare an approved article for the existing Workbench draft and delivery workflow. Reuse adequate briefs, research and project context.
---

# Write Content

## Expression method

Use [reader-led writing and review](../reader-experience-review/SKILL.md) as the single method for prose decisions while drafting and revising. This skill supplies task methods and inputs. Its templates and examples are optional aids; they do not add style rules or mandatory expression passes. Deliver the user's requested format.

Writes a complete SEO article. Four phases: research → content type decision → knowledge extraction → write. Use evidence to answer the reader's task and the shared reader-experience review to assess the prose.

## Delivery mode

When the task is to import an existing approved article or prepare its CMS handoff, read [draft handoff](references/draft-handoff.md) and [Workbench operations](../seo/references/workbench-operations.md). Use the supplied article, metadata and current project state. Perform the requested import or validation, then report its actual state. The topic questions and creation phases below apply when writing an article; delivery work does not restart them.

## Input

- **Topic or target keyword** (required)
- *(Optional)* An existing content brief — skip the research phase if provided
- *(Optional)* Expert interview output from the `expert-interview` skill

If no topic is given, ask for one before proceeding.

## Business context persistence

Business context (audience, tone, language, brand voice, examples) shapes every article. In this Workbench, read the current project's `context/`, `strategy/`, existing content, and state before asking repeated questions. Save new business context only inside the current project after the user authorizes the content. Never write it to global agent instructions or another store's folder.

Fill only material gaps after reading existing project context. Useful questions when needed:
- What does the business do, and who is it for?
- What's the brand's tone of voice? (Professional / Casual / Technical / Authoritative / Conversational)
- What language should content be written in?
- What topics should NEVER appear? (compliance, competitor mentions, etc.)
- Who are the 2-3 main competitors?

## Phase 1: Research

If a content brief wasn't provided, Google the topic and read the top 5 results. Note: what formats are ranking, what angles exist, what gaps you see. 3-5 bullet points, not a full brief.

Skip this phase entirely if a brief or prior conversation context already contains SERP analysis.

## Phase 2: Content Type Decision

Based on what's ranking, pick a content type: how-to, definition/explainer, comparison (X vs Y), listicle/roundup, product review, case study, pillar/ultimate guide, FAQ, landing page, service page, news/trend analysis.

Use an approved brief or choose a format from the reader's task and available research. When the user requests a complete draft in one pass, proceed with a brief statement of any material assumption. Ask about format only when an unresolved choice materially changes the requested result; do not turn an already-decided format into a confirmation gate.

Load `references/content-types-overview.md` for optional page patterns. Then load one relevant template when it helps. Template headings, lengths, CTA positions, and schema suggestions are starting points, not requirements. The `schema` skill and current Google documentation are authoritative for rich-result eligibility.

## Phase 3: Knowledge Extraction

Reuse available interview answers, approved project facts and research. If first-party input is necessary and an interview fits the request, ask focused questions such as:

- "How do you handle [specific task] in practice?"
- "Can you give me a specific example — a client, a project, a number?"
- "What surprised you when you actually did this?"
- "Who should NOT follow this advice, and why?"

Ask one at a time when conducting an interview. For a direct drafting request or a run without an available interview, continue from supported sources. Keep optional first-party gaps in the task/editorial artifact. If the requested result depends on missing test data, quotations or product facts, narrow the claim or ask for that essential input; do not invent it or repeat the missing-interview status in the article.

**Adapt style**:
- Newer/smaller site, less SEO-savvy user: conversational, explain why each question matters
- Established site, experienced user: fast, direct, no hand-holding

## Phase 4: Write the Article

**Length**: Do not target a specific word count or copy competitor depth mechanically. Cover the user's task with enough verified evidence and explanation, then stop.

Produce the complete article in clean markdown. Follow ALL of these rules:

### Evidence and Expression
- Answer the reader's question directly, in the requested tone. Choose person, register, sentence length and paragraph structure for clarity in the article's language; plain Chinese or English can remain plain.
- Take clear positions when evidence supports them. Use specific numbers, names and dates only when verified or supplied by the user. Never claim a test, result or personal experience without supporting evidence.
- Attribute interview answers to the actual speaker. Use first person only when the author can truthfully own the experience; an interview does not make it the writer's experience.
- Use examples when they clarify a mechanism. Distinguish hypothetical illustrations from observed cases, and never turn an uncertain claim into an invented story.
- Include current events, changes in reasoning, comparisons or limitations when they help readers use the answer. Do not add an objection, contrarian opening, anecdote or reassurance to make the writing appear experienced.
- Follow `../reader-experience-review/SKILL.md` for prose decisions. Lists of three, negative sentences, repeated technical terms, punctuation and familiar phrases are not defects by themselves. Do not impose word bans, punctuation quotas, sentence-length patterns, asides or register changes.

### Content Type Structure

Use these patterns when they serve the task; short explanations do not need a full article template.

- **How-to**: Give the direct answer and steps in working order. Include failure conditions where they affect an action.
- **Comparison**: Explain who each option suits, with evidence for the distinctions.
- **Listicle**: Use consistent evaluation criteria; add a summary table when it helps comparison.
- **Definition**: Define the term directly, then explain its relevant use or limits.
- **Case study**: Present the documented outcome, context and method. Preserve uncertainty and attribution.
- **Pillar page**: Provide navigation and links to relevant detailed explanations.
- **Service/landing page**: Explain the reader's need and the supported offer without inventing or amplifying a problem.

### SEO Structure
- Make the topic clear in the title, main heading, introduction, and relevant sections without exact-match quotas or density targets.
- Put direct answers where they improve time to value. Paragraphs, lists, and tables should match the information, not a fixed snippet formula.
- Use PAA questions only when they support the page's main task.
- Add internal links where they help users continue a task or understand a relationship. Use descriptive anchor text and do not target a per-word quota.
- Front-load value. The first screen is the highest-value real estate. No preamble paragraphs.

### Long Article Strategy
- Write section by section. Track what you've covered to prevent repetition and voice drift.
- Support the article's claims with appropriate evidence and explanation. First-party tests or cases are valuable when available, but their absence does not require invented experience or an editorial disclaimer in an otherwise supported explanation.

### Final Checks

1. **Task and evidence**: Check that each section helps the reader complete the task and that factual claims match available evidence. Keep unresolved evidence gaps in the task artifact; qualify public claims when readers need the qualification.
2. **SEO usefulness**: Check topic clarity, descriptive headings, helpful links and the relevant content-type structure without counting keyword or link quotas.
3. **Reader comprehension**: Use `../reader-experience-review/SKILL.md` on the actual draft before delivery. Assess whole passages for instruction leakage, invisible arguments, confusing transitions and reader actions. Preserve useful caveats and correct terms. Clear, plain prose can pass with zero edits; do not rewrite to satisfy a style pattern or imply AI authorship.

### Output

Follow the user's requested format. For a complete article, default to clean Markdown with title and article body; for body-only copy, return that body. Keep internal review and evidence notes in the existing task artifact.

### Language

Write in the language from the business context. If not specified, match the language of the user's messages.

## Bundled references

Load from `references` only when the step or rule calls for them. Don't preload — each file is heavy enough to blow context if stacked.

**Content type templates** (`references/content-types`) — load one after Phase 2:
- Common: `how-to.md`, `definition.md`, `comparison.md`, `listicle.md`, `pillar-page.md`, `faq-page.md`, `landing-page.md`, `service-page.md`, `case-study.md`
- Content and news: `statistics-page.md`, `news-article.md`, `glossary-page.md`
- Commercial: `alternatives-page.md`, `buying-guide.md`, `product-page.md`, `category-page.md`, `integration-page.md`, `location-page.md`, `programmatic-page.md`
- `references/content-types-overview.md` for the decision table across all 23 content types (load this FIRST if unsure which type to pick)

**Writing technique modules** (`references`) — load only when the matching rule needs more depth:
- `anti-slop-ruleset.md` — historical wording prompts; use only to investigate a specific reader problem, never as word bans or structural quotas
- `voice-injection-playbook.md` — optional expression techniques for a specific clarity or requested voice problem; do not force personality into adequate prose
- `eeat-signal-embedding.md` — how to surface experience without a bio section
- `structured-data-snippets.md` — current structured-data eligibility boundaries and content formatting
- `fact-checking.md` — how to verify every specific number and claim
- `human-input-framework.md` — the knowledge-extraction questions (reinforces Phase 3)

Supporting references may contain word bans, mandatory stylistic quirks, vendor benchmarks, fixed keyword densities, outdated rich-result advice or hypotheses about private ranking systems. Do not adopt these as execution rules. The reader method alone governs prose decisions; this entrypoint governs task scope and delivery; current project evidence, the shared content-type overview, the `schema` skill and current primary documentation govern SEO claims.

## Adapted specialist and workflow references

Read the matching reference when it supports the current task:

- [Research-to-article handoff](references/article-workflow.md): an article requires coordinating research, a brief and a draft.
- [Draft production handoff](references/drafting-workflow.md): a writer-ready brief is being turned into an article.
- [Draft delivery handoff](references/draft-handoff.md): an approved article needs metadata and CMS delivery preparation.

## Research evidence

Use [source verification](references/fact-checking.md) for factual claims and source currency. Keep evidence notes with the task artifact and reader-useful conditions with the relevant claim.
