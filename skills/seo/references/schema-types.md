# Schema.org type selection and search eligibility

This is a semantic candidate list, not a claim that every type has a current Google rich result. The [shared eligibility reference](../../schema/references/search-eligibility.md) records targeted FAQPage, BreadcrumbList and Event policy checks on 2026-10-29. Other type versions, requirements and availability need their own current verification; this document does not declare a complete 2026 catalog refresh.

## Format and candidate types

Prefer JSON-LD for implementation. Validate Schema.org vocabulary and data types separately from the search provider's feature eligibility. Values must describe real page entities and agree with visible content; do not invent ratings, offers, dates or credentials.

| Type | Use Case | Key Properties |
|------|----------|----------------|
| Organization | Company info | name, url, logo, contactPoint, sameAs |
| LocalBusiness | Physical businesses | name, address, telephone, openingHours, geo, priceRange |
| SoftwareApplication | Desktop/mobile apps | name, operatingSystem, applicationCategory, offers, aggregateRating |
| WebApplication | Browser-based SaaS | name, applicationCategory, offers, browserRequirements, featureList |
| Product | Physical/digital products | name, image, description, sku, brand, offers, review |
| Offer | Pricing | price, priceCurrency, availability, url, validFrom |
| Service | Service businesses | name, provider, areaServed, description, offers |
| Article | Blog posts, news | headline, author, datePublished, dateModified, image, publisher |
| BlogPosting | Blog content | Same as Article + blog-specific context |
| NewsArticle | News content | Same as Article + news-specific context |
| Review | Individual reviews | reviewRating, author, itemReviewed, reviewBody |
| AggregateRating | Rating summaries | ratingValue, reviewCount, bestRating, worstRating |
| BreadcrumbList | Navigation | itemListElement with position, name, item; Google breadcrumb appearance is desktop-only |
| WebSite | Site-level | name, url; check current feature support separately |
| WebPage | Page-level | name, description, datePublished, dateModified |
| Person | Author/team | name, jobTitle, url, sameAs, image, worksFor |
| ContactPage | Contact pages | name, url |
| VideoObject | Video content | name, description, thumbnailUrl, uploadDate, duration, contentUrl |
| ImageObject | Image content | contentUrl, caption, creator, copyrightHolder |
| Event | Events | name, startDate, endDate, location, organizer, offers; Google requires public booking and a physical location |
| JobPosting | Job listings | title, description, datePosted, hiringOrganization, jobLocation |
| Course | Educational content | name, description, provider, hasCourseInstance |
| DiscussionForumPosting | Forum threads | headline, author, datePublished, text, url |
| ProductGroup | Variant products | name, productGroupID, variesBy, hasVariant |
| ProfilePage | Author/creator profiles | mainEntity (Person), name, url, description, sameAs |


## FAQPage and HowTo

- Google FAQ rich results stopped appearing for all sites on 2026-05-07; the earlier government/health exception no longer applies. Documentation updates recorded the announcement on May 8 and removal on June 15.
- Existing truthful FAQPage is informational rather than a critical error solely because rich results retired. Keep or remove it based on content, actual consumers and maintenance needs; do not claim automatic AI citation gains or losses.
- Do not add FAQPage for a Google FAQ appearance. An editorial FAQ remains valuable for actual reader questions without markup.
- Google HowTo rich results are retired. This is separate from Schema.org vocabulary validity and does not erase the usefulness of verified procedural content.

## Other historical type statuses

Older source lists described retirements or changes affecting SpecialAnnouncement, CourseInfo, EstimatedSalary, LearningVideo, ClaimReview, VehicleListing, practice problems, Dataset and book actions. Those labels mixed vocabulary, Google Search appearances and other consumers. Verify each affected consumer and official feature guide before recommending a replacement or removal. Do not treat the old “never recommend” list as current policy or infer that a separate service has been discontinued.

For Product, Offer, variants, certification, shipping or return policies, verify the current requirements and actual implementation surface before generating properties. Do not copy dated version numbers, release claims or required-property assertions from this historical source list without verification.

## Validation checklist

1. Identify the actual entity and visible content.
2. Parse JSON-LD; check context, type, data types, identifiers, URLs and date formats.
3. Remove placeholders and unsupported facts before deployment.
4. Check current Google eligibility for a supported appearance, including content policies and device restrictions.
5. Use the Schema.org validator for broader vocabulary and the Rich Results Test for supported Google features.
6. Report valid markup, eligibility, indexing observations and actual display separately. No markup guarantees a ranking, CTR or AI citation benefit.

## Official references

- [Google Search documentation updates](https://developers.google.com/search/updates)
- [Breadcrumb structured data](https://developers.google.com/search/docs/appearance/structured-data/breadcrumb)
- [Event structured data](https://developers.google.com/search/docs/appearance/structured-data/event?hl=en)
- [Google search gallery](https://developers.google.com/search/docs/appearance/structured-data/search-gallery)
- [Schema.org Validator](https://validator.schema.org/)
- [Google Rich Results Test](https://search.google.com/test/rich-results)
