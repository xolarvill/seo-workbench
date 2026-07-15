from __future__ import annotations

from pathlib import Path
from typing import Any

from seo_workbench import state
from seo_workbench.workflow import load_workflow, output_for_step, skill_for_step


VALID_STEP_STATUSES = {"pending", "in_progress", "done"}


def _issue(severity: str, code: str, message: str, path: str = "") -> dict[str, str]:
    result = {"severity": severity, "code": code, "message": message}
    if path:
        result["path"] = path
    return result


def validate_state(data: dict[str, Any], project_dir: Path) -> list[dict[str, str]]:
    issues: list[dict[str, str]] = []
    project = data.get("project")
    if not isinstance(project, dict):
        issues.append(_issue("error", "state.project_missing", "state.project must be an object"))
        project = {}

    project_type = project.get("type", "")
    if project_type not in {"shopify", "shopify-headless", "general", "existing", ""}:
        issues.append(_issue("error", "state.project_type", f"unknown project type: {project_type}"))

    phases = data.get("phases")
    if not isinstance(phases, dict):
        issues.append(_issue("error", "state.phases_missing", "state.phases must be an object"))
        return issues

    phase_order = data.get("phaseOrder", [])
    if not isinstance(phase_order, list) or not phase_order:
        issues.append(_issue("error", "state.phase_order", "state.phaseOrder must be a non-empty list"))
        phase_order = []

    for phase in phase_order:
        if phase not in phases:
            issues.append(_issue("error", "state.phase_missing", f"phaseOrder references missing phase: {phase}"))

    for phase, phase_data in phases.items():
        steps = phase_data.get("steps") if isinstance(phase_data, dict) else None
        if not isinstance(steps, list):
            issues.append(_issue("error", "state.steps_missing", f"{phase}.steps must be a list"))
            continue
        seen: set[str] = set()
        for index, step in enumerate(steps):
            location = f"phases.{phase}.steps[{index}]"
            if not isinstance(step, dict):
                issues.append(_issue("error", "state.step_shape", f"{location} must be an object", location))
                continue
            step_id = step.get("id", "")
            if not step_id:
                issues.append(_issue("error", "state.step_id_missing", f"{location} is missing id", location))
            elif step_id in seen:
                issues.append(_issue("error", "state.step_id_duplicate", f"duplicate step id in {phase}: {step_id}", location))
            seen.add(step_id)
            status = step.get("status")
            if status not in VALID_STEP_STATUSES:
                issues.append(_issue("error", "state.step_status", f"{location} has invalid status: {status}", location))

    technical_steps = phases.get("TECHNICAL_AUDIT", {}).get("steps", [])
    headless = next((item for item in technical_steps if item.get("id") == "headless-precheck"), None)
    if project_type != "shopify-headless" and headless and headless.get("status") != "done":
        issues.append(
            _issue(
                "warning",
                "state.headless_gating",
                "non-headless projects should have TECHNICAL_AUDIT/headless-precheck marked done",
                "phases.TECHNICAL_AUDIT.steps.headless-precheck",
            )
        )

    for dirname in state.PROJECT_DIRS:
        try:
            runtime_dir = state.safe_project_path(project_dir, dirname)
        except ValueError as exc:
            issues.append(_issue("error", "project_dir.unsafe", str(exc), str(project_dir / dirname)))
            continue
        if not runtime_dir.exists():
            issues.append(_issue("warning", "project_dir.missing", f"missing runtime directory: {runtime_dir}"))
    return issues


def validate_workflow(workflow: dict[str, Any], data: dict[str, Any], project_dir: Path, workflow_path: Path) -> list[dict[str, str]]:
    issues: list[dict[str, str]] = []
    root = workflow_path.resolve().parent.parent
    skills = workflow.get("skills", {})
    if not isinstance(skills, dict):
        return [_issue("error", "workflow.skills_missing", "workflow.skills must be an object")]

    phases = data.get("phases", {})
    for phase, phase_data in phases.items():
        for step in phase_data.get("steps", []):
            step_id = step.get("id", "")
            if not step_id or phase == "INIT":
                continue
            skill = skill_for_step(workflow, phase, step_id)
            if not skill:
                issues.append(_issue("error", "workflow.skill_missing", f"no skill mapping for {phase}/{step_id}"))
            else:
                skill_path = root / skill
                if not skill_path.exists():
                    issues.append(_issue("error", "workflow.skill_path_missing", f"skill path does not exist: {skill}", skill))
            if phase != "CONTENT_PRODUCTION" and not output_for_step(phase, step_id, project_dir):
                issues.append(_issue("warning", "workflow.output_missing", f"no output contract for {phase}/{step_id}"))

    for key, skill in skills.items():
        skill_path = root / skill
        if not skill_path.exists():
            issues.append(_issue("error", "workflow.orphan_skill_path_missing", f"skill mapping {key} points to missing path: {skill}", skill))
    return issues


def validate_project(project_dir: Path, workflow_path: Path) -> dict[str, Any]:
    issues: list[dict[str, str]] = []
    state_path = state.state_path(project_dir)
    if not state_path.exists():
        issues.append(_issue("error", "state.not_found", f"{state_path} not found; run init first", str(state_path)))
        return {"ok": False, "issues": issues}

    try:
        data = state.read_json(state_path)
    except Exception as exc:
        issues.append(_issue("error", "state.invalid_json", str(exc), str(state_path)))
        return {"ok": False, "issues": issues}

    try:
        workflow = load_workflow(workflow_path)
    except Exception as exc:
        issues.append(_issue("error", "workflow.invalid_json", str(exc), str(workflow_path)))
        return {"ok": False, "issues": issues}

    issues.extend(validate_state(data, project_dir))
    issues.extend(validate_workflow(workflow, data, project_dir, workflow_path))
    return {"ok": not any(issue["severity"] == "error" for issue in issues), "issues": issues}
