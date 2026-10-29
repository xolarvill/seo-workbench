---
name: seo-dataforseo
description: >
  Live SEO data via DataForSEO MCP server. SERP analysis (Google, Bing, Yahoo,
  YouTube, Google Images), keyword research (volume, difficulty, intent, trends),
  backlink profiles, on-page analysis (Lighthouse, content parsing), competitor
  analysis, content analysis, business listings, AI visibility (ChatGPT scraper,
  LLM mention tracking), and domain analytics. Uses installed Workbench backlink collection or a verified DataForSEO connector/export. Use when user says "dataforseo", "live SERP", "keyword volume",
  "backlink data", "competitor data", "AI visibility check", "LLM mentions",
  "image SERP", "google images", "image rankings", or "real search data".
user-invokable: true
argument-hint: "[command] [query]"
license: MIT
compatibility: "Workbench paid backlinks collect/gap, or verified DataForSEO connector/export for other API families"
metadata:
  author: AgriciDaniel
  version: "1.9.6"
  category: seo
---

# DataForSEO evidence and API selection

## Installed collection and available inputs

Workbench has paid DataForSEO backlink snapshot and competitor-intersection collectors. Inspect their current interfaces before an authorized collection:

```bash
./seo backlinks collect --help
./seo backlinks gap --help
```

Use `--project` to select the store. Both collectors require `--confirm-paid`; choose bounded row/competitor limits within the user's existing spending authorization. Existing provider snapshots and exports can often answer the question. Read [Workbench operations](../seo/references/workbench-operations.md) and the [backlinks method](../backlinks/SKILL.md).

The API families below are a source capability map. They do not register slash commands or guarantee that an MCP tool is connected. For other families, discover an actually available connector, inspect its schema and configured identity, or use supplied output. The [source tool catalog](references/tool-catalog.md) helps identify candidate endpoint families; runtime discovery supplies the callable tool names and parameters.

## Query scope and cost

Choose market, language, device, dates and result depth from project context. Reuse suitable existing results. Before a paid query, establish the endpoint, bounded request count, pricing basis and the user's spending authorization. Account for pagination, task submission/retrieval and optional sub-calls. Preserve provider-reported cost where available. The local collector's explicit paid flag is its execution gate; the source pack's budget tracker and extension installer are not installed here.

Read [cost planning](references/cost-tiers.md) for a scoped estimate. A skill selection or estimated unit price does not itself authorize new spending.

## SERP Analysis

### serp <keyword>

Fetch live Google organic search results.

**Source endpoint identifiers to verify:** `serp_organic_live_advanced`

**Query scope:** choose the target market, language, device and result depth from project context; record the values used.

**Also supports:** The `serp_organic_live_advanced` tool supports Google, Bing, and Yahoo via the `se` parameter. Specify "bing" or "yahoo" to switch search engines.

**Output:** Rank, URL, title, description, domain, featured snippets, AI overview references, People Also Ask.

### serp-youtube <keyword>

Fetch YouTube search results. Valuable for GEO. YouTube mentions correlate most strongly with AI citations.

**Source endpoint identifiers to verify:** `serp_youtube_organic_live_advanced`

**Output:** Video title, channel, views, upload date, description, URL.

### youtube <video_id>

Deep analysis of a specific YouTube video: info, comments, and subtitles. YouTube mentions have the strongest correlation (0.737) with AI visibility, making this critical for GEO analysis.

**Source endpoint identifiers to verify:** `serp_youtube_video_info_live_advanced`, `serp_youtube_video_comments_live_advanced`, `serp_youtube_video_subtitles_live_advanced`

**Parameters:** video_id (the YouTube video ID, e.g., "dQw4w9WgXcQ")

**Output:** Video metadata (title, channel, views, likes, description), top comments with engagement, subtitle/transcript text.

### serp-images <keyword>

Fetch live Google Images search results. See which images rank for a keyword,
which domains dominate image results, and identify visual content opportunities.

**Source endpoint identifiers to verify:** `serp_google_images_live_advanced`

**Query scope:** choose the target market, language, device and result depth from project context; record the values used.

**Parameters:** keyword (required), depth (optional, max 700, billed per 100-result increment), search_param (optional, e.g. "site:example.com")

**Cost scope:** verify the provider pricing for operators, result depth and queue before a paid filtered query.

**Output:** Position, title, alt text, source page URL, direct image URL, domain, encoded URL.

