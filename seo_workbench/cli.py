from __future__ import annotations

import argparse
import json
import os
from datetime import date, datetime
from pathlib import Path

from seo_workbench import dataforseo, state
from seo_workbench.audit_diff import AUDIT_KINDS, create_diff
from seo_workbench.backlinks import (
    backlink_status,
    collect_dataforseo_backlinks,
    collect_dataforseo_gap,
    import_backlink_snapshot,
)
from seo_workbench.business_signals import import_business_signals
from seo_workbench.business_signals_merge import collect_business_signals
from seo_workbench.content_assets import (
    apply_asset_urls,
    describe_asset_candidates,
    download_asset_files_from_feishu,
    upload_asset_files_to_shopify,
    write_asset_candidates_from_feishu,
    write_asset_manifest,
)
from seo_workbench.content_briefs import export_revision_brief, export_writing_brief
from seo_workbench.content_clusters import export_cluster_brief, import_clusters
from seo_workbench.content_drafts import import_draft
from seo_workbench.content_indexing import (
    apply_gsc_index_status,
    list_due_for_indexing,
    mark_index_notifications_sent,
    pending_index_notifications,
    submit_due_for_indexing,
)
from seo_workbench.content_ops import build_content_ops
from seo_workbench.content_pipeline import set_queue_status, sync_pipeline_status
from seo_workbench.content_portfolio import analyze_content_portfolio
from seo_workbench.content_quality import run_content_qc
from seo_workbench.content_publish import publish_dry_run, publish_item
from seo_workbench.metadata_ops import update_article_summary, update_collection_seo, update_product_seo
from seo_workbench.content_review_digest import generate_review_digest
from seo_workbench.content_review_push import push_review_request
from seo_workbench.content_reports import generate_content_report
from seo_workbench.content_serp import write_serp_competitors
from seo_workbench.crux import collect_from_state as collect_crux_from_state
from seo_workbench.doctor import run_doctor
from seo_workbench.evidence import collect_from_state
from seo_workbench.feishu_notify import send_report_via_feishu_gateway
from seo_workbench.feishu_sync import import_hexcal_from_feishu_gateway
from seo_workbench.gsc import (
    authenticate as authenticate_gsc,
    bind_property as bind_gsc_property,
    collect_all as collect_gsc,
    collect_inspection as collect_gsc_inspection,
    collect_performance as collect_gsc_performance,
    collect_sitemaps as collect_gsc_sitemaps,
    list_properties as list_gsc_properties,
)
from seo_workbench.hexcal_blog_import import import_hexcal_blog
from seo_workbench.keywords import collect_keywords
from seo_workbench.measurement_regimes import SOURCES as MEASUREMENT_SOURCES, list_regimes, record_regime
from seo_workbench.performance import collect_from_state as collect_performance_from_state
from seo_workbench.presentation import (
    DEFAULT_MAX_STATISTICS_AGE_HOURS,
    generate_weekly_presentation,
    presentation_status,
)
from seo_workbench.report_archive import list_report_archive, scaffold_weekly_report
from seo_workbench.seo_changes import CHANGE_STATUSES, CHANGE_TYPES, list_changes, record_change, update_change_status
from seo_workbench.seo_outcomes import evaluate_change, evaluate_change_with_fresh_gsc
from seo_workbench.statistics_pipeline import collect_statistics
from seo_workbench.technology import collect_from_state as collect_technology_from_state
from seo_workbench.tech_audit import (
    CrawlConfig,
    DEFAULT_BACKOFF,
    DEFAULT_CONCURRENCY,
    DEFAULT_REQUEST_DELAY,
    DEFAULT_USER_AGENT,
    RULES,
    disable_schedule,
    continue_tech_audit,
    load_schedule,
    mark_schedule_run,
    recrawl_urls,
    run_tech_audit,
    schedule_due,
    set_schedule,
)
from seo_workbench.tech_issues import USER_ISSUE_STATUSES, list_issue_register, update_issue_status
from seo_workbench.validation import validate_project
from seo_workbench.workflow import load_workflow, next_contract
from seo_workbench_tools import ga4_probe, shopify_orders_probe


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
    state.mutate_state(args.project_dir, lambda data: state.set_phase(data, args.phase))
    print(state.state_path(args.project_dir))
    return 0


def cmd_step(args: argparse.Namespace) -> int:
    phase, step_id = state.mutate_state(
        args.project_dir,
        lambda data: state.update_step(data, args.action, args.step_id),
    )
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
    print(f"after: ./seo --project-dir {args.project_dir} step done")
    return 0


def cmd_ui(args: argparse.Namespace) -> int:
    try:
        from seo_workbench.ui import run_ui
    except ImportError as exc:
        missing = exc.name or getattr(exc, "name", None)
        if missing and missing != "seo_workbench.ui":
            raise RuntimeError(
                f"UI dependencies are missing in the active environment ({missing}); "
                "re-run ./setup.sh, or: uv sync --frozen --python 3.11 "
                "--extra ui (add --extra rendered --extra technology --extra google as needed)"
            ) from exc
        raise RuntimeError("UI support is not installed; run ./setup.sh") from exc
    allow_cookieless = args.allow_cookieless or os.environ.get("SEO_WORKBENCH_UI_ALLOW_COOKIELESS") == "1"
    return run_ui(
        port=args.port,
        open_browser=not args.no_open,
        initial_project=args.project,
        allow_cookieless=allow_cookieless,
    )


def cmd_evidence(args: argparse.Namespace) -> int:
    output_dir = args.output_dir or state.safe_project_path(args.project_dir, "audits/raw")
    if args.output_dir is None:
        state.safe_project_path(args.project_dir, "audits/rendered")
        state.safe_project_path(args.project_dir, "audits/technology")
        state.safe_project_path(args.project_dir, "audits/performance")
        state.safe_project_path(args.project_dir, "audits/crux")
        state.safe_project_path(args.project_dir, "audits/gsc")
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
        crux=args.crux,
        gsc=args.gsc,
        crawl_limit=args.crawl_limit,
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
                "error_count": len(report.get("errors", [])),
                "warning_count": len(report.get("warnings", [])),
                "rendered": args.rendered,
                "technology": args.technology,
                "performance": args.performance,
                "crux": args.crux,
                "gsc": args.gsc,
                "crux_status": report.get("crux_audit", {}).get("collection_status", "not_requested"),
                "gsc_status": report.get("gsc_audit", {}).get("collection_status", "not_requested"),
                "crawl_limit": args.crawl_limit,
                "discovered_count": report.get("discovery", {}).get("discovered_count", 0),
                "possible_spa_shell": report.get("route_sample_audit", {}).get("possible_spa_shell", False),
            }
        )
        return 0 if ok else 1
    print(path)
    return 0 if ok else 1


def cmd_technology(args: argparse.Namespace) -> int:
    output_dir = args.output_dir or state.safe_project_path(args.project_dir, "audits/technology")
    path = collect_technology_from_state(
        state.state_path(args.project_dir),
        args.timeout,
        output_dir,
        allow_private=args.allow_private,
        scan_mode=args.scan_mode,
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
                "scan_mode": report.get("scan_mode", ""),
                "technology_count": len(
                    {
                        technology.get("name")
                        for page in report.get("pages", [])
                        for technology in page.get("technologies", [])
                        if technology.get("name")
                    }
                ),
                "architecture_summary": report.get("architecture_analysis", {}).get("summary", ""),
            }
        )
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
                "requested_url": report.get("requested_url") or report.get("url", ""),
                "final_url": report.get("final_url", ""),
                "redirected": report.get("redirected", False),
                "redirect_consistent": report.get("redirect_consistent", True),
                "performance_score": report.get("aggregate", {}).get("performance_score", {}),
                "high_variance": report.get("aggregate", {}).get("high_variance", False),
            }
        )
        return 0 if ok else 1
    print(path)
    return 0 if ok else 1


def cmd_crux(args: argparse.Namespace) -> int:
    output_dir = args.output_dir or state.safe_project_path(args.project_dir, "audits/crux")
    path = collect_crux_from_state(
        state.state_path(args.project_dir),
        output_dir,
        url=args.url,
        form_factors=args.form_factor or ("aggregate", "mobile", "desktop"),
        timeout=args.timeout,
    )
    report = json.loads(path.read_text(encoding="utf-8"))
    status = report.get("collection_status", "failed")
    ok = status != "failed"
    if args.json_output:
        print_json(
            {
                "ok": ok,
                "path": str(path),
                "collection_status": status,
                "requested_url": report.get("requested_url", ""),
                "form_factors": [item.get("form_factor") for item in report.get("queries", [])],
                "summary": report.get("summary", {}),
                "error_count": len(report.get("errors", [])),
                "warning_count": len(report.get("warnings", [])),
            }
        )
        return 0 if ok else 1
    print(path)
    return 0 if ok else 1


def _gsc_result(report: dict, args: argparse.Namespace, *, path: str = "") -> int:
    status = report.get("collection_status", "ok")
    ok = status in {"ok", "partial"}
    if args.json_output:
        print_json({"ok": ok, "path": path, **report})
    elif path:
        print(path)
    else:
        print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if ok else 1


def cmd_gsc_auth(args: argparse.Namespace) -> int:
    report = authenticate_gsc(
        args.profile,
        client_secret=args.client_secret,
        service_account_path=args.service_account,
    )
    return _gsc_result({"collection_status": "ok", **report}, args)


def cmd_gsc_properties(args: argparse.Namespace) -> int:
    return _gsc_result(list_gsc_properties(args.profile, timeout=args.timeout), args)


