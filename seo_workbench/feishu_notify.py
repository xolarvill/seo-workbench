from __future__ import annotations

import json
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from seo_workbench import state
from seo_workbench.feishu_gateway import send_role_post
from seo_workbench_tools.files import atomic_write_text


def send_report_via_feishu_gateway(
    project_dir: Path,
    report_path: Path,
    *,
    title: str,
    role: str,
    profile: str,
    config_path: Path | None = None,
    runner: Any = subprocess.run,
) -> tuple[dict[str, Any], Path]:
    report_path = _project_relative_report_path(project_dir, report_path)
    path = state.safe_project_path(project_dir, report_path)
    content = path.read_text(encoding="utf-8")
    lines = _message_lines(content)
    response = send_role_post(
        profile=profile,
        config_path=config_path,
        role=role,
        title=title,
        lines=lines,
        runner=runner,
    )
    message_id = str(response.get("message_id") or "")
    if not message_id:
        raise RuntimeError("Feishu message send returned no message_id")
    result = {
        "schema_version": "feishu-notification-v1",
        "collection_status": "sent",
        "notification_sent": True,
        "sent_at": datetime.now(timezone.utc).isoformat(),
        "profile": profile,
        "role": role,
        "title": title,
        "report_path": report_path.as_posix(),
        "message_id": message_id,
    }
    output = state.safe_project_path(project_dir, f"audits/runs/{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}-feishu-notification.json")
    output.parent.mkdir(parents=True, exist_ok=True)
    atomic_write_text(output, json.dumps(result, ensure_ascii=False, indent=2) + "\n", mode=0o600)
    return result, output


def _message_lines(content: str) -> list[str]:
    lines = ["✅ Status: notification sent via Feishu."]
    for raw in content.splitlines():
        line = raw.strip()
        if not line or line == "Status: draft only, no notification sent.":
            continue
        lines.append(_readable_report_line(line))
    return lines[:40] or ["⚠️ Empty report"]


def _readable_report_line(line: str) -> str:
    heading = line.lstrip("#").strip()
    if line.startswith("#") and heading:
        return f"📌 {heading}"
    if line.startswith(("- ", "* ")):
        return f"  • {line[2:].replace('`', '').strip()}"
    return line.replace("`", "")


def _project_relative_report_path(project_dir: Path, report_path: Path) -> Path:
    if report_path.is_absolute():
        try:
            return report_path.resolve(strict=False).relative_to(project_dir.resolve(strict=False))
        except ValueError as exc:
            raise ValueError(f"report_path must be inside project directory: {report_path}") from exc

    project_parts = project_dir.parts
    report_parts = report_path.parts
    if len(report_parts) >= len(project_parts) and report_parts[: len(project_parts)] == project_parts:
        return Path(*report_parts[len(project_parts) :])
    return report_path
