# Structured Data and Extractable Content

Structured data describes page entities and can make a page eligible for supported search appearances. It does not guarantee a rich result, ranking improvement, click-through lift, featured snippet, or AI citation.

## Source of truth

Before recommending or generating markup:

1. Identify the visible entity and page purpose.
2. Use the repository's `schema` skill for current type status and validation.
3. Verify Google's current Search Gallery documentation for rich-result eligibility.
4. Use Schema.org only for properties that accurately describe visible facts.
5. Validate syntax and required properties, then monitor GSC enhancement reports when available.

Do not reuse old vendor lift percentages or treat a patent, correlation, or case study as a guaranteed effect.

## Current boundaries

- `FAQPage` rich results are restricted to eligible authoritative government and health sites. A normal FAQ page can still be useful without FAQ rich results.
- Google removed HowTo rich results. Do not add `HowTo` solely for Google visibility.
- Deprecated or retired rich-result types must not be recommended as active search features.
- Product, Offer, Review, AggregateRating, Article, LocalBusiness, Event, JobPosting, VideoObject, and other types have specific eligibility and policy requirements.
- Product price, availability, rating, review, author, and date values must match visible, current facts.
- Customer-specific or login-only price and availability must not leak into public JSON-LD.

## Content formatting is separate from schema

Clear content can help users and extraction systems even when no rich-result type applies:

- answer the main question near the point where the user asks it;
- use ordered steps for genuine sequences;
- use tables for consistent comparisons;
- define units, dates, entities, and assumptions;
- use descriptive headings and stable anchor links;
- cite primary sources beside material claims;
- explain limitations and update history.

Do not force every answer into 40 to 60 words. Do not add a fixed number of PAA questions or FAQs. Choose the format that preserves accuracy and context.

## Candidate types by real page entity

| Page entity | Candidate markup | Key checks |
|---|---|---|
| Organization | Organization | legal/display name, canonical URL, logo, real profiles |
| Local location | LocalBusiness subtype | address, phone, hours, service area, page visibility |
| Editorial article | Article, BlogPosting, NewsArticle | author, publisher, dates, headline, image |
| Public product | Product, ProductGroup | identity, variants, brand, identifiers, visible details |
| Public offer | Offer | price, currency, availability, URL, transaction reality |
| First-party or permitted review | Review, AggregateRating | visible review text, source, count, policy compliance |
| Software product | SoftwareApplication | operating system, category, offer or pricing facts |
| Video | VideoObject | watch page, thumbnail, upload date, duration, access |
| Event | Event | real dates, location, status, offer, cancellation updates |
| Job | JobPosting | genuine opening, location, employer, valid through date |
| Navigation trail | BreadcrumbList | matches visible or logical site hierarchy |

Use the most specific truthful type. More markup is not automatically better.

## Minimal Article example

```json
{
  "@context": "https://schema.org",
  "@type": "Article",
  "headline": "Visible page headline",
  "mainEntityOfPage": "https://example.com/article/",
  "datePublished": "2026-07-01",
  "dateModified": "2026-07-15",
  "author": {
    "@type": "Person",
    "name": "Verified author name",
    "url": "https://example.com/authors/name/"
  },
  "publisher": {
    "@type": "Organization",
    "name": "Publisher name",
    "url": "https://example.com/"
  },
  "image": "https://example.com/images/article.jpg"
}
```

Every value above must be replaced with facts from the page or project. Never publish placeholders.

## Validation workflow

- Parse the JSON-LD and resolve syntax errors.
- Check that URLs are absolute, canonical, fetchable, and appropriate.
- Compare markup with rendered visible content.
- Run the Google Rich Results Test for supported Google features.
- Run Schema Markup Validator for broader Schema.org vocabulary.
- Recheck after theme, CMS, app, or template changes.
- Use GSC to monitor detected items and errors, remembering that detection does not guarantee display.

## Common failures

- Marking up hidden, fabricated, stale, or customer-specific facts.
- Adding Product or Review markup to a comparison article that does not represent a genuine product or review entity.
- Duplicating incompatible JSON-LD from a theme, app, and custom template.
- Using FAQ or HowTo markup because an old template promises a rich result.
- Assuming JavaScript-injected markup is equivalent without checking the rendered and indexed versions.
- Reporting schema presence as proof that Google trusts, ranks, or cites the page.
