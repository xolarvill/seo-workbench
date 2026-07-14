from __future__ import annotations

from typing import Any


COMPARE_FIELDS = ["title", "meta_description", "canonical", "robots_meta"]


def _first_rendered_view(page: dict[str, Any]) -> dict[str, Any]:
    viewports = page.get("viewports", {})
    for key in ("desktop_1920x1080", "mobile_375x812", "tablet_768x1024"):
        data = viewports.get(key, {})
        if data and not data.get("error"):
            return data
    return next((data for data in viewports.values() if not data.get("error")), {})


def _schema_types(page: dict[str, Any]) -> list[str]:
    audit = page.get("schema_audit", {})
    if audit.get("schema_types_found") is not None:
        return sorted(audit.get("schema_types_found", []))
    return sorted(page.get("schema_types", []))


def _normalize_list(values: Any) -> list[str]:
    if not isinstance(values, list):
        return []
    return [" ".join(str(value).split()) for value in values if str(value).strip()]


def _rendered_page_map(rendered: dict[str, Any] | None) -> dict[str, dict[str, Any]]:
    if not rendered:
        return {}
    mapping = {}
    for page in rendered.get("pages", []):
        view = _first_rendered_view(page)
        if view:
            mapping[page.get("url", "")] = view
            mapping[view.get("url", "")] = view
    return mapping


def compare_page(raw: dict[str, Any], rendered: dict[str, Any] | None) -> dict[str, Any]:
    diffs = []
    raw_schema_types = _schema_types(raw)
    rendered_schema_types = _schema_types(rendered or {})

    if rendered:
        for field in COMPARE_FIELDS:
            raw_value = raw.get(field, "")
            rendered_value = rendered.get(field, "")
            if raw_value != rendered_value:
                diffs.append({"field": field, "raw": raw_value, "rendered": rendered_value})
        raw_h1 = _normalize_list(raw.get("h1"))
        rendered_h1 = _normalize_list(rendered.get("h1"))
        if raw_h1 != rendered_h1:
            diffs.append({"field": "h1", "raw": raw_h1, "rendered": rendered_h1})
        if raw_schema_types != rendered_schema_types:
            diffs.append({"field": "schema_types", "raw": raw_schema_types, "rendered": rendered_schema_types})

    raw_links = raw.get("link_summary", {})
    rendered_links = rendered.get("link_summary", {}) if rendered else {}
    raw_images = raw.get("image_stats", {})
    rendered_images = rendered.get("images", {}) if rendered else {}

    return {
        "url": raw.get("url", ""),
        "final_url": raw.get("final_url", ""),
        "rendered_available": bool(rendered),
        "diffs": diffs,
        "raw": {
            "title": raw.get("title", ""),
            "meta_description": raw.get("meta_description", ""),
            "canonical": raw.get("canonical", ""),
            "robots_meta": raw.get("robots_meta", ""),
            "h1": _normalize_list(raw.get("h1")),
            "schema_types": raw_schema_types,
            "schema_count": raw.get("schema_audit", {}).get("inline_schema_count", 0),
            "has_body_text": raw.get("content_audit", {}).get("has_body_text_in_raw_html", False),
            "link_count": raw_links.get("anchor_count", 0),
            "image_count": raw_images.get("total", 0),
        },
        "rendered": {
            "title": (rendered or {}).get("title", ""),
            "meta_description": (rendered or {}).get("meta_description", ""),
            "canonical": (rendered or {}).get("canonical", ""),
            "robots_meta": (rendered or {}).get("robots_meta", ""),
            "h1": _normalize_list((rendered or {}).get("h1")),
            "schema_types": rendered_schema_types,
            "schema_count": (rendered or {}).get("schema_count", 0),
            "has_body_text": (rendered or {}).get("has_body_text", False),
            "link_count": rendered_links.get("anchor_count", 0),
            "image_count": rendered_images.get("total", 0),
        },
    }


def build_headless_audit(bundle: dict[str, Any], rendered: dict[str, Any] | None, project_type: str = "") -> dict[str, Any]:
    rendered_pages = _rendered_page_map(rendered)
    pages = []
    critical = []
    warnings = []
    info = []

    for raw in bundle.get("pages", []):
        if raw.get("error"):
            warnings.append(f"{raw.get('url', '')}: raw fetch failed: {raw.get('error')}")
            continue
        rendered_page = rendered_pages.get(raw.get("url", "")) or rendered_pages.get(raw.get("final_url", ""))
        comparison = compare_page(raw, rendered_page)
        pages.append(comparison)

        url = raw.get("url", "")
        if raw.get("status") != 200:
            critical.append(f"{url}: raw response status is {raw.get('status')}")
        for field in ("title", "meta_description", "canonical"):
            if not raw.get(field):
                critical.append(f"{url}: raw HTML missing {field}")
        if not raw.get("h1"):
            critical.append(f"{url}: raw HTML missing H1")
        if not raw.get("content_audit", {}).get("has_body_text_in_raw_html", False):
            warnings.append(f"{url}: raw HTML has little or no body text")

        for diff in comparison["diffs"]:
            if diff["field"] in {"canonical", "robots_meta"}:
                critical.append(f"{url}: raw/rendered {diff['field']} mismatch")
            elif diff["field"] == "schema_types" and not comparison["raw"]["schema_count"] and comparison["rendered"]["schema_count"]:
                critical.append(f"{url}: schema appears only after rendering")
            else:
                warnings.append(f"{url}: raw/rendered {diff['field']} differs")

    if not rendered:
        info.append("rendered evidence unavailable; raw/rendered diff skipped")
    if project_type != "shopify-headless":
        info.append("project is not shopify-headless; headless findings are advisory")

    return {
        "status": "fail" if critical else "warn" if warnings else "pass",
        "critical": sorted(set(critical)),
        "warnings": sorted(set(warnings)),
        "info": info,
        "pages": pages,
    }
