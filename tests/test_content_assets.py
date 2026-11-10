import json
import subprocess
from pathlib import Path

import pytest

from seo_workbench import state
from seo_workbench.cli import main
from seo_workbench.content_assets import (
    apply_asset_urls,
    collect_inline_rids,
    describe_asset_candidates,
    download_asset_files_from_feishu,
    patch_html_with_asset_urls,
    upload_asset_files_to_shopify,
    write_asset_candidates_from_feishu,
    write_asset_manifest,
)
from seo_workbench.content_publish import build_publish_payload
from seo_workbench.product_anchors import load_product_anchors


FEISHU_CONFIG = Path(__file__).resolve().parents[1] / "tests/fixtures/feishu-profile.json"


def test_project_asset_binding_uses_bot_and_reports_denied_catalog(tmp_path: Path) -> None:
    project_dir = tmp_path / "project"
    state.init_state("shopify", "Hexcal", "https://example.com", project_dir=project_dir)
    (project_dir / "content/blog-pipeline.jsonl").write_text(json.dumps({"id": "rec1"}) + "\n")
    config = json.loads(FEISHU_CONFIG.read_text())
    config["profiles"]["seo-profile"]["identity"] = "bot"
    profile_path = project_dir / ".runtime/feishu/assets.json"
    profile_path.parent.mkdir(parents=True)
    profile_path.write_text(json.dumps(config))
    binding = project_dir / ".runtime/integrations/asset-library.json"
    binding.parent.mkdir(parents=True)
    binding.write_text(json.dumps({"profile": "seo-profile", "config_path": ".runtime/feishu/assets.json"}))
    calls = []

    def runner(cmd, **kwargs):
        calls.append(cmd)
        return subprocess.CompletedProcess(cmd, 1, stdout="", stderr='{"error":{"code":91403,"message":"permission denied"}}')

    report, path = write_asset_candidates_from_feishu(project_dir, "rec1", runner=runner)

    assert report["collection_status"] == "failed"
    assert report["candidate_count"] == 0
    assert report["errors"] and "91403" in report["errors"][0]["message"]
    assert len(calls) == 1  # Denied Base is not repeatedly searched or reported as empty.
    assert calls[0][calls[0].index("--as") + 1] == "bot"
    assert json.loads(path.read_text())["collection_status"] == "failed"


def test_asset_binding_rejects_config_outside_project_runtime(tmp_path: Path) -> None:
    project_dir = tmp_path / "project"
    state.init_state("shopify", "Hexcal", "https://example.com", project_dir=project_dir)
    binding = project_dir / ".runtime/integrations/asset-library.json"
    binding.parent.mkdir(parents=True)
    binding.write_text(json.dumps({"profile": "p", "config_path": "../other/.runtime/profiles.json"}))
    with pytest.raises(ValueError, match="project-local"):
        write_asset_candidates_from_feishu(project_dir, "rec1")


def test_download_recovers_missing_cache_using_recorded_source_table(tmp_path: Path) -> None:
    project_dir = tmp_path / "project"
    state.init_state("shopify", "Hexcal", "https://example.com", project_dir=project_dir)
    manifest = project_dir / "content/assets/rec1.json"
    manifest.write_text(json.dumps({"assets": [{"rid": "recCover", "role": "feature", "source_table": "ugc_historical", "local_path": "content/assets/files/recCover"}]}))
    calls = []

    def runner(cmd, **kwargs):
        calls.append(cmd)
        if "+record-get" in cmd:
            return subprocess.CompletedProcess(cmd, 0, stdout=json.dumps({"data": {"record": {"record_id": "recCover", "fields": {"replace_with_attachment_field_id": [{"file_token": "file_cover"}]}}}}), stderr="")
        Path(cmd[cmd.index("--output") + 1]).write_bytes(b"\xff\xd8\xffimage")
        return subprocess.CompletedProcess(cmd, 0, stdout='{"ok":true}', stderr="")

    report, _ = download_asset_files_from_feishu(project_dir, "rec1", profile="seo-profile", config_path=FEISHU_CONFIG, runner=runner)
    assert report["collection_status"] == "ok" and report["downloaded"] == ["recCover"]
    assert len(calls) == 2
    table_id = json.loads(FEISHU_CONFIG.read_text())["profiles"]["seo-profile"]["bases"]["dcdb"]["tables"]["ugc_historical"]["id"]
    assert calls[0][calls[0].index("--table-id") + 1] == table_id


