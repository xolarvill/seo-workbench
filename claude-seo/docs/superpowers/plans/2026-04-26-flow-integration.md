# FLOW Framework Integration (v1.9.5) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Integrate FLOW's 42 AI prompts + framework doc into Claude SEO as the `seo-flow` skill, wiring it into the main orchestrator and 4 cross-referenced skills.

**Architecture:** New `skills/seo-flow/` skill exposes the FLOW prompt library (Find → Leverage → Optimize → Win loop) via `/seo flow`. A companion `agents/seo-flow.md` handles URL-targeted analysis. `scripts/sync_flow.py` (Codex-written, Claude-reviewed) fetches all 42 prompts from the Flow repo with CC BY 4.0 attribution headers. All other changes are additive cross-references — no existing skill logic is altered.

**Tech Stack:** Python 3.10+, GitHub REST API v3, `gh` CLI (authenticated requests), stdlib only (`base64`, `argparse`, `pathlib`, `json`, `urllib.request`, `subprocess`)

**Orchestration split:** Claude writes all skill/agent/project files. Codex writes `sync_flow.py`. Claude reviews Codex output line-by-line before any execution. The sync script populates the 42 prompt files when run.

---

## File Map

| Action | Path | Owner |
|--------|------|-------|
| Create | `skills/seo-flow/SKILL.md` | Claude |
| Create | `agents/seo-flow.md` | Claude |
| Create | `scripts/sync_flow.py` | Codex (reviewed by Claude) |
| Create (via sync) | `skills/seo-flow/references/flow-framework.md` | `sync_flow.py` |
| Create (via sync) | `skills/seo-flow/references/bibliography.md` | `sync_flow.py` |
| Create (via sync) | `skills/seo-flow/references/prompts/README.md` | `sync_flow.py` |
| Create (via sync) | `skills/seo-flow/references/prompts/find/*.md` (5) | `sync_flow.py` |
| Create (via sync) | `skills/seo-flow/references/prompts/leverage/*.md` (1) | `sync_flow.py` |
| Create (via sync) | `skills/seo-flow/references/prompts/optimize/*.md` (18) | `sync_flow.py` |
| Create (via sync) | `skills/seo-flow/references/prompts/win/*.md` (3) | `sync_flow.py` |
| Create (via sync) | `skills/seo-flow/references/prompts/local/*.md` (8) | `sync_flow.py` |
| Create | `tests/test_sync_flow.py` | Claude (TDD gate) |
| Modify | `skills/seo/SKILL.md` | Claude |
| Modify | `skills/seo-geo/SKILL.md` | Claude |
| Modify | `skills/seo-local/SKILL.md` | Claude |
| Modify | `skills/seo-content/SKILL.md` | Claude |
| Modify | `skills/seo-cluster/SKILL.md` | Claude |
| Modify | `.claude-plugin/plugin.json` | Claude |
| Modify | `CONTRIBUTORS.md` | Claude |
| Modify | `README.md` | Claude |
| Modify | `CLAUDE.md` | Claude |
| Modify | `CHANGELOG.md` | Claude |

---

## Task 1: Create directory skeleton

**Files:**
- Create: `skills/seo-flow/references/prompts/find/`
- Create: `skills/seo-flow/references/prompts/leverage/`
- Create: `skills/seo-flow/references/prompts/optimize/`
- Create: `skills/seo-flow/references/prompts/win/`
- Create: `skills/seo-flow/references/prompts/local/`
- Create: `tests/`

- [ ] **Step 1.1: Create directories**

```bash
mkdir -p skills/seo-flow/references/prompts/{find,leverage,optimize,win,local}
mkdir -p tests
```

Expected: No output. Exit code 0.

- [ ] **Step 1.2: Verify structure**

```bash
find skills/seo-flow -type d | sort
```

Expected:
```
skills/seo-flow
skills/seo-flow/references
skills/seo-flow/references/prompts
skills/seo-flow/references/prompts/find
skills/seo-flow/references/prompts/leverage
skills/seo-flow/references/prompts/local
skills/seo-flow/references/prompts/optimize
skills/seo-flow/references/prompts/win
```

Note: Git does not track empty directories. The first commit for `skills/seo-flow/` happens in Task 2 when `SKILL.md` is added.

---

## Task 2: Write `skills/seo-flow/SKILL.md`

**Files:**
- Create: `skills/seo-flow/SKILL.md`

- [ ] **Step 2.1: Write SKILL.md**

Create `skills/seo-flow/SKILL.md` with this exact content:

