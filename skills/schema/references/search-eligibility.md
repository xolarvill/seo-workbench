# Search eligibility: targeted policy checks

This reference records the policies checked against official Google documentation on 2026-10-29. It is not a complete refresh of Schema.org or every Google search feature. Verify the relevant current documentation before implementing other types or requirements.

## Keep three questions separate

1. **Vocabulary and validity:** Does Schema.org define this type and are its properties and JSON-LD valid?
2. **Feature eligibility:** Does the search provider currently support a relevant feature, and does this page meet its content and policy requirements?
3. **Observed display:** Was that appearance actually observed for a particular query, date, market and device?

Valid markup does not establish eligibility; eligibility does not guarantee display. A retired Google appearance does not by itself invalidate the underlying Schema.org type.

## FAQPage

Google FAQ rich results stopped appearing on **2026-05-07**, for all sites. The May 8 update announced that change, and Google removed the feature documentation on June 15. The earlier government/health restriction is historical and no longer describes an available feature.

- Do not propose new FAQPage markup for a Google FAQ rich result.
- Existing truthful FAQPage is not a critical error solely because the appearance retired. Inspect accuracy, maintenance cost and actual consumers before recommending removal; do not remove it automatically.
- Real FAQ content can still answer reader questions and be indexed as ordinary content.
- No general AI citation uplift from FAQPage is established here. Do not justify markup with vendor citation percentages or claim that removing it loses such a benefit.
- Do not convert an editorial FAQ into QAPage merely to seek another appearance; that is a different content model requiring its own current eligibility check.

Source: [Google Search documentation updates, May 8 and June 15, 2026](https://developers.google.com/search/updates).

## BreadcrumbList

Google's breadcrumb feature is available on **desktop**. Do not promise a mobile breadcrumb appearance or classify mobile non-display as a markup failure. Valid navigation markup and visible mobile site navigation can remain useful independently of Google's display.

Source: [Google breadcrumb structured data](https://developers.google.com/search/docs/appearance/structured-data/breadcrumb).

## Event

Google's Event search experience requires events bookable by the general public and held at a physical location. A purely online event with no real-world component does not qualify. Do not invent a venue or change truthful event facts to meet eligibility.

An online event can still be represented truthfully in Schema.org where that vocabulary fits; vocabulary validity is separate from Google Event eligibility. A hybrid event needs a genuine physical component and must meet the remaining current rules; a physical address alone does not guarantee eligibility or display.

Source: [Google Event structured data](https://developers.google.com/search/docs/appearance/structured-data/event?hl=en).

## HowTo and other historical recommendations

Google HowTo rich results have been removed. Do not promise HowTo cards or add markup solely to pursue that retired appearance. Verified instructions and, where appropriate, truthful semantic markup remain separate choices.

For other types, use the current [Google structured data gallery](https://developers.google.com/search/docs/appearance/structured-data/search-gallery) and the relevant feature guide. Do not treat an inherited active/deprecated list as a complete current eligibility registry.

## Validation and reporting

Use the [Schema.org validator](https://validator.schema.org/) for vocabulary checks and the [Rich Results Test](https://search.google.com/test/rich-results) for supported Google features. Lack of a retired feature's test or reporting support is not evidence of invalid Schema.org vocabulary.

Report syntax, visible-fact consistency, provider eligibility and actual display separately. Keep draft recommendations distinct from implemented markup, indexed observations and measured results.