def test_upload_resumes_existing_shopify_file_without_duplicate_create(tmp_path: Path) -> None:
    project_dir = tmp_path / "project"
    state.init_state("shopify", "Store", "https://example.com", project_dir=project_dir)
    manifest = project_dir / "content/assets/rec1.json"
    manifest.write_text(json.dumps({"assets": [{"rid": "recCover", "role": "feature", "local_path": "content/assets/files/recCover", "shopify_file_id": "gid://shopify/MediaImage/12", "upload_error": "CDN was still processing"}]}))
    calls = []

    def graphql(query, variables):
        calls.append(query)
        assert "FileNode" in query
        return {"data": {"node": {"id": "gid://shopify/MediaImage/12", "fileStatus": "READY", "image": {"url": "https://cdn.shopify.com/cover.jpg"}}}}

    report, _ = upload_asset_files_to_shopify(project_dir, "rec1", graphql_runner=graphql)
    assert report["collection_status"] == "ok" and len(calls) == 1
    asset = json.loads(manifest.read_text())["assets"][0]
    assert asset["url"] == "https://cdn.shopify.com/cover.jpg" and "upload_error" not in asset


def test_collect_inline_rids_preserves_document_order() -> None:
    assert collect_inline_rids('<p><img data-rid="recA1" /></p><img alt="x" data-rid="recB2">') == ["recA1", "recB2"]


def test_asset_manifest_flags_inline_ref_mismatch(tmp_path: Path) -> None:
    project_dir = tmp_path / "project"
    state.init_state("shopify", "Store", "https://example.com", project_dir=project_dir)
    record = {
        "id": "rec1",
        "feature_image_refs": ["recFeature"],
        "inline_image_refs": ["recInline"],
        "draft_html": '<p><img data-rid="recOther" /></p>',
    }
    (project_dir / "content/blog-pipeline.jsonl").write_text(json.dumps(record) + "\n", encoding="utf-8")

    manifest, path = write_asset_manifest(project_dir, "rec1")

    assert path == project_dir / "content/assets/rec1.json"
    assert manifest["assets"][0] == {"rid": "recFeature", "role": "feature", "resolved": False}
    assert {warning["code"] for warning in manifest["warnings"]} == {"inline_refs.missing_from_html", "inline_placeholders.not_in_refs"}


def test_asset_manifest_preserves_existing_asset_state(tmp_path: Path) -> None:
    project_dir = tmp_path / "project"
    state.init_state("shopify", "Store", "https://example.com", project_dir=project_dir)
    (project_dir / "content/blog-pipeline.jsonl").write_text(
        json.dumps({"id": "rec1", "feature_image_refs": ["recFeature"], "inline_image_refs": ["recInline"]}) + "\n",
        encoding="utf-8",
    )
    manifest = project_dir / "content/assets/rec1.json"
    manifest.parent.mkdir(parents=True, exist_ok=True)
    manifest.write_text(
        json.dumps(
            {
                "assets": [
                    {"rid": "recFeature", "role": "inline", "local_path": "content/assets/files/recFeature"},
                    {"rid": "recOld", "role": "inline", "local_path": "content/assets/files/recOld"},
                ]
            }
        ),
        encoding="utf-8",
    )

    saved, _ = write_asset_manifest(project_dir, "rec1")

    assert saved["assets"][0]["role"] == "feature"
    assert saved["assets"][0]["local_path"] == "content/assets/files/recFeature"
    assert {asset["rid"] for asset in saved["assets"]} == {"recFeature", "recInline"}


