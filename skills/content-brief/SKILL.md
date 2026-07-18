---
name: content-brief
description: Use when planning a new article. The agent Googles the keyword, reads the top 10 results, classifies intent, maps the content gap, and produces a writer-ready brief with structure, outline, and on-page artifacts. No keyword tool required.
---

# Content Brief

A writer-ready content brief based on real SERP analysis. The agent Googles the target keyword, reads the top 10 results, classifies intent, identifies competitor gaps, and produces the brief. No keyword tool exports, no manual SERP pasting.

## Input

**Target keyword** (required). Optionally: business context if you want the brief tailored to a specific audience/tone.

If the user didn't provide a keyword, ask for it before proceeding.

## Role

You are a senior content strategist and SEO brief specialist. Produce a writer-ready brief from current SERP evidence, the site's business context, and primary sources. Ranking pages are competitive evidence, not a substitute for user needs or official eligibility rules.

## Step 1: Research the SERP

Google the target keyword. Read the top 10 results. For each top-ranking page, note:
- Content format (listicle / long-form guide / comparison / how-to / tool / video)
- Approximate word count
- Heading structure (H1, main H2s)
- Content angle and unique hook
- What they cover that others don't
- Whether they appear to hold a featured snippet, People Also Ask positions, or other SERP features

## Step 2: Identify Search Intent

Classify dominant intent: **Informational / Commercial Investigation / Transactional / Navigational**.

Use intent to decide the work the page must complete. Estimate scope from required questions, evidence, comparisons, media, and conversion needs. Competitor length is a descriptive observation only. Do not create a minimum word count or use a top-result average as a target.

## Step 3: Map the People Also Ask

If PAA questions appear, record them as current SERP observations. Use only the questions that support the page's main task; they do not automatically become headings or an FAQ block.

## Step 4: Identify Content Type

Pick the content type from the SERP pattern. Content types: how-to, definition/explainer, comparison, listicle, product-review, case-study, pillar-page, faq-page, landing-page, service-page, category-page, buying-guide, alternatives-page, pricing-page, location-page.

Load `../write-content/references/content-types-overview.md` for content-type patterns. Treat its structures as options, not quotas. For rich-result eligibility, the `schema` skill and current Google documentation override older examples in content templates.

## Step 5: Produce the Brief

### Target Keyword Analysis

- Primary keyword | Apparent difficulty based on SERP competition | Dominant intent
- Difficulty explanation based on observable result types, brand competition, intent fit, evidence burden, link profile proxies, and the site's current position. Use scenarios and uncertainty, not promised timelines.
- Related terms to target on the same page (from what the top pages cover as H2s)

### SERP Competitive Intelligence

For each of the top 3 competitors:
- URL | Estimated words | Format type | Key sections covered | What they miss

### Content Gap Analysis

Specific subtopics covered by 2+ top competitors but missing from where most results are thin. Name exact missing sections — not generic "add more depth."

### Recommended Outline

H1 and H2/H3 structure aligned to search intent and the gap analysis. Include:
- **Featured snippet target**: which H2 hosts the 40-60 word snippet answer — mark the spot
- **PAA integration**: questions to address as H2/H3 headings
- **Supporting questions** only when they reduce a real decision or comprehension gap

### Hub & Spoke Architecture
- This piece as: hub / spoke / standalone (based on keyword breadth)
- Internal linking pattern recommended

### Technical Optimization
- **Title tag**: distinctive and accurate; include the primary topic naturally and preview likely truncation without treating character count as a ranking rule
- **Meta description**: accurate click preview; report likely truncation without imposing a fixed length
- **Schema**: only a currently supported type whose required facts are visible on the page; validate through the `schema` skill
- **Featured snippet format**: paragraph (what is) / ordered list (how to) / table (comparison)

### E-E-A-T Signals Required
- Author expertise markers needed
- Original data or research to include
- External authoritative sources to cite

### Resource Assessment
- **Effort**: Low / Medium / High based on research, first-party evidence, production, expert review, media, and implementation work
- A measurable review window and leading indicators, without promising a ranking position

## What to Ignore

- **Keyword density targets** — write naturally and make the topic unambiguous; do not require exact-match placements or percentages
- **NLP term lists of 50+ words** — focus on 5-8 core entities that must appear
- **Word count without checking SERP** — "write 3,000 words" without intent matching creates padded content

## Next Step

Brief ready? Use the `write-content` skill with this brief as context to write the article.

## Bundled references

Load these from `references/` only when the step calls for them — don't preload.

- **`../write-content/references/content-types-overview.md`** — decision patterns for picking a content type (Step 4)
- **`../write-content/references/structured-data-snippets.md`** — current markup and eligibility boundaries (Step 5)
- **`../write-content/references/human-input-framework.md`** — questions for extracting real expert input
- **`../write-content/references/fact-checking.md`** — claim and source verification
