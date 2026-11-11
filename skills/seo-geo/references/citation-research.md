# AI citation research

Read when a topic needs a prompt-based citation observation plan, or when a competitive landscape needs the same AI questions run across a target and its competitors. Use [seo-geo](../SKILL.md) as the canonical entrypoint for GEO work, and [competitive-landscape](../../competitive-landscape/SKILL.md) when the wider comparison includes links, content and technical evidence.

## Method

1. Construct realistic recommendation, comparison, feature and use-case prompts for the intended audience.
2. Group prompts by user task and record platform, date, locale and observation conditions for actual runs.
3. Record the returned answer, cited URLs, presence of the brand and observed source types.
4. Separate proposed prompts from executed observations and cite actual source material before proposing changes.

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

Return a prompt/task matrix and citation evidence log. For a competitive run, return the target-versus-competitor matrix with the raw rows and a short source-composition summary. Do not infer citation or conversion gains from distribution alone, and do not reduce the matrix to an aggregate score.

## Source

Adapted from the [preserved SEO Machine method](../../../third_party/skill-history/seomachine/commands/research-ai-citations.md). Its original environment and commands remain historical source material. The competitive extension is adapted from [Boom-Caoq/geo-seo-competitor-lens](https://github.com/Boom-Caoq/geo-seo-competitor-lens) at commit `49deea6cd227ed46e20edfe8138e60f1709505f2` (MIT); see [the decision record](../../../docs/history/20261111-competitive-landscape-skill.md).