```markdown
---
name: seo-flow
description: >
  FLOW framework integration — evidence-led SEO using the Find → Leverage →
  Optimize → Win loop. Surfaces stage-specific AI prompts from the FLOW
  knowledge base (42 prompts, CC BY 4.0). Use when user says "FLOW", "FLOW
  framework", "seo flow", "evidence-led SEO", "find leverage optimize win",
  or wants stage-specific SEO prompts.
user-invokable: true
argument-hint: "[stage] [url|topic]"
license: MIT
metadata:
  author: AgriciDaniel
  version: "1.9.5"
  category: seo
---

# FLOW Framework — Find · Leverage · Optimize · Win

> Framework and prompts © Daniel Agrici, CC BY 4.0 — github.com/AgriciDaniel/flow

FLOW is an evidence-led SEO operating model built for the AI-search era. Claude SEO
integrates the FLOW prompt library (42 prompts across 5 stages) so every analysis can
be driven by structured, evidence-backed AI prompts rather than improvised queries.

**Runtime context:** Load `references/flow-framework.md` on every `/seo flow` activation.
Load prompt files on demand — only for the stage the user requests.

---

## Commands

| Command | What it does |
|---------|-------------|
| `/seo flow` | Show FLOW overview + stage menu |
| `/seo flow find [url\|topic]` | Find-stage: keyword research, gap analysis, SERP intent mapping (5 prompts) |
| `/seo flow leverage [url]` | Leverage-stage: backlink strategy, off-site authority (1 prompt) |
| `/seo flow optimize [url]` | Optimize-stage: select 2-3 most relevant of 18 prompts based on context |
| `/seo flow win [url]` | Win-stage: BOFU, conversion rate, dual-surface scorecard (3 prompts) |
| `/seo flow local [url]` | Local-stage: GBP optimization, meta, title tags, local audits (8 prompts) |
| `/seo flow prompts` | Full index of all 42 prompts — stage, name, trigger conditions |
| `/seo flow sync` | Pull latest prompt files from github.com/AgriciDaniel/flow |

---

## Orchestration Logic

### On `/seo flow` (no sub-command)
1. Read `references/flow-framework.md`
2. Show the FLOW stage overview with a one-line description of each stage
3. Ask: which stage matches the user's current situation?

### On `/seo flow find [url|topic]`
1. Read all files in `references/prompts/find/`
2. Apply each prompt to the URL or topic
3. Cross-reference: "For deeper SERP clustering, see `/seo cluster <seed-keyword>`"

### On `/seo flow leverage [url]`
1. Read the file in `references/prompts/leverage/`
2. Apply to the URL's current backlink context
3. Cross-reference: "For raw backlink data, see `/seo backlinks <url>`"

### On `/seo flow optimize [url]`
1. Read all file names in `references/prompts/optimize/`
2. Read prior analysis context (URL, industry vertical, any prior skill output in conversation)
3. Select 2-3 most relevant prompts; load only those files
4. Apply selected prompts; note the others are accessible via `/seo flow prompts`
5. Cross-reference: "For full content quality analysis, see `/seo content <url>` and `/seo geo <url>`"

### On `/seo flow win [url]`
1. Read all files in `references/prompts/win/`
2. Apply each prompt to the URL's conversion and BOFU context
3. Cross-reference: "For SXO persona scoring, see `/seo sxo <url>`"

### On `/seo flow local [url]`
1. Read all files in `references/prompts/local/`
2. Apply to the URL's local SEO context
3. Cross-reference: "For full local SEO analysis, see `/seo local <url>` and `/seo maps [command]`"

### On `/seo flow prompts`
1. Read `references/prompts/README.md`
2. Display the full index: all 42 prompts with stage, name, trigger conditions

### On `/seo flow sync`
1. Run: `python scripts/sync_flow.py`
2. Display the JSON summary (files added, updated, unchanged)
3. Show attribution notice after sync completes

---

## Context Matching (Optimize stage)

The optimize stage has 18 prompts. Dumping all 18 is noise. Select by priority:

1. **Industry vertical** (SaaS → on-page + technical; local → citations + GBP; publisher → E-E-A-T + freshness)
2. **Prior skill output** (seo-technical flagged crawl issues → technical optimize prompts; seo-content flagged E-E-A-T gaps → content optimize prompts)
3. **URL signals** (product pages → conversion; blog → freshness + authority)

Always surface exactly 2-3 prompts. State which prompts you chose and why.

---

## Reference Files

Load on-demand — do NOT load all at startup:
- `references/flow-framework.md` — FLOW operating model (load on every `/seo flow` activation)
- `references/bibliography.md` — Evidence sources; load when citing studies or statistics
- `references/prompts/README.md` — Prompt index; load for `/seo flow prompts`
- `references/prompts/find/` — 5 prompts; load for `/seo flow find`
- `references/prompts/leverage/` — 1 prompt; load for `/seo flow leverage`
- `references/prompts/optimize/` — 18 prompts; load selectively for `/seo flow optimize`
- `references/prompts/win/` — 3 prompts; load for `/seo flow win`
- `references/prompts/local/` — 8 prompts; load for `/seo flow local`

---

## Attribution

Every `/seo flow` activation (any sub-command) outputs before analysis:

```
Framework and prompts © Daniel Agrici, CC BY 4.0 — github.com/AgriciDaniel/flow
```

Do not omit or modify the attribution.

---

## Error Handling

| Scenario | Action |
|----------|--------|
| `references/flow-framework.md` missing | "FLOW reference files not synced. Run: `/seo flow sync`" |
| Prompt file missing | "Run `/seo flow sync` to pull the latest prompts from the FLOW repo." |
| `sync_flow.py` network error | Display the script's stderr. Check rate limits: `gh api rate_limit`. |
| `sync_flow.py` auth error | Run `gh auth login` then retry. |
```

