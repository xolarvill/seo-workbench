from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import time
from html import escape
from pathlib import Path
from typing import Any
from urllib.request import Request, urlopen

from seo_workbench import state
from seo_workbench.feishu_gateway import download_attachment, list_records, upsert_record
from seo_workbench_tools.files import atomic_write_text


IMG_DATA_RID_RE = re.compile(r'<img\s+[^>]*?data-rid="(rec[A-Za-z0-9]+)"[^>]*?>', re.I)
IMG_TAG_DATA_RID_RE = re.compile(r'<img\s+([^>]*?)data-rid="(rec[A-Za-z0-9]+)"([^>]*?)\s*/?>', re.I)
ALT_RE = re.compile(r'\balt="([^"]*)"', re.I)
UGC_TABLES = ("ugc_current", "ugc_historical", "official_v3")
MIME_TO_EXT = {"image/jpeg": ".jpg", "image/png": ".png", "image/gif": ".gif"}
MAX_SHOPIFY_IMAGE_BYTES = 15 * 1024 * 1024
SHOPIFY_RESIZE_WIDTH_PX = 2400
MMX_PROMPT = (
    "Describe this Hexcal desk-setup image in 1-2 sentences for blog-post image matching. "
    "Mention the main product/object, shot composition, and visual mood. "
    "Avoid generic phrases like 'a desk setup'."
)
TIMES_USED_HARD_CAP = 3
ALLOWED_CONTENT_TYPES = {"Photo", "Rendering"}
RATING_RANK = {"Brand Contents": 3, "PUGC": 2, "UGC": 1, "": 0}
FEISHU_RECORD_ID_RE = re.compile(r"rec[A-Za-z0-9]+")
ANCHOR_PRODUCTS = {
    "studio": {
        "Hexcal Studio",
        "Hexcal Studio Extension Kit",
        "Under Desk Drawer",
        "Under Desk Cable Management Tray",
        "Hexcal Light",
        "Hexcal Power",
        "Hexcal Cable Management",
        "Tech Pouch",
        "Desk Mat Bundle",
        "Hexcal Desk Mat",
    },
    "plus": {"Hexcal Studio Plus (Silver)", "Hexcal Studio Plus (Dark Gray)"},
    "ergon": {
        "Hexcal Elevate Standing Desk",
        "Hexcal Ascend Standing Desk",
        "Hexcal Arm",
        "Single Monitor Arm",
        "Heavy Duty Monitor Arm",
        "Monitor Mount System",
        "Hexcal Inspire Chair",
    },
}
ASSET_FIELDS = {
    table: {
        name: name
        for name in (
            "contents_number", "product", "content_type", "rating", "notes", "creator",
            "times_used", "large_file_link", "mmx",
        )
    }
    for table in UGC_TABLES
}
ASSET_FIELDS["official_v3"]["rating"] = ""
STAGED_UPLOADS_MUTATION = """
mutation StagedUploadsCreate($input: [StagedUploadInput!]!) {
  stagedUploadsCreate(input: $input) {
    stagedTargets {
      url
      resourceUrl
      parameters { name value }
    }
    userErrors { field message }
  }
}
"""
FILE_CREATE_MUTATION = """
mutation FileCreate($files: [FileCreateInput!]!) {
  fileCreate(files: $files) {
    files {
      id
      fileStatus
      alt
      createdAt
      ... on MediaImage {
        image { url width height }
      }
    }
    userErrors { field message }
  }
}
"""
FILE_NODE_QUERY = """
query FileNode($id: ID!) {
  node(id: $id) {
    ... on MediaImage {
      id
      fileStatus
      image { url width height }
    }
  }
}
"""


def build_asset_manifest(record: dict[str, Any]) -> dict[str, Any]:
    feature_refs = list(record.get("feature_image_refs") or [])
    inline_refs = list(record.get("inline_image_refs") or [])
    placeholders = collect_inline_rids(record.get("draft_html") or "")
    assets = [{"rid": rid, "role": "feature", "resolved": False} for rid in feature_refs]
    assets.extend({"rid": rid, "role": "inline", "resolved": False} for rid in inline_refs)
    warnings = image_ref_warnings(record)
    return {
        "collection_status": "ok",
        "item_id": record.get("id", ""),
        "assets": assets,
        "feature_refs": feature_refs,
        "inline_refs": inline_refs,
        "inline_placeholders": placeholders,
        "warnings": warnings,
    }


