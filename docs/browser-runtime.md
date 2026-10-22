# Browser collection runtime

Workbench uses the Chromium revision shipped for the installed Playwright.
The resolver recognizes both the matching headless shell and full Chromium.
Install with `./setup.sh --local-browser` when neither is available. Browser
paths are prepared before starting the driver. There is no silent fallback to
the user's daily Chrome application. `CHROME_PATH` remains an explicit override
for an executable chosen by the operator; its compatibility is the operator's
responsibility. Browser resolution does not install, upgrade or kill software.

Rendered collection and Lighthouse share one local workload lease. A concurrent
job reports busy rather than launching another browser. Contexts close before
the browser; setup, collection and diagnostic-write failures also enter cleanup.
A renderer crash or unexpected disconnect stops the current capture; it does not
trigger repeated browser launches or turn missing profiles into successful
observations. This reduces avoidable launches and overlapping workloads; it is
not evidence that every historical OS crash dialog had the same cause.

Each capture saves a private, timestamped `browser-runtime-*.json` with selected
executable, Playwright/browser versions, parent/browser process metadata where
available, lifecycle outcome and failure stage. Launch failures retain parsed
exit code/signal and permission classification when available. Raw exception
command lines are excluded. Missing process metadata is explicit; memory
exhaustion is not inferred from a generic browser close. Keep crash reports,
execution time and process IDs aligned when investigating a new OS dialog.

Probe comparisons require eligible HTML, desktop evidence and matching final
routes, preserving non-root trailing slashes. A failed desktop does not silently
substitute mobile. Raw/desktop comparisons can be unavailable while positive
observations for another profile remain useful. Challenge/error responses and
partial captures cannot prove missing elements. Rendered failures and partial
profiles propagate into structured collection status, including technical-audit
consumers; a low-confidence result is not a site defect or a verified fix.
