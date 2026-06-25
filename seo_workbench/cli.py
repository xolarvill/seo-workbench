from __future__ import annotations

import argparse
from pathlib import Path

from seo_workbench import state
from seo_workbench.evidence import collect_from_state
from seo_workbench.workflow import load_workflow, next_contract


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


def cmd_status(args: argparse.Namespace) -> int:
    data = state.load_state(args.project_dir)
    phase, step = state.current_step(data)
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
    print(f"{args.action}: {phase}/{step_id}")
    return 0


def cmd_next(args: argparse.Namespace) -> int:
    data = state.load_state(args.project_dir)
    phase, step = state.current_step(data)
    if not step:
        print(f"{phase}: no pending step")
        return 0
    contract = next_contract(load_workflow(args.workflow), phase, step, args.project_dir)
    print(f"{contract['phase']}/{contract['step']}: {contract['label']}")
    if contract["skill"]:
        print(f"skill: {contract['skill']}")
    if contract["context"]:
        print("context:")
        for path in contract["context"]:
            print(f"- {path}")
    if contract["output"]:
        print(f"output: {contract['output']}")
    print("after: python -m seo_workbench step done")
    return 0


def cmd_evidence(args: argparse.Namespace) -> int:
    output_dir = args.output_dir or args.project_dir / "audits/raw"
    path = collect_from_state(state.state_path(args.project_dir), args.timeout, args.sample_limit, output_dir)
    print(path)
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="seo-workbench")
    parser.add_argument("--project-dir", type=Path, default=state.DEFAULT_PROJECT_DIR)
    parser.add_argument("--workflow", type=Path, default=None)
    sub = parser.add_subparsers(dest="command", required=True)

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
    status.set_defaults(func=cmd_status)

    phase = sub.add_parser("phase")
    phase.add_argument("phase")
    phase.set_defaults(func=cmd_phase)

    step = sub.add_parser("step")
    step.add_argument("action", choices=["done", "skip", "reset", "start"])
    step.add_argument("step_id", nargs="?")
    step.set_defaults(func=cmd_step)

    next_cmd = sub.add_parser("next")
    next_cmd.set_defaults(func=cmd_next)

    evidence = sub.add_parser("evidence")
    evidence.add_argument("--timeout", type=float, default=15)
    evidence.add_argument("--sample-limit", type=int, default=50)
    evidence.add_argument("--output-dir", type=Path)
    evidence.set_defaults(func=cmd_evidence)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if args.workflow is None:
        from seo_workbench.workflow import DEFAULT_WORKFLOW

        args.workflow = DEFAULT_WORKFLOW
    try:
        return args.func(args)
    except (FileNotFoundError, FileExistsError, ValueError) as exc:
        raise SystemExit(str(exc)) from exc


if __name__ == "__main__":
    raise SystemExit(main())
