# SEO Workbench

A local-first all-in-one SEO workspace. Use it from an AI coding agent and manage the visual browser interface. Progress your work in weekly paces.

1. Overview 
![SEO Workbench overview](docs/assets/overview.png)

2. Keywords
![SEO Workbench keywords](docs/assets/keywords.png)

3. Technical audit
![SEO Workbench detail](docs/assets/details_in_audit.png)

4. Book SEO changes
![SEO changes](docs/assets/seo_changes.png)

## What it does

| Area | Included capabilities |
| --- | --- |
| Site evidence | Raw HTML, redirects, metadata, robots.txt, Sitemaps, representative routes, and rendered browser checks |
| Technology stack | Wappalyzer-style detection with architecture and SEO impact analysis |
| Performance | Repeatable multi-run Lighthouse audits plus CrUX field data and 40-week history |
| Google Search integration | Read-only Search Analytics by query, page, query-page, device, and country; URL Inspection; and Sitemap status |
| Shopify integration | Read-only product net revenue/orders plus a GA4 Organic Search commerce funnel with separate all-channel tracking coverage |
| Technical crawl | URL inventory, deterministic rules, GSC page metrics, priority queue, issue ownership/status/reverification, scheduled CLI runs, and Feishu notification adapter |
| Change tracking | Comparable evidence diffs plus a URL-level SEO change ledger and non-causal outcome review |
| Page operations | A same-site page inventory, transparent opportunities, query ownership conflicts, and projected Now/Review/Watch actions |
| Keyword Planning | Discover to map, map to research, research to produce |
| Content operations | Content production state plus optional page-level aggregate sessions, conversions, and revenue evidence |
| Off-page evidence | Provider-neutral backlink imports plus optional paid DataForSEO snapshots/gap evidence, conservative new/lost comparison, anchor counts, and 404 target reclaim candidates |
| Project management | One local folder per site, with private runtime data excluded from Git |
| Weekly-based Workflow Orchestration | Advancing SEO work by a week as a unit |

SEO Workbench is agent-neutral. Codex, Claude Code, or another coding agent can use the same `./seo` commands, project files, and local skills. The CLI remains the source of truth when the UI is closed.

The Hexcal content workflow remains available as an optional adapter. Workbench project files stay authoritative; Feishu imports never overwrite existing local decisions, and remote Base, table, field, recipient, and chat IDs stay in ignored `.runtime/profiles.json` configuration.

## Quick start

```bash
git clone https://github.com/xolarvill/seo-workbench.git
cd seo-workbench
./setup.sh
```

### Working with an agent

Run your coding agent from the repository root and give it the project ID. A useful first request is:

> Audit the `my-site` project, explain the technical and performance findings, then prepare a content SEO strategy using the local workbench. Give me a report of what should be done in this week.

Agents can discover the current workflow step with:

```bash
./seo --project my-site status --json
./seo --project my-site next --json
```

When the UI is open, new audit files and Markdown documents appear there automatically.

### Working manually

Manual operation is supported, create a project and collect its first evidence:

```bash
./seo --project my-site init general \
  --name "My Site" --url "https://example.com"

./seo --project my-site evidence --rendered --technology --json
./seo --project my-site performance --json
```

Open the workbench:

```bash
./seo --project my-site ui
```

The interface only listens on `127.0.0.1`. It is optional and uses the same local project files as the CLI.

WebView/cookieless previews (for example the Codex built-in browser) can use `./seo ui --allow-cookieless`; the one-time bootstrap token is then also accepted via `Authorization: Bearer` on every local request. The default stays cookie-based.


## Reporting

Each project stores decision records under `projects/<id>/reports/` with the name `YYYYMMDD_<category>_<topic>.md`. Weekly work uses one `YYYY_week_WW_work_done.md` file and the four-section template in `templates/weekly_work_done.md`; update the same weekly file instead of creating duplicates.

`./seo reports list` indexes the archive (weekly checkbox/carry-over/follow-up projections plus category-grouped sub-reports; `--q`, `--category`, and `--year` narrow the sub-report index) and `./seo reports new` scaffolds the next ISO week from the template, carrying unfinished work over into the new `速览` by default. The **Reports** tab in the browser workbench surfaces the same archive: **Weekly** leads with a progress view (follow-up due dates grouped into overdue/this-week/later, plus tasks carried across two or more weeks) and a searchable, filterable sub-report index, while **Notify** covers content reports, index inspection, and Feishu notifications.

## Workbench interface

