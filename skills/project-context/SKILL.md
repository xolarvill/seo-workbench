---
name: project-context
description: Create or maintain project brand voice and search-direction context. Use for initial context, changed positioning or keyword ownership, and stale or conflicting keyword plans.
---

# Project Context

Create durable operating context for later SEO skills. Separate verified facts from working assumptions and keep each store's files inside its own project directory.

## Brand voice

Write `context/brand-voice.md` with:

- status: approved, supplied, or inferred;
- positioning and primary audiences;
- voice traits with concrete do/don't guidance;
- evidence and claim standards;
- editorial and localization guardrails.

Keep these as operating context. Future writers use evidence standards to select supported claims, and the [evidence-to-prose method](../reader-experience-review/references/evidence-to-prose.md) to decide which conditions readers need. Brand guardrails and lists of unperformed tests do not become mandatory disclaimers or article slogans.

If no approved brand guide is available, infer a working draft from the project state and public site evidence. Label it as inferred and list what the owner must confirm. Do not present inferred tone or audience as approved fact.

## Target keywords

Use [keyword context maintenance](../../docs/keyword-context-maintenance.md) when creating, relying on, or updating this file. It defines file responsibilities, decision and evidence handling, update triggers, and handoff checks.

Keep `context/target-keywords.md` as a concise search-direction summary with:

- applicable audience, market, language and scope;
- confirmed intent groups and boundaries, separated from working hypotheses;
- the actual maintained location of detailed query-to-page ownership and priorities;
- supporting decision/research paths, relevant evidence dates and unresolved validation needs;
- a last substantive review date and what was reviewed; link to historical launch lists in dated project reports rather than keeping release-specific tables in context.

Maintain detailed keyword decisions and page ownership in one declared strategy location, not in a second full table here. The keyword workspace uses `strategy/keyword-pool.jsonl`; Markdown is not imported or synchronized automatically. Existing manual projects may keep an explicitly identified plan without first creating a keyword pool.

Update affected context and ownership records in the same task as an authorized strategy change. Reuse still-applicable research; refresh only the evidence needed for the current decision. A missing file, old date, unlisted keyword or historical phase does not prohibit work.

Base keyword selection on applicable observed SERP evidence; reuse suitable research and collect fresh evidence when the decision requires it. If Search Console, paid keyword volume, conversion, or margin data is unavailable, say so and avoid traffic or revenue forecasts.

## Completion checks

- Keep verified facts, evidence-backed inference, and unknowns visibly separate.
- Preserve regional differences instead of combining incompatible prices, claims, or product specifications.
- Give each selected primary intent one intended owner page in the declared ownership record, or mark the assignment unresolved; do not fabricate a URL or research to fill the summary.
- Save the context in the current project; preserve existing approved documents and their actual paths.
- Check the saved artifact against the requested scope, record unresolved facts and supporting evidence, and run `./seo --project <id> validate --json` when state or workflow contracts changed. No phase transition or next-step command is required.