def test_publish_payload_includes_image_ref_warnings() -> None:
    report = build_publish_payload(
        {
            "id": "rec1",
            "status": "approved",
            "title": "Title",
            "slug": "title",
            "scheduled_at": "2026-08-01T00:00:00Z",
            "draft_html": '<p><img data-rid="recOther" /></p>',
            "inline_image_refs": ["recInline"],
        },
        project_url="https://example.com",
        blog_id="100",
    )

    codes = {warning["code"] for warning in report["warnings"]}
    assert "inline_refs.missing_from_html" in codes
    assert "inline_placeholders.not_in_refs" in codes


def test_apply_asset_urls_patches_html_and_publish_image(tmp_path: Path) -> None:
    project_dir = tmp_path / "project"
    state.init_state("shopify", "Store", "https://example.com", project_dir=project_dir)
    (project_dir / "content/blog-pipeline.jsonl").write_text(
        json.dumps(
            {
                "id": "rec1",
                "status": "approved",
                "title": "Ready",
                "slug": "ready",
                "scheduled_at": "2026-08-01T00:00:00Z",
                "feature_image_refs": ["recFeature"],
                "inline_image_refs": ["recInline"],
                "draft_html": '<p><img data-rid="recInline" alt="Old alt" /></p>',
            }
        )
        + "\n",
        encoding="utf-8",
    )
    manifest = project_dir / "manifest.json"
    manifest.write_text(
        json.dumps(
            {
                "assets": [
                    {"rid": "recFeature", "role": "feature", "url": "https://cdn.example.com/feature.jpg", "alt": "Feature"},
                    {"rid": "recInline", "role": "inline", "url": "https://cdn.example.com/inline.jpg", "alt": "Inline"},
                ]
            }
        ),
        encoding="utf-8",
    )

    report, _ = apply_asset_urls(project_dir, "rec1", manifest_path=manifest)
    record = json.loads((project_dir / "content/blog-pipeline.jsonl").read_text(encoding="utf-8"))
    publish = build_publish_payload(record, project_url="https://example.com", blog_id="100")

    assert report["applied_inline_rids"] == ["recInline"]
    assert 'src="https://cdn.example.com/inline.jpg"' in record["draft_html"]
    assert record["feature_image_url"] == "https://cdn.example.com/feature.jpg"
    assert publish["article"]["image"] == {"url": "https://cdn.example.com/feature.jpg", "altText": "Feature"}
    assert publish["warnings"] == []


def test_patch_html_with_asset_urls_escapes_values() -> None:
    patched = patch_html_with_asset_urls(
        '<img data-rid="recInline" alt="Old">',
        {"recInline": {"rid": "recInline", "url": 'https://cdn.example.com/a"b.jpg', "alt": 'A " B'}},
    )

    assert '&quot;' in patched


def test_download_asset_files_from_feishu_updates_manifest(tmp_path: Path) -> None:
    project_dir = tmp_path / "project"
    state.init_state("shopify", "Acme", "https://example.com", project_dir=project_dir)
    manifest = project_dir / "content/assets/rec1.json"
    manifest.write_text(json.dumps({"assets": [{"rid": "recInline", "role": "inline", "resolved": False}]}), encoding="utf-8")
    calls = []

    def runner(cmd, **kwargs):
        calls.append((cmd, kwargs))
        table_id = cmd[cmd.index("--table-id") + 1]
        if "current" in table_id:
            return subprocess.CompletedProcess(cmd, 1, stdout="", stderr="not found")
        if "+record-get" in cmd:
            payload = {"data": {"items": [{"fields": {"replace_with_attachment_field_id": [{"file_token": "file_1"}]}}]}}
            return subprocess.CompletedProcess(cmd, 0, stdout=json.dumps(payload), stderr="")
        output = Path(cmd[cmd.index("--output") + 1])
        output.write_bytes(b"image")
        return subprocess.CompletedProcess(cmd, 0, stdout=json.dumps({"path": str(output)}), stderr="")

    report, path = download_asset_files_from_feishu(
        project_dir,
        "rec1",
        profile="seo-profile",
        config_path=FEISHU_CONFIG,
        runner=runner,
    )
    saved = json.loads(path.read_text(encoding="utf-8"))

    assert report["collection_status"] == "ok"
    assert report["downloaded"] == ["recInline"]
    assert saved["assets"][0]["source_table"] == "ugc_historical"
    assert saved["assets"][0]["local_path"] == "content/assets/files/recInline"
    assert calls[0][0][:3] == ["lark-cli", "--profile", "seo-profile"]
    assert calls[-1][0][-2:] == ["--as", "user"]


