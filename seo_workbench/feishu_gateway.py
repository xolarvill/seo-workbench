from __future__ import annotations

import json
import os
import subprocess
import tempfile
from pathlib import Path
from typing import Any


DEFAULT_CONFIG_PATH = Path(".runtime/profiles.json")


def list_records(
    *,
    profile: str,
    config_path: Path | None = None,
    base: str,
    table: str,
    field_ids: list[str] | None = None,
    limit: int | None = None,
    runner: Any = subprocess.run,
) -> list[dict[str, Any]]:
    if limit is not None and limit < 1:
        raise ValueError("limit must be at least 1")
    resolved = _load_profile(profile, config_path)
    base_config, table_config = _resolve_table(resolved, base, table)
    field_map = _field_map(table_config)
    projected = [_resolve_field(field_map, field) for field in field_ids or []]
    rows: list[dict[str, Any]] = []
    offset = 0
    for _page in range(100):
        remaining = None if limit is None else limit - len(rows)
        if remaining is not None and remaining <= 0:
            break
        page_size = min(remaining or 200, 200)
        command = _lark_command(resolved) + [
            "base",
            "+record-list",
            "--base-token",
            str(base_config["token"]),
            "--table-id",
            str(table_config["id"]),
            "--offset",
            str(offset),
            "--limit",
            str(page_size),
            "--format",
            "json",
        ]
        for field in projected:
            command += ["--field-id", field]
        payload = _run_json(command, runner=runner, operation="Base record list")
        page_rows = [_decode_record(row, field_map) for row in _items(payload) if isinstance(row, dict)]
        rows.extend(page_rows)
        if not _has_more(payload, len(page_rows), page_size) or not page_rows:
            break
        offset += len(page_rows)
    else:
        raise RuntimeError("Base record list exceeded the 20,000-record safety limit")
    return rows[:limit] if limit is not None else rows


def upsert_record(
    *,
    profile: str,
    config_path: Path | None = None,
    base: str,
    table: str,
    fields: dict[str, Any],
    record_id: str = "",
    runner: Any = subprocess.run,
) -> dict[str, Any]:
    resolved = _load_profile(profile, config_path)
    base_config, table_config = _resolve_table(resolved, base, table)
    field_map = _field_map(table_config)
    encoded = {_configured_field(field_map, name): value for name, value in fields.items()}
    with tempfile.TemporaryDirectory() as tmp:
        payload_path = Path(tmp) / "fields.json"
        _write_private_json(payload_path, encoded)
        command = _lark_command(resolved) + [
            "base",
            "+record-upsert",
            "--base-token",
            str(base_config["token"]),
            "--table-id",
            str(table_config["id"]),
            "--json",
            "@fields.json",
        ]
        if record_id:
            command += ["--record-id", record_id]
        return _run_json(command, runner=runner, operation="Base record upsert", cwd=Path(tmp))


def download_attachment(
    *,
    profile: str,
    config_path: Path | None = None,
    base: str,
    table: str,
    record_id: str,
    field: str,
    output: Path,
    identity: str = "user",
    runner: Any = subprocess.run,
) -> dict[str, Any]:
    resolved = _load_profile(profile, config_path)
    base_config, table_config = _resolve_table(resolved, base, table)
    field_map = _field_map(table_config)
    remote_field = _configured_field(field_map, field)
    get_command = _lark_command(resolved) + [
        "base",
        "+record-get",
        "--base-token",
        str(base_config["token"]),
        "--table-id",
        str(table_config["id"]),
        "--record-id",
        record_id,
        "--field-id",
        remote_field,
        "--format",
        "json",
        "--as",
        identity,
    ]
    record_payload = _run_json(get_command, runner=runner, operation="Base attachment lookup")
    records = [item for item in _items(record_payload) if isinstance(item, dict)]
    if not records:
        raise RuntimeError(f"Base record not found: {record_id}")
    fields = records[0].get("fields") if isinstance(records[0].get("fields"), dict) else records[0]
    tokens = _attachment_tokens(fields.get(remote_field) or fields.get(field))
    if not tokens:
        raise RuntimeError(f"Base attachment field is empty: {field}")
    output.parent.mkdir(parents=True, exist_ok=True)
    command = _lark_command(resolved) + [
        "base",
        "+record-download-attachment",
        "--base-token",
        str(base_config["token"]),
        "--table-id",
        str(table_config["id"]),
        "--record-id",
        record_id,
        "--file-token",
        tokens[0],
        "--output",
        str(output),
        "--overwrite",
        "--as",
        identity,
    ]
    return _run_json(command, runner=runner, operation="Base attachment download", timeout=300)


