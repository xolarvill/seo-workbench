# Capability Preservation

The independent workbench keeps the three original SEO repos as distinct capability families.

## SuperSEO

Role: content strategy and quality review.

Primary workflow modules:

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

Preserved as local pipeline assets under `skills/seo-machine-pipeline/`:

- `commands/` - research, write, optimize, publish, repurpose, landing page, content calendar, and performance workflows.
- `agents/` - SEO optimizer, metadata creator, internal linker, keyword mapper, editor, CRO, headline, cluster, and performance specialists.
- `skills/` - copywriting, content strategy, programmatic SEO, CRO, schema markup, social, ads, launch, referral, and related production modules.

These assets are not the default state-machine executor. The default executor is `seo_workbench` plus local `skills/`.

## Claude SEO

Role: site-wide technical, performance, structured data, search visibility, and specialty SEO audits.

Primary workflow modules:

- `skills/technical-audit`
- `skills/schema`
- `skills/sitemap`
- `skills/images`
- `skills/drift`
- `skills/backlinks`

Additional preserved modules live under `skills/claude-seo-extra/`, including:

- full site audit, content audit, page audit, cluster and competitor page analysis
- DataForSEO and Google integrations
- ecommerce, GEO, SXO, local, maps, hreflang, image generation
- SEO plan, programmatic SEO, flow framework, and shared SEO references

## Workbench Native

- `seo_workbench/` - harness-neutral CLI and workflow contract.
- `seo_workbench_tools/` - raw/rendered evidence collectors.
- `skills/headless-precheck` - local Headless precheck built on evidence JSON.
