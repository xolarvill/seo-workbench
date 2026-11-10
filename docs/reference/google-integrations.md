# Google integrations

SEO Workbench uses the official CrUX, Search Console, and Google Analytics Data APIs. CrUX, Lighthouse, GSC, and GA4 remain separate evidence sources so an agent can explain whether a conclusion comes from lab execution, aggregated Chrome users, Google Search, or first-party site behavior.

## Setup boundary

`./setup.sh` installs and verifies `google-auth` and `google-auth-oauthlib`, creates private runtime directories, and checks that the local environment can load them. It cannot create Google Cloud credentials or grant Search Console access.

All credential material is stored below `.runtime/google/` with private file permissions. Per-project property bindings are stored at `projects/<id>/.runtime/integrations/google.json`. These paths, CrUX artifacts, and GSC artifacts are ignored even for `projects/default`.

## Visual credential management

Start the local UI and open **Connections**:

```bash
./seo --project example-store ui
```

The Connections workspace supports the complete operator flow:

1. Store, rotate, verify, or remove the workspace CrUX API key.
2. Import a Google Desktop OAuth JSON file and complete consent in the browser, or import a service account JSON file.
3. List Search Console properties visible to the selected auth profile.
4. Bind one exact property to the current SEO project.
5. Run CrUX or GSC evidence collection and inspect the resulting status.
6. Disconnect project bindings and delete unused auth profiles.

GA4 uses a separate `analytics.readonly` token and an explicit project-to-property binding. A 28-day collection stores landing-page and acquisition-channel aggregates ending two complete days ago by default; it does not collect user or event identifiers. To compare with finalized GSC and Shopify evidence, pass the GSC window's exact end date to both business collectors.

```bash
./seo --project example-store ga4 properties --profile ga4 --json
./seo --project example-store ga4 bind --profile ga4 --property 123456789 --json
./seo --project example-store ga4 collect --end-date 2026-08-10 --json
```

For routine production use, prefer `./seo --project example-store statistics collect --json`. It selects the finalized GSC end date, aligns GA4 and Shopify automatically, persists aggregate date-by-page history, and refuses incomparable windows. Record tracking, consent, property, or key-event definition changes with `statistics regime add`; see the [statistical SEO operations manual](统计学SEO操作手册.md).

Security rules:

- Credential APIs are available only on the local `127.0.0.1` or `localhost` Workbench session. Remote hosts cannot use them.
- Secret values are write-only. Status responses contain credential type, profile name, service account identity when applicable, and timestamps, but never API keys, OAuth secrets, private keys, or tokens.
- UI imports accept JSON content only, never arbitrary filesystem paths or shell commands. Payloads are limited to 128 KB.
- Credential files and project bindings use mode `0600`; credential directories use mode `0700`.
- A profile cannot be deleted while any project is bound to it. Disconnect those projects first.
- Environment-managed CrUX keys remain read-only in the UI. Restart the UI with a different environment value to rotate them.

The CLI remains available for automation and recovery. UI and CLI use the same runtime files and binding contract.

## CrUX

Enable the Chrome UX Report API in a Google Cloud project and create an API key. Supply it through `SEO_WORKBENCH_CRUX_API_KEY` or `.runtime/google/crux-api-key`.

```bash
export SEO_WORKBENCH_CRUX_API_KEY="your-key"
./seo --project example-store crux --json
```

The default run requests aggregate, PHONE, and DESKTOP data. Each successful scope contains the current 28-day rolling record and 40 weekly history periods. A page-level miss falls back to its origin for that form factor; history then uses the same effective scope. `no_data` means neither page nor origin had an eligible record and is not a collector failure.

## Search Console authentication

Enable the Search Console API. For local use, create an OAuth client of type Desktop app and download its JSON file:

```bash
./seo --project example-store gsc auth \
  --profile default --client-secret /path/to/client-secret.json
```

The first OAuth run opens Google's consent flow and requires the user. Later read-only commands refresh the stored token without repeating consent.

For automation, create a service account, add its email as a user on the required Search Console property, then run:

```bash
./seo --project example-store gsc auth \
  --profile automation --service-account /path/to/service-account.json
```

List accessible properties and bind the exact Search Console identifier. URL-prefix properties include scheme and trailing slash; Domain properties use `sc-domain:`.

```bash
./seo --project example-store gsc properties --profile default --json
./seo --project example-store gsc bind \
  --profile default --property sc-domain:example.com --json
```

Binding rejects inaccessible properties and properties that do not cover the project's URL.

## Collection behavior

```bash
./seo --project example-store gsc performance --days 28 --compare --json
./seo --project example-store gsc inspect --limit 10 --json
./seo --project example-store gsc sitemaps --json
./seo --project example-store gsc collect --json
```

- Search Analytics uses finalized web data and compares the latest complete 28-day window with the preceding 28 days. Query, page, query-page, device, and country rows paginate to the API's 50,000-row exposure ceiling. Query-page rows support landing-page ownership and multiple-page signals; country remains a separate market slice and is not merged into page totals.
- Inspection chooses the homepage and representative URLs from current evidence, deduplicates them, enforces the bound property, and stops immediately on quota exhaustion. It describes Google's indexed version, not a live test.
- Sitemap collection is read-only and excludes the deprecated `indexed` field.
- `gsc collect` writes component snapshots plus a composite `audits/gsc/latest.json` used by audit diff.

## Status handling

| Status | Meaning | Agent action |
|---|---|---|
| `ok` | Requested evidence was collected | Use it with its scope and date window |
| `partial` | Some API calls or URLs failed | Use successful components and disclose gaps |
| `no_data` | CrUX has no eligible page or origin record | Use Lighthouse only as lab evidence |
| `needs_config` | CrUX API key is missing | Ask the user to configure a key |
| `needs_auth` | GSC is unbound or unauthenticated | Ask the user to authenticate and bind a property |
| `failed` | Configured collection failed | Report the structured error; do not invent evidence |

`evidence --crux --gsc` preserves these component states. Missing Google configuration does not turn a successful raw site probe into a failure.
