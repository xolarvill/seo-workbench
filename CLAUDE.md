# SEO Workbench Claude Adapter

This repo is now agent-neutral. Claude should use the same local CLI and `skills/` modules as Codex or any other harness.

## Primary Commands

```bash
env UV_CACHE_DIR=.uv-cache uv run --frozen --python 3.11 python -m seo_workbench status
env UV_CACHE_DIR=.uv-cache uv run --frozen --python 3.11 python -m seo_workbench next
env UV_CACHE_DIR=.uv-cache uv run --frozen --python 3.11 python -m seo_workbench step done
env UV_CACHE_DIR=.uv-cache uv run --frozen --python 3.11 python -m seo_workbench evidence
```

Initialize:

```bash
env UV_CACHE_DIR=.uv-cache uv run --frozen --python 3.11 python -m seo_workbench \
  init shopify-headless --name "Project" --url "https://example.com" \
  --framework hydrogen --hosting oxygen --cms sanity
```

## Rules

- Read `AGENTS.md` for the authoritative workflow instructions.
- Use local `skills/` first; do not call external `superseo-skills/`, `seomachine/`, or `claude-seo/` unless the user asks to import or compare upstream.
- Treat `.claude/commands/` as legacy compatibility notes, not the core workflow.
- Do not run `git pull` inside third-party source directories during normal setup.
