"""Local Shopify Web Bot Auth storage and request-header handling."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlsplit

from seo_workbench import state
from seo_workbench_tools.files import atomic_write_text


CRAWLER_ACCESS_RELATIVE_PATH = ".runtime/integrations/shopify-crawler.json"
SIGNATURE_AGENT = '"https://shopify.com"'
_HOST_RE = re.compile(r"^[a-z0-9](?:[a-z0-9.-]{0,251}[a-z0-9])?$")


@dataclass(frozen=True)
class ShopifyCrawlerAccess:
    domain_host: str
    signature: str
    signature_input: str
    signature_agent: str
    expires_at: datetime

    @property
    def expired(self) -> bool:
        return self.expires_at <= datetime.now(timezone.utc)

    def headers_for(self, url: str) -> dict[str, str]:
        """Return the signed headers only for the exact Shopify domain scope."""
        hostname = (urlsplit(url).hostname or "").rstrip(".").lower()
        if hostname != self.domain_host:
            return {}
        return {
            "Signature": self.signature,
            "Signature-Input": self.signature_input,
            "Signature-Agent": self.signature_agent,
        }


def crawler_access_path(project_dir: Path) -> Path:
    return state.safe_project_path(project_dir, CRAWLER_ACCESS_RELATIVE_PATH)


def _parse_expiry(value: datetime | str) -> datetime:
    parsed = value if isinstance(value, datetime) else datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        raise ValueError("expiration must include a timezone")
    return parsed.astimezone(timezone.utc)


def normalize_domain_host(value: str) -> str:
    host = value.strip().lower().rstrip(".")
    if not host or "://" in host or "/" in host or "@" in host or not _HOST_RE.fullmatch(host):
        raise ValueError("crawler domain must be a public hostname without scheme or path")
    try:
        host = host.encode("idna").decode("ascii")
    except UnicodeError as exc:
        raise ValueError("crawler domain is not a valid hostname") from exc
    if len(host) > 253 or "." not in host:
        raise ValueError("crawler domain must be a fully qualified hostname")
    return host


def _validate_header(name: str, value: str, max_length: int = 4096) -> str:
    value = value.strip()
    if not value or len(value) > max_length or "\r" in value or "\n" in value:
        raise ValueError(f"{name} is empty, too long, or contains a line break")
    return value


def build_crawler_access(
    *,
    domain_host: str,
    signature: str,
    signature_input: str,
    signature_agent: str,
    expires_at: datetime | str,
    seed_url: str,
) -> ShopifyCrawlerAccess:
    normalized_host = normalize_domain_host(domain_host)
    seed_host = (urlsplit(seed_url).hostname or "").rstrip(".").lower()
    if normalized_host != seed_host:
        raise ValueError(f"crawler domain must match the project URL host ({seed_host})")
    normalized_agent = _validate_header("Signature-Agent", signature_agent, 512)
    if normalized_agent != SIGNATURE_AGENT:
        raise ValueError(f"Signature-Agent must be {SIGNATURE_AGENT}")
    expiry = _parse_expiry(expires_at)
    if expiry <= datetime.now(timezone.utc):
        raise ValueError("crawler signature has already expired")
    return ShopifyCrawlerAccess(
        domain_host=normalized_host,
        signature=_validate_header("Signature", signature),
        signature_input=_validate_header("Signature-Input", signature_input),
        signature_agent=normalized_agent,
        expires_at=expiry,
    )


def write_crawler_access(project_dir: Path, access: ShopifyCrawlerAccess) -> None:
    path = crawler_access_path(project_dir)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.parent.chmod(0o700)
    path.parent.parent.chmod(0o700)
    payload = {
        "schema_version": "1.0",
        "domain_host": access.domain_host,
        "signature": access.signature,
        "signature_input": access.signature_input,
        "signature_agent": access.signature_agent,
        "expires_at": access.expires_at.isoformat(),
        "saved_at": datetime.now(timezone.utc).isoformat(),
    }
    atomic_write_text(path, json.dumps(payload, ensure_ascii=False, indent=2) + "\n", mode=0o600)


def read_crawler_access(project_dir: Path, seed_url: str, *, allow_expired: bool = False) -> ShopifyCrawlerAccess:
    path = crawler_access_path(project_dir)
    if not path.is_file():
        raise FileNotFoundError(path)
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
        access = build_crawler_access(
            domain_host=str(payload["domain_host"]),
            signature=str(payload["signature"]),
            signature_input=str(payload["signature_input"]),
            signature_agent=str(payload["signature_agent"]),
            expires_at=str(payload["expires_at"]),
            seed_url=seed_url,
        )
    except (KeyError, TypeError, ValueError, json.JSONDecodeError) as exc:
        raise ValueError("stored Shopify crawler access is invalid") from exc
    if access.expired and not allow_expired:
        raise ValueError("stored Shopify crawler signature has expired")
    return access


def crawler_access_status(project_dir: Path, seed_url: str) -> dict[str, object]:
    path = crawler_access_path(project_dir)
    default_host = (urlsplit(seed_url).hostname or "").lower() or None
    result: dict[str, object] = {
        "configured": path.is_file(),
        "status": "missing" if not path.is_file() else "invalid",
        "domain_host": default_host,
        "expires_at": None,
        "signature_agent": None,
        "removable": path.is_file(),
        "secret_visibility": "write_only",
    }
    if not path.is_file():
        return result
    try:
        access = read_crawler_access(project_dir, seed_url, allow_expired=True)
    except ValueError:
        return result
    result.update({
        "status": "expired" if access.expired else "ready",
        "domain_host": access.domain_host,
        "expires_at": access.expires_at.isoformat(),
        "signature_agent": access.signature_agent,
    })
    return result


def delete_crawler_access(project_dir: Path) -> None:
    path = crawler_access_path(project_dir)
    if path.exists():
        path.unlink()
