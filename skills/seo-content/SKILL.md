---
name: seo-content
description: >
  Evaluate content usefulness, evidence, E-E-A-T, readability and AI citation
  readiness for content-focused reviews. Use for a content-quality question,
  not a full technical audit or every supplied URL. Wording-only reviews use
  reader-experience-review.
user-invokable: true
argument-hint: "[url]"
license: MIT
metadata:
  author: AgriciDaniel
  version: "1.9.6"
  category: seo
---

# Content Quality & E-E-A-T Analysis

Use current project evidence and the [Workbench operations guide](../seo/references/workbench-operations.md) for fresh collection. Record coverage and unavailable inputs alongside findings.

## Who, How and Why

Assess the actual content before treating author labels as quality evidence:

- **Who:** Is responsibility clear in the way readers reasonably expect for this page? A personal byline may help an article; an identifiable organization can be appropriate for its service page. Do not fail a brand page solely for lacking a personal byline.
- **How:** Are claims supported by an appropriate method, source or first-hand evidence? Explain production methods where readers would reasonably expect them. Credentials or an author profile do not substitute for accurate, useful content.
- **Why:** Does the page help its intended reader complete a task? Inspect actual usefulness rather than assuming quality from author status, prose style or an asserted motivation.

Recommend truthful, applicable attribution. Never invent an expert, credential, author profile, test or experience to fill a checklist. Missing attribution where expected is a scoped finding; it does not establish AI authorship or invalidate all content.

