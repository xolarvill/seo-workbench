import json
import subprocess
from pathlib import Path

import pytest

from seo_workbench.feishu_gateway import (
    download_attachment,
    list_records,
    list_thread_replies,
    send_role_post,
    upsert_record,
)


def _config(tmp_path: Path) -> Path:
    path = tmp_path / "profiles.json"
    path.write_text(
        json.dumps(
            {
                "profiles": {
                    "hexcal-seo": {
                        "lark_cli_profile": "hexcal-seo",
                        "recipients": {"review": {"kind": "chat", "chat_id": "oc_private"}},
                        "roles": {"seo_review": {"recipient": "review"}},
                        "bases": {
                            "dcdb": {
                                "token": "bascn_private",
                                "tables": {
                                    "blog_pipeline": {
                                        "id": "tbl_private",
                                        "fields": {
                                            "title": "fld_title",
                                            "status": "fld_status",
                                            "contents": "fld_contents",
                                        },
                                    }
                                },
                            }
                        },
                    }
                },
            }
        ),
        encoding="utf-8",
    )
    return path


def test_list_records_decodes_remote_field_ids(tmp_path: Path) -> None:
    calls = []

    def runner(cmd, **kwargs):
        calls.append(cmd)
        payload = {"data": {"items": [{"record_id": "rec1", "fields": {"fld_title": "Draft"}}], "has_more": False}}
        return subprocess.CompletedProcess(cmd, 0, stdout=json.dumps(payload), stderr="")

    rows = list_records(
        profile="hexcal-seo",
        config_path=_config(tmp_path),
        base="dcdb",
        table="blog_pipeline",
        field_ids=["title"],
        runner=runner,
    )

    assert rows == [{"title": "Draft", "_record_id": "rec1"}]
    assert calls[0][:3] == ["lark-cli", "--profile", "hexcal-seo"]
    assert "bascn_private" in calls[0]
    assert "tbl_private" in calls[0]
    assert "fld_title" in calls[0]


def test_list_records_decodes_lark_columnar_rows(tmp_path: Path) -> None:
    def runner(cmd, **kwargs):
        payload = {
            "data": {
                "field_id_list": ["fld_title", "fld_status"],
                "record_id_list": ["rec1"],
                "data": [["Draft", "approved"]],
            }
        }
        return subprocess.CompletedProcess(cmd, 0, stdout=json.dumps(payload), stderr="")

    rows = list_records(
        profile="hexcal-seo",
        config_path=_config(tmp_path),
        base="dcdb",
        table="blog_pipeline",
        runner=runner,
    )

    assert rows == [{"title": "Draft", "status": "approved", "_record_id": "rec1"}]


def test_upsert_record_encodes_aliases_in_private_payload(tmp_path: Path) -> None:
    payloads = []

    def runner(cmd, **kwargs):
        payloads.append(json.loads((Path(kwargs["cwd"]) / "fields.json").read_text(encoding="utf-8")))
        return subprocess.CompletedProcess(cmd, 0, stdout=json.dumps({"data": {"record_id": "rec1"}}), stderr="")

    upsert_record(
        profile="hexcal-seo",
        config_path=_config(tmp_path),
        base="dcdb",
        table="blog_pipeline",
        record_id="rec1",
        fields={"status": "approved"},
        runner=runner,
    )

    assert payloads == [{"fld_status": "approved"}]


def test_upsert_record_rejects_unconfigured_field_alias(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="field alias not found"):
        upsert_record(
            profile="hexcal-seo",
            config_path=_config(tmp_path),
            base="dcdb",
            table="blog_pipeline",
            fields={"remote_field_id": "value"},
        )


def test_send_role_post_keeps_message_and_recipient_out_of_argv(tmp_path: Path) -> None:
    calls = []
    payloads = []

    def runner(cmd, **kwargs):
        calls.append(cmd)
        cwd = Path(kwargs["cwd"])
        payloads.append(
            (
                json.loads((cwd / "params.json").read_text(encoding="utf-8")),
                json.loads((cwd / "body.json").read_text(encoding="utf-8")),
            )
        )
        return subprocess.CompletedProcess(cmd, 0, stdout=json.dumps({"data": {"message_id": "om_1"}}), stderr="")

    response = send_role_post(
        profile="hexcal-seo",
        config_path=_config(tmp_path),
        role="seo_review",
        title="Review",
        lines=["Draft body"],
        idempotency_key="review-1",
        runner=runner,
    )

    assert response == {"message_id": "om_1"}
    assert "oc_private" not in calls[0]
    assert "Draft body" not in calls[0]
    assert payloads[0][0] == {"receive_id_type": "chat_id", "uuid": "review-1"}
    assert payloads[0][1]["receive_id"] == "oc_private"
    assert "Draft body" in payloads[0][1]["content"]


def test_send_role_post_requires_confirmed_message_id(tmp_path: Path) -> None:
    def runner(cmd, **kwargs):
        return subprocess.CompletedProcess(cmd, 0, stdout=json.dumps({"code": 0, "data": {}}), stderr="")

    with pytest.raises(RuntimeError, match="no message_id"):
        send_role_post(
            profile="hexcal-seo",
            config_path=_config(tmp_path),
            role="seo_review",
            title="Review",
            lines=["Draft body"],
            runner=runner,
        )


def test_download_attachment_resolves_field_alias_and_file_token(tmp_path: Path) -> None:
    output = tmp_path / "asset.jpg"
    calls = []

    def runner(cmd, **kwargs):
        calls.append(cmd)
        if "+record-get" in cmd:
            payload = {"data": {"record": {"record_id": "rec1", "fields": {"fld_contents": [{"file_token": "file_1"}]}}}}
            return subprocess.CompletedProcess(cmd, 0, stdout=json.dumps(payload), stderr="")
        output.write_bytes(b"image")
        return subprocess.CompletedProcess(cmd, 0, stdout=json.dumps({"ok": True}), stderr="")

    download_attachment(
        profile="hexcal-seo",
        config_path=_config(tmp_path),
        base="dcdb",
        table="blog_pipeline",
        record_id="rec1",
        field="contents",
        output=output,
        runner=runner,
    )

    assert "fld_contents" in calls[0]
    assert "file_1" in calls[1]
    assert output.read_bytes() == b"image"


def test_list_thread_replies_unwraps_lark_envelope(tmp_path: Path) -> None:
    def runner(cmd, **kwargs):
        return subprocess.CompletedProcess(
            cmd,
            0,
            stdout=json.dumps({"data": {"messages": [{"message_id": "om_1"}]}}),
            stderr="",
        )

    replies = list_thread_replies(
        profile="hexcal-seo", config_path=_config(tmp_path), thread_id="om_root", runner=runner
    )

    assert replies == [{"message_id": "om_1"}]


def test_gateway_times_out_instead_of_blocking_forever(tmp_path: Path) -> None:
    def runner(cmd, **kwargs):
        raise subprocess.TimeoutExpired(cmd, kwargs["timeout"])

    with pytest.raises(RuntimeError, match="timed out after 30 seconds"):
        list_records(
            profile="hexcal-seo",
            config_path=_config(tmp_path),
            base="dcdb",
            table="blog_pipeline",
            runner=runner,
        )