def test_download_asset_files_from_feishu_reports_failure(tmp_path: Path) -> None:
    project_dir = tmp_path / "project"
    state.init_state("shopify", "Acme", "https://example.com", project_dir=project_dir)
    manifest = project_dir / "content/assets/rec1.json"
    manifest.write_text(json.dumps({"assets": [{"rid": "recInline", "role": "inline"}]}), encoding="utf-8")

    def runner(cmd, **kwargs):
        return subprocess.CompletedProcess(cmd, 1, stdout="", stderr="missing")

    report, _ = download_asset_files_from_feishu(
        project_dir, "rec1", profile="seo-profile", config_path=FEISHU_CONFIG, runner=runner
    )

    assert report["collection_status"] == "failed"
    assert report["failed"][0]["rid"] == "recInline"


def test_download_asset_files_rejects_manifest_path_traversal(tmp_path: Path) -> None:
    project_dir = tmp_path / "project"
    state.init_state("shopify", "Acme", "https://example.com", project_dir=project_dir)
    manifest = project_dir / "content/assets/rec1.json"
    manifest.write_text(json.dumps({"assets": [{"rid": "../../escape", "role": "inline"}]}), encoding="utf-8")

    with pytest.raises(ValueError, match="invalid Feishu record ID"):
        download_asset_files_from_feishu(project_dir, "rec1", profile="seo-profile")
    assert not (tmp_path / "escape").exists()


def test_upload_asset_files_to_shopify_updates_manifest_url(tmp_path: Path) -> None:
    project_dir = tmp_path / "project"
    state.init_state("shopify", "Store", "https://example.com", project_dir=project_dir)
    image = project_dir / "content/assets/files/recInline"
    image.parent.mkdir(parents=True, exist_ok=True)
    image.write_bytes(b"\x89PNG\r\n\x1a\nimage")
    manifest = project_dir / "content/assets/rec1.json"
    manifest.write_text(json.dumps({"assets": [{"rid": "recInline", "role": "inline", "local_path": "content/assets/files/recInline", "alt": "Inline"}]}), encoding="utf-8")
    uploads = []

    def graphql(query, variables):
        if "stagedUploadsCreate" in query:
            return {
                "data": {
                    "stagedUploadsCreate": {
                        "stagedTargets": [{"url": "https://upload.example.com", "resourceUrl": "https://staged.example.com/image", "parameters": [{"name": "key", "value": "value"}]}],
                        "userErrors": [],
                    }
                }
            }
        return {
            "data": {
                "fileCreate": {
                    "files": [{"id": "gid://shopify/MediaImage/1", "fileStatus": "READY", "image": {"url": "https://cdn.shopify.com/image.png"}}],
                    "userErrors": [],
                }
            }
        }

    def upload(target, file_path, mime, timeout):
        uploads.append((target["url"], file_path.name, mime, timeout))

    report, _ = upload_asset_files_to_shopify(project_dir, "rec1", graphql_runner=graphql, upload_runner=upload, timeout=5)
    saved = json.loads(manifest.read_text(encoding="utf-8"))

    assert report["collection_status"] == "ok"
    assert report["uploaded"] == ["recInline"]
    assert uploads == [("https://upload.example.com", "recInline", "image/png", 5)]
    assert saved["assets"][0]["url"] == "https://cdn.shopify.com/image.png"


