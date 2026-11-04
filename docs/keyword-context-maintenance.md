# Keyword context responsibilities and maintenance

This is the shared contract for agents maintaining a project's target keyword register. The [project-context skill](../skills/project-context/SKILL.md) owns the method. The register records actual selected keywords across tasks and releases, including subsequent removal; detailed rationale belongs in linked reports.

## File responsibilities

| Location | Responsibility | Maintenance boundary |
| --- | --- | --- |
| `context/target-keywords.md` | Maintained register of current target keywords, candidates if useful, and previously targeted keywords that were removed | Record each selected keyword here with a decision/research link; preserve its lifecycle instead of replacing the register with a navigation page |
| `strategy/keyword-pool.jsonl` | Broader discovery pool and structured keyword workspace data, including operational decisions and mappings | A collected query is not automatically an approved target. Use existing CLI/UI operations to reflect applicable register decisions; Markdown and JSONL are not synchronized automatically |
| Scoped strategy plans | Article batches, cluster structure and publication sequencing | Link to the register for current target selection; a historical plan is not a competing current target register |
| `strategy/keyword-dives/` and `strategy/briefs/` | Query-scoped research and writing decisions, including observation dates, market and evidence limits | Reuse applicable evidence; a brief or research file does not by itself approve a strategy change |
| `audits/` and existing content records | Observed search/site/business evidence and content production state | Keep original source windows and eligibility; do not copy metrics or production status into a parallel context ledger |
| Dated project reports | Detailed decisions, evidence, release/campaign plans, historical snapshots and removal rationale | Link from the keyword's register entry; keep historical snapshots dated rather than treating them as current target state |

All paths above are project-relative. Repository policy and architecture belong under `docs/`; private store decisions remain in their project. No new task database, background synchronizer or Markdown parser is required by this contract.

## What a usable context file contains

Keep a cumulative site-wide register, not just themes and document pointers. A keyword selected for today's task belongs in this file even when it originated in a single launch. Put a link immediately after the keyword, or link the keyword itself, to the actual decision/report or research. Add the selection/change date and intended page or content handle when known. Do not fabricate an owner or imply publication from a planning entry.

Use sections or an explicit status column for current targets, candidates and removed targets. Distinguish a candidate that was never selected from a target later removed. Keep detailed research, batch production plans and explanations in reports; the register contains the concise current decision and its entry point.

An explicit user choice to target a keyword can be registered immediately with its decision link. Missing research belongs in the linked record; it does not require reopening the selection before recording it.

For example, adapt this small outline to the available evidence:

```markdown
# Target keywords

- Scope: audience, market and language
- Last substantive update: YYYY-MM-DD; what changed

## Current targets

| Keyword and decision | Selected | Intended page | Note |
| --- | --- | --- | --- |
| AAA — [decision](../reports/YYYYMMDD_decision_topic.md) | YYYY-MM-DD | Known page or unassigned | Brief targeting scope |

## Candidates

Record proposed keywords here only when useful; keep them visibly unconfirmed.

## Targets but removed

| Keyword and decision | Removed | Reason / replacement |
| --- | --- | --- |
| BBB — [change decision](../reports/YYYYMMDD_decision_change.md) | YYYY-MM-DD | Changed strategy; replacement if applicable |
```

A new review date must describe an actual check, not silently renew old SERP, volume or ranking evidence. Review dates and research observation dates serve different purposes. Existing files need not be bulk-converted before unrelated work can continue.

## Resolve decisions and evidence

Use the current user goal and applicable repository/project instructions to establish scope and authorization. Read the register and its relevant linked decisions. The register is the maintained strategic target state, not merely a navigation aid. If a later confirmed decision has not been reflected there, reconcile the affected entry in this task instead of silently treating one copy as permanently authoritative. Use sufficiently current, applicable evidence for claims about intent, demand, observed rankings or page conflicts.

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
| A keyword is selected | Add or promote it to current targets in target-keywords.md in the same task, with date, intended page if known and a decision/research link; do not wait for a full strategy refresh |
| A target's scope, priority or intended page changes | Update that entry and link the applicable decision; reflect affected operational mappings through existing workspace operations when used |
| A previously selected target is dropped or replaced | Move it to Targets but removed with removal date, concise reason and decision link; retain its selection history or link and replacement if any. Restore it to current targets if later reselected, retaining the removal history in the linked record |
| SERP intent, GSC conflicts or new site evidence challenges the plan | Record the observation, scope and uncertainty; distinguish a proposed change from an authorized decision |
| A candidate keyword is discussed without a decision | Keep it in the linked research artifact and optionally the candidates section; do not promote it to a current target or mislabel it as previously removed |
| A strategy file is moved or replaced | Update maintained incoming pointers in the same task; retain historical records and add a supersession pointer when needed |
| Existing evidence is reused | Check query/intent, market/language, observation window and relevant site changes; record why it fits in the task artifact |

Before writing, reread affected records and preserve concurrent edits. Use existing revision/locking mechanisms for structured workspace changes. If the task cannot finish a dependent synchronization, record the exact unresolved record in the task artifact; do not claim the strategy is fully synchronized.

There is no daily/weekly rewrite or fixed expiry threshold. Review relevant context at the start of a keyword, topic or page-ownership decision and when the events above occur. Refresh evidence only when its applicability or the decision requires it; file age alone neither proves validity nor invalidity.

## Handoff and verification

Both new-research and existing-research handoffs should point to this contract and the available target register. Check whether the keyword is current, a candidate, removed or unrecorded, then read its linked decision. A removed keyword requires the relevant strategy decision to be revisited before reactivation; a new or unrecorded keyword can still be researched. When the task selects it, record it in current targets rather than leaving it only in a report. If context is missing, continue supported work and establish the register when making the first target decision.

After changes, check the keyword's status, decision link and affected page mapping. Preserve history and unconfirmed status, avoid duplicate conflicting rows, and check any workspace projection touched by the task. A completed article remains a target until an actual strategy decision removes it; do not confuse publication/production state with target status. Follow repository validation requirements when workflow, state, CLI or skill contracts change.

`validate --json` checks structural contracts; it cannot certify that research is still applicable or that a strategy is approved. This policy and handoff guidance do not automatically assess semantic freshness, update plans or force every agent to comply.
