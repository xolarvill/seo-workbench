# Cost Tracking Reference

> Load this on-demand when the user asks about costs or before batch operations.

## Historical Source Pricing Examples

These figures describe the preserved source snapshot. They are not a current
quote or an estimate for the session’s selected tool. For a planned charged
request, verify the actual provider/model, unit, quantity, and current rate.

| Model | Resolution | Cost/Image | Notes |
|-------|-----------|-----------|-------|
| 3.1 Flash | 512 | $0.020 | Quick drafts |
| 3.1 Flash | 1K | $0.039 | Standard (default) |
| 3.1 Flash | 2K | $0.078 | Quality assets |
| 3.1 Flash | 4K | $0.156 | Print/hero images |
| 2.5 Flash | 512 | $0.020 | Draft fallback |
| 2.5 Flash | 1K | $0.039 | Standard fallback |
| Batch API | Any | 50% of above | Asynchronous, higher latency |

Pricing is approximate, based on ~1,290 output tokens per image.
Research suggests actual costs may be ~$0.067/img. Verify at https://ai.google.dev/gemini-api/docs/pricing

## Historical Source Free-Tier Examples

- ~10 requests per minute (RPM)
- ~500 requests per day (RPD)
- Per Google Cloud project, resets midnight Pacific

## Usage Evidence

Use actual tool responses or a verified provider usage report. Useful fields are
provider, account/project scope, model, returned resolution, image count, request
time, billed unit/count, currency, charge, and whether a value is estimated or
settled. Preserve only fields the source actually exposes; unknown cost is not
zero. Keep credentials and private account identifiers out of shared reports.

For a batch, establish the requested quantity and actual provider charging basis
before the call. Afterward, record returned usage alongside the existing project
task artifact when useful. This repository supplies no image cost tracker or
automatic ledger. Do not create or reset a global ledger, or infer total account
usage from the current conversation's images.