def write_asset_manifest(project_dir: Path, item_id: str) -> tuple[dict[str, Any], Path]:
    record = _find_pipeline_record(project_dir, item_id)
    manifest = build_asset_manifest(record)
    output_dir = state.safe_project_path(project_dir, "content/assets")
    output_dir.mkdir(parents=True, exist_ok=True)
    path = output_dir / f"{_safe_name(item_id)}.json"
    if path.exists():
        previous = {asset.get("rid"): asset for asset in json.loads(path.read_text(encoding="utf-8")).get("assets", []) if isinstance(asset, dict)}
        for asset in manifest["assets"]:
            old = previous.get(asset.get("rid"))
            if old:
                asset.update(old)
                asset["role"] = "feature" if asset.get("rid") in manifest["feature_refs"] else "inline"
    atomic_write_text(path, json.dumps(manifest, ensure_ascii=False, indent=2) + "\n")
    return manifest, path


def write_asset_candidates_from_feishu(
    project_dir: Path,
    item_id: str,
    *,
    profile: str,
    config_path: Path | None = None,
    limit: int = 40,
    runner: Any = subprocess.run,
) -> tuple[dict[str, Any], Path]:
    _require_hexcal_project(project_dir)
    record = _find_pipeline_record(project_dir, item_id)
    allowed = _allowed_products(record)
    candidates = []
    for table in UGC_TABLES:
        for row in _list_asset_rows(table, profile, config_path, runner):
            candidate = _asset_candidate(table, row)
            if not candidate:
                continue
            if allowed and not (set(candidate["product"]) & allowed):
                continue
            candidates.append(candidate)
    candidates.sort(key=lambda item: (-RATING_RANK.get(item["rating"], 0), item["times_used"], item["table"], item["rid"]))
    candidates = candidates[:limit]
    report = {
        "collection_status": "ok",
        "item_id": item_id,
        "allowed_products": sorted(allowed),
        "candidate_count": len(candidates),
        "candidates": candidates,
    }
    path = state.safe_project_path(project_dir, f"content/assets/{_safe_name(item_id)}-candidates.json")
    path.parent.mkdir(parents=True, exist_ok=True)
    atomic_write_text(path, json.dumps(report, ensure_ascii=False, indent=2) + "\n")
    return report, path


def describe_asset_candidates(
    project_dir: Path,
    item_id: str,
    *,
    profile: str,
    config_path: Path | None = None,
    manifest_path: Path | None = None,
    limit: int = 20,
    write_back: bool = True,
    runner: Any = subprocess.run,
) -> tuple[dict[str, Any], Path]:
    _require_hexcal_project(project_dir)
    manifest_path = manifest_path or state.safe_project_path(project_dir, f"content/assets/{_safe_name(item_id)}-candidates.json")
    if not manifest_path.exists():
        raise FileNotFoundError(f"{manifest_path} not found; run content asset-candidates first")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    files_dir = state.safe_project_path(project_dir, "content/assets/description-files")
    files_dir.mkdir(parents=True, exist_ok=True)
    cache_hit = 0
    described = 0
    write_back_count = 0
    failed: list[dict[str, str]] = []
    remaining = max(0, limit)
    for candidate in manifest.get("candidates", []):
        if not isinstance(candidate, dict) or not candidate.get("rid") or not candidate.get("table"):
            continue
        cached = str(candidate.get("mmx_visual_description") or "").strip()
        if cached and not cached.startswith("("):
            cache_hit += 1
            continue
        if remaining <= 0:
            continue
        rid = str(candidate["rid"])
        table = str(candidate["table"])
        try:
            local = state.safe_project_path(
                project_dir, f"content/assets/description-files/{_feishu_record_id(rid)}"
            )
            _download_table_attachment(rid, table, local, profile, config_path, runner)
            desc = _mmx_describe(local, runner=runner).strip()[:500]
            candidate["mmx_visual_description"] = desc
            described += 1
            remaining -= 1
            if write_back and ASSET_FIELDS.get(table, {}).get("mmx"):
                _upsert_asset_field(rid, table, {ASSET_FIELDS[table]["mmx"]: desc}, profile, config_path, runner)
                write_back_count += 1
        except Exception as exc:  # noqa: BLE001
            message = str(exc)[:300]
            candidate["mmx_visual_description"] = f"(mmx error: {type(exc).__name__})"
            failed.append({"rid": rid, "table": table, "message": message})
    manifest["mmx_enrichment"] = {
        "cache_hit": cache_hit,
        "described": described,
        "write_back_count": write_back_count,
        "failed": failed,
    }
    atomic_write_text(manifest_path, json.dumps(manifest, ensure_ascii=False, indent=2) + "\n")
    report = {
        "collection_status": "partial" if failed else "ok",
        "item_id": item_id,
        **manifest["mmx_enrichment"],
    }
    return report, manifest_path


