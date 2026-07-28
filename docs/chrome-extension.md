# SEO Workbench Chrome extension

## Product role

The Chrome extension is an optional browser companion, not a prerequisite for SEO Workbench.

| Mode | Available behavior |
| --- | --- |
| Extension not installed | The CLI, local UI, skills, and all existing workflows remain complete. |
| Extension installed, Workbench offline | Inspect the active page and export a local JSON capture. |
| Extension installed, Workbench connected | Match a project, persist browser evidence, compare collection freshness, open the Workbench, and prepare an agent handoff. |

Missing browser evidence is `not_collected`, never proof that a page has no issue. Playwright rendered evidence remains the fallback for workflows that do not use the extension.

## Shared data contract

The project repository is the durable source of truth. HTTP is transport and SSE is notification only.

```text
active tab -> extension -> local API -> projects/<id>/audits/browser/
                                      -> local UI
                                      -> Codex/Claude/other agents
```

Browser captures use `schema/browser-capture-v1.schema.json` and preserve the existing evidence vocabulary: `schema_version`, `collection_status`, URLs, page facts, `errors`, and `warnings`.

```text
projects/<id>/audits/browser/
├── latest.json
└── browser-capture-<UTC timestamp>-<capture id>.json
```

Timestamped files are immutable records. `latest.json` is the stable pointer. Captures are observations from an interactive browser, not replacements for raw HTML, Playwright, Lighthouse, CrUX, or GSC evidence.

The extension never submits cookies, local storage, form values, authorization headers, complete HTML, or sensitive query values. The server validates request size and every nested schema field, rejects unknown fields, redacts sensitive query values, and confirms the project and extension authorization before writing. Captured page text is marked as untrusted external data for downstream agents.

## Product surface

The side panel is useful without an AI runtime and uses five compact views:

- **Overview**: page identity, indexability, issue summary, metadata, and freshness.
- **Structure**: headings, content landmarks, language, hreflang, and structured data.
- **Assets**: images, links, resource hints, and media loading attributes.
- **Signals**: Open Graph, Twitter cards, browser navigation observations, and runtime-only caveats.
- **Workbench**: optional connection, project match, capture persistence, export, Workbench launch, Codex launch, and handoff copy.

No traffic, backlink, Whois, rank, or paid-provider estimate is invented from page data.

## Local integration

The extension connects only to the loopback Workbench UI. Pairing is an explicit user gesture and produces a revocable token scoped to project discovery, browser capture writes, and fixed Workbench/Codex launch actions. The browser stores the token locally; the Workbench stores only its SHA-256 hash under ignored `.runtime/` paths. Tokens never enter project artifacts.

Pairing flow:

1. Start the local UI with `./seo ui`.
2. Open the extension's **Workbench** tab and confirm the loopback URL.
3. Click **Connect securely**. The extension creates a one-time verifier and opens a local approval page.
4. Approve the listed scopes in the authenticated Workbench session.
5. Return to the side panel, choose the matched project, and click **Save capture** when evidence should be persisted.

Pairing tokens expire after 30 days. Disconnecting revokes the server-side client and removes the browser token; a local operator can revoke all clients independently by removing the ignored `.runtime/ui/extensions.json` registry while the UI is stopped. The inspector, JSON export, and handoff copy continue working without a connection.

The side panel invalidates a capture when the active tab navigates or changes. Save also rechecks the tab identity and URL, and no unmatched hostname is silently assigned to the first project.

`Open in Codex` is a narrow local action. The server resolves the fixed repository root and executes `codex app <root>` without a shell. The extension cannot provide a command, prompt, or filesystem path.

## Local installation

```bash
npm ci
npm run extension:build
```

Then open `chrome://extensions`, enable Developer mode, choose **Load unpacked**, and select `extension/dist`. The extension opens as a Chrome side panel when its toolbar icon is clicked.

The requested permissions are deliberately narrow:

- `activeTab` and `scripting` inspect the page only after the toolbar action is used.
- `sidePanel` presents the inspector without modifying the page.
- `storage` keeps local connection settings and the paired token.
- Chrome's permission-free `tabs.create()` opens explicit approval and Workbench surfaces; no broad `tabs` browsing-history permission is requested.
- Loopback host access is limited to `http://127.0.0.1/*` and `http://localhost/*`.

Restricted browser pages such as `chrome://` cannot be inspected. Because Chrome can reopen a persistent side panel without granting `activeTab`, start or refresh an inspection by clicking the SEO Workbench toolbar icon on the target page. The service worker explicitly disables Chrome's automatic action-to-panel behavior so that this click reaches the extension and grants page access. If the Workbench uses a non-default port, change only the loopback URL in the Workbench tab.

## Brand

The product name is **SEO Workbench** everywhere. The extension subtitle is **On-page SEO inspector**.

The global mark combines a four-corner inspection frame, a compact `W`, and one emerald evidence dot. It uses the existing Workbench palette:

- Graphite: `#171A19`
- Ink: `#1B1E1D`
- Emerald: `#138A68`
- Paper: `#FFFFFF`
- Amber: `#C88721`
- Regression: `#BF4D45`

The source SVG is authoritative. Chrome, the web UI, documentation, and release assets derive from it.

## Release contract

The extension has an independent version and tag namespace:

```text
tag: chrome-v0.1.0
artifact: seo-workbench-chrome-v0.1.0.zip
checksum: seo-workbench-chrome-v0.1.0.zip.sha256
```

A `chrome-v*` tag runs tests in a read-only build job, builds the Manifest V3 package, validates its contents and version, creates a checksum, and passes only the artifacts to a write-scoped GitHub Release job. A manual workflow builds the same artifacts without publishing a release. Chrome Web Store publication is separate because it requires a store account and OAuth credentials.

Local release rehearsal:

```bash
npm run extension:typecheck
npm run extension:test
npm run extension:package
(cd dist/releases && shasum -a 256 -c seo-workbench-chrome-v0.1.0.zip.sha256)
```

Release only from a version-matching tag:

```bash
git tag chrome-v0.1.0
git push origin chrome-v0.1.0
```

The packager rejects missing entry points, unexpected or hidden files, source maps, symlinks, permission drift, non-loopback host permissions, and a tag/Manifest version mismatch. ZIP entries use a fixed timestamp so identical inputs produce a stable archive and checksum.

## Commercial maturity target: 8/10

The first release is complete only when all of these are evidenced:

1. Useful active-page inspection while Workbench is offline.
2. Clear loading, empty, restricted-page, disconnected, partial, error, and success states.
3. Keyboard navigation, visible focus, reduced-motion support, and 40px minimum targets.
4. Structured metadata, headings, images, links, structured data, social, hreflang, and navigation observations.
5. Explicit evidence provenance and no mixing with Lighthouse or field data.
6. Optional, authenticated project matching and atomic capture persistence.
7. JSON export, agent handoff copy, Workbench launch, and bounded Codex launch.
8. Unified icon and product name at 16, 32, 48, 128, 256, and 512 pixels.
9. Unit, contract, build, package, and real Chrome checks.
10. Automatic ZIP, checksum, and GitHub Release with install and privacy documentation.

Out of scope for 8/10: accounts, billing, cloud sync, team collaboration, paid data providers, Chrome Web Store OAuth publication, Firefox/Safari ports, arbitrary terminal execution, and embedded AI chat.
