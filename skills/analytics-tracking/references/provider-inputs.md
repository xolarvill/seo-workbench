# Analytics provider inputs

Use the current project's event plan, measurement regimes and collected evidence first. For Workbench GA4 setup and collection, read [Google integrations](../../../docs/google-integrations.md) and [current operations](../../seo/references/workbench-operations.md).

| Source | Inputs needed for this task |
|---|---|
| GA4 | Bound property, exact window/timezone, dimensions, event definitions and tracking coverage |
| Mixpanel / Amplitude / PostHog | Project identity, event/property schema, cohort filters, interval and export or verified connected read operation |
| Segment | Source/destination mapping, event contract and delivery/debug observations |

A provider name does not establish an installed connector. Discover the session's available tools before using a provider; consult its current official API contract when implementing integration. Without access, use supplied exports and identify the missing input. Keep event counts, users and sessions distinct and preserve consent/definition changes. Deliver an event map and verification observations tied to the selected property and window.