Primary guidance: [Google's helpful-content questions](https://developers.google.com/search/docs/fundamentals/creating-helpful-content).

## E-E-A-T Framework (updated Sept 2025 QRG)

Read the [E-E-A-T framework](../seo/references/eeat-framework.md) for full criteria.

### Experience (first-hand signals)
- Original research, case studies, before/after results
- Personal anecdotes, process documentation
- Unique data, proprietary insights
- Photos/videos from direct experience

### Expertise
- Author credentials, certifications, bio
- Professional background relevant to topic
- Technical depth appropriate for audience
- Accurate, well-sourced claims

### Authoritativeness
- External citations, backlinks from authoritative sources
- Brand mentions, industry recognition
- Published in recognized outlets
- Cited by other experts

### Trustworthiness
- Contact information, physical address
- Privacy policy, terms of service
- Customer testimonials, reviews
- Date stamps, transparent corrections
- Secure site (HTTPS)

## Content Metrics

### Word Count Analysis
Use length as a description of available text, not a quality floor or ranking prediction. Check whether the page answers its intended task with adequate facts, conditions and next actions. A short service page may be sufficient; a long page may still omit the deciding information. Confirm evidence coverage before calling content thin.

### Readability
- Assess comprehension in the original language and intended audience. English readability formulas do not establish Chinese readability.
- Optional language-appropriate readability scores are diagnostics, not direct ranking metrics or rewriting targets. Do not impose sentence/paragraph length quotas.
- Use [reader-experience-review](../reader-experience-review/SKILL.md) for contextual prose decisions; clear, plain writing may need no edits.

### Keyword Optimization
- Make the topic clear in the title, main heading, introduction and relevant sections without exact-match placement or density quotas.
- Use relevant entities and variations when they clarify meaning; do not add synonyms just to satisfy coverage counts.
- Inspect unnatural repetition in context rather than inferring stuffing from a percentage alone.

### Content Structure
- Logical heading hierarchy (H1 -> H2 -> H3)
- Scannable sections with descriptive headings
- Bullet/numbered lists where appropriate
- Table of contents for long-form content

### Multimedia
- Relevant images with proper alt text
- Videos where appropriate
- Infographics for complex data
- Charts/graphs for statistics

### Internal Linking
- Add internal links when their destinations help the reader's task, with no per-word quota
- Descriptive anchor text
- Links to related content
- Confirm orphan claims only with sufficient eligible same-site link coverage; absent source observations are not proof of no inlinks

### External Linking
- Cite authoritative sources
- Use links where they substantiate a claim or help the reader; no count quota or mandatory new-tab behavior

## Content Production and Quality

Assess usefulness, accuracy and misleading production claims. Prose style, missing personal bylines and AI assistance do not by themselves establish low quality or AI authorship.

### Useful content
- Answers the current reader question accurately and clearly
- Gives the source, responsibility and conditions readers need to use the answer
- Preserves appropriate detail and a structure suited to the task
- Supplies original analysis or first-hand evidence when the article promises it or the task needs it

### Problems to investigate
- Claims, instructions or product details contradicted by the available evidence
- Missing steps or context that prevent the reader completing the task
- Repetition or generic phrasing that obscures the answer
- Missing responsibility or attribution where readers need it for the claims
- Fabricated testing, author identities, credentials or quotations

A standard procedure can be complete without original research or a contrarian viewpoint. Assess the actual passage; do not require stories or novel findings to make ordinary instructions pass.

> **Helpful Content System (March 2024):** The Helpful Content System was merged into Google's core ranking algorithm during the March 2024 core update. It no longer operates as a standalone classifier. Helpfulness signals are now weighted within every core update. The same principles apply (people-first content, demonstrating E-E-A-T, satisfying user intent), but enforcement is continuous rather than through separate HCU updates.

## AI Citation Readiness (GEO signals)

Optimize for AI search engines (ChatGPT, Perplexity, Google AI Overviews):

- Clear, quotable statements with statistics/facts
- Structured data (especially for data points)
- Strong heading hierarchy (H1->H2->H3 flow)
- Answer-first formatting for key questions
- Tables and lists for comparative data
- Clear attribution and source citations

### AI search observations

Use the shared [GEO writing and measurement method](../write-content/references/geo-optimization.md) when the request includes AI-search visibility. Establish the actual query set, model/platform, date, market and observed citations; keep the sample's denominator with any comparison.

Choose useful answers, accurate entity descriptions, genuine sources and a structure that fits the reader. Select semantic markup from real page facts and an actual consumer's contract. FAQPage is not a default AI citation technique; consult [current eligibility checks](../schema/references/search-eligibility.md) and evidence for the proposed use. Do not infer private authority weights or general citation gains from a source pack's historical recipe.

## Content Freshness

- Publication date visible
- Last updated date if content has been revised
- Flag content older than 12 months without update for fast-changing topics

## Output

Report evidence-backed findings and coverage first. The historical score templates below are optional, not a default scorer. If scoring is requested, state the heuristic method, limits and unknown inputs; do not invent numerical evidence or present scores as Google metrics.

### Content Quality Score: XX/100

### E-E-A-T Breakdown
| Factor | Score | Key Signals |
|--------|-------|-------------|
| Experience | XX/25 | ... |
| Expertise | XX/25 | ... |
| Authoritativeness | XX/25 | ... |
| Trustworthiness | XX/25 | ... |

### AI Citation Readiness: XX/100

### Issues Found
### Recommendations

## Optional provider evidence

Use supplied keyword and content evidence with its provider, locale and query window. For fresh volume, difficulty or intent data, discover a relevant available integration and verify its supported operation and cost before use. Page text can be reviewed without a paid keyword provider; metrics without observations stay unobserved. See [Workbench operations](../seo/references/workbench-operations.md) for current local collection interfaces.

## Error Handling

| Scenario | Action |
|----------|--------|
| URL unreachable (DNS failure, connection refused) | Report the error clearly. Do not guess page content. Suggest the user verify the URL and try again. |
| Content behind paywall (402/403, login wall) | Report that the content is not publicly accessible. Analyze only the visible portion (meta tags, headers) and note the limitation. |
| Thin content (fewer than 100 words retrievable) | Report the findings as-is rather than guessing. Flag the page as potentially JavaScript-rendered or gated, and suggest the user provide the full text directly. |

## FLOW Framework Integration

For prompt-guided content optimization, select relevant optimize and win references from [seo-flow](../seo-flow/SKILL.md) — FLOW's optimize and win prompts provide structured E-E-A-T improvement and BOFU conversion workflows.
