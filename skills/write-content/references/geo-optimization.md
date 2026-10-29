# Technique 06: Generative Search Observation and Content Review

## Purpose and evidence limits

Help readers and evaluate how AI search systems represent and cite existing content. Clear answers, accurate entities and traceable evidence are useful editorial methods; they do not guarantee citation, ranking or traffic. Studies describe particular models, prompts and measurement methods, not a universal optimization formula.

The original research reference is [GEO: Generative Engine Optimization](https://arxiv.org/abs/2311.09735). Preserve its experimental scope when discussing findings. Do not transfer a reported percentage into a forecast for the current site or claim access to a provider's private authority score.

## 1. Establish the actual task

Reuse the approved brief and sufficiently current research. Identify the audience, question, relevant sources and search systems being studied. Separate a request to improve content from a request to measure AI appearances; one does not prove the other.

## 2. Make answers useful and verifiable

Put a direct answer where the reader needs it, then explain conditions, evidence and limits. Use headings, steps and tables according to the question. Avoid arbitrary answer lengths or mandatory Q&A sections.

Pair material claims with named sources, dates and relevant methodology. Cite original evidence where available. Prefer appropriate current sources over cosmetic freshness: an older foundational source may remain the best reference.

Use explicit product, organization and author names when they identify actual entities. Explain relationships clearly, without padding prose with entity names. Credentials and author involvement must be genuine. Distinguish original tests, reported findings, hypothetical examples and editorial inference.

## 3. Use structured data for truthful description

Consult the [schema skill](../../schema/SKILL.md) and [shared eligibility policy](../../schema/references/search-eligibility.md). Schema.org validity, Google eligibility and observed appearance are different questions.

FAQ rich results stopped appearing for every site on 2026-05-07. Existing accurate FAQPage is not automatically a removal task, and new markup has no Google FAQ appearance to pursue. No general AI citation benefit from FAQPage is established here. Do not prescribe FAQ items, markup or update cycles to obtain vendor-reported citation lifts.

## 4. Record observable AI appearances

For a bounded observation set, record:

- Exact prompt/query, engine or product, model/version when exposed, date, market/language and session conditions.
- Whether an answer or overview appeared, and whether citation data were accessible.
- Cited URLs, the associated claims, citation placement and whether the source actually supports the answer.
- Sampling plan and repeat observations where variability matters.
- Known access, personalization and collection limits.

A missing citation in one response is a non-observation in that sample, not proof that the page is never cited or eligible. Follow project rules for private evidence and do not expose user data in prompts or shared artifacts.

## 5. Define metrics before comparing

| Observable metric | Definition and limits |
|-------------------|-----------------------|
| Prompt coverage | Share of a defined observed prompt set citing the site; report numerator, denominator and unavailable responses |
| Citation share | Site citations divided by all citations in the same sampled responses, using a declared counting rule |
| Placement | Observed citation position and context, not a provider authority score |
| Source accuracy | Whether each cited source supports the associated claim |
| Source currency | Source dates relative to the topic's actual update needs, not a mandatory 30-day cycle |

Compare equivalent prompt sets, products and collection conditions. Keep AI observation, GSC clicks, analytics sessions and business outcomes separate. Before/after differences alone do not prove that an edit caused citation changes.

## 6. Decide what to change

Use observations to locate specific reader or evidence problems: an ambiguous entity, unsupported statement, stale instruction or buried answer. Revise those problems and preserve accurate ordinary content. Do not add FAQ markup, personal claims, synthetic authority signals or unnecessary content merely to seek a citation.

Monitor meaningful content changes and topic freshness rather than changing dates on a fixed schedule. State what was actually observed and what remains uncertain.

## Key Sources

- [krillinai/GEO (GitHub)](https://github.com/krillinai/GEO)
- [awesome-generative-engine-optimization (GitHub)](https://github.com/amplifying-ai/awesome-generative-engine-optimization)
- [AgriciDaniel/claude-blog (GitHub)](https://github.com/AgriciDaniel/claude-blog) -- historical source attribution, not an established uplift
- [aaron-he-zhu/seo-geo-claude-skills (GitHub)](https://github.com/aaron-he-zhu/seo-geo-claude-skills) -- CORE-EEAT framework
- [Ahrefs: Short vs Long Content in AI Overviews](https://ahrefs.com/blog/short-vs-long-content-in-ai-overviews/)

Additional historical research links, retained for attribution rather than a general uplift claim:

- [Ahrefs](https://ahrefs.com/blog/ai-overview-citations-top-10/)
