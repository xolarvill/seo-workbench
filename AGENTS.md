# SEO Workbench

Agent-neutral SEO workflow repo. Use the local Python CLI and local `skills/` first.

## Start

- Work from the user's current goal, the project's `AGENTS.md`, decisions, artifacts, and evidence.
- State goal, scope, and acceptance criteria in a few lines before acting, and deliver the whole stated scope in one pass. If it clearly exceeds one session, give a phase plan and report one line per phase.
- For substantive SEO work, choose skills from [`skills/README.md`](skills/README.md) and read the useful bodies before doing the professional work; combine or shorten methods to fit the task. The catalog is a navigation aid, not an allowlist, so search local modules when the task falls outside the examples. Do not wait for the user to name skills; engineering-only changes need SEO skills only when they change SEO semantics.
- Keyword, page-ownership, and reader-facing writing tasks begin with the owner document named in [Task routing](#task-routing).
- Scale the method to the task and reuse applicable, sufficiently current research. State the chosen method and purpose briefly, and keep decisions, outputs, evidence pointers, and gaps in the task artifact so another session can resume from it.
- New invariants go to `docs/` first; promote one here only if it changes every action. On conflict: this file beats `docs/`, which beats examples inside `skills/`; the user's current instruction beats this file.

## Definition of done

Done means you re-ran the real path and can show the output. A clean diff, a passing read of the code, or "should work" is not done.

- Evidence and statistics: re-run the collector or artifact on a real project and show `collection_status`, gate results, the written file, and its timestamp. No absence claim may rest on data that was not collected.
- Contracts, CLI, state: execute the changed path end to end, paste the JSON, and show the affected test summary line.
- UI: open the changed surface and show a screenshot with a clean console.
- Docs and instructions: show the changed text and confirm every referenced path or link resolves.

## Task routing

| Task | Read first | Never |
|---|---|---|
| Keyword, topic, or page ownership | [`docs/reference/keyword-context-maintenance.md`](docs/reference/keyword-context-maintenance.md), `context/target-keywords.md` | Reduce the register to a portal, or silently drop a past target |
| Competitive landscape or competitor comparison | [`skills/competitive-landscape/SKILL.md`](skills/competitive-landscape/SKILL.md), `context/competitors.md` | Invent authority or traffic numbers, or reduce the comparison to a weighted score |
| Reader-facing prose | [`skills/reader-experience-review/SKILL.md`](skills/reader-experience-review/SKILL.md) | Add a second style policy or a competing mandatory prose pass |
| Technical audit and issue verification | [`docs/reference/technical-audit.md`](docs/reference/technical-audit.md) | Verify an issue from partial, incomparable, or stale evidence |
| Performance (Lighthouse, CrUX) | [`docs/reference/google-integrations.md`](docs/reference/google-integrations.md) | Treat lab or crawler metrics as field proof |
| GSC, GA4, statistics, Pages, outcomes | [`docs/reference/google-integrations.md`](docs/reference/google-integrations.md), [`docs/reference/统计学SEO操作手册.md`](docs/reference/统计学SEO操作手册.md), [`docs/reference/SEO迭代闭环.md`](docs/reference/SEO迭代闭环.md) | Smooth across a regime change, read absence as zero, or claim causality |
| Shopify orders | [`docs/reference/shopify-integrations.md`](docs/reference/shopify-integrations.md) | Turn product revenue into channel attribution |
| Clarity | [`docs/reference/clarity-integrations.md`](docs/reference/clarity-integrations.md) | Share authenticated processes across brands |
| Rendered and browser evidence | [`docs/reference/browser-runtime.md`](docs/reference/browser-runtime.md), [`docs/reference/chrome-extension.md`](docs/reference/chrome-extension.md) | Fill raw metadata from partial or challenge HTML |
| Audit diff | [`docs/reference/technical-audit.md`](docs/reference/technical-audit.md) | Call a regression when comparability failed |
| Weekly report and presentation | [`templates/weekly_work_done.md`](templates/weekly_work_done.md), [`docs/reference/统计学SEO操作手册.md`](docs/reference/统计学SEO操作手册.md) | Hand-build a deck or skip the readiness gate |
| UI surfaces | [`docs/reference/ui-local-surface.md`](docs/reference/ui-local-surface.md), [`docs/reference/UI状态Pill规范.md`](docs/reference/UI状态Pill规范.md), [`docs/reference/UI帮助气泡规范.md`](docs/reference/UI帮助气泡规范.md) | Add page-local tone maps or tooltips |
| Skill layout and provenance | [`docs/skill-sources.md`](docs/skill-sources.md), [`docs/history/20261029-skill-layout-migration.md`](docs/history/20261029-skill-layout-migration.md) | Create a second entrypoint or drop source IDs |
| CLI, state, or repository contract | [`docs/reference/independent-workbench.md`](docs/reference/independent-workbench.md), `README.md` → Common commands | Change a contract without `validate --json` |

## Guardrails

### Evidence and claims

- Response evidence eligibility is separate from SEO severity and priority. Unknown status, rate limits, challenges, parse failures, and unavailable target HTML cannot prove missing metadata or hreflang return links; incomplete link or sitemap coverage cannot prove absence. Preserve real observed HTTP errors, and never verify old issues from unavailable evidence or an older rule-evaluation fingerprint version.
- Absence vocabulary: `not_observed` is not zero, not unindexed, and not nonexistent. Missing observations stay absent instead of being synthesized as zero, and missing business evidence is `insufficient_data`, not zero.
- SEO change outcomes are descriptive pre/post evidence, never causal claims. Verdicts are per expected metric: one metric without sufficient evidence is `insufficient_data` on its own without vetoing the others, and a non-comparable window or a fully unobserved change stays `insufficient_data`. Matched controls require private history over both windows plus at least three unchanged same-type pages matching pre-change clicks and impressions.
- Technical-rule effects need at least six verified or provisional fixes with complete 14-day pre/post GSC history, exclude comparisons crossing a GSC measurement regime, and apply FDR across tested rules. Call them associations, never causal impact; each observation carries a `confidence` flag.
- Apply Benjamini-Hochberg false-discovery control before promoting simultaneous page-level CTR deviations into the action queue. Preserve unadjusted p-values and adjusted q-values; a point-estimate opportunity stays diagnostic when it does not survive FDR.
- Stable pointers: `projects/<id>/audits/{raw,browser,performance,crux,gsc,diffs}/latest.json` are the current evidence pointers, and timestamped files are immutable records. `audits/gsc/search-analytics/latest.json` is the canonical page/query source for technical priority, Pages, and outcome evaluation; the composite GSC pointer is for combined status and audit diff.
- Audit diff compares the newest immutable raw, technology, performance, CrUX, and GSC snapshot with its newest matching identity. Never classify a regression when Lighthouse runtime, CrUX effective scope or form factor, or GSC property/window/data-state comparability fails.

### Collection

- The Chrome extension is optional: missing browser evidence is `not_collected` and must never block the core CLI or workflow.
- Project-level `evidence` defaults to at most five representative same-host routes discovered from raw and rendered internal links. Keep discovery bounded, exclude static resources and sensitive query parameters, and use `--crawl-limit 0` for a strict single-URL run.
- Project raw, robots/sitemap, resource-header, rendered, and technical crawls share the injected crawl session: attach signing headers only to the exact HTTPS host on each hop, preserve the mobile UA, respect persistent host cooldown, and never forward signature headers across redirects. Keep unavailable-page retries separate from discovery and retain both through Continue; a recovered request must not remain failed because of earlier transport attempts. Keep Lighthouse and CrUX traffic separate from crawl pacing.
- Prefer `./seo evidence --rendered --json` when Playwright is available so `headless_audit` carries raw and rendered diffs. Collectors return structured JSON with `collection_status`, `errors`, and `warnings` even when some fetches fail.
- Technology detection uses the pinned Go helper under `seo_workbench_tools/technology_detector/`; keep its JSON contract stable and update fixtures before changing the fingerprint provider version. Detection defaults to balanced Wappalyzer data (page, scripts, robots, DNS) with asset-name fallback plus existing rendered runtime evidence; `--scan-mode fast` is the reproducible Go headers/cookies/raw-HTML path. Never turn a zero detection into a positive absence claim; record runtime-only gaps in `architecture_analysis.evidence_quality`.
- Rendered mobile evidence needs a mobile user agent and a mobile viewport. Preserve per-profile final URLs and report profile-specific navigation instead of merging desktop and mobile routes. Rendered comparisons require eligible desktop evidence at the same final route; partial or challenge HTML must not fill raw metadata.
- Browser jobs prefer the matching installed Playwright runtime, use a shared workload lease, close contexts and browsers on every exit path, and save redacted per-run diagnostics. Crashes or missing profiles propagate partial or failed status; never infer OOM from a generic disconnect or silently fall back to the user's daily Chrome.
- Lighthouse performance evidence uses the pinned Node runner and the Playwright-matched browser; keep runs sequential, default to five runs, and preserve every complete LHR before changing aggregation behavior. Keep it behind `network_boundary.guarded_proxy` unless the user explicitly selects `--allow-private`, and redact URL credentials and query values before persisting LHR or HTML artifacts.
- Performance summaries preserve `requested_url`, `final_url`, `main_document_url`, per-run final URL consistency, and redirect status; never compare snapshots that ended on different final URLs. CrUX is the field source of truth for verdicts, Lighthouse and crawler/bot measurements such as `SLOW_RESPONSE` are diagnostics only, and CrUX keeps its URL-to-origin fallback and `no_data` status. CrUX defaults to aggregate, mobile, and desktop current data plus 40 history periods.

### Data, secrets, and surfaces

- GSC and GA4 are read-only and explicit. Keep OAuth clients, tokens, service accounts, property bindings, and project bindings under ignored `.runtime/` paths (`GA4` tokens under `.runtime/google/`, binding under the project's ignored `.runtime/`), and never persist authorization headers or credentials in artifacts. GSC artifacts are private local data with mode `0600`.
- GA4 keeps exact query windows in every artifact and defaults to two complete processing days before today. Its commerce funnel is event-count based and landing-page associated: `view_item`, `add_to_cart`, `begin_checkout`, and `purchase` may be filtered to Organic Search, but standard-event coverage must be checked across all channels, and zero organic purchases alone never prove broken tracking.
- `statistics collect` is the production entry point for statistical SEO evidence: use finalized GSC as the common end date, align GA4 and Shopify to it, refuse truncated or incomparable evidence, append only aggregate date-by-page history, and refresh Portfolio only after every gate passes. `audits/statistics/history/` is private aggregate evidence with a rolling 120-day default; daily rows are idempotent by date and URL.
- Record GSC, GA4, Shopify, consent, or cross-source measurement-definition changes in `context/measurement-regimes.jsonl`. A breaking regime inside a comparison range makes the affected source incomparable; never smooth across it or treat the series as continuous.
- `gsc collect` combines a finalized 28-day Search Analytics comparison, Sitemap status, and a bounded URL Inspection sample. URL Inspection is indexed-version evidence, not a live test, and `needs_auth` is a user handoff, not a site failure.
- Shopify order evidence is product-level net revenue, not channel attribution: use exact windows matching GA4, aggregate line-item amounts instead of repeating order totals, exclude test and unpaid orders, and never persist customer or order identifiers. Shopify Admin credentials stay project-scoped at `projects/<id>/.runtime/integrations/shopify.json` with mode `0600`; accept only canonical `*.myshopify.com` targets, use the pinned Admin GraphQL version and fixed read-only verification query, expose granted scopes but never the token, and warn when a token carries write scopes.
- Clarity MCP uses the pinned local Node runner and project-scoped credentials at `.runtime/integrations/clarity.json`; never share authenticated processes across brands or expose tokens in argv, status, evidence, or logs, and let queries and credential verification share the per-brand operation lease and cooldown. Unconfirmed scope is exploratory partial evidence, not production statistics: keep per-kind immutable records and current pointers under `audits/clarity/`, keep private recording links only in the local viewer's transient memory, and never treat Clarity as CrUX or as part of the production statistics chain.
- Change-scoped GSC collection for outcome reviews excludes the change day from both windows, an unobserved changed URL is `insufficient_data` rather than zero traffic, and refreshes stay at most 25 URLs with an explicit full-property artifact for larger change sets. Pages evaluates one-URL changes through the existing background job runner and multi-URL reviews through the CLI with an explicit GSC artifact.
- `content-portfolio-v4` is the same-site union of current and previous GSC pages, the latest technical inventory, live content URLs, comparable business-only URLs, transparent query projections, and private daily-history diagnostics, with `audits/content-portfolio/latest.json` as its pointer. Query statistics cover observed GSC query-page rows only, longitudinal intervals require explicit daily coverage, and Shopify product value is all-channel context rather than SEO revenue attribution.
- Technical issues persist one per fingerprint, and operator queues group by rule and page template while fingerprint-level evidence and verification history stay authoritative. Verification requires a complete later audit with the same semantic config fingerprint (collection parameters such as crawl limits, concurrency, timeouts, and private-network access are excluded); partial same-fingerprint runs record lower-confidence provisional evidence only, and incomparable runs cannot prove absence. Identity uses explicit per-rule source and target fields, while timings, sizes, group members, and content hashes remain observations; new findings are candidates until fresh comparable evidence confirms them, targeted rechecks never verify absence and must preserve concurrent operator decisions, and legacy identity migration stays preview-only until an explicit apply workflow is reviewed.
- Effective internal inlinks require an observed eligible HTML source distinct from the target, including final-URL aliases. Error-template outlinks stay observations and must not expand discovery or prove live incoming broken links; the same rule applies to continuation graph rebuilds, and a policy change invalidates cross-version absence verification.
- Backlink snapshots are provider-scoped: only two complete same-source snapshots can confirm absence as lost; never invent authority or toxicity scores and never auto-generate disavow actions.
- Pages actions are read-time projections of portfolio, content operations, technical issues, and SEO changes, so do not add a generic task database or duplicate domain status. Grouped technical actions are read-only and drill down by rule and template, with status, owner, and notes updated on individual issue fingerprints. Pages may update existing local ledgers only: never publish, redirect, recrawl, push notifications, or mutate the site from Pages.
- The local UI is optional and local-only; see [`docs/reference/ui-local-surface.md`](docs/reference/ui-local-surface.md) for detection, audit whitelisting, credential APIs, Markdown write scope, and the read-only Pages boundary.
- Shared UI status pills are mandatory through [`ui/src/components/StatusPill.tsx`](ui/src/components/StatusPill.tsx) and [`docs/reference/UI状态Pill规范.md`](docs/reference/UI状态Pill规范.md); shared help tooltips are mandatory through [`ui/src/components/HelpTooltip.tsx`](ui/src/components/HelpTooltip.tsx) and [`docs/reference/UI帮助气泡规范.md`](docs/reference/UI帮助气泡规范.md), never page-local implementations.
- Keep stores isolated under `projects/<id>/`, prefer `--project <id>` for daily use, and retain `--project-dir` for explicit external or test directories. Repository-wide diagnostics, architecture decisions, and agent or workflow design belong under `docs/`, not in a store's reports or weekly archive, and public repository documents stay free of private store evidence and local session identifiers.
- Store project reports and decision records under `projects/<id>/reports/` as `YYYYMMDD_<category>_<topic>.md` (categories `tech`, `content`, `ops`, `decision`, `outcome`) with decision rationale, evidence pointers, and follow-up dates in the body. Keep the current week's archive there as `YYYY_week_WW_work_done.md`, following [`templates/weekly_work_done.md`](templates/weekly_work_done.md), carrying unfinished work into the next week, and never duplicating weekly files. Team-facing decks live under `projects/<id>/reports/presentations/` as one stable `YYYY_week_WW.pdf` plus a private aggregate manifest, generated only through `reports presentation generate`; the readiness gate needs fresh `statistics`, a recent finalized GSC end date, 28 days of GSC and business history, and a portfolio snapshot. Partial or incomparable evidence may render with explicit caveats, while missing or stale required evidence blocks generation. The local UI scheduler attempts the current week's deck after Friday 16:00 local time; it is not a hosted scheduler.

### Engineering

- Prefer `skills/` over third-party skill packs and `seo_workbench_tools/` for machine evidence; do not rewrite probes unless the existing collector cannot supply the field. Callable methods share `skills/<capability>/SKILL.md`: keep one canonical entrypoint per capability, put complementary methods in its references, preserve source IDs and old paths in `docs/skill-sources.json` when moving material, and keep historical specialist documents under `third_party/skill-history/`.
- CLI commands execute explicit operations and return evidence; choose them through `./seo --help` or command-specific help. There is no stored phase, step, or `next` scheduler.
- Skill selection never expands the user's authorized scope. Project facts and current Workbench evidence or collection rules override conflicting source-material recipes; do not execute archived slash commands or old scripts blindly.
- Run `validate --json` after changing workflow, state, CLI contracts, or skill mappings, and `doctor --json` when debugging local setup, missing evidence, or optional rendered support. Do not restore Claude slash commands or external repo dependencies unless the user explicitly asks.
- Each reform layer is committed separately.

## Reporting

- A project record under `projects/<id>/reports/` is five sections in this order: `结论` → `方法与覆盖` → `证据` → `边界` → `后续`. Lead with the answer in a few sentences, then the scope and method actually used, then evidence pointers that keep URL, window, device or form factor, and confidence attached, then what the evidence cannot support, then follow-ups with dates and owner. Record the data time zone, and use `###` subheadings and tables only where they help.
- Weekly archives follow [`templates/weekly_work_done.md`](templates/weekly_work_done.md) exactly: `速览` → `实质工作` → `遗留工作` → `其他`, with `###` only inside `实质工作`. Each substantive item opens its own `### N. 标题（MM-DD）` block and links its sub-report and evidence pointer; unfinished work from last week is carried forward in both `速览` and `遗留工作`.
- The chat reply answers first, then groups by theme: decisions, artifact links, verification results, remaining gaps. No section template and no restating internal collection logs.
- Close every task with a `技能使用` line naming the local skills actually read or consulted this round, one clause each on what they supplied; write `未使用本地技能` when none applied, with a short reason. Count only a skill whose body was opened or whose method was used — a catalog listing or a skill you skipped does not count, and never fill the line with invented usage.
- Presentations are generated only through `reports presentation generate`; never hand-author or re-render the PDF.

## Repository shape and commands

```text
seo_workbench/          Python execution layer: project manifests, CLI, evidence wrappers
seo_workbench_tools/    Raw and rendered SEO evidence collectors
skills/                 First-party SEO playbooks
templates/              Reusable project and report templates
projects/<id>/          One isolated runtime directory per store
```

Project records live under `projects/<id>/`: reports in `reports/YYYYMMDD_<category>_<topic>.md`, plus `context/`, `strategy/`, `content/`, and `audits/`. Root `docs/` holds repository-wide and cross-project documentation only.

`./seo` is the repository-local launcher for the installed `seo-workbench` console script; keep `python -m seo_workbench` only as a compatibility and diagnosis fallback. For the full command catalog, see `README.md` → Common commands, or run `./seo --help` and `./seo <command> --help`.
