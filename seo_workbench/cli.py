from __future__ import annotations

import argparse
import json
from pathlib import Path

from seo_workbench import state
from seo_workbench.audit_diff import AUDIT_KINDS, create_diff
from seo_workbench.doctor import run_doctor
from seo_workbench.evidence import collect_from_state
from seo_workbench.performance import collect_from_state as collect_performance_from_state
from seo_workbench.technology import collect_from_state as collect_technology_from_state
from seo_workbench.validation import validate_project
from seo_workbench.workflow import load_workflow, next_contract


def print_json(data: dict) -> None:
    print(json.dumps(data, ensure_ascii=False, indent=2))


def cmd_init(args: argparse.Namespace) -> int:
    platform = None
    if args.framework or args.hosting or args.cms:
        platform = {"framework": args.framework or "", "hosting": args.hosting or "", "cms": args.cms or ""}
    path = state.init_state(
        args.type,
        args.name,
        args.url,
        project_dir=args.project_dir,
        description=args.description or "",
        platform=platform,
        force=args.force,
    )
    print(path)
    return 0


def cmd_projects(args: argparse.Namespace) -> int:
    projects = state.discover_projects()
    if args.json_output:
        print_json({"ok": True, "count": len(projects), "projects": projects})
        return 0
    if not projects:
        print("no projects found")
        return 0
    for project in projects:
        if not project.get("selectable"):
            status = "non-selectable; use --project-dir"
        else:
            status = project.get("phase", "") if project.get("valid_state") else "invalid-state"
        print(f"{project['id']}: {project.get('name', '')} [{status}] {project.get('url', '')}")
    return 0


def cmd_status(args: argparse.Namespace) -> int:
    data = state.load_state(args.project_dir)
    phase, step = state.current_step(data)
    payload = {
        "ok": True,
        "project": data.get("project", {}),
        "phase": phase,
        "step": step,
        "next": data.get("nextAction") or "",
        "last": data.get("lastAction") or "",
    }
    if args.json_output:
        print_json(payload)
        return 0
    print(f"project: {data.get('project', {}).get('name', '')}")
    print(f"phase: {phase}")
    print(f"step: {step.get('id') if step else 'none'}")
    print(f"next: {data.get('nextAction') or ''}")
    return 0


def cmd_phase(args: argparse.Namespace) -> int:
    data = state.load_state(args.project_dir)
    state.set_phase(data, args.phase)
    state.save_state(data, args.project_dir)
    print(state.state_path(args.project_dir))
    return 0


def cmd_step(args: argparse.Namespace) -> int:
    data = state.load_state(args.project_dir)
    phase, step_id = state.update_step(data, args.action, args.step_id)
    state.save_state(data, args.project_dir)
    if args.json_output:
        print_json({"ok": True, "action": args.action, "phase": phase, "step": step_id})
        return 0
    print(f"{args.action}: {phase}/{step_id}")
    return 0


def cmd_next(args: argparse.Namespace) -> int:
    data = state.load_state(args.project_dir)
    phase, step = state.current_step(data)
    if not step:
        if args.json_output:
            print_json({"ok": True, "phase": phase, "step": None, "pending": False})
            return 0
        print(f"{phase}: no pending step")
        return 0
    contract = next_contract(load_workflow(args.workflow), phase, step, args.project_dir)
    if args.json_output:
        print_json({"ok": True, "pending": True, **contract})
        return 0
    print(f"{contract['phase']}/{contract['step']}: {contract['label']}")
    if contract["skill"]:
        print(f"skill: {contract['skill']}")
    if contract["context"]:
        print("context:")
        for path in contract["context"]:
            print(f"- {path}")
    if contract["output"]:
        print(f"output: {contract['output']}")
    print(f"after: python -m seo_workbench --project-dir {args.project_dir} step done")
    return 0


