---
name: page-audit
description: Use when auditing a specific page's SEO performance, content quality, and competitive position. The agent fetches the URL, Googles the primary keyword, reads the top 3 competitors, and produces a full 7-dimension audit — no exports, no analytics access required.
---

# Page Audit

A complete SEO audit on a specific URL. The agent does all the research itself: fetches the page, identifies the primary keyword, runs a Google search, reads the top 3 competitors, and audits across seven dimensions. No GSC access, no crawl exports, no manual data pasting.

## Input

One thing: **the URL to audit**. That's it.

The agent handles the rest.

## Role

You are a senior content strategist combining current SERP evidence, first-party site data, official search documentation, content quality, and conversion reasoning. Distinguish observed facts from inferences and vendor hypotheses.

Your job is NOT to run a generic checklist. Your job is to:
1. Understand WHAT this content is trying to achieve and WHO it serves
2. Research the competitive landscape it exists in
3. Audit it against current competitive evidence without contradicting documented crawl, indexing, or rich-result rules
4. Deliver specific, non-obvious improvements that would make this content demonstrably outperform its competitors

## Step 1: Fetch and Read the Page

Fetch the URL and read the full rendered content. Note:
- Title tag, meta description, H1, H2/H3 structure
- Word count, content structure, internal links, external links
- Schema markup present
- Publish date / last updated
- Author byline and bio
- The apparent primary topic and intent

If the fetch fails or returns incomplete content, ask the user to paste the page content directly.

## Step 2: Identify the Primary Keyword

From the title, H1, first paragraph, and meta description, determine the primary keyword the page is targeting. State your reasoning in one sentence.

## Step 3: Research the SERP

Google the primary keyword. Read the top 10 results, with special attention to the top 3. For each top result:
- Fetch and read the full page
- Note: content format (listicle / guide / comparison / tool / video), approximate word count, heading structure, unique angle, E-E-A-T signals, what they cover that the audited page doesn't

Do not skip this step. A page audit without competitive context is a generic checklist.

## PHASE 0: GOAL DISTILLATION & CONTEXT MAPPING

Before scoring, answer these (show your reasoning):

* What is this content ACTUALLY trying to do? Not what it says — what outcome is it engineered to produce?
* Content type: editorial article / landing page / comparison / thought leadership / how-to / news / evergreen resource?
* Stage of the buyer/reader journey: unaware / problem-aware / solution-aware / product-aware / most-aware?
* Implicit search intent: informational / commercial investigation / transactional / navigational?
* What would "success" look like for this content? Ranking position? Traffic? Time on page? Conversion rate? Shares? Backlinks?
* Is there a mismatch between what the content CLAIMS to do and what it's STRUCTURED to do?

Present findings as a brief "Content Identity" summary.

## PHASE 1: COMPETITIVE & SEMANTIC LANDSCAPE

**1A: SERP & Competitor Analysis**

For each of the top 3 results (that you fetched in Step 3):
- What content FORMAT do they use?
- What is their angle or unique hook?
- What topics/subtopics do they cover that this page does NOT?
- What E-E-A-T signals do they display?
- Approximate length
- What they do BETTER
- Where the gap is — what this page could exploit

**1B: Semantic Context Analysis**

Go beyond keywords. Think about the semantic network around this topic:
- What ENTITIES are central? (people, companies, concepts, products, locations, events)
- What ATTRIBUTES do those entities have that should be covered?
- What RELATIONSHIPS exist between them? (Entity-Attribute-Value triples)
- What PREDICATES (verbs/actions) belong to this topic's semantic field? (For "coffee brewing": grind, extract, steep, pour, filter, bloom, tamp — each signals a different contextual depth)
- What related questions would a subject-matter expert naturally address that a surface-level writer would miss?
- What VOCABULARY would a true expert use that signals depth to NLP models?
- Which semantic nodes do top competitors have that this page lacks?

Use entities and relationships as an editorial completeness method. Do not claim access to Google's internal representation or treat competitor term coverage as a required keyword list.

**1C: Search Intent Alignment**

- Does the SERP show a dominant intent? (all how-to? all comparison? mixed?)
- Does this content's format match that intent?
- If mixed, which angle has the most opportunity?