**Analysis to provide:**
- Domain dominance: which sites own the most image positions (top 10 domains by count)
- Alt text patterns: common title/alt text patterns in top-ranking images
- Format distribution: WebP vs JPEG vs PNG in top results (infer from image_url extension)
- Opportunity identification: keywords where user has organic rankings but no image presence

---

## Keyword Research

### keywords <seed>

Generate keyword ideas, suggestions, and related terms from a seed keyword.

**Source endpoint identifiers to verify:** `dataforseo_labs_google_keyword_ideas`, `dataforseo_labs_google_keyword_suggestions`, `dataforseo_labs_google_related_keywords`

**Query scope:** use the project market/language and a bounded result limit.

**Output:** Keyword, search volume, CPC, competition level, keyword difficulty, trend.

### volume <keywords>

Get search volume and metrics for a list of keywords.

**Source endpoint identifiers to verify:** `kw_data_google_ads_search_volume`

**Parameters:** keywords (array, comma-separated), location_code, language_code

**Output:** Keyword, monthly search volume, CPC, competition, monthly trend data.

### difficulty <keywords>

Calculate keyword difficulty scores for ranking competitiveness.

**Source endpoint identifiers to verify:** `dataforseo_labs_bulk_keyword_difficulty`

**Parameters:** keywords (array), location_code, language_code

**Output:** Keyword and provider difficulty score with its scale and definition.

### intent <keywords>

Classify keywords by user search intent.

**Source endpoint identifiers to verify:** `dataforseo_labs_search_intent`

**Parameters:** keywords (array), location_code, language_code

**Output:** Keyword, intent type (informational, navigational, commercial, transactional), confidence score.

### trends <keyword>

Analyze keyword trends over time using Google Trends data.

**Source endpoint identifiers to verify:** `kw_data_google_trends_explore`

**Parameters:** keywords (array), location_code, date_from, date_to, language_code

**Output:** Keyword, time series data, trend direction, seasonality signals.

---

## Domain & Competitor Analysis

### backlinks <domain>

Provider-scoped backlink profile analysis; use the canonical backlinks method for completeness and comparison rules.

**Source endpoint identifiers to verify:** `backlinks_summary`, `backlinks_backlinks`, `backlinks_anchors`, `backlinks_referring_domains`, `backlinks_bulk_spam_score`, `backlinks_timeseries_summary`

**Default parameters:** limit=100 per sub-call

**Output:** Total backlinks, referring domains, domain rank, spam score, top anchors, new/lost backlinks over time, dofollow ratio, top referring domains.

### competitors <domain>

Identify competing domains and estimate traffic.

**Source endpoint identifiers to verify:** `dataforseo_labs_google_competitors_domain`, `dataforseo_labs_google_domain_rank_overview`, `dataforseo_labs_bulk_traffic_estimation`

**Output:** Competitor domains, keyword overlap %, estimated traffic, domain rank, common keywords.

### ranked <domain>

List keywords a domain ranks for with positions and page data.

**Source endpoint identifiers to verify:** `dataforseo_labs_google_ranked_keywords`, `dataforseo_labs_google_relevant_pages`

**Query scope:** use the project market/language and a bounded result limit.

**Output:** Keyword, position, URL, search volume, traffic share, SERP features.

### intersection <domain1> <domain2> [...]

Find shared keywords and backlink sources across 2-20 domains.

**Source endpoint identifiers to verify:** `dataforseo_labs_google_domain_intersection`, `backlinks_domain_intersection`

**Parameters:** domains (2-20 array)

**Output:** Shared keywords with positions per domain, shared backlink sources, unique keywords per domain.

### traffic <domains>

Estimate organic search traffic for one or more domains.

**Source endpoint identifiers to verify:** `dataforseo_labs_bulk_traffic_estimation`

**Parameters:** domains (array)

**Output:** Domain, estimated organic traffic, estimated traffic cost, top keywords.

### subdomains <domain>

Enumerate subdomains with their ranking data and traffic estimates.

**Source endpoint identifiers to verify:** `dataforseo_labs_google_subdomains`

**Parameters:** target (domain), location_code, language_code

**Output:** Subdomain, ranked keywords count, estimated traffic, organic cost.

### top-searches <domain>

Find the most popular search queries that mention a specific domain in results.

**Source endpoint identifiers to verify:** `dataforseo_labs_google_top_searches`

**Parameters:** target (domain), location_code, language_code

**Output:** Query, search volume, domain position, SERP features, traffic share.

---

## Technical / On-Page

### onpage <url>

Run on-page analysis including Lighthouse audit and content parsing.

