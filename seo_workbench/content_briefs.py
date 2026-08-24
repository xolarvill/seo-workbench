from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

from seo_workbench import state
from seo_workbench_tools.files import atomic_write_text


PRODUCT_LINKS = {
    "studio": [
        ("Hexcal Studio", "hexcal-studio"),
        ("Magnetic Desk Mat Bundle", "hexcal-magnetic-desk-mat-bundle-black"),
        ("Tech Pouch", "tech-pouch"),
    ],
    "plus": [("Hexcal Studio Plus", "hexcal-studio-plus")],
    "ergon": [
        ("Elevate Standing Desk", "elevate-standing-desk"),
        ("Single Monitor Arm", "single-monitor-arm"),
        ("Heavy Duty Monitor Arm", "heavy-duty-monitor-arm"),
        ("Monitor Mount System", "monitor-mount-system"),
        ("Hexcal Inspire Chair", "hexcal-inspire-chair"),
    ],
}


def export_writing_brief(project_dir: Path, item_id: str) -> tuple[dict[str, Any], Path]:
    record = _find_record(project_dir, item_id)
    links = _internal_links(project_dir, current_id=item_id)
    product_links = _product_links(project_dir, record)
    serp = _serp_competitors(project_dir, item_id)
    path = state.safe_project_path(project_dir, f"strategy/briefs/{_safe_name(item_id)}.md")
    path.parent.mkdir(parents=True, exist_ok=True)
    content = _render_brief(project_dir, record, links, product_links, serp)
    atomic_write_text(path, content)
    return {
        "collection_status": "ok",
        "item_id": item_id,
        "path": str(path),
        "internal_link_candidates": len(links),
        "product_link_candidates": len(product_links),
        "serp_competitors": len(serp),
        "next_step": "Use skills/content-brief or skills/write-content with this brief, then import the draft for QC.",
    }, path


def export_revision_brief(project_dir: Path, item_id: str) -> tuple[dict[str, Any], Path]:
    record = _find_record(project_dir, item_id)
    if record.get("status") != "revision_requested":
        raise ValueError(f"content item must be revision_requested: {item_id}")
    if not record.get("edit_notes"):
        raise ValueError(f"content item has no edit_notes: {item_id}")
    links = _internal_links(project_dir, current_id=item_id)
    product_links = _product_links(project_dir, record)
    path = state.safe_project_path(project_dir, f"strategy/briefs/{_safe_name(item_id)}-revision.md")
    path.parent.mkdir(parents=True, exist_ok=True)
    atomic_write_text(path, _render_revision_brief(project_dir, record, links, product_links))
    return {
        "collection_status": "ok",
        "item_id": item_id,
        "path": str(path),
        "internal_link_candidates": len(links),
        "next_step": "Revise the draft using edit_notes, then run content qc before review-push.",
    }, path


def _render_brief(
    project_dir: Path,
    record: dict[str, Any],
    links: list[dict[str, str]],
    product_links: list[dict[str, str]],
    serp: list[dict[str, str]],
) -> str:
    project_name = str((state.load_state(project_dir).get("project") or {}).get("name") or "the project")
    lines = [
        f"# {record.get('title') or record.get('cluster_name') or record.get('id')}",
        "",
        "## Source",
        "",
        f"- Item ID: {record.get('id', '')}",
        f"- Status: {record.get('status', '')}",
        f"- Target keyword: {record.get('target_keyword') or record.get('representative_keyword') or record.get('representative_kw') or ''}",
        f"- Intent: {record.get('intent', '')}",
        f"- Product anchor: {_join(record.get('product_anchor'))}",
        "",
        "## Cluster Context",
        "",
        record.get("cluster_rationale") or "No cluster rationale provided.",
        "",
        "## Keywords",
        "",
        f"- Representative: {record.get('representative_keyword') or record.get('representative_kw') or ''}",
        f"- Long tail: {_join(record.get('long_tail_keywords') or record.get('long_tail_kws'))}",
        f"- Members: {_join(record.get('member_keywords'))}",
        "",
        "## Draft Requirements",
        "",
        "- Read and follow the project context files listed below before writing.",
        f"- Preserve {project_name}'s configured brand voice and Blog channel rules.",
        "- Use factual product claims only when supported by local product context or cited sources.",
        "- Keep generated HTML free of a leading H1; Shopify renders the article title.",
        f"- Run `content serp-competitors {record.get('id', '')}` before writing if the SERP competitor section is empty.",
        "- Run `content qc` before publishing.",
        "",
        "## Project Context Files",
        "",
    ]
    lines.extend(_context_reference_lines(project_dir))
    lines.extend([
        "",
        "## SERP Competitors",
        "",
    ]
    )
    lines.extend([f"- [{item['title'] or item['url']}]({item['url']}): {item['snippet']}" for item in serp] or ["- none"])
    lines.extend([
        "",
        "## Image Candidate Workflow",
        "",
        f"- If a Feishu asset profile is configured, run `content asset-candidates {record.get('id', '')}` before selecting images.",
        f"- Run `content describe-candidates {record.get('id', '')}` to fill missing visual descriptions when that adapter is enabled.",
        "- Use selected inline images as `<img data-rid=\"rec...\" alt=\"...\">`; resolve them with the asset commands before publishing.",
        "",
        "## Internal Link Candidates",
        "",
    ])
    lines.extend([f"- [{item['title']}]({item['live_url']})" for item in product_links] or ["- none"])
    lines.extend([
        "",
        "## Published Blog Link Candidates",
        "",
    ])
    lines.extend([f"- [{item['title']}]({item['live_url']})" for item in links] or ["- none"])
    lines.extend(_asset_reference_lines(record))
    return "\n".join(lines).rstrip() + "\n"


