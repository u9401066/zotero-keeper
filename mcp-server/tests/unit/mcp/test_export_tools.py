"""Tests for read-only export_items / get_bibliography."""

from unittest.mock import AsyncMock

import httpx
import pytest

from zotero_mcp.infrastructure.mcp.export_tools import register_export_tools
from zotero_mcp.infrastructure.zotero_client.client import ZoteroAPIError, ZoteroClient, ZoteroConfig

KEY = "ABCD2345"
OTHER = "BCDE3456"


def _wire_client(handler) -> ZoteroClient:
    client = ZoteroClient(config=ZoteroConfig(host="localhost", port=23119))
    client._client = httpx.AsyncClient(
        base_url=client.config.base_url,
        transport=httpx.MockTransport(handler),
    )
    return client


@pytest.fixture
def tools():
    client = AsyncMock()
    functions = {}

    class Server:
        @staticmethod
        def tool(**_kwargs):
            def register(fn):
                functions[fn.__name__] = fn
                return fn

            return register

    register_export_tools(Server(), client)
    return client, functions


@pytest.mark.asyncio
async def test_real_sdk_exposes_two_read_only_tools():
    from mcp.server import MCPServer

    server = MCPServer("export")
    register_export_tools(server, AsyncMock())
    listed = {tool.name: tool for tool in await server.list_tools()}
    assert set(listed) == {"export_items", "get_bibliography"}
    assert all(tool.annotations.read_only_hint for tool in listed.values())


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "keys",
    [[], "ABCD2345", ["not-a-key"], [f"AAAA{i:04d}" for i in range(51)]],
)
async def test_invalid_keys_never_reach_zotero(tools, keys):
    client, functions = tools
    result = await functions["export_items"](keys)
    assert result["error"]["code"] in {"invalid_keys", "invalid_key"}
    assert not client.mock_calls


@pytest.mark.asyncio
async def test_export_rejects_unknown_format_and_reports_missing(tools):
    client, functions = tools
    bad = await functions["export_items"]([KEY], format="pdf")
    assert bad["error"]["code"] == "invalid_format"
    client.export_items_snapshot.return_value = ("@article{x}", "srv", 1)
    result = await functions["export_items"]([KEY, OTHER, KEY], format="BibTeX")
    assert result["success"] and result["format"] == "bibtex"
    assert result["requested_count"] == 2 and result["missing_count"] == 1
    client.export_items_snapshot.assert_awaited_once_with([KEY, OTHER], "bibtex")


@pytest.mark.asyncio
async def test_bibliography_validation_and_missing_keys(tools):
    client, functions = tools
    assert (await functions["get_bibliography"]([KEY], style="../x"))["error"]["code"] == "invalid_style"
    assert (await functions["get_bibliography"]([KEY], output="html"))["error"]["code"] == "invalid_output"
    assert (await functions["get_bibliography"]([KEY], locale="en_US!"))["error"]["code"] == "invalid_locale"
    assert not client.mock_calls
    client.get_bibliography_snapshot.return_value = (
        [{"key": KEY, "bib": "<div>A</div>", "citation": "(A)"}, {"key": "ZZZZ9999", "bib": "ignored"}],
        "srv",
    )
    result = await functions["get_bibliography"]([KEY, OTHER], style="vancouver", output="bib", locale="en-US")
    assert result["entries"] == [{"key": KEY, "bib": "<div>A</div>"}]
    assert result["missing_keys"] == [OTHER]
    client.get_bibliography_snapshot.assert_awaited_once_with(
        [KEY, OTHER], style="vancouver", include="bib", linkwrap=False, locale="en-US"
    )


@pytest.mark.asyncio
async def test_zotero_errors_are_structured(tools):
    client, functions = tools
    client.export_items_snapshot.side_effect = ZoteroAPIError("nope", status_code=404)
    result = await functions["export_items"]([KEY])
    assert result["error"]["code"] == "not_found"


@pytest.mark.asyncio
async def test_client_uses_official_item_route_and_headers():
    seen = {}

    def handler(request: httpx.Request) -> httpx.Response:
        seen["path"] = request.url.path
        seen["params"] = dict(request.url.params)
        if request.url.params.get("format") == "bibtex":
            return httpx.Response(200, text="@article{a}", headers={"Total-Results": "2", "Zotero-Server-ID": "srv"})
        return httpx.Response(200, json=[{"key": KEY, "bib": "<div/>"}], headers={"Zotero-Server-ID": "srv"})

    client = _wire_client(handler)
    try:
        text, server_id, total = await client.export_items_snapshot([KEY, OTHER], "bibtex")
        assert (text, server_id, total) == ("@article{a}", "srv", 2)
        assert seen["path"] == "/api/users/0/items"
        assert seen["params"] == {"itemKey": f"{KEY},{OTHER}", "format": "bibtex", "limit": "2"}

        rows, server_id = await client.get_bibliography_snapshot([KEY], style="apa", include="bib,citation", linkwrap=True, locale="en-US")
        assert rows == [{"key": KEY, "bib": "<div/>"}] and server_id == "srv"
        assert seen["params"]["include"] == "bib,citation"
        assert seen["params"]["style"] == "apa" and seen["params"]["linkwrap"] == "1"
    finally:
        await client.close()
