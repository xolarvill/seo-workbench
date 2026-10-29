# Marketplace Inputs and Normalization

This reference retains the source method's Google Shopping product, seller, and
Amazon comparison coverage. The repository does not install a Merchant search
client. Endpoint names and schemas must come from an actually available provider;
read its current tool contract before a request. See
[Workbench operations](../../seo/references/workbench-operations.md).

## Sample Identity

For each input retain provider/export source, query, country or location,
language, device where relevant, collection date, pagination/depth, completeness,
and currency. Record sponsored versus organic listing type when available. Price
comparisons need the same product variant, pack size, tax/shipping treatment,
and capture window. An incomplete listing sample cannot establish absence.

## Product and Seller Fields

| Analysis | Required observed fields |
|----------|--------------------------|
| Product pricing | Product title/ID, listing URL, variant, price, currency, shipping/tax treatment, availability |
| Listing quality | Title, image reference, rating, review count, seller, listing type |
| Seller landscape | Seller identity, seller listing count within the sample, seller rating and rating count |
| Amazon comparison | Product identity/ASIN where supplied, pack size/variant, price, currency, availability; Prime/badges only when observed |
| Organic/Shopping gaps | Query, observed organic page/rank, Shopping listing/rank, matching collection scope |

Use source columns actually present. Keep omitted rating, shipping, or availability
as unknown; do not fill them with zero or false. Deduplicate repeated products and
sellers before computing listing shares. Label every share with its sample base.

## Normalization

- Parse decimal prices without currency symbols and retain the original currency.
- Convert currencies only with a dated exchange-rate input and retain original values.
- Map observed availability to in_stock, out_of_stock, preorder, or unknown.
- Preserve a rating's scale and its review count; compare ratings on a common scale.
- Retain raw aggregate source values alongside normalized analytical values.

## Provider Operations

Use an available tool's task/poll and pagination contract. Record returned status,
errors, completeness, and charged usage when exposed. Respect its retry guidance;
no local Merchant budget-check, normalization, or task-poll script is bundled.
Current pricing and rate limits require provider evidence for the planned request.
A supplied export supports the same analysis without an API request.
