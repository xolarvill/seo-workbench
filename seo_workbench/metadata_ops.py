from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from seo_workbench import state
from seo_workbench.content_publish import SHOPIFY_API_VERSION, SHOPIFY_DOMAIN
from seo_workbench_tools.files import atomic_write_text


SHOPIFY_REQUIRED_WRITE_SCOPES = {"write_products", "write_content"}
PRODUCT_SEO_METAFIELDS = (
    ("global", "title_tag", "single_line_text_field"),
    ("global", "description_tag", "single_line_text_field"),
)
TITLE_MAX = 70
DESCRIPTION_MAX = 160
COLLECTION_BODY_MAX = 800
ARTICLE_SUMMARY_MAX = 155
PRODUCT_QUERY = """
query ProductSeo($q: String!) {
  products(first: 1, query: $q) {
    edges { node { id title handle
      seo { title description }
    } }
  }
}
"""
UPDATE_MUTATION = """
mutation UpdateProductSeo($id: ID!, $metafields: [MetafieldInput!]!) {
  productUpdate(product: { id: $id, metafields: $metafields }) {
    product { id title handle }
    userErrors { field message }
  }
}
"""
VERIFY_QUERY = """
query ProductSeoVerify($id: ID!) {
  product(id: $id) {
    id title handle
    seo { title description }
    metafields(first: 10, namespace: "global") { edges { node { namespace key value type } } }
  }
}
"""
COLLECTION_QUERY = """
query CollectionSeo($q: String!) {
  collections(first: 1, query: $q) {
    edges { node { id title handle
      seo { title description }
      descriptionHtml
    } }
  }
}
"""
COLLECTION_UPDATE_MUTATION = """
mutation UpdateCollectionSeo($id: ID!, $seo: SEOInput!, $body: String!) {
  collectionUpdate(collection: { id: $id, seo: $seo, descriptionHtml: $body }) {
    collection { id title handle }
    userErrors { field message }
  }
}
"""
COLLECTION_VERIFY_QUERY = """
query CollectionSeoVerify($id: ID!) {
  collection(id: $id) {
    id title handle
    seo { title description }
    descriptionHtml
  }
}
"""
ARTICLE_QUERY = """
query ArticleSummary($q: String!) {
  articles(first: 1, query: $q) {
    edges { node { id title handle summary } }
  }
}
"""
ARTICLE_UPDATE_MUTATION = """
mutation UpdateArticleSummary($id: ID!, $summary: HTML!, $metafields: [MetafieldInput!]!) {
  articleUpdate(id: $id, article: { summary: $summary, metafields: $metafields }) {
    article { id title handle }
    userErrors { field message }
  }
}
"""
ARTICLE_VERIFY_QUERY = """
query ArticleSummaryVerify($id: ID!) {
  article(id: $id) {
    id title handle summary
    metafields(first: 10, namespace: "global") { edges { node { namespace key value type } } }
  }
}
"""


def build_product_seo_payload(handle: str, seo_title: str, seo_description: str) -> dict[str, Any]:
    warnings = _seo_warnings(handle, seo_title, seo_description)
    metafields = [
        {"namespace": namespace, "key": key, "value": value, "type": type_}
        for (namespace, key, type_), value in zip(
            PRODUCT_SEO_METAFIELDS, (seo_title, seo_description), strict=True
        )
    ]
    return {
        "collection_status": "ok",
        "dry_run": True,
        "resource": "product",
        "handle": handle,
        "mutation": "productUpdate",
        "query": UPDATE_MUTATION,
        "variables": {"id": "gid://shopify/Product/<resolved>", "metafields": metafields},
        "seo": {"title": seo_title, "description": seo_description},
        "warnings": warnings,
    }


