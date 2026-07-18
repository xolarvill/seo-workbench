# Content Types Overview

Use this reference to choose a page pattern after reviewing business context, current SERP evidence, and the user's task. These are editorial starting points, not ranking formulas.

## Decision boundaries

- There is no required word count for any content type. Estimate scope from the questions, evidence, media, comparisons, and decisions the page must support.
- A ranking competitor's length is an observation, not a target. Never use “top five average plus 10%.”
- Headings are optional patterns. Preserve a logical outline instead of forcing every section into every page.
- Schema.org vocabulary and Google rich-result eligibility are different things. Before implementation, use the `schema` skill and verify current Google documentation.
- FAQ rich results are restricted to eligible authoritative health and government sites. HowTo rich results are no longer available in Google Search. Do not prescribe either as a general SEO tactic.
- A page can rank without structured data. Markup must describe visible, truthful page facts.

## Decision table

| Content type | Dominant user task | Useful page pattern | Candidate semantic types |
|---|---|---|---|
| how-to | Complete a task | Outcome / prerequisites / ordered steps / failure handling | Article, VideoObject when applicable |
| definition | Understand a term | Direct definition / mechanics / examples / boundaries | Article, DefinedTerm |
| pillar page | Navigate a broad subject | Scope / topic map / concise sections / deep-dive links | Article, CollectionPage |
| FAQ page | Resolve recurring questions | Real questions grouped by task / concise sourced answers | WebPage; FAQPage only when eligible |
| statistics page | Find and reuse data | Method / key findings / tables / sources / update history | Article; Dataset only as semantic markup when accurate |
| news | Understand a current event | What happened / evidence / impact / update log | NewsArticle |
| thought leadership | Evaluate an argument | Thesis / evidence / counterargument / implications | Article, Person |
| glossary | Look up domain terms | A-Z navigation / definitions / examples / cross-links | DefinedTermSet, BreadcrumbList |
| comparison | Choose between options | Verdict by use case / consistent criteria / evidence / limitations | Article; Product or Review only when eligibility is met |
| list or roundup | Shortlist options | Selection method / summary / consistent evaluation / tradeoffs | ItemList, Article |
| alternatives | Replace an option | Reason for switching / criteria / comparison / migration cost | ItemList, Article |
| product review | Evaluate one product | Disclosure / test method / evidence / pros, limits, alternatives | Review, Product when truthful |
| buying guide | Learn selection criteria | Quick decision model / criteria / budget / mistakes | Article |
| product page | Evaluate or buy a product | Identity / specs / variants / proof / offer or inquiry action | Product; Offer only for real public offers |
| category page | Browse a product or service set | Scope / filters / item links / selection help | CollectionPage, ItemList |
| landing page | Complete one conversion task | Value / fit / evidence / objection handling / action | WebPage or Service |
| pricing page | Understand commercial terms | Tiers or quote model / inclusions / conditions / action | Product and Offer only when they represent real offers |
| integration page | Understand or implement an integration | Outcome / compatibility / setup / limits / support | SoftwareApplication, WebPage |
| service page | Evaluate a service | Scope / fit / process / deliverables / proof / contact | Service; LocalBusiness when applicable |
| location page | Find a real local offering | Local availability / service evidence / NAP / contact | LocalBusiness, Service |
| case study | Evaluate demonstrated results | Context / permission / method / timeline / results / limitations | Article, Organization |
| about page | Verify the organization | Ownership / people / experience / policies / contact | Organization, Person, ProfilePage |
| programmatic page | Resolve a repeated data-backed task | Unique data / conditional explanation / quality gate / related items | Depends on the actual page entity |

## Intent and page selection

Search intent is useful, but a page often serves more than one task:

- Informational pages explain or help complete a task.
- Commercial investigation pages help compare and reduce decision risk.
- Transactional pages let the user buy, inquire, register, download, or contact.
- Navigational and trust pages help locate or verify a business, person, product, or resource.

Read the actual result layout. If multiple formats rank, identify the distinct user tasks instead of copying the majority format mechanically. A product query may need a category page, product page, buying guide, or local result depending on the market.

## Scope estimation

Describe scope using deliverables rather than words:

- questions and decisions the page must resolve;
- first-party facts, tests, examples, or expert input required;
- tables, images, video, calculators, downloads, or interactive tools;
- legal, medical, financial, safety, or product claims requiring review;
- related pages needed to avoid duplication or orphaning;
- freshness and maintenance burden.

Stop when the page completes its task accurately. Add depth only when it improves a decision, explains evidence, covers an important edge case, or removes ambiguity.

## YMYL and high-trust topics

For content that can affect health, financial stability, legal safety, physical safety, or major purchases:

- identify the responsible author or reviewer;
- cite current primary sources;
- explain methods, conflicts, dates, and limitations;
- avoid unsupported guarantees;
- obtain appropriate subject-matter and legal review.

E-E-A-T concepts help editorial review, but an internal E-E-A-T score is not a Google score or a ranking-factor measurement.

## When to load a full template

Load one `content-types/<type>.md` file when its process or quality gates help. Ignore any fixed word count, keyword density, FAQ/HowTo rich-result promise, or mandatory heading that conflicts with this reference. For structured data, the `schema` skill always wins.

Related methodology files:

- `intent-matching.md`: intent and SERP observations
- `serp-driven-writing.md`: turning competitive evidence into editorial decisions
- `information-gain-writing.md`: finding defensible first-party value
- `fact-checking.md`: verifying claims and sources
- `structured-data-snippets.md`: current markup boundaries
