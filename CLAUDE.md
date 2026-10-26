# SEO Workbench Claude Adapter

This repo is now agent-neutral. Claude should use the same local CLI and `skills/` modules as Codex or any other harness.

## Primary Commands

```bash
./seo status
./seo evidence
```

Initialize:

```bash
./seo \
  init shopify-headless --name "Project" --url "https://example.com" \
  --framework hydrogen --hosting oxygen --cms sanity
```

## Rules

- Read `AGENTS.md` for the authoritative instructions. Choose work from the current goal, project artifacts, and evidence; stored phases do not schedule the agent.
- Consult `skills/README.md` and read useful local skill bodies without waiting for the user to name them; combine or shorten methods to fit the task.
- Use local `skills/` first; do not call external `superseo-skills/`, `seomachine/`, or `claude-seo/` unless the user asks to import or compare upstream.
- Do not use legacy slash-command files; the local CLI executes explicit operations. The retired `next` command is not an agent entrypoint.
- Do not run `git pull` inside third-party source directories during normal setup.
