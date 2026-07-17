# Google integrations

SEO Workbench uses the official CrUX and Search Console REST APIs. CrUX, Lighthouse, and GSC remain separate evidence sources so an agent can explain whether a conclusion comes from lab execution, aggregated Chrome users, or Google Search.

## Setup boundary

`./setup.sh` installs and verifies `google-auth` and `google-auth-oauthlib`, creates private runtime directories, and checks that the local environment can load them. It cannot create Google Cloud credentials or grant Search Console access.

All credential material is stored below `.runtime/google/` with private file permissions. Per-project property bindings are stored at `projects/<id>/.runtime/integrations/google.json`. These paths, CrUX artifacts, and GSC artifacts are ignored even for `projects/default`.

## CrUX

Enable the Chrome UX Report API in a Google Cloud project and create an API key. Supply it through `SEO_WORKBENCH_CRUX_API_KEY` or `.runtime/google/crux-api-key`.

```bash
export SEO_WORKBENCH_CRUX_API_KEY="your-key"
python -m seo_workbench --project example-store crux --json
```

The default run requests aggregate, PHONE, and DESKTOP data. Each successful scope contains the current 28-day rolling record and 40 weekly history periods. A page-level miss falls back to its origin for that form factor; history then uses the same effective scope. `no_data` means neither page nor origin had an eligible record and is not a collector failure.

## Search Console authentication

Enable the Search Console API. For local use, create an OAuth client of type Desktop app and download its JSON file:

```bash
python -m seo_workbench --project example-store gsc auth \
  --profile default --client-secret /path/to/client-secret.json
```

The first OAuth run opens Google's consent flow and requires the user. Later read-only commands refresh the stored token without repeating consent.

For automation, create a service account, add its email as a user on the required Search Console property, then run:

```bash
python -m seo_workbench --project example-store gsc auth \
  --profile automation --service-account /path/to/service-account.json
```

List accessible properties and bind the exact Search Console identifier. URL-prefix properties include scheme and trailing slash; Domain properties use `sc-domain:`.

```bash
python -m seo_workbench --project example-store gsc properties --profile default --json
python -m seo_workbench --project example-store gsc bind \
  --profile default --property sc-domain:example.com --json
```

Binding rejects inaccessible properties and properties that do not cover the project's URL.

## Collection behavior

```bash
python -m seo_workbench --project example-store gsc performance --days 28 --compare --json
python -m seo_workbench --project example-store gsc inspect --limit 10 --json
python -m seo_workbench --project example-store gsc sitemaps --json
python -m seo_workbench --project example-store gsc collect --json
```

- Search Analytics uses finalized web data and compares the latest complete 28-day window with the preceding 28 days. Page and query rows paginate to the API's 50,000-row exposure ceiling.
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