def apply_asset_urls(project_dir: Path, item_id: str, *, manifest_path: Path | None = None) -> tuple[dict[str, Any], Path]:
    manifest_path = manifest_path or state.safe_project_path(project_dir, f"content/assets/{_safe_name(item_id)}.json")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    urls = {
        item["rid"]: item
        for item in manifest.get("assets", [])
        if isinstance(item, dict) and item.get("rid") and item.get("url")
    }
    if not urls:
        raise ValueError("asset manifest has no resolved asset URLs")
    applied: list[str] = []
    feature = next((item for item in urls.values() if item.get("role") == "feature"), None)

    def patch(record: dict[str, Any]) -> dict[str, Any]:
        html = record.get("draft_html") or ""
        updated_html = patch_html_with_asset_urls(html, urls, applied)
        record["draft_html"] = updated_html
        if feature:
            record["feature_image_url"] = feature["url"]
            record["feature_image_alt"] = feature.get("alt") or ""
        record["asset_urls_applied"] = True
        return record

    record = _update_pipeline_record(project_dir, item_id, patch)
    report = {
        "collection_status": "ok",
        "item_id": item_id,
        "applied_inline_rids": applied,
        "feature_image_url": record.get("feature_image_url", ""),
    }
    output_dir = state.safe_project_path(project_dir, "audits/publish")
    output_dir.mkdir(parents=True, exist_ok=True)
    path = output_dir / f"{_safe_name(item_id)}-assets-applied.json"
    atomic_write_text(path, json.dumps(report, ensure_ascii=False, indent=2) + "\n")
    return report, path


def download_asset_files_from_feishu(
    project_dir: Path,
    item_id: str,
    *,
    profile: str,
    config_path: Path | None = None,
    manifest_path: Path | None = None,
    runner: Any = subprocess.run,
) -> tuple[dict[str, Any], Path]:
    _require_hexcal_project(project_dir)
    if manifest_path is None:
        manifest_path = state.safe_project_path(project_dir, f"content/assets/{_safe_name(item_id)}.json")
        if not manifest_path.exists():
            _, manifest_path = write_asset_manifest(project_dir, item_id)
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    files_dir = state.safe_project_path(project_dir, "content/assets/files")
    files_dir.mkdir(parents=True, exist_ok=True)
    downloaded = []
    failed = []
    for asset in manifest.get("assets", []):
        if not isinstance(asset, dict) or not asset.get("rid"):
            continue
        if asset.get("local_path"):
            continue
        rid = str(asset["rid"])
        out = state.safe_project_path(project_dir, f"content/assets/files/{_feishu_record_id(rid)}")
        table, error = _download_asset(rid, out, profile, config_path, runner)
        if table:
            asset["local_path"] = str(out.relative_to(project_dir))
            asset["source_table"] = table
            asset["downloaded"] = True
            downloaded.append(rid)
        else:
            asset["downloaded"] = False
            asset["download_error"] = error
            failed.append({"rid": rid, "message": error})
    manifest["downloaded_count"] = len(downloaded)
    manifest["download_errors"] = failed
    atomic_write_text(manifest_path, json.dumps(manifest, ensure_ascii=False, indent=2) + "\n")
    report = {
        "collection_status": "partial" if failed and downloaded else ("failed" if failed else "ok"),
        "item_id": item_id,
        "downloaded": downloaded,
        "failed": failed,
        "manifest_path": str(manifest_path.relative_to(project_dir)),
    }
    return report, manifest_path