def cmd_evidence(args: argparse.Namespace) -> int:
    output_dir = args.output_dir or state.safe_project_path(args.project_dir, "audits/raw")
    if args.output_dir is None:
        state.safe_project_path(args.project_dir, "audits/rendered")
        state.safe_project_path(args.project_dir, "audits/technology")
        state.safe_project_path(args.project_dir, "audits/performance")
    path = collect_from_state(
        state.state_path(args.project_dir),
        args.timeout,
        args.sample_limit,
        output_dir,
        rendered=args.rendered,
        technology=args.technology,
        performance=args.performance,
        performance_runs=args.performance_runs,
        performance_form_factor=args.performance_form_factor,
    )
    if args.json_output:
        print_json(
            {
                "ok": True,
                "path": str(path),
                "rendered": args.rendered,
                "technology": args.technology,
                "performance": args.performance,
            }
        )
        return 0
    print(path)
    return 0


def cmd_technology(args: argparse.Namespace) -> int:
    output_dir = args.output_dir or state.safe_project_path(args.project_dir, "audits/technology")
    path = collect_technology_from_state(
        state.state_path(args.project_dir),
        args.timeout,
        output_dir,
        allow_private=args.allow_private,
    )
    report = json.loads(path.read_text(encoding="utf-8"))
    collection_status = report.get("collection_status", "failed")
    ok = collection_status != "failed"
    if args.json_output:
        print_json({"ok": ok, "path": str(path), "collection_status": collection_status})
        return 0 if ok else 1
    print(path)
    return 0 if ok else 1


def cmd_performance(args: argparse.Namespace) -> int:
    output_dir = args.output_dir or state.safe_project_path(args.project_dir, "audits/performance")
    path = collect_performance_from_state(
        state.state_path(args.project_dir),
        output_dir,
        runs=args.runs,
        form_factor=args.form_factor,
        timeout=args.timeout,
        allow_private=args.allow_private,
    )
    report = json.loads(path.read_text(encoding="utf-8"))
    collection_status = report.get("collection_status", "failed")
    ok = collection_status != "failed"
    if args.json_output:
        print_json(
            {
                "ok": ok,
                "path": str(path),
                "collection_status": collection_status,
                "performance_score": report.get("aggregate", {}).get("performance_score", {}),
                "high_variance": report.get("aggregate", {}).get("high_variance", False),
            }
        )
        return 0 if ok else 1
    print(path)
    return 0 if ok else 1


def cmd_audit_diff(args: argparse.Namespace) -> int:
    report, path = create_diff(
        args.project_dir,
        kind=args.kind,
        baseline_path=args.baseline_path,
        current_path=args.current_path,
    )
    ok = report["collection_status"] != "failed"
    if args.json_output:
        print_json(
            {
                "ok": ok,
                "path": str(path),
                "collection_status": report["collection_status"],
                "summary": report["summary"],
                "comparisons": {
                    kind: {"status": item["status"], "comparable": item["comparable"]}
                    for kind, item in report["comparisons"].items()
                },
            }
        )
        return 0 if ok else 1
    print(path)
    return 0 if ok else 1


def cmd_validate(args: argparse.Namespace) -> int:
    result = validate_project(args.project_dir, args.workflow)
    if args.json_output:
        print_json(result)
    else:
        print("ok" if result["ok"] else "failed")
        for issue in result["issues"]:
            print(f"{issue['severity']}: {issue['code']}: {issue['message']}")
    return 0 if result["ok"] else 1


