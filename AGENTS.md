# SEO Workbench

Agent-neutral SEO workflow repo. Use the local Python CLI and local `skills/` first.

## Current Shape

```text
seo_workbench/          Python execution layer: state, CLI, evidence wrappers
seo_workbench_tools/    Existing raw/rendered SEO evidence collectors
skills/                 Extracted first-party SEO playbooks
workflows/              Workflow manifests
templates/              State templates
projects/<id>/          One isolated runtime directory per store; default remains backward-compatible
third_party/            Attribution and upstream license notes
```

The original third-party repos are not runtime dependencies. Their useful content is preserved under `skills/`.

## Daily Commands

```bash
env UV_CACHE_DIR=.uv-cache uv run --frozen --python 3.11 python -m seo_workbench status
env UV_CACHE_DIR=.uv-cache uv run --frozen --python 3.11 python -m seo_workbench projects --json
env UV_CACHE_DIR=.uv-cache uv run --frozen --python 3.11 python -m seo_workbench --project example-store status --json
env UV_CACHE_DIR=.uv-cache uv run --frozen --python 3.11 python -m seo_workbench status --json
env UV_CACHE_DIR=.uv-cache uv run --frozen --python 3.11 python -m seo_workbench next
env UV_CACHE_DIR=.uv-cache uv run --frozen --python 3.11 python -m seo_workbench next --json
env UV_CACHE_DIR=.uv-cache uv run --frozen --python 3.11 python -m seo_workbench step done
env UV_CACHE_DIR=.uv-cache uv run --frozen --python 3.11 python -m seo_workbench phase TECHNICAL_AUDIT
env UV_CACHE_DIR=.uv-cache uv run --frozen --python 3.11 python -m seo_workbench evidence
env UV_CACHE_DIR=.uv-cache uv run --frozen --python 3.11 python -m seo_workbench evidence --json
env UV_CACHE_DIR=.uv-cache uv run --frozen --python 3.11 python -m seo_workbench evidence --rendered --crawl-limit 5 --json
env UV_CACHE_DIR=.uv-cache uv run --frozen --python 3.11 python -m seo_workbench technology --json
env UV_CACHE_DIR=.uv-cache uv run --frozen --python 3.11 python -m seo_workbench technology --scan-mode fast --json
env UV_CACHE_DIR=.uv-cache uv run --frozen --python 3.11 python -m seo_workbench evidence --technology --json
env UV_CACHE_DIR=.uv-cache uv run --frozen --python 3.11 python -m seo_workbench performance --json
env UV_CACHE_DIR=.uv-cache uv run --frozen --python 3.11 python -m seo_workbench evidence --performance --json
env UV_CACHE_DIR=.uv-cache uv run --frozen --python 3.11 python -m seo_workbench audit-diff --json
env UV_CACHE_DIR=.uv-cache uv run --frozen --python 3.11 python -m seo_workbench validate --json
env UV_CACHE_DIR=.uv-cache uv run --frozen --python 3.11 python -m seo_workbench doctor --json
```

If uv cannot read its user-profile managed Python, install Python locally for this workspace:

```bash
env UV_CACHE_DIR=.uv-cache UV_PYTHON_INSTALL_DIR=.uv-python uv python install 3.11
env UV_CACHE_DIR=.uv-cache UV_PYTHON_INSTALL_DIR=.uv-python uv sync --frozen --python 3.11
```

Initialize a project:

```bash
env UV_CACHE_DIR=.uv-cache uv run --frozen --python 3.11 python -m seo_workbench \
  init shopify-headless --name "Project" --url "https://example.com" \
  --framework hydrogen --hosting oxygen --cms sanity
```

## Working Rules

- Prefer `skills/` over third-party skill packs.
- Prefer `seo_workbench_tools/` for machine evidence; do not rewrite probes unless the existing collector cannot supply the field.
- Run `validate --json` after changing workflow, state, CLI contracts, or skill mappings.
- Run `doctor --json` when debugging local setup, missing evidence, or optional rendered support.
- Treat `projects/<id>/audits/raw/latest.json` as the stable current evidence pointer; timestamped `evidence-*.json` files are the immutable audit records.
- Project-level `evidence` defaults to a maximum of five representative same-host routes discovered from raw/rendered internal links. Keep discovery bounded, exclude static resources and sensitive query parameters, and use `--crawl-limit 0` for a strict single-URL run.
- For Headless SEO work, prefer `python -m seo_workbench evidence --rendered --json` when Playwright is available so `headless_audit` includes raw/rendered diffs.
- Evidence collectors should return structured JSON with `collection_status`, `errors`, and `warnings` even when some fetches fail.
- Technology detection uses the pinned Go helper under `seo_workbench_tools/technology_detector/`; keep its JSON contract stable and update fixtures before changing the fingerprint provider version.
- `technology` defaults to balanced Wappalyzer detection (page, scripts, robots, and DNS), then adds explicit asset-name fallback and consumes existing rendered runtime evidence when available. Use `--scan-mode fast` for the reproducible Go headers/cookies/raw-HTML path. Never turn a zero detection into a positive absence claim; record runtime-only gaps in `architecture_analysis.evidence_quality`.
- Rendered mobile evidence must use a mobile user agent as well as a mobile viewport. Preserve per-profile final URLs and report profile-specific navigation instead of merging desktop and mobile routes.
- Lighthouse performance evidence uses the pinned Node runner and browser resolved by `setup.sh`; keep runs sequential, default to five runs, and preserve every complete LHR before changing aggregation behavior.
- Performance summaries must preserve `requested_url`, `final_url`, `main_document_url`, per-run final URL consistency, and redirect status. Never compare performance snapshots that ended on different final URLs.
- Keep Lighthouse traffic behind `network_boundary.guarded_proxy` unless the user explicitly selects `--allow-private`; redact sensitive URL credentials and query values before persisting LHR or HTML artifacts.
- Treat `projects/<id>/audits/performance/latest.json` as the stable performance pointer; timestamped performance directories are immutable records.
- Keep stores isolated under `projects/<id>/`; prefer `--project <id>` for daily use and retain `--project-dir` for explicit external or test directories.
- Audit diff compares the newest immutable raw, technology, and performance snapshot with its newest matching URL/runtime baseline. Never classify a performance regression when Lighthouse, form factor, browser version, run count, variance, or benchmark comparability fails.
- Treat `projects/<id>/audits/diffs/latest.json` as the stable current diff pointer; timestamped `audit-diff-*.json` files are immutable records.
- Do not restore Claude slash commands or external repo dependencies unless the user explicitly asks.
- Each reform layer should be committed separately.

## Skill Modules

- `skills/keyword-deep-dive`
- `skills/content-brief`
- `skills/technical-audit`

Load only the referenced files needed for the current step.
