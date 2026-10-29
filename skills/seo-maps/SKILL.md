---
name: seo-maps
description: >
  Maps intelligence for local SEO — geo-grid rank tracking, GBP profile
  auditing via API, review intelligence across Google/Tripadvisor/Trustpilot,
  cross-platform NAP verification (Google/Bing/Apple/OSM), competitor
  radius mapping, and LocalBusiness schema generation from API data.
  Three-tier capability: free (Overpass + Geoapify), DataForSEO (full
  intelligence), DataForSEO + Google (maximum coverage). Use when user
  says "maps", "geo-grid", "rank tracking", "GBP audit", "review
  velocity", "competitor radius", "maps analysis", "local rank
  tracking", "Share of Local Voice", or "SoLV".
user-invokable: true
argument-hint: "[command] [url|keyword|location]"
license: MIT
compatibility: "Supplied listing data or verified available provider integrations"
metadata:
  author: AgriciDaniel
  version: "1.9.6"
  category: seo
---

# Maps Intelligence (March 2026)

Maps platform analysis for local businesses. Works with external APIs to assess
how a business appears on Google Maps, Bing Places, Apple Maps, and OpenStreetMap.

**Boundary with seo-local:** This skill analyzes the business on maps PLATFORMS
(via APIs). seo-local analyzes local SEO signals on the WEBSITE (via HTML fetch).
Use [seo-local](../seo-local/SKILL.md) for website-level checks alongside this maps analysis.

---

## Available analysis modes

Choose the mode from the user's question and the evidence available:

| Mode | Required inputs |
|------|-----------------|
| Maps presence | Business identity, location and observed listing URLs or exports |
| Geo-grid rank scan | Keyword, center coordinates, radius and comparable point-level rank observations |
| Review intelligence | Dated reviews, ratings, response fields and collection coverage |
| Competitor radius mapping | Geocoded business records and a defined search radius |
| Cross-platform NAP | Observed name, address and phone for each platform |
| Schema generation | Verified visible business facts and the implementation page |
| GBP completeness | Profile export or authorized profile observations |

## Evidence availability

Workbench does not install the source project's Maps executors. Start from supplied
exports, existing evidence and available connected tools. Discover and verify the
specific provider operation, account scope and cost before requesting fresh data.
Use the [Workbench operations guide](../seo/references/workbench-operations.md)
for project evidence and current local command discovery.

The tier labels below describe evidence options:

- **Tier 0:** Supplied records and public observations; website-only evidence leaves
  unobserved GBP fields unknown. Public API access still requires an available
  client and any provider prerequisites.
- **Tier 1:** Verified available DataForSEO operations for the requested listing,
  review or point-level rank fields. Availability of one operation does not imply
  the others are available.
- **Tier 2:** Verified available Google Maps Platform operations that add relevant
  fields. Apply current provider storage and usage terms to those fields.

Read [public API query patterns](../seo/references/maps-free-apis.md) or
[provider endpoint references](../seo/references/maps-api-endpoints.md) only when
that source is relevant. Record which source and fields were actually observed.

---

## Geo-Grid Rank Tracking (Tier 1+)

Simulates Google Maps searches from multiple GPS coordinates to show ranking
variation across a geographic area. Requires point-level observations from a verified provider or a supplied comparable export.

**Load:** [maps-geo-grid](../seo/references/maps-geo-grid.md) for algorithm, SoLV formula, heatmap format.
**Load:** [maps-api-endpoints](../seo/references/maps-api-endpoints.md) for Maps SERP endpoint details.

### Workflow

1. Geocode business address to get center lat/lng
2. Generate grid points (default: 7x7, 5km radius) using Haversine offset formula
3. Verify the operation and estimated total cost; obtain any spending authorization not already supplied by the user
4. Collect the authorized point observations using the verified operation and its supported coordinate field, or validate the supplied export
5. Find target business rank at each point
6. Calculate SoLV: `(top_3_count / total_points) * 100`
7. Render ASCII heatmap in output

### Scan scope and cost

Before a paid scan, state the keyword count, grid size, locations and estimated
total cost using current provider evidence. Reuse any existing spending
authorization that covers this scope. Record actual charges returned by the
provider separately from estimates.

---

## GBP Profile Audit (Tier 1 preferred, Tier 0 manual)

Audits the 25 fields that affect Google Business Profile quality and ranking.

**Load:** [maps-gbp-checklist](../seo/references/maps-gbp-checklist.md) for full checklist and scoring.

### Tier 1 Workflow

1. Fetch business profile via DataForSEO My Business Info API (keyword or CID)
2. Map API response fields to 25-field checklist
3. Score each field: Present + Optimized = 2pts, Present = 1pt, Missing = 0pts
4. Apply industry-specific weight multipliers
5. Normalize to 0-100 scale

### Tier 0 Workflow

1. Inspect eligible collected website evidence or supplied page content
2. Extract any visible GBP signals (Maps embed, place references, review widgets)
3. Apply static checklist based on detectable signals
4. Mark undetectable fields as "Unknown" and name the profile input needed to assess them

---

## Review Intelligence (Tier 1+)

Cross-platform review analysis: velocity, sentiment, rating distribution, fake detection.

**Reference:** [local-seo-signals](../seo/references/local-seo-signals.md) for benchmarks (shared with seo-local).

### Workflow

1. Fetch Google reviews via DataForSEO Reviews API (sort by newest)
2. Calculate review velocity: reviews per month over last 6 months
3. Check 18-day rule (Sterling Sky): any 3-week gap = ranking risk
4. Analyze rating distribution: healthy = bell curve skewed to 5-star
5. Calculate owner response rate: responses / total reviews
6. Fetch Tripadvisor and Trustpilot reviews (if available)
7. Cross-platform comparison table

