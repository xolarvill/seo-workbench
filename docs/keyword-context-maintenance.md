# Keyword context responsibilities and maintenance

This is the shared contract for agents creating, using or changing a project's keyword direction. The [project-context skill](../skills/project-context/SKILL.md) owns the method. Use it for the current decision; this document does not schedule research or require a project reset.

## File responsibilities

| Location | Responsibility | Maintenance boundary |
| --- | --- | --- |
| `context/target-keywords.md` | Concise search direction: audience, market, language, relevant intent groups, confirmed boundaries, hypotheses and pointers | Summarizes applicable decisions; not an exhaustive query list, metrics store, publication status or task allowlist |
| `strategy/keyword-pool.jsonl` | Keyword workspace decisions, priorities and query-to-page/content assignments | Use the existing CLI/UI operations and preserve concurrent decisions; the Markdown summary does not populate it |
| An explicitly declared manual strategy plan | Detailed ownership and priorities for projects not using the keyword workspace | Declare the actual path in context; do not require a pool merely to begin work or maintain two independently authoritative ownership tables |
| `strategy/keyword-dives/` and `strategy/briefs/` | Query-scoped research and writing decisions, including observation dates, market and evidence limits | Reuse applicable evidence; a brief or research file does not by itself approve a strategy change |
| `audits/` and existing content records | Observed search/site/business evidence and content production state | Keep original source windows and eligibility; do not copy metrics or production status into a parallel context ledger |
| Dated project reports | Decision rationale, proposals, release/campaign-specific query lists and plans, historical snapshots and supersession pointers | Preserve prior decisions; distinguish proposed, confirmed and superseded conclusions |

All paths above are project-relative. Repository policy and architecture belong under `docs/`; private store decisions remain in their project. No new task database, background synchronizer or Markdown parser is required by this contract.

## What a usable context file contains

Record the file's site-wide purpose and scope, last substantive review date, and what that review covered. Distinguish confirmed direction from site-wide working hypotheses. Keep release/campaign-specific query lists, article batches, launch priorities and publication order in dated reports; link to them as scoped plans rather than embedding them in context. Include the real maintained strategy path and relevant decision/research pointers. Link to detailed ownership instead of repeating the full table.

For example, adapt this small outline to the available evidence:

```markdown
# Search direction

- Scope: audience, market, language, business stage and topics covered
- Last substantive review: YYYY-MM-DD; decisions/evidence checked
- Detailed ownership and priorities: actual project-relative path

## Confirmed direction
Intent groups and supported exclusions, with decision references.

## Working hypotheses
Site-wide search assumptions and what remains to be decided or verified.

## Evidence and history
Relevant dated research, unresolved limits and historical plan pointers.
```

A new review date must describe an actual check, not silently renew old SERP, volume or ranking evidence. Review dates and research observation dates serve different purposes. Existing files need not be bulk-converted before unrelated work can continue.

## Resolve decisions and evidence

Use the current user goal and applicable repository/project instructions to establish scope and authorization. Read the relevant confirmed decisions and declared ownership record. Use sufficiently current, applicable evidence for claims about intent, demand, observed rankings or page conflicts. The context summary is a navigation aid to those materials.

Resolve conflicts by subject and scope, not by taking the newest timestamp everywhere:

- A later confirmed decision supersedes an earlier decision only for the affected scope. A newer proposal does not supersede a confirmed choice.
- Evidence can challenge an existing plan; it does not grant permission to publish, redirect or change an approved strategy. Record the finding and act within the user's task authorization.
- A selected target page is a planning decision; observed GSC query-page relationships are evidence. Neither should silently overwrite the other.
- Old launch priorities, missing keywords, pending legacy steps and absent data are not vetoes on a new user request. Missing observations remain unknown, not zero or proof of absence.
- Check actual paths. If a declared plan is missing or several plans conflict, use supported work that can proceed, record the gap and clarify only the choice that depends on it. Do not guess a replacement from filename similarity alone.

## Update triggers and responsibility

The agent performing an authorized change owns the related maintenance in that task; it is not deferred to an unspecified future agent.

| Event | Required maintenance |
| --- | --- |
| Audience, market, language, offer or confirmed search boundary changes | Update the scoped context and link the decision; reassess only affected plans |
| A topic/keyword is selected, reprioritized, dropped or assigned to a different page | Update the declared ownership/priority record and rationale; update context if its direction, hypotheses or pointers are affected |
| SERP intent, GSC conflicts or new site evidence challenges the plan | Record the observation, scope and uncertainty; distinguish a proposed change from an authorized decision |
| A candidate direction is discussed without a decision | Keep it in the existing research/decision artifact as a proposal; do not present it as confirmed context |
| A strategy file is moved or replaced | Update maintained incoming pointers in the same task; retain historical records and add a supersession pointer when needed |
| Existing evidence is reused | Check query/intent, market/language, observation window and relevant site changes; record why it fits in the task artifact |

Before writing, reread affected records and preserve concurrent edits. Use existing revision/locking mechanisms for structured workspace changes. If the task cannot finish a dependent synchronization, record the exact unresolved record in the task artifact; do not claim the strategy is fully synchronized.

There is no daily/weekly rewrite or fixed expiry threshold. Review relevant context at the start of a keyword, topic or page-ownership decision and when the events above occur. Refresh evidence only when its applicability or the decision requires it; file age alone neither proves validity nor invalidity.

## Handoff and verification

Both new-research and existing-research handoffs should point to this contract and the available project context. Before acting, inspect applicable decisions, evidence dates and the declared strategy location. If context is missing, continue from the current task and available evidence, recording essential unknowns. Do not create context just to satisfy a gate.

After changes, check affected pointers, preserve decision history and unconfirmed status, and ensure only one declared location owns detailed keyword assignments. Summaries may be projections of that record, not independent decisions. Follow repository validation requirements when workflow, state, CLI or skill contracts change.

`validate --json` checks structural contracts; it cannot certify that research is still applicable or that a strategy is approved. This policy and handoff guidance do not automatically assess semantic freshness, update plans or force every agent to comply.
