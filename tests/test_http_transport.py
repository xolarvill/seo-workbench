from http.client import IncompleteRead
from urllib.error import HTTPError

import pytest

from seo_workbench_tools import http_transport


class _Response:
    def __init__(self, value):
        self.value = value

    def __enter__(self):
        return self

    def __exit__(self, *_args):
        return None

    def read(self, *_args):
        if isinstance(self.value, Exception):
            raise self.value
        return self.value


def test_read_url_retries_incomplete_reads(monkeypatch) -> None:
    responses = iter([_Response(IncompleteRead(b"partial")), _Response(b"complete")])
    sleeps = []
    monkeypatch.setattr(http_transport, "urlopen", lambda *_args, **_kwargs: next(responses))
    monkeypatch.setattr(http_transport.time, "sleep", sleeps.append)

    assert http_transport.read_url(object(), timeout=1) == b"complete"
    assert sleeps == [1]


def test_read_url_does_not_retry_http_errors(monkeypatch) -> None:
    calls = 0

    def fail(*_args, **_kwargs):
        nonlocal calls
        calls += 1
        raise HTTPError("https://example.com", 403, "forbidden", {}, None)

    monkeypatch.setattr(http_transport, "urlopen", fail)

    with pytest.raises(HTTPError):
        http_transport.read_url(object(), timeout=1)
    assert calls == 1
