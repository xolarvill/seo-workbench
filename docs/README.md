# SEO Workbench Documentation

The operational references are in English. The practical SEO tutorials are written in Simplified Chinese so they can explain implementation choices without duplicating the main README.

## Start here

1. [SEO 基础知识与证据模型](SEO基础知识与证据模型.md) explains what can be observed, inferred, measured, or only verified by Google data.
2. [SEO 工具链协同工作流指南](SEO工具链协同工作流指南.md) maps Workbench commands to decisions and deliverables.
3. [从 0 到 1 新站 SEO 建设教程](从0到1新站SEO建设教程.md) covers discovery, launch, measurement, and iteration for a new site.

## Choose the site guide

| Site type | Guide | Main concerns |
|---|---|---|
| Shopify Liquid theme | [Shopify 从 0 到 1 SEO 建设进阶教程](Shopify从0到1-SEO建设进阶教程.md) | templates, collections, products, apps, markets |
| Shopify Hydrogen | [Shopify Hydrogen Headless SEO 指南](Shopify-Hydrogen-Headless-SEO指南.md) | raw/rendered parity, routing, Storefront API, edge delivery |
| WooCommerce B2B | [WooCommerce B2B SEO 指南](WooCommerce-B2B-SEO指南.md) | public catalog, inquiry, role pricing, cache boundaries |
| Custom or framework-free site | [自建普通网站 SEO 指南](自建普通网站SEO指南.md) | HTTP contracts, HTML, routing, Sitemap, release checks |

The platform guides contain only platform-specific decisions. Use the shared foundation for content quality, evidence confidence, structured data boundaries, Lighthouse, CrUX, GSC, and audit-diff interpretation.

## Operations and architecture

- [Google integrations](google-integrations.md): CrUX and read-only GSC configuration, evidence scopes, and status meanings.
- [Standalone workbench architecture](independent-workbench.md): local setup, project isolation, CLI boundaries, and runtime design.
- [Preserved SEO capability families](capability-preservation.md): provenance and capability-preservation notes from the standalone refactor.

## Evidence selection

| Question | Evidence |
|---|---|
| What did the server return? | raw evidence |
| What did the browser render? | rendered evidence |
| Which technologies were observable? | technology evidence |
| How does the page perform in a controlled run? | Lighthouse |
| How did eligible Chrome users experience it? | CrUX |
| What did Google Search report? | GSC |
| What changed between comparable collections? | audit diff |

Do not merge these sources into one SEO score. Keep URL, final URL, collection scope, device or form factor, data window, and confidence attached to every conclusion.
