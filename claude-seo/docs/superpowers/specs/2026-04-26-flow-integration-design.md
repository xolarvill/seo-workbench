# Design: FLOW Framework Integration — Claude SEO v1.9.5

**Date:** 2026-04-26
**Author:** Daniel Agrici
**Status:** Approved — pending implementation plan
**Version target:** 1.9.5

---

## 1. Intent

Integrate the FLOW SEO knowledge base (github.com/AgriciDaniel/flow) into Claude SEO as a
prompt-and-framework layer. FLOW is a content corpus (72 docs, 42 prompts, CC BY 4.0). Claude SEO
is the execution runtime. This integration makes the runtime framework-aware: skills gain access to
FLOW's evidence-led prompts and operate within the Find → Leverage → Optimize → Win loop.

## 2. Integration depth: selective port (Option B)

Bundle the **operational layer** of FLOW into the claude-seo repo:
- 42 standardized AI prompts (`docs/09-prompts/`)
- FLOW framework overview (`docs/01-framework/flow-framework.md`)
- Bibliography (`docs/10-references/bibliography.md`)

Do NOT bundle the full 72-doc corpus. The full content lives at github.com/AgriciDaniel/flow as
the canonical source. Skills reference the canonical URL for anything beyond the operational layer.

**Rationale:** Prompts are the runtime-relevant artifacts — they travel with the agent. The 72 docs
are reference material better served from the canonical repo where they stay current.

## 3. New files

### 3.1 `skills/seo-flow/SKILL.md`

Entry-point skill. Exposes the FLOW framework and prompt library through the `/seo flow` command
surface. Routes to stage-specific prompts and cross-references existing skills.

**Commands:**

| Command | Behavior |
|---|---|
| `/seo flow` | Show FLOW framework overview + stage menu |
| `/seo flow find [url\|topic]` | Load Find-stage prompts, apply to target |
| `/seo flow leverage [url]` | Load Leverage-stage prompt (backlink/off-site) |
| `/seo flow optimize [url]` | Load Optimize-stage prompts, context-match to 2-3 most relevant |
| `/seo flow win [url]` | Load Win-stage prompts (BOFU, conversion, dual-surface scorecard) |
| `/seo flow local [url]` | Load Local-stage prompts (GBP, meta descriptions, title tags, audits) |
| `/seo flow prompts` | List all 42 prompts with stage + trigger conditions |
| `/seo flow sync` | Re-pull latest prompt files from github.com/AgriciDaniel/flow |

**Context matching rule:** `/seo flow optimize` does not dump all 18 prompts. It reads the current
analysis context (URL, industry, prior skill output) and surfaces the 2-3 most relevant. All 18
remain accessible by name via `/seo flow prompts`.

**Attribution (appears on every activation):**
```
Framework and prompts © Daniel Agrici, CC BY 4.0 — github.com/AgriciDaniel/flow
```

### 3.2 `skills/seo-flow/references/flow-framework.md`

Synced from `docs/01-framework/flow-framework.md` in the Flow repo. Contains the FLOW operating
model, stage definitions, AI agent prompt, and failure modes. The primary context document loaded
when any `/seo flow` command activates.

### 3.3 `skills/seo-flow/references/bibliography.md`

Synced from `docs/10-references/bibliography.md`. Loaded when skills need to cite sources or the
user asks for evidence backing a recommendation.

### 3.4 `skills/seo-flow/references/prompts/`

42 prompt files organized by FLOW stage. Each file is synced verbatim from the Flow repo with a
CC BY 4.0 attribution header inserted at the top:

```markdown
<!-- Source: github.com/AgriciDaniel/flow | License: CC BY 4.0 | Synced: YYYY-MM-DD -->
```

Directory structure:
```
prompts/
  README.md          ← index: all 42 prompts, stage, trigger conditions
  find/              ← 5 prompts
  leverage/          ← 1 prompt
  optimize/          ← 18 prompts
  win/               ← 3 prompts
  local/             ← 8 prompts (GBP, meta, titles, audits, deep research)
```

### 3.5 `agents/seo-flow.md`

Subagent definition. Handles prompt-guided analysis tasks delegated from the `seo-flow` skill:
reads the target URL, selects the relevant FLOW prompts, applies them, returns structured output
with the FLOW stage label and evidence requirements.

### 3.6 `scripts/sync_flow.py`

Sync script. Pulls the latest prompts, framework doc, and bibliography from the Flow repo via
GitHub API. Inserts CC BY 4.0 attribution headers. Writes to `skills/seo-flow/references/`.

