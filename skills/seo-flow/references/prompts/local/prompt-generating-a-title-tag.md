<!-- Source: github.com/AgriciDaniel/flow | License: CC BY 4.0 | Synced: 2026-04-26 -->
---
title: "Prompt: Generating a Title Tag"
description: "Prompt: Generating a Title Tag"
updated: 2026-11-11
tags:
  - prompts
  - local
---

# Prompt: Generating a Title Tag

## Use This When

Use this prompt when a page has a topic, reader, intent and evidence, and you need title candidates with a defensible reason to read. It is not a request for a general SEO audit.

## AI Compatibility

Works with long-context reasoning models. For smaller models, provide narrower inputs and ask for the angle and candidates in separate turns.

## Inputs

- Page or article topic, target query and search intent.
- Reader and the decision or action the page supports.
- Page type: article, comparison, how-to, definition, listicle or service page.
- Three to five observed SERP titles for the same query, when available.
- Concrete evidence the page can support: findings, numbers, names, constraints, examples.
- Brand voice and any banned phrases.
- Display constraints that matter for the target language and layout.

## Prompt

```text
Act as an editor and SEO strategist. Create title candidates for: [PAGE OR ARTICLE].

Inputs:
- Target query and intent: [QUERY AND INTENT]
- Reader and decision: [WHO THE PAGE IS FOR AND WHAT THEY NEED TO DECIDE]
- Page type: [PAGE TYPE]
- Observed SERP titles: [3-5 TITLES, OR "not supplied"]
- Supported specifics: [FINDINGS, NUMBERS, NAMES, CONSTRAINTS, EXAMPLES]
- Brand voice and constraints: [VOICE, BANNED PHRASES]
- Display constraints: [LANGUAGE, LAYOUT, KNOWN TRUNCATION]

First state the article's angle in one sentence: "After reading this, the reader can / will know / will avoid ___." Use only the supplied material. If the material does not support an angle, say what is missing instead of inventing one.

Then generate 6-8 title candidates. Label each with its strategy: specific outcome, named object or number, common mistake, tradeoff, reader situation, comparison, counterintuitive finding, or how-to with a boundary. Use only facts supplied. Do not add best, top, complete, a year or a number unless the input supports it. Do not copy a SERP title.

For each candidate, give:
1. The title.
2. The strategy.
3. The specific fact or section that supports it.
4. The main risk: overpromise, ambiguity, truncation or an unsupported claim.

Recommend one primary title and one or two alternates. Explain the choice against intent fit, specificity, truth, differentiation, voice and display. Then give H1 and meta-description notes. Mark any claim that still needs verification.
```

## Output

- The angle sentence.
- A candidate table: title, strategy, supporting fact, risk.
- One primary title and one or two alternates, with the reason for the choice.
- H1 and meta-description notes.
- Claims or facts that still need verification.

## Example

Input: a page about migrating a small team's analytics setup, with a documented constraint that the CMS cannot change.

Expected output: a candidate such as `Analytics Migration for Teams That Cannot Change Their CMS`; reject `The Ultimate Guide to Analytics Migration` when the page has no evidence for the superlative. The example is a pattern, not a claim about a real page.

## See Also

- [Title craft](../../../../write-content/references/title-craft.md)
- [Prompt Library](../README.md)
- [FLOW Framework](../../flow-framework.md)
- [Bibliography](../../bibliography.md)

## Source Note

Derived from the Local SEO Knowledge Base structure and rewritten for public use with the repository evidence standard. Title-specific method follows the write-content title craft reference.
