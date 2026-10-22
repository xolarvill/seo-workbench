from __future__ import annotations

import json
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from seo_workbench import state
from seo_workbench.locks import project_lock
from seo_workbench_tools.files import atomic_write_text


REGISTER_PATH = "strategy/technical-issues.jsonl"
ISSUE_STATUSES = ("open", "planned", "fixed", "verified", "accepted")
USER_ISSUE_STATUSES = ("open", "planned", "fixed", "accepted")


def load_issue_register(project_dir: Path) -> list[dict[str, Any]]:
    return _read(state.safe_project_path(project_dir, REGISTER_PATH))


def list_issue_register(
    project_dir: Path,
    *,
    status: str = "",
    owner: str = "",
) -> dict[str, Any]:
    if status and status not in ISSUE_STATUSES:
        raise ValueError(f"issue status must be one of: {', '.join(ISSUE_STATUSES)}")
    records = load_issue_register(project_dir)
    if status:
        records = [record for record in records if record.get("status") == status]
    if owner:
        records = [record for record in records if str(record.get("owner", "")).casefold() == owner.casefold()]
    records.sort(key=lambda record: (-float(record.get("priority", 0) or 0), str(record.get("url", ""))))
    return {
        "schema_version": "technical-issue-list-v1",
        "collection_status": "ok",
        "count": len(records),
        "counts": dict(sorted(Counter(str(record.get("status", "")) for record in records).items())),
        "issues": records,
    }


def update_issue_status(
    project_dir: Path,
    fingerprint: str,
    status: str,
    *,
    owner: str = "",
    note: str = "",
    now: datetime | None = None,
) -> dict[str, Any]:
    if status not in USER_ISSUE_STATUSES:
        raise ValueError(f"operator issue status must be one of: {', '.join(USER_ISSUE_STATUSES)}")
    if status == "accepted" and not note.strip():
        raise ValueError("accepted issues require a decision note")
    path = state.safe_project_path(project_dir, REGISTER_PATH)
    updated_at = _timestamp(now)
    with project_lock(project_dir):
        records = _read(path)
        record = next((item for item in records if item.get("fingerprint") == fingerprint), None)
        if record is None:
            raise ValueError(f"technical issue not found: {fingerprint}")
        previous = str(record.get("status", ""))
        record["status"] = status
        if owner:
            record["owner"] = owner.strip()
        record["verification_status"] = "pending" if status == "fixed" else "not_requested"
        record.setdefault("history", []).append(
            {
                "event": "status_changed",
                "at": updated_at,
                "previous_status": previous,
                "status": status,
                "owner": record.get("owner", ""),
                "note": note.strip(),
            }
        )
        _write(path, records)
    return record


def sync_issue_register(
    project_dir: Path,
    issues: list[dict[str, Any]],
    baseline_issues: list[dict[str, Any]],
    *,
    run_id: str,
    verification_allowed: bool,
    verification_provisional: bool = False,
    now: datetime | None = None,
) -> tuple[dict[str, Any], Path]:
    path = state.safe_project_path(project_dir, REGISTER_PATH)
    at = _timestamp(now)
    current = {str(issue.get("fingerprint", "")): issue for issue in issues if issue.get("fingerprint")}
    baseline = {str(issue.get("fingerprint", "")) for issue in baseline_issues if issue.get("fingerprint")}
    created = verified = reopened = failed = provisional = 0
    with project_lock(project_dir):
        records = _read(path)
        by_fingerprint = {str(record.get("fingerprint", "")): record for record in records}
        for fingerprint, issue in current.items():
            record = by_fingerprint.get(fingerprint)
            if record is None:
                record = _record(issue, run_id, at)
                records.append(record)
                by_fingerprint[fingerprint] = record
                created += 1
            else:
                record.update(_latest(issue, run_id))
                if not any(event.get("event") == "observed" and event.get("run_id") == run_id for event in record.get("history", [])):
                    record.setdefault("history", []).append({"event": "observed", "at": at, "run_id": run_id, "observation_hash": issue.get("observation_hash"), "confirmation_status": issue.get("confirmation_status", "not_observed")})
                confirmed = issue.get("confirmation_status") != "candidate"
                if record.get("status") == "verified" and confirmed:
                    _event(record, "reopened", at, run_id, previous_status="verified")
                    record["status"] = "open"
                    reopened += 1
                elif record.get("status") == "fixed" and confirmed and record.get("last_verification_run") != run_id:
                    _event(record, "verification_failed", at, run_id, previous_status="fixed")
                    record["status"] = "open"
                    record["verification_status"] = "failed"
                    record["last_verification_run"] = run_id
                    failed += 1
        if verification_allowed or verification_provisional:
            for fingerprint in baseline - set(current):
                record = by_fingerprint.get(fingerprint)
                if record is None or record.get("status") in {"verified", "accepted"}:
                    continue
                previous = str(record.get("status", ""))
                if record.get("confirmation_status") == "candidate" and previous != "fixed":
                    record["confirmation_reason"] = "not_reproduced_no_fix_claim"
                    _event(record, "candidate_not_reproduced", at, run_id, previous_status=previous)
                    continue
                if verification_allowed:
                    record["status"] = "verified"
                    record["verification_status"] = "passed"
                    record["last_verification_run"] = run_id
                    _event(record, "verified_absent", at, run_id, previous_status=previous)
                    verified += 1
                elif record.get("status") == "fixed":
                    record["verification_status"] = "provisional"
                    record["last_verification_run"] = run_id
                    _event(record, "provisional_verified_absent", at, run_id, previous_status=previous)
                    provisional += 1
        _write(path, records)
    counts = Counter(str(record.get("status", "")) for record in records)
    return (
        {
            "schema_version": "technical-issue-sync-v1",
            "collection_status": "ok",
            "run_id": run_id,
            "verification_allowed": verification_allowed,
            "verification_provisional": verification_provisional,
            "count": len(records),
            "counts": dict(sorted(counts.items())),
            "created": created,
            "verified": verified,
            "provisional_verified": provisional,
            "reopened": reopened,
            "verification_failed": failed,
        },
        path,
    )


