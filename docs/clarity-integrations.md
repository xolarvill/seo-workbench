# Microsoft Clarity integration

Workbench runs the official Clarity MCP server through a pinned local SDK client.
The implementation is shared; credentials, website, query timezone, cache and evidence
belong to the selected project. There is no global authenticated Clarity connection.

## Setup

`./setup.sh` installs the locked Node dependencies. `npm run clarity:self-test`, using
the project Node 24 runtime, checks actual stdio initialization, tool discovery, a
missing-auth tool response and shutdown without accessing a Clarity account.
`./seo --project example-store doctor --json` reports missing optional support as a warning.

Obtain a Data Export token from the target Clarity project's Settings → Data Export.
Use **Connections → Optional → Microsoft Clarity** to enter the project ID, explicit
IANA query timezone and token. Save verifies the candidate before replacement. The
token field clears after success or failure and is never returned by the API.

Alternatively, use the hidden CLI prompt:

```bash
./seo --project example-store clarity configure --clarity-project abc123 --timezone UTC --json
./seo --project example-store clarity status --json
./seo --project example-store clarity verify --json
```

Automation may pipe one token line through stdin with `--token-stdin`; never put the
token in a shell argument, environment dump or report. Initial offline configuration
supports `--skip-verify`; rotation always verifies. Credentials are stored only at
`projects/<id>/.runtime/integrations/clarity.json` (0600; directories 0700).
The declared project ID is not an independently verified account identity. A
successful query proves that the credential can access the service, not that the
returned data independently identifies the selected website. Status preserves this distinction.

## Queries

```bash
./seo --project example-store clarity query --query "Total sessions" \
  --start 2026-10-20 --end 2026-10-21 --timezone UTC --json
./seo --project example-store clarity recordings \
  --start 2026-10-20T00:00:00Z --end 2026-10-22T00:00:00Z \
  --device Mobile --rage-click --count 10 --json
./seo --project example-store clarity docs --query "How are rage clicks defined?" --json
```

Dashboard dates are inclusive; recordings use explicit UTC instants, with the end
representing the requested boundary. The UI's inclusive date inputs convert to
the next UTC midnight for recordings. The dashboard server subprocess receives the
explicit query timezone through `TZ`. This is a query setting, not proof of the
Clarity project's native reporting timezone.

Recordings default to 10 samples, maximum 50. Optional filters include `--url` (clean
same-site public HTTPS only), `--device`, `--channel`, `--rage-click`, `--dead-click`
and `--js-error`. The UI queues the same fixed CLI operations through the existing
job runner. There is no shell, arbitrary tool name, server URL or executable field.

The CLI prints status and evidence paths, not provider payloads. Read the private
evidence file or use the local UI for results. Recording samples can be opened
from transient local links immediately after a UI query. Links remain in UI server
memory for at most 15 minutes, are brand/credential-generation scoped, and do not
enter evidence or job logs. After server restart or expiry, use Refresh cached
result to request new links. Recording results contain samples, not a complete
population or an estimated overall problem rate.

## Evidence and failure handling

`audits/clarity/{dashboard,recordings,documentation}/` contains immutable timestamped
records, `latest.json`, and `last_successful.json` when a complete result exists.
The top-level `audits/clarity/latest.json` indexes each kind separately. All evidence
is private, including the default scaffold project's Clarity directory.

`clarity-evidence-v1` records versions, declared binding, exact request, provider-confirmed
scope when present, sanitized response, warnings and collection status. Unknown fields
are excluded. User/session identifiers, inputs, credentials and private recording links
are not persisted. URL query values and private commerce paths are redacted.

- `ok`: usable complete reference evidence; does not imply cross-source comparability.
- `partial`: exploratory response, including an unconfirmed reporting scope or narrative.
- `failed`: configured request failed; inspect `reason_code`.
- `not_collected`: configuration/runtime/auth unavailable or another operation is busy.

The official server can return HTTP failures as ordinary text. Workbench detects
these responses; nonempty text alone is not a successful metric query. Hidden HTTP
status stays `provider_error` rather than a guessed auth/limit diagnosis. The backend's
nonzero `dataErrorType` is `provider_query_error`; do not invent its undocumented enum meaning.

Operations have a 60-second parent deadline, bounded output and owned-process cleanup.
Queries and credential verification share a nonblocking per-brand lease and cooldown.
Known 429s trigger 60 seconds of cooldown; no automatic network retries. Matching usable
results are cached for 15 minutes. `--force` bypasses cache but not cooldown. A failed
request never replaces history with zero or erases the last successful snapshot.

Clarity does not feed `statistics collect`, replace CrUX performance verdicts or alter
GA4/Shopify measurement windows. Narrative output is external data, never instructions.
This integration reads existing data; it does not install tracking or change consent.

## Disconnect and recovery

```bash
./seo --project example-store clarity disconnect --json
```

Disconnect deletes only this brand's credential file. Existing private evidence remains.
Reconfigure to recover. Missing runtime requires `./setup.sh`; unsupported tool schema
fails explicitly instead of switching to an undocumented HTTP API. Removing the optional
entry points does not require migrating any existing source data.

Official sources: [server](https://github.com/microsoft/clarity-mcp-server),
[tool schemas](https://github.com/microsoft/clarity-mcp-server/blob/main/src/types.ts),
[error handling](https://github.com/microsoft/clarity-mcp-server/blob/main/src/utils.ts).