def test_upload_asset_files_to_shopify_waits_for_async_image_url(tmp_path: Path, monkeypatch) -> None:
    project_dir = tmp_path / "project"
    state.init_state("shopify", "Store", "https://example.com", project_dir=project_dir)
    image = project_dir / "content/assets/files/recInline"
    image.parent.mkdir(parents=True, exist_ok=True)
    image.write_bytes(b"\x89PNG\r\n\x1a\nimage")
    manifest = project_dir / "content/assets/rec1.json"
    manifest.write_text(json.dumps({"assets": [{"rid": "recInline", "role": "inline", "local_path": "content/assets/files/recInline"}]}), encoding="utf-8")
    monkeypatch.setattr("seo_workbench.content_assets.time.sleep", lambda _: None)

    def graphql(query, variables):
        if "stagedUploadsCreate" in query:
            return {"data": {"stagedUploadsCreate": {"stagedTargets": [{"url": "https://upload.example.com", "resourceUrl": "https://staged.example.com/image", "parameters": []}], "userErrors": []}}}
        if "fileCreate" in query:
            return {"data": {"fileCreate": {"files": [{"id": "gid://shopify/MediaImage/1", "fileStatus": "PROCESSING", "image": None}], "userErrors": []}}}
        return {"data": {"node": {"id": variables["id"], "fileStatus": "READY", "image": {"url": "https://cdn.shopify.com/ready.png"}}}}

    report, _ = upload_asset_files_to_shopify(project_dir, "rec1", graphql_runner=graphql, upload_runner=lambda *_: None, timeout=1)
    saved = json.loads(manifest.read_text(encoding="utf-8"))

    assert report["collection_status"] == "ok"
    assert saved["assets"][0]["url"] == "https://cdn.shopify.com/ready.png"
    assert saved["assets"][0]["file_status"] == "READY"


def test_upload_asset_files_to_shopify_resizes_large_jpeg(tmp_path: Path, monkeypatch) -> None:
    project_dir = tmp_path / "project"
    state.init_state("shopify", "Store", "https://example.com", project_dir=project_dir)
    image = project_dir / "content/assets/files/recInline"
    image.parent.mkdir(parents=True, exist_ok=True)
    image.write_bytes(b"\xff\xd8\xff" + (b"x" * (15 * 1024 * 1024 + 1)))
    manifest = project_dir / "content/assets/rec1.json"
    manifest.write_text(json.dumps({"assets": [{"rid": "recInline", "role": "inline", "local_path": "content/assets/files/recInline"}]}), encoding="utf-8")
    monkeypatch.setattr("seo_workbench.content_assets.shutil.which", lambda name: "/usr/bin/sips")
    resize_calls = []

    def resize_runner(cmd, **kwargs):
        resize_calls.append(cmd)
        image.write_bytes(b"\xff\xd8\xffsmall")
        return subprocess.CompletedProcess(cmd, 0, stdout="", stderr="")

    def graphql(query, variables):
        if "stagedUploadsCreate" in query:
            return {"data": {"stagedUploadsCreate": {"stagedTargets": [{"url": "https://upload.example.com", "resourceUrl": "https://staged.example.com/image", "parameters": []}], "userErrors": []}}}
        return {"data": {"fileCreate": {"files": [{"id": "gid://shopify/MediaImage/1", "fileStatus": "READY", "image": {"url": "https://cdn.shopify.com/image.jpg"}}], "userErrors": []}}}

    report, _ = upload_asset_files_to_shopify(
        project_dir,
        "rec1",
        graphql_runner=graphql,
        upload_runner=lambda *_: None,
        resize_runner=resize_runner,
    )
    saved = json.loads(manifest.read_text(encoding="utf-8"))

    assert report["collection_status"] == "ok"
    assert resize_calls[0][:3] == ["sips", "-Z", "2400"]
    assert saved["assets"][0]["resized_for_shopify"] is True


