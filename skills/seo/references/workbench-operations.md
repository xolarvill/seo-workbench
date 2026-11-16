# Workbench execution and evidence

Use this reference when a skill needs collection, state, credentials or delivery. Select the project explicitly and check the operation's current `--help` before building arguments. The repository launcher uses the project environment. Adapted methods describe professional work; available CLI operations and connected tools determine execution.

## Evidence and analysis

| Need | Current local operation / evidence |
|---|---|
| Project manifest and setup | `./seo projects --json`; `./seo --project example-store validate --json`; `./seo --project example-store doctor --json` |
| Raw/rendered page evidence | `./seo --project example-store evidence --rendered --crawl-limit 5 --json` when collection is needed; use `--crawl-limit 0` for the project URL alone |
| Technical rules | `./seo --project example-store tech-audit --help`; reuse eligible current evidence and record coverage |
| Search Console / GA4 / CrUX | See [Google integration setup and commands](../../../docs/reference/google-integrations.md); use the bound property and exact window |
| Comparable production statistics | `./seo --project example-store statistics collect --json` aligns finalized GSC and business windows through its readiness gates |
| Backlink provider exports | `./seo --project example-store backlinks import --help`; preserve provider identity, capture date and completeness |
| Backlink paid collection | `./seo --project example-store backlinks collect --help`; the explicit `--confirm-paid` operation spends provider credits |
| Portfolio and content queue | `./seo --project example-store content portfolio --help`; `./seo --project example-store content queue --help` |

Run only the collection needed by the task. A wording review can reuse adequate evidence. Raw/rendered observations, lab measurements, field performance and business statistics have different scopes; keep the collector's status, source identity, timestamp and gaps with the finding. Existing project evidence and collection rules govern which observations support a conclusion.

## Project artifacts and credentials

Resolve `context/`, `strategy/`, `content/`, `audits/` and `reports/` under the selected project directory, normally `projects/<id>/`. Reuse existing brand and product context before creating another document. Keep repository architecture and maintenance records in `docs/`.

Use the configured Workbench connection for the selected project. [Google integrations](../../../docs/reference/google-integrations.md) documents shared auth profiles and project bindings. Shopify and Clarity credentials are project scoped under the project's ignored runtime directory. Keep secrets out of prompts, commands, reports and source control; the connection interfaces expose status without returning secret values.

## Draft and publication handoff

For article imports, first inspect `./seo content import-draft --help` and the existing draft format. `./seo --project example-store content publish-dry-run ITEM_ID --blog-id BLOG_ID --json` checks the existing item's planned handoff. Use `./seo content publish --help` only when the requested delivery includes that operation. Metadata changes have a separate `./seo metadata update --help` interface with `--dry-run`.

Keep the proposed content and target reviewable before a write. After an authorized operation, read back its actual state; draft creation, publication and public URL verification are distinct results. Preserve existing project ledgers and content state rather than creating a parallel workflow database.

## Optional capabilities

Discover available session tools for advertising, email, image generation, maps, marketplace research or other providers. Verify the tool's supported operation and account/project scope before relying on it. If it is unavailable, work from an appropriate supplied export or record the specific missing input. An upstream tool catalog describes possible data; it does not establish an installed executor or grant paid collection, messaging or publication authority.

Weekly presentations use the gated `reports presentation` operations. For another report format, use an actually available renderer or deliver the requested source document. Historical PDF scripts, slash commands and automatic source sync are preserved as provenance rather than installed interfaces.

## Report and check-in delivery

Reuse the same subject/period artifact when correcting that report; a materially new period or question can have its own report. Give a short conclusion, leading action and evidence links so later work can resume without rereading the full material. Continue to use the existing report format and [reader-led expression](../../reader-experience-review/SKILL.md); no separate HTML writer or mandatory prose pass is installed. Saving locally does not authorize public sharing.

Before enabling a user-requested recurring check-in, run its read-only reporting path once to expose missing, stale or incomparable sources. Keep actual collection windows, denominators and gates; failed reads do not become zero. Only an actually available authorized scheduler can run future checks. The local Friday presentation attempt is not a hosted always-on agent. Do not create a second task database or treat document instructions as installed automation.
