# SEO Workbench

Agent-neutral SEO workflow repo. Use the local Python CLI and local `skills/` first.

## Current Shape

```text
seo_workbench/          Python execution layer: state, CLI, evidence wrappers
seo_workbench_tools/    Existing raw/rendered SEO evidence collectors
skills/                 Extracted first-party SEO playbooks
workflows/              Workflow manifests
templates/              State templates
projects/default/       Default runtime project directory
third_party/            Attribution and upstream license notes
```

The original third-party repos are not runtime dependencies. Their useful content is preserved under `skills/`.

## Daily Commands

```bash
env UV_CACHE_DIR=.uv-cache uv run --frozen --python 3.11 python -m seo_workbench status
env UV_CACHE_DIR=.uv-cache uv run --frozen --python 3.11 python -m seo_workbench status --json
env UV_CACHE_DIR=.uv-cache uv run --frozen --python 3.11 python -m seo_workbench next
env UV_CACHE_DIR=.uv-cache uv run --frozen --python 3.11 python -m seo_workbench next --json
env UV_CACHE_DIR=.uv-cache uv run --frozen --python 3.11 python -m seo_workbench step done
env UV_CACHE_DIR=.uv-cache uv run --frozen --python 3.11 python -m seo_workbench phase TECHNICAL_AUDIT
env UV_CACHE_DIR=.uv-cache uv run --frozen --python 3.11 python -m seo_workbench evidence
env UV_CACHE_DIR=.uv-cache uv run --frozen --python 3.11 python -m seo_workbench evidence --json
env UV_CACHE_DIR=.uv-cache uv run --frozen --python 3.11 python -m seo_workbench technology --json
env UV_CACHE_DIR=.uv-cache uv run --frozen --python 3.11 python -m seo_workbench evidence --technology --json
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
- Treat `projects/default/audits/raw/latest.json` as the stable current evidence pointer; timestamped `evidence-*.json` files are the immutable audit records.
- For Headless SEO work, prefer `python -m seo_workbench evidence --rendered --json` when Playwright is available so `headless_audit` includes raw/rendered diffs.
- Evidence collectors should return structured JSON with `collection_status`, `errors`, and `warnings` even when some fetches fail.
- Technology detection uses the pinned Go helper under `seo_workbench_tools/technology_detector/`; keep its JSON contract stable and update fixtures before changing the fingerprint provider version.
- Do not restore Claude slash commands or external repo dependencies unless the user explicitly asks.
- Each reform layer should be committed separately.

## Skill Modules

- `skills/keyword-deep-dive`
- `skills/content-brief`
- `skills/technical-audit`

Load only the referenced files needed for the current step.
