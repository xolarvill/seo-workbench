# Shopify integrations

SEO Workbench can keep one Shopify Admin API connection per `shopify` or `shopify-headless` project. The current integration manages credentials and permission visibility only; it does not mutate Shopify data or collect Shopify evidence yet.

## Create the credential

In Shopify Admin, create or open a custom app, configure only the Admin API scopes the SEO workflow actually needs, install the app, and copy its Admin API access token. Shopify shows a custom-app token only once, so store it directly in the local Workbench instead of a project document.

Use the permanent `store.myshopify.com` domain. Do not use the public storefront domain, a Shopify Admin URL, or a URL containing a path.

Start the local UI and open **Integrations**:

```bash
./seo --project example-store ui
```

Enter the `.myshopify.com` domain and Admin API access token, then select **Connect Shopify**. The Workbench performs one fixed read-only GraphQL request to verify:

- the token belongs to the entered store;
- the store name and canonical Shopify domain;
- every granted access scope.

The UI highlights the number of granted `write_*` scopes. This is a least-privilege warning, not evidence that the Workbench used a write operation.

## Storage and network boundary

- Credential endpoints are available only from the local `127.0.0.1` or `localhost` Workbench session.
- The target is restricted to HTTPS on a canonical `*.myshopify.com` hostname.
- The Admin GraphQL version is pinned to `2026-07`.
- Credentials are stored at `projects/<id>/.runtime/integrations/shopify.json` with mode `0600`; its parent runtime directories use mode `0700`.
- Status responses include shop identity, API version, scopes, and last verification time, but never the access token.
- **Verify connection** reuses the stored token without returning it. **Replace connection** verifies a new token before replacing the existing file.
- Removing a connection deletes the credential file but leaves project documents and existing evidence unchanged.

## Rotation

Generate or install the replacement custom-app token in Shopify Admin, enter it in **Replace Admin API access token**, and submit it. The old token remains stored until the new store identity and scopes verify successfully.

If Shopify rejects the token, confirm that the app remains installed on the same store. Scope changes can require reinstalling or updating the app before Shopify grants them.

## Official references

- [Shopify API access scopes](https://shopify.dev/docs/api/usage/access-scopes)
- [Shop query](https://shopify.dev/docs/api/admin-graphql/latest/queries/shop)
- [currentAppInstallation query](https://shopify.dev/docs/api/admin-graphql/latest/queries/currentappinstallation)