def update_product_seo(
    project_dir: Path,
    handle: str,
    seo_title: str,
    seo_description: str,
    *,
    dry_run: bool = False,
    timeout: float = 30,
) -> tuple[dict[str, Any], Path]:
    handle = handle.strip()
    report = build_product_seo_payload(handle, seo_title, seo_description)
    if report["warnings"]:
        blocked = {**report, "collection_status": "blocked", "dry_run": False}
        return _write_metadata_report(project_dir, handle, "blocked", blocked)
    if dry_run:
        report = {**report, "collection_status": "dry-run"}
        return _write_metadata_report(project_dir, handle, "dry-run", report)

    credentials = _load_shopify_credentials(project_dir)

    product_id = _resolve_product_id(credentials, handle, timeout=timeout)
    report["variables"]["id"] = product_id

    response = _shopify_graphql(credentials, query=UPDATE_MUTATION, variables=report["variables"], timeout=timeout)
    payload = response.get("data", {}).get("productUpdate", {})
    user_errors = payload.get("userErrors") or []
    if user_errors or not (payload.get("product") or {}).get("id"):
        failed = {
            **report,
            "collection_status": "error",
            "dry_run": False,
            "shop_domain": credentials["shop_domain"],
            "shopify": {"user_errors": user_errors},
        }
        return _write_metadata_report(project_dir, handle, "error", failed)

    verified = _verify_seo(credentials, product_id, seo_title, seo_description, timeout=timeout)
    complete = {
        **report,
        "collection_status": "complete",
        "dry_run": False,
        "shop_domain": credentials["shop_domain"],
        "shopify": {"product": payload.get("product"), "user_errors": []},
        "verified": verified,
    }
    return _write_metadata_report(project_dir, handle, "update", complete)


def build_collection_seo_payload(handle: str, seo_title: str, seo_description: str, body_html: str) -> dict[str, Any]:
    warnings = _seo_warnings(handle, seo_title, seo_description)
    if not body_html:
        warnings.append({"code": "body.missing", "message": "collection body description is empty"})
    elif len(body_html) > COLLECTION_BODY_MAX:
        warnings.append({"code": "body.too_long", "message": f"collection body description exceeds {COLLECTION_BODY_MAX} characters"})
    return {
        "collection_status": "ok",
        "dry_run": True,
        "resource": "collection",
        "handle": handle,
        "mutation": "collectionUpdate",
        "query": COLLECTION_UPDATE_MUTATION,
        "variables": {
            "id": "gid://shopify/Collection/<resolved>",
            "seo": {"title": seo_title, "description": seo_description},
            "body": body_html,
        },
        "seo": {"title": seo_title, "description": seo_description},
        "body_html": body_html,
        "warnings": warnings,
    }


def update_collection_seo(
    project_dir: Path,
    handle: str,
    seo_title: str,
    seo_description: str,
    body_html: str,
    *,
    dry_run: bool = False,
    timeout: float = 30,
) -> tuple[dict[str, Any], Path]:
    handle = handle.strip()
    report = build_collection_seo_payload(handle, seo_title, seo_description, body_html)
    if report["warnings"]:
        blocked = {**report, "collection_status": "blocked", "dry_run": False}
        return _write_metadata_report(project_dir, handle, "blocked", blocked)
    if dry_run:
        report = {**report, "collection_status": "dry-run"}
        return _write_metadata_report(project_dir, handle, "dry-run", report)

    credentials = _load_shopify_credentials(project_dir)

    collection_id = _resolve_collection_id(credentials, handle, timeout=timeout)
    report["variables"]["id"] = collection_id

    response = _shopify_graphql(credentials, query=COLLECTION_UPDATE_MUTATION, variables=report["variables"], timeout=timeout)
    payload = response.get("data", {}).get("collectionUpdate", {})
    user_errors = payload.get("userErrors") or []
    if user_errors or not (payload.get("collection") or {}).get("id"):
        failed = {
            **report,
            "collection_status": "error",
            "dry_run": False,
            "shop_domain": credentials["shop_domain"],
            "shopify": {"user_errors": user_errors},
        }
        return _write_metadata_report(project_dir, handle, "error", failed)

    verified = _verify_collection_seo(credentials, collection_id, seo_title, seo_description, body_html, timeout=timeout)
    complete = {
        **report,
        "collection_status": "complete",
        "dry_run": False,
        "shop_domain": credentials["shop_domain"],
        "shopify": {"collection": payload.get("collection"), "user_errors": []},
        "verified": verified,
    }
    return _write_metadata_report(project_dir, handle, "update", complete)