**Source endpoint identifiers to verify:** `on_page_instant_pages`, `on_page_content_parsing`, `on_page_lighthouse`

**Usage:**
- `on_page_instant_pages`:Quick page analysis (status codes, meta tags, content size, page timing, broken links, on-page checks)
- `on_page_content_parsing`:Extract and parse page content (plain text, word count, structure)
- `on_page_lighthouse`:Full Lighthouse audit (performance score, accessibility, best practices, SEO, Core Web Vitals)

**Output:** Pages crawled, status codes, meta tags, titles, content size, load times, Lighthouse scores, broken links, resource analysis.

### tech <domain>

Detect technologies used on a domain.

**Source endpoint identifiers to verify:** `domain_analytics_technologies_domain_technologies`

**Output:** Technology name, version, category (CMS, analytics, CDN, framework, etc.).

### whois <domain>

Retrieve WHOIS registration data.

**Source endpoint identifiers to verify:** `domain_analytics_whois_overview`

**Output:** Registrar, creation date, expiration date, nameservers, registrant info (if public).

---

## Content & Business Data

### content <keyword/url>

Analyze content quality, search for content by topic, and track phrase trends.

**Source endpoint identifiers to verify:** `content_analysis_search`, `content_analysis_summary`, `content_analysis_phrase_trends`

**Parameters:** keyword (for search/trends) or URL (for summary)

**Output:** Content matches with quality scores, sentiment analysis, readability metrics, phrase trend data over time.

### listings <keyword>

Search business listings for local SEO competitive analysis.

**Source endpoint identifiers to verify:** `business_data_business_listings_search`

**Parameters:** keyword, location (optional)

**Output:** Business name, description, category, address, phone, domain, rating, review count, claimed status.

---

## AI Visibility / GEO

### ai-scrape <query>

Scrape what ChatGPT web search returns for a query. Real GEO visibility check: see which sources ChatGPT cites for your target keywords.

**Source endpoint identifiers to verify:** `ai_optimization_chat_gpt_scraper`

**Parameters:** query, location_code (optional), language_code (optional). Use `ai_optimization_chat_gpt_scraper_locations` to look up available locations.

**Output:** ChatGPT response content, cited sources/URLs, referenced domains.

### ai-mentions <keyword>

Track how LLMs mention brands, domains, and topics. Keep the tested models, query set and capture scope with the observations.

**Source endpoint identifiers to verify:** `ai_opt_llm_ment_search`, `ai_opt_llm_ment_top_domains`, `ai_opt_llm_ment_top_pages`, `ai_opt_llm_ment_agg_metrics`

**Parameters:** keyword, location_code (optional), language_code (optional). Use `ai_opt_llm_ment_loc_and_lang` for available locations/languages and `ai_optimization_llm_models` for supported LLM models.

**Workflow:**
1. Search LLM mentions with `ai_opt_llm_ment_search` (find mentions of a brand/keyword across LLM responses)
2. Get top cited domains with `ai_opt_llm_ment_top_domains` (which domains are most cited for this topic)
3. Get top cited pages with `ai_opt_llm_ment_top_pages` (which specific pages are most cited)
4. Get aggregate metrics with `ai_opt_llm_ment_agg_metrics` (overall mention volume, trends)

**Output:** LLM mention count, top cited domains with frequency, top cited pages, mention trends over time, provider-defined cross-platform metrics with their definitions.

**Advanced:** Use `ai_opt_llm_ment_cross_agg_metrics` for cross-model comparison (how mentions differ across ChatGPT, Claude, Perplexity, etc.).

---

## Apply results to the current method

Use SERP inputs for intent and landing-page review, keyword inputs for demand/ownership planning, provider backlinks for link analysis, and AI output for the tested query/model observation. For local technical collection, prefer existing Workbench raw/rendered, technology and Lighthouse collectors; use CrUX for field performance verdicts. Read the canonical skill before drawing specialist conclusions.

Retain requested scope, provider/endpoint, capture time, pagination/completeness, exact market/language/device and reported cost. Provider traffic and keyword estimates remain estimates; a scraped AI response describes its own sample. Do not manufacture scores from unavailable fields.

## Failed or unavailable inputs

If a connector is unavailable, work from suitable existing evidence or specify the missing input. Authentication errors need configuration of the actual integration rather than an archived installer. For invalid market codes or unsupported parameters, inspect the connector's lookup/schema. Preserve quota failures, empty results and partial coverage separately from measured zero, and bound retries according to the actual connector contract.