def cmd_doctor(args: argparse.Namespace) -> int:
    result = run_doctor(args.project_dir, args.workflow)
    if args.json_output:
        print_json(result)
    else:
        print("ok" if result["ok"] else "attention needed")
        for check in result["checks"]:
            status = "ok" if check["ok"] else check["severity"]
            print(f"{status}: {check['name']} - {check['detail']}")
    return 0 if result["ok"] else 1


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="seo-workbench")
    project_group = parser.add_mutually_exclusive_group()
    project_group.add_argument("--project", help="Project id under projects/, for example wildone")
    project_group.add_argument("--project-dir", type=Path, help="Explicit project directory")
    parser.add_argument("--workflow", type=Path, default=None)
    sub = parser.add_subparsers(dest="command", required=True)

    projects = sub.add_parser("projects")
    projects.add_argument("--json", action="store_true", dest="json_output")
    projects.set_defaults(func=cmd_projects)

    init = sub.add_parser("init")
    init.add_argument("type", choices=["shopify", "shopify-headless", "general", "existing"])
    init.add_argument("--name", required=True)
    init.add_argument("--url", required=True)
    init.add_argument("--description")
    init.add_argument("--framework")
    init.add_argument("--hosting")
    init.add_argument("--cms")
    init.add_argument("--force", action="store_true")
    init.set_defaults(func=cmd_init)

    status = sub.add_parser("status")
    status.add_argument("--json", action="store_true", dest="json_output")
    status.set_defaults(func=cmd_status)

    phase = sub.add_parser("phase")
    phase.add_argument("phase")
    phase.set_defaults(func=cmd_phase)

    step = sub.add_parser("step")
    step.add_argument("action", choices=["done", "skip", "reset", "start"])
    step.add_argument("step_id", nargs="?")
    step.add_argument("--json", action="store_true", dest="json_output")
    step.set_defaults(func=cmd_step)

    next_cmd = sub.add_parser("next")
    next_cmd.add_argument("--json", action="store_true", dest="json_output")
    next_cmd.set_defaults(func=cmd_next)

    evidence = sub.add_parser("evidence")
    evidence.add_argument("--timeout", type=float, default=15)
    evidence.add_argument("--sample-limit", type=int, default=50)
    evidence.add_argument("--output-dir", type=Path)
    evidence.add_argument("--rendered", action="store_true")
    evidence.add_argument("--technology", action="store_true")
    evidence.add_argument("--performance", action="store_true")
    evidence.add_argument("--performance-runs", type=int, default=5)
    evidence.add_argument("--performance-form-factor", choices=["mobile", "desktop"], default="mobile")
    evidence.add_argument("--json", action="store_true", dest="json_output")
    evidence.set_defaults(func=cmd_evidence)

    technology = sub.add_parser("technology")
    technology.add_argument("--timeout", type=float, default=20)
    technology.add_argument("--output-dir", type=Path)
    technology.add_argument("--allow-private", action="store_true")
    technology.add_argument("--json", action="store_true", dest="json_output")
    technology.set_defaults(func=cmd_technology)

    performance = sub.add_parser("performance")
    performance.add_argument("--runs", type=int, default=5)
    performance.add_argument("--form-factor", choices=["mobile", "desktop"], default="mobile")
    performance.add_argument("--timeout", type=float, default=45)
    performance.add_argument("--output-dir", type=Path)
    performance.add_argument("--allow-private", action="store_true")
    performance.add_argument("--json", action="store_true", dest="json_output")
    performance.set_defaults(func=cmd_performance)

    audit_diff = sub.add_parser("audit-diff")
    audit_diff.add_argument("--kind", choices=["all", *AUDIT_KINDS], default="all")
    audit_diff.add_argument("--from", type=Path, dest="baseline_path")
    audit_diff.add_argument("--to", type=Path, dest="current_path")
    audit_diff.add_argument("--json", action="store_true", dest="json_output")
    audit_diff.set_defaults(func=cmd_audit_diff)

    validate = sub.add_parser("validate")
    validate.add_argument("--json", action="store_true", dest="json_output")
    validate.set_defaults(func=cmd_validate)

    doctor = sub.add_parser("doctor")
    doctor.add_argument("--json", action="store_true", dest="json_output")
    doctor.set_defaults(func=cmd_doctor)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        if args.project:
            args.project_dir = state.project_dir_from_id(args.project)
        elif args.project_dir is None:
            args.project_dir = state.project_dir_from_id("default")
        if args.workflow is None:
            from seo_workbench.workflow import DEFAULT_WORKFLOW

            args.workflow = DEFAULT_WORKFLOW
        return args.func(args)
    except (FileNotFoundError, FileExistsError, RuntimeError, ValueError) as exc:
        if getattr(args, "json_output", False):
            print_json({"ok": False, "error": str(exc)})
            return 1
        raise SystemExit(str(exc)) from exc


if __name__ == "__main__":
    raise SystemExit(main())
