---
name: site-audit
description: Use when diagnosing SEO across a website or multiple page templates, reviewing site-wide evidence, or deciding which specialist checks a full-site audit needs. Use page-audit for a single URL and technical-audit for a technical-only investigation.
---

# Site Audit

Coordinate a site-wide diagnosis from the current project's context, page inventory and available evidence. Read the repository and project AGENTS, then choose the relevant methods from the shared skill index.

## Establish scope and evidence

Identify the project, canonical host, markets, page types, business objective and requested review depth. Locate existing context, decisions, page inventories and current audit pointers before requesting inputs or collecting more data.

Record observation dates, source coverage and collection status. Reuse applicable evidence. A representative sample does not establish full-site coverage, and an unobserved page is not evidence of absence or zero traffic.

## Build the diagnosis

1. Reconcile the supplied inventory with eligible crawl, sitemap, GSC and content observations; keep their coverage distinguishable.
2. Use [technical-audit](../technical-audit/SKILL.md) for technical findings and [sitemap](../sitemap/SKILL.md) for coverage. Use [headless-precheck](../headless-precheck/SKILL.md) where raw/rendered parity matters.
3. Use [page-audit](../page-audit/SKILL.md) for representative pages and [eeat-audit](../eeat-audit/SKILL.md) where credibility or content evidence is the question.
4. Add schema, images, ecommerce, hreflang, local, backlinks or other specialist methods only when the site and task warrant them. The shared index supplies their canonical paths.
5. Prioritize supported findings by affected pages, user/business consequence and evidence quality. Keep technical defects, content opportunities and measurement gaps distinguishable; do not substitute a blended health score for their evidence.

Performance verdicts follow CrUX field evidence. Lighthouse and crawler timings support diagnosis. Statistical comparisons follow the project's comparable-window and measurement-regime rules.

## Workbench operations and deliverable

For an evidence review or planning-only request, read existing artifacts. When collection is in scope, choose explicit project-scoped operations using `./seo --help` and command-specific help. This method does not install an upstream executor or assign a default crawl size.

Keep the chosen scope, methods, evidence pointers, findings and uncovered areas in the existing project deliverable, following the project's report conventions. A proposal remains a proposal until the corresponding authorized operation is completed and verified.

## Supporting methods

- [SEO Machine audit framework](references/seo-machine-audit.md): consult for business context, crawl/indexation, content and authority questions relevant to this site.
- [Claude SEO audit coverage](references/claude-seo-audit.md): consult for page-type and specialty coverage. Its original scripts, crawl settings and orchestration are preserved source material.

Source mappings and licenses are recorded in [the provenance reference](../../docs/skill-sources.md).
