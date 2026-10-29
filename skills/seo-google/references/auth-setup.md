# Google authentication and project binding

The maintained setup contract is [Google integrations](../../../docs/google-integrations.md). Read it when creating or repairing a connection; use the current CLI help for arguments. Authentication profiles and per-project property bindings replace the source pack's global configuration.

## Existing setup first

Inspect the local Connections workspace or current project status for the requested source. CrUX, GSC and GA4 have separate configuration and access scopes. A configured API key does not imply access to a GSC or GA4 property.

Credential material lives below ignored `.runtime/google/`; property bindings live below the selected project's ignored `.runtime/integrations/`. Files use private permissions. Use the Workbench credential flow and keep secrets out of skill documents, reports, command output and audit artifacts.

## Search Console

For Desktop OAuth, import a client JSON through Connections or use:

```bash
./seo --project example-store gsc auth --profile default --client-secret /path/to/client-secret.json
```

The consent flow needs the user. For a service account already granted access to the relevant Search Console property, use the `--service-account` alternative shown by `gsc auth --help`.

List visible properties, then bind the exact domain or URL-prefix property through the existing commands:

```bash
./seo --project example-store gsc properties --profile default --json
./seo --project example-store gsc bind --profile default --property sc-domain:example.com --json
```

Binding checks access and coverage of the project's URL. These commands use read-only Search Console scope. GSC collection and binding do not require ownership or a write scope for indexing or sitemap submission.

## GA4 and CrUX

GA4 uses its separate `analytics.readonly` token and an explicit numeric property binding. Follow the Google integrations document and `ga4 properties`/`ga4 bind` help rather than reusing a Search Console token by assumption. A service account needs access to that GA4 property.

CrUX uses the Workbench key storage or supported environment setting documented in Google integrations. Its field records do not require a Search Console property binding. Local Connections stores, rotates and verifies supported credentials without returning secret values.

## Diagnose the actual result

`needs_auth` indicates a missing/invalid binding or authorization handoff; an access-denied response needs identity/property checks. `needs_config` indicates absent required configuration. CrUX `no_data` is an eligible-record coverage result, distinct from failed authentication. Preserve the collector's response when diagnosing quota or API-enable failures.

Optional Google APIs require their own verified integration and scopes. Do not broaden an existing read-only profile to enable an unrelated API workflow.
