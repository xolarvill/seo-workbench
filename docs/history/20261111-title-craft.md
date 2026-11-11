# Title craft for article titles

Date: 2026-11-11

## Background

Agent-written article titles were repeatedly accurate but bland: `A Guide to X`, `How to Improve Y`, `What Is Z?`. The existing write-content guidance asked for clarity and a truthful reason to read, but gave no method for finding that reason. The SEO optimization layer also warned against unsupported `best`, year and numeric claims; in practice that warning was over-applied, and specific, supported details were removed along with unsupported ones.

A reviewed external skill, [seo-title-optimization](https://github.com/Illyism/seo-skills/blob/main/seo/seo-title-optimization/SKILL.md), was a useful title audit checklist but not a title ideation method. Its `keyword + modifier + brand` formula and generic modifiers (`Best`, `Top`, `Complete`, current year) would reinforce the same template problem. It was not imported.

A second defect was concrete: `skills/seo-flow/references/prompts/local/prompt-generating-a-title-tag.md` was named as a title generator but asked for an executive summary, priority table, measurement plan and verification checklist. It did not ask for a title.

## Decision

Add title craft to the existing `write-content` capability instead of creating a second title skill or importing the external skill.

The method covers:

1. State the article's angle in one sentence before drafting.
2. Generate six to eight candidates across explicit strategies, not one safe default.
3. Select against intent fit, specificity, truth, differentiation, voice, display and a single promise.
4. Separate title, H1 and meta-description roles.
5. Keep post-publication GSC CTR review optional and diagnostic, not causal proof.

The optional "blandness test" from the review was intentionally left out. The seo-flow title prompt was rewritten to generate and evaluate actual titles.

## Files

- Added `skills/write-content/references/title-craft.md`.
- Updated `skills/write-content/SKILL.md` to route article drafting through title craft.
- Updated `skills/write-content/references/seo-optimization-layer.md` to make title craft the pre-draft method and the metadata section the final check, while allowing supported specifics.
- Updated `skills/write-content/references/quality-scoring.md` so a topic-only title is not accepted as merely "accurate".
- Updated `skills/improve-content/SKILL.md` and `skills/README.md` so title revisions reuse the same method.
- Rewrote `skills/seo-flow/references/prompts/local/prompt-generating-a-title-tag.md` as an actual title-generation prompt.

## Boundaries

- The method does not require a fixed character count, a fixed number of modifiers, or a title formula.
- Unsupported superlatives, numbers and years remain prohibited.
- No title change is treated as a guaranteed CTR or ranking improvement.
- A title cannot make a generic article specific; the article angle is a prerequisite.

## Verification

- `python3 scripts/skill_inventory.py check --strict-active`
- `python3 -m pytest tests/test_skill_layout.py`
- `./seo --project <id> validate --json` (an initialized local project; this checkout has no default project)
- `git diff --check`

Results are recorded in the commit that introduced this note.
