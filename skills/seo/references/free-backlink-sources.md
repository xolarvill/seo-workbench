# Backlink evidence source selection

Use with [backlinks](../../backlinks/SKILL.md). Read [Workbench operations](workbench-operations.md) for the installed collector and import interfaces.

## Source capabilities and inputs

| Source | Useful evidence | Required input or connection | Scope to preserve |
|---|---|---|---|
| Moz | Provider authority/spam metrics, referring domains, anchors and destination pages when included | Supplied export or a verified connector | Product/index, metric scale, capture date and row limits |
| Bing Webmaster | Links and anchors visible to the property; comparison data when actually supplied | Export or connector with access to the relevant property | Verified property, report population and truncation |
| Common Crawl web graph | Domain-level in-degree and graph relationships | Supplied release data or an explicitly available graph query service | Release identifier, domain-level granularity and coverage |
| Direct source-page observation | A particular link, anchor, rel and destination at capture time | Authorized bounded fetch/browser evidence | Final URL, response eligibility, rendering and capture time |
| DataForSEO | Backlink snapshots and competitor link intersections | Installed Workbench paid collector with configuration and spending authorization, or a supplied export | Target, provider snapshot completeness, row cap and reported cost |

Workbench does not bundle the source project's Moz, Bing, Common Crawl or standalone verification executors. Provider names describe possible evidence sources. Discover an available connector and inspect its schema before using it, or work from an export. Import supported exports through `backlinks import`; consult command help for the accepted input.

## Interpret coverage

Free and paid indexes both have sampling and crawl coverage limits. Inspect the actual response rather than assigning a fixed completeness percentage or numerical confidence weight to a vendor name.

Look for these biases:

- Popular sites may have more complete coverage than niche sites.
- Export row caps can hide the long tail or change the apparent anchor distribution.
- Verified-property access can make competitor datasets asymmetric.
- Domain graphs cannot answer page-level anchor or destination questions.
- Release lag can make a source unsuitable for a recent change review.

Keep comparable provider snapshots separate. Deduplicate source/destination relationships only within a documented view; keep original rows available for count reconciliation. A graph rank, provider authority score and directly observed link existence measure different things and cannot be averaged into an invented authority or toxicity score.

For known-link checking, inaccessible HTML or unresolved rendering is unknown. For provider-level disappearance, require two complete same-source snapshots. Recommend a different source only when its verified capabilities would fill a specific requested evidence gap.
