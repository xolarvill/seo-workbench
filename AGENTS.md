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

The external directories `superseo-skills/`, `seomachine/`, and `claude-seo/` are optional source material. Do not depend on them at runtime unless the user explicitly asks to import or compare upstream content.

## Daily Commands

```bash
env UV_CACHE_DIR=.uv-cache uv run --frozen --python 3.11 python -m seo_workbench status
env UV_CACHE_DIR=.uv-cache uv run --frozen --python 3.11 python -m seo_workbench next
env UV_CACHE_DIR=.uv-cache uv run --frozen --python 3.11 python -m seo_workbench step done
env UV_CACHE_DIR=.uv-cache uv run --frozen --python 3.11 python -m seo_workbench phase TECHNICAL_AUDIT
env UV_CACHE_DIR=.uv-cache uv run --frozen --python 3.11 python -m seo_workbench evidence
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
- Keep Claude slash commands as legacy adapters, not the core workflow.
- Do not run `git pull` inside external packs as part of normal setup.
- Each reform layer should be committed separately.

## Skill Modules

- `skills/keyword-deep-dive`
- `skills/content-brief`
- `skills/technical-audit`

Load only the referenced files needed for the current step.
