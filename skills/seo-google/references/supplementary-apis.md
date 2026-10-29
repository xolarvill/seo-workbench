# Supplementary Google APIs for SEO

Source capability reference. These APIs are not installed Workbench commands. Use supplied output or discover a verified connector; inspect its current schema, account access, quotas and pricing before a requested call. Endpoint examples below describe the preserved source method.

## Knowledge Graph Search API

Verify brand/entity presence in Google's Knowledge Graph.

**Endpoint:** `GET https://kgsearch.googleapis.com/v1/entities:search`

| Param | Description |
|-------|-------------|
| `query` | Search query |
| `ids` | Specific entity IDs (e.g., `/m/0d6lp`) |
| `languages` | Language codes (e.g., `en`) |
| `types` | Schema.org types to filter (e.g., `Organization`, `Person`) |
| `limit` | Max results (1-500) |
| `key` | API key (required) |

**Response:**
```json
{
  "itemListElement": [{
    "result": {
      "@id": "kg:/m/0d6lp",
      "name": "Google",
      "@type": ["Organization", "Corporation"],
      "description": "Technology company",
      "detailedDescription": {
        "articleBody": "Google LLC is an American...",
        "url": "https://en.wikipedia.org/wiki/Google"
      },
      "image": { "url": "..." },
      "url": "https://www.google.com"
    },
    "resultScore": 4892.5
  }]
}
```

**Use for SEO:** Inspect returned entity matches and disambiguation. A Knowledge Graph result alone does not verify that a search result displays a Knowledge Panel.

**Access:** Verify the available integration and its current key, quota and billing requirements.

---

## Custom Search JSON API

Programmatic Google search results (limited).

**Endpoint:** `GET https://customsearch.googleapis.com/customsearch/v1`

| Param | Description |
|-------|-------------|
| `key` | API key (required) |
| `cx` | Programmable Search Engine ID (required) |
| `q` | Search query |
| `num` | Results per page (1-10) |
| `start` | Start index (max 91) |
| `dateRestrict` | Date restriction (e.g., `d30` for 30 days) |
| `gl` | Country (e.g., `us`) |
| `lr` | Language restriction |
| `searchType` | `image` for image search |
| `siteSearch` | Restrict to a domain |

**Limitations:**
- Max 100 total results per query (10 pages x 10 results)
- Account eligibility, lifecycle dates, quotas and price must be checked against the actual connected service before use.

For SERP evidence, choose a verified search connector or supplied export with the requested market, language and device scope. The [DataForSEO method](../../seo-dataforseo/SKILL.md) describes optional provider inputs.

---

## Web Risk API

Check if URLs are flagged as unsafe by Google Safe Browsing.

**Endpoint:** `GET https://webrisk.googleapis.com/v1/uris:search`

| Param | Description |
|-------|-------------|
| `threatTypes` | `MALWARE`, `SOCIAL_ENGINEERING`, `UNWANTED_SOFTWARE`, `SOCIAL_ENGINEERING_EXTENDED_COVERAGE` |
| `uri` | URL to check |
| `key` | API key (required) |

**Response (clean URL):** Empty threat object.

**Response (flagged URL):**
```json
{
  "threat": {
    "threatTypes": ["MALWARE"],
    "expireTime": "2026-04-01T00:00:00Z"
  }
}
```

**Use for SEO:** Record the returned threat match and expiry for the tested URL. Investigate any relationship with indexing separately; the threat response alone does not establish a deindexing cause.

**Access:** Verify the available integration, permitted threat types, current billing and quota before use.