def send_role_post(
    *,
    profile: str,
    config_path: Path | None = None,
    role: str,
    title: str,
    lines: list[str],
    idempotency_key: str = "",
    runner: Any = subprocess.run,
) -> dict[str, Any]:
    if len(idempotency_key) > 50:
        raise ValueError("idempotency_key must be at most 50 characters")
    resolved = _load_profile(profile, config_path)
    receive_type, receive_id = _resolve_role(resolved, role)
    post = {
        "zh_cn": {
            "title": title,
            "content": [[{"tag": "text", "text": line}] for line in lines],
        }
    }
    params: dict[str, Any] = {"receive_id_type": receive_type}
    if idempotency_key:
        params["uuid"] = idempotency_key
    body = {"receive_id": receive_id, "msg_type": "post", "content": json.dumps(post, ensure_ascii=False)}
    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        _write_private_json(tmp_path / "params.json", params)
        _write_private_json(tmp_path / "body.json", body)
        command = _lark_command(resolved) + [
            "api",
            "POST",
            "/open-apis/im/v1/messages",
            "--params",
            "@params.json",
            "--data",
            "@body.json",
            "--as",
            "bot",
        ]
        response = _run_json(command, runner=runner, operation="Feishu message send", cwd=tmp_path)
    data = response.get("data") if isinstance(response, dict) and isinstance(response.get("data"), dict) else {}
    message_id = data.get("message_id") or (response.get("message_id") if isinstance(response, dict) else "")
    if not message_id:
        raise RuntimeError("Feishu message send returned no message_id")
    return {"message_id": str(message_id)}


def list_thread_replies(
    *,
    profile: str,
    config_path: Path | None = None,
    thread_id: str,
    runner: Any = subprocess.run,
) -> list[dict[str, Any]]:
    # ponytail: one 500-message page; add page-token pagination if real review threads exceed it.
    resolved = _load_profile(profile, config_path)
    command = _lark_command(resolved) + [
        "im",
        "+threads-messages-list",
        "--thread",
        thread_id,
        "--page-size",
        "500",
        "--format",
        "json",
        "--as",
        "bot",
    ]
    payload = _run_json(command, runner=runner, operation="Feishu thread replies")
    return [item for item in _items(payload) if isinstance(item, dict)]


def _load_profile(name: str, config_path: Path | None) -> dict[str, Any]:
    path = config_path or Path(os.environ.get("SEO_WORKBENCH_FEISHU_CONFIG", DEFAULT_CONFIG_PATH))
    if not path.is_file():
        raise FileNotFoundError(f"Feishu profile config not found: {path}")
    payload = json.loads(path.read_text(encoding="utf-8"))
    profiles = payload.get("profiles") if isinstance(payload, dict) else None
    if not isinstance(profiles, dict) or not profiles:
        raise ValueError("Feishu profile config must contain a non-empty profiles object")
    profile_name = name.strip()
    if not profile_name:
        raise ValueError("Feishu profile must be selected explicitly")
    profile = profiles.get(profile_name)
    if not isinstance(profile, dict):
        raise ValueError(f"Feishu profile not found: {profile_name}")
    if not str(profile.get("lark_cli_profile") or "").strip():
        raise ValueError(f"Feishu profile has no lark_cli_profile: {profile_name}")
    return profile


def _resolve_table(profile: dict[str, Any], base: str, table: str) -> tuple[dict[str, Any], dict[str, Any]]:
    bases = profile.get("bases") if isinstance(profile.get("bases"), dict) else {}
    base_config = bases.get(base)
    if not isinstance(base_config, dict) or not str(base_config.get("token") or "").strip():
        raise ValueError(f"Feishu Base alias not found: {base}")
    tables = base_config.get("tables") if isinstance(base_config.get("tables"), dict) else {}
    table_config = tables.get(table)
    if not isinstance(table_config, dict) or not str(table_config.get("id") or "").strip():
        raise ValueError(f"Feishu table alias not found: {base}.{table}")
    return base_config, table_config


def _resolve_role(profile: dict[str, Any], role: str) -> tuple[str, str]:
    roles = profile.get("roles") if isinstance(profile.get("roles"), dict) else {}
    role_config = roles.get(role)
    recipient_name = role_config.get("recipient") if isinstance(role_config, dict) else role_config
    recipients = profile.get("recipients") if isinstance(profile.get("recipients"), dict) else {}
    recipient = recipients.get(recipient_name)
    if not isinstance(recipient, dict):
        raise ValueError(f"Feishu role not found: {role}")
    kind = str(recipient.get("kind") or "").strip()
    if kind == "chat" and str(recipient.get("chat_id") or "").strip():
        return "chat_id", str(recipient["chat_id"])
    if kind == "user" and str(recipient.get("open_id") or "").strip():
        return "open_id", str(recipient["open_id"])
    raise ValueError(f"Feishu recipient is incomplete for role: {role}")