def build_article_summary_payload(handle: str, summary: str) -> dict[str, Any]:
    warnings: list[dict[str, str]] = []
    if not handle:
        warnings.append({"code": "handle.missing", "message": "article handle is empty"})
    if not summary:
        warnings.append({"code": "summary.missing", "message": "article summary is empty"})
    elif len(summary) > ARTICLE_SUMMARY_MAX:
        warnings.append({"code": "summary.too_long", "message": f"article summary exceeds {ARTICLE_SUMMARY_MAX} characters"})
    if "<" in summary or ">" in summary:
        warnings.append({"code": "html.in_summary", "message": "article summary must not contain HTML tags"})
    metafields = [
        {"namespace": "global", "key": "description_tag", "value": summary, "type": "single_line_text_field"}
    ]
    return {
        "collection_status": "ok",
        "dry_run": True,
        "resource": "article",
        "handle": handle,
        "mutation": "articleUpdate",
        "query": ARTICLE_UPDATE_MUTATION,
        "variables": {"id": "gid://shopify/Article/<resolved>", "summary": summary, "metafields": metafields},
        "summary": summary,
        "warnings": warnings,
    }


def update_article_summary(
    project_dir: Path,
    handle: str,
    summary: str,
    *,
    dry_run: bool = False,
    timeout: float = 30,
) -> tuple[dict[str, Any], Path]:
    handle = handle.strip()
    report = build_article_summary_payload(handle, summary)
    if report["warnings"]:
        blocked = {**report, "collection_status": "blocked", "dry_run": False}
        return _write_metadata_report(project_dir, handle, "blocked", blocked)
    if dry_run:
        report = {**report, "collection_status": "dry-run"}
        return _write_metadata_report(project_dir, handle, "dry-run", report)

    credentials = _load_shopify_credentials(project_dir)

    article_id = _resolve_article_id(credentials, handle, timeout=timeout)
    report["variables"]["id"] = article_id

    response = _shopify_graphql(credentials, query=ARTICLE_UPDATE_MUTATION, variables=report["variables"], timeout=timeout)
    payload = response.get("data", {}).get("articleUpdate", {})
    user_errors = payload.get("userErrors") or []
    if user_errors or not (payload.get("article") or {}).get("id"):
        failed = {
            **report,
            "collection_status": "error",
            "dry_run": False,
            "shop_domain": credentials["shop_domain"],
            "shopify": {"user_errors": user_errors},
        }
        return _write_metadata_report(project_dir, handle, "error", failed)

    verified = _verify_article_summary(credentials, article_id, summary, timeout=timeout)
    complete = {
        **report,
        "collection_status": "complete",
        "dry_run": False,
        "shop_domain": credentials["shop_domain"],
        "shopify": {"article": payload.get("article"), "user_errors": []},
        "verified": verified,
    }
    return _write_metadata_report(project_dir, handle, "update", complete)


def _resolve_article_id(credentials: dict[str, Any], handle: str, *, timeout: float) -> str:
    response = _shopify_graphql(credentials, query=ARTICLE_QUERY, variables={"q": f"handle:\"{handle}\""}, timeout=timeout)
    edges = response.get("data", {}).get("articles", {}).get("edges") or []
    if not edges:
        raise ValueError(f"article handle not found: {handle}")
    return edges[0]["node"]["id"]


def _verify_article_summary(
    credentials: dict[str, Any], article_id: str, summary: str, *, timeout: float
) -> dict[str, Any]:
    response = _shopify_graphql(credentials, query=ARTICLE_VERIFY_QUERY, variables={"id": article_id}, timeout=timeout)
    node = response.get("data", {}).get("article") or {}
    metafields = {}
    for edge in (node.get("metafields") or {}).get("edges") or []:
        item = edge.get("node") or {}
        metafields[f"{item.get('namespace')}.{item.get('key')}"] = item.get("value")
    return {
        "summary_matches": node.get("summary") == summary,
        "metafield_matches": metafields.get("global.description_tag") == summary,
        "summary": node.get("summary"),
        "metafields": metafields,
    }


