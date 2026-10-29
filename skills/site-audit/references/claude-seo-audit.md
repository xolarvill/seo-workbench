# Full website audit coverage

Adapted source method for [site-audit](../SKILL.md). Use this coverage map when the request spans multiple SEO disciplines. Select current collection operations through [Workbench operations](../../seo/references/workbench-operations.md).

## Establish the scope

Read project context, current evidence and the user's target before collecting. Identify business type from observed product, location, editorial or service signals. Choose representative templates and the missing evidence that would change a decision. The project evidence command defaults to five representative same-host routes; inspect collector help before choosing a wider scope. Use `--crawl-limit 0` for a strict single-URL evidence run.

Reuse existing raw/rendered evidence and technical inventories where current enough. Preserve immutable records and stable latest pointers. If deeper technical coverage is needed, use the existing `tech-audit` interface and its persistent session/continuation behavior. Collector configuration, crawl pacing, retries, signing and robots handling belong to that implementation.

## Audit lenses

| Lens | Questions and evidence |
|---|---|
| Technical | Eligible status/HTML, robots, canonicals, redirects, indexability and link/sitemap coverage |
| Content | Search intent, factual support, authorship, unique value, duplication and readable organization |
| On-page | Titles, descriptions, headings and internal links on observed pages |
| Structured data | Detected types, rendered availability, validation and suitable current opportunities |
| Performance | CrUX LCP/INP/CLS verdicts; Lighthouse resource/script diagnostics separately |
| Visual and experience | Observed desktop/mobile layout, above-fold clarity, page-type fit and conversion path |
| Images | Actual alt text, image role, dimensions, transfer cost and format evidence |
| AI search | Crawl access, attributable claims, useful structure and actual observed citation evidence |
| Local/maps | Relevant location/service intent, GBP/citation/review evidence, geo-grid data if supplied |
| Links/clusters/ecommerce | Provider-scoped backlink evidence, topic ownership or product/category specifics when relevant |

Read the matching canonical skill before specialist work. Use available API evidence when it fills a concrete gap; API credentials do not require a full extra audit. Specialist coverage can be completed inline. Agent names from the source pack do not register executable agents.

## Synthesis and deliverable

Combine related observations into an action plan with affected URLs/templates, evidence, expected benefit, priority and effort. Use current rule severity and evidence eligibility rather than hardcoded numerical category weights. A partial source cannot establish absence or verify an old issue as fixed.

A useful report covers the business context, key findings, technical/content/on-page/schema/performance/image/experience findings that were actually investigated, and the next decisions. Keep unavailable sections brief and explicit. Store evidence pointers and collection scope so a later session can resume. The project's standard Markdown report path and existing presentation workflow supply the artifact contract.

## Failed or partial collection

For unreachable URLs, rate limits, robots restrictions or runtime failures, preserve structured errors and the successful observations. Continue only within the collector's bounded retry/session policy. Rendering failure does not establish missing page elements. A CrUX `no_data` result leaves field performance unobserved; lab diagnostics remain labeled separately.