**CLI interface:**
```bash
python scripts/sync_flow.py              # sync all, write to disk
python scripts/sync_flow.py --dry-run    # show what would change, no writes
python scripts/sync_flow.py --ref <sha>  # pin to a specific Flow commit
```

**Output:** JSON summary listing files added, updated, and unchanged.

**Triggered by:** `/seo flow sync` command and manually during claude-seo releases.

## 4. Modified files

All modifications are additive. No existing skill routing logic changes.

| File | Change | Lines added |
|---|---|---|
| `skills/seo/SKILL.md` | Add `seo-flow` entry to routing table | ~4 |
| `skills/seo-geo/SKILL.md` | Add cross-reference to Flow optimize prompts | ~2 |
| `skills/seo-local/SKILL.md` | Add cross-reference to Flow local prompts | ~2 |
| `skills/seo-content/SKILL.md` | Add cross-reference to Flow optimize/win prompts | ~2 |
| `skills/seo-cluster/SKILL.md` | Add cross-reference to Flow find prompts | ~2 |
| `.claude-plugin/plugin.json` | Version bump `1.9.0` → `1.9.5` | ~1 |
| `CONTRIBUTORS.md` | Credit Daniel Agrici / FLOW framework, CC BY 4.0 | ~3 |
| `README.md` | Add FLOW to Ecosystem table; add `sync_flow.py` to dev docs | ~5 |
| `CHANGELOG.md` | v1.9.5 release entry with FLOW integration notes | ~10 |

## 5. Orchestration layer

Work is split by type between Claude (main) and Codex (sub-agent via `openai-codex` plugin v1.0.4).

| Task | Agent | Boundary reason |
|---|---|---|
| Design and write `seo-flow` SKILL.md | Claude | Requires understanding existing skill routing architecture |
| Write cross-skill reference additions (5 files) | Claude | Context-sensitive — must match each skill's format/voice |
| Write `agents/seo-flow.md` | Claude | Agent contract design requires full system context |
| Version bump + CONTRIBUTORS.md + README | Claude | Project-level judgment calls |
| Review all Codex output | Claude | Hard gate — no merge without full line-by-line review |
| Download + format 42 prompt files from GitHub API | **Codex** | Mechanical file transformation, no architecture knowledge needed |
| Insert CC BY 4.0 attribution headers into 42 files | **Codex** | Templated string insertion across many files |
| Implement `scripts/sync_flow.py` | **Codex** | Python + GitHub API scripting — Codex strength |

**Sub-agent review protocol** (per user's stated requirements):
1. Codex output staged on a branch before any merge.
2. Claude reviews the full diff: do prompt files match the Flow source verbatim? Attribution headers
   present and correctly formatted on all 42? Does `sync_flow.py` use only real GitHub API
   endpoints (no invented methods)? Any scope drift (files modified outside the task boundary)?
3. Only after the review gate passes does the branch merge to main.
4. "Agents produce plausible code that quietly does the wrong thing." No skimming. Every file.

## 6. Scope of changes

- **New files:** ~47 (1 SKILL.md, 1 agent, 2 reference docs, 42 prompts + 1 prompt index, 1 script)
- **Modified files:** ~8 (all additive, avg < 5 lines each)
- **Largest single change:** `skills/seo-flow/SKILL.md` (~150 lines, new file)
- **No deletions**
- **No schema migrations, no DB changes, no API contract changes**
- **All within the 200-line ceiling per existing file**

## 7. License compliance

FLOW content is CC BY 4.0 (content) + MIT (scripts). Requirements:
- Attribution header on every bundled prompt file (automated by `sync_flow.py`)
- CONTRIBUTORS.md credit entry
- SKILL.md footer with attribution + canonical URL
- `README.md` Ecosystem table links to `github.com/AgriciDaniel/flow`
- Claude SEO's own MIT license is unaffected (applies to skill code, not bundled CC BY 4.0 content)

## 8. Rollback plan

`seo-flow` is additive. No existing skill logic changes. To revert:
1. Remove `seo-flow` entry from `skills/seo/SKILL.md` routing table
2. Delete `skills/seo-flow/` directory
3. Delete `agents/seo-flow.md`
4. Remove the 5 cross-reference additions from existing skills
5. Revert `plugin.json` version to `1.9.0`

No redeploy of infrastructure. No migration needed. Time to rollback: < 5 minutes.

## 9. What this is not

- Not a full port of Flow's 72-doc corpus into claude-seo
- Not a dependency on Flow being online (prompts are bundled locally)
- Not a change to any existing skill's analysis logic
- Not a replacement for the canonical Flow repo, which remains authoritative for the full knowledge base

## 10. Next step

Invoke `superpowers:writing-plans` to produce the implementation plan.
