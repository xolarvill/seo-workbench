# Title Craft

Use this before drafting and again at metadata review. A title is not a label added after the article is finished. It is the shortest promise the article must keep.

## The rule

A useful title compresses one true, specific thing the article delivers: a decision, a finding, a method, a comparison, a failure mode or a constraint. Clarity is the floor. Specificity and a reason to read are the craft.

If the article has no distinct finding, judgment or method, fix the article before polishing the title. A title cannot make a generic article specific.

## 1. State the angle first

Before writing the draft, complete one sentence in the brief or outline:

> After reading this, the reader can ______, will know ______, or will avoid ______.

Use a real finding, decision or constraint from the research. Do not fill the sentence with "understand the basics" or "learn best practices." If the sentence cannot be completed honestly, the article is not ready for a title.

Keep the angle visible while drafting so the sections actually support it.

## 2. Generate candidates by strategy

Generate six to eight candidates, not one safe default. Label the strategy for each so the set is not eight variations of the same idea.

| Strategy | What it looks like | Use when |
|---|---|---|
| Specific outcome | The decision or result the reader gets | The article supports a concrete outcome |
| Named object, place or number | A real entity, dataset, threshold or count | The article contains the named thing and can support it |
| Common mistake | The failure mode the article explains | The article has observed or documented the mistake |
| Tradeoff or cost | What the reader gives up, pays or risks | The article honestly compares options |
| Reader situation | The identity or constraint that changes the answer | The article is written for a distinct reader |
| Comparison | X vs Y, or when to choose each | The article makes a supported distinction |
| Counterintuitive finding | The result that differs from the default assumption | The evidence supports the surprise |
| How-to with a boundary | The method plus the condition where it applies | The article has a real method and limits |

Rules for the candidate set:

- Every candidate must be truthful to the article and its evidence.
- Do not add a number, year, superlative or "best" unless the article supports it. An unsupported modifier is not specificity.
- Do not use a strategy just to fill a slot. Skip it when the article has nothing behind it.
- Do not imitate a competitor's title or a SERP pattern verbatim.

Illustrative patterns only, not claims about a real page:

- Topic label: `A Practical Guide to X`
- Specific decision: `When X Is Worth the Migration Cost`
- Failure mode: `Why X Projects Stall After the Pilot`
- Constraint: `X for Teams That Cannot Change Their CMS`

## 3. Select against criteria

Choose one primary title and one or two alternates. Judge each candidate on:

- **Intent fit**: it matches the page's query and page type; it does not promise a different article.
- **Specificity**: it contains a concrete noun, decision, condition or finding, not only a topic plus a generic modifier.
- **Truth**: every number, year, comparison and superlative is supported by the article or cited evidence.
- **Differentiation**: it says something a generic article on the same topic would not say. This is about the substance of the promise, not clever wording.
- **Voice**: it fits the brand and the reader; do not force humor, provocation or a persona the page does not use.
- **Display**: put important words early and check truncation in the target language and layout. Character counts are drafting aids, not universal limits or ranking guarantees.
- **One promise**: do not stack several claims into one title.

Prefer the candidate that is both accurate and worth clicking. Do not choose the most clickable option at the expense of truth.

Record why the selected title fits and which claims still need verification.

## 4. Title, H1 and description

- **Title**: lead with the query or subject and the specific value. It may differ from the H1.
- **H1**: state the reader-facing promise or angle. It can be more editorial than the title.
- **Meta description**: expand the same promise with one concrete detail and the next step. Do not repeat the title word for word.
- **Slug**: keep it short, stable and descriptive. Do not change it for title polish after publication without a redirect plan.

These surfaces must agree on the facts, not repeat the same sentence.

## 5. Optional: post-publication CTR diagnostic

When GSC data has enough impressions, compare CTR at similar average positions, for the same page type and query class. Record the window, device and country. Treat the result as a diagnostic, not causal proof that the title change produced the difference. Do not run an A/B test on low traffic, and do not rewrite a title for CTR without rechecking intent and accuracy.

## Avoid

- Defaulting to `Best`, `Top`, `Complete`, `Ultimate`, `Free` or the current year when the article does not support the claim.
- Two topics or two promises in one title.
- `A Guide to X` when the article actually makes a specific argument.
- Unsupported numbers, `proven`, `guaranteed` or invented urgency.
- Keyword stuffing or exact-match repetition.
- Matching the top SERP titles rather than differentiating on substance.
- Summarizing the article instead of giving a reason to read it.

## Output

Return:

1. The angle sentence.
2. A candidate table: candidate, strategy, supporting fact, risk.
3. The selected title and the reason it fits.
4. H1 and description notes.
5. Claims or facts that still need verification.

## See also

- [SEO optimization layer](seo-optimization-layer.md) for the final metadata check.
- [Quality scoring](quality-scoring.md) for the broader content acceptance check.
- [SEO flow title prompt](../../seo-flow/references/prompts/local/prompt-generating-a-title-tag.md) for a runnable title-generation prompt.
