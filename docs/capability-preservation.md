# Capability Preservation

Callable methods share skills/<capability>/SKILL.md. The [task index](../skills/README.md) lists 60 canonical entrypoints. Sources are recorded in [the provenance reference](skill-sources.md), and old paths in [the migration record](20261029-skill-layout-migration.md). The families below describe attribution, not separate skill namespaces.

## SuperSEO

Role: content strategy and quality review.

Workbench method entrypoints:

- `skills/keyword-deep-dive`
- `skills/topic-cluster-planning`
- `skills/content-brief`
- `skills/write-content`
- `skills/page-audit`
- `skills/eeat-audit`
- `skills/semantic-gap-analysis`
- `skills/linkbuilding`

Additional preserved modules:

- `skills/improve-content`
- `skills/featured-snippet-optimizer`
- `skills/expert-interview`

## SEO Machine

Role: content production pipeline.

Callable marketing, copy, CRO, measurement and commercial strategy methods live directly under skills/. Preserved specialist and workflow documents live under [third_party/skill-history/seomachine](../third_party/skill-history/seomachine):

- `commands/` - research, write, optimize, publish, repurpose, landing page, content calendar, and performance workflows.
- `agents/` - SEO optimizer, metadata creator, internal linker, keyword mapper, editor, CRO, headline, cluster, and performance specialists.
- `skills` - copywriting, content strategy, programmatic SEO, CRO, schema markup, social, ads, launch, referral, and related production modules.

Thirty-four portable methods are attached to their canonical skills as references, with their original sources recorded in [the adaptation map](skill-method-adaptations.json). The old scrub routine remains historical only. The originals are preserved for comparison, not installed slash commands or agent executors. Agents choose methods from `skills/README.md`; `seo_workbench` executes explicit operations. Stored phase mappings are compatibility records, not the scheduler.

## Claude SEO

Role: site-wide technical, performance, structured data, search visibility, and specialty SEO audits.

Workbench method entrypoints:

- `skills/technical-audit`
- `skills/schema`
- `skills/sitemap`
- `skills/images`
- `skills/drift`
- `skills/backlinks`

Specialty modules share the skills/ root, including:

- full site audit, content audit, page audit, cluster and competitor page analysis
- DataForSEO and Google integrations
- ecommerce, GEO, SXO, local, maps, hreflang, image generation
- SEO plan, programmatic SEO, flow framework, and shared SEO references

## Workbench Native

- `seo_workbench/` - harness-neutral operation CLI and legacy step references.
- `seo_workbench_tools/` - raw/rendered evidence collectors.
- `skills/headless-precheck` - local Headless precheck built on evidence JSON.

The canonical site-audit, page-audit, schema and programmatic-seo entrypoints own overlapping source methods. Original texts and licenses remain in their references; shared Claude SEO references are under [seo/references](../skills/seo/references). Project-context and reader-experience-review remain Workbench methods; site-audit and seo compose preserved methods with current execution rules.
