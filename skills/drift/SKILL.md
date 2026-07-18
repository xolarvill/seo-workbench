---
name: drift
description: >
  Compare immutable Workbench audit snapshots to find SEO regressions while
  preserving collection identity and comparability. Use for before/after,
  release checks, audit diff, regression, or monitoring requests.
user-invokable: true
argument-hint: "[raw|technology|performance|crux|gsc]"
license: MIT
metadata:
  category: seo
---

# SEO Audit Diff

Use the repository's project-scoped `audit-diff` command. Do not use the removed `/seo drift` commands, external `~/.cache/claude-seo` database, or legacy scripts.

## Evidence model

Collectors write immutable timestamped snapshots plus a stable `latest.json` pointer inside the current project:

| Kind | Evidence | Important identity boundaries |
|---|---|---|
| `raw` | HTTP, HTML, metadata, links, route sample | requested site and crawl contract |
| `technology` | fingerprint evidence and architecture analysis | provider, scan mode, target identity |
| `performance` | sequential Lighthouse runs and aggregation | runtime, profiles, requested/final URLs |
| `crux` | current and historical field metrics | effective URL/origin scope and form factor |
| `gsc` | Search Analytics, URL Inspection, Sitemap | property, search type, window, finalized state |

The command selects the newest snapshot and the newest earlier snapshot with matching identity. If only one matching snapshot exists, report `no_baseline`. If the identity or evidence contract is incompatible, report the comparability warning instead of classifying a regression.

## Standard workflow

Before a release or material SEO change, collect the relevant baseline:

```bash
./seo --project <id> evidence --rendered --technology --json
./seo --project <id> performance --json
```

Add CrUX or GSC only when explicitly needed and configured:

```bash
./seo --project <id> crux --json
./seo --project <id> gsc collect --json
```

After the release, repeat the same collectors with the same target and options. Then compare:

```bash
./seo --project <id> audit-diff --json
```

Compare one kind:

```bash
./seo --project <id> audit-diff --kind raw --json
./seo --project <id> audit-diff --kind technology --json
./seo --project <id> audit-diff --kind performance --json
./seo --project <id> audit-diff --kind crux --json
./seo --project <id> audit-diff --kind gsc --json
```

Explicit files are supported for one kind only:

```bash
./seo --project <id> audit-diff \
  --kind raw \
  --from projects/<id>/audits/raw/evidence-<before>.json \
  --to projects/<id>/audits/raw/evidence-<after>.json \
  --json
```

Both paths must remain inside that kind's project audit directory and share the same audit identity.

## Interpretation order

For every comparison:

1. Read `status`, `comparable`, warnings, baseline path, and current path.
2. Confirm collection status and final URL before interpreting changes.
3. Separate confirmed changes from collection gaps and architecture inferences.
4. Identify affected templates or routes rather than extrapolating from one page.
5. Prioritize by indexability, user impact, business importance, and confidence.

Do not call a change a regression merely because a score moved. Confirm the underlying metric or document change and its evidence boundary.

## Kind-specific rules

### Raw and rendered evidence

Review status, final URL, title, description, canonical, robots, headings, links, schema presence, navigation, and raw/rendered differences. A deliberate content change is not automatically a defect. A new `noindex`, wrong canonical, soft 404, broken navigation, or missing primary content deserves urgent verification.

### Technology

Detection is presence evidence, not a complete inventory. A missing fingerprint can reflect route, consent, runtime, scan mode, or provider changes. Use `architecture_analysis.evidence_quality` and explicit asset evidence before concluding that a dependency was removed.

### Lighthouse

Compare only matching runtime, profile, requested URL, main document, and final URL conditions. Keep individual LHR runs available. Lighthouse is lab evidence; do not replace it with CrUX or combine their scores.

### CrUX

Compare only the same effective scope and form factor. A page-to-origin fallback changes meaning. `no_data` usually means eligible field data is unavailable, not that performance is good or bad.

### GSC

Compare Search Analytics only when property, search type, window length, and finalized state match. URL Inspection describes Google's indexed version, not a live test. Sitemap fields indicate submitted and processed state, not guaranteed index coverage.

## Output

Read the current report from:

```text
projects/<id>/audits/diffs/latest.json
```

Timestamped `audit-diff-*.json` files are immutable records. The report should explain:

- what changed;
- whether the snapshots are comparable;
- evidence confidence and collection gaps;
- which routes or templates are affected;
- the smallest verification or fix;
- whether the change appears intentional.

If the optional UI is active, continue using the same CLI and project files. The filesystem watcher will surface the new diff automatically. Never read or expose the UI token.

## Error handling

| Status | Action |
|---|---|
| `no_data` | Run the relevant collector or report why it is unavailable |
| `no_baseline` | Preserve the current snapshot and repeat the same collection after a meaningful change or interval |
| not comparable | Explain the mismatched identity or contract and recollect under matching conditions |
| partial collection | Use surviving evidence, list missing components, and avoid absence claims |
| GSC `needs_auth` | Hand authentication back to the user; continue non-Google evidence |
| CrUX `no_data` | Keep Lighthouse as separate lab evidence; do not fabricate field data |

## Cross-skill follow-up

- Raw/rendered or canonical issue: `technical-audit`
- Structured-data issue: `schema`
- Content or intent change: `page-audit`
- Trust or evidence issue: `eeat-audit`
- Lighthouse or CrUX change: `technical-audit`
- Query, index, or Sitemap change: `technical-audit` with GSC evidence