def cmd_gsc_bind(args: argparse.Namespace) -> int:
    binding = bind_gsc_property(args.project_dir, args.property, profile=args.profile, timeout=args.timeout)
    return _gsc_result({"collection_status": "ok", "binding": binding}, args)


def cmd_gsc_performance(args: argparse.Namespace) -> int:
    report = collect_gsc_performance(
        args.project_dir,
        state.safe_project_path(args.project_dir, "audits/gsc/search-analytics"),
        days=args.days,
        compare=args.compare,
        timeout=args.timeout,
    )
    return _gsc_result(report, args, path=report.get("manifest", {}).get("path", ""))


def cmd_gsc_inspect(args: argparse.Namespace) -> int:
    report = collect_gsc_inspection(
        args.project_dir,
        state.safe_project_path(args.project_dir, "audits/gsc/inspection"),
        urls=args.url,
        limit=args.limit,
        timeout=args.timeout,
    )
    return _gsc_result(report, args, path=report.get("manifest", {}).get("path", ""))


def cmd_gsc_sitemaps(args: argparse.Namespace) -> int:
    report = collect_gsc_sitemaps(
        args.project_dir,
        state.safe_project_path(args.project_dir, "audits/gsc/sitemaps"),
        timeout=args.timeout,
    )
    return _gsc_result(report, args, path=report.get("manifest", {}).get("path", ""))


def cmd_gsc_collect(args: argparse.Namespace) -> int:
    report = collect_gsc(
        args.project_dir,
        state.safe_project_path(args.project_dir, "audits/gsc"),
        days=args.days,
        inspection_limit=args.inspection_limit,
        timeout=args.timeout,
    )
    return _gsc_result(report, args, path=report.get("manifest", {}).get("path", ""))


def cmd_ga4_import(args: argparse.Namespace) -> int:
    payload = json.loads(args.credential.read_text(encoding="utf-8"))
    result = ga4_probe.import_credentials(args.profile, payload)
    if args.json_output:
        print_json({"ok": True, "profile": result["profile"], "credential_type": result["credential_type"]})
    else:
        print(f"GA4 credentials stored for profile '{result['profile']}'")
    return 0


def cmd_ga4_properties(args: argparse.Namespace) -> int:
    result = ga4_probe.list_properties(args.profile, timeout=args.timeout)
    if args.json_output:
        print_json({"ok": True, "profile": result["profile"], "properties": result["properties"]})
    else:
        for item in result["properties"]:
            print(f"{item['property_id']}  {item['display_name']}")
    return 0


def cmd_ga4_bind(args: argparse.Namespace) -> int:
    binding = ga4_probe.bind_property(args.project_dir, args.property, profile=args.profile, timeout=args.timeout)
    if args.json_output:
        print_json({"ok": True, "binding": binding})
    else:
        print(f"GA4 property bound: {binding['property']} ({binding.get('display_name', '')})")
    return 0


def cmd_ga4_collect(args: argparse.Namespace) -> int:
    report = ga4_probe.collect(
        args.project_dir,
        state.safe_project_path(args.project_dir, "audits/ga4"),
        days=args.days,
        timeout=args.timeout,
        end_date=args.end_date,
    )
    ok = report.get("collection_status") == "ok"
    if args.json_output:
        print_json(
            {
                "ok": ok,
                "path": report.get("manifest", {}).get("path", ""),
                "collection_status": report.get("collection_status"),
                "property": report.get("property", ""),
                "property_display_name": report.get("property_display_name", ""),
                "windows": {
                    name: {key: len(rows) for key, rows in group.items() if isinstance(rows, list)}
                    for name, group in report.get("windows", {}).items()
                },
                "error_count": len(report.get("errors", [])),
                "warning_count": len(report.get("warnings", [])),
            }
        )
    else:
        print(report.get("manifest", {}).get("path", ""))
    return 0 if ok else 1


def cmd_shopify_orders_collect(args: argparse.Namespace) -> int:
    report = shopify_orders_probe.collect_orders(
        args.project_dir,
        days=args.days,
        timeout=args.timeout,
        end_date=args.end_date,
    )
    ok = report.get("collection_status") == "ok"
    if args.json_output:
        print_json(
            {
                "ok": ok,
                "path": report.get("manifest", {}).get("path", ""),
                "collection_status": report.get("collection_status"),
                "windows": {name: group.get("orders", 0) for name, group in report.get("windows", {}).items()},
                "error_count": len(report.get("errors", [])),
                "warning_count": len(report.get("warnings", [])),
            }
        )
    else:
        print(report.get("manifest", {}).get("path", ""))
    return 0 if ok else 1


def cmd_business_signals_collect(args: argparse.Namespace) -> int:
    report, path = collect_business_signals(args.project_dir)
    ok = report.get("collection_status") == "ok"
    if args.json_output:
        print_json(
            {
                "ok": ok,
                "path": str(path),
                "collection_status": report.get("collection_status"),
                "windows": {name: len(group.get("rows", [])) for name, group in report.get("windows", {}).items()},
                "warnings": report.get("warnings", []),
            }
        )
    else:
        print(path)
    return 0 if ok else 1


def cmd_statistics_collect(args: argparse.Namespace) -> int:
    report, path = collect_statistics(args.project_dir, days=args.days, timeout=args.timeout)
    ok = report.get("collection_status") != "failed"
    payload = {"ok": ok, "path": str(path), **report}
    if args.json_output:
        print_json(payload)
    else:
        print(path if ok else report.get("errors", ["statistics collection failed"])[0])
    return 0 if ok else 1


def cmd_statistics_regime_add(args: argparse.Namespace) -> int:
    record = record_regime(
        args.project_dir,
        source=args.source,
        effective_at=args.effective_at,
        description=args.description,
        metrics=args.metric,
        breaks_comparability=not args.comparable_across,
    )
    if args.json_output:
        print_json({"ok": True, "regime": record})
    else:
        print(record["id"])
    return 0


def cmd_statistics_regime_list(args: argparse.Namespace) -> int:
    report = list_regimes(args.project_dir)
    if args.json_output:
        print_json({"ok": True, **report})
    else:
        for record in report["regimes"]:
            print(f"{record['effective_at']}  {record['source']}  {record['description']}")
    return 0


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
                "comparability": report.get("comparability"),
                "comparability_summary": report.get("comparability_summary"),
                "comparisons": {
                    kind: {
                        "status": item["status"],
                        "comparable": item["comparable"],
                        "comparability": item.get("comparability"),
                        "comparability_notes": item.get("comparability_notes", []),
                    }
                    for kind, item in report["comparisons"].items()
                },
            }
        )
        return 0 if ok else 1
    print(path)
    return 0 if ok else 1


def cmd_tech_audit_run(args: argparse.Namespace) -> int:
    schedule = load_schedule(args.project_dir) if args.scheduled else {}
    if args.scheduled and not schedule_due(schedule):
        payload = {"ok": True, "status": "not_due", "schedule": schedule}
        if args.json_output:
            print_json(payload)
        else:
            print("technical audit is not due")
        return 0
    if args.notify_role and not args.confirm and not args.scheduled:
        raise ValueError("tech-audit notifications require --confirm")
    notify_role = args.notify_role or (schedule.get("notify_role", "") if args.scheduled else "")
    profile = args.profile or (schedule.get("profile", "") if args.scheduled else "")
    if notify_role and not profile:
        raise ValueError("tech-audit notifications require an explicit --profile")
    if args.refresh_gsc:
        collect_gsc(
            args.project_dir,
            state.safe_project_path(args.project_dir, "audits/gsc"),
            days=args.gsc_days,
            inspection_limit=args.gsc_inspection_limit,
            timeout=args.timeout,
        )
    config = CrawlConfig(
        max_urls=args.max_urls,
        concurrency=args.concurrency,
        request_delay=args.delay,
        retries=args.retries,
        backoff=args.backoff,
        timeout=args.timeout,
        user_agent=args.user_agent,
        include_subdomains=args.include_subdomains,
        load_sitemap=args.load_sitemap,
        sitemap_urls=tuple(args.sitemap or ()),
        max_sitemaps=args.max_sitemaps,
        max_redirects=args.max_redirects,
        high_depth=args.high_depth,
        slow_response_ms=args.slow_ms,
        large_html_bytes=args.large_html_bytes,
        allow_private=args.allow_private,
        rendered=args.rendered,
        render_limit=args.render_limit,
        render_wait_ms=args.render_wait_ms,
    )
    try:
        report, path = run_tech_audit(args.project_dir, config)
        notification = None
        if notify_role and report.get("new_high_impact_actions"):
            notification, notification_path = send_report_via_feishu_gateway(
                args.project_dir,
                Path(report["action_queue_path"]),
                title=f"Technical SEO: {len(report['new_high_impact_actions'])} new high-impact action(s)",
                role=notify_role,
                profile=profile,
                config_path=args.config,
            )
            report["notification_path"] = str(notification_path)
        if args.scheduled or load_schedule(args.project_dir).get("enabled"):
            report["schedule"] = mark_schedule_run(args.project_dir)
    except Exception:
        if args.scheduled:
            mark_schedule_run(args.project_dir)
        raise
    if args.json_output:
        print_json({"ok": report["collection_status"] != "failed", "path": str(path), **report, "notification": notification})
        return 0 if report["collection_status"] != "failed" else 1
    print(path)
    return 0 if report["collection_status"] != "failed" else 1


