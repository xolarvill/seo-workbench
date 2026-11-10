# Shopify integrations

SEO Workbench can keep one Shopify Admin API connection and one Shopify Web Bot Auth signature per `shopify` or `shopify-headless` project. The integration manages local credentials, permission visibility, publish dry-runs, and explicit operator-confirmed article publish/update commands.

With `read_orders` or `read_all_orders`, it can also collect two complete 28-day order windows and aggregate line-item net revenue by product handle. The collector excludes test and unpaid orders, uses the line-item price after discounts, returns, and refunds, and excludes tax and shipping. It stores no customer or order identifiers and does not attribute Shopify revenue to organic search.

```bash
./seo --project example-store shopify-orders collect --end-date 2026-08-10 --json
./seo --project example-store business-signals collect --json
```

For routine production use, prefer `./seo --project example-store statistics collect --json`; it derives the common finalized end date from GSC and prevents a Shopify window from being combined with different GA4 or search dates. Shopify revenue remains all-channel context, never organic-search attribution. Operational prerequisites and recovery are in the [statistical SEO operations manual](统计学SEO操作手册.md).

## Signed technical crawls

Shopify's **Online Store → Preferences → Crawler access** page can generate a Web Bot Auth signature for the public domain. In **Connections → Signed storefront crawl**, paste the three generated headers and set the expiration date:

- `Signature`
- `Signature-Input`
- `Signature-Agent` (Shopify's recommended value is `"https://shopify.com"`)

The saved signature is automatically attached to every robots.txt, sitemap, page, and bounded recrawl request for the exact configured public host. The crawl refuses an expired signature or one whose host does not match the project URL. This is native Shopify crawler authentication; the Workbench does not generate or modify the signature.

## Create the credential

In Shopify Admin, create or open a custom app, configure only the Admin API scopes the SEO workflow actually needs, install the app, and copy its Admin API access token. Shopify shows a custom-app token only once, so store it directly in the local Workbench instead of a project document.

Use the permanent `store.myshopify.com` domain. Do not use the public storefront domain, a Shopify Admin URL, or a URL containing a path.

Start the local UI and open **Connections**:

```bash
./seo --project example-store ui
```

Enter the `.myshopify.com` domain and Admin API access token, then select **Connect Shopify**. The Workbench performs one fixed read-only GraphQL request to verify:

- the token belongs to the entered store;
- the store name and canonical Shopify domain;
- every granted access scope.

The UI highlights the number of granted `write_*` scopes. This is a least-privilege warning, not evidence that the Workbench used a write operation.

## Publish articles

Preview the exact GraphQL payload first:

```bash
./seo --project example-store content publish-dry-run rec_xxx --blog-id YOUR_BLOG_ID --json
```

Publish or update only after review:

```bash
./seo --project example-store content publish rec_xxx --blog-id YOUR_BLOG_ID --confirm --json
```

The command reads `content/blog-pipeline.jsonl`, requires configured Shopify credentials with `write_content` or `write_online_store_pages`, writes an audit file under `audits/publish/`, and updates the local content queue only after Shopify confirms the scheduled publication date. HITL and blocking QC warnings cannot be bypassed.

## Storage and network boundary

- Credential endpoints are available only from the local `127.0.0.1` or `localhost` Workbench session.
- The target is restricted to HTTPS on a canonical `*.myshopify.com` hostname.
- The Admin GraphQL version is pinned to `2026-07`.
- Credentials are stored at `projects/<id>/.runtime/integrations/shopify.json` with mode `0600`; its parent runtime directories use mode `0700`.
- The crawler signature is stored separately at `projects/<id>/.runtime/integrations/shopify-crawler.json` with mode `0600`; signature values never appear in status responses, snapshots, logs, or CLI JSON output.
- Status responses include shop identity, API version, scopes, and last verification time, but never the access token.
- Publish audit files never include the access token.
- **Verify connection** reuses the stored token without returning it. **Replace connection** verifies a new token before replacing the existing file.
- Removing a connection deletes the credential file but leaves project documents and existing evidence unchanged.
- Removing the crawler signature only disables signed requests; it leaves existing crawl evidence unchanged.

## Rotation

Generate or install the replacement custom-app token in Shopify Admin, enter it in **Replace Admin API access token**, and submit it. The old token remains stored until the new store identity and scopes verify successfully.

If Shopify rejects the token, confirm that the app remains installed on the same store. Scope changes can require reinstalling or updating the app before Shopify grants them.

## Official references

- [Shopify API access scopes](https://shopify.dev/docs/api/usage/access-scopes)
- [Shop query](https://shopify.dev/docs/api/admin-graphql/latest/queries/shop)
- [currentAppInstallation query](https://shopify.dev/docs/api/admin-graphql/latest/queries/currentappinstallation)
- [Shopify: Crawling your store](https://help.shopify.com/en/manual/promoting-marketing/seo/crawling-your-store)
- [Shopify Web Bot Auth changelog](https://shopify.dev/changelog/bots-and-agents-should-identify-themselves-via-web-bot-auth)
