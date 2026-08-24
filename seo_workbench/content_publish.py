from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from seo_workbench import state
from seo_workbench.content_assets import image_ref_warnings
from seo_workbench.content_pipeline import set_queue_status
from seo_workbench.content_quality import build_qc_report, extract_faq, load_spec_whitelist, strip_html_text
from seo_workbench_tools.files import atomic_write_text


SHOPIFY_API_VERSION = "2026-07"
SHOPIFY_DOMAIN = re.compile(r"^[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?\.myshopify\.com$")
SHOPIFY_REQUIRED_WRITE_SCOPES = {"write_content", "write_online_store_pages"}
QC_BLOCKING_CODES = {"ai_signature", "spec_provenance"}
CREATE_ARTICLE_MUTATION = """
mutation CreateArticle($article: ArticleCreateInput!) {
  articleCreate(article: $article) {
    article { id title handle isPublished publishedAt }
    userErrors { code field message }
  }
}
"""
UPDATE_ARTICLE_MUTATION = """
mutation UpdateArticle($id: ID!, $article: ArticleUpdateInput!) {
  articleUpdate(id: $id, article: $article) {
    article { id title handle isPublished publishedAt }
    userErrors { code field message }
  }
}
"""


def publish_dry_run(project_dir: Path, item_id: str, *, blog_id: str) -> tuple[dict[str, Any], Path]:
    report = _build_project_publish_payload(project_dir, item_id, blog_id=blog_id)
    output_dir = state.safe_project_path(project_dir, "audits/publish")
    output_dir.mkdir(parents=True, exist_ok=True)
    path = output_dir / f"{_safe_name(item_id)}-dry-run.json"
    atomic_write_text(path, json.dumps(report, ensure_ascii=False, indent=2) + "\n")
    return report, path


def build_publish_payload(
    record: dict[str, Any],
    *,
    project_url: str,
    blog_id: str,
    publisher_name: str = "Store",
    publisher_url: str = "",
    publisher_logo_url: str = "",
) -> dict[str, Any]:
    slug = record.get("slug") or ""
    title = record.get("title") or record.get("cluster_name") or ""
    body = strip_leading_h1(record.get("draft_html") or "")
    meta_description = record.get("meta_description") or ""
    scheduled_at = record.get("scheduled_at") or ""
    live_url = str(record.get("live_url") or "").strip() or _article_url(project_url, slug)
    body = inject_jsonld(
        body,
        title=title,
        description=meta_description,
        url=live_url,
        date_published=str(scheduled_at or ""),
        publisher_name=publisher_name,
        publisher_url=publisher_url or project_url,
        publisher_logo_url=publisher_logo_url,
    )
    existing_id = record.get("shopify_article_id") or ""
    warnings = _publish_warnings(record, body=body, title=title, slug=slug, scheduled_at=scheduled_at, blog_id=blog_id)

    if existing_id:
        article_input = {
            "title": title,
            "body": body,
        }
        if meta_description:
            article_input["summary"] = meta_description
            article_input["metafields"] = [
                {
                    "key": "description_tag",
                    "value": meta_description,
                    "type": "single_line_text_field",
                    "namespace": "global",
                }
            ]
        if record.get("feature_image_url"):
            article_input["image"] = {"url": record["feature_image_url"], "altText": record.get("feature_image_alt") or title}
        variables = {"id": _article_gid(str(existing_id)), "article": article_input}
        mutation = "articleUpdate"
        query = UPDATE_ARTICLE_MUTATION
    else:
        article_input = {
            "title": title,
            "author": {"name": publisher_name},
            "blogId": f"gid://shopify/Blog/{blog_id}",
            "isPublished": bool(scheduled_at),
            "body": body,
            "handle": slug,
        }
        if record.get("feature_image_url"):
            article_input["image"] = {"url": record["feature_image_url"], "altText": record.get("feature_image_alt") or title}
        if meta_description:
            article_input["summary"] = meta_description
            article_input["metafields"] = [
                {
                    "key": "description_tag",
                    "value": meta_description,
                    "type": "single_line_text_field",
                    "namespace": "global",
                }
            ]
        if scheduled_at:
            article_input["publishDate"] = scheduled_at
        variables = {"article": article_input}
        mutation = "articleCreate"
        query = CREATE_ARTICLE_MUTATION

    return {
        "collection_status": "ok",
        "dry_run": True,
        "item_id": record.get("id", ""),
        "operation": "update" if existing_id else "create",
        "mutation": mutation,
        "query": query,
        "variables": variables,
        "live_url": live_url,
        "unresolved_image_refs": {
            "feature": record.get("feature_image_refs") or [],
            "inline": record.get("inline_image_refs") or [],
        },
        "article": article_input,
        "warnings": warnings,
    }


