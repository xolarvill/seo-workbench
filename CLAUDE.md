# SEO Workbench Claude Adapter

This repo is agent-neutral. Claude uses the same local CLI and `skills/` modules as Codex or any other harness.

## Start

- Read `AGENTS.md` for the authoritative instructions: task routing, guardrails, and reporting contracts.
- Work from the user's current goal, project artifacts, and evidence; stored phases never schedule the agent.
- Read the useful local skill bodies from `skills/README.md` without waiting to be told, and combine or shorten methods to fit the task. Prefer local `skills/` over third-party packs.
- Do not use legacy slash commands or the retired `next` command; the CLI executes explicit operations.

## Commands

```bash
./seo status
./seo evidence
```

Initialization, the full command catalog, and the uv fallback live in `README.md`.
