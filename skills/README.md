# Local SEO skills

Choose methods from the user's goal and the project's current artifacts and evidence. Read the relevant `SKILL.md` before applying it; use the CLI for explicit operations. No phase, next-step command, or user reminder is needed to discover a skill.

This index offers starting points, not a required sequence or an allowlist. Combine useful methods, search other local modules, and omit work already supported by applicable evidence. For small reviews, use the review method instead of starting a research/rewrite pipeline. Record material omissions and evidence gaps in the existing deliverable; do not call a partial method complete.

## Workbench entrypoints

For prose, [reader-experience-review](reader-experience-review/SKILL.md) is the single expression method for drafting and revision. Domain skills supply research, offer facts, structure and delivery. Voice samples are inputs; editing references are diagnostics. They do not establish separate style authorities or require another prose pass. Follow the user's requested output, and use [evidence to prose](reader-experience-review/references/evidence-to-prose.md) to keep internal verification notes out of an article unless readers need the condition.

| Task or question | Start here | Useful combinations |
|---|---|---|
| Site-wide or multi-template diagnosis | [site-audit](site-audit/SKILL.md) | Select specialist checks from current scope and evidence |
| Audience, positioning, brand voice, evidence boundaries | [project-context](project-context/SKILL.md) | Existing project context and approved facts |
| Query opportunity, intent, SERP, existing page owner | [keyword-deep-dive](keyword-deep-dive/SKILL.md) | [semantic-gap-analysis](semantic-gap-analysis/SKILL.md) for coverage gaps |
| Hubs, spokes, overlapping articles and internal links | [topic-cluster-planning](topic-cluster-planning/SKILL.md) | Query research and current content inventory |
| Writer-ready scope and evidence requirements | [content-brief](content-brief/SKILL.md) | [expert-interview](expert-interview/SKILL.md) if first-party knowledge is missing |
| A new article from an approved brief | [write-content](write-content/SKILL.md) | [reader-experience-review](reader-experience-review/SKILL.md) before delivery |
| Substantial refresh of an existing page | [improve-content](improve-content/SKILL.md) | [page-audit](page-audit/SKILL.md) if diagnosis is still needed |
| Prose review, confusing passages, local edits | [reader-experience-review](reader-experience-review/SKILL.md) | Preserve correct cautions and useful technical language |
| Page-level SEO, credibility, missing topics | [page-audit](page-audit/SKILL.md), [eeat-audit](eeat-audit/SKILL.md), or [semantic-gap-analysis](semantic-gap-analysis/SKILL.md) | Choose by the actual question; do not run all by default |
| Eligible concise answers and result formats | [featured-snippet-optimizer](featured-snippet-optimizer/SKILL.md) | Observed SERP features, not an assumed snippet |
| Technical diagnosis or bounded audit | [technical-audit](technical-audit/SKILL.md) | [headless-precheck](headless-precheck/SKILL.md) when raw/rendered parity matters |
| Structured data, sitemap coverage or image SEO | [schema](schema/SKILL.md), [sitemap](sitemap/SKILL.md), or [images](images/SKILL.md) | Existing eligible collection evidence |
| Comparable changes and monitoring | [drift](drift/SKILL.md) | Existing audit diff, measurement windows and change ledger |
| Backlink evidence or link acquisition | [backlinks](backlinks/SKILL.md) or [linkbuilding](linkbuilding/SKILL.md) | Same-source snapshots; acquisition plans do not authorize outreach |

Project-specific skills add store facts, assets and delivery formats. They complement these professional methods rather than replace them. Follow the project's own `AGENTS.md` when present.

## Unified skill namespace

Every callable method lives at `skills/<capability>/SKILL.md`. The 60 entrypoints share one namespace; source repositories are recorded in [the provenance reference](../docs/skill-sources.md) and [attribution](../third_party/NOTICE.md). [The migration map](../docs/20261029-skill-layout-migration.md) connects old paths to current owners.

Additional entrypoints are listed below. These are capability groupings for navigation, not source-specific directories.

