# Independent SEO Workbench

This branch turns the project into a normal Python repo that any agent harness can use.

## Shape

```text
seo_workbench/          Python execution layer
seo_workbench_tools/    Existing evidence collectors, kept for compatibility
skills/                 Extracted SEO playbooks and rubrics
workflows/              State-machine definitions
templates/              Reusable state and report templates
third_party/            License and attribution notes
```

## Harness Contract

Agents should use the same local files and commands:

```bash
uv run seo-workbench status
uv run seo-workbench next
python -m seo_workbench_tools.workflow_evidence
```

Claude-specific slash commands and Codex-specific instructions become adapters, not the core product.

## Migration Rule

Reuse working code first. Move only when the new package owns the behavior and the old import path can stay as a wrapper.
