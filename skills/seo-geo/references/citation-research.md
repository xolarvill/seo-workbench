# AI citation research

Read when a topic needs prompt discovery or a prompt-based citation observation plan, or when a competitive landscape needs the same AI questions run across a target and its competitors. Use [seo-geo](../SKILL.md) as the canonical entrypoint for GEO work, and [competitive-landscape](../../competitive-landscape/SKILL.md) when the wider comparison includes links, content and technical evidence.

## Prompt discovery (optional)

Use this before constructing a prompt set when the questions would otherwise come only from the analyst. Discovery produces candidates; it does not establish that anyone asks them.

1. Ask 2–3 assistants, in fresh sessions with personalization and memory off, to propose how a named audience would ask for the job: "If you were <audience> trying to <job>, what would you ask an AI assistant?" Ask for 10–15 exact phrasings across the six prompt families in Competitive extension below, not a summary.
2. Record the model, date, locale and session condition for each discovery batch. Deduplicate and cluster the phrasings by task and intent; keep the exact wording.
3. Validate every candidate against observed demand when it is available: GSC queries, site search, sales or support language, and community threads. Label each prompt's provenance as `model_generated`, `observed_query`, `customer_language` or `competitor_gap`; a model-only prompt stays exploratory and never counts as demand.
4. Freeze 6–12 validated prompts per topic or competitor set as the observation set. Keep the discovery list separate and run the frozen set unchanged across the target and competitors.

Model-generated questions are hypotheses. Answers vary by model, date, locale and account memory, and a model's suggestion is not evidence of search demand, ranking, traffic or conversion. A model's content recommendation is a candidate to test against the citation log, not a content brief. Do not publish a discovery answer as a finding without a real-demand check.

## Method

1. Construct realistic recommendation, comparison, feature and use-case prompts for the intended audience from the frozen observation set; if no set exists, run prompt discovery first.
2. Group prompts by user task and record platform, date, locale and observation conditions for actual runs.
3. Record the returned answer, cited URLs, presence of the brand and observed source types.
4. Separate proposed prompts from executed observations, record which prompts came from discovery versus observed demand, and cite actual source material before proposing changes.

## Competitive extension

When the observation is for a competitive landscape, run one question set unchanged for the target and each selected competitor. Use 1–3 competitors for a focused comparison; a larger set needs a reason and a narrower question set.

| Prompt family | Question pattern | What it tests |
|---|---|---|
| Brand | "What is <brand> and what does it do?" | Whether the brand is known and described accurately |
| Category | "What are the best <category> tools?" | Which brands appear for the category job |
| Comparison | "<brand> vs <competitor>" or "best <category> alternatives" | Which alternatives are named and in what order |
| Best-for | "Best <category> for <audience or use case>" | Which brand is recommended for a specific job |
| How-to | "How do I <task>?" | Which sources are cited for the method |
| Problem | "How do I solve <problem>?" | Which brand or source is offered for the underlying need |

Record every observed row, including misses:

| Question | Platform | Date | Locale | Session / model | Target present | Competitor A | Competitor B | Cited domains | Citation type |
|---|---|---|---|---|---|---|---|---|---|

For each cited domain, classify its type as official, media, community, docs or other. Keep the raw rows and report counts only for the observed sample; do not claim that a citation causes traffic, conversion or ranking.

If a platform is unavailable, log the access condition and mark the row `not_observed`. Do not infer a competitor's visibility from a run that only covered the target.

## Deliverable

Return a prompt discovery log, a frozen prompt/task matrix and a citation evidence log. For a competitive run, return the target-versus-competitor matrix with the raw rows and a short source-composition summary. Do not infer citation or conversion gains from distribution alone, and do not reduce the matrix to an aggregate score.

## Source

Adapted from the [preserved SEO Machine method](../../../third_party/skill-history/seomachine/commands/research-ai-citations.md). Its original environment and commands remain historical source material. The competitive extension is adapted from [Boom-Caoq/geo-seo-competitor-lens](https://github.com/Boom-Caoq/geo-seo-competitor-lens) at commit `49deea6cd227ed46e20edfe8138e60f1709505f2` (MIT); see [the decision record](../../../docs/history/20261111-competitive-landscape-skill.md). The optional prompt-discovery step was added in 2026-11 from a public AI-search practitioner discussion; see [the decision record](../../../docs/history/20261111-prompt-discovery.md). It is a hypothesis-generation aid, not a measured benchmark.