def _record(issue: dict[str, Any], run_id: str, at: str) -> dict[str, Any]:
    return {
        "schema_version": "technical-issue-v1",
        "fingerprint": issue.get("fingerprint", ""),
        **_latest(issue, run_id),
        "first_seen_run": run_id,
        "status": "open",
        "owner": "",
        "verification_status": "not_requested",
        "history": [{"event": "opened", "at": at, "run_id": run_id}],
    }


def _latest(issue: dict[str, Any], run_id: str) -> dict[str, Any]:
    priority = issue.get("priority") if isinstance(issue.get("priority"), dict) else {}
    return {
        **{key: issue[key] for key in ("identity", "identity_version", "observation_hash", "evidence", "confirmation_status", "confirmation_reason") if key in issue},
        "rule_id": issue.get("rule_id", ""),
        "title": issue.get("title", ""),
        "severity": issue.get("severity", ""),
        "category": issue.get("category", ""),
        "url": issue.get("url", ""),
        "template": issue.get("template", ""),
        "priority": float(priority.get("score", 0) or 0),
        "priority_tier": priority.get("tier", ""),
        "remediation_guidance": issue.get("remediation_guidance", ""),
        "last_seen_run": run_id,
    }


def _event(record: dict[str, Any], event: str, at: str, run_id: str, *, previous_status: str) -> None:
    record.setdefault("history", []).append(
        {"event": event, "at": at, "run_id": run_id, "previous_status": previous_status}
    )


def _timestamp(value: datetime | None) -> str:
    return (value or datetime.now(timezone.utc)).astimezone(timezone.utc).isoformat()


def _read(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    records = []
    for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        if not line.strip():
            continue
        try:
            record = json.loads(line)
        except json.JSONDecodeError as exc:
            raise ValueError(f"invalid technical issue register line {line_number}: {exc.msg}") from exc
        if not isinstance(record, dict):
            raise ValueError(f"invalid technical issue register line {line_number}: expected an object")
        records.append(record)
    return records


def _write(path: Path, records: list[dict[str, Any]]) -> None:
    atomic_write_text(path, "".join(json.dumps(record, ensure_ascii=False) + "\n" for record in records))


def preview_identity_migration(project_dir: Path) -> dict[str, Any]:
    """Read-only mapping; never infer an operator decision or close old issues."""
    import hashlib
    from seo_workbench.tech_identity import identity_fingerprint, issue_identity
    path = state.safe_project_path(project_dir, REGISTER_PATH)
    # A single immutable snapshot supplies evidence missing from old ledgers.
    # Index by old fingerprint, never by URL alone (which loses distinct targets).
    with project_lock(project_dir):
        records = _read(path)
        register_bytes = path.read_bytes() if path.exists() else b""
    observations: dict[str, dict[str, Any]] = {}
    audit_root = state.safe_project_path(project_dir, "audits/tech-audit")
    if audit_root.exists():
        for artifact in sorted(audit_root.glob("runs/*/normalized/issues.jsonl")):
            try:
                artifact = state.safe_project_path(project_dir, artifact.relative_to(project_dir))
            except ValueError:
                continue
            for issue in _read(artifact):
                if issue.get("fingerprint"):
                    observations[str(issue["fingerprint"])] = issue
    groups: dict[str, dict[str, Any]] = {}
    unresolved = []
    for record in records:
        old_fp = str(record.get("fingerprint", ""))
        issue = {**record, **observations.get(old_fp, {})}
        identity = issue_identity(issue)
        if identity is None:
            unresolved.append({"fingerprint": old_fp, "rule_id": record.get("rule_id"), "reason": "missing_identity_evidence"})
            continue
        fp = identity_fingerprint(identity)
        group = groups.setdefault(fp, {"fingerprint": fp, "identity": identity, "members": []})
        # Keep complete records, including every decision note and event. The
        # preview makes no choice between conflicting owners/statuses/decisions.
        group["members"].append(record)
    for group in groups.values():
        members = group["members"]
        decisions = {(r.get("status", ""), r.get("owner", "")) for r in members}
        group["requires_decision"] = len(decisions) > 1
        group["legacy_fingerprints"] = [r.get("fingerprint") for r in members]
    return {
        "schema_version": "technical-identity-preview-v1", "read_only": True,
        "register_sha256": hashlib.sha256(register_bytes).hexdigest(),
        "record_count": len(records), "proposed_identity_count": len(groups),
        "merge_groups": sum(len(g["members"]) > 1 for g in groups.values()),
        "decision_conflicts": sum(g["requires_decision"] for g in groups.values()),
        "unresolved_count": len(unresolved), "unresolved": unresolved,
        "groups": sorted(groups.values(), key=lambda g: g["fingerprint"]),
        "applied": False,
    }
