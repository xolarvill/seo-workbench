---
name: write-content
description: Use when writing a complete SEO article. Includes the full anti-AI-slop ruleset (banned vocabulary, banned phrases, banned structural patterns) and voice rules. The agent researches the SERP itself if needed — no keyword data exports required.
---

# Write Content

Writes a complete SEO-optimized article. Four phases: research → content type decision → knowledge extraction → write. Includes the full anti-AI-slop ruleset and the voice rules that make the output sound like a practitioner, not a press release.

## Input

- **Topic or target keyword** (required)
- *(Optional)* An existing content brief — skip the research phase if provided
- *(Optional)* Expert interview output from the `expert-interview` skill

If no topic is given, ask for one before proceeding.

## Business context persistence

Business context (audience, tone, language, brand voice, examples) shapes every article. In this Workbench, read the current project's `context/`, `strategy/`, existing content, and state before asking repeated questions. Save new business context only inside the current project after the user authorizes the content. Never write it to global agent instructions or another store's folder.

Questions on first use:
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

State it plainly:
"The top results for [keyword] are all [format]. I'll write a [content type] with [key structural element]. Sound good, or did you have something else in mind?"

Wait for confirmation.

Load `references/content-types-overview.md` for optional page patterns. Then load one relevant template when it helps. Template headings, lengths, CTA positions, and schema suggestions are starting points, not requirements. The `schema` skill and current Google documentation are authoritative for rich-result eligibility.

## Phase 3: Knowledge Extraction

Ask 2-3 quick questions to extract unique knowledge the user has. Pick from:

- "What do most people get wrong about [topic]?"
- "Can you give me a specific example — a client, a project, a number?"
- "What surprised you when you actually did this?"
- "Who should NOT follow this advice, and why?"

Ask one at a time. Keep it quick.

**Adapt style**:
- Newer/smaller site, less SEO-savvy user: conversational, explain why each question matters
- Established site, experienced user: fast, direct, no hand-holding

## Phase 4: Write the Article

**Length**: Do not target a specific word count or copy competitor depth mechanically. Cover the user's task with enough verified evidence and explanation, then stop.

Produce the complete article in clean markdown. Follow ALL of these rules:

### Voice and Stance
- Write like a practitioner talking to a peer. Not a textbook, not a press release.
- Take clear positions when evidence supports them. Never claim “we tested” unless the project contains that test or the user supplied it.
- Use "you" and "I/we" — write to one person, not an audience.
- Use specific numbers, names, and dates only when verified or supplied by the user. Never invent specificity to make prose sound experienced.
- Weave in interview answers as first-person experience. Preserve phrasing where it sounds natural.
- Use contractions: "doesn't" not "does not."
- Preserve genuine changes in reasoning when they exist; do not fabricate a personal story as a stylistic device.
- Anchor in real context — reference current events, industry shifts, or cultural touchstones where relevant.

### Rhythm and Structure
- Vary sentence length dramatically. Mix 5-word punches with 30-word complexes. Never 3+ consecutive sentences of similar length.
- Vary paragraph length. One-sentence paragraphs are fine. So are 6-sentence ones.
- Use fragments for emphasis. Start sentences with "And" or "But" when natural.
- Include parenthetical asides and brief tangents — humans do this, AI doesn't.
- Shift registers. After a technical explanation, drop into a casual aside. Uniform register = AI tell.
- Break the topic-sentence-support pattern. Start some paragraphs with an example, a question, or a statement that only makes sense after reading on.
- Cover sections asymmetrically. Spend 500 words on the interesting part and 50 on the boring-but-necessary one.
- Don't summarize at the end of sections unless genuinely complex (3+ subsections).

### Show, Don't Just State
- Use concrete examples when they clarify a real mechanism. Do not turn an uncertain ranking claim into a fictional scenario.
- For claims backed by documented experience, explain what was tried, what happened, and what remained uncertain.

### Anti-Slop Rules

**NEVER use these words** — highest-signal AI tells:
delve, landscape (metaphorical), testament, leverage, utilize, robust, seamless, furthermore, moreover, additionally, pivotal, multifaceted, harness, embark, navigate (metaphorical), showcase, streamline, paramount, culminate, spearhead, commence, endeavor, vibrant, innovative, comprehensive (as adjective).

