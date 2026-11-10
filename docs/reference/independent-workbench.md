# Independent SEO Workbench

This branch turns the project into a normal Python repo that any agent harness can use.

## Shape

```text
seo_workbench/          Python execution layer
seo_workbench_tools/    Existing evidence collectors, kept for compatibility
skills/                 Extracted SEO playbooks and rubrics
workflows/              Legacy step reference mappings
templates/              Reusable state and report templates
third_party/            License and attribution notes
projects/default/       Default runtime project directory
```

Local modules now cover every non-INIT step in `templates/state.json`.

## Harness Contract

Agents should use the same local files and commands:

```bash
./seo status
./seo evidence --rendered --json
```

Agents choose work from the current goal, project context, artifacts and evidence, using `AGENTS.md` and `skills/README.md` to discover methods. The `next` command is retired. Stored phases and explicit `phase`/`step` maintenance remain for compatibility; they do not constrain skill selection or prove professional completion. The UI Methods map offers capabilities without a current-stage gate.

Claude-specific slash commands and Codex-specific instructions become adapters, not the core product.

## Migration Rule

Reuse working code first. Move only when the new package owns the behavior and the old import path can stay as a wrapper.
