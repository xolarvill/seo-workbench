# SEO Workbench Documentation

The operational references are in English. The practical SEO tutorials are written in Simplified Chinese so they can explain implementation choices without duplicating the main README.

## Start here

1. [SEO 基础知识与证据模型](SEO基础知识与证据模型.md) explains what can be observed, inferred, measured, or only verified by Google data.
2. [SEO 增长诊断与拆解](SEO增长诊断与拆解.md) connects search visibility to visits, products, conversion, and revenue without turning diagnostic models into ranking formulas.
3. [SEO 工具链协同工作流指南](SEO工具链协同工作流指南.md) maps Workbench commands to decisions and deliverables.
4. [从 0 到 1 新站 SEO 建设教程](从0到1新站SEO建设教程.md) covers discovery, launch, measurement, and iteration for a new site.
5. [BLOG 生产线操作教程](BLOG生产线操作教程.md) is the day-to-day Workbench-led path from topic approval through Shopify scheduling, GSC inspection, and Feishu notification.
6. [Technical SEO Audit](technical-audit.md) documents the bounded crawl, deterministic rules, GSC priority model, diff, scheduling, and Feishu notification loop.
7. [SEO 迭代闭环](SEO迭代闭环.md) covers the Pages action loop, change records, outcome review, aggregate business signals, technical issue verification, and backlink snapshots.
8. [统计学 SEO 操作手册](统计学SEO操作手册.md) defines production prerequisites, measurement-regime duties, statistical methods, UI surfaces, and recovery rules.

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
- [Shopify integrations](shopify-integrations.md): Admin API credential setup, granted scopes, rotation, and project isolation.
- [Statistical SEO operations](统计学SEO操作手册.md): the minimum operator preparation, daily collection entry point, measurement boundaries, and metric catalog.
- [Hexcal BLOG adapter](hexcal-blog-migration.md): optional Feishu field aliases, ownership boundaries, and retained production capabilities.
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
| Which technical issues are tied to page performance and historical change? | technical audit |
| Which shipped SEO changes are winning or regressing after their review date? | change ledger + GSC + optional aggregate business signals |
| Which same-site pages need action, review, or observation now? | Pages workspace + full-site portfolio |
| Which external links are new, confirmed lost, or pointing to known 404/410 targets? | same-source backlink snapshots + technical inventory |
| What changed between comparable collections? | audit diff |

Do not merge these sources into one SEO score. Keep URL, final URL, collection scope, device or form factor, data window, and confidence attached to every conclusion.