def _require_hexcal_project(project_dir: Path) -> None:
    name = str((state.load_state(project_dir).get("project") or {}).get("name") or "").strip().casefold()
    if name != "hexcal":
        raise ValueError("Feishu asset catalogs are available only for the Hexcal project adapter")


def upload_asset_files_to_shopify(
    project_dir: Path,
    item_id: str,
    *,
    manifest_path: Path | None = None,
    graphql_runner: Any | None = None,
    upload_runner: Any | None = None,
    resize_runner: Any = subprocess.run,
    timeout: float = 60,
) -> tuple[dict[str, Any], Path]:
    manifest_path = manifest_path or state.safe_project_path(project_dir, f"content/assets/{_safe_name(item_id)}.json")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if graphql_runner is None:
        from seo_workbench.content_publish import _shopify_graphql, load_shopify_credentials

        credentials = load_shopify_credentials(project_dir)
        graphql_runner = lambda query, variables: _shopify_graphql(credentials, query=query, variables=variables, timeout=timeout)
    upload_runner = upload_runner or _post_staged_upload
    uploaded = []
    failed = []
    for asset in manifest.get("assets", []):
        if not isinstance(asset, dict) or asset.get("url"):
            continue
        local_path = asset.get("local_path")
        if not local_path:
            failed.append({"rid": asset.get("rid", ""), "message": "local_path is missing"})
            continue
        try:
            file_path = state.safe_project_path(project_dir, local_path)
            mime = _image_mime(file_path, check_size=False)
            if _resize_for_shopify(file_path, mime, resize_runner):
                asset["resized_for_shopify"] = True
            mime = _image_mime(file_path)
            filename = f"{asset.get('rid') or file_path.stem}{MIME_TO_EXT[mime]}"
            staged = _create_staged_target(graphql_runner, filename, mime)
            upload_runner(staged, file_path, mime, timeout)
            created = _create_shopify_file(graphql_runner, staged["resourceUrl"], asset.get("alt") or "")
            asset["shopify_file_id"] = created.get("id", "")
            asset["file_status"] = created.get("fileStatus", "")
            url = ((created.get("image") or {}).get("url")) or ""
            if not url and asset["shopify_file_id"]:
                created = _wait_for_shopify_file_url(graphql_runner, asset["shopify_file_id"], timeout)
                asset["file_status"] = created.get("fileStatus", asset["file_status"])
                url = ((created.get("image") or {}).get("url")) or ""
            if not url:
                raise ValueError("Shopify fileCreate returned no CDN image URL")
            asset["url"] = url
            asset.pop("upload_error", None)
            uploaded.append(asset.get("rid", ""))
        except Exception as exc:  # noqa: BLE001
            asset["upload_error"] = str(exc)
            failed.append({"rid": asset.get("rid", ""), "message": str(exc)})
    manifest["uploaded_count"] = len(uploaded)
    manifest["upload_errors"] = failed
    atomic_write_text(manifest_path, json.dumps(manifest, ensure_ascii=False, indent=2) + "\n")
    report = {
        "collection_status": "partial" if failed and uploaded else ("failed" if failed else "ok"),
        "item_id": item_id,
        "uploaded": uploaded,
        "failed": failed,
        "manifest_path": str(manifest_path.relative_to(project_dir)),
    }
    return report, manifest_path


