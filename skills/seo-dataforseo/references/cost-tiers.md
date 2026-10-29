# DataForSEO cost planning

Use the actual integration's current pricing and returned cost fields for a spending decision. The source pack's price table and budget presets are historical estimates recorded at its pinned source revision; they do not configure a local budget service.

## Establish the request cost

Record the endpoint family, queue/live mode, market, result depth, requested rows and number of targets. Count pagination and secondary calls as part of the proposed operation. Some APIs charge per task, result increment, row or keyword batch, so a generic cost per call is insufficient. Check operator and enrichment surcharges when present.

The installed Workbench `backlinks collect` and `backlinks gap` collectors have explicit `--confirm-paid` gates and bounded row/competitor options; inspect command help before an authorized operation. Other DataForSEO families require a verified connector or supplied input. A connected server does not imply a locally enforced daily spending limit.

Use existing spending authorization for the requested bounded operation. If its cost or scope would exceed that authorization, prepare the concrete request estimate for the user's decision before executing. Preserve actual provider-reported cost with the result; an unavailable cost remains unknown.

## Reduce unnecessary calls

- Reuse current evidence with matching market, device, date and query scope.
- Choose the smallest result depth that answers the question.
- Use a supported bulk endpoint when it reduces the actual billing units.
- Consider a supported asynchronous queue when latency is acceptable and current pricing makes it useful.
- Request advanced SERP fields or extra subreports only when they change the analysis.

Do not import an upstream extension or claim that a missing local budget tracker has approved a call. This reference supplies planning criteria; execution follows the verified collector or connector contract.