def test_upload_asset_files_to_shopify_rejects_unsupported_image(tmp_path: Path) -> None:
    project_dir = tmp_path / "project"
    state.init_state("shopify", "Store", "https://example.com", project_dir=project_dir)
    image = project_dir / "content/assets/files/recInline"
    image.parent.mkdir(parents=True, exist_ok=True)
    image.write_bytes(b"RIFFxxxxWEBP")
    manifest = project_dir / "content/assets/rec1.json"
    manifest.write_text(json.dumps({"assets": [{"rid": "recInline", "role": "inline", "local_path": "content/assets/files/recInline"}]}), encoding="utf-8")

    report, _ = upload_asset_files_to_shopify(project_dir, "rec1", graphql_runner=lambda *_: {}, upload_runner=lambda *_: None)

    assert report["collection_status"] == "failed"
    assert "convert to png" in report["failed"][0]["message"]


def test_content_assets_cli_outputs_json(tmp_path: Path, capsys) -> None:
    project_dir = tmp_path / "project"
    state.init_state("shopify", "Store", "https://example.com", project_dir=project_dir)
    (project_dir / "content/blog-pipeline.jsonl").write_text(json.dumps({"id": "rec1", "draft_html": ""}) + "\n", encoding="utf-8")

    assert main(["--project-dir", str(project_dir), "content", "assets", "rec1", "--json"]) == 0
    payload = json.loads(capsys.readouterr().out)

    assert payload["ok"] is True
    assert Path(payload["path"]).name == "rec1.json"


def test_write_asset_candidates_from_feishu_filters_and_writes_manifest(tmp_path: Path) -> None:
    project_dir = tmp_path / "project"
    state.init_state("shopify", "Acme", "https://example.com", project_dir=project_dir)
    (project_dir / "content/blog-pipeline.jsonl").write_text(
        json.dumps({"id": "rec1", "product_anchor": ["studio"]}) + "\n",
        encoding="utf-8",
    )
    (project_dir / "context").mkdir(parents=True, exist_ok=True)
    (project_dir / "context/product-anchors.json").write_text(
        json.dumps({"studio": [{"title": "Acme Studio", "handle": "acme-studio"}]}),
        encoding="utf-8",
    )
    calls = []

    def runner(cmd, **kwargs):
        calls.append((cmd, kwargs))
        table_id = cmd[cmd.index("--table-id") + 1]
        table = "ugc_current" if "current" in table_id else ("ugc_historical" if "historical" in table_id else "official_v3")
        rows = {
            "ugc_current": [
                {
                    "_record_id": "recGood",
                    "contents_number": "HX-1",
                    "product": ["Acme Studio"],
                    "content_type": "Photo",
                    "rating": "PUGC",
                    "times_used": 1,
                    "mmx": "Clean studio shot",
                },
                {
                    "_record_id": "recOther",
                    "product": ["Single Monitor Arm"],
                    "content_type": "Photo",
                    "times_used": 0,
                },
                {
                    "_record_id": "recUsed",
                    "product": ["Acme Studio"],
                    "content_type": "Photo",
                    "times_used": 3,
                },
            ],
            "ugc_historical": [],
            "official_v3": [],
        }[table]
        return subprocess.CompletedProcess(cmd, 0, stdout=json.dumps(rows), stderr="")

    report, path = write_asset_candidates_from_feishu(
        project_dir,
        "rec1",
        profile="seo-profile",
        config_path=FEISHU_CONFIG,
        runner=runner,
    )

    assert report["candidate_count"] == 1
    assert report["candidates"][0]["rid"] == "recGood"
    assert report["candidates"][0]["mmx_visual_description"] == "Clean studio shot"
    assert path == project_dir / "content/assets/rec1-candidates.json"
    assert calls[0][0][:3] == ["lark-cli", "--profile", "seo-profile"]
    assert json.loads(path.read_text(encoding="utf-8"))["candidate_count"] == 1


