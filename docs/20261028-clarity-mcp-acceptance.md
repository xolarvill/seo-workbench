# Clarity MCP implementation and acceptance

Date: 2026-10-28. Scope: the five-stage [integration plan](clarity-mcp-integration-plan.md).

## Delivered

- Pinned official server 2.0.1 / SDK 1.32.2, using the existing Node 24 runtime and
  a bounded stdio client. Actual initialization, discovery and missing-auth calls
  pass without provider credentials.
- Project-private connections, hidden/stdin token entry, candidate verification,
  rotation conflict detection, generation-scoped cache and disconnect. Public status
  distinguishes runtime, credential acceptance and unverified remote identity.
- Dashboard, recording and documentation commands, fixed local routes, background
  UI jobs, per-kind immutable evidence/current pointers, structured errors and warnings.
- Shared nonblocking project operation lease and cooldown cover both verification
  and queries. Scoped SIGTERM cleanup and a bounded nonblocking stdin/output transport
  prevent abandoned authenticated subprocesses and unbounded waiting.
- Connections → Optional includes configuration, queries, status and private results.
  Validated recording links are held in local UI server memory for up to 15 minutes,
  removed from job output before logging, generation-checked, and served with no-store.
- Evidence watcher refreshes preserve the active query form. Brand switches remount
  the panel and clear sensitive inputs. Existing shared status pills and help are reused.

## Validation

Executed in this implementation session:

- Backend/CLI/UI-route/transport tests plus Google/UI and statistical/business
  collector regressions: 97 passed.
- Related frontend integration and Clarity interaction tests: 10 passed.
- `npm run clarity:self-test`, `npm run ui:typecheck`, and `npm run ui:build`: passed.
  The existing large-chunk build advisory remains.
- Project `validate --json` and `doctor --json`: ok; optional missing browser-capture
  directory remains a warning, not a Clarity failure.
- Playwright desktop 1440×1050 and iPhone 13 390×844 with mobile UA: meaningful page,
  no app page errors, no horizontal overflow, empty token field, actual dashboard job,
  recording filters and transient recording links exercised. The Browser plugin was
  unavailable. The matching installed Chromium required sandbox escalation after an
  explicit macOS MachPort permission failure; the daily browser was not substituted.
- Credential storage mode 0600 and secret scans of tracked/untracked distributable
  files and Clarity audit JSON: no supplied token found.
- Security/architecture specialist review identified private-path filter exposure,
  cancellation ownership, verification lease bypass and missing transient links. These
  were fixed with regression checks; architecture follow-up found no unresolved findings.

Full frontend suite has four pre-existing failures in `components.test.tsx`: three
Pages drawer/action tests and the Markdown preview font-size expectation. All four
were reproduced from the pre-integration `d2565b2` source in a separate temporary
tree with the same installed dependencies. They were not silently counted as passing
or changed as part of this integration.

## Live-provider limits

Authenticated dashboard and bounded recording queries succeeded for the configured
private project. The documentation tool returned HTTP 500 on two different focused
questions; the last record retains the observed status and provider_error. The adapter
is implemented and failure handling is verified, but this service capability cannot
be claimed operational at acceptance time.

The dashboard response did not independently confirm its reporting window, timezone
or remote project identity. Consequently these observations remain partial exploratory
evidence. There was no independent signed-in Clarity dashboard reconciliation; no
claim is made that these observations are a production statistics baseline. Provider
limits and maximum history remain unverified. No tracking installation, consent
change, existing statistics migration or external publication was performed.

Private project configuration, query counts, evidence pointers and screenshot locations
are recorded only in that project's report. See [operator guide](clarity-integrations.md)
for ongoing use and recovery.
