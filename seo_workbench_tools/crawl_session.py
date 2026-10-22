"""Project-injected crawl identity and a persistent, host-wide request gate."""
from __future__ import annotations

import hashlib
import json
import math
import random
import threading
import time
from contextlib import contextmanager
from contextvars import ContextVar
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from http.client import HTTPException
from pathlib import Path
from typing import Any, Iterator
from urllib.error import HTTPError, URLError
from urllib.parse import parse_qsl, urlencode, urljoin, urlsplit, urlunsplit
from urllib.request import HTTPRedirectHandler, Request, build_opener

from filelock import FileLock

from seo_workbench_tools.files import atomic_write_text
from seo_workbench_tools.network_boundary import inspect_target, sensitive_query_key

DEFAULT_CONTROL_ROOT = Path(__file__).resolve().parent.parent / ".runtime/crawl-control"
DEFAULT_USER_AGENT = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"
MAX_COOLDOWN_SECONDS = 365 * 86400
_ACTIVE: ContextVar[CrawlSession | None] = ContextVar("crawl_session", default=None)


def active_session() -> CrawlSession | None:
    return _ACTIVE.get()


def retry_after_seconds(headers: dict[str, str]) -> float | None:
    value = headers.get("retry-after", "").strip()
    if not value:
        return None
    if value.isdigit():
        seconds = float(value)
        return min(seconds, MAX_COOLDOWN_SECONDS) if math.isfinite(seconds) else float(MAX_COOLDOWN_SECONDS)
    try:
        target = parsedate_to_datetime(value)
        if target.tzinfo is None:
            target = target.replace(tzinfo=timezone.utc)
        return min(MAX_COOLDOWN_SECONDS, max(0.0, target.timestamp() - time.time()))
    except (TypeError, ValueError, OverflowError):
        return None


class CrawlDeferred(RuntimeError):
    def __init__(self, until: float):
        self.until = until
        super().__init__("crawl host is cooling down; resume after next_eligible_at")


class CrawlAccessError(RuntimeError):
    """Project access needs attention; retrying more pages cannot repair it."""


class _NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


class CrawlSession:
    def __init__(self, seed_url: str, *, access: Any = None, delay: float = 1.0,
                 control_root: Path = DEFAULT_CONTROL_ROOT, allow_private: bool = False,
                 user_agent: str = DEFAULT_USER_AGENT):
        self.host = (urlsplit(seed_url).hostname or "").lower()
        self.access = access
        self.delay = max(0.0, delay)
        self.control_root = control_root
        self.allow_private = allow_private
        self.user_agent = user_agent
        self.attempts: list[dict[str, Any]] = []
        self._lock = threading.Lock()

    @contextmanager
    def activate(self) -> Iterator[CrawlSession]:
        token = _ACTIVE.set(self)
        try:
            yield self
        finally:
            _ACTIVE.reset(token)

    def headers_for(self, url: str, *, user_agent: str | None = None) -> dict[str, str]:
        headers = {"User-Agent": user_agent or self.user_agent, "Accept-Language": "en-US,en;q=0.9"}
        if self.access and urlsplit(url).scheme == "https" and (urlsplit(url).hostname or "").lower() == self.host:
            if self.access.expired:
                raise CrawlAccessError("crawler signature expired; update project access before continuing")
            headers.update(self.access.headers_for(url))
        return headers

    @contextmanager
    def _state(self, url: str):
        host = (urlsplit(url).hostname or "").lower()
        if self.control_root.is_symlink():
            raise ValueError("crawl control directory must not be a symlink")
        self.control_root.mkdir(parents=True, exist_ok=True, mode=0o700)
        key = hashlib.sha256(host.encode()).hexdigest()[:24]
        path = self.control_root / f"{key}.json"
        with self._lock, FileLock(str(path) + ".lock", timeout=10):
            data = json.loads(path.read_text()) if path.exists() else {}
            yield data
            atomic_write_text(path, json.dumps(data, allow_nan=False) + "\n", mode=0o600)

    def before_request(self, url: str) -> None:
        inspect_target(url, self.allow_private)
        while True:
            with self._state(url) as data:
                now = time.time()
                cooling = float(data.get("cooldown_until", 0))
                if cooling > now:
                    raise CrawlDeferred(cooling)
                wait = max(0.0, float(data.get("next_start", 0)) - now)
                if not wait:
                    data["next_start"] = now + self.delay
                    return
            time.sleep(min(wait, 0.25))

    def observe_response(self, url: str, status: int | None, headers: dict[str, str], *, signed: bool = False) -> None:
        with self._state(url) as data:
            if status == 429:
                strikes = int(data.get("rate_limit_count", 0)) + 1
                seconds = max(retry_after_seconds(headers) or 0, 30 * 2 ** min(strikes - 1, 5))
                data.update(rate_limit_count=strikes, cooldown_until=time.time() + seconds + random.uniform(0, 1))
            elif status is not None and 200 <= status < 400:
                data["rate_limit_count"] = 0
        with self._lock:
            parsed = urlsplit(url)
            safe_url = urlunsplit((parsed.scheme, parsed.netloc.rsplit("@", 1)[-1], parsed.path, urlencode([(k, "[redacted]" if sensitive_query_key(k) else v) for k, v in parse_qsl(parsed.query)]), ""))
            self.attempts.append({"at": datetime.now(timezone.utc).isoformat(), "url": safe_url,
                                  "status": status, "signed_headers_attached": signed})

    def next_eligible_at(self, url: str) -> float:
        with self._state(url) as data:
            return float(data.get("cooldown_until", 0))

    def fetch(self, url: str, timeout: float, *, method: str = "GET", retries: int = 2) -> dict[str, Any]:
        opener = build_opener(_NoRedirect())
        current = url
        for hop in range(11):
            for attempt in range(retries + 1):
                self.before_request(current)
                headers = self.headers_for(current)
                started = time.perf_counter()
                try:
                    try:
                        response = opener.open(Request(current, headers=headers, method=method), timeout=timeout)
                    except HTTPError as exc:
                        response = exc
                    with response:
                        body = response.read()
                        status = int(response.code)
                        response_headers = {k.lower(): v for k, v in response.headers.items()}
                    break
                except (URLError, OSError, HTTPException) as exc:
                    if attempt == retries:
                        raise RuntimeError("crawl transport failed after bounded retries") from exc
                    time.sleep(0.25 * 2 ** attempt + random.uniform(0, 0.1))
            self.observe_response(current, status, response_headers, signed="Signature" in headers)
            if status in {301, 302, 303, 307, 308} and response_headers.get("location"):
                current = urljoin(current, response_headers["location"])
                continue
            return {"status": status, "final_url": current, "headers": response_headers,
                    "body": body, "elapsed_ms": round((time.perf_counter() - started) * 1000),
                    "signed_headers_attached": "Signature" in headers}
        raise RuntimeError("crawl redirect limit exceeded")
