"""Real-process smoke: ``python -m zotero_mcp`` over stdio against a loopback fake Zotero.

Unit tests call tool functions in-process. These tests launch the actual entry
point the VSIX/Claude Desktop use, so startup, argument/env handling, stdio
framing and the full MCP -> HTTP path are exercised together, including the
failure paths (Zotero not running, bad configuration).
"""

from __future__ import annotations

import json
import os
import socket
import subprocess
import sys
from collections.abc import Iterator
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from threading import Thread
from urllib.parse import parse_qs, urlsplit

import pytest
from mcp.client import Client
from mcp.client.stdio import StdioServerParameters, stdio_client

KNOWN = "ABCD2345"
UNKNOWN = "BCDE3456"
SERVER_ID = "stdio-smoke"


class _FakeZotero(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"

    def log_message(self, *_args: object) -> None:  # keep pytest output quiet
        pass

    def _send(self, body: bytes, *, content_type: str = "application/json", **headers: str) -> None:
        self.send_response(200)
        for name, value in {
            "Content-Type": content_type,
            "Content-Length": str(len(body)),
            "Zotero-API-Version": "3",
            "Zotero-Schema-Version": "42",
            "Zotero-Server-ID": SERVER_ID,
            **headers,
        }.items():
            self.send_header(name, value)
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self) -> None:  # noqa: N802
        parsed = urlsplit(self.path)
        query = {k: v[0] for k, v in parse_qs(parsed.query).items()}
        if parsed.path == "/connector/ping":
            self._send(b"Zotero is running", content_type="text/plain", **{"X-Zotero-Version": "10.0.5"})
        elif parsed.path == "/api/":
            self._send(b'{"version":3}')
        elif parsed.path == "/api/users/0/items" and "itemKey" in query:
            present = [key for key in query["itemKey"].split(",") if key == KNOWN]
            if query.get("format") == "bibtex":
                body = "".join(f"@article{{{key}, title={{Stored}}}}\n" for key in present).encode()
                self._send(body, content_type="application/x-bibtex", **{"Total-Results": str(len(present))})
            elif "include" in query:
                rows = [{"key": key, "bib": f"<div>{query.get('style')}:{key}</div>", "citation": "(Stored)"} for key in present]
                self._send(json.dumps(rows).encode(), **{"Total-Results": str(len(rows))})
            else:
                self._send(b"[]", **{"Total-Results": "0"})
        else:
            self.send_response(404)
            self.send_header("Content-Length", "0")
            self.end_headers()


@pytest.fixture
def fake_zotero() -> Iterator[int]:
    server = ThreadingHTTPServer(("127.0.0.1", 0), _FakeZotero)
    thread = Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield server.server_address[1]
    finally:
        server.shutdown()
        server.server_close()


def _closed_port() -> int:
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        return sock.getsockname()[1]  # released on exit, so nothing listens on it


def _params(port: int, **extra_env: str) -> StdioServerParameters:
    env = {k: v for k, v in os.environ.items() if not k.startswith("ZOTERO_")}
    env.update({"ZOTERO_HOST": "127.0.0.1", "ZOTERO_PORT": str(port), "PYTHONUTF8": "1", **extra_env})
    return StdioServerParameters(command=sys.executable, args=["-m", "zotero_mcp"], env=env)


@pytest.mark.asyncio
async def test_stdio_server_exposes_the_documented_surface_and_round_trips_exports(fake_zotero):
    async with Client(stdio_client(_params(fake_zotero))) as client:
        names = {tool.name for tool in (await client.list_tools()).tools}
        assert len(names) == 50
        assert {"export_items", "get_bibliography", "import_articles", "check_connection"} <= names
        assert not names & {"import_ris_to_zotero", "import_from_pmids", "batch_import_from_pubmed"}  # legacy bridge stays opt-in

        connection = (await client.call_tool("check_connection", {})).structured_content
        assert connection["connected"] is True and connection["zotero_version"] == "10.0.5"

        export = (await client.call_tool("export_items", {"item_keys": [KNOWN, UNKNOWN], "format": "bibtex"})).structured_content
        assert export["success"] and f"@article{{{KNOWN}" in export["content"]
        assert (export["requested_count"], export["exported_count"], export["missing_count"]) == (2, 1, 1)

        bibliography = (
            await client.call_tool("get_bibliography", {"item_keys": [KNOWN, UNKNOWN], "style": "vancouver"})
        ).structured_content
        assert bibliography["entries"] == [{"key": KNOWN, "bib": f"<div>vancouver:{KNOWN}</div>"}]
        assert bibliography["missing_keys"] == [UNKNOWN]


@pytest.mark.asyncio
async def test_stdio_server_degrades_to_structured_errors_when_zotero_is_not_running():
    async with Client(stdio_client(_params(_closed_port()))) as client:
        connection = (await client.call_tool("check_connection", {})).structured_content
        assert connection["connected"] is False and "hint" in connection

        export = (await client.call_tool("export_items", {"item_keys": [KNOWN]})).structured_content
        assert export["success"] is False and export["error"]["code"] == "connection_error"

        invalid = (await client.call_tool("export_items", {"item_keys": ["../etc/passwd"]})).structured_content
        assert invalid["error"]["code"] == "invalid_key"  # rejected before any network I/O


@pytest.mark.parametrize(
    ("env", "args", "message"),
    [
        ({"ZOTERO_PORT": "abc"}, [], "ZOTERO_PORT must be an integer"),
        ({"ZOTERO_PORT": "70000"}, [], "ZOTERO_PORT must be an integer"),
        ({"ZOTERO_TIMEOUT": "-3"}, [], "ZOTERO_TIMEOUT must be a positive number"),
        ({}, ["--port", "0"], "--port must be between 1 and 65535"),
        ({}, ["--transport", "carrier-pigeon"], "invalid choice"),
    ],
)
def test_invalid_configuration_exits_with_a_usage_error_not_a_traceback(env, args, message):
    clean = {k: v for k, v in os.environ.items() if not k.startswith("ZOTERO_")}
    result = subprocess.run(
        [sys.executable, "-m", "zotero_mcp", *args],
        env={**clean, "PYTHONUTF8": "1", **env},
        capture_output=True,
        text=True,
        timeout=60,
        check=False,
    )
    assert result.returncode == 2, result.stderr
    assert message in result.stderr
    assert "Traceback" not in result.stderr
