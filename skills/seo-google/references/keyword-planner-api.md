# Google Ads API - Keyword Planner Reference

Source method for interpreting supplied Google Ads keyword data or a verified optional connector. Workbench does not implement a Keyword Planner collector.

## Required input or integration

Use an existing Keyword Planner export or discover an available Google Ads connector. Verify account/customer identity, market, language, date range and whether volumes are counts or ranges. For a connector, inspect its current developer-token, OAuth scope and manager/customer requirements. A Workbench GSC or GA4 read-only profile does not establish Google Ads access. A keyword research task does not authorize creating an advertising campaign.

## Key Methods

### GenerateKeywordIdeas
Generate keyword suggestions from seed terms.

**Returns per keyword:**
- `text`: Keyword string
- `avg_monthly_searches`: Average monthly volume (exact if spending, bucketed if not)
- `competition`: LOW / MEDIUM / HIGH (for ads, not organic)
- `competition_index`: 0-100 competition score
- `low_top_of_page_bid_micros`: ~20th percentile CPC in micros
- `high_top_of_page_bid_micros`: ~80th percentile CPC in micros
- `monthly_search_volumes[]`: Per-month volume for last 12 months

### GenerateKeywordHistoricalMetrics
Get volume data for specific keywords.

Same return fields as above but for exact keyword list instead of suggestions.

### GenerateKeywordForecastMetrics
Predict clicks, impressions, and cost for keywords.

## Configuration

Configure only the verified optional connector using its actual credential and account-binding contract. Keep its developer token and OAuth material in that integration's supported private secret storage. Do not create a global source-pack config or add Ads credentials to Workbench's GSC/GA4 binding. Supplied exports can be analyzed without configuring a connection.

## Rate Limits

- Keyword Planning requests are more strictly rate-limited than other Ads API services
- Exact QPM/QPS not publicly documented
- Google recommends caching results

## Important Notes

- **Volume precision**: Preserve the returned granularity and account/source context; do not turn a range into an exact count or promise precision based on an assumed spending threshold.
- **Competition score**: Measures advertiser competition for ads, NOT organic ranking difficulty
- **CPC bids**: Reflect what advertisers pay, useful for estimating keyword commercial value
- **Location targeting**: Use location IDs (2840 = United States, 2826 = United Kingdom)
- **Language targeting**: Use language IDs (1000 = English, 1003 = Spanish)
