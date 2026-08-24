# Hexcal BLOG adapter

SEO Workbench retains the Hexcal BLOG production flow as an optional project adapter. The adapter covers keyword and pipeline imports, writing briefs, Feishu review, asset handoff, Shopify publishing, GSC inspection, and reporting. Workbench files remain the source of truth.

For daily commands, see the [BLOG production tutorial](BLOG生产线操作教程.md).

## Private configuration

Copy the example gateway profile, then replace every placeholder in the ignored runtime file:

```bash
mkdir -p .runtime
chmod 700 .runtime
cp templates/hexcal-feishu-profile.json .runtime/profiles.json
chmod 600 .runtime/profiles.json
```

Keep the following values only in `.runtime/profiles.json`:

- Feishu Base tokens, table IDs, and field IDs;
- app-scoped user IDs and chat IDs;
- the local `lark-cli` profile name.

The example profile maps remote IDs to semantic aliases such as `keyword`, `status`, `draft_html`, and `mmx`. Company resource identifiers do not enter source code or tracked public artifacts. Feishu record IDs needed for incremental merging and review remain only in ignored Hexcal project/runtime evidence.

Credentials remain in `lark-cli`. Do not place credentials in the gateway profile, project documents, command arguments, or Git history.

Workbench implements the small Feishu boundary in `seo_workbench/feishu_gateway.py`. It resolves private aliases, calls `lark-cli`, and returns normalized records to the Hexcal adapter. No separate bot package or sibling repository is required.

Every Feishu command requires an explicit `--profile`; Workbench never falls back to a shared default destination.

## Import

```bash
./seo --project hexcal content import-feishu \
  --profile hexcal-seo \
  --json
```

The gateway reads the configured Base tables, replaces remote field IDs with semantic aliases, and caches the private response under `projects/hexcal/.runtime/feishu/`. The importer then merges records into:

```text
projects/hexcal/
  strategy/keyword-pool.jsonl
  content/blog-pipeline.jsonl
  content/assets/
  content/reports/
  audits/publish/
  audits/runs/
  state.json
```

Matching Workbench records keep their existing local title, keyword, status, draft, and operator notes. Feishu can add missing records but does not replace local decisions.

## Retained capabilities

| Capability | Workbench command or file |
|---|---|
| Keyword intake and scoring | `keywords collect`, `strategy/keyword-pool.jsonl` |
| Feishu keyword and article import | `content import-feishu` |
| Topic clustering | `content cluster-brief`, `content import-clusters` |
| Writing and revision briefs | `content brief`, `content revise-brief` |
| Draft import and QC | `content import-draft`, `content qc` |
| Feishu asset candidates | `content asset-candidates`, `content describe-candidates` |
| Shopify image handoff | `content download-assets`, `content upload-assets`, `content apply-assets` |
| Review messages and reply digest | `content review-push`, `content review-digest` |
| Shopify dry-run and publish | `content publish-dry-run`, `content publish --confirm` |
| GSC indexing evidence | `gsc inspect`, `content index-status` |
| Daily and weekly reports | `content report`, `content notify-report --confirm` |

Hexcal product anchors, brand exclusions, and product-link suggestions activate only when the project name is `Hexcal`. Other projects keep the same SEO and content commands without inheriting Hexcal defaults.

## Status mapping

| Imported status | Workbench status |
|---|---|
| `cluster_pending` | `planned` |
| `cluster_approved` | `ready_to_write` |
| `cluster_dropped` | `dropped` |
| `in_writing` | `drafting` |
| `review` | `review` |
| `in_writing_failed` | `blocked` |
| `修改中` | `revision_requested` |
| `approved` | `approved` |
| `推送已排期` | `scheduled` |
| `已提交索引` | `submitted_for_indexing` |
| `已收录` | `indexed` |
| `收录异常` | `indexing_issue` |

The mapping runs only during Hexcal imports. Generic content status updates accept Workbench statuses directly.

## Operator boundary

These operations are read-only or local by default:

- Feishu import;
- keyword and queue planning;
- brief and report generation;
- GSC collection and URL Inspection;
- review-reply digest.

Shopify publish, Feishu messages, status mutations derived from review replies, and report delivery require an explicit operator action. `content publish` and notification commands also require `--confirm`.
`content describe-candidates` is read-only with `--no-writeback`; Feishu MMX writeback requires `--confirm`.

Ordinary BLOG URLs use Sitemap discovery and read-only GSC inspection. The Google Indexing API compatibility command rejects BLOG URLs.

Shopify owns the release clock after it accepts a future `scheduled_at`. SEO Workbench has no hosted worker; run due tasks from `content ops` or an external scheduler.
