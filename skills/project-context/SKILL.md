---
name: project-context
description: Create or maintain project brand voice and the target keyword register. Use for initial context, keyword selection or removal, changed positioning or page ownership, and conflicting keyword plans.
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

Maintain `context/target-keywords.md` as a cumulative target keyword register with:

- applicable audience, market, language and scope;
- actual current target keywords, each linked to its decision/report or research, plus selection date and intended page when known;
- candidates kept separate from confirmed targets;
- a Targets but removed section retaining removed keywords, removal dates, reasons, decision links and replacements where applicable;
- the latest substantive update and relevant market/language boundaries. Keep detailed launch plans, research and rationale in linked reports, while retaining the selected keywords themselves here across releases.

This file owns the maintained strategic target list; do not reduce it to a document portal or move all selected keywords into reports. The keyword workspace uses `strategy/keyword-pool.jsonl` for discovery and operational data. Reflect affected register decisions there through existing operations when used; Markdown is not imported or synchronized automatically, and a collected query does not become a selected target merely by being in the pool.

When an authorized task selects a keyword, add it to current targets in the same task with its decision link. When strategy removes it, move it to Targets but removed rather than deleting it. Update affected page mappings, preserve history, and keep undecided proposals separate. Reuse still-applicable research; refresh only evidence needed for the decision. A missing file, old date, unlisted keyword or historical phase does not prohibit supported research.

Base SEO recommendations about which keywords to select on applicable observed SERP evidence; reuse suitable research and collect fresh evidence when needed. Register an explicit user target choice immediately with its decision link, recording research gaps in the linked report rather than requiring research before registration. If Search Console, paid keyword volume, conversion, or margin data is unavailable, say so and avoid traffic or revenue forecasts.

## Completion checks

- Keep verified facts, evidence-backed inference, and unknowns visibly separate.
- Preserve regional differences instead of combining incompatible prices, claims, or product specifications.
- Check each selected keyword is recorded in current targets with a resolvable decision/research link and one intended page per primary intent, or an explicit unresolved assignment. Check removed targets retain their change history; do not fabricate research, pages or approvals.
- Save the context in the current project; preserve existing approved documents and their actual paths.
- Check the saved artifact against the requested scope, record unresolved facts and supporting evidence, and run `./seo --project <id> validate --json` when state or workflow contracts changed. No phase transition or next-step command is required.
