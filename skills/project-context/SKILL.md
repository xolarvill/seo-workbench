---
name: project-context
description: Create or update the brand voice and target keyword context files that initialize an SEO Workbench project. Use for INIT/config-brand-voice and INIT/config-target-keywords, or whenever project positioning, evidence boundaries, audience, editorial guardrails, or keyword ownership must be made explicit before strategy work.
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

If no approved brand guide is available, infer a working draft from the project state and public site evidence. Label it as inferred and list what the owner must confirm. Do not present inferred tone or audience as approved fact.

## Target keywords

Write `context/target-keywords.md` with:

- commercial, comparison, and informational keyword groups;
- one preferred page type or existing URL for each primary intent;
- explicit first-priority hypothesis and rationale;
- known cannibalization risks;
- missing data and validation requirements.

Use live SERP research for keyword selection. If Search Console, paid keyword volume, conversion, or margin data is unavailable, say so and avoid traffic or revenue forecasts.

## Completion checks

- Keep verified facts, evidence-backed inference, and unknowns visibly separate.
- Preserve regional differences instead of combining incompatible prices, claims, or product specifications.
- Map every primary keyword to one intended owner page.
- Ensure the file path matches the workflow contract.
- Run `./seo --project <id> next --json` and mark the step done only after the declared output exists.
