from __future__ import annotations

import ipaddress
import select
import socket
import socketserver
import threading
from contextlib import contextmanager
from typing import Iterator
from urllib.parse import parse_qsl, urlsplit


MAX_HEADER_BYTES = 64 * 1024


def sensitive_query_key(key: str) -> bool:
    normalized = key.lower().replace("-", "_")
    if normalized in {"key", "api_key", "apikey", "auth", "authorization", "sig", "code"}:
        return True
    return any(fragment in normalized for fragment in ("token", "secret", "signature", "credential", "password"))


def validate_url(url: str) -> str:
    parsed = urlsplit(url)
    if parsed.scheme not in {"http", "https"} or not parsed.hostname:
        raise ValueError("only absolute http and https URLs are supported")
    if parsed.username or parsed.password:
        raise ValueError("URL userinfo is not allowed")
    if sensitive := next((key for key, _ in parse_qsl(parsed.query, keep_blank_values=True) if sensitive_query_key(key)), None):
        raise ValueError(f"sensitive query parameter is not allowed in performance reports: {sensitive}")
    return url


def resolve_target(host: str, port: int, allow_private: bool) -> tuple[int, tuple, list[str]]:
    try:
        addresses = socket.getaddrinfo(host, port, type=socket.SOCK_STREAM)
    except socket.gaierror as exc:
        raise RuntimeError(f"unable to resolve target host {host}: {exc}") from exc
    public = []
    seen = set()
    for family, socktype, proto, _, sockaddr in addresses:
        raw_address = sockaddr[0].split("%", 1)[0]
        try:
            address = ipaddress.ip_address(raw_address)
        except ValueError:
            continue
        if raw_address in seen:
            continue
        seen.add(raw_address)
        if allow_private or address.is_global:
            public.append((family, socktype, proto, sockaddr, raw_address))
    if not public:
        raise RuntimeError("target resolves only to non-public addresses; use --allow-private for a trusted local target")
    family, _, _, sockaddr, _ = public[0]
    return family, sockaddr, [item[4] for item in public]


def inspect_target(url: str, allow_private: bool) -> dict[str, object]:
    parsed = urlsplit(validate_url(url))
    port = parsed.port or (443 if parsed.scheme == "https" else 80)
    _, _, addresses = resolve_target(parsed.hostname or "", port, allow_private)
    return {"url": url, "hostname": parsed.hostname, "port": port, "resolved_addresses": addresses}


def _read_headers(connection: socket.socket) -> tuple[bytes, bytes]:
    data = bytearray()
    while b"\r\n\r\n" not in data:
        chunk = connection.recv(8192)
        if not chunk:
            break
        data.extend(chunk)
        if len(data) > MAX_HEADER_BYTES:
            raise ValueError("proxy request headers exceed 64 KiB")
    head, separator, remainder = bytes(data).partition(b"\r\n\r\n")
    if not separator:
        raise ValueError("incomplete proxy request headers")
    return head, remainder


def _relay(left: socket.socket, right: socket.socket) -> None:
    sockets = [left, right]
    while sockets:
        readable, _, exceptional = select.select(sockets, [], sockets, 30)
        if exceptional or not readable:
            return
        for source in readable:
            data = source.recv(64 * 1024)
            if not data:
                return
            destination = right if source is left else left
            destination.sendall(data)


def _host_and_port(target: str, default_port: int) -> tuple[str, int]:
    parsed = urlsplit(f"//{target}")
    if not parsed.hostname:
        raise ValueError("proxy request is missing a host")
    return parsed.hostname, parsed.port or default_port


class _GuardedProxyHandler(socketserver.BaseRequestHandler):
    def handle(self) -> None:
        self.request.settimeout(30)
        try:
            head, remainder = _read_headers(self.request)
            lines = head.decode("iso-8859-1").split("\r\n")
            method, target, version = lines[0].split(" ", 2)
            headers = [line for line in lines[1:] if not line.lower().startswith("proxy-connection:")]
            if method.upper() == "CONNECT":
                host, port = _host_and_port(target, 443)
                upstream = self._connect(host, port)
                self.request.sendall(b"HTTP/1.1 200 Connection Established\r\n\r\n")
            else:
                if target.startswith(("http://", "https://")):
                    validate_url(target)
                    parsed = urlsplit(target)
                else:
                    host_header = next((line.split(":", 1)[1].strip() for line in headers if line.lower().startswith("host:")), "")
                    parsed = urlsplit(f"http://{host_header}{target}")
                    validate_url(parsed.geturl())
                host = parsed.hostname or ""
                port = parsed.port or (443 if parsed.scheme == "https" else 80)
                upstream = self._connect(host, port)
                origin_target = parsed.path or "/"
                if parsed.query:
                    origin_target += f"?{parsed.query}"
                forwarded = "\r\n".join([f"{method} {origin_target} {version}", *headers]).encode("iso-8859-1")
                upstream.sendall(forwarded + b"\r\n\r\n" + remainder)
            try:
                _relay(self.request, upstream)
            finally:
                upstream.close()
        except (OSError, RuntimeError, ValueError):
            try:
                self.request.sendall(b"HTTP/1.1 403 Forbidden\r\nConnection: close\r\nContent-Length: 0\r\n\r\n")
            except OSError:
                pass

    def _connect(self, host: str, port: int) -> socket.socket:
        family, sockaddr, _ = resolve_target(host, port, self.server.allow_private)
        upstream = socket.socket(family, socket.SOCK_STREAM)
        upstream.settimeout(30)
        try:
            upstream.connect(sockaddr)
        except Exception:
            upstream.close()
            raise
        return upstream


class _GuardedProxyServer(socketserver.ThreadingMixIn, socketserver.TCPServer):
    allow_reuse_address = True
    daemon_threads = True

    def __init__(self, allow_private: bool) -> None:
        self.allow_private = allow_private
        super().__init__(("127.0.0.1", 0), _GuardedProxyHandler)


@contextmanager
def guarded_proxy(allow_private: bool = False) -> Iterator[str]:
    server = _GuardedProxyServer(allow_private)
    thread = threading.Thread(target=server.serve_forever, name="seo-workbench-network-boundary", daemon=True)
    thread.start()
    try:
        yield f"http://127.0.0.1:{server.server_address[1]}"
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)