def test_describe_asset_candidates_downloads_mmx_and_writes_back(tmp_path: Path, monkeypatch) -> None:
    project_dir = tmp_path / "project"
    state.init_state("shopify", "Acme", "https://example.com", project_dir=project_dir)
    manifest = project_dir / "content/assets/rec1-candidates.json"
    manifest.write_text(
        json.dumps(
            {
                "candidates": [
                    {"rid": "recFresh", "table": "ugc_current", "mmx_visual_description": ""},
                    {"rid": "recCached", "table": "ugc_current", "mmx_visual_description": "Already described"},
                ]
            }
        ),
        encoding="utf-8",
    )
    monkeypatch.setenv("MINIMAX_API_KEY", "mmx-test")
    calls = []
    payloads = []

    def runner(cmd, **kwargs):
        calls.append((cmd, kwargs))
        if "+record-get" in cmd:
            payload = {"data": {"items": [{"fields": {"replace_with_attachment_field_id": [{"file_token": "file_1"}]}}]}}
            return subprocess.CompletedProcess(cmd, 0, stdout=json.dumps(payload), stderr="")
        if "+record-download-attachment" in cmd:
            Path(cmd[cmd.index("--output") + 1]).write_bytes(b"image")
            return subprocess.CompletedProcess(cmd, 0, stdout="{}", stderr="")
        if cmd[:3] == ["mmx", "vision", "describe"]:
            return subprocess.CompletedProcess(cmd, 0, stdout=json.dumps({"content": "Clean angled product shot."}), stderr="")
        if "+record-upsert" in cmd:
            payloads.append(json.loads((Path(kwargs["cwd"]) / "fields.json").read_text(encoding="utf-8")))
            return subprocess.CompletedProcess(cmd, 0, stdout=json.dumps({"ok": True}), stderr="")
        raise AssertionError(cmd)

    report, path = describe_asset_candidates(
        project_dir,
        "rec1",
        profile="seo-profile",
        config_path=FEISHU_CONFIG,
        runner=runner,
    )
    saved = json.loads(path.read_text(encoding="utf-8"))

    assert report["collection_status"] == "ok"
    assert report["cache_hit"] == 1
    assert report["described"] == 1
    assert report["write_back_count"] == 1
    assert saved["candidates"][0]["mmx_visual_description"] == "Clean angled product shot."
    assert payloads == [{"replace_with_visual_description_field_id": "Clean angled product shot."}]
    mmx_call = next(cmd for cmd, _kwargs in calls if cmd[:3] == ["mmx", "vision", "describe"])
    assert "--api-key" not in mmx_call
    assert "mmx-test" not in mmx_call


def test_product_anchors_are_optional_and_project_scoped(tmp_path: Path) -> None:
    project_dir = tmp_path / "project"
    state.init_state("shopify", "Store", "https://example.com", project_dir=project_dir)

    assert load_product_anchors(project_dir) == {}

    (project_dir / "context").mkdir(parents=True, exist_ok=True)
    (project_dir / "context/product-anchors.json").write_text(
        json.dumps({"studio": [{"title": "Acme Studio", "handle": "acme-studio"}, {"title": "Broken"}]}),
        encoding="utf-8",
    )

    assert load_product_anchors(project_dir) == {"studio": [{"title": "Acme Studio", "handle": "acme-studio"}]}