The browser interface includes project switching, evidence status, audit actions, workflow progress, local Shopify and Google credential management, file browsing, and a Markdown editor with source, split, and preview modes. Opening a report or document from any workbench surface raises it as a floating overlay — click the backdrop or press Escape to close it and keep working in the list behind it. The overlay starts in a compact preview size tuned for quick scanning; use the `A−` / `A+` controls in its toolbar to adjust the preview and editor font size (12–20px, remembered across sessions).

**Keywords** joins `strategy/keyword-pool.jsonl`, the latest GSC queries, keyword deep dives, the Content queue, and the Pages portfolio into one operating view. Query is read-only observed search language; Keyword holds the durable strategy decision; Cluster groups related keywords and observed queries; Target URL assigns page ownership. GSC-only queries remain candidates until an operator first records a decision or ownership field. Opportunity Pool keeps exact-query metrics separate from cluster aggregates; Topic Map rolls member queries up by cluster and flags planned target, Content, and exact-query ownership conflicts; Research opens an existing deep dive or copies a request based on `skills/keyword-deep-dive/SKILL.md` without creating an empty document. Batch edits are limited to 1,000 filtered keywords and use the keyword-pool file revision: validation is all-or-nothing, and concurrent changes return a conflict instead of being overwritten.

**Pages** opens on the current `Now` actions, with separate views for all observed pages and query ownership conflicts. It projects existing portfolio, content, technical issue, and change state instead of creating another task store. Query links return to Keywords; keyword target URLs and Content items link forward to their owning workspaces, completing the discovery → mapping → research → production → live → measured loop.

Keywords and Pages can record local decisions and update existing ledgers. Publishing, redirects, recrawls, indexing submissions, and site changes remain in their domain workspaces with their existing confirmation steps. Keyword performance is read from Statistics/Portfolio rather than copied into a second store. Missing evidence is shown as not observed, never as a zero metric.

Open **Connections** to configure Shopify Admin API, CrUX, and GSC without exposing secret values to project files or audit output. The **Optional providers** tab stores project-scoped DataForSEO credentials and verifies them with the free `appendix/user_data` endpoint. Credential changes are local-only and persist below ignored `.runtime/` paths with private permissions.

DataForSEO integration uses its REST API v3 directly, with no SDK dependency. Opportunity Pool shows provider Volume, CPC, paid-search Competition, Intent and 12-month trend separately from GSC query performance; Score remains the Workbench strategic priority score. A confirmed single-keyword action calls Keyword Overview plus a depth-10 Live SERP, records the returned cost and sanitized evidence under `audits/keywords/dataforseo/`, and never copies provider metrics into `keyword-pool.jsonl`. Every paid refresh requires an explicit browser confirmation.

![SEO Workbench Markdown editor](docs/assets/workbench-editor.jpg)

The editor checks file revisions before saving. If an agent changes the same document, the UI preserves your local edit and asks you to compare or reload instead of overwriting either version.

## Common commands

```bash
# Projects and workflow
./seo projects --json
./seo --project my-site status --json
./seo --project my-site next
./seo --project my-site step done
./seo --project my-site keywords collect --google-ads-csv google-ads.csv --semrush-xlsx semrush.xlsx --json

# Technical evidence
./seo --project my-site evidence --rendered --json
./seo --project my-site technology --json
./seo --project my-site performance --json
./seo --project my-site tech-audit run --json
./seo --project my-site tech-audit recrawl --url https://example.com/missing --json
./seo --project my-site tech-audit diff --json
./seo --project my-site tech-audit issues list --status open --json
./seo --project my-site tech-audit issues status <fingerprint> fixed --owner seo --note "deployed" --json

# Google evidence, after configuration
./seo --project my-site crux --json
./seo --project my-site gsc collect --json
./seo --project my-site statistics collect --json

# Compare recent compatible snapshots
./seo --project my-site audit-diff --json

# Optional Hexcal seed import; Workbench decisions remain authoritative
./seo --project hexcal content import-feishu --profile hexcal-seo --json

# Workbench-led Blog production
./seo --project my-site content cluster-brief --json
./seo --project my-site content import-clusters --from-file clusters.json --json
./seo --project my-site content status <item_id> ready_to_write --note "topic approved" --json
./seo --project my-site content brief <item_id> --json
./seo --project my-site content import-draft --from-file article.json --json
./seo --project my-site content qc <item_id> --json
./seo --project my-site content status <item_id> approved --note "human approved" --json
./seo --project my-site content publish-dry-run <item_id> --blog-id <blog_id> --json
./seo --project my-site content publish <item_id> --blog-id <blog_id> --confirm --json
./seo --project my-site gsc inspect --limit 10 --json
./seo --project my-site content index-status --notify-role seo --profile my-site --confirm --json
./seo --project my-site pages refresh --json

# Reporting archive
./seo --project my-site reports list --json
./seo --project my-site reports new --json

# Record a shipped SEO change, then evaluate it after the review window
./seo --project my-site changes add --url https://example.com/page --type content \
  --hypothesis "Improve qualified clicks" --metric clicks --metric conversions --json
./seo --project my-site business-signals import --from-file business-signals.csv --json
./seo --project my-site changes evaluate <change_id> --json

# Import repeatable backlink exports from any provider
./seo --project my-site backlinks import --from-file backlinks.csv --source semrush --json
./seo --project my-site backlinks status --source semrush --json

# Optional paid DataForSEO evidence (uses project-private BYOK credentials)
./seo --project my-site backlinks collect --confirm-paid --json
./seo --project my-site backlinks gap --competitor competitor-a.com \
  --competitor competitor-b.com --confirm-paid --json

# Environment and project checks
./seo --project my-site validate --json
./seo --project my-site doctor --json
./setup.sh --check
```