def cmd_tech_audit_continue(args: argparse.Namespace) -> int:
    report, path = continue_tech_audit(args.project_dir)
    if args.json_output:
        print_json({"ok": report["collection_status"] != "failed", "path": str(path), **report})
        return 0 if report["collection_status"] != "failed" else 1
    print(path)
    return 0 if report["collection_status"] != "failed" else 1


def cmd_tech_audit_recrawl(args: argparse.Namespace) -> int:
    config = CrawlConfig(
        max_urls=len(args.url),
        concurrency=args.concurrency,
        request_delay=args.delay,
        retries=args.retries,
        backoff=args.backoff,
        timeout=args.timeout,
        user_agent=args.user_agent,
        allow_private=args.allow_private,
        load_sitemap=False,
    )
    report, path = recrawl_urls(args.project_dir, args.url, config)
    if args.json_output:
        print_json({"ok": report["collection_status"] != "failed", "path": str(path), **report})
        return 0 if report["collection_status"] != "failed" else 1
    print(path)
    return 0 if report["collection_status"] != "failed" else 1


def cmd_tech_audit_rules(args: argparse.Namespace) -> int:
    payload = {"ok": True, "count": len(RULES), "rules": [{"rule_id": key, **vars(value)} for key, value in RULES.items()]}
    if args.json_output:
        print_json(payload)
    else:
        for rule in payload["rules"]:
            print(f"{rule['rule_id']}: {rule['title']} [{rule['default_severity']}]")
    return 0


def cmd_tech_audit_schedule(args: argparse.Namespace) -> int:
    if args.schedule_action == "set":
        if args.notify_role and not args.profile:
            raise ValueError("tech-audit notification schedules require an explicit --profile")
        payload = set_schedule(args.project_dir, args.every_minutes, notify_role=args.notify_role or "", profile=args.profile)
    elif args.schedule_action == "disable":
        payload = disable_schedule(args.project_dir)
    else:
        payload = load_schedule(args.project_dir)
    if args.json_output:
        print_json({"ok": True, "schedule": payload, "path": str(state.safe_project_path(args.project_dir, ".runtime/tech-audit/schedule.json"))})
    else:
        print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0


def _running_tech_audit_status(project_dir: Path) -> tuple[dict, Path] | None:
    runs: list[Path] = []
    for relative_root in ("audits/tech-audit/runs", "audits/tech-audit/recrawls"):
        root = state.safe_project_path(project_dir, relative_root)
        if root.is_dir():
            runs.extend(root.glob("*/run.json"))
    for path in sorted(runs, key=lambda item: (item.stat().st_mtime, item.parent.name), reverse=True):
        try:
            status = state.read_json(path)
        except (OSError, ValueError, json.JSONDecodeError):
            continue
        if isinstance(status, dict) and status.get("status") == "running":
            return status, path
    return None


def cmd_tech_audit_status(args: argparse.Namespace) -> int:
    latest = state.safe_project_path(args.project_dir, "audits/tech-audit/latest.json")
    payload = {"ok": True, "status": "no_data", "schedule": load_schedule(args.project_dir)}
    if latest.is_file():
        payload.update({"status": "ready", "snapshot": state.read_json(latest), "path": str(latest)})
    if running := _running_tech_audit_status(args.project_dir):
        run, run_path = running
        payload.update({"status": "running", "run": run, "run_path": str(run_path)})
    if args.json_output:
        print_json(payload)
    else:
        if payload["status"] == "running":
            run = payload["run"]
            print(f"running: {run.get('phase', 'starting')} · {run.get('processed_urls', 0)} processed · {run.get('discovered_urls', 0)} discovered · {run.get('error_count', 0)} errors")
        else:
            print(payload["status"])
    return 0


def cmd_tech_audit_diff(args: argparse.Namespace) -> int:
    args.kind = "tech-audit"
    return cmd_audit_diff(args)


def cmd_tech_audit_issues(args: argparse.Namespace) -> int:
    if args.issues_action == "status":
        issue = update_issue_status(
            args.project_dir,
            args.fingerprint,
            args.status,
            owner=args.owner or "",
            note=args.note or "",
        )
        payload = {"ok": True, "issue": issue}
    else:
        payload = {"ok": True, **list_issue_register(args.project_dir, status=args.status or "", owner=args.owner or "")}
    if args.json_output:
        print_json(payload)
        return 0
    if args.issues_action == "status":
        print(f"{payload['issue']['fingerprint']}: {payload['issue']['status']}")
    else:
        for issue in payload["issues"]:
            print(f"{issue['fingerprint']}: {issue['status']} {issue['rule_id']} {issue['url']}")
    return 0


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


def cmd_content_import_hexcal(args: argparse.Namespace) -> int:
    if not args.keywords_json and not args.pipeline_json:
        raise ValueError("content import-hexcal requires --keywords-json or --pipeline-json")
    result = import_hexcal_blog(
        args.project_dir,
        keywords_path=args.keywords_json,
        pipeline_path=args.pipeline_json,
    )
    payload = {"ok": True, **result}
    if args.json_output:
        print_json(payload)
        return 0
    print(result["blog_pipeline_path"] or result["keyword_pool_path"])
    return 0


def cmd_content_import_feishu(args: argparse.Namespace) -> int:
    if args.keywords_only and args.pipeline_only:
        raise ValueError("choose at most one of --keywords-only or --pipeline-only")
    report = import_hexcal_from_feishu_gateway(
        args.project_dir,
        profile=args.profile,
        config_path=args.config,
        include_keywords=not args.pipeline_only,
        include_pipeline=not args.keywords_only,
        limit=args.limit,
    )
    if args.json_output:
        print_json({"ok": True, **report})
        return 0
    print(f"imported keywords={report['keywords_imported']} pipeline={report['pipeline_imported']}")
    return 0


def cmd_content_import_draft(args: argparse.Namespace) -> int:
    report, path = import_draft(args.project_dir, args.from_file)
    if args.json_output:
        print_json({"ok": True, "path": str(path), **report})
        return 0
    print(path)
    return 0


def cmd_content_cluster_brief(args: argparse.Namespace) -> int:
    report, path = export_cluster_brief(args.project_dir, max_keywords=args.max_keywords)
    if args.json_output:
        print_json({"ok": True, "path": str(path), **report})
        return 0
    print(path)
    return 0


def cmd_content_import_clusters(args: argparse.Namespace) -> int:
    report, path = import_clusters(args.project_dir, args.from_file)
    if args.json_output:
        print_json({"ok": True, "path": str(path), **report})
        return 0
    print(path)
    return 0


def cmd_content_queue(args: argparse.Namespace) -> int:
    data = state.load_state(args.project_dir)
    items = data.get("contentQueue", [])
    if not isinstance(items, list):
        raise ValueError("state.contentQueue must be a list")
    if args.status:
        items = [item for item in items if isinstance(item, dict) and item.get("status") == args.status]
    payload = {"ok": True, "count": len(items), "items": items}
    if args.json_output:
        print_json(payload)
        return 0
    if not items:
        print("no content queue items")
        return 0
    for item in items:
        print(f"{item.get('id', '')}: {item.get('status', '')} {item.get('title', '')}")
    return 0


def cmd_content_status(args: argparse.Namespace) -> int:
    def mutate(data: dict) -> dict:
        item = set_queue_status(data, args.item_id, args.status, note=args.note or "")
        state.record_history(
            data,
            "content-status",
            phase="CONTENT_PRODUCTION",
            step_id=args.item_id,
            note=f"{item['status']}: {args.note or ''}".strip(),
        )
        data["lastAction"] = f"Updated content item {args.item_id} to {item['status']}"
        data["nextAction"] = "Review content queue"
        return item

    item = state.mutate_state(args.project_dir, mutate)
    pipeline_synced = sync_pipeline_status(args.project_dir, args.item_id, item)
    if args.json_output:
        print_json({"ok": True, "item": item, "pipeline_synced": pipeline_synced})
        return 0
    print(f"{item['id']}: {item['status']}")
    return 0


def cmd_content_portfolio(args: argparse.Namespace) -> int:
    report, path = analyze_content_portfolio(
        args.project_dir,
        gsc_path=args.gsc_json,
        business_path=args.business_json,
    )
    if args.json_output:
        payload = {"ok": True, "path": str(path), **report}
        if getattr(args, "pages_command", None) == "refresh":
            payload = {
                key: payload[key]
                for key in (
                    "ok", "path", "schema_version", "collection_status", "generated_at",
                    "comparability", "count", "counts", "source_status", "mutation_performed",
                )
            }
        print_json(payload)
        return 0
    print(path)
    return 0


def cmd_content_qc(args: argparse.Namespace) -> int:
    report, path = run_content_qc(args.project_dir, args.item_id)
    if args.json_output:
        print_json({"ok": True, "path": str(path), **report})
        return 0
    print(path)
    return 0


def cmd_content_publish_dry_run(args: argparse.Namespace) -> int:
    report, path = publish_dry_run(args.project_dir, args.item_id, blog_id=args.blog_id)
    if args.json_output:
        print_json({"ok": True, "path": str(path), **report})
        return 0
    print(path)
    return 0


def cmd_content_publish(args: argparse.Namespace) -> int:
    if not args.confirm:
        raise ValueError("content publish requires --confirm")
    if args.allow_warnings:
        raise ValueError("content publish cannot bypass warnings")
    report, path = publish_item(
        args.project_dir,
        args.item_id,
        blog_id=args.blog_id,
        timeout=args.timeout,
    )
    if args.json_output:
        print_json({"ok": report["collection_status"] == "complete", "path": str(path), **report})
        return 0 if report["collection_status"] == "complete" else 2
    print(path)
    return 0 if report["collection_status"] == "complete" else 2


