"""Protocol-level tests for MCP SDK v2 interactive save authorization."""

from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager
from typing import Any
from unittest.mock import AsyncMock, patch

from mcp import types
from mcp.client import Client
from mcp.server import MCPServer
from mcp.shared.exceptions import MCPError
import pytest

from zotero_mcp.infrastructure.mcp.interactive_tools import register_interactive_save_tools


ARTICLE = {
    "itemType": "journalArticle",
    "title": "Protocol-safe article",
    "creators": [{"firstName": "Ada", "lastName": "Lovelace", "creatorType": "author"}],
}
TOOL_ARGUMENTS = {
    "item_type": "journalArticle",
    "title": ARTICLE["title"],
    "creators": ARTICLE["creators"],
    "auto_fetch_metadata": False,
}


@contextmanager
def interactive_server(
    *, duplicates: list[dict[str, Any]] | None = None
) -> Iterator[tuple[MCPServer[Any], AsyncMock, AsyncMock]]:
    """Create a real MCPServer while replacing every external read/write boundary."""
    zotero = AsyncMock()
    zotero.get_collections.return_value = [{"key": "COL1", "data": {"name": "Research"}}]

    async def get_collection(key: str) -> dict[str, Any]:
        if key != "COL1":
            raise KeyError(key)
        return {"key": key, "data": {"name": "Research"}}

    zotero.get_collection.side_effect = get_collection
    metadata = AsyncMock(return_value=(dict(ARTICLE), "user"))
    duplicate_lookup = AsyncMock(return_value=duplicates or [])
    suggestions = AsyncMock(return_value=[])

    with (
        patch(
            "zotero_mcp.infrastructure.mcp.interactive_tools.auto_fetch_and_merge",
            new=metadata,
        ),
        patch(
            "zotero_mcp.infrastructure.mcp.smart_tools._find_duplicates",
            new=duplicate_lookup,
        ),
        patch(
            "zotero_mcp.infrastructure.mcp.smart_tools._suggest_collections",
            new=suggestions,
        ),
    ):
        server: MCPServer[Any] = MCPServer("interactive-save-test")
        register_interactive_save_tools(server, zotero)
        yield server, zotero, metadata


@pytest.mark.asyncio
async def test_v2_schema_hides_resolvers_and_exposes_optional_extra_fields() -> None:
    with interactive_server() as (server, _, __):
        tool = next(tool for tool in await server.list_tools() if tool.name == "interactive_save")

    schema = tool.input_schema
    assert schema["required"] == ["item_type", "title"]
    assert schema["properties"]["extra_fields"]["default"] is None
    assert "candidate" not in schema["properties"]
    assert "duplicate_confirmation" not in schema["properties"]
    assert "collection_choice" not in schema["properties"]
    assert "root_confirmation" not in schema["properties"]
    assert "ctx" not in schema["properties"]


@pytest.mark.asyncio
@pytest.mark.parametrize("mode", ["auto", "legacy"])
async def test_collection_acceptance_writes_once_on_modern_and_legacy_protocols(mode: str) -> None:
    prompts: list[str] = []

    async def answer(_context: Any, params: types.ElicitRequestParams) -> types.ElicitResult:
        prompts.append(params.message)
        return types.ElicitResult(action="accept", content={"choice": "COL1"})

    with interactive_server() as (server, zotero, metadata):
        async with Client(server, mode=mode, elicitation_callback=answer) as client:
            result = await client.call_tool("interactive_save", TOOL_ARGUMENTS)

    assert result.is_error is False
    assert result.structured_content["success"] is True
    assert result.structured_content["saved_to"]["key"] == "COL1"
    assert len(prompts) == 1 and "Choose a collection key" in prompts[0]
    zotero.save_items.assert_awaited_once()
    assert zotero.save_items.await_args.args[0][0]["collections"] == ["COL1"]
    assert metadata.await_count >= 1  # Modern multi-round trips may rerun read-only resolvers.


@pytest.mark.asyncio
async def test_duplicate_rejection_does_not_prompt_for_collection_or_write() -> None:
    prompts: list[str] = []
    duplicate = {"title": ARTICLE["title"], "score": 100, "match_type": "title"}

    async def reject(_context: Any, params: types.ElicitRequestParams) -> types.ElicitResult:
        prompts.append(params.message)
        return types.ElicitResult(action="accept", content={"confirm": False})

    with interactive_server(duplicates=[duplicate]) as (server, zotero, _):
        async with Client(server, elicitation_callback=reject) as client:
            result = await client.call_tool("interactive_save", TOOL_ARGUMENTS)

    assert result.is_error is False
    assert result.structured_content["success"] is False
    assert result.structured_content["duplicate"] == duplicate
    assert len(prompts) == 1 and "Potential Duplicate" in prompts[0]
    zotero.save_items.assert_not_awaited()


@pytest.mark.asyncio
async def test_duplicate_acceptance_then_collection_writes_once() -> None:
    prompts: list[str] = []
    duplicate = {"title": ARTICLE["title"], "score": 100, "match_type": "title"}

    async def answer(_context: Any, params: types.ElicitRequestParams) -> types.ElicitResult:
        prompts.append(params.message)
        if "Potential Duplicate" in params.message:
            return types.ElicitResult(action="accept", content={"confirm": True})
        return types.ElicitResult(action="accept", content={"choice": "COL1"})

    with interactive_server(duplicates=[duplicate]) as (server, zotero, _):
        async with Client(server, elicitation_callback=answer) as client:
            result = await client.call_tool("interactive_save", TOOL_ARGUMENTS)

    assert result.is_error is False
    assert result.structured_content["success"] is True
    assert "Potential Duplicate" in prompts[0]
    assert "Choose a collection key" in prompts[1]
    zotero.save_items.assert_awaited_once()