Use `./seo --help` and `./seo <command> --help` for the full command reference.


## Optional Google integrations

CrUX requires a Google API key. GSC supports desktop OAuth and service accounts, requests read-only access, and never submits Sitemaps. Ordinary Blog URLs rely on Sitemap discovery and GSC monitoring; `content index-submit` is retained only as a fail-safe compatibility command and rejects Blog submissions because Google's Indexing API is limited to `JobPosting` and `BroadcastEvent` pages.

See [Google integrations](docs/google-integrations.md) for setup, authentication, evidence scopes, and status meanings.

## Optional Shopify integration

Shopify projects can store one project-scoped Admin API access token. The Workbench verifies the canonical `.myshopify.com` domain and granted access scopes before saving, never returns the token, and warns when the connected app has write scopes.

See [Shopify integrations](docs/shopify-integrations.md) for custom app setup, rotation, and security boundaries.

## Setup requirements

`./setup.sh` creates the Python environment, installs the pinned Python and Node dependencies, builds the Go technology helper and browser UI, and resolves Chrome or Chromium for rendered audits and Lighthouse.

Automatic installation of missing system runtimes currently requires macOS and Homebrew. On other systems, install these prerequisites first:

- Git
- uv
- Python 3.11
- Go 1.25 or newer
- Node.js 24
- Chrome or Chromium

## Documentation

- [SEO tutorial index](docs/README.md)
- [SEO iteration loop](docs/SEO迭代闭环.md)
- [BLOG production tutorial](docs/BLOG生产线操作教程.md)
- [Hexcal BLOG migration and production contract](docs/hexcal-blog-migration.md)
- [Google integrations](docs/google-integrations.md)
- [Shopify integrations](docs/shopify-integrations.md)
- [Standalone workbench architecture](docs/independent-workbench.md)
- [Preserved SEO capability families](docs/capability-preservation.md)

## Current boundaries

- The local UI can keep a project-scoped technical-audit scheduler alive while it is open; cron/launchd can call the same `tech-audit run --scheduled --json` command when the UI is closed. There is no hosted scheduler.
- One project represents one site. Use separate project folders for separate sites or stores.
- Lighthouse lab data, CrUX field data, and GSC search data remain separate evidence sources.
- Business signals accept aggregate page-window rows. GA4 and Shopify projects can collect read-only landing-page and product-revenue evidence locally; CSV/JSON import remains available for CRM and other sources.
- Backlink evidence preserves provider provenance. DataForSEO commands are metered, require `--confirm-paid`, and never turn capped collections into confirmed loss. Gap targets require an exact existing keyword-to-page mapping; Workbench does not calculate authority/toxicity scores, automate outreach, or generate disavow files.
- GSC OAuth requires the user to approve the first browser authorization.
- Local probes reject private network targets by default, but they are not a complete sandbox for malicious websites.

## Credits and References

SEO Workbench preserves and adapts useful ideas and material from:

- [claude-seo](https://github.com/AgriciDaniel/claude-seo)
- [seomachine](https://github.com/TheCraigHewitt/seomachine)
- [superseo-skills](https://github.com/inhouseseo/superseo-skills)
- [wappalyzergo](https://github.com/projectdiscovery/wappalyzergo)
- [Lighthouse](https://github.com/GoogleChrome/lighthouse)
- [open-seo](https://github.com/every-app/open-seo)
- [DataForSEO](https://dataforseo.com/)

See the local skill and third-party attribution files for component-specific terms.

Other useful references:

- [Shopify SEO Crawling](https://help.shopify.com/en/manual/promoting-marketing/seo/crawling-your-store)

## License

[MIT](LICENSE)