def publish_item(
    project_dir: Path,
    item_id: str,
    *,
    blog_id: str,
    allow_warnings: bool = False,
    timeout: float = 30,
) -> tuple[dict[str, Any], Path]:
    report = _build_project_publish_payload(project_dir, item_id, blog_id=blog_id)
    if allow_warnings:
        report["warnings"].append({"code": "hitl.allow_warnings_disabled", "message": "real publish cannot bypass HITL warnings"})
        blocked = {**report, "collection_status": "blocked", "dry_run": False}
        return _write_publish_report(project_dir, item_id, "blocked", blocked)
    if report["warnings"]:
        blocked = {**report, "collection_status": "blocked", "dry_run": False}
        return _write_publish_report(project_dir, item_id, "blocked", blocked)

    credentials = load_shopify_credentials(project_dir)
    response = _shopify_graphql(
        credentials,
        query=report["query"],
        variables=report["variables"],
        timeout=timeout,
    )
    payload = response.get("data", {}).get(report["mutation"], {})
    user_errors = payload.get("userErrors") or []
    article = payload.get("article") or {}
    if user_errors or not article.get("id"):
        failed = {
            **report,
            "collection_status": "error",
            "dry_run": False,
            "shop_domain": credentials["shop_domain"],
            "shopify": {"user_errors": user_errors},
        }
        return _write_publish_report(project_dir, item_id, "error", failed)
    if report["operation"] == "create" and report["article"].get("publishDate") and not article.get("publishedAt"):
        failed = {
            **report,
            "collection_status": "error",
            "dry_run": False,
            "shop_domain": credentials["shop_domain"],
            "shopify": {"article": article, "user_errors": [], "schedule_error": "Shopify did not confirm publishedAt"},
        }
        return _write_publish_report(project_dir, item_id, "error", failed)

    article_id = _article_int_id(article["id"])
    live_url = report["live_url"]
    _update_pipeline_record(project_dir, item_id, {"shopify_article_id": article_id, "live_url": live_url, "status": "scheduled"})
    _update_queue_after_publish(project_dir, item_id, article_id=article_id, live_url=live_url)
    complete = {
        **report,
        "collection_status": "complete",
        "dry_run": False,
        "shop_domain": credentials["shop_domain"],
        "shopify": {"article": article, "user_errors": []},
    }
    return _write_publish_report(project_dir, item_id, "publish", complete)


def _build_project_publish_payload(project_dir: Path, item_id: str, *, blog_id: str) -> dict[str, Any]:
    record = _find_pipeline_record(project_dir, item_id)
    project = state.load_state(project_dir).get("project") or {}
    report = build_publish_payload(
        record,
        project_url=project.get("url") or "",
        blog_id=blog_id,
        publisher_name=project.get("name") or "Store",
        publisher_url=project.get("url") or "",
    )
    project_name = str(project.get("name") or "").strip().lower()
    quality = build_qc_report(
        record,
        spec_whitelist=load_spec_whitelist(project_dir),
        brand_terms=(project_name,) if project_name else (),
    )
    report["quality"] = quality
    report["warnings"].extend(
        {"code": f"qc.{warning['code']}", "message": warning["message"]}
        for warning in quality["warnings"]
        if warning["code"] in QC_BLOCKING_CODES
    )
    return report