def cmd_metadata_update(args: argparse.Namespace) -> int:
    if not args.dry_run and not args.confirm:
        raise ValueError("metadata update requires --confirm")
    if args.resource == "collection":
        report, path = update_collection_seo(
            args.project_dir,
            args.handle,
            args.seo_title or "",
            args.seo_description or "",
            args.body or "",
            dry_run=args.dry_run,
            timeout=args.timeout,
        )
    elif args.resource == "article":
        report, path = update_article_summary(
            args.project_dir,
            args.handle,
            args.summary or "",
            dry_run=args.dry_run,
            timeout=args.timeout,
        )
    else:
        report, path = update_product_seo(
            args.project_dir,
            args.handle,
            args.seo_title or "",
            args.seo_description or "",
            dry_run=args.dry_run,
            timeout=args.timeout,
        )
    if args.json_output:
        print_json({"ok": report["collection_status"] in ("complete", "dry-run"), "path": str(path), **report})
        return 0 if report["collection_status"] in ("complete", "dry-run") else 2
    print(path)
    return 0 if report["collection_status"] in ("complete", "dry-run") else 2


def cmd_content_report(args: argparse.Namespace) -> int:
    report_date = datetime.fromisoformat(args.date).date() if args.date else None
    summary, path = generate_content_report(args.project_dir, period=args.period, report_date=report_date)
    if args.json_output:
        print_json({"ok": True, "path": str(path), **summary})
        return 0
    print(path)
    return 0


def cmd_content_review_digest(args: argparse.Namespace) -> int:
    report, path = generate_review_digest(
        args.project_dir,
        item_id=args.item_id,
        profile=args.profile,
        config_path=args.config,
        bot_id=args.bot_id or "",
    )
    if args.json_output:
        print_json({"ok": True, "path": str(path), **report})
        return 0
    print(path)
    return 0


def cmd_content_review_push(args: argparse.Namespace) -> int:
    if not args.confirm:
        raise ValueError("content review-push requires --confirm")
    report, path = push_review_request(
        args.project_dir,
        args.item_id,
        role=args.role,
        profile=args.profile,
        config_path=args.config,
    )
    if args.json_output:
        print_json({"ok": True, "path": str(path), **report})
        return 0
    print(path)
    return 0


def cmd_content_ops(args: argparse.Namespace) -> int:
    report = build_content_ops(args.project_dir)
    if args.json_output:
        print_json({"ok": True, **report})
        return 0
    for action in report["actions"]:
        marker = "due" if action["due"] else "idle"
        print(f"{marker}: {action['id']} ({action['count']}) - {action['command']}")
    return 0


def cmd_content_index_queue(args: argparse.Namespace) -> int:
    report = list_due_for_indexing(args.project_dir)
    if args.json_output:
        print_json({"ok": True, **report})
        return 0
    for url in report["urls"]:
        print(url)
    return 0


def cmd_content_index_submit(args: argparse.Namespace) -> int:
    if not args.confirm:
        raise ValueError("content index-submit requires --confirm")
    report, path = submit_due_for_indexing(
        args.project_dir,
        profile=args.profile,
        limit=args.limit,
        timeout=args.timeout,
    )
    if args.json_output:
        print_json({"ok": report["collection_status"] in {"ok", "partial"}, "path": str(path), **report})
        return 0 if report["collection_status"] in {"ok", "partial"} else 2
    print(path)
    return 0 if report["collection_status"] in {"ok", "partial"} else 2


def cmd_content_index_status(args: argparse.Namespace) -> int:
    if args.notify_role and not args.confirm:
        raise ValueError("content index-status notifications require --confirm")
    if args.notify_role and not args.profile:
        raise ValueError("content index-status notifications require an explicit --profile")
    report, path = apply_gsc_index_status(
        args.project_dir,
        inspection_path=args.inspection_json,
        anomaly_days=args.anomaly_days,
    )
    newly_indexed = pending_index_notifications(args.project_dir, report["changes"])
    if args.notify_role and newly_indexed:
        _summary, report_path = generate_content_report(args.project_dir, period="daily")
        notification, notification_path = send_report_via_feishu_gateway(
            args.project_dir,
            report_path,
            title=f"BLOG indexed: {len(newly_indexed)} new",
            role=args.notify_role,
            profile=args.profile,
            config_path=args.config,
        )
        report["notification_sent"] = True
        report["notification"] = notification
        report["notification_path"] = str(notification_path)
        mark_index_notifications_sent(args.project_dir, [str(change["id"]) for change in newly_indexed])
        state.write_json(path, report)
    elif args.notify_role:
        report["notification_reason"] = "no newly indexed items"
    if args.json_output:
        print_json({"ok": True, "path": str(path), **report})
        return 0
    print(path)
    return 0


def cmd_content_brief(args: argparse.Namespace) -> int:
    report, path = export_writing_brief(args.project_dir, args.item_id)
    if args.json_output:
        print_json({"ok": True, "path": str(path), **report})
        return 0
    print(path)
    return 0


def cmd_content_revise_brief(args: argparse.Namespace) -> int:
    report, path = export_revision_brief(args.project_dir, args.item_id)
    if args.json_output:
        print_json({"ok": True, "path": str(path), **report})
        return 0
    print(path)
    return 0


def cmd_content_serp_competitors(args: argparse.Namespace) -> int:
    report, path = write_serp_competitors(
        args.project_dir,
        args.item_id,
        query=args.query or "",
        max_results=args.max_results,
        timeout=args.timeout,
    )
    if args.json_output:
        print_json({"ok": True, "path": str(path), **report})
        return 0
    print(path)
    return 0


def cmd_content_assets(args: argparse.Namespace) -> int:
    manifest, path = write_asset_manifest(args.project_dir, args.item_id)
    if args.json_output:
        print_json({"ok": True, "path": str(path), **manifest})
        return 0
    print(path)
    return 0


def cmd_content_asset_candidates(args: argparse.Namespace) -> int:
    report, path = write_asset_candidates_from_feishu(
        args.project_dir,
        args.item_id,
        profile=args.profile,
        config_path=args.config,
        limit=args.limit,
    )
    if args.json_output:
        print_json({"ok": True, "path": str(path), **report})
        return 0
    print(path)
    return 0


def cmd_content_describe_candidates(args: argparse.Namespace) -> int:
    if not args.no_writeback and not args.confirm:
        raise ValueError("content describe-candidates writeback requires --confirm")
    report, path = describe_asset_candidates(
        args.project_dir,
        args.item_id,
        profile=args.profile,
        config_path=args.config,
        manifest_path=args.manifest,
        limit=args.limit,
        write_back=not args.no_writeback,
    )
    if args.json_output:
        print_json({"ok": report["collection_status"] in {"ok", "partial"}, "path": str(path), **report})
        return 0 if report["collection_status"] in {"ok", "partial"} else 2
    print(path)
    return 0 if report["collection_status"] in {"ok", "partial"} else 2


def cmd_content_apply_assets(args: argparse.Namespace) -> int:
    report, path = apply_asset_urls(args.project_dir, args.item_id, manifest_path=args.manifest)
    if args.json_output:
        print_json({"ok": True, "path": str(path), **report})
        return 0
    print(path)
    return 0


def cmd_content_download_assets(args: argparse.Namespace) -> int:
    report, path = download_asset_files_from_feishu(
        args.project_dir,
        args.item_id,
        profile=args.profile,
        config_path=args.config,
        manifest_path=args.manifest,
    )
    if args.json_output:
        print_json({"ok": report["collection_status"] in {"ok", "partial"}, "path": str(path), **report})
        return 0 if report["collection_status"] in {"ok", "partial"} else 2
    print(path)
    return 0 if report["collection_status"] in {"ok", "partial"} else 2


def cmd_content_upload_assets(args: argparse.Namespace) -> int:
    report, path = upload_asset_files_to_shopify(
        args.project_dir,
        args.item_id,
        manifest_path=args.manifest,
        timeout=args.timeout,
    )
    if args.json_output:
        print_json({"ok": report["collection_status"] in {"ok", "partial"}, "path": str(path), **report})
        return 0 if report["collection_status"] in {"ok", "partial"} else 2
    print(path)
    return 0 if report["collection_status"] in {"ok", "partial"} else 2


def cmd_content_notify_report(args: argparse.Namespace) -> int:
    if not args.confirm:
        raise ValueError("content notify-report requires --confirm")
    report, path = send_report_via_feishu_gateway(
        args.project_dir,
        args.report_path,
        title=args.title,
        role=args.role,
        profile=args.profile,
        config_path=args.config,
    )
    if args.json_output:
        print_json({"ok": True, "path": str(path), **report})
        return 0
    print(path)
    return 0


def cmd_reports_list(args: argparse.Namespace) -> int:
    payload = list_report_archive(args.project_dir, query=args.q or "", category=args.category or "", year=args.year, month=args.month)
    if args.json_output:
        print_json({"ok": True, **payload})
        return 0
    for week in payload["weekly"]:
        marker = f"{week['checked']}/{week['total']} done" if week["total"] else "empty"
        print(f"{week['path']}: {marker}, {week['carry_over']} carried over")
    for category, reports in payload["categories"].items():
        for report in reports:
            print(f"{report['path']} [{category}]")
    return 0


def cmd_reports_new(args: argparse.Namespace) -> int:
    result = scaffold_weekly_report(
        args.project_dir,
        week=args.week,
        year=args.year,
        carry_over=not args.no_carry_over,
        force=args.force,
    )
    if args.json_output:
        print_json(result)
        return 0
    print(result["path"])
    return 0