**NEVER use these phrases:**
"It's worth noting", "In today's [anything]", "Let's dive in", "In conclusion", "plays a crucial/vital/pivotal role", "It goes without saying", "In the realm of".

**Avoid these structural patterns:**
- Rule-of-three groupings (use 2 or 4 items instead)
- Synonym cycling (repeat the right word rather than finding alternatives)
- Copula avoidance ("serves as" — just say "is")
- Em-dash chains (max 1-2 per 1000 words)
- Binary contrasts ("it's not X, it's Y" — just make the argument)
- Participial tack-ons ("...highlighting the importance of X" — delete or make a separate sentence)
- Clustering of: however, notably, essentially, that said, arguably — fine individually, but 3+ in one article flags AI

### Content Type Structure

- **How-to**: 40-60 word quick answer first (featured snippet target), then numbered steps, each step = one action with "what goes wrong"
- **Comparison**: Verdict first ("Choose A if... Choose B if..."), then detailed analysis
- **Listicle**: Summary table above fold, consistent evaluation framework per item
- **Definition**: "[Term] is..." in the first sentence, no preamble
- **Case study**: Lead with the result number, then the story (PAS framework)
- **Pillar page**: Table of contents, overview, then link to deep-dive articles
- **Service/landing page**: PAS framework. Pain point first, agitate consequences, then solution

### SEO Structure
- Make the topic clear in the title, main heading, introduction, and relevant sections without exact-match quotas or density targets.
- Put direct answers where they improve time to value. Paragraphs, lists, and tables should match the information, not a fixed snippet formula.
- Use PAA questions only when they support the page's main task.
- Add internal links where they help users continue a task or understand a relationship. Use descriptive anchor text and do not target a per-word quota.
- Front-load value. The first screen is the highest-value real estate. No preamble paragraphs.

### Long Article Strategy
- Write section by section. Track what you've covered to prevent repetition and voice drift.
- The article should contain enough first-party evidence, examples, analysis, or experience to justify publishing it. Do not fabricate these elements or enforce an arbitrary percentage.

### Final Checks

1. **"So What?" test**: For each major section — could anyone have written this, for anyone, about anything? If yes, inject specific knowledge.
2. **Self-check**: Scan for blacklisted words, sections where every paragraph starts with a topic sentence, unnecessary section summaries, participial tack-ons. Fix before delivering.

### Output

Clean markdown. Title + article content. Nothing else.

### Language

Write in the language from the business context. If not specified, match the language of the user's messages.

## Bundled references

Load from `references/` only when the step or rule calls for them. Don't preload — each file is heavy enough to blow context if stacked.

**Content type templates** (`references/content-types/`) — load one after Phase 2:
- Common: `how-to.md`, `definition.md`, `comparison.md`, `listicle.md`, `pillar-page.md`, `faq-page.md`, `landing-page.md`, `service-page.md`, `case-study.md`
- Content and news: `statistics-page.md`, `news-article.md`, `glossary-page.md`
- Commercial: `alternatives-page.md`, `buying-guide.md`, `product-page.md`, `category-page.md`, `integration-page.md`, `location-page.md`, `programmatic-page.md`
- `references/content-types-overview.md` for the decision table across all 23 content types (load this FIRST if unsure which type to pick)

**Writing technique modules** (`references/`) — load only when the matching rule needs more depth:
- `anti-slop-ruleset.md` — full tiered banned vocab + structural tell list (when the inline anti-slop block isn't catching something)
- `voice-injection-playbook.md` — voice and register techniques (when the draft reads flat)
- `eeat-signal-embedding.md` — how to surface experience without a bio section
- `structured-data-snippets.md` — current structured-data eligibility boundaries and content formatting
- `fact-checking.md` — how to verify every specific number and claim
- `human-input-framework.md` — the knowledge-extraction questions (reinforces Phase 3)

Other archived technique notes may contain vendor benchmarks, fixed keyword densities, outdated rich-result advice, or hypotheses about private ranking systems. Do not load them as execution rules. Current project evidence, the shared content-type overview, the `schema` skill, and current primary documentation override them.