def _create_staged_target(graphql_runner: Any, filename: str, mime: str) -> dict[str, Any]:
    payload = graphql_runner(
        STAGED_UPLOADS_MUTATION,
        {"input": [{"filename": filename, "mimeType": mime, "resource": "PRODUCT_IMAGE", "httpMethod": "POST"}]},
    )
    body = payload.get("data", {}).get("stagedUploadsCreate", {})
    errors = body.get("userErrors") or []
    targets = body.get("stagedTargets") or []
    if errors or not targets:
        raise ValueError(f"Shopify stagedUploadsCreate failed: {errors}")
    return targets[0]


def _create_shopify_file(graphql_runner: Any, source: str, alt: str) -> dict[str, Any]:
    payload = graphql_runner(
        FILE_CREATE_MUTATION,
        {"files": [{"alt": alt, "contentType": "IMAGE", "originalSource": source}]},
    )
    body = payload.get("data", {}).get("fileCreate", {})
    errors = body.get("userErrors") or []
    files = body.get("files") or []
    if errors or not files:
        raise ValueError(f"Shopify fileCreate failed: {errors}")
    return files[0]


def _wait_for_shopify_file_url(graphql_runner: Any, file_id: str, timeout: float) -> dict[str, Any]:
    deadline = time.monotonic() + timeout
    last: dict[str, Any] = {"id": file_id}
    while time.monotonic() < deadline:
        payload = graphql_runner(FILE_NODE_QUERY, {"id": file_id})
        node = payload.get("data", {}).get("node") or {}
        if isinstance(node, dict):
            last = node
            if (node.get("image") or {}).get("url"):
                return node
        time.sleep(2)
    return last


def _post_staged_upload(target: dict[str, Any], file_path: Path, mime: str, timeout: float) -> None:
    boundary = "----seo-workbench-upload"
    fields = [(item["name"], item["value"]) for item in target.get("parameters", []) if isinstance(item, dict)]
    body = _multipart_body(boundary, fields, file_path, mime)
    request = Request(
        target["url"],
        data=body,
        headers={"Content-Type": f"multipart/form-data; boundary={boundary}", "Content-Length": str(len(body))},
        method="POST",
    )
    with urlopen(request, timeout=timeout) as response:
        response.read()


def _multipart_body(boundary: str, fields: list[tuple[str, str]], file_path: Path, mime: str) -> bytes:
    chunks: list[bytes] = []
    for name, value in fields:
        chunks.append(f"--{boundary}\r\nContent-Disposition: form-data; name=\"{name}\"\r\n\r\n{value}\r\n".encode())
    chunks.append(
        (
            f"--{boundary}\r\n"
            f"Content-Disposition: form-data; name=\"file\"; filename=\"{file_path.name}\"\r\n"
            f"Content-Type: {mime}\r\n\r\n"
        ).encode()
    )
    chunks.append(file_path.read_bytes())
    chunks.append(f"\r\n--{boundary}--\r\n".encode())
    return b"".join(chunks)


def _image_mime(path: Path, *, check_size: bool = True) -> str:
    if check_size and path.stat().st_size > MAX_SHOPIFY_IMAGE_BYTES:
        raise ValueError("image exceeds Shopify safety limit of 15 MB")
    data = path.read_bytes()[:12]
    if data.startswith(b"\xff\xd8\xff"):
        return "image/jpeg"
    if data.startswith(b"\x89PNG\r\n\x1a\n"):
        return "image/png"
    if data.startswith((b"GIF87a", b"GIF89a")):
        return "image/gif"
    if data.startswith(b"RIFF") and data[8:12] == b"WEBP":
        raise ValueError("webp is not uploaded directly; convert to png first")
    raise ValueError("unsupported image type; expected jpeg, png, or gif")


def _resize_for_shopify(path: Path, mime: str, runner: Any) -> bool:
    if mime not in {"image/jpeg", "image/png"} or shutil.which("sips") is None:
        return False
    before = path.stat().st_size
    completed = runner(
        ["sips", "-Z", str(SHOPIFY_RESIZE_WIDTH_PX), str(path)],
        text=True,
        capture_output=True,
        check=False,
    )
    return completed.returncode == 0 and path.exists() and path.stat().st_size != before