def cmd_reports_presentation(args: argparse.Namespace) -> int:
    if args.reports_presentation_command == "status":
        payload = presentation_status(
            args.project_dir,
            year=args.year,
            week=args.week,
            max_statistics_age_hours=args.max_statistics_age_hours,
        )
        if args.json_output:
            print_json(payload)
            return 0
        print(payload["status"])
        return 0

    result, _path = generate_weekly_presentation(
        args.project_dir,
        year=args.year,
        week=args.week,
        max_statistics_age_hours=args.max_statistics_age_hours,
    )
    if args.json_output:
        print_json({"ok": True, **result})
        return 0
    print(result["path"])
    return 0


def cmd_keywords_collect(args: argparse.Namespace) -> int:
    result = collect_keywords(
        args.project_dir,
        google_ads_csv=args.google_ads_csv or [],
        semrush_xlsx=args.semrush_xlsx or [],
        gsc_search_json=args.gsc_search_json or [],
        autocomplete_seeds=args.autocomplete_seed or [],
        competitor_domains=args.competitor_domain or [],
        top_n=args.top_n,
        timeout=args.timeout,
        dry_run=args.dry_run,
    )
    payload = {"ok": True, **result}
    if args.json_output:
        print_json(payload)
        return 0
    print(result["path"])
    return 0


def cmd_changes_add(args: argparse.Namespace) -> int:
    change = record_change(
        args.project_dir,
        urls=args.url,
        change_type=args.change_type,
        hypothesis=args.hypothesis,
        metrics=args.metric,
        changed_at=args.changed_at,
        review_date=args.review_date,
        review_after_days=args.review_after_days,
        status=args.status,
        note=args.note or "",
    )
    if args.json_output:
        print_json({"ok": True, "change": change})
        return 0
    print(change["id"])
    return 0


def cmd_changes_list(args: argparse.Namespace) -> int:
    report = list_changes(args.project_dir, status=args.status or "", due=args.due, as_of=args.as_of)
    if args.json_output:
        print_json({"ok": True, **report})
        return 0
    for change in report["changes"]:
        print(f"{change['id']}: {change['status']} {change['change_type']} review {change['review_date']}")
    return 0


def cmd_changes_status(args: argparse.Namespace) -> int:
    change = update_change_status(args.project_dir, args.change_id, args.status, note=args.note or "")
    if args.json_output:
        print_json({"ok": True, "change": change})
        return 0
    print(f"{change['id']}: {change['status']}")
    return 0


def cmd_changes_evaluate(args: argparse.Namespace) -> int:
    if args.refresh_gsc:
        report, path = evaluate_change_with_fresh_gsc(
            args.project_dir,
            args.change_id,
            business_path=args.business_json,
            timeout=args.timeout,
        )
    else:
        report, path = evaluate_change(
            args.project_dir,
            args.change_id,
            gsc_path=args.gsc_json,
            business_path=args.business_json,
        )
    if args.json_output:
        print_json({"ok": True, "path": str(path), **report})
        return 0
    print(path)
    return 0


def cmd_business_signals_import(args: argparse.Namespace) -> int:
    report, path = import_business_signals(args.project_dir, args.from_file)
    if args.json_output:
        print_json({"ok": True, "path": str(path), **report})
        return 0
    print(path)
    return 0