- [ ] **Step 2.2: Verify line count is under 200**

```bash
wc -l skills/seo-flow/SKILL.md
```

Expected: fewer than 200 lines.

- [ ] **Step 2.3: Commit**

```bash
git add skills/seo-flow/SKILL.md
git commit -m "feat: add skills/seo-flow/SKILL.md — FLOW framework entry-point skill"
```

---

## Task 3: Write `agents/seo-flow.md`

**Files:**
- Create: `agents/seo-flow.md`

- [ ] **Step 3.1: Write agent file**

Create `agents/seo-flow.md` with this exact content:

```markdown
---
name: seo-flow
description: FLOW framework prompt analyst. Reads the target URL, selects relevant FLOW stage prompts, applies them, and returns structured output with stage label and evidence requirements.
model: sonnet
maxTurns: 15
tools: Read, Bash, WebFetch, Glob, Grep
---

You are a FLOW framework SEO analyst. You apply evidence-led FLOW prompts to a target URL.

When given a URL and a FLOW stage (find, leverage, optimize, win, or local):

1. Fetch the target URL with WebFetch to understand the page content and industry signals
2. Read the relevant prompt files from `skills/seo-flow/references/prompts/{stage}/`
3. For the optimize stage: read all file names in `prompts/optimize/` first, then select 2-3 most relevant based on:
   - Industry vertical signals from the fetched page
   - Content gaps visible on the page
   - Technical or authority issues detected
4. Apply each selected prompt to the page content — fill in the prompt for this specific site
5. Return structured output with:
   - Stage label (FIND / LEVERAGE / OPTIMIZE / WIN / LOCAL)
   - Prompts applied (file names + one-line rationale for each selection)
   - Per-prompt findings (structured, evidence-tagged)
   - Evidence requirements: what data would validate or strengthen each finding

## Output Format

```
# FLOW Analysis: {STAGE} — {domain}

> Framework and prompts © Daniel Agrici, CC BY 4.0 — github.com/AgriciDaniel/flow

## Prompts Applied
- {prompt-filename}: {one-line rationale}

## Findings

### {Prompt Name}
[Findings for this prompt applied to the target URL]

**Evidence needed:** [Specific data sources that would validate these findings]
```

## Rules

- Always output the attribution line before any analysis output
- Apply at most 5 prompts per call (context window constraint)
- For optimize stage: never load all 18 at once; select based on page signals
- If the URL is unreachable, report the error then list the prompts you would have applied
```

- [ ] **Step 3.2: Commit**

```bash
git add agents/seo-flow.md
git commit -m "feat: add agents/seo-flow.md — FLOW prompt analyst subagent"
```

---

## Task 4: Write failing test for `sync_flow.py` (TDD)

**Files:**
- Create: `tests/test_sync_flow.py`

- [ ] **Step 4.1: Write test file**

Create `tests/test_sync_flow.py`:

