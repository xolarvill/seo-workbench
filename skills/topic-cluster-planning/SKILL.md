---
name: topic-cluster-planning
description: Use when planning a topic cluster (hub + spokes) for a new content area. The agent researches the space, identifies the hub topic, maps the spokes, and produces a specific content plan with internal linking strategy.
---

# Topic Cluster Planning

Builds a hub-and-spoke architecture for a new content area. Hub = a broad pillar page that owns the topic. Spokes = specific articles that target long-tail keywords and link up to the hub. Done right, this signals topical authority to Google and concentrates link equity on the pages that matter.

## Input

**Seed topic or broad keyword** (required). Example: "email marketing", "keto diet", "small business accounting".

Optionally: your domain, so the agent can check what you've already published in this space.

## Role

You are a senior SEO content strategist specializing in topical authority architecture. You think in clusters, not individual articles.

## Step 1: Research the Topic Space

Google the seed topic. Read:
- The top 10 results for the broad keyword
- The People Also Ask questions
- The "Searches related to" at the bottom of the SERP
- 2-3 major publications in the space to see how they structure their content

Note:
- Who dominates the broad keyword? (This tells you the difficulty level.)
- What sub-topics emerge from PAA and related searches?
- What specific questions do people ask?

## Step 2: Identify the Hub

The hub is the one page that deserves to own the broad topic. It should:
- Target the broad/seed keyword directly
- Cover the topic comprehensively at a high level (don't go deep on every sub-topic)
- Link out to all the spoke articles

**Hub content type options:**
- **Ultimate guide** ("The Complete Guide to X") — best for broad informational topics
- **Pillar + chapters** (pillar page with a TOC linking to deep-dive chapters) — best for very broad topics with clear sub-chapters
- **Category page with curated featured content** — best for product/service topics

State your recommended hub format with reasoning.

## Step 3: Map the Spokes

From business needs, GSC queries, user research, PAA questions, related searches, and competitor coverage, identify only the spoke topics that deserve distinct pages. A small cluster may need three pages; a complex domain may need many more. Each spoke should:
- Target a long-tail keyword or specific question
- Go deeper on one narrow sub-topic than the hub can
- Link back to the hub (primary)
- Link to 2-3 related spokes

For each spoke, specify:
- Target keyword / question it answers
- Content type (how-to / definition / comparison / case study / listicle)
- Required scope, evidence, and format
- Why it matters for the cluster (what sub-topic does it own?)

**Rule of thumb:** a spoke should answer a question the hub can only summarize.

## Step 4: Map the Internal Linking

Draw the link graph:
- Every spoke links to the hub when that relationship helps the reader, using a descriptive anchor
- Hub links to every spoke (usually in a "In this guide" TOC or a "Related deep dives" section)
- Related spokes link to each other when the next step is useful
- Cite the primary and authoritative sources needed to support claims; do not target a fixed link count

Place important contextual links where users are likely to need them. Do not claim a universal “first link” weighting rule without site-specific test evidence.

## Step 5: Publishing Order

Choose the publishing order from user value and production readiness. A useful hub can launch first as a navigation and scope page; existing spokes can launch first when they provide the evidence the hub needs. Never publish an empty hub or delay a complete useful page only to follow a formula.

## Step 6: Output

### Cluster Overview
- Seed topic | Estimated difficulty (Easy / Moderate / Hard) based on SERP competition
- Delivery estimate based on actual research, writing, review, design, and implementation capacity

### Hub
- Recommended format (Ultimate guide / Pillar + chapters / Category)
- Target keyword (the broad seed)
- Main H2 sections (roughly 5-10)
- Required scope and evidence
- What the hub should NOT cover in depth (save that for spokes)

### Spoke List

| # | Spoke Topic | Target Query/Task | Content Type | Evidence Needed | Hub Anchor Text |
|---|---|---|---|---|---|

Include only justified pages. Sort by audience value, business fit, available evidence, dependency, and search opportunity.

### Publishing Sequence

Provide a dependency-aware sequence with owners or prerequisites. Use dates only when publishing capacity is known.

### Internal Link Map
A simple list showing which spokes link to which other spokes. Not every spoke needs to link to every other — just the naturally related ones.

### External Linking Strategy
3-5 authoritative external sources the hub should cite. (Not competitors — actual authoritative sources: research papers, industry standards, government/university resources, or the primary creators of the concepts you're discussing.)

### Success Metrics
- Published and indexed canonical pages
- Growth in relevant query and page impressions from GSC
- Qualified clicks, assisted conversions, leads, sales, or product discovery as applicable
- Internal-link and orphan-page coverage
- Content accuracy, freshness, and evidence maintenance

Set review windows rather than guaranteed positions. Rankings depend on competition, site history, links, demand, and search-system changes.

## What to Ignore

- **Publishing to a calendar instead of readiness** — release useful, reviewed pages at a sustainable cadence
- **Over-linking between spokes** — if it doesn't feel natural in the article, skip it
- **Keyword density in the hub** — the hub is about breadth, not keyword stuffing

## Next Step

For each spoke, use `content-brief` with the spoke's target keyword to produce a writer-ready brief. Then `write-content` to write the article.

## Bundled references

Load from `references/` only when the step calls for them.

- **`spoke-selection-worked-example.md`** — an illustrative cluster; do not copy its page count or schedule as a quota
- **`topic-cluster-strategy.md`** — optional architecture background; treat “topical authority” claims as a planning model, not a measured Google score
- **`pillar-page-template.md`** — optional hub outline; adapt it to the actual user task
