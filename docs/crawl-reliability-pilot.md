# Bounded crawl reliability pilot

Before resuming a broad audit, select up to 20 known routes across normal pages,
historic findings, major templates, and relevant locales. Record why each route
was selected. A representative sample is not a statistical false-positive-rate
estimate and does not establish site-wide graph coverage.

Use project-scoped `tech-audit recrawl` with concurrency 1, at least a two-second
request interval, and bounded retries/redirects. This entry point requires URLs
already present in the inventory. It writes an independent recrawl snapshot;
it does not replace the full-audit `latest.json` or sync the operator ledger.
Verify those protected files are unchanged. Review actual request receipts,
including recovered failures, rather than equating final error count zero with
no transient failures. Keep signatures out of reports.

For each sample, inspect status, final URL, evidence eligibility, request identity,
parser output, and preserved raw evidence. Replay suspected extraction problems
against the saved HTML using an independently implemented reference check. If
comparing an older parser, replay exactly the same HTML without network calls;
report the observed comparison even when both versions agree. Do not attribute
changes across different live HTML snapshots to a parser fix.

Evaluate bounded samples with `coverage_complete=False`. Label all first
observations as candidates. Report source/target coverage gaps explicitly;
missing sampled targets cannot prove missing hreflang return links or canonical
failures. An error template's self links and links from unavailable/non-HTML
sources are not evidence of incoming links from live pages. Keep these raw
outlink observations for inspection without expanding discovery from error
pages. Broken-link findings require a distinct, eligible observed source.

Exercise disconnects, throttling, cooldown persistence and resume on a local
HTTP fixture, not by increasing traffic to a production site. Verify successful
retries preserve the failed attempt and clear the final transport error, the
first 429 stops further host requests, failed URLs remain recoverable, and
resuming after cooldown preserves immutable earlier artifacts.

Readiness means the bounded collection/recovery and evidence gates behave as
specified. Outstanding real 404s or editorial heading choices do not require
alert counts to reach zero. Crawler response times remain diagnostics, not
CrUX performance verdicts. Do not claim browser-profile parity from raw HTML or
silently start an unbounded crawl as part of this pilot. Keep operational run
reports and store-specific URL lists in the project's private reports directory.