def _lark_command(profile: dict[str, Any]) -> list[str]:
    return ["lark-cli", "--profile", str(profile["lark_cli_profile"])]


def _field_map(table: dict[str, Any]) -> dict[str, str]:
    fields = table.get("fields")
    return {str(alias): str(remote) for alias, remote in fields.items()} if isinstance(fields, dict) else {}


def _resolve_field(field_map: dict[str, str], field: str) -> str:
    return field_map.get(field, field)


def _configured_field(field_map: dict[str, str], field: str) -> str:
    if field not in field_map:
        raise ValueError(f"Feishu field alias not found: {field}")
    return field_map[field]


def _decode_record(row: dict[str, Any], field_map: dict[str, str]) -> dict[str, Any]:
    inverse = {remote: alias for alias, remote in field_map.items()}
    fields = row.get("fields") if isinstance(row.get("fields"), dict) else {
        key: value for key, value in row.items() if key not in {"record_id", "id", "_record_id"}
    }
    decoded = {inverse.get(str(key), str(key)): value for key, value in fields.items()}
    record_id = row.get("record_id") or row.get("recordId") or row.get("_record_id") or row.get("id")
    if record_id:
        decoded["_record_id"] = str(record_id)
    return decoded


def _items(payload: Any) -> list[Any]:
    if isinstance(payload, list):
        return payload
    if not isinstance(payload, dict):
        return []
    for container in (payload, payload.get("data")):
        if isinstance(container, list):
            return container
        if isinstance(container, dict):
            fields = container.get("field_id_list")
            record_ids = container.get("record_id_list")
            values = container.get("data")
            if isinstance(fields, list) and isinstance(record_ids, list) and isinstance(values, list):
                return [
                    {**dict(zip(fields, row)), "record_id": record_id}
                    for record_id, row in zip(record_ids, values)
                    if isinstance(row, list)
                ]
            for key in ("items", "records", "messages"):
                if isinstance(container.get(key), list):
                    return container[key]
            for key in ("item", "record"):
                if isinstance(container.get(key), dict):
                    return [container[key]]
            if isinstance(container.get("fields"), dict):
                return [container]
    return []


def _has_more(payload: Any, row_count: int, page_size: int) -> bool:
    if isinstance(payload, dict):
        for container in (payload, payload.get("data")):
            if isinstance(container, dict) and "has_more" in container:
                return bool(container["has_more"])
    return row_count == page_size


def _attachment_tokens(value: Any) -> list[str]:
    tokens: list[str] = []
    if isinstance(value, str) and value.startswith("file_"):
        tokens.append(value)
    elif isinstance(value, list):
        for item in value:
            tokens.extend(_attachment_tokens(item))
    elif isinstance(value, dict):
        token = value.get("file_token") or value.get("fileToken") or value.get("token")
        if token:
            tokens.append(str(token))
        elif "value" in value:
            tokens.extend(_attachment_tokens(value["value"]))
    return list(dict.fromkeys(tokens))


def _write_private_json(path: Path, payload: Any) -> None:
    path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
    path.chmod(0o600)


def _run_json(
    command: list[str],
    *,
    runner: Any,
    operation: str,
    cwd: Path | None = None,
    timeout: float = 30,
) -> Any:
    kwargs: dict[str, Any] = {"text": True, "capture_output": True, "check": False, "timeout": timeout}
    if cwd is not None:
        kwargs["cwd"] = cwd
    try:
        completed = runner(command, **kwargs)
    except subprocess.TimeoutExpired as exc:
        raise RuntimeError(f"{operation} timed out after {timeout:g} seconds") from exc
    if completed.returncode != 0:
        detail = _redact_command_values(
            (completed.stderr or completed.stdout or "unknown error").strip()[:500], command
        )
        raise RuntimeError(f"{operation} failed: {detail}")
    try:
        return json.loads(completed.stdout or "{}")
    except json.JSONDecodeError as exc:
        raise RuntimeError(f"{operation} returned invalid JSON") from exc


def _redact_command_values(detail: str, command: list[str]) -> str:
    private_flags = {"--profile", "--base-token", "--table-id", "--field-id", "--record-id", "--file-token", "--thread"}
    for index, part in enumerate(command[:-1]):
        if part in private_flags:
            detail = detail.replace(command[index + 1], "[redacted]")
    return detail
