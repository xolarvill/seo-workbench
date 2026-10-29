---
name: schema
description: >
  Detect, validate, and generate Schema.org structured data. JSON-LD format
  preferred. Use when user says "schema", "structured data", "rich results",
  "JSON-LD", or "markup".
user-invokable: true
argument-hint: "[url]"
license: MIT
metadata:
  author: AgriciDaniel
  version: "1.9.6"
  category: seo
---

# Schema Markup Analysis & Generation

Use current project evidence and the [Workbench operations guide](../seo/references/workbench-operations.md) for fresh collection. Record coverage and unavailable inputs alongside findings.

## Implementation mode

For adding or repairing markup, establish the page type, existing markup, visible source facts and implementation stack. Apply the detection and validation rules below, then choose how the site's templates or components emit JSON-LD. Check the rendered result against the visible facts and record validation results.

Consult [implementation patterns](references/implementation/guide.md) for static, framework and CMS integration, multiple types and validation errors, and [JSON-LD examples](references/implementation/references/schema-examples.md) for a relevant example. The current project and this entrypoint govern eligibility; examples are not a separate eligibility policy.


## Detection

1. Scan page source for JSON-LD `<script type="application/ld+json">`
2. Check for Microdata (`itemscope`, `itemprop`)
3. Check for RDFa (`typeof`, `property`)
4. Always recommend JSON-LD as primary format (Google's stated preference)

## Validation

- Check required properties per schema type
- Validate against Google's supported rich result types
- Test for common errors:
  - Missing @context
  - Invalid @type
  - Wrong data types
  - Placeholder text
  - Relative URLs (should be absolute)
  - Invalid date formats
- Distinguish invalid vocabulary, retired Google appearances and unmet feature requirements; see the eligibility reference.

## Type selection and search eligibility

Use the [targeted search eligibility reference](references/search-eligibility.md) for the checked FAQPage, BreadcrumbList and Event policies and the distinction between vocabulary validity, eligibility and observed display. Its check date does not refresh every type in this directory.

Use the [type reference](../seo/references/schema-types.md) to identify semantic candidates, then verify the relevant current Google feature guide before promising a search appearance. A type is not invalid merely because Google retired its rich result.

- FAQ rich results stopped appearing for every site on 2026-05-07; government and health sites are no exception. Do not promise Google FAQ appearance or general AI-citation gains.
- Existing accurate FAQPage is not automatically an error or a removal task. Assess actual content and consumers.
- Breadcrumb appearance is a desktop feature; mobile non-display alone is not a schema defect.
- Google Event eligibility requires a public-bookable event at a physical location. A purely online event without a real-world component does not qualify, even when its semantic markup is valid.
- Google HowTo rich results are retired. Do not prescribe HowTo cards as a visibility tactic.

Select truthful entities and preserve stable identifiers when combining markup from templates, apps or components. For JavaScript-generated markup, inspect rendered output and indexed evidence when available rather than assuming discovery or processing from source presence alone.

## Generation

When generating schema for a page:
1. Identify page type from content analysis
2. Select appropriate schema type(s)
3. Generate valid JSON-LD with all required + recommended properties
4. Include only truthful, verifiable data. Clearly label any example placeholders and never publish them.
5. Validate output before presenting

## Common Schema Templates

### Organization
```json
{
  "@context": "https://schema.org",
  "@type": "Organization",
  "name": "[Company Name]",
  "url": "[Website URL]",
  "logo": "[Logo URL]",
  "contactPoint": {
    "@type": "ContactPoint",
    "telephone": "[Phone]",
    "contactType": "customer service"
  },
  "sameAs": [
    "[Facebook URL]",
    "[LinkedIn URL]",
    "[Twitter URL]"
  ]
}
```

### LocalBusiness
```json
{
  "@context": "https://schema.org",
  "@type": "LocalBusiness",
  "name": "[Business Name]",
  "address": {
    "@type": "PostalAddress",
    "streetAddress": "[Street]",
    "addressLocality": "[City]",
    "addressRegion": "[State]",
    "postalCode": "[ZIP]",
    "addressCountry": "US"
  },
  "telephone": "[Phone]",
  "openingHours": "Mo-Fr 09:00-17:00",
  "geo": {
    "@type": "GeoCoordinates",
    "latitude": "[Lat]",
    "longitude": "[Long]"
  }
}
```

### Article/BlogPosting
```json
{
  "@context": "https://schema.org",
  "@type": "Article",
  "headline": "[Title]",
  "author": {
    "@type": "Person",
    "name": "[Author Name]"
  },
  "datePublished": "[YYYY-MM-DD]",
  "dateModified": "[YYYY-MM-DD]",
  "image": "[Image URL]",
  "publisher": {
    "@type": "Organization",
    "name": "[Publisher]",
    "logo": {
      "@type": "ImageObject",
      "url": "[Logo URL]"
    }
  }
}
```

## Output

- `SCHEMA-REPORT.md`: detection and validation results
- `generated-schema.json`: verified implementation snippets, or clearly labeled examples with unresolved inputs

### Validation Results
| Schema | Type | Vocabulary / syntax | Visible facts | Google eligibility | Observed display | Issues |
|--------|------|---------------------|---------------|--------------------|------------------|--------|
| ... | ... | ... | ... | ... | not observed / observed | ... |

### Recommendations
- Missing schema opportunities
- Validation fixes needed
- Generated code for implementation

## Error Handling

| Scenario | Action |
|----------|--------|
| URL unreachable | Report connection error with status code. Suggest verifying URL and checking if the page requires authentication. |
| No schema markup found | Report that no JSON-LD, Microdata, or RDFa was detected. Recommend appropriate schema types based on page content analysis. |
| Invalid JSON-LD syntax | Parse and report specific syntax errors (missing brackets, trailing commas, unquoted keys). Provide corrected JSON-LD output. |
| Retired Google appearance or invalid type detected | Determine which applies. A retired appearance does not invalidate the vocabulary or authorize removal. Check current consumers and recommend changes supported by the facts. |
