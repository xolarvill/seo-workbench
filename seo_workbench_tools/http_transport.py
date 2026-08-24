from __future__ import annotations

import time
from http.client import HTTPException
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import urlopen


def read_url(request: Any, *, timeout: float, max_bytes: int | None = None, attempts: int = 3) -> bytes:
    """Read an idempotent HTTP request, retrying only transport failures."""
    for attempt in range(1, attempts + 1):
        try:
            with urlopen(request, timeout=timeout) as response:
                return response.read(max_bytes + 1) if max_bytes is not None else response.read()
        except HTTPError:
            raise
        except (URLError, TimeoutError, HTTPException, OSError) as exc:
            if attempt == attempts:
                if isinstance(exc, (URLError, TimeoutError)):
                    raise
                raise URLError(exc) from exc
            time.sleep(attempt)
    raise AssertionError("unreachable")
