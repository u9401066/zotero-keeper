"""End-to-end smoke tests for the public Zotero 10+ Local API MCP surface.

The fake Zotero service is a real loopback HTTP server.  This keeps the test
deterministic in CI while exercising the complete MCP Client -> MCPServer ->
ZoteroClient -> HTTP wire path instead of replacing the transport with mocks.
"""

from __future__ import annotations

import json
from collections.abc import Iterator
from contextlib import contextmanager
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from threading import Thread
from typing import Any

from mcp.client import Client
import pytest

from zotero_mcp.infrastructure.mcp.config import (
    McpServerConfig,
    ZoteroConfig as McpZoteroConfig,
)
from zotero_mcp.infrastructure.mcp.server import create_server


SERVER_ID = "keeper-smoke-server"
LOCAL_KEY = "S" * 32
COLLECTION_KEY = "ABCD2345"


class _ZoteroSmokeHandler(BaseHTTPRequestHandler):
    """Minimal stateful Zotero 10 Local API simulator."""

    protocol_version = "HTTP/1.1"
    requests: list[dict[str, Any]] = []

    def log_message(self, _format: str, *_args: Any) -> None:
        """Keep pytest output quiet."""

    def _body(self) -> bytes:
        length = int(self.headers.get("Content-Length", "0"))
        return self.rfile.read(length) if length else b""

    def _send(
        self,
        status: int,
        body: bytes = b"",
        *,
        content_type: str = "application/json",
        headers: dict[str, str] | None = None,
    ) -> None:
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Zotero-API-Version", "3")
        self.send_header("Zotero-Schema-Version", "42")
        self.send_header("Zotero-Server-ID", SERVER_ID)
        for name, value in (headers or {}).items():
            self.send_header(name, value)
        self.end_headers()
        if body:
            self.wfile.write(body)

    def _record(self, body: bytes = b"") -> None:
        self.requests.append(
            {
                "method": self.command,
                "path": self.path,
                "headers": {name.lower(): value for name, value in self.headers.items()},
                "body": body,
            }
        )

    def do_GET(self) -> None:  # noqa: N802 - stdlib handler contract
        self._record()
        if self.path == "/connector/ping":
            self._send(
                200,
                b"Zotero is running",
                content_type="text/plain",
                headers={
                    "X-Zotero-Version": "10.0.0",
                    "X-Zotero-Connector-API-Version": "3",
                },
            )
            return
        if self.path == "/api/":
            self._send(200, b'{"version":3}')
            return
        self._send(404, b'{"error":"not found"}')

    def do_POST(self) -> None:  # noqa: N802 - stdlib handler contract
        body = self._body()
        self._record(body)
        if self.path == "/api/local/authorize":
            if self.headers.get("Zotero-Server-ID") != SERVER_ID:
                self._send(412, b'{"error":"wrong server"}')
                return
            if json.loads(body) != {"appName": "Zotero Keeper"}:
                self._send(400, b'{"error":"bad app"}')
                return
            self._send(
                200,
                json.dumps({"key": LOCAL_KEY, "remember": True}).encode(),
            )
            return

        if self.path == "/api/users/0/collections":
            required_headers = {
                "Zotero-Server-ID": SERVER_ID,
                "Zotero-API-Key": LOCAL_KEY,
                "Zotero-API-Version": "3",
            }
            if any(self.headers.get(name) != value for name, value in required_headers.items()):
                self._send(401, b'{"error":"missing write identity"}')
                return
            token = self.headers.get("Zotero-Write-Token", "")
            if len(token) != 32:
                self._send(428, b'{"error":"missing token"}')
                return
            payload = json.loads(body)
            if payload != [{"name": "Smoke Collection"}]:
                self._send(400, b'{"error":"unexpected collection"}')
                return
            self._send(
                200,
                json.dumps(
                    {
                        "successful": {
                            "0": {
                                "key": COLLECTION_KEY,
                                "version": 1,
                                "data": {
                                    "key": COLLECTION_KEY,
                                    "version": 1,
                                    "name": "Smoke Collection",
                                    "parentCollection": False,
                                },
                            }
                        },
                        "unchanged": {},
                        "failed": {},
                    }
                ).encode(),
            )
            return

        self._send(404, b'{"error":"not found"}')


@contextmanager
def _fake_zotero() -> Iterator[tuple[ThreadingHTTPServer, type[_ZoteroSmokeHandler]]]:
    _ZoteroSmokeHandler.requests = []
    server = ThreadingHTTPServer(("127.0.0.1", 0), _ZoteroSmokeHandler)
    thread = Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield server, _ZoteroSmokeHandler
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)


@pytest.mark.asyncio
async def test_public_mcp_local_api_authorize_and_create_collection_smoke() -> None:
    """Exercise discovery, authorization, and one confirmed mutation end to end."""
    with _fake_zotero() as (http_server, handler):
        config = McpServerConfig(
            zotero=McpZoteroConfig(
                host="127.0.0.1",
                port=http_server.server_port,
                timeout=2,
            )
        )
        keeper = create_server(config)
        try:
            async with Client(keeper.mcp) as client:
                connection = await client.call_tool("check_connection", {})
                authorization = await client.call_tool("authorize_local_writes", {})
                proposal = await client.call_tool(
                    "create_collection",
                    {"name": "Smoke Collection"},
                )
                creation = await client.call_tool(
                    "create_collection",
                    {
                        "name": "Smoke Collection",
                        "confirm": True,
                        "expected_server_id": SERVER_ID,
                    },
                )
        finally:
            await keeper._zotero.close()

    assert connection.is_error is False
    assert connection.structured_content["connected"] is True
    assert connection.structured_content["capabilities"]["local_api_version"] == "3"
    assert connection.structured_content["capabilities"]["local_api_server_id"] == SERVER_ID

    assert authorization.is_error is False
    assert authorization.structured_content["authorized"] is True
    assert authorization.structured_content["remembered"] is True
    assert LOCAL_KEY not in json.dumps(authorization.structured_content)

    assert proposal.structured_content["confirmation_required"] is True
    assert creation.is_error is False
    assert creation.structured_content["success"] is True
    assert creation.structured_content["collection"]["key"] == COLLECTION_KEY

    paths = [(entry["method"], entry["path"]) for entry in handler.requests]
    assert paths == [
        ("GET", "/connector/ping"),
        ("GET", "/api/"),
        # Authorization refreshes the root identity even when check_connection
        # already observed one.
        ("GET", "/api/"),
        ("POST", "/api/local/authorize"),
        # Every confirmed mutation freshly binds its reviewed proposal to the
        # same Zotero database before sending the sole write.
        ("GET", "/api/"),
        ("POST", "/api/users/0/collections"),
    ]


@pytest.mark.asyncio
async def test_public_mcp_connection_failure_is_bounded_and_structured() -> None:
    """A missing Zotero process must not hang or escape as an MCP exception."""
    server = ThreadingHTTPServer(("127.0.0.1", 0), _ZoteroSmokeHandler)
    unused_port = server.server_port
    server.server_close()

    keeper = create_server(
        McpServerConfig(
            zotero=McpZoteroConfig(
                host="127.0.0.1",
                port=unused_port,
                timeout=0.25,
            )
        )
    )
    try:
        async with Client(keeper.mcp) as client:
            result = await client.call_tool("check_connection", {})
    finally:
        await keeper._zotero.close()

    assert result.is_error is False
    assert result.structured_content["connected"] is False
    assert "Zotero" in result.structured_content["message"]
