from __future__ import annotations

import json
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parent.parent
DEFAULT_WORKFLOW = ROOT / "workflows" / "seo_full.json"


def load_workflow(path: Path = DEFAULT_WORKFLOW) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def skill_for_step(workflow: dict[str, Any], phase: str, step_id: str) -> str:
    skills = workflow.get("skills", {})
    return skills.get(step_id) or skills.get(f"{phase}:{step_id}") or skills.get(f"{phase}:dynamic", "")


def context_for_step(phase: str, step_id: str, project_dir: Path) -> list[str]:
    common = [str(project_dir / "state.json")]
    if phase == "INIT" and step_id == "config-brand-voice":
        return [
            *common,
            str(project_dir / "audits/raw/latest.json"),
            str(project_dir / "audits/rendered"),
            str(project_dir / "audits/technology/latest.json"),
        ]
    if phase == "INIT" and step_id == "config-target-keywords":
        return [
            *common,
            str(project_dir / "context/brand-voice.md"),
            str(project_dir / "audits/raw/latest.json"),
        ]
    if phase == "STRATEGY":
        return [*common, str(project_dir / "context/brand-voice.md"), str(project_dir / "context/target-keywords.md")]
    if phase == "CONTENT_PRODUCTION":
        return [*common, str(project_dir / "strategy/cluster-plan.md"), str(project_dir / "strategy/briefs")]
    if phase == "QUALITY_REVIEW":
        return [*common, str(project_dir / "content/drafts")]
    if phase == "TECHNICAL_AUDIT":
        return [
            *common,
            str(project_dir / "audits/raw/latest.json"),
            str(project_dir / "audits/rendered"),
            str(project_dir / "audits/technology/latest.json"),
            str(project_dir / "audits/performance/latest.json"),
            str(project_dir / "audits/diffs/latest.json"),
        ]
    if phase == "OFF_PAGE":
        return [*common, str(project_dir / "audits/technical-audit.md"), str(project_dir / "strategy/cluster-plan.md")]
    if phase == "MONITORING":
        return [
            *common,
            str(project_dir / "audits/raw/latest.json"),
            str(project_dir / "audits/performance/latest.json"),
            str(project_dir / "audits/diffs/latest.json"),
        ]
    return common


def output_for_step(phase: str, step_id: str, project_dir: Path) -> str:
    outputs = {
        "config-brand-voice": project_dir / "context/brand-voice.md",
        "config-target-keywords": project_dir / "context/target-keywords.md",
        "keyword-dive-product": project_dir / "strategy/keyword-dives/product-{keyword}.md",
        "keyword-dive-info": project_dir / "strategy/keyword-dives/info-{keyword}.md",
        "cluster-plan": project_dir / "strategy/cluster-plan.md",
        "content-briefs": project_dir / "strategy/briefs/{slug}.md",
        "page-audits": project_dir / "audits/page-audit-{slug}.md",
        "eeat-audit": project_dir / "audits/eeat-{slug}.md",
        "semantic-gap": project_dir / "audits/semantic-gap-{slug}.md",
        "headless-precheck": project_dir / "audits/headless-precheck.md",
        "technical-audit": project_dir / "audits/technical-audit.md",
        "schema": project_dir / "audits/schema-report.md",
        "sitemap": project_dir / "audits/sitemap-report.md",
        "images": project_dir / "audits/images-report.md",
        "drift-baseline": project_dir / "audits/drift-baseline.md",
        "linkbuilding-strategy": project_dir / "strategy/linkbuilding-plan.md",
        "backlinks-audit": project_dir / "audits/backlinks-report.md",
        "technical-recheck": project_dir / "audits/technical-recheck.md",
        "drift-compare": project_dir / "audits/drift-compare.md",
        "backlinks-recheck": project_dir / "audits/backlinks-recheck.md",
    }
    if phase == "CONTENT_PRODUCTION":
        return str(project_dir / "content/drafts/{slug}.md")
    return str(outputs[step_id]) if step_id in outputs else ""


def next_contract(workflow: dict[str, Any], phase: str, step: dict[str, Any], project_dir: Path = Path("projects/default")) -> dict[str, Any]:
    step_id = step.get("id", "")
    return {
        "phase": phase,
        "step": step_id,
        "label": step.get("label", ""),
        "skill": skill_for_step(workflow, phase, step_id),
        "context": context_for_step(phase, step_id, project_dir),
        "output": output_for_step(phase, step_id, project_dir),
    }


def _self_test() -> None:
    workflow = {"skills": {"x": "skills/x/SKILL.md"}}
    contract = next_contract(workflow, "STRATEGY", {"id": "x", "label": "X"}, Path("project"))
    assert contract["skill"] == "skills/x/SKILL.md"
    assert contract["output"] == ""
    assert "project/state.json" in contract["context"]