### Fake Review Detection Signals

Flag reviews matching 2+ of these patterns:
- Uniform timing (multiple reviews same day/hour)
- Reviewer accounts with limited history or single review
- Geographic inconsistencies (reviewer location vs business location)
- Exclusively 5-star velocity spike (vs historical baseline)
- Identical or near-identical text across reviews
- Sudden volume spike without corresponding marketing activity

---

## Competitor Radius Mapping (Tier 0+)

Identify and analyze competitors within a defined radius.

### Tier 0 (Overpass API)

**Load:** [maps-free-apis](../seo/references/maps-free-apis.md) for query templates.

1. Geocode business address
2. Query Overpass API for businesses with same OSM tag within radius
3. Parse results: name, address, phone, website, distance from center
4. Sort by distance, present as competitor landscape table

### Tier 1 (DataForSEO)

1. Use Maps SERP API with business keyword + location
2. Extract top 20 competitors with full profile data
3. Compare: rating, review count, categories, photos, attributes
4. Calculate competitive density score: competitors per km^2

---

## Cross-Platform NAP Verification (Tier 0+)

Check business listing consistency across Google, Bing Places, Apple, and OSM.

### Workflow

1. Search for business name on each platform:
   - Google: infer from GBP data or Maps SERP result
   - Bing: inspect an observed public listing or supplied Bing Places record
   - Apple: manual check (no public API -- recommend Apple Business Connect at businessconnect.apple.com)
   - OSM: Overpass or Nominatim search
2. Extract NAP (Name, Address, Phone) from each source
3. Compare for consistency: exact match, partial match, missing, or conflicting
4. Flag discrepancies as Critical (name mismatch), High (address mismatch), Medium (phone mismatch)
5. Recommend claiming unclaimed profiles

---

## Schema Generation (Tier 0+)

Generate LocalBusiness JSON-LD markup from collected data.

**Reference:** [local-schema-types](../seo/references/local-schema-types.md) for industry subtypes (shared with seo-local).

### Workflow

1. Determine most specific schema subtype for the industry
2. Populate required properties: `@type`, `name`, `address`, `image`
3. Add recommended properties: `telephone`, `url`, `geo`, `openingHoursSpecification`, `priceRange`
4. Add strategic properties for multi-location: `branchOf`, `areaServed`, `sameAs`
5. Add `aggregateRating` if review data available
6. Output valid JSON-LD block ready for implementation

**Do NOT generate self-serving review markup** -- Google ignores LocalBusiness review markup from the business itself. Only mark up third-party reviews visible on the page.

---

## Reference Files

Load on-demand as needed (do NOT load all at startup):
- [maps-api-endpoints](../seo/references/maps-api-endpoints.md): DataForSEO endpoint details, params, costs
- [maps-free-apis](../seo/references/maps-free-apis.md): Overpass, Geoapify, Nominatim query templates
- [maps-geo-grid](../seo/references/maps-geo-grid.md): Grid algorithm, SoLV formula, heatmap rendering
- [maps-gbp-checklist](../seo/references/maps-gbp-checklist.md): 25-field GBP audit with industry weights
- [local-seo-signals](../seo/references/local-seo-signals.md): Ranking factors, review benchmarks (shared)
- [local-schema-types](../seo/references/local-schema-types.md): LocalBusiness subtypes by industry (shared)

---

## Output

Generate `MAPS-ANALYSIS-{domain}.md` with:

1. **Maps Health Score: XX/100** with dimension breakdown table
2. **Capability tier detected** (Tier 0 or Tier 1) with explanation of what's available
3. **Geo-grid heatmap** (Tier 1): ASCII grid with SoLV percentage and average rank
4. **GBP profile audit**: field-by-field scoring with industry-specific weights
5. **Review intelligence**: velocity chart, rating distribution, response rate, cross-platform comparison
6. **Competitor landscape**: count in radius, top 5 by rating/reviews, competitive density
7. **Cross-platform presence**: Google/Bing/Apple/OSM listing status
8. **Schema recommendation**: generated LocalBusiness JSON-LD (if missing or incomplete)
9. **Top 10 prioritized actions** (Critical > High > Medium > Low)
10. **Cost report**: DataForSEO credits consumed during analysis (Tier 1 only)
11. **Limitations disclaimer**: what could not be assessed at current tier

---

## Related local methods

- Website on-page local signals: use [seo-local](../seo-local/SKILL.md)
- Full AI search visibility: consult [seo-geo](../seo-geo/SKILL.md)
- Schema validation and fixes: use [schema](../schema/SKILL.md)
- Live SERP and keyword data: consult [seo-dataforseo](../seo-dataforseo/SKILL.md) for supported provider inputs

---

## Error Handling

| Scenario | Action |
|----------|--------|
| Requested provider operation unavailable | Continue with supplied records and supported public observations. Identify the specific fields still needed for the requested analysis. |
| Business not found in Maps SERP | Try My Business Info with keyword. If still not found, report "Business not found in Google Maps for this location." |
| Geocoding fails (Nominatim) | Ask user to provide coordinates or a more specific address. |
| API rate limit hit | Report the limit. Suggest waiting or using standard (queued) method instead of live. |
| No reviews returned | Record the source and query coverage. Report zero reviews only when a successful complete response establishes that count; otherwise mark review evidence unavailable. |
| Multi-location detected | Ask user which location to analyze, or offer batch mode with per-location cost estimate. |