def load_shopify_credentials(project_dir: Path) -> dict[str, Any]:
    path = state.safe_project_path(project_dir, ".runtime/integrations/shopify.json")
    if path.is_symlink():
        raise ValueError("Shopify credential path cannot be a symlink")
    if not path.is_file():
        raise ValueError("Shopify credentials are not configured")
    try:
        stored = json.loads(path.read_text(encoding="utf-8"))
        domain = str(stored["shop_domain"]).strip().lower()
        token = stored["access_token"]
        scopes = stored.get("scopes") or []
    except (KeyError, OSError, TypeError, json.JSONDecodeError) as exc:
        raise ValueError("Shopify credentials are invalid") from exc
    if not SHOPIFY_DOMAIN.fullmatch(domain):
        raise ValueError("Shopify credential domain must be canonical store.myshopify.com")
    if not isinstance(token, str) or not token or any(ch.isspace() for ch in token):
        raise ValueError("Shopify access token is invalid")
    safe_scopes = {scope for scope in scopes if isinstance(scope, str)}
    if safe_scopes.isdisjoint(SHOPIFY_REQUIRED_WRITE_SCOPES):
        raise ValueError("Shopify publish requires write_content or write_online_store_pages scope")
    return {"shop_domain": domain, "access_token": token, "scopes": sorted(safe_scopes)}


def _shopify_graphql(credentials: dict[str, Any], *, query: str, variables: dict[str, Any], timeout: float) -> dict[str, Any]:
    request = Request(
        f"https://{credentials['shop_domain']}/admin/api/{SHOPIFY_API_VERSION}/graphql.json",
        data=json.dumps({"query": query, "variables": variables}).encode("utf-8"),
        headers={
            "Content-Type": "application/json",
            "User-Agent": "SEO-Workbench/0.2",
            "X-Shopify-Access-Token": credentials["access_token"],
        },
        method="POST",
    )
    try:
        with urlopen(request, timeout=timeout) as response:
            body = response.read(2_000_001)
    except HTTPError as exc:
        raise ValueError(f"Shopify Admin API returned HTTP {exc.code}") from exc
    except (OSError, URLError) as exc:
        raise ValueError("Shopify Admin API could not be reached") from exc
    if len(body) > 2_000_000:
        raise ValueError("Shopify Admin API response exceeded the safety limit")
    try:
        payload = json.loads(body)
    except json.JSONDecodeError as exc:
        raise ValueError("Shopify Admin API returned invalid JSON") from exc
    if payload.get("errors"):
        raise ValueError("Shopify Admin API returned GraphQL errors")
    return payload


def strip_leading_h1(html: str) -> str:
    return re.sub(r"^\s*<h1[^>]*>.*?</h1>\s*", "", html or "", count=1, flags=re.I | re.S)


def inject_jsonld(
    html: str,
    *,
    title: str,
    description: str,
    url: str,
    date_published: str,
    publisher_name: str,
    publisher_url: str,
    publisher_logo_url: str = "",
) -> str:
    publisher: dict[str, Any] = {
        "@type": "Organization",
        "name": publisher_name,
        "url": publisher_url,
    }
    if publisher_logo_url:
        publisher["logo"] = {"@type": "ImageObject", "url": publisher_logo_url}
    schemas: list[dict[str, Any]] = [
        {
            "@context": "https://schema.org",
            "@type": "BlogPosting",
            "headline": title,
            "description": description or title,
            "url": url,
            "mainEntityOfPage": {"@type": "WebPage", "@id": url},
            "datePublished": date_published,
            "dateModified": date_published,
            "author": {"@type": "Organization", "name": publisher_name, "url": publisher_url},
            "publisher": publisher,
        }
    ]
    faqs = extract_faq(html)
    if faqs:
        schemas.append(
            {
                "@context": "https://schema.org",
                "@type": "FAQPage",
                "mainEntity": [
                    {
                        "@type": "Question",
                        "name": item["question"],
                        "acceptedAnswer": {"@type": "Answer", "text": item["answer"]},
                    }
                    for item in faqs
                ],
            }
        )
    blocks = [
        f'<script type="application/ld+json">{json.dumps(schema, ensure_ascii=False, separators=(",", ":"))}</script>'
        for schema in schemas
    ]
    return "\n".join(blocks) + "\n" + html