def cmd_backlinks(args: argparse.Namespace) -> int:
    if args.backlinks_command == "import":
        report, path = import_backlink_snapshot(
            args.project_dir,
            args.from_file,
            source=args.source,
            complete=args.complete,
            captured_at=args.captured_at or "",
        )
        payload = {"ok": True, "path": str(path), **report}
    elif args.backlinks_command == "status":
        payload = {"ok": True, **backlink_status(args.project_dir, source=args.source or "")}
    else:
        try:
            if args.backlinks_command == "collect":
                report, path = collect_dataforseo_backlinks(
                    args.project_dir,
                    confirm_paid=args.confirm_paid,
                    max_links=args.max_links,
                    timeout=args.timeout,
                )
            else:
                report, path = collect_dataforseo_gap(
                    args.project_dir,
                    args.competitor,
                    confirm_paid=args.confirm_paid,
                    limit=args.limit,
                    timeout=args.timeout,
                )
            payload = {"ok": True, "path": str(path), **report}
        except dataforseo.DataForSeoCredentialsError as exc:
            payload = {"ok": False, "collection_status": "needs_credentials", "error": str(exc)}
        except dataforseo.DataForSeoUnavailable as exc:
            payload = {"ok": False, "collection_status": "provider_unavailable", "error": str(exc)}
    if args.json_output:
        print_json(payload)
        return 0 if payload["ok"] else 1
    print(payload.get("path", payload.get("collection_status", "unknown")))
    return 0 if payload["ok"] else 1


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
    evidence.add_argument("--crawl-limit", type=int, default=5)
    evidence.add_argument("--output-dir", type=Path)
    evidence.add_argument("--rendered", action="store_true")
    evidence.add_argument("--technology", action="store_true")
    evidence.add_argument("--performance", action="store_true")
    evidence.add_argument("--performance-runs", type=int, default=5)
    evidence.add_argument("--performance-form-factor", choices=["mobile", "desktop"], default="mobile")
    evidence.add_argument("--crux", action="store_true")
    evidence.add_argument("--gsc", action="store_true")
    evidence.add_argument("--json", action="store_true", dest="json_output")
    evidence.set_defaults(func=cmd_evidence)

    technology = sub.add_parser("technology")
    technology.add_argument("--timeout", type=float, default=20)
    technology.add_argument("--scan-mode", choices=("fast", "balanced"), default="balanced")
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

    crux = sub.add_parser("crux")
    crux.add_argument("--url")
    crux.add_argument(
        "--form-factor",
        action="append",
        choices=["aggregate", "mobile", "desktop", "tablet"],
    )
    crux.add_argument("--timeout", type=float, default=15)
    crux.add_argument("--output-dir", type=Path)
    crux.add_argument("--json", action="store_true", dest="json_output")
    crux.set_defaults(func=cmd_crux)

    gsc = sub.add_parser("gsc")
    gsc_sub = gsc.add_subparsers(dest="gsc_command", required=True)

    gsc_auth = gsc_sub.add_parser("auth")
    gsc_auth.add_argument("--profile", default="default")
    credential = gsc_auth.add_mutually_exclusive_group(required=True)
    credential.add_argument("--client-secret", type=Path)
    credential.add_argument("--service-account", type=Path)
    gsc_auth.add_argument("--json", action="store_true", dest="json_output")
    gsc_auth.set_defaults(func=cmd_gsc_auth)

    gsc_properties = gsc_sub.add_parser("properties")
    gsc_properties.add_argument("--profile", default="default")
    gsc_properties.add_argument("--timeout", type=float, default=20)
    gsc_properties.add_argument("--json", action="store_true", dest="json_output")
    gsc_properties.set_defaults(func=cmd_gsc_properties)

    gsc_bind = gsc_sub.add_parser("bind")
    gsc_bind.add_argument("--profile", default="default")
    gsc_bind.add_argument("--property", required=True)
    gsc_bind.add_argument("--timeout", type=float, default=20)
    gsc_bind.add_argument("--json", action="store_true", dest="json_output")
    gsc_bind.set_defaults(func=cmd_gsc_bind)

    gsc_performance = gsc_sub.add_parser("performance")
    gsc_performance.add_argument("--days", type=int, default=28)
    gsc_performance.add_argument("--compare", action=argparse.BooleanOptionalAction, default=True)
    gsc_performance.add_argument("--timeout", type=float, default=30)
    gsc_performance.add_argument("--json", action="store_true", dest="json_output")
    gsc_performance.set_defaults(func=cmd_gsc_performance)

    gsc_inspect = gsc_sub.add_parser("inspect")
    gsc_inspect.add_argument("--url", action="append")
    gsc_inspect.add_argument("--limit", type=int, default=10)
    gsc_inspect.add_argument("--timeout", type=float, default=30)
    gsc_inspect.add_argument("--json", action="store_true", dest="json_output")
    gsc_inspect.set_defaults(func=cmd_gsc_inspect)

    gsc_sitemaps = gsc_sub.add_parser("sitemaps")
    gsc_sitemaps.add_argument("--timeout", type=float, default=30)
    gsc_sitemaps.add_argument("--json", action="store_true", dest="json_output")
    gsc_sitemaps.set_defaults(func=cmd_gsc_sitemaps)

    gsc_collect = gsc_sub.add_parser("collect")
    gsc_collect.add_argument("--days", type=int, default=28)
    gsc_collect.add_argument("--inspection-limit", type=int, default=10)
    gsc_collect.add_argument("--timeout", type=float, default=30)
    gsc_collect.add_argument("--json", action="store_true", dest="json_output")
    gsc_collect.set_defaults(func=cmd_gsc_collect)

    ga4 = sub.add_parser("ga4")
    ga4_sub = ga4.add_subparsers(dest="ga4_command", required=True)

    ga4_import = ga4_sub.add_parser("import")
    ga4_import.add_argument("--profile", default="default")
    ga4_import.add_argument("--credential", type=Path, required=True)
    ga4_import.add_argument("--json", action="store_true", dest="json_output")
    ga4_import.set_defaults(func=cmd_ga4_import)

    ga4_properties = ga4_sub.add_parser("properties")
    ga4_properties.add_argument("--profile", default="default")
    ga4_properties.add_argument("--timeout", type=float, default=20)
    ga4_properties.add_argument("--json", action="store_true", dest="json_output")
    ga4_properties.set_defaults(func=cmd_ga4_properties)

    ga4_bind = ga4_sub.add_parser("bind")
    ga4_bind.add_argument("--profile", default="default")
    ga4_bind.add_argument("--property", required=True)
    ga4_bind.add_argument("--timeout", type=float, default=20)
    ga4_bind.add_argument("--json", action="store_true", dest="json_output")
    ga4_bind.set_defaults(func=cmd_ga4_bind)

    ga4_collect = ga4_sub.add_parser("collect")
    ga4_collect.add_argument("--days", type=int, default=28)
    ga4_collect.add_argument("--end-date", type=date.fromisoformat)
    ga4_collect.add_argument("--timeout", type=float, default=30)
    ga4_collect.add_argument("--json", action="store_true", dest="json_output")
    ga4_collect.set_defaults(func=cmd_ga4_collect)

    shopify_orders = sub.add_parser("shopify-orders")
    shopify_orders_sub = shopify_orders.add_subparsers(dest="shopify_orders_command", required=True)

    shopify_orders_collect = shopify_orders_sub.add_parser("collect")
    shopify_orders_collect.add_argument("--days", type=int, default=28)
    shopify_orders_collect.add_argument("--end-date", type=date.fromisoformat)
    shopify_orders_collect.add_argument("--timeout", type=float, default=30)
    shopify_orders_collect.add_argument("--json", action="store_true", dest="json_output")
    shopify_orders_collect.set_defaults(func=cmd_shopify_orders_collect)

    audit_diff = sub.add_parser("audit-diff")
    audit_diff.add_argument("--kind", choices=["all", *AUDIT_KINDS], default="all")
    audit_diff.add_argument("--from", type=Path, dest="baseline_path")
    audit_diff.add_argument("--to", type=Path, dest="current_path")
    audit_diff.add_argument("--json", action="store_true", dest="json_output")
    audit_diff.set_defaults(func=cmd_audit_diff)

    tech_audit = sub.add_parser("tech-audit")
    tech_audit_sub = tech_audit.add_subparsers(dest="tech_audit_command", required=True)

    tech_run = tech_audit_sub.add_parser("run")
    tech_run.add_argument("--max-urls", type=int, default=1000)
    tech_run.add_argument("--concurrency", type=int, default=DEFAULT_CONCURRENCY)
    tech_run.add_argument("--delay", type=float, default=DEFAULT_REQUEST_DELAY)
    tech_run.add_argument("--retries", type=int, default=2)
    tech_run.add_argument("--backoff", type=float, default=DEFAULT_BACKOFF)
    tech_run.add_argument("--timeout", type=float, default=15.0)
    tech_run.add_argument("--user-agent", default=DEFAULT_USER_AGENT)
    tech_run.add_argument("--include-subdomains", action="store_true")
    tech_run.add_argument("--load-sitemap", action=argparse.BooleanOptionalAction, default=True)
    tech_run.add_argument("--sitemap", action="append", default=[])
    tech_run.add_argument("--max-sitemaps", type=int, default=20)
    tech_run.add_argument("--max-redirects", type=int, default=10)
    tech_run.add_argument("--high-depth", type=int, default=3)
    tech_run.add_argument("--slow-ms", type=int, default=1000)
    tech_run.add_argument("--large-html-bytes", type=int, default=500000)
    tech_run.add_argument("--allow-private", action="store_true")
    tech_run.add_argument("--rendered", action="store_true")
    tech_run.add_argument("--render-limit", type=int, default=5)
    tech_run.add_argument("--render-wait-ms", type=int, default=2500)
    tech_run.add_argument("--refresh-gsc", action="store_true")
    tech_run.add_argument("--gsc-days", type=int, default=28)
    tech_run.add_argument("--gsc-inspection-limit", type=int, default=10)
    tech_run.add_argument("--scheduled", action="store_true")
    tech_run.add_argument("--notify-role")
    tech_run.add_argument("--profile")
    tech_run.add_argument("--config", type=Path)
    tech_run.add_argument("--confirm", action="store_true")
    tech_run.add_argument("--json", action="store_true", dest="json_output")
    tech_run.set_defaults(func=cmd_tech_audit_run)

    tech_continue = tech_audit_sub.add_parser("continue")
    tech_continue.add_argument("--json", action="store_true", dest="json_output")
    tech_continue.set_defaults(func=cmd_tech_audit_continue)

    tech_recrawl = tech_audit_sub.add_parser("recrawl")
    tech_recrawl.add_argument("--url", action="append", required=True)
    tech_recrawl.add_argument("--concurrency", type=int, default=DEFAULT_CONCURRENCY)
    tech_recrawl.add_argument("--delay", type=float, default=DEFAULT_REQUEST_DELAY)
    tech_recrawl.add_argument("--retries", type=int, default=2)
    tech_recrawl.add_argument("--backoff", type=float, default=DEFAULT_BACKOFF)
    tech_recrawl.add_argument("--timeout", type=float, default=15.0)
    tech_recrawl.add_argument("--user-agent", default=DEFAULT_USER_AGENT)
    tech_recrawl.add_argument("--allow-private", action="store_true")
    tech_recrawl.add_argument("--json", action="store_true", dest="json_output")
    tech_recrawl.set_defaults(func=cmd_tech_audit_recrawl)

    tech_rules = tech_audit_sub.add_parser("rules")
    tech_rules.add_argument("--json", action="store_true", dest="json_output")
    tech_rules.set_defaults(func=cmd_tech_audit_rules)

    tech_status = tech_audit_sub.add_parser("status")
    tech_status.add_argument("--json", action="store_true", dest="json_output")
    tech_status.set_defaults(func=cmd_tech_audit_status)

    tech_diff = tech_audit_sub.add_parser("diff")
    tech_diff.add_argument("--from", type=Path, dest="baseline_path")
    tech_diff.add_argument("--to", type=Path, dest="current_path")
    tech_diff.add_argument("--json", action="store_true", dest="json_output")
    tech_diff.set_defaults(func=cmd_tech_audit_diff)

    tech_schedule = tech_audit_sub.add_parser("schedule")
    tech_schedule_sub = tech_schedule.add_subparsers(dest="schedule_action", required=True)
    schedule_set = tech_schedule_sub.add_parser("set")
    schedule_set.add_argument("--every-minutes", type=int, required=True)
    schedule_set.add_argument("--notify-role")
    schedule_set.add_argument("--profile", default="")
    schedule_set.add_argument("--json", action="store_true", dest="json_output")
    schedule_set.set_defaults(func=cmd_tech_audit_schedule)
    schedule_show = tech_schedule_sub.add_parser("show")
    schedule_show.add_argument("--json", action="store_true", dest="json_output")
    schedule_show.set_defaults(func=cmd_tech_audit_schedule)
    schedule_disable = tech_schedule_sub.add_parser("disable")
    schedule_disable.add_argument("--json", action="store_true", dest="json_output")
    schedule_disable.set_defaults(func=cmd_tech_audit_schedule)

    tech_issues = tech_audit_sub.add_parser("issues")
    tech_issues_sub = tech_issues.add_subparsers(dest="issues_action", required=True)
    tech_issues_list = tech_issues_sub.add_parser("list")
    tech_issues_list.add_argument("--status", choices=("open", "planned", "fixed", "verified", "accepted"))
    tech_issues_list.add_argument("--owner")
    tech_issues_list.add_argument("--json", action="store_true", dest="json_output")
    tech_issues_list.set_defaults(func=cmd_tech_audit_issues)
    tech_issues_status = tech_issues_sub.add_parser("status")
    tech_issues_status.add_argument("fingerprint")
    tech_issues_status.add_argument("status", choices=USER_ISSUE_STATUSES)
    tech_issues_status.add_argument("--owner")
    tech_issues_status.add_argument("--note")
    tech_issues_status.add_argument("--json", action="store_true", dest="json_output")
    tech_issues_status.set_defaults(func=cmd_tech_audit_issues)

    validate = sub.add_parser("validate")
    validate.add_argument("--json", action="store_true", dest="json_output")
    validate.set_defaults(func=cmd_validate)

    doctor = sub.add_parser("doctor")
    doctor.add_argument("--json", action="store_true", dest="json_output")
    doctor.set_defaults(func=cmd_doctor)

    pages = sub.add_parser("pages")
    pages_sub = pages.add_subparsers(dest="pages_command", required=True)
    pages_refresh = pages_sub.add_parser("refresh")
    pages_refresh.add_argument("--gsc-json", type=Path)
    pages_refresh.add_argument("--business-json", type=Path)
    pages_refresh.add_argument("--json", action="store_true", dest="json_output")
    pages_refresh.set_defaults(func=cmd_content_portfolio)

    content = sub.add_parser("content")
    content_sub = content.add_subparsers(dest="content_command", required=True)
    import_hexcal = content_sub.add_parser("import-hexcal")
    import_hexcal.add_argument("--keywords-json", type=Path)
    import_hexcal.add_argument("--pipeline-json", type=Path)
    import_hexcal.add_argument("--json", action="store_true", dest="json_output")
    import_hexcal.set_defaults(func=cmd_content_import_hexcal)

    import_feishu = content_sub.add_parser("import-feishu")
    import_feishu.add_argument("--profile", required=True)
    import_feishu.add_argument("--config", type=Path)
    import_feishu.add_argument("--keywords-only", action="store_true")
    import_feishu.add_argument("--pipeline-only", action="store_true")
    import_feishu.add_argument("--limit", type=int)
    import_feishu.add_argument("--json", action="store_true", dest="json_output")
    import_feishu.set_defaults(func=cmd_content_import_feishu)

    import_draft_cmd = content_sub.add_parser("import-draft")
    import_draft_cmd.add_argument("--from-file", type=Path, required=True)
    import_draft_cmd.add_argument("--json", action="store_true", dest="json_output")
    import_draft_cmd.set_defaults(func=cmd_content_import_draft)

    cluster_brief = content_sub.add_parser("cluster-brief")
    cluster_brief.add_argument("--max-keywords", type=int, default=200)
    cluster_brief.add_argument("--json", action="store_true", dest="json_output")
    cluster_brief.set_defaults(func=cmd_content_cluster_brief)

    import_clusters_cmd = content_sub.add_parser("import-clusters")
    import_clusters_cmd.add_argument("--from-file", type=Path, required=True)
    import_clusters_cmd.add_argument("--json", action="store_true", dest="json_output")
    import_clusters_cmd.set_defaults(func=cmd_content_import_clusters)

    queue = content_sub.add_parser("queue")
    queue.add_argument("--status")
    queue.add_argument("--json", action="store_true", dest="json_output")
    queue.set_defaults(func=cmd_content_queue)

    content_status = content_sub.add_parser("status")
    content_status.add_argument("item_id")
    content_status.add_argument("status")
    content_status.add_argument("--note")
    content_status.add_argument("--json", action="store_true", dest="json_output")
    content_status.set_defaults(func=cmd_content_status)

    content_portfolio = content_sub.add_parser("portfolio")
    content_portfolio.add_argument("--gsc-json", type=Path)
    content_portfolio.add_argument("--business-json", type=Path)
    content_portfolio.add_argument("--json", action="store_true", dest="json_output")
    content_portfolio.set_defaults(func=cmd_content_portfolio)

    qc = content_sub.add_parser("qc")
    qc.add_argument("item_id")
    qc.add_argument("--json", action="store_true", dest="json_output")
    qc.set_defaults(func=cmd_content_qc)

    publish_dry_run_cmd = content_sub.add_parser("publish-dry-run")
    publish_dry_run_cmd.add_argument("item_id")
    publish_dry_run_cmd.add_argument("--blog-id", required=True)
    publish_dry_run_cmd.add_argument("--json", action="store_true", dest="json_output")
    publish_dry_run_cmd.set_defaults(func=cmd_content_publish_dry_run)

    publish_cmd = content_sub.add_parser("publish")
    publish_cmd.add_argument("item_id")
    publish_cmd.add_argument("--blog-id", required=True)
    publish_cmd.add_argument("--confirm", action="store_true")
    publish_cmd.add_argument("--allow-warnings", action="store_true")
    publish_cmd.add_argument("--timeout", type=float, default=30)
    publish_cmd.add_argument("--json", action="store_true", dest="json_output")
    publish_cmd.set_defaults(func=cmd_content_publish)

    report_cmd = content_sub.add_parser("report")
    report_cmd.add_argument("--period", choices=["daily", "weekly"], default="daily")
    report_cmd.add_argument("--date")
    report_cmd.add_argument("--json", action="store_true", dest="json_output")
    report_cmd.set_defaults(func=cmd_content_report)

    ops_cmd = content_sub.add_parser("ops")
    ops_cmd.add_argument("--json", action="store_true", dest="json_output")
    ops_cmd.set_defaults(func=cmd_content_ops)

    review_push = content_sub.add_parser("review-push")
    review_push.add_argument("item_id")
    review_push.add_argument("--role", required=True)
    review_push.add_argument("--profile", required=True)
    review_push.add_argument("--config", type=Path)
    review_push.add_argument("--confirm", action="store_true")
    review_push.add_argument("--json", action="store_true", dest="json_output")
    review_push.set_defaults(func=cmd_content_review_push)

    review_digest = content_sub.add_parser("review-digest")
    review_digest.add_argument("--item-id")
    review_digest.add_argument("--profile", required=True)
    review_digest.add_argument("--config", type=Path)
    review_digest.add_argument("--bot-id")
    review_digest.add_argument("--json", action="store_true", dest="json_output")
    review_digest.set_defaults(func=cmd_content_review_digest)

    index_queue = content_sub.add_parser("index-queue")
    index_queue.add_argument("--json", action="store_true", dest="json_output")
    index_queue.set_defaults(func=cmd_content_index_queue)

    index_submit = content_sub.add_parser("index-submit")
    index_submit.add_argument("--profile", default="default")
    index_submit.add_argument("--limit", type=int)
    index_submit.add_argument("--timeout", type=float, default=20)
    index_submit.add_argument("--confirm", action="store_true")
    index_submit.add_argument("--json", action="store_true", dest="json_output")
    index_submit.set_defaults(func=cmd_content_index_submit)

    index_status = content_sub.add_parser("index-status")
    index_status.add_argument("--inspection-json", type=Path)
    index_status.add_argument("--anomaly-days", type=int, default=12)
    index_status.add_argument("--notify-role")
    index_status.add_argument("--profile", default="")
    index_status.add_argument("--config", type=Path)
    index_status.add_argument("--confirm", action="store_true")
    index_status.add_argument("--json", action="store_true", dest="json_output")
    index_status.set_defaults(func=cmd_content_index_status)

    brief_cmd = content_sub.add_parser("brief")
    brief_cmd.add_argument("item_id")
    brief_cmd.add_argument("--json", action="store_true", dest="json_output")
    brief_cmd.set_defaults(func=cmd_content_brief)

    revise_brief_cmd = content_sub.add_parser("revise-brief")
    revise_brief_cmd.add_argument("item_id")
    revise_brief_cmd.add_argument("--json", action="store_true", dest="json_output")
    revise_brief_cmd.set_defaults(func=cmd_content_revise_brief)

    serp_cmd = content_sub.add_parser("serp-competitors")
    serp_cmd.add_argument("item_id")
    serp_cmd.add_argument("--query")
    serp_cmd.add_argument("--max-results", type=int, default=3)
    serp_cmd.add_argument("--timeout", type=float, default=20)
    serp_cmd.add_argument("--json", action="store_true", dest="json_output")
    serp_cmd.set_defaults(func=cmd_content_serp_competitors)

    assets_cmd = content_sub.add_parser("assets")
    assets_cmd.add_argument("item_id")
    assets_cmd.add_argument("--json", action="store_true", dest="json_output")
    assets_cmd.set_defaults(func=cmd_content_assets)

    asset_candidates_cmd = content_sub.add_parser("asset-candidates")
    asset_candidates_cmd.add_argument("item_id")
    asset_candidates_cmd.add_argument("--profile", required=True)
    asset_candidates_cmd.add_argument("--config", type=Path)
    asset_candidates_cmd.add_argument("--limit", type=int, default=40)
    asset_candidates_cmd.add_argument("--json", action="store_true", dest="json_output")
    asset_candidates_cmd.set_defaults(func=cmd_content_asset_candidates)

    describe_candidates_cmd = content_sub.add_parser("describe-candidates")
    describe_candidates_cmd.add_argument("item_id")
    describe_candidates_cmd.add_argument("--profile", required=True)
    describe_candidates_cmd.add_argument("--config", type=Path)
    describe_candidates_cmd.add_argument("--manifest", type=Path)
    describe_candidates_cmd.add_argument("--limit", type=int, default=20)
    describe_candidates_cmd.add_argument("--no-writeback", action="store_true")
    describe_candidates_cmd.add_argument("--confirm", action="store_true")
    describe_candidates_cmd.add_argument("--json", action="store_true", dest="json_output")
    describe_candidates_cmd.set_defaults(func=cmd_content_describe_candidates)

    apply_assets_cmd = content_sub.add_parser("apply-assets")
    apply_assets_cmd.add_argument("item_id")
    apply_assets_cmd.add_argument("--manifest", type=Path)
    apply_assets_cmd.add_argument("--json", action="store_true", dest="json_output")
    apply_assets_cmd.set_defaults(func=cmd_content_apply_assets)

    download_assets_cmd = content_sub.add_parser("download-assets")
    download_assets_cmd.add_argument("item_id")
    download_assets_cmd.add_argument("--profile", required=True)
    download_assets_cmd.add_argument("--config", type=Path)
    download_assets_cmd.add_argument("--manifest", type=Path)
    download_assets_cmd.add_argument("--json", action="store_true", dest="json_output")
    download_assets_cmd.set_defaults(func=cmd_content_download_assets)

    upload_assets_cmd = content_sub.add_parser("upload-assets")
    upload_assets_cmd.add_argument("item_id")
    upload_assets_cmd.add_argument("--manifest", type=Path)
    upload_assets_cmd.add_argument("--timeout", type=float, default=60)
    upload_assets_cmd.add_argument("--json", action="store_true", dest="json_output")
    upload_assets_cmd.set_defaults(func=cmd_content_upload_assets)

    notify_report = content_sub.add_parser("notify-report")
    notify_report.add_argument("report_path", type=Path)
    notify_report.add_argument("--role", required=True)
    notify_report.add_argument("--title", required=True)
    notify_report.add_argument("--profile", required=True)
    notify_report.add_argument("--config", type=Path)
    notify_report.add_argument("--confirm", action="store_true")
    notify_report.add_argument("--json", action="store_true", dest="json_output")
    notify_report.set_defaults(func=cmd_content_notify_report)

    reports = sub.add_parser("reports")
    reports_sub = reports.add_subparsers(dest="reports_command", required=True)
    reports_list = reports_sub.add_parser("list")
    reports_list.add_argument("--q")
    reports_list.add_argument("--category")
    reports_list.add_argument("--year", type=int)
    reports_list.add_argument("--month", type=int)
    reports_list.add_argument("--json", action="store_true", dest="json_output")
    reports_list.set_defaults(func=cmd_reports_list)

    reports_new = reports_sub.add_parser("new")
    reports_new.add_argument("--week", type=int)
    reports_new.add_argument("--year", type=int)
    reports_new.add_argument("--no-carry-over", action="store_true")
    reports_new.add_argument("--force", action="store_true")
    reports_new.add_argument("--json", action="store_true", dest="json_output")
    reports_new.set_defaults(func=cmd_reports_new)

    presentation = reports_sub.add_parser("presentation")
    presentation_sub = presentation.add_subparsers(dest="reports_presentation_command", required=True)
    for command in ("status", "generate"):
        presentation_command = presentation_sub.add_parser(command)
        presentation_command.add_argument("--year", type=int)
        presentation_command.add_argument("--week", type=int)
        presentation_command.add_argument("--max-statistics-age-hours", type=int, default=DEFAULT_MAX_STATISTICS_AGE_HOURS)
        presentation_command.add_argument("--json", action="store_true", dest="json_output")
        presentation_command.set_defaults(func=cmd_reports_presentation)

    keywords = sub.add_parser("keywords")
    keywords_sub = keywords.add_subparsers(dest="keywords_command", required=True)
    keywords_collect = keywords_sub.add_parser("collect")
    keywords_collect.add_argument("--google-ads-csv", type=Path, action="append")
    keywords_collect.add_argument("--semrush-xlsx", type=Path, action="append")
    keywords_collect.add_argument("--gsc-search-json", type=Path, action="append")
    keywords_collect.add_argument("--autocomplete-seed", action="append")
    keywords_collect.add_argument("--competitor-domain", action="append")
    keywords_collect.add_argument("--top-n", type=int, default=50)
    keywords_collect.add_argument("--timeout", type=float, default=15)
    keywords_collect.add_argument("--dry-run", action="store_true")
    keywords_collect.add_argument("--json", action="store_true", dest="json_output")
    keywords_collect.set_defaults(func=cmd_keywords_collect)

    changes = sub.add_parser("changes")
    changes_sub = changes.add_subparsers(dest="changes_command", required=True)
    changes_add = changes_sub.add_parser("add")
    changes_add.add_argument("--url", action="append", required=True)
    changes_add.add_argument("--type", choices=CHANGE_TYPES, required=True, dest="change_type")
    changes_add.add_argument("--hypothesis", required=True)
    changes_add.add_argument("--metric", action="append", required=True)
    changes_add.add_argument("--changed-at")
    changes_add.add_argument("--review-date")
    changes_add.add_argument("--review-after-days", type=int, default=28)
    changes_add.add_argument("--status", choices=CHANGE_STATUSES, default="shipped")
    changes_add.add_argument("--note")
    changes_add.add_argument("--json", action="store_true", dest="json_output")
    changes_add.set_defaults(func=cmd_changes_add)

    changes_list = changes_sub.add_parser("list")
    changes_list.add_argument("--status", choices=CHANGE_STATUSES)
    changes_list.add_argument("--due", action="store_true")
    changes_list.add_argument("--as-of")
    changes_list.add_argument("--json", action="store_true", dest="json_output")
    changes_list.set_defaults(func=cmd_changes_list)

    changes_status = changes_sub.add_parser("status")
    changes_status.add_argument("change_id")
    changes_status.add_argument("status", choices=CHANGE_STATUSES)
    changes_status.add_argument("--note")
    changes_status.add_argument("--json", action="store_true", dest="json_output")
    changes_status.set_defaults(func=cmd_changes_status)

    changes_evaluate = changes_sub.add_parser("evaluate")
    changes_evaluate.add_argument("change_id")
    changes_evaluate_gsc = changes_evaluate.add_mutually_exclusive_group()
    changes_evaluate_gsc.add_argument("--gsc-json", type=Path)
    changes_evaluate_gsc.add_argument("--refresh-gsc", action="store_true")
    changes_evaluate.add_argument("--timeout", type=float, default=30)
    changes_evaluate.add_argument("--business-json", type=Path)
    changes_evaluate.add_argument("--json", action="store_true", dest="json_output")
    changes_evaluate.set_defaults(func=cmd_changes_evaluate)

    business_signals = sub.add_parser("business-signals")
    business_signals_sub = business_signals.add_subparsers(dest="business_signals_command", required=True)
    business_signals_import = business_signals_sub.add_parser("import")
    business_signals_import.add_argument("--from-file", type=Path, required=True)
    business_signals_import.add_argument("--json", action="store_true", dest="json_output")
    business_signals_import.set_defaults(func=cmd_business_signals_import)
    business_signals_collect = business_signals_sub.add_parser("collect")
    business_signals_collect.add_argument("--json", action="store_true", dest="json_output")
    business_signals_collect.set_defaults(func=cmd_business_signals_collect)

    statistics = sub.add_parser("statistics")
    statistics_sub = statistics.add_subparsers(dest="statistics_command", required=True)
    statistics_collect = statistics_sub.add_parser("collect")
    statistics_collect.add_argument("--days", type=int, default=28)
    statistics_collect.add_argument("--timeout", type=float, default=30)
    statistics_collect.add_argument("--json", action="store_true", dest="json_output")
    statistics_collect.set_defaults(func=cmd_statistics_collect)
    statistics_regime = statistics_sub.add_parser("regime")
    statistics_regime_sub = statistics_regime.add_subparsers(dest="statistics_regime_command", required=True)
    statistics_regime_add = statistics_regime_sub.add_parser("add")
    statistics_regime_add.add_argument("--source", choices=MEASUREMENT_SOURCES, required=True)
    statistics_regime_add.add_argument("--effective-at", type=date.fromisoformat, required=True)
    statistics_regime_add.add_argument("--description", required=True)
    statistics_regime_add.add_argument("--metric", action="append", default=[])
    statistics_regime_add.add_argument("--comparable-across", action="store_true")
    statistics_regime_add.add_argument("--json", action="store_true", dest="json_output")
    statistics_regime_add.set_defaults(func=cmd_statistics_regime_add)
    statistics_regime_list = statistics_regime_sub.add_parser("list")
    statistics_regime_list.add_argument("--json", action="store_true", dest="json_output")
    statistics_regime_list.set_defaults(func=cmd_statistics_regime_list)

    backlinks = sub.add_parser("backlinks")
    backlinks_sub = backlinks.add_subparsers(dest="backlinks_command", required=True)
    backlinks_import = backlinks_sub.add_parser("import")
    backlinks_import.add_argument("--from-file", type=Path, required=True)
    backlinks_import.add_argument("--source", required=True)
    backlinks_import.add_argument("--captured-at")
    backlinks_import.add_argument("--complete", action="store_true")
    backlinks_import.add_argument("--json", action="store_true", dest="json_output")
    backlinks_import.set_defaults(func=cmd_backlinks)
    backlinks_status = backlinks_sub.add_parser("status")
    backlinks_status.add_argument("--source")
    backlinks_status.add_argument("--json", action="store_true", dest="json_output")
    backlinks_status.set_defaults(func=cmd_backlinks)
    backlinks_collect = backlinks_sub.add_parser("collect", help="Collect a paid DataForSEO backlink snapshot")
    backlinks_collect.add_argument("--confirm-paid", action="store_true", help="Confirm this command may spend DataForSEO balance")
    backlinks_collect.add_argument("--max-links", type=int, default=10_000, help="Maximum provider rows to collect (1-20000)")
    backlinks_collect.add_argument("--timeout", type=float, default=45)
    backlinks_collect.add_argument("--json", action="store_true", dest="json_output")
    backlinks_collect.set_defaults(func=cmd_backlinks)
    backlinks_gap = backlinks_sub.add_parser("gap", help="Collect paid DataForSEO competitor link intersections")
    backlinks_gap.add_argument("--competitor", action="append", required=True, help="Bare external domain; repeat for up to three")
    backlinks_gap.add_argument("--confirm-paid", action="store_true", help="Confirm this command may spend DataForSEO balance")
    backlinks_gap.add_argument("--limit", type=int, default=1_000)
    backlinks_gap.add_argument("--timeout", type=float, default=45)
    backlinks_gap.add_argument("--json", action="store_true", dest="json_output")
    backlinks_gap.set_defaults(func=cmd_backlinks)

    metadata = sub.add_parser("metadata")
    metadata_sub = metadata.add_subparsers(dest="metadata_command", required=True)
    metadata_update = metadata_sub.add_parser("update")
    metadata_update.add_argument("handle")
    metadata_update.add_argument("--resource", choices=["product", "collection", "article"], default="product")
    metadata_update.add_argument("--seo-title", dest="seo_title")
    metadata_update.add_argument("--seo-description", dest="seo_description")
    metadata_update.add_argument("--body")
    metadata_update.add_argument("--summary")
    metadata_update.add_argument("--dry-run", action="store_true")
    metadata_update.add_argument("--confirm", action="store_true")
    metadata_update.add_argument("--timeout", type=float, default=30)
    metadata_update.add_argument("--json", action="store_true", dest="json_output")
    metadata_update.set_defaults(func=cmd_metadata_update)

    ui = sub.add_parser("ui")
    ui.add_argument("--port", type=int, default=8765)
    ui.add_argument("--no-open", action="store_true")
    ui.add_argument(
        "--allow-cookieless",
        action="store_true",
        help="accept the bootstrap token on every request for WebView/cookieless browsers (e.g. Codex preview)",
    )
    ui.set_defaults(func=cmd_ui)
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
