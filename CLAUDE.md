# SEO Workbench Claude Adapter

@AGENTS.md

This repo is agent-neutral: Claude uses the same local CLI and `skills/` modules as any other harness. The shared rules are imported above and are the single source of truth; do not restate them here.

Claude-only notes:

- Do not call external `superseo-skills/`, `seomachine/`, or `claude-seo/` unless the user asks to import or compare upstream.
- Do not run `git pull` inside third-party source directories during normal setup.