def _render_revision_brief(
    project_dir: Path,
    record: dict[str, Any],
    links: list[dict[str, str]],
    product_links: list[dict[str, str]],
) -> str:
    lines = [
        f"# Revision Brief - {record.get('title') or record.get('cluster_name') or record.get('id')}",
        "",
        "## Source",
        "",
        f"- Item ID: {record.get('id', '')}",
        f"- Status: {record.get('status', '')}",
        f"- Target keyword: {record.get('target_keyword') or record.get('representative_keyword') or record.get('representative_kw') or ''}",
        "",
        "## Edit Notes",
        "",
        str(record.get("edit_notes") or "").strip(),
        "",
        "## Current Draft HTML",
        "",
        "```html",
        str(record.get("draft_html") or "").strip(),
        "```",
        "",
        "## Revision Requirements",
        "",
        "- Address only the requested changes unless a factual or SEO issue is found.",
        "- Re-check the migrated brand voice, Blog style guide, and product specs before changing claims.",
        "- Preserve supported claims and existing internal links when still relevant.",
        "- Keep generated HTML free of a leading H1; Shopify renders the article title.",
        "- Run `content qc` before sending the revised draft back to review.",
        "",
        "## Project Context Files",
        "",
    ]
    lines.extend(_context_reference_lines(project_dir))
    lines.extend([
        "",
        "## Internal Link Candidates",
        "",
    ]
    )
    lines.extend([f"- [{item['title']}]({item['live_url']})" for item in product_links] or ["- none"])
    lines.extend([
        "",
        "## Published Blog Link Candidates",
        "",
    ])
    lines.extend([f"- [{item['title']}]({item['live_url']})" for item in links] or ["- none"])
    lines.extend(_asset_reference_lines(record))
    return "\n".join(lines).rstrip() + "\n"


def _context_reference_lines(project_dir: Path) -> list[str]:
    candidates = [
        ("Brand voice index", "context/brand-voice.md"),
        ("Universal voice pillars", "context/brand-voice/cross-market.md"),
        ("Overseas voice", "context/brand-voice/overseas.md"),
        ("Blog style guide", "context/blog-style-guide.md"),
        ("Product specs aggregate", "context/product-specs.md"),
        ("Product source files", "context/product-context/"),
    ]
    lines = []
    for label, rel_path in candidates:
        path = state.safe_project_path(project_dir, rel_path.rstrip("/"))
        if path.exists():
            lines.append(f"- {label}: `{rel_path}`")
    return lines or ["- No project context files found; create `context/brand-voice.md` before final writing."]


def _find_record(project_dir: Path, item_id: str) -> dict[str, Any]:
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


def _internal_links(project_dir: Path, *, current_id: str) -> list[dict[str, str]]:
    path = state.safe_project_path(project_dir, "content/blog-pipeline.jsonl")
    links = []
    if not path.exists():
        return links
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        record = json.loads(line)
        live_url = record.get("live_url")
        if record.get("id") != current_id and isinstance(live_url, str) and live_url:
            links.append({"title": str(record.get("title") or record.get("cluster_name") or live_url), "live_url": live_url})
    return links[:20]


def _product_links(project_dir: Path | None, record: dict[str, Any]) -> list[dict[str, str]]:
    if project_dir is None:
        return []
    project = state.load_state(project_dir).get("project") or {}
    site_url = str(project.get("url") or "").rstrip("/")
    if not site_url or str(project.get("name") or "").strip().casefold() != "hexcal":
        return []
    links = []
    for anchor in record.get("product_anchor") or []:
        for title, slug in PRODUCT_LINKS.get(str(anchor), []):
            links.append({"title": title, "live_url": f"{site_url}/products/{slug}"})
    return links


def _serp_competitors(project_dir: Path, item_id: str) -> list[dict[str, str]]:
    path = state.safe_project_path(project_dir, f"strategy/briefs/{_safe_name(item_id)}-serp.json")
    if not path.exists():
        return []
    data = json.loads(path.read_text(encoding="utf-8"))
    return [
        {
            "title": str(item.get("title") or ""),
            "url": str(item.get("url") or ""),
            "snippet": str(item.get("snippet") or ""),
        }
        for item in data.get("competitors", [])
        if isinstance(item, dict) and item.get("url")
    ][:10]


def _asset_reference_lines(record: dict[str, Any]) -> list[str]:
    feature = _join(record.get("feature_image_refs"))
    inline = _join(record.get("inline_image_refs"))
    if not feature and not inline:
        return []
    return [
        "",
        "## Selected Image References",
        "",
        f"- Feature image record IDs: {feature or 'none'}",
        f"- Inline image record IDs: {inline or 'none'}",
        "- Use inline images as `<img data-rid=\"rec...\" alt=\"...\">`; run `content assets`, `content download-assets`, `content upload-assets`, and `content apply-assets` before publishing.",
    ]


def _join(value: Any) -> str:
    if isinstance(value, list):
        return ", ".join(str(item) for item in value if item)
    return str(value or "")


def _safe_name(value: str) -> str:
    return re.sub(r"[^A-Za-z0-9_.-]+", "-", value).strip("-") or "brief"