def _resolve_collection_id(credentials: dict[str, Any], handle: str, *, timeout: float) -> str:
    response = _shopify_graphql(credentials, query=COLLECTION_QUERY, variables={"q": f"handle:{handle}"}, timeout=timeout)
    edges = response.get("data", {}).get("collections", {}).get("edges") or []
    if not edges:
        raise ValueError(f"collection handle not found: {handle}")
    return edges[0]["node"]["id"]


def _verify_collection_seo(
    credentials: dict[str, Any], collection_id: str, seo_title: str, seo_description: str, body_html: str, *, timeout: float
) -> dict[str, Any]:
    response = _shopify_graphql(credentials, query=COLLECTION_VERIFY_QUERY, variables={"id": collection_id}, timeout=timeout)
    node = response.get("data", {}).get("collection") or {}
    return {
        "title_matches": node.get("seo", {}).get("title") == seo_title,
        "description_matches": node.get("seo", {}).get("description") == seo_description,
        "body_matches": node.get("descriptionHtml") == body_html,
        "seo": node.get("seo"),
        "body_length": len(node.get("descriptionHtml") or ""),
    }


def _load_shopify_credentials(project_dir: Path) -> dict[str, Any]:
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
        raise ValueError("metadata update requires write_products or write_content scope")
    return {"shop_domain": domain, "access_token": token, "scopes": sorted(safe_scopes)}


def _resolve_product_id(credentials: dict[str, Any], handle: str, *, timeout: float) -> str:
    response = _shopify_graphql(credentials, query=PRODUCT_QUERY, variables={"q": f"handle:{handle}"}, timeout=timeout)
    edges = response.get("data", {}).get("products", {}).get("edges") or []
    if not edges:
        raise ValueError(f"product handle not found: {handle}")
    return edges[0]["node"]["id"]


def _verify_seo(
    credentials: dict[str, Any], product_id: str, seo_title: str, seo_description: str, *, timeout: float
) -> dict[str, Any]:
    response = _shopify_graphql(credentials, query=VERIFY_QUERY, variables={"id": product_id}, timeout=timeout)
    node = response.get("data", {}).get("product") or {}
    metafields = {}
    for edge in (node.get("metafields") or {}).get("edges") or []:
        item = edge.get("node") or {}
        metafields[f"{item.get('namespace')}.{item.get('key')}"] = item.get("value")
    return {
        "title_matches": node.get("seo", {}).get("title") == seo_title,
        "description_matches": node.get("seo", {}).get("description") == seo_description,
        "seo": node.get("seo"),
        "metafields": metafields,
    }


def _seo_warnings(handle: str, seo_title: str, seo_description: str) -> list[dict[str, str]]:
    warnings: list[dict[str, str]] = []
    if not handle:
        warnings.append({"code": "handle.missing", "message": "product handle is empty"})
    if not seo_title:
        warnings.append({"code": "seo_title.missing", "message": "seo title is empty"})
    if not seo_description:
        warnings.append({"code": "seo_description.missing", "message": "seo description is empty"})
    if len(seo_title) > TITLE_MAX:
        warnings.append({"code": "seo_title.too_long", "message": f"seo title exceeds {TITLE_MAX} characters"})
    if len(seo_description) > DESCRIPTION_MAX:
        warnings.append({"code": "seo_description.too_long", "message": f"seo description exceeds {DESCRIPTION_MAX} characters"})
    if "<" in seo_title or ">" in seo_title or "<" in seo_description or ">" in seo_description:
        warnings.append({"code": "html.in_seo_text", "message": "seo title/description must not contain HTML tags"})
    return warnings


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


def _safe_name(value: str) -> str:
    return re.sub(r"[^A-Za-z0-9_.-]+", "-", value).strip("-") or "product"


def _write_metadata_report(project_dir: Path, handle: str, suffix: str, report: dict[str, Any]) -> tuple[dict[str, Any], Path]:
    output_dir = state.safe_project_path(project_dir, "audits/metadata")
    output_dir.mkdir(parents=True, exist_ok=True)
    path = output_dir / f"{_safe_name(handle)}-{suffix}.json"
    atomic_write_text(path, json.dumps(report, ensure_ascii=False, indent=2) + "\n")
    return report, path