def _download_asset(
    rid: str,
    out: Path,
    profile: str,
    config_path: Path | None,
    runner: Any,
) -> tuple[str, str]:
    errors = []
    for table in UGC_TABLES:
        try:
            download_attachment(
                profile=profile,
                config_path=config_path,
                base="dcdb",
                table=table,
                record_id=rid,
                field="contents",
                output=out,
                identity="user",
                runner=runner,
            )
        except RuntimeError as exc:
            errors.append(f"{table}: {str(exc)[:200]}")
            continue
        if out.exists() and out.stat().st_size > 0:
            return table, ""
        errors.append(f"{table}: attachment download returned success but no file was written")
    return "", " | ".join(errors)


def _download_table_attachment(
    rid: str,
    table: str,
    out: Path,
    profile: str,
    config_path: Path | None,
    runner: Any,
) -> None:
    download_attachment(
        profile=profile,
        config_path=config_path,
        base="dcdb",
        table=table,
        record_id=rid,
        field="contents",
        output=out,
        identity="user",
        runner=runner,
    )
    if not out.exists() or out.stat().st_size == 0:
        raise RuntimeError("gateway returned success but no file was written")


def _upsert_asset_field(
    rid: str,
    table: str,
    fields: dict[str, Any],
    profile: str,
    config_path: Path | None,
    runner: Any,
) -> None:
    upsert_record(
        profile=profile,
        config_path=config_path,
        base="dcdb",
        table=table,
        record_id=rid,
        fields=fields,
        runner=runner,
    )


def _list_asset_rows(
    table: str,
    profile: str,
    config_path: Path | None,
    runner: Any,
) -> list[dict[str, Any]]:
    fields = [field for field in ASSET_FIELDS[table].values() if field]
    return list_records(
        profile=profile,
        config_path=config_path,
        base="dcdb",
        table=table,
        field_ids=fields,
        runner=runner,
    )


def _mmx_describe(image_path: Path, *, runner: Any) -> str:
    key = os.environ.get("MINIMAX_API_KEY", "").strip()
    if not key:
        raise ValueError("MINIMAX_API_KEY is not set")
    completed = runner(
        [
            "mmx",
            "vision",
            "describe",
            "--image",
            str(image_path),
            "--prompt",
            MMX_PROMPT,
            "--output",
            "json",
            "--region",
            os.environ.get("MMX_REGION", "cn"),
        ],
        text=True,
        capture_output=True,
        check=False,
        timeout=120,
    )
    if completed.returncode != 0:
        raise RuntimeError((completed.stderr or completed.stdout).strip()[:300])
    data = json.loads(completed.stdout or "{}")
    content = data.get("content") or ""
    if isinstance(content, list):
        content = "".join(str(block.get("text", "")) for block in content if isinstance(block, dict))
    return _strip_fences(str(content))


def _strip_fences(text: str) -> str:
    stripped = text.strip()
    if stripped.startswith("```"):
        lines = stripped.splitlines()
        if lines:
            lines = lines[1:]
        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]
        return "\n".join(lines).strip()
    return stripped


def _asset_candidate(table: str, row: dict[str, Any]) -> dict[str, Any] | None:
    fields = ASSET_FIELDS[table]
    rid = str(row.get("_record_id") or "")
    products = _multi_select(row.get(fields["product"]))
    content_type = _scalar(row.get(fields["content_type"]))
    times_used = int(_number(row.get(fields["times_used"])) or 0)
    if not rid or content_type not in ALLOWED_CONTENT_TYPES or times_used >= TIMES_USED_HARD_CAP:
        return None
    return {
        "rid": rid,
        "table": table,
        "contents_number": _scalar(row.get(fields["contents_number"])),
        "product": products,
        "content_type": content_type,
        "rating": _scalar(row.get(fields["rating"])) if fields["rating"] else "",
        "creator": _scalar(row.get(fields["creator"])),
        "times_used": times_used,
        "large_file_link": _scalar(row.get(fields["large_file_link"])),
        "mmx_visual_description": _scalar(row.get(fields["mmx"])),
        "notes": _scalar(row.get(fields["notes"])),
    }