```python
"""Tests for scripts/sync_flow.py"""

import json
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).parents[1]
SCRIPT = REPO_ROOT / "scripts" / "sync_flow.py"
REF_DIR = REPO_ROOT / "skills" / "seo-flow" / "references"


def test_dry_run_exits_zero():
    result = subprocess.run(
        [sys.executable, str(SCRIPT), "--dry-run"],
        capture_output=True, text=True, cwd=REPO_ROOT
    )
    assert result.returncode == 0, f"Dry run failed:\n{result.stderr}"


def test_dry_run_produces_valid_json():
    result = subprocess.run(
        [sys.executable, str(SCRIPT), "--dry-run"],
        capture_output=True, text=True, cwd=REPO_ROOT
    )
    assert result.returncode == 0, f"Dry run failed:\n{result.stderr}"
    data = json.loads(result.stdout)
    assert "added" in data, "JSON missing 'added' key"
    assert "updated" in data, "JSON missing 'updated' key"
    assert "unchanged" in data, "JSON missing 'unchanged' key"


def test_dry_run_does_not_write_files():
    files_before = set(REF_DIR.rglob("*.md"))
    subprocess.run(
        [sys.executable, str(SCRIPT), "--dry-run"],
        capture_output=True, cwd=REPO_ROOT
    )
    files_after = set(REF_DIR.rglob("*.md"))
    assert files_before == files_after, (
        f"Dry run created unexpected files: {files_after - files_before}"
    )


def test_real_sync_produces_42_prompts():
    """After a real sync, all 42 prompt files must be present."""
    prompts_dir = REF_DIR / "prompts"
    if not prompts_dir.exists():
        return  # sync not yet run — skip silently

    prompt_files = [
        f for f in prompts_dir.rglob("*.md") if f.name != "README.md"
    ]
    assert len(prompt_files) == 42, (
        f"Expected 42 prompt files, found {len(prompt_files)}:\n"
        + "\n".join(str(f.relative_to(REPO_ROOT)) for f in sorted(prompt_files))
    )


def test_synced_files_have_attribution_headers():
    """Every synced prompt file must start with the CC BY 4.0 attribution comment."""
    prompts_dir = REF_DIR / "prompts"
    if not prompts_dir.exists():
        return  # sync not yet run — skip silently

    attribution_prefix = "<!-- Source: github.com/AgriciDaniel/flow"
    failures = []
    for md_file in prompts_dir.rglob("*.md"):
        if md_file.name == "README.md":
            continue
        content = md_file.read_text(encoding="utf-8")
        if not content.startswith(attribution_prefix):
            failures.append(str(md_file.relative_to(REPO_ROOT)))

    assert not failures, (
        "Files missing attribution headers:\n" + "\n".join(failures)
    )
```

- [ ] **Step 4.2: Run test — confirm it fails because script doesn't exist yet**

```bash
python -m pytest tests/test_sync_flow.py -v 2>&1 | head -25
```

