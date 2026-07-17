# SEO Workbench Claude Adapter

This repo is now agent-neutral. Claude should use the same local CLI and `skills/` modules as Codex or any other harness.

## Primary Commands

```bash
./seo status
./seo next
./seo step done
./seo evidence
```

Initialize:

```bash
./seo \
  init shopify-headless --name "Project" --url "https://example.com" \
  --framework hydrogen --hosting oxygen --cms sanity
```

## Rules

- Read `AGENTS.md` for the authoritative workflow instructions.
- Use local `skills/` first; do not call external `superseo-skills/`, `seomachine/`, or `claude-seo/` unless the user asks to import or compare upstream.
- Do not use legacy slash-command files; the local CLI is the workflow interface.
- Do not run `git pull` inside third-party source directories during normal setup.
