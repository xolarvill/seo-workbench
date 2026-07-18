---
name: keyword-deep-dive
description: Use when planning to rank for a specific keyword. The agent Googles it, reads the top 10, classifies intent, reads the top 3 competitor pages, and produces a 90-day ranking plan with intent, SERP analysis, and content recommendations.
---

# Keyword Deep Dive

A complete picture of a single keyword's opportunity — intent, competition, what it takes to rank, and a specific 90-day plan. The agent does all the research itself. No keyword tool required.

## Input

**Target keyword** (required). Optionally: a URL if you already have a page targeting this keyword.

If the user didn't provide a keyword, ask for it before proceeding.

## Role

You are a senior SEO strategist specializing in keyword intelligence and SERP analysis.

## Step 1: Research the SERP

Google the target keyword. Read the top 10 results in detail, the top 3 in full.

Note for each top 3:
- Domain (note authority proxies: is it a known brand? Specialist vs generalist?)
- Content format (guide / comparison / listicle / tool / video / product page)
- Approximate word count
- Unique angle or hook
- Freshness signals (publish date, last updated)
- E-E-A-T signals present

## Step 2: Classify Intent

Classify dominant intent: **Informational / Commercial Investigation / Transactional / Navigational**.

**Click-opportunity assessment:**
- Record the current result layout, including AI features, featured snippets, local, shopping, video, image, forum, and knowledge results.
- Explain which user needs may be satisfied on the results page and which still require a site visit.
- Use GSC impressions, clicks, CTR, devices, and countries when available. Do not apply a universal zero-click percentage or vendor CTR curve to one keyword.
- If citing an external CTR study, identify its dataset, date, market, and limitations. Keep it separate from observed site evidence.

## Step 3: Assess SERP Features

What SERP features are active?
- Featured snippet (what format — paragraph, list, table? Who holds it?)
- People Also Ask (how many questions? What are they?)
- AI Overview
- Image pack / video carousel
- Local pack
- Site links
- Knowledge panel

## Step 4: SERP Volatility Signal

Can you tell if the SERP is stable or turbulent?
- If top results look freshly updated / have "Updated YYYY" in the title → moderate volatility
- If multiple top results are from different years (2021, 2024, 2026) → stable
- If results are all dated past 6 months with news angles → turbulent
- If you can't tell → say so, don't fabricate

## Step 5: Competitive Read of Top 3

Fetch and read the top 3 pages. For each:
- Key sections they cover
- Word count
- Internal linking patterns (what they link to)
- What they cover that others don't
- What they do that's genuinely hard to replicate (original data? First-party screenshots? Proprietary frameworks?)

## Step 6: Output

### Keyword Profile
- Keyword | Apparent search intent | Estimated difficulty (Easy / Moderate / Hard based on SERP competition, not a KD score)
- SERP features present and their likely click implications, clearly separated from measured GSC impact
- Zero-click risk: Low / Medium / High

### Competitive Read
For each of the top 3 competitors:
- URL | Domain authority proxy | Format | Words (approx) | Unique angle | What they do best

### Content Gaps (what's missing from top results)
Specific subtopics or angles that top-ranking pages don't cover well. These are where a new entrant can differentiate.

### Ranking Strategy

**If the user has no existing page for this keyword:**

**Quick assessment:**
- Is this keyword worth pursuing? (Intent match to business? Traffic potential? Zero-click risk?)
- Plausible scenarios, dependencies, and review windows. Do not promise a ranking position or fixed timeline from a single SERP snapshot.

**Content requirements:**
- Content type to build (matches SERP)
- Required scope and evidence; competitor word counts are context, not a target
- Sections that MUST be covered (from competitive read)
- Unique angle this page should take (from gap analysis)
- E-E-A-T signals required

**If the user already has a page ranking:**

**Position diagnosis:**
- Current position apparent from Google? (If not in top 100, note this)
- Compared to the top 3, what's missing? Specific evidence, task coverage, format, intent alignment, or usability?

**Optimization plan:**
- Quick wins (title/meta rewrite for CTR, add missing section, fix intent mismatch)
- 30-day content plan (sections to add, depth to deepen)
- Supporting cluster pages to create for internal linking

### Title Tag & Meta Rewrites

Propose 2 title options and 1 meta description. Include a preview-length warning when useful, but do not treat 60/160 characters as ranking limits.

### Ranking Timeline Estimate

- Current position (or "unranked"): [X]
- 90-day indicators to review: indexing, impressions, query coverage, CTR, qualified visits, and conversions as applicable
- Effort: Low (CTR fix) / Medium (content update) / High (new content + internal links)

## What to Ignore

- **KD scores alone** — meaningless without reading the actual SERP. Use the read above instead.
- **Volume without business fit** — judge the query by audience, click opportunity, conversion path, and strategic value
- **Assuming a result type is unwinnable** — explain format and authority disadvantages, then identify a different intent or asset when appropriate

## Next Step

Need a full content brief to execute the ranking plan? Use `content-brief` with this keyword as context.

## Bundled references

Load references only when they help interpret the current result page. `serp-features-recognition.md` can help inventory visible features and `serp-volatility-heuristics.md` can frame uncertainty. Do not load bundled CTR curves, universal zero-click percentages, or fixed ranking timelines as site evidence. Prefer current GSC data and clearly sourced, dated market studies.
