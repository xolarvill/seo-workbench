from __future__ import annotations

import getpass
import json
import sys
import os

from seo_workbench import clarity


def execute(args) -> int:
    project = args.project_dir
    action = args.clarity_command
    if action == "status":
        payload = clarity.integration_status(project)
    elif action == "configure":
        token = sys.stdin.readline(16386).strip() if args.token_stdin else getpass.getpass("Clarity token: ")
        payload = clarity.configure(project, token, args.clarity_project, args.timezone, verify=not args.skip_verify)
    elif action == "verify":
        payload = clarity.verify_connection(project)
    elif action == "disconnect":
        payload = clarity.disconnect(project)
    else:
        from seo_workbench_tools.clarity_probe import collect
        transient = {}
        report = collect(project, action, query=getattr(args, "query", ""), start=getattr(args, "start", ""),
                         end=getattr(args, "end", ""), timezone_name=getattr(args, "timezone", None),
                         url=getattr(args, "url", None), device=getattr(args, "device", None),
                         channel=getattr(args, "channel", None), rage_click=getattr(args, "rage_click", False),
                         dead_click=getattr(args, "dead_click", False), js_error=getattr(args, "js_error", False),
                         count=getattr(args, "count", 10), force=args.force,
                         transient_sink=transient.update if action == "recordings" and os.environ.get("SEO_WORKBENCH_CLARITY_TRANSIENT") == "1" else None)
        # A background job must not copy session/document content into its log.
        payload = {key: report[key] for key in ("collection_status", "reason_code", "warnings", "manifest", "cache_hit") if key in report}
        if action == "recordings":
            payload["cache_key"] = report.get("cache_key")
        payload["ok"] = report["collection_status"] in ("ok", "partial")
        if transient:
            payload["_private_clarity_links"] = transient
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0 if payload.get("ok", True) else 1


def register(sub) -> None:
    parser = sub.add_parser("clarity", help="Project-scoped Clarity MCP queries and private connections")
    commands = parser.add_subparsers(dest="clarity_command", required=True)
    for name in ("status", "configure", "verify", "disconnect", "query", "recordings", "docs"):
        command = commands.add_parser(name)
        command.add_argument("--json", action="store_true", dest="json_output")
        command.set_defaults(func=execute)
        if name == "configure":
            command.add_argument("--token-stdin", action="store_true", help="Read one token line from stdin; never pass a token as an argument")
            command.add_argument("--clarity-project", required=True)
            command.add_argument("--timezone", required=True, help="Explicit IANA query timezone")
            command.add_argument("--skip-verify", action="store_true", help="Initial setup only; rotations always verify")
        if name in ("query", "docs"):
            command.add_argument("--query", required=True)
        if name in ("query", "recordings"):
            command.add_argument("--start", required=True)
            command.add_argument("--end", required=True)
        if name == "query":
            command.add_argument("--timezone")
        if name == "recordings":
            command.add_argument("--url")
            command.add_argument("--device", choices=("Mobile", "PC", "Tablet"))
            command.add_argument("--channel", choices=("OrganicSearch", "Direct", "Email", "Display", "Social", "PaidSearch", "Other", "Affiliate", "Referral", "Video", "Audio", "SMS", "AITools", "PaidAITools"))
            command.add_argument("--rage-click", action="store_true")
            command.add_argument("--dead-click", action="store_true")
            command.add_argument("--js-error", action="store_true")
            command.add_argument("--count", type=int, default=10)
        if name in ("query", "recordings", "docs"):
            command.add_argument("--force", action="store_true")