Expected: `test_dry_run_exits_zero`, `test_dry_run_produces_valid_json`, and `test_dry_run_does_not_write_files` fail with `FileNotFoundError` or similar. `test_real_sync_produces_42_prompts` and `test_synced_files_have_attribution_headers` pass (they return early when `prompts/` doesn't exist).

- [ ] **Step 4.3: Commit test file**

```bash
git add tests/test_sync_flow.py
git commit -m "test: add sync_flow.py test suite (TDD — dry-run tests fail until script written)"
```

---

## Task 5: Delegate `scripts/sync_flow.py` to Codex

**Files:**
- Create: `scripts/sync_flow.py` (Codex-written, Claude-reviewed before use)

- [ ] **Step 5.1: Invoke Codex sub-agent**

Use the Agent tool with `subagent_type: "codex:codex-rescue"` and this exact task prompt (pass verbatim):

```
Write scripts/sync_flow.py in the claude-seo repository.

WHAT THE SCRIPT DOES:
Fetches the operational layer of the Flow SEO repo (github.com/AgriciDaniel/flow)
via GitHub REST API v3 and writes synced files to skills/seo-flow/references/.

FILES TO SYNC:
- docs/01-framework/flow-framework.md  →  skills/seo-flow/references/flow-framework.md
- docs/10-references/bibliography.md  →  skills/seo-flow/references/bibliography.md
- All .md files in docs/09-prompts/find/      →  skills/seo-flow/references/prompts/find/
- All .md files in docs/09-prompts/leverage/  →  skills/seo-flow/references/prompts/leverage/
- All .md files in docs/09-prompts/optimize/  →  skills/seo-flow/references/prompts/optimize/
- All .md files in docs/09-prompts/win/       →  skills/seo-flow/references/prompts/win/
- All .md files in docs/09-prompts/local/     →  skills/seo-flow/references/prompts/local/

ATTRIBUTION HEADER:
Insert this as the very first line of every synced .md file (before existing content):
<!-- Source: github.com/AgriciDaniel/flow | License: CC BY 4.0 | Synced: YYYY-MM-DD -->
Replace YYYY-MM-DD with today's date at sync time.

GENERATE PROMPT INDEX:
After syncing all prompts, write skills/seo-flow/references/prompts/README.md.
Content: a markdown table with columns: Stage | Filename | Title | Description
Extract Title from frontmatter `title:` field (or first H1 if no frontmatter).
Extract Description from frontmatter `description:` field (or first non-heading line).

GITHUB API:
Use only real GitHub REST API v3 endpoints:
  GET https://api.github.com/repos/AgriciDaniel/flow/contents/{path}
  Listing a directory returns a JSON array; fetching a file returns base64 `content` field.

Authentication via gh CLI:
  import subprocess
  result = subprocess.run(["gh", "auth", "token"], capture_output=True, text=True)
  token = result.stdout.strip()
  headers = {
      "Authorization": f"Bearer {token}",
      "Accept": "application/vnd.github+json",
      "X-GitHub-Api-Version": "2022-11-28"
  }

Use urllib.request for HTTP — no third-party packages.

CLI INTERFACE:
  python scripts/sync_flow.py              # sync all, write to disk
  python scripts/sync_flow.py --dry-run    # show what would change, no writes
  python scripts/sync_flow.py --ref <sha>  # pin to a specific Flow commit

For --ref: append ?ref=<sha> to all GitHub API content URLs.

OUTPUT:
  stdout: single JSON object — {"added": [...], "updated": [...], "unchanged": [...]}
  stderr: per-file progress lines (all progress must go to stderr, not stdout)

CONSTRAINTS:
- Stdlib only: base64, argparse, pathlib, json, urllib.request, subprocess, datetime
- No requests, no httpx, no third-party packages
- Use os.path.dirname(os.path.abspath(__file__)) to locate the repo root — no hardcoded paths
- Module docstring at top. --help describes all three modes.
- Single file, under 200 lines.
```

- [ ] **Step 5.2: Wait for Codex to write the file**

Do not proceed to Task 6 until Codex has written `scripts/sync_flow.py`. The file must exist before review.

---

## Task 6: Review Codex output — hard gate

**Mandatory review. Do not run the script or proceed to Task 7 without passing every check.**

- [ ] **Step 6.1: Read the full script — every line**

```bash
cat -n scripts/sync_flow.py
```

Read completely. Do not skim.

- [ ] **Step 6.2: Verify GitHub API endpoints are real**

```bash
grep -n "api.github.com" scripts/sync_flow.py
```

Expected: only `https://api.github.com/repos/AgriciDaniel/flow/contents/...` patterns.
Reject if: invented method names, non-GitHub domains, hardcoded tokens, or `requests`/`httpx` imports.

- [ ] **Step 6.3: Verify attribution header insertion**

```bash
grep -n "CC BY 4.0\|Synced:" scripts/sync_flow.py
```

Expected: the string `<!-- Source: github.com/AgriciDaniel/flow | License: CC BY 4.0 | Synced:` appears in the script.
Reject if: attribution is missing or is inserted anywhere other than line 1 of each file.

- [ ] **Step 6.4: Verify no hardcoded home paths**

```bash
grep -n "/home/" scripts/sync_flow.py
```

Expected: no output.

- [ ] **Step 6.5: Verify all writes target skills/seo-flow/references/**

```bash
grep -n "\.write\|open(" scripts/sync_flow.py
```

Confirm: every file write path is under `skills/seo-flow/references/`. Reject if the script writes to any other path.

- [ ] **Step 6.6: Verify --dry-run gates all writes**

```bash
grep -n "dry.run\|dry_run" scripts/sync_flow.py
```

Expected: `--dry-run` flag exists and every file write is gated behind `if not dry_run:` (or equivalent).

- [ ] **Step 6.7: Verify --ref flag is implemented**

```bash
grep -n "\-\-ref\|\\?ref=" scripts/sync_flow.py
```

Expected: `--ref` arg exists and the SHA is appended as `?ref=<sha>` on GitHub API URLs.

- [ ] **Step 6.8: Verify stdout is clean JSON only**

```bash
grep -n "^.*print(" scripts/sync_flow.py
```

Confirm: all progress/status messages use `print(..., file=sys.stderr)`. Only the final JSON goes to stdout (no stray `print()` calls without `file=sys.stderr`).

- [ ] **Step 6.9: Verify prompts/README.md generation is present**

```bash
grep -n "README" scripts/sync_flow.py
```

Expected: logic to write `prompts/README.md` (the prompt index) is present.

- [ ] **Step 6.10: If any check fails, request a fix**

Use Agent with `subagent_type: "codex:codex-rescue"` and `--resume` in the task text to fix the specific issue. Re-run all checks from Step 6.2 after any fix. Do not continue until all checks pass.

- [ ] **Step 6.11: Commit after passing all checks**

```bash
git add scripts/sync_flow.py
git commit -m "feat: add scripts/sync_flow.py — GitHub API sync for FLOW prompt library (Codex, reviewed)"
```

---

## Task 7: Run tests — confirm dry-run tests pass

- [ ] **Step 7.1: Run dry-run tests**

```bash
python -m pytest tests/test_sync_flow.py::test_dry_run_exits_zero \
  tests/test_sync_flow.py::test_dry_run_produces_valid_json \
  tests/test_sync_flow.py::test_dry_run_does_not_write_files -v
```

Expected:
```
PASSED tests/test_sync_flow.py::test_dry_run_exits_zero
PASSED tests/test_sync_flow.py::test_dry_run_produces_valid_json
PASSED tests/test_sync_flow.py::test_dry_run_does_not_write_files
```

If any test fails: read the failure message, fix `scripts/sync_flow.py`, re-run Task 6 checks for the changed section, then re-run this step.

---

## Task 8: Run sync to populate reference files

- [ ] **Step 8.1: Run the sync script**

```bash
python scripts/sync_flow.py
```

Expected: JSON object on stdout listing added files. Progress on stderr. Exit code 0.

- [ ] **Step 8.2: Run full test suite**

```bash
python -m pytest tests/test_sync_flow.py -v
```

Expected: all 5 tests PASS.

- [ ] **Step 8.3: Commit reference files**

```bash
git add skills/seo-flow/references/
git commit -m "feat: sync FLOW reference files (42 prompts + framework + bibliography, CC BY 4.0)"
```

---

## Task 9: Verify sync output

- [ ] **Step 9.1: Count prompt files**

```bash
find skills/seo-flow/references/prompts -name "*.md" ! -name "README.md" | wc -l
```

Expected: `42`

- [ ] **Step 9.2: Verify per-stage counts**

```bash
for stage in find leverage optimize win local; do
  count=$(find skills/seo-flow/references/prompts/$stage -name "*.md" | wc -l)
  echo "$stage: $count"
done
```

Expected:
```
find: 5
leverage: 1
optimize: 18
win: 3
local: 8
```

- [ ] **Step 9.3: Spot-check attribution headers**

```bash
for stage in find leverage optimize win local; do
  first=$(find skills/seo-flow/references/prompts/$stage -name "*.md" | head -1)
  echo "=== $first ==="
  head -1 "$first"
done
```

Expected: every file starts with `<!-- Source: github.com/AgriciDaniel/flow | License: CC BY 4.0 | Synced:`.

- [ ] **Step 9.4: Verify framework and bibliography exist and are non-empty**

```bash
ls -lh skills/seo-flow/references/flow-framework.md skills/seo-flow/references/bibliography.md
```

Expected: both files exist with size > 0.

- [ ] **Step 9.5: Verify prompts/README.md index exists**

```bash
wc -l skills/seo-flow/references/prompts/README.md
```

Expected: more than 40 lines (42 prompts + table header rows).

---

## Task 10: Modify `skills/seo/SKILL.md`

**Files:**
- Modify: `skills/seo/SKILL.md` (Quick Reference table + Sub-Skills list — additive only)

- [ ] **Step 10.1: Add seo-flow row to Quick Reference table**

In `skills/seo/SKILL.md`, find the Quick Reference table. The last row is:
```
| `/seo image-gen [use-case] <description>` | AI image generation for SEO assets (extension) |
```

Insert this row immediately after it:
```
| `/seo flow [stage] [url\|topic]` | FLOW framework: evidence-led prompts for Find, Leverage, Optimize, Win, or Local stages |
```

- [ ] **Step 10.2: Add seo-flow to Sub-Skills list**

In `skills/seo/SKILL.md`, find the Sub-Skills list. The last entry is:
```
23. **seo-image-gen** -- AI image generation for SEO assets via Gemini (extension)
```

Append after it:
```
24. **seo-flow** -- FLOW framework integration (Find → Leverage → Optimize → Win, 42 AI prompts, CC BY 4.0)
```

- [ ] **Step 10.3: Verify only additions**

```bash
git diff skills/seo/SKILL.md | grep "^-" | grep -v "^---"
```

Expected: no output (no deletions).

- [ ] **Step 10.4: Commit**

```bash
git add skills/seo/SKILL.md
git commit -m "feat: add seo-flow to skills/seo/SKILL.md routing table and sub-skills list"
```

---

## Task 11: Add FLOW cross-references to 4 existing skills

**Files:**
- Modify: `skills/seo-geo/SKILL.md`
- Modify: `skills/seo-local/SKILL.md`
- Modify: `skills/seo-content/SKILL.md`
- Modify: `skills/seo-cluster/SKILL.md`

Each skill gets a 4-line section appended at the end.

- [ ] **Step 11.1: Append to `skills/seo-geo/SKILL.md`**

```bash
cat >> skills/seo-geo/SKILL.md << 'EOF'

## FLOW Framework Integration

For prompt-guided AI content optimization, use `/seo flow optimize <url>` — FLOW's 18 optimize-stage prompts complement GEO's citability and structure analysis with evidence-led AI prompts.
EOF
```

- [ ] **Step 11.2: Append to `skills/seo-local/SKILL.md`**

```bash
cat >> skills/seo-local/SKILL.md << 'EOF'

## FLOW Framework Integration

For prompt-guided local optimization, use `/seo flow local <url>` — FLOW's 8 local-stage prompts cover GBP optimization, meta descriptions, title tags, and structured local audit workflows.
EOF
```

- [ ] **Step 11.3: Append to `skills/seo-content/SKILL.md`**

```bash
cat >> skills/seo-content/SKILL.md << 'EOF'

## FLOW Framework Integration

For prompt-guided content optimization, use `/seo flow optimize <url>` and `/seo flow win <url>` — FLOW's optimize and win prompts provide structured E-E-A-T improvement and BOFU conversion workflows.
EOF
```

- [ ] **Step 11.4: Append to `skills/seo-cluster/SKILL.md`**

```bash
cat >> skills/seo-cluster/SKILL.md << 'EOF'

## FLOW Framework Integration

For prompt-guided keyword research and gap analysis, use `/seo flow find [url|topic]` — FLOW's 5 find-stage prompts complement the SERP-overlap clustering methodology with structured discovery prompts.
EOF
```

- [ ] **Step 11.5: Verify no deletions in any of the 4 files**

```bash
git diff skills/seo-geo/SKILL.md skills/seo-local/SKILL.md skills/seo-content/SKILL.md skills/seo-cluster/SKILL.md | grep "^-" | grep -v "^---"
```

Expected: no output.

- [ ] **Step 11.6: Commit**

```bash
git add skills/seo-geo/SKILL.md skills/seo-local/SKILL.md skills/seo-content/SKILL.md skills/seo-cluster/SKILL.md
git commit -m "feat: add FLOW framework cross-references to seo-geo, seo-local, seo-content, seo-cluster"
```

---

## Task 12: Project-level file updates

**Files:**
- Modify: `.claude-plugin/plugin.json`
- Modify: `CONTRIBUTORS.md`
- Modify: `README.md`
- Modify: `CLAUDE.md`
- Modify: `CHANGELOG.md`

- [ ] **Step 12.1: Version bump in plugin.json**

In `.claude-plugin/plugin.json`, change `"version": "1.9.0"` to `"version": "1.9.5"`.

Verify:
```bash
grep '"version"' .claude-plugin/plugin.json
```
Expected: `"version": "1.9.5"`

- [ ] **Step 12.2: Commit plugin.json**

```bash
git add .claude-plugin/plugin.json
git commit -m "chore: bump version 1.9.0 → 1.9.5 in plugin.json"
```

- [ ] **Step 12.3: Add FLOW credit to CONTRIBUTORS.md**

In `CONTRIBUTORS.md`, find the line `## Community Pull Requests`. Insert this block immediately before it (after the v1.9.0 table block):

```markdown

## Framework Integration (v1.9.5)

| Source | Type | License | Integrated As |
|--------|------|---------|--------------|
| **[FLOW](https://github.com/AgriciDaniel/flow)** — Daniel Agrici | 42 AI prompts + framework doc + bibliography | CC BY 4.0 | `seo-flow` skill + `skills/seo-flow/references/` |

Attribution header on every bundled prompt file (automated by `scripts/sync_flow.py`).
```

- [ ] **Step 12.4: Commit CONTRIBUTORS.md**

```bash
git add CONTRIBUTORS.md
git commit -m "docs: credit FLOW framework integration in CONTRIBUTORS.md"
```

- [ ] **Step 12.5: Add FLOW to README.md Ecosystem table**

In `README.md`, find the Ecosystem table (around line 379). The table has 4 rows. Add this row after the last row (`AI Marketing Claude`):

```markdown
| [FLOW](https://github.com/AgriciDaniel/flow) | Evidence-led SEO framework (42 AI prompts, CC BY 4.0) | Knowledge base — powers `seo-flow` prompts |
```

- [ ] **Step 12.6: Commit README.md**

```bash
git add README.md
git commit -m "docs: add FLOW to README ecosystem table"
```

- [ ] **Step 12.7: Add sync_flow.py to CLAUDE.md scripts list**

In `CLAUDE.md` (the project CLAUDE.md at `/home/agricidaniel/Desktop/Claude-SEO/CLAUDE.md`), make two changes:

**Change 1** — Find the scripts directory comment line:
```
  scripts/                         # Python execution scripts (28 tracked + 2 dev-only)
```
Update the count:
```
  scripts/                         # Python execution scripts (29 tracked + 2 dev-only)
```

**Change 2** — Find the scripts list. The last tracked script is `dataforseo_normalize.py`. Add this entry immediately after it (before the `mobile_analysis.py` dev-only comment):
```
    sync_flow.py                         # FLOW prompt library sync (GitHub API, CC BY 4.0 headers, --dry-run, --ref)
```

- [ ] **Step 12.8: Commit CLAUDE.md**

```bash
git add CLAUDE.md
git commit -m "docs: add sync_flow.py to CLAUDE.md scripts list"
```

- [ ] **Step 12.9: Add CHANGELOG.md entry**

In `CHANGELOG.md`, find the line `## [1.9.0] - 2026-04-14`. Insert this block immediately before it:

```markdown
## [1.9.5] - 2026-04-26

### Added
- **seo-flow**: FLOW framework integration — Find → Leverage → Optimize → Win. 42 evidence-led AI prompts (CC BY 4.0) bundled as `skills/seo-flow/references/prompts/`. Commands: `/seo flow [find|leverage|optimize|win|local|prompts|sync]`.
- **Context-matching orchestration**: `/seo flow optimize` selects 2-3 most relevant prompts from 18 based on URL industry signals and prior skill output — not a full dump.
- **`scripts/sync_flow.py`**: GitHub API sync script — pulls latest FLOW prompts, framework doc, and bibliography from AgriciDaniel/flow. Supports `--dry-run` and `--ref <sha>` pinning. Outputs JSON summary.
- **`agents/seo-flow.md`**: FLOW subagent — applies stage prompts to target URLs, returns structured evidence-tagged findings.
- **FLOW cross-references**: Integration notes added to seo-geo, seo-local, seo-content, and seo-cluster skills.

### License
- FLOW content bundled under CC BY 4.0. Attribution header on every prompt file (automated by `sync_flow.py`). Claude SEO's MIT license unchanged — applies to skill code only.

```

- [ ] **Step 12.10: Commit CHANGELOG.md**

```bash
git add CHANGELOG.md
git commit -m "docs: add v1.9.5 FLOW integration entry to CHANGELOG.md"
```

---

## Task 13: Final integration check

- [ ] **Step 13.1: Run full test suite**

```bash
python -m pytest tests/test_sync_flow.py -v
```

Expected: 5/5 PASS.

- [ ] **Step 13.2: Verify complete file structure**

```bash
find skills/seo-flow -type f | sort
```

Expected: 1 (SKILL.md) + 2 (flow-framework.md, bibliography.md) + 1 (prompts/README.md) + 42 (prompts) = **46 files**.

- [ ] **Step 13.3: Verify version consistency**

```bash
grep '"version"' .claude-plugin/plugin.json
grep 'version:' skills/seo-flow/SKILL.md
grep '## \[1.9.5\]' CHANGELOG.md
```

Expected: all three show `1.9.5`.

- [ ] **Step 13.4: Verify attribution in SKILL.md**

```bash
grep "CC BY 4.0" skills/seo-flow/SKILL.md
```

Expected: at least 2 matches (attribution quote at top + Attribution section).

- [ ] **Step 13.5: Verify routing in skills/seo/SKILL.md**

```bash
grep -n "seo-flow\|seo flow" skills/seo/SKILL.md
```

Expected: at least 2 matches (Quick Reference row + Sub-Skills entry).

- [ ] **Step 13.6: Verify agents/seo-flow.md frontmatter**

```bash
head -8 agents/seo-flow.md
```

Expected:
```
---
name: seo-flow
description: FLOW framework prompt analyst. ...
model: sonnet
maxTurns: 15
tools: Read, Bash, WebFetch, Glob, Grep
---
```

- [ ] **Step 13.7: Final commit log review**

```bash
git log --oneline -15
```

Confirm the feature commits are all present: directories, SKILL.md, agent, tests, sync_flow.py, reference files, routing update, cross-references, version bump, CONTRIBUTORS, README, CLAUDE.md, CHANGELOG.

- [ ] **Step 13.8: Tag v1.9.5**

```bash
git tag v1.9.5
```

---

## Rollback

If any task fails unrecoverably and the feature must be reverted:

```bash
# Remove seo-flow from routing (revert the Task 10 commit)
git revert <task-10-commit-sha>

# Delete all new files
git rm -r skills/seo-flow/ agents/seo-flow.md scripts/sync_flow.py tests/test_sync_flow.py

# Revert cross-reference appends (revert Task 11 commit)
git revert <task-11-commit-sha>

# Revert version bump
# Edit .claude-plugin/plugin.json: "1.9.5" → "1.9.0"
git add .claude-plugin/plugin.json && git commit -m "chore: revert version to 1.9.0"
```

No infrastructure changes. No migrations. No schema changes. Time to full rollback: < 5 minutes.