| Capability | Methods |
|---|---|
| Scope, strategy and query grouping | [seo](seo/SKILL.md), [seo-plan](seo-plan/SKILL.md), [seo-flow](seo-flow/SKILL.md), [seo-cluster](seo-cluster/SKILL.md) |
| Content and search experience | [seo-content](seo-content/SKILL.md), [seo-sxo](seo-sxo/SKILL.md), [seo-competitor-pages](seo-competitor-pages/SKILL.md), [seo-geo](seo-geo/SKILL.md) |
| Ecommerce, international and local | [seo-ecommerce](seo-ecommerce/SKILL.md), [seo-hreflang](seo-hreflang/SKILL.md), [seo-local](seo-local/SKILL.md), [seo-maps](seo-maps/SKILL.md) |
| Data services and generated images | [seo-google](seo-google/SKILL.md), [seo-dataforseo](seo-dataforseo/SKILL.md), [seo-image-gen](seo-image-gen/SKILL.md) |
| Dataset-driven pages | [programmatic-seo](programmatic-seo/SKILL.md) |
| Marketing context and copy | [product-marketing-context](product-marketing-context/SKILL.md), [content-strategy](content-strategy/SKILL.md), [copywriting](copywriting/SKILL.md), [copy-editing](copy-editing/SKILL.md), [competitor-alternatives](competitor-alternatives/SKILL.md) |
| Conversion and experiments | [page-cro](page-cro/SKILL.md), [form-cro](form-cro/SKILL.md), [popup-cro](popup-cro/SKILL.md), [signup-flow-cro](signup-flow-cro/SKILL.md), [onboarding-cro](onboarding-cro/SKILL.md), [paywall-upgrade-cro](paywall-upgrade-cro/SKILL.md), [ab-test-setup](ab-test-setup/SKILL.md) |
| Measurement and distribution | [analytics-tracking](analytics-tracking/SKILL.md), [email-sequence](email-sequence/SKILL.md), [social-content](social-content/SKILL.md), [paid-ads](paid-ads/SKILL.md) |
| Growth and offers | [growth-lead](growth-lead/SKILL.md), [launch-strategy](launch-strategy/SKILL.md), [pricing-strategy](pricing-strategy/SKILL.md), [referral-program](referral-program/SKILL.md), [free-tool-strategy](free-tool-strategy/SKILL.md), [marketing-ideas](marketing-ideas/SKILL.md), [marketing-psychology](marketing-psychology/SKILL.md) |

Current specialist methods are attached to their canonical owners: [article editing](copy-editing/references/article-editing.md), [internal links](topic-cluster-planning/references/internal-link-review.md), [metadata options](page-audit/references/metadata-writing.md), [SEO editing](improve-content/references/seo-editing.md) and [conversion reasoning](page-cro/references/conversion-analysis.md). Read the matching reference for a task. The [adaptation map](../docs/skill-method-adaptations.json) covers all 11 specialists and 24 workflows; [historical originals](../third_party/skill-history/seomachine/README.md) remain available for source comparison.

Source material is available for judgment and adaptation, not automatic execution. Check its assumptions against the current task and Workbench contracts. Current evidence eligibility, bounded collectors, project isolation, and user authorization take precedence. Do not restore old scripts, crawl sizes, publishing behavior or external dependencies just because a preserved recipe names them.

Some recipes still impose fixed article lengths, keyword density, invented authority estimates or generic scoring. These are not Workbench acceptance gates: use reader-task coverage, verified facts, observed intent and evidence quality. [reader-experience-review](reader-experience-review/SKILL.md) alone governs expression; [write-content](write-content/SKILL.md) organizes article work; attribution preserves the source, not the authority of every old rule.

## Resuming work

When a selected method needs collection, credentials or delivery, read [Workbench operations](seo/references/workbench-operations.md) for the current local interfaces and project artifact locations. Discover optional provider operations from the session's available tools.

Read the relevant decision or brief, latest artifact, evidence pointers and remaining gaps. Reuse research only when its target, market, observation date and scope still apply. A stored stage or checked step cannot establish that the research is complete. Keep the method and its boundaries with the deliverable; do not create a second task database or a global skill-call counter.