@pytest.mark.asyncio
@pytest.mark.parametrize("action", ["decline", "cancel"])
async def test_declining_or_cancelling_collection_fails_closed(action: str) -> None:
    async def refuse(_context: Any, _params: types.ElicitRequestParams) -> types.ElicitResult:
        return types.ElicitResult(action=action)

    with interactive_server() as (server, zotero, _):
        async with Client(server, elicitation_callback=refuse) as client:
            result = await client.call_tool("interactive_save", TOOL_ARGUMENTS)

    assert result.is_error is True
    zotero.save_items.assert_not_awaited()


@pytest.mark.asyncio
async def test_missing_elicitation_callback_never_falls_back_to_library_root() -> None:
    with interactive_server() as (server, zotero, _):
        async with Client(server) as client:
            with pytest.raises(MCPError, match="elicitation capability"):
                await client.call_tool("interactive_save", TOOL_ARGUMENTS)

    zotero.save_items.assert_not_awaited()


@pytest.mark.asyncio
async def test_skip_collection_prompt_is_a_noninteractive_abort() -> None:
    with interactive_server() as (server, zotero, _):
        async with Client(server) as client:
            result = await client.call_tool(
                "interactive_save",
                {**TOOL_ARGUMENTS, "skip_collection_prompt": True},
            )

    assert result.is_error is False
    assert result.structured_content["success"] is False
    assert "no longer writes to My Library" in result.structured_content["message"]
    zotero.save_items.assert_not_awaited()


@pytest.mark.asyncio
@pytest.mark.parametrize("confirm_root, expected_success", [(False, False), (True, True)])
async def test_library_root_requires_a_second_explicit_confirmation(
    confirm_root: bool, expected_success: bool
) -> None:
    prompts: list[str] = []

    async def answer(_context: Any, params: types.ElicitRequestParams) -> types.ElicitResult:
        prompts.append(params.message)
        if "Choose a collection key" in params.message:
            return types.ElicitResult(action="accept", content={"choice": "ROOT"})
        return types.ElicitResult(action="accept", content={"confirm_root": confirm_root})

    with interactive_server() as (server, zotero, _):
        async with Client(server, elicitation_callback=answer) as client:
            result = await client.call_tool("interactive_save", TOOL_ARGUMENTS)

    assert result.is_error is False
    assert result.structured_content["success"] is expected_success
    assert len(prompts) == 2
    if expected_success:
        zotero.save_items.assert_awaited_once()
        assert "collections" not in zotero.save_items.await_args.args[0][0]
    else:
        zotero.save_items.assert_not_awaited()


@pytest.mark.asyncio
@pytest.mark.parametrize("action", ["decline", "cancel"])
async def test_declining_or_cancelling_root_confirmation_never_writes(action: str) -> None:
    prompts: list[str] = []

    async def answer(_context: Any, params: types.ElicitRequestParams) -> types.ElicitResult:
        prompts.append(params.message)
        if "Choose a collection key" in params.message:
            return types.ElicitResult(action="accept", content={"choice": "ROOT"})
        return types.ElicitResult(action=action)

    with interactive_server() as (server, zotero, _):
        async with Client(server, elicitation_callback=answer) as client:
            result = await client.call_tool("interactive_save", TOOL_ARGUMENTS)

    assert result.is_error is True
    assert len(prompts) == 2
    zotero.save_items.assert_not_awaited()


@pytest.mark.asyncio
async def test_invalid_collection_key_never_becomes_root() -> None:
    async def invalid(_context: Any, _params: types.ElicitRequestParams) -> types.ElicitResult:
        return types.ElicitResult(action="accept", content={"choice": "MISSING"})

    with interactive_server() as (server, zotero, _):
        async with Client(server, elicitation_callback=invalid) as client:
            result = await client.call_tool("interactive_save", TOOL_ARGUMENTS)

    assert result.is_error is False
    assert result.structured_content["success"] is False
    assert "no longer available" in result.structured_content["message"]
    zotero.save_items.assert_not_awaited()


@pytest.mark.asyncio
async def test_quick_save_requires_explicit_library_root_opt_in() -> None:
    with interactive_server() as (server, zotero, _):
        async with Client(server) as client:
            blocked = await client.call_tool(
                "quick_save",
                {**TOOL_ARGUMENTS, "force_add": True},
            )
            allowed = await client.call_tool(
                "quick_save",
                {**TOOL_ARGUMENTS, "force_add": True, "allow_library_root": True},
            )

    assert blocked.structured_content["success"] is False
    assert "No Zotero collection selected" in blocked.structured_content["message"]
    assert allowed.structured_content["success"] is True
    zotero.save_items.assert_awaited_once()


@pytest.mark.asyncio
async def test_quick_save_rejects_collection_name_without_a_usable_key() -> None:
    with interactive_server() as (server, zotero, _):
        zotero.find_collection_by_name.return_value = {"data": {"name": "Malformed"}}
        async with Client(server) as client:
            result = await client.call_tool(
                "quick_save",
                {
                    **TOOL_ARGUMENTS,
                    "force_add": True,
                    "collection_name": "Malformed",
                    # Even a separately authorized root write must not turn an
                    # invalid named destination into My Library.
                    "allow_library_root": True,
                },
            )

    assert result.is_error is False
    assert result.structured_content["success"] is False
    assert "no usable key" in result.structured_content["message"]
    zotero.save_items.assert_not_awaited()
