# Competitive landscape analysis workflow

Use with [competitive-landscape](../SKILL.md). This is a default order, not a scheduler. Skip a step only when its entry condition fails, and record the reason in the run log.

## Step table

| Step | Read or run | Artifact | Done when |
|---|---|---|---|
| 1. Scope and entry check | Target URL, market/language, decision served, existing evidence; the page skills if the output is a comparison page | Scope line in the report | Target, market and evidence boundary are explicit |
| 2. Competitor register | User-named competitors, observed SERP results, similar products, provider gap set | `context/competitors.md` | 3–5 competitors, each with a reason, overlap and date |
| 3a. Target baseline | Existing project artifacts; project collectors when authorized | Evidence table | Target claims have a pointer and date, or a stated gap |
| 3b. Competitor observations | Bounded public pages; provider-scoped link gap when comparable | Evidence table | Every observation has URL, date, surface and access condition |
| 4. GEO comparison | [Citation research](../../seo-geo/references/citation-research.md) competitive mode | Question × platform matrix | Same questions for target and competitors; unavailable rows are `not_observed` |
| 5. Synthesis | The evidence tables | Findings | Biggest gap and strongest lead are named with evidence pointers |
| 6. Report and run log | [Report template](report-template.md) if useful | Five-section report | Every step is logged as done, skipped or unavailable |

## 1. Scope and entry check

Confirm the target site, the market and language, the decision this analysis serves, and which evidence already exists. Read the project's `AGENTS.md`, current context and audit pointers before collecting.

If the user wants a comparison or alternatives page, stop. Use [competitor-alternatives](../../competitor-alternatives/SKILL.md) or [seo-competitor-pages](../../seo-competitor-pages/SKILL.md).

## 2. Competitor register

Use sources in this order:

1. Competitors the user named.
2. Observed results for 2–3 core category or comparison queries.
3. Similar products the target's own pages, pricing or positioning make relevant.
4. A provider-scoped gap set, if one already exists and is comparable.

Keep 3–5. A larger set needs a reason and a smaller observation depth.

Maintain `projects/<id>/context/competitors.md` in this shape:

```markdown
# Competitors

Last reviewed: YYYY-MM-DD
Market / language: ...
Target: https://...

| Competitor | URL | Why included | Keyword overlap | Evidence date | Notes |
|---|---|---|---|---|---|
| Example | https://example.com | SERP top 3 for "category" | high | YYYY-MM-DD | direct product match |
```

Reuse the file when it is still current. Update the date and changed rows; retain removed competitors with a reason instead of silently deleting them. Do not add a competitor merely because it ranks for one unrelated query.

## 3. Target baseline and competitor observations

### Target

Use the project's own collectors and existing artifacts. Typical explicit operations:

```bash
./seo --project <id> evidence --json
./seo --project <id> tech-audit run --json
```

Add `--rendered` only when the browser runtime is available. Reuse current audit pointers before collecting again. `./seo evidence` is project-scoped and has no `--url`; do not point it at a competitor.

### Competitors

There is no project-scoped collector for an external competitor. Observe only bounded public surfaces:

- home page, about, pricing and one or two representative category or product pages;
- `robots.txt`, sitemap index and a sample of sitemap URLs;
- rendered HTML where access and the question require it.

For each observation record: entity, URL, surface, observed date, market/language, access condition (public page, user export, provider) and status. Use `not_observed` for a page or signal that was not available; do not turn it into zero.

If a comparable provider export exists, [backlinks](../../backlinks/SKILL.md) gap can compare up to three competitors:

```bash
./seo --project <id> backlinks gap --competitor <domain> --confirm-paid
```

Only run it with the user's paid-collection authorization. A partial or non-comparable provider export cannot prove a link gap.

Do not create a project directory for a competitor, run a full crawl of its site, or present a bounded sample as a full audit.

## 4. GEO comparison

Use the competitive extension in [citation research](../../seo-geo/references/citation-research.md). Build one question set and run it unchanged for the target and each competitor:

| Family | What it tests |
|---|---|
| Brand | Whether the model knows and describes the brand |
| Category | Which brands appear for the category job |
| Comparison | Which alternatives are named for "X vs Y" or "best X" |
| Best-for | Which brand is recommended for a specific audience or use case |
| How-to | Which sources are cited for the task |
| Problem | Which brand or source is offered for the underlying problem |

Record each observed row:

| Question | Platform | Date | Locale | Session / model | Target present | Competitor A | Competitor B | Cited domains | Citation type |
|---|---|---|---|---|---|---|---|---|---|

Keep the raw rows. Classify cited domains as official, media, community, docs or other. Report what was observed in this sample; do not claim that a citation causes traffic or conversion. If a platform is inaccessible, record `not_observed` with the access condition.

## 5. Synthesis

Compare qualitatively across:

- content and citability;
- links and mentions;
- technical access and crawlability;
- keyword and intent coverage;
- AI citation visibility.

Name one largest gap and one strongest lead. Keep the evidence pointer next to each. Do not add the dimensions into a weighted total, a 0–100 score or a synthetic health index.

A 30/90-day plan is optional. When the user asks for one, hand the findings to [seo-plan](../../seo-plan/SKILL.md) rather than inventing priorities here.

## 6. Report and run log

Write `projects/<id>/reports/YYYYMMDD_ops_competitive-landscape.md` with the project's five sections: `结论` → `方法与覆盖` → `证据` → `边界` → `后续`. Put the run log at the end of the report:

| Step | Status | Reason / evidence |
|---|---|---|
| 1. Scope | done | ... |
| 2. Register | done | `context/competitors.md` |
| 3a. Target baseline | done / skipped | pointer or reason |
| 3b. Competitor observations | done / partial | ... |
| 4. GEO comparison | done / partial | ... |
| 5. Synthesis | done | ... |
| 6. Report | done | this file |

Status is `done`, `partial`, `skipped` or `unavailable`; a skipped step always has a reason.

## Skip conditions

- No named competitor and no usable SERP evidence: ask for a competitor or record the register gap; do not invent one.
- No comparable provider export: skip the link gap and say so.
- A platform or page is inaccessible: record `not_observed`, not a negative finding.
- Target evidence is absent and collection is not authorized: record the gap; do not compare against an empty baseline.
- The requested output is a comparison page: route to the page skills instead of producing a landscape report.

## Completion checklist

- [ ] `context/competitors.md` is current or explicitly reused.
- [ ] Every competitor claim has URL, date and source, or `not_observed`.
- [ ] The same GEO questions were used for target and competitors.
- [ ] Synthesis names the biggest gap and strongest lead, without an aggregate score.
- [ ] The run log covers every step.
- [ ] The report uses the five-section format and records evidence limits.
