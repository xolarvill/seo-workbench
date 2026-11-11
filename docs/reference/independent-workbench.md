# Independent SEO Workbench

This branch turns the project into a normal Python repo that any agent harness can use.

## Shape

```text
seo_workbench/          Python execution layer
seo_workbench_tools/    Existing evidence collectors, kept for compatibility
skills/                 Extracted SEO playbooks and rubrics
templates/              Reusable project and report templates
third_party/            License and attribution notes
projects/default/       Default runtime project directory
```

Every project has a `project.json` manifest. The retired workflow state file is migrated automatically and its action log is preserved under the project's `.runtime/` directory.

## Harness Contract

Agents should use the same local files and commands:

```bash
./seo projects --json
./seo evidence --rendered --json
```

Agents choose work from the current goal, project context, artifacts and evidence, using `AGENTS.md` and `skills/README.md` to discover methods. There is no stored phase, step, `next` scheduler, or current-stage gate. The UI Methods map offers capabilities without a stage gate.

Claude-specific slash commands and Codex-specific instructions become adapters, not the core product.

## Migration Rule

Reuse working code first. Move only when the new package owns the behavior and the old import path can stay as a wrapper.