def _allowed_products(record: dict[str, Any]) -> set[str]:
    allowed: set[str] = set()
    for anchor in record.get("product_anchor") or []:
        allowed.update(ANCHOR_PRODUCTS.get(str(anchor), set()))
    return allowed


def patch_html_with_asset_urls(html: str, assets: dict[str, dict[str, Any]], applied: list[str] | None = None) -> str:
    def repl(match: re.Match[str]) -> str:
        before, rid, after = match.group(1), match.group(2), match.group(3)
        asset = assets.get(rid)
        if not asset:
            return match.group(0)
        if applied is not None:
            applied.append(rid)
        alt_match = ALT_RE.search(before + after)
        alt = asset.get("alt") or (alt_match.group(1) if alt_match else "")
        return f'<img src="{escape(str(asset["url"]), quote=True)}" alt="{escape(str(alt), quote=True)}" loading="lazy">'

    return IMG_TAG_DATA_RID_RE.sub(repl, html or "")


def collect_inline_rids(html: str) -> list[str]:
    return IMG_DATA_RID_RE.findall(html or "")


def image_ref_warnings(record: dict[str, Any]) -> list[dict[str, str]]:
    inline_refs = list(record.get("inline_image_refs") or [])
    placeholders = collect_inline_rids(record.get("draft_html") or "")
    warnings = []
    missing = sorted(set(inline_refs) - set(placeholders))
    extra = sorted(set(placeholders) - set(inline_refs))
    if missing:
        warnings.append({"code": "inline_refs.missing_from_html", "message": f"inline refs not present as data-rid placeholders: {', '.join(missing)}"})
    if extra:
        warnings.append({"code": "inline_placeholders.not_in_refs", "message": f"HTML data-rid placeholders missing from inline refs: {', '.join(extra)}"})
    return warnings


def _find_pipeline_record(project_dir: Path, item_id: str) -> dict[str, Any]:
    path = state.safe_project_path(project_dir, "content/blog-pipeline.jsonl")
    if not path.exists():
        raise FileNotFoundError(f"{path} not found; import content first")
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        record = json.loads(line)
        if record.get("id") == item_id:
            return record
    raise ValueError(f"content pipeline item not found: {item_id}")


def _update_pipeline_record(project_dir: Path, item_id: str, patch: Any) -> dict[str, Any]:
    path = state.safe_project_path(project_dir, "content/blog-pipeline.jsonl")
    if not path.exists():
        raise FileNotFoundError(f"{path} not found; import content first")
    lines = []
    updated: dict[str, Any] | None = None
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        record = json.loads(line)
        if record.get("id") == item_id:
            updated = patch(record)
            record = updated
        lines.append(json.dumps(record, ensure_ascii=False))
    if updated is None:
        raise ValueError(f"content pipeline item not found: {item_id}")
    atomic_write_text(path, "\n".join(lines) + "\n")
    return updated


def _safe_name(value: str) -> str:
    return re.sub(r"[^A-Za-z0-9_.-]+", "-", value).strip("-") or "assets"


def _feishu_record_id(value: str) -> str:
    if not FEISHU_RECORD_ID_RE.fullmatch(value):
        raise ValueError(f"invalid Feishu record ID: {value!r}")
    return value


def _scalar(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, list):
        return _scalar(value[0]) if value else ""
    if isinstance(value, dict):
        return _scalar(value.get("text", value.get("name", value.get("id", ""))))
    return str(value).strip()


def _multi_select(value: Any) -> list[str]:
    if not value:
        return []
    if isinstance(value, list):
        return [text for text in (_scalar(item) for item in value) if text]
    text = _scalar(value)
    return [text] if text else []


def _number(value: Any) -> int | float | None:
    if value in (None, ""):
        return None
    if isinstance(value, (int, float)):
        return value
    try:
        num = float(str(value).strip())
    except ValueError:
        return None
    return int(num) if num.is_integer() else num
