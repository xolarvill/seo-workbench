"""Bounded re-observation of page-local candidates, without absence verification."""
from __future__ import annotations

import json
from dataclasses import replace
from pathlib import Path
from typing import Any

from seo_workbench import state
from seo_workbench.locks import project_lock
from seo_workbench.tech_identity import IDENTITY_VERSION, LOCAL_CONFIRM_RULES
from seo_workbench.tech_issues import REGISTER_PATH, _event, _read, _timestamp, _write
from seo_workbench_tools.files import atomic_write_text


def confirm_candidates(project_dir: Path, *, limit: int = 50) -> dict[str, Any]:
    from seo_workbench import tech_audit as audit
    if not 1 <= limit <= 50:
        raise ValueError("confirmation limit must be between 1 and 50")
    latest = state.safe_project_path(project_dir, "audits/tech-audit/latest.json")
    snapshot_bytes = latest.read_bytes()
    snapshot = json.loads(snapshot_bytes)
    if snapshot.get("config_fingerprint_version") != audit.CONFIG_FINGERPRINT_VERSION:
        raise ValueError("confirmation requires a current-version audit; legacy evidence remains pending")
    values = {key: value for key, value in snapshot.get("config", {}).items() if key in audit.CrawlConfig.__dataclass_fields__}
    values["sitemap_urls"] = tuple(values.get("sitemap_urls", ()))
    config = audit.CrawlConfig(**values)
    if config.rendered:
        raise ValueError("rendered candidates require a comparable rendered audit")
    register_path = state.safe_project_path(project_dir, REGISTER_PATH)
    with project_lock(project_dir):
        register_bytes = register_path.read_bytes() if register_path.exists() else b""
        records = _read(register_path)
    already_confirmed = {r.get("fingerprint") for r in records if r.get("confirmation_status") == "confirmed" and r.get("last_seen_run") == snapshot.get("run_id")}
    candidates = [i for i in audit.load_tech_issues(project_dir) if i.get("identity_version") == IDENTITY_VERSION and i.get("confirmation_status") != "confirmed" and i["fingerprint"] not in already_confirmed]
    candidates.sort(key=lambda i: (-float(i.get("priority", {}).get("score", 0)), i["fingerprint"]))
    supported = [i for i in candidates if i["rule_id"] in LOCAL_CONFIRM_RULES][:limit]
    unsupported = [i for i in candidates if i["rule_id"] not in LOCAL_CONFIRM_RULES]
    selected = [*supported, *unsupported[:max(0, limit - len(supported))]]
    rows = [{"fingerprint": i["fingerprint"], "status": "pending", "reason": "requires_graph_target_or_sitemap_coverage"} for i in selected if i not in supported]
    report: dict[str, Any] = {"schema_version": "technical-confirmation-v1", "baseline_run": snapshot.get("run_id"), "selected": len(selected), "unselected": max(0, len(candidates) - len(selected)), "requires_coverage_count": len(unsupported), "absence_verification": False, "results": rows}
    if not supported:
        return {**report, "confirmed": 0}
    # At most one document plus one redirect per selected candidate; no transport
    # retries. Robots is shared overhead, also using the persistent host gate.
    recrawl, recrawl_path = audit.recrawl_urls(project_dir, list(dict.fromkeys(i["url"] for i in supported)), replace(config, concurrency=1, retries=0, max_redirects=1))
    fresh_pages = audit.load_tech_inventory(project_dir, recrawl_path)
    fresh = {i["fingerprint"] for i in audit.evaluate_rules(fresh_pages, [], [], config, coverage_complete=False)}
    by_url = {p["url"]: p for p in fresh_pages}
    for issue in supported:
        page = by_url.get(issue["url"])
        quality_key = "http_eligible" if issue["rule_id"] in {"HTTP_4XX", "HTTP_5XX"} else "html_eligible"
        eligible = bool(page and audit._page_quality(page)[quality_key] and audit._page_quality(page)["status"] != "unavailable" and not page.get("error") and not page.get("redirect_limit_exceeded"))
        present = eligible and issue["fingerprint"] in fresh
        rows.append({"fingerprint": issue["fingerprint"], "status": "confirmed" if present else "not_reproduced" if eligible else "pending", "reason": "repeated_page_observation" if present else "no_absence_claim" if eligible else "unavailable_evidence"})
    at = _timestamp(None)
    with project_lock(project_dir):
        # The audit can change during network I/O. Never confirm against a newer
        # inventory/config or overwrite a concurrent operator decision silently.
        if latest.read_bytes() != snapshot_bytes:
            for row in rows:
                row.update(status="pending", reason="baseline_changed")
        elif (register_path.read_bytes() if register_path.exists() else b"") != register_bytes:
            for row in rows:
                row.update(status="pending", reason="operator_or_register_changed")
        else:
            records = _read(register_path)
            by_fp = {r.get("fingerprint"): r for r in records}
            for row in rows:
                record = by_fp.get(row["fingerprint"])
                if record is None or record.get("last_seen_run") != snapshot.get("run_id"):
                    row.update(status="pending", reason="register_changed_or_missing")
                    continue
                record.setdefault("history", []).append({"event": "candidate_confirmation", "at": at, "run_id": recrawl["run_id"], **row})
                record["confirmation_status"] = row["status"] if row["status"] == "confirmed" else "candidate"
                record["confirmation_reason"] = row["reason"]
                if row["status"] == "confirmed" and record.get("status") in {"fixed", "verified"}:
                    _event(record, "reopened", at, recrawl["run_id"], previous_status=record["status"])
                    record.update(status="open", verification_status="failed")
            _write(register_path, records)
    report.update(confirmed=sum(r["status"] == "confirmed" for r in rows), evidence_path=str(recrawl_path))
    output = state.safe_project_path(project_dir, f"audits/tech-audit/confirmation-{recrawl['run_id']}.json")
    atomic_write_text(output, json.dumps(report, ensure_ascii=False, indent=2) + "\n")
    return {**report, "report_path": str(output)}