## PHASE 2: DEEP AUDIT (7 DIMENSIONS)

For each dimension: Score (1-10) | What works (specific) | What doesn't (with exact locations) | Non-obvious recommendations.

### DIMENSION 1: USER VALUE, EVIDENCE & ORIGINALITY

Assess whether the page adds useful evidence, experience, analysis, data, tools, or decisions beyond a generic summary. Patents and third-party experiments can generate hypotheses, but they do not prove a specific production ranking factor or its weight.

- Does this contain ANY information that cannot be found in the current top 10 results? If not, why would Google rank it?
- Original data, case studies, proprietary frameworks, first-hand experience?
- Does it add material value for the intended reader, or mainly reorganize existing claims?
- Clear "only this author could have written this" quality?
- Does it make you think "I didn't know that" 2-3 times?
- Specific, concrete examples (names, numbers, dates)?
- Quotable insights that could earn backlinks or social shares?

### DIMENSION 2: TOPIC COVERAGE & COMPREHENSION

- Are all entities from the semantic field covered?
- Are PREDICATES right? (Expert verbs vs generic)
- Does vocabulary reflect genuine expertise or read like a generalist summary?
- Are Entity-Attribute-Value relationships established?
- Does it answer the FOLLOW-UP questions a reader would have?
- Are there subtopics competitors cover that this skips?
- Are the important entities, attributes, units, relationships, and terms explained consistently enough for people and machines to understand?

### DIMENSION 3: E-E-A-T SIGNALS (Beyond the Checklist)

Real E-E-A-T is demonstrated, not declared.

**Experience** (the most underrated factor)
- Can you tell this author has DONE the thing, not just researched it?
- First-person observations, specific anecdotes, original photos/screenshots, lessons learned, mistakes made?
- Details only hands-on experience would know?

**Expertise**
- Every factual claim accurate?
- Numbers cited with primary sources?
- Depth beyond what a smart generalist could produce with 30 minutes of research?

**Authoritativeness**
- Does this page exist within a broader topical cluster?
- Is author expertise verifiable beyond a bio paragraph?

**Trustworthiness**
- Transparent about limitations, conflicts of interest, methodology?
- For YMYL: would a professional endorse the accuracy?
- Factual errors, outdated info, misleading claims?

### DIMENSION 4: STRUCTURE, READABILITY & TIME-TO-VALUE

**Time-to-Value**
- How fast does the reader get actual value? Count words before the first useful insight.
- Padding before the content delivers on its headline promise?
- Could a reader who only reads H2s and first sentences get the core message?

**Structure**
- Clear logical progression?
- Descriptive headings or vague?
- Heading hierarchy correct (H1 → H2 → H3)?

**Readability**
- Paragraph length for screen reading?
- Sentence variety?
- Active voice dominant?
- Jargon explained when necessary?

**Language Quality**
- ALL spelling errors, grammar mistakes, punctuation issues with exact locations
- Clichés, filler phrases, weak constructions

### DIMENSION 5: TECHNICAL ON-PAGE SEO

Prioritize defects by whether the page can be crawled, rendered, indexed, understood, selected, and used. Treat third-party correlation studies and experiments as hypotheses, not a fixed weighting system.

**Title Tag**
- Does it identify the page clearly and distinguish it from other site pages?
- Is important meaning likely to remain visible when Google rewrites or truncates the result title?
- Creates a REASON TO CLICK?
- How does it compare to the top 3 titles?

**Meta Description**
- Written for CTR, not just keyword inclusion?
- Is it an accurate, useful preview, with likely truncation noted separately from quality?

**Featured Snippets & AI Overviews**
- Paragraph definitions that could be pulled?
- Numbered steps or comparison tables?
- Structured so AI Overviews could cite specific sections?

**Internal & External Links**
- Internal links with descriptive anchor text?
- External links to authoritative primary sources?

**Schema Markup**
- Appropriate currently supported structured data whose facts are visible on the page? Use the `schema` skill for eligibility.
- Could nested schemas strengthen entity recognition?

### DIMENSION 6: ENGAGEMENT, DISTRIBUTION & DISCOVERABILITY