def _publish_warnings(record: dict[str, Any], *, body: str, title: str, slug: str, scheduled_at: Any, blog_id: str) -> list[dict[str, str]]:
    warnings: list[dict[str, str]] = []
    if record.get("status") != "approved":
        warnings.append({"code": "status.not_approved", "message": f"content status is {record.get('status')!r}, expected 'approved'"})
    if not blog_id:
        warnings.append({"code": "blog_id.missing", "message": "--blog-id is required for Shopify payload"})
    if not title:
        warnings.append({"code": "title.missing", "message": "title is empty"})
    if not slug and not record.get("shopify_article_id"):
        warnings.append({"code": "slug.missing", "message": "slug is required for articleCreate"})
    if not body:
        warnings.append({"code": "body.missing", "message": "draft_html/body is empty"})
    if not scheduled_at and not record.get("shopify_article_id"):
        warnings.append({"code": "schedule.missing", "message": "scheduled_at is empty; Shopify articleCreate will produce an unpublished draft"})
    if not record.get("asset_urls_applied") and ((record.get("feature_image_refs") or []) or (record.get("inline_image_refs") or [])):
        warnings.append({"code": "images.unresolved", "message": "image refs are present; resolve/upload images before publishing"})
        warnings.extend(image_ref_warnings(record))
    return warnings


def _article_url(project_url: str, slug: str) -> str:
    return f"{project_url.rstrip('/')}/blogs/articles/{slug}" if project_url and slug else ""


def _article_gid(value: str) -> str:
    return value if value.startswith("gid://shopify/Article/") else f"gid://shopify/Article/{value}"


def _article_int_id(value: str) -> str:
    return value.rsplit("/", 1)[-1] if value else ""


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


def _safe_name(value: str) -> str:
    return re.sub(r"[^A-Za-z0-9_.-]+", "-", value).strip("-") or "publish"


def _write_publish_report(project_dir: Path, item_id: str, suffix: str, report: dict[str, Any]) -> tuple[dict[str, Any], Path]:
    output_dir = state.safe_project_path(project_dir, "audits/publish")
    output_dir.mkdir(parents=True, exist_ok=True)
    path = output_dir / f"{_safe_name(item_id)}-{suffix}.json"
    atomic_write_text(path, json.dumps(report, ensure_ascii=False, indent=2) + "\n")
    return report, path


def _update_pipeline_record(project_dir: Path, item_id: str, updates: dict[str, Any]) -> None:
    path = state.safe_project_path(project_dir, "content/blog-pipeline.jsonl")
    lines: list[str] = []
    found = False
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        record = json.loads(line)
        if record.get("id") == item_id:
            record.update(updates)
            found = True
        lines.append(json.dumps(record, ensure_ascii=False))
    if not found:
        raise ValueError(f"content pipeline item not found: {item_id}")
    atomic_write_text(path, "\n".join(lines) + "\n")


def _update_queue_after_publish(project_dir: Path, item_id: str, *, article_id: str, live_url: str) -> None:
    def mutation(data: dict[str, Any]) -> None:
        try:
            item = set_queue_status(data, item_id, "scheduled", note=f"Shopify article {article_id}")
        except ValueError:
            item = {"id": item_id, "status": "scheduled", "note": f"Shopify article {article_id}"}
            data.setdefault("contentQueue", []).append(item)
        item["shopify_article_id"] = article_id
        item["live_url"] = live_url
        data["lastAction"] = f"Published content item {item_id} to Shopify"
        data["nextAction"] = "Review scheduled article in Shopify Admin"
        state.record_history(data, "content-publish", "CONTENT_PRODUCTION", "prepare-publish", item_id)

    state.mutate_state(project_dir, mutation)
