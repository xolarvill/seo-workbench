# Local UI surface

The local UI is optional and local-only: it is an operator convenience over the same project-scoped CLI and project files, not a second backend. A headless session keeps using `./seo --project <id> ...` and reads the same evidence and Markdown files.

## Detection

An active UI writes `.runtime/ui/session.json`. Its `http://localhost:<port>` address opens in any browser without a browser session. The filesystem watcher surfaces new evidence and Markdown files automatically.

## Audit execution path

When the UI starts an audit it invokes the existing project-scoped CLI through a fixed action whitelist. Never add arbitrary command execution, shell strings, or remote binds to that path.

## Credentials

Credential management is limited to fixed local-only provider APIs. Secret values are write-only, never returned by any read path, stored below ignored `.runtime/` paths with private permissions, and never accepted through arbitrary filesystem paths or a generic environment editor.

## Markdown writes

Editor writes are limited to `context/`, `strategy/`, `content/`, `audits/`, and `reports/`, and use revision-based conflict detection so a concurrent agent edit is never overwritten silently.

## Pages workspace

- Pages actions are read-time projections of portfolio, content operations, technical issues, and SEO changes. Do not add a generic task database or duplicate domain status.
- Grouped technical actions are read-only and drill down by rule and page template; status, owner, and notes are updated on individual issue fingerprints.
- Pages may update existing local ledgers only. Never publish, redirect, recrawl, push notifications, or mutate the site from Pages; those actions stay in the existing workspaces and confirmation paths.

## Shared components

Status pills use `ui/src/components/StatusPill.tsx` (see `docs/UI状态Pill规范.md`); help tooltips use `ui/src/components/HelpTooltip.tsx` (see `docs/UI帮助气泡规范.md`). Page-local tone maps, pill CSS, and ad-hoc tooltip implementations are not accepted.
