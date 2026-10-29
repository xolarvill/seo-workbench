---
name: seo-flow
description: >
  FLOW framework integration — evidence-led SEO using the Find → Leverage →
  Optimize → Win loop. Surfaces stage-specific AI prompts from the FLOW
  knowledge base (41 prompts, CC BY 4.0). Use when user says "FLOW", "FLOW
  framework", "seo flow", "evidence-led SEO", "find leverage optimize win",
  or wants stage-specific SEO prompts.
user-invokable: true
argument-hint: "[stage] [url|topic]"
license: MIT
metadata:
  author: AgriciDaniel
  version: "1.9.6"
  category: seo
---

# FLOW Framework — Find · Leverage · Optimize · Win

Framework and prompts © Daniel Agrici, CC BY 4.0 — github.com/AgriciDaniel/flow.

Use FLOW to locate the current research or conversion question within the Find → Leverage → Optimize → Win loop. Read [the framework](references/flow-framework.md), then select only prompts that serve the user's current goal from [the prompt index](references/prompts/README.md). Keep attribution with reused framework or prompt material.

| Question | Prompt family | Current local method |
|---|---|---|
| Demand, intent and gaps | Find | [keyword-deep-dive](../keyword-deep-dive/SKILL.md) |
| Off-site corroboration and links | Leverage | [backlinks](../backlinks/SKILL.md) |
| Content, technical or citation gaps | Optimize | [page-audit](../page-audit/SKILL.md), [seo-geo](../seo-geo/SKILL.md) |
| Buying decisions and conversion | Win | [page-cro](../page-cro/SKILL.md) |
| Business profile and local visibility | Local | [seo-local](../seo-local/SKILL.md), [seo-maps](../seo-maps/SKILL.md) |

Prompts live in the corresponding subdirectories of `references/prompts/`. Use the bibliography when checking a cited study; a preserved prompt's dated assertion needs verification when it supports current advice. Choose the number of prompts to fit the task rather than applying a whole stage by default.

Use [Workbench operations](../seo/references/workbench-operations.md) for collection and artifact locations. The source pack's slash-command and automatic sync interfaces are not installed here. If material is missing, report the missing reference and use the available canonical method. Source revisions are compared through [the provenance manifest](../../docs/skill-sources.md); do not overwrite the local adaptations by fetching an unreviewed upstream HEAD.