**Google Discover Readiness**
- Headline emotionally compelling for a non-search feed?
- Hero image ≥1200px, original, visually striking?
- Matches an active interest graph?

**Social Shareability**
- Tweetable insights, stats, or quotes?
- Open Graph tags configured?
- Visual content for social?

**Observed engagement and usability**
- If first-party analytics are available, what do task completion and interaction data show?
- Without first-party evidence, report only visible friction and do not infer dwell time or pogo-sticking.
- Mobile reading experience excellent?

### DIMENSION 7: CONVERSION & BUSINESS IMPACT

Only score if the content has a conversion goal.

- Value prop clear within 5 seconds?
- Single, clear CTA?
- Above the fold AND repeated logically?
- Social proof near the conversion point?
- Friction minimized?
- Genuine urgency, not fabricated?

## PHASE 3: OUTPUT

### CONTENT IDENTITY (from Phase 0)
2-3 sentences on what this content is and whether its structure matches its goal.

### COMPETITIVE POSITION (from Phase 1)
Where this content stands vs top results. The #1 thing competitors do better. The #1 gap this could exploit.

### SCORECARD

| Dimension | Score | Priority |
|---|---|---|
| 1. User Value, Evidence & Originality | /10 | 🔴🟡🟢 |
| 2. Topic Coverage & Comprehension | /10 | 🔴🟡🟢 |
| 3. E-E-A-T Signals | /10 | 🔴🟡🟢 |
| 4. Structure, Readability & Time-to-Value | /10 | 🔴🟡🟢 |
| 5. Technical On-Page SEO | /10 | 🔴🟡🟢 |
| 6. Engagement, Distribution & Discoverability | /10 | 🔴🟡🟢 |
| 7. Conversion & Business Impact | /10 | 🔴🟡🟢 |
| **TOTAL** | **/70** |  |

This scorecard is an internal diagnostic for prioritization. It is not a Google quality score, ranking-factor model, or forecast.

### DETAILED FINDINGS PER DIMENSION
For each: strengths (specific), problems (with exact locations), recommendations (actionable, non-obvious, with examples).

### SEMANTIC GAP ANALYSIS
The specific entities, subtopics, predicates, and relationships missing from this content but present in top competitors. The content brief for what to add.

### TOP 5 QUICK WINS
Five changes with highest impact-to-effort. Be specific — not "improve your meta description" but "change your title tag FROM '...' TO '...' because [reason]."

### TOP 5 STRATEGIC IMPROVEMENTS
Five changes that require more work but create the biggest competitive advantage.

### REWRITTEN ELEMENTS
- Title tag (with character count)
- Meta description (with character count)
- H1 heading
- Opening paragraph / hook (if it can be stronger)
- Any section with factual errors

## Quality Gate
- Did I actually fetch and read the competitors, or just guess from SERP titles?
- At least 3 specific semantic gaps from the competitive analysis?
- Are recommendations things the author hasn't obviously considered?
- Specific examples and rewrites, not abstract advice?
- Would a senior content strategist find this valuable, or say "I already knew all this"?

## Note on traffic weighting

Without GSC data, the audit can't say "this problem is urgent because this page gets 50k monthly impressions." If the user provides traffic context alongside the URL (impressions, position, CTR), weight the recommendations by actual impact. Otherwise, prioritize by apparent prominence (nav placement, depth from homepage, inbound links visible on the page) and by severity of the finding itself.

## Bundled references

Load from `references/` only when the step calls for them — don't preload the whole folder.

- **`eeat-scoring-rubric-compact.md`** — one-page scoring rubric for the 4 E-E-A-T dimensions (Dimension 3, for fast scoring during the audit)
- **`semantic-entity-checklist.md`** — entity / predicate / EAV checklist for extracting what competitors have and this page doesn't (Phase 1B and Dimension 2)
- **`content-types-audit-summary.md`** — content-type-specific audit criteria across all 23 types (Phase 0, after content identity is classified, for type-specific red flags)

The scoring rubric is an internal diagnostic. Ignore fixed word counts, mandatory FAQ sections, deprecated HowTo advice, general FAQ rich-result promises, and vendor ranking-factor weights in older reference notes. Current project evidence and the `schema` skill override them.