def test_content_describe_candidates_cli_outputs_json(tmp_path: Path, capsys, monkeypatch) -> None:
    project_dir = tmp_path / "project"
    state.init_state("shopify", "Store", "https://example.com", project_dir=project_dir)

    def fake_describe(project_dir, item_id, **kwargs):
        return {"collection_status": "ok", "item_id": item_id, "described": 1}, project_dir / "content/assets/rec1-candidates.json"

    monkeypatch.setattr("seo_workbench.cli.describe_asset_candidates", fake_describe)

    assert main(["--project-dir", str(project_dir), "content", "describe-candidates", "rec1", "--profile", "seo-profile", "--json"]) == 1
    assert "requires --confirm" in json.loads(capsys.readouterr().out)["error"]
    assert main(["--project-dir", str(project_dir), "content", "describe-candidates", "rec1", "--profile", "seo-profile", "--confirm", "--json"]) == 0
    payload = json.loads(capsys.readouterr().out)

    assert payload["ok"] is True
    assert payload["described"] == 1


def test_content_apply_assets_cli_outputs_json(tmp_path: Path, capsys) -> None:
    project_dir = tmp_path / "project"
    state.init_state("shopify", "Store", "https://example.com", project_dir=project_dir)
    (project_dir / "content/blog-pipeline.jsonl").write_text(
        json.dumps({"id": "rec1", "draft_html": '<img data-rid="recInline">'}) + "\n",
        encoding="utf-8",
    )
    manifest = project_dir / "manifest.json"
    manifest.write_text(json.dumps({"assets": [{"rid": "recInline", "role": "inline", "url": "https://cdn.example.com/i.jpg"}]}), encoding="utf-8")

    assert main(["--project-dir", str(project_dir), "content", "apply-assets", "rec1", "--manifest", str(manifest), "--json"]) == 0
    payload = json.loads(capsys.readouterr().out)

    assert payload["ok"] is True
    assert payload["applied_inline_rids"] == ["recInline"]


def test_content_asset_candidates_cli_outputs_json(tmp_path: Path, capsys, monkeypatch) -> None:
    project_dir = tmp_path / "project"
    state.init_state("shopify", "Store", "https://example.com", project_dir=project_dir)

    def fake_candidates(project_dir, item_id, **kwargs):
        return {"collection_status": "ok", "candidate_count": 1, "candidates": [{"rid": "rec1"}]}, project_dir / "content/assets/rec1-candidates.json"

    monkeypatch.setattr("seo_workbench.cli.write_asset_candidates_from_feishu", fake_candidates)

    assert main(["--project-dir", str(project_dir), "content", "asset-candidates", "rec1", "--profile", "seo-profile", "--json"]) == 0
    payload = json.loads(capsys.readouterr().out)

    assert payload["ok"] is True
    assert payload["candidate_count"] == 1


def test_content_download_assets_cli_outputs_json(tmp_path: Path, capsys, monkeypatch) -> None:
    project_dir = tmp_path / "project"
    state.init_state("shopify", "Store", "https://example.com", project_dir=project_dir)

    def fake_download(project_dir, item_id, **kwargs):
        return {"collection_status": "ok", "downloaded": ["rec1"], "failed": []}, project_dir / "content/assets/rec1.json"

    monkeypatch.setattr("seo_workbench.cli.download_asset_files_from_feishu", fake_download)

    assert main(["--project-dir", str(project_dir), "content", "download-assets", "rec1", "--profile", "seo-profile", "--json"]) == 0
    payload = json.loads(capsys.readouterr().out)

    assert payload["ok"] is True
    assert payload["downloaded"] == ["rec1"]


def test_content_upload_assets_cli_outputs_json(tmp_path: Path, capsys, monkeypatch) -> None:
    project_dir = tmp_path / "project"
    state.init_state("shopify", "Store", "https://example.com", project_dir=project_dir)

    def fake_upload(project_dir, item_id, **kwargs):
        return {"collection_status": "ok", "uploaded": ["rec1"], "failed": []}, project_dir / "content/assets/rec1.json"

    monkeypatch.setattr("seo_workbench.cli.upload_asset_files_to_shopify", fake_upload)

    assert main(["--project-dir", str(project_dir), "content", "upload-assets", "rec1", "--json"]) == 0
    payload = json.loads(capsys.readouterr().out)

    assert payload["ok"] is True
    assert payload["uploaded"] == ["rec1"]
