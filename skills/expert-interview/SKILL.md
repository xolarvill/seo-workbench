---
name: expert-interview
description: Use when extracting first-party expertise from a subject-matter expert before writing content. Produces an attributed knowledge document of observations, methods, examples and relevant limits through an interactive interview.
---

# Expert Interview

Extracts unique expertise through targeted interview questions. Produces a knowledge document that can be fed directly into `write-content` or `improve-content`, or used on its own for presentations or training materials.

This is a pure conversation skill. No data, no research, no URL fetching. Just good questions and active listening.

## Input

**Topic to discuss** (required — ask if not provided). Optionally: what the knowledge will be used for (blog article, case study, thought leadership piece, training material).

## Role

Help the expert explain what they actually know and how they know it. Ordinary, accurate professional practice can be useful without being surprising or contrary to common advice. Ask for specifics, numbers, failures or surprises only when they exist and help the intended reader. Do not press for a contrarian position, a story or false precision to complete a template.

## How to Conduct the Interview

Ask 2-4 questions, one at a time. Pick and adapt — don't ask all of them.

### Core questions (pick 2-3)

1. **"How do you approach [topic] in practice?"** — establishes the actual method or observation
2. **"Can you give an example or describe a check you use?"** — asks for available first-party detail; names or numbers are optional
3. **"What happened when you used this approach?"** — permits expected results as well as surprises or failures
4. **"What conditions or limits should a reader know?"** — establishes useful scope without requiring a rebuttal

If the expert mentions a misconception or unexpected result, ask which claim or expectation they mean and what evidence supports their view. Do not assume that most people are wrong or that the expert has a contrary opinion.

### Adapt to topic type

- **Technical / how-to**: "What should the reader check first?" Ask about observed errors if relevant, without assuming all beginners skip a step.
- **Comparison / review**: "Which option fits which conditions, and why?" Preserve supported tradeoffs rather than presuming an official answer is dishonest.
- **Thought leadership**: "What is your view, and what supports it?" Ask about disagreement or future expectations only when relevant; distinguish predictions from observations.
- **Case study**: "Walk me through what happened and what you observed." Request result numbers only if measured and available.

### Follow up on interesting answers

- "You mentioned X — what happened exactly?"
- "How did that compare to what you expected?"
- "Can you put a number on that?"

Ask one question at a time. Wait for the answer before proceeding. Quality depends on depth, not breadth — 2-3 excellent answers beat 8 surface-level ones.

### Adapt style to the user

- Newer site, less experienced user: explain why each question matters for the content you'll write
- Established site, experienced user: fast, direct, no hand-holding

## Output

After the interview, organize answers into a structured knowledge document:

**Expert Knowledge: [topic]**

- **Main explanation or observation** — what the expert knows, with a contrary view only if actually expressed and relevant
- **Examples and evidence** — available observations, checks, measurements or projects; preserve attribution and distinguish recollection from measured data
- **Experience details** — what happened; include failures or surprises only if reported
- **Scope and limitations** — who this applies to, who it doesn't, when the advice breaks down

This document can be passed directly to `write-content` or `improve-content` as context. Mark unavailable information without filling it in. The writer should use only material that serves the reader, preserve attribution and never turn an interview statement into a claim of independent testing. A complete, useful answer does not require more questions to meet a novelty or detail quota.

## Language

Conduct the interview in the language the user responds in.

## Bundled references

Load from `references` only when the step calls for them.

- **`question-bank-by-topic.md`** — a larger question bank organized by content type (how-to, comparison, thought leadership, case study, product review, definition) for when the 4 core questions don't fit the topic
- **`knowledge-doc-template.md`** — the full structured knowledge document template (Output section, when producing a reusable artifact instead of a one-off writeup)
- **`human-input-framework.md`** — the theory behind why first-party knowledge beats SERP synthesis (background, when the user asks "why not just research it yourself?")
- **`information-gain-writing.md`** — background on useful first-party contributions; apply the current writing method rather than a fixed information-gain percentage
- **`voice-injection-playbook.md`** — how the first-person phrasing carries into the final article (when handing off to `write-content` for a voice-heavy piece)
- **`eeat-signal-embedding.md`** — which interview answers to prioritize for demonstrated Experience signals (when the content needs to pass an E-E-A-T bar, e.g., YMYL)
