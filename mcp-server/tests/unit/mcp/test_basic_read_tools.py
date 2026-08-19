"""Contract tests for the basic Zotero read tools."""

from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pytest

from zotero_mcp.infrastructure.mcp.basic_read_tools import register_basic_read_tools


def _registered_tools(zotero: AsyncMock) -> dict[str, Any]:
    tools: dict[str, Any] = {}
    mcp = MagicMock()

    def tool_decorator():
        def wrapper(function: Any) -> Any:
            tools[function.__name__] = function
            return function

        return wrapper

    mcp.tool = tool_decorator
    register_basic_read_tools(mcp, zotero)
    return tools


@pytest.mark.asyncio
async def test_get_item_exposes_instance_local_version_for_safe_updates() -> None:
    zotero = AsyncMock()
    # Shared discovery state may change after the HTTP response. The tool must
    # still label the object version with the identity from response A.
    zotero._local_server_id = "server-B"
    zotero.get_item_snapshot.return_value = (
        {
            "key": "ABCD2345",
            "version": 42,
            "data": {
                "itemType": "journalArticle",
                "title": "Versioned item",
            },
        },
        "server-A",
    )

    result = await _registered_tools(zotero)["get_item"]("ABCD2345")

    assert result["found"] is True
    assert result["item"]["version"] == 42
    assert result["item"]["version_scope"] == "local"
    assert result["server_id"] == "server-A"
    assert result["item"]["server_id"] == "server-A"


@pytest.mark.asyncio
async def test_get_item_accepts_version_in_data_payload() -> None:
    zotero = AsyncMock()
    zotero.get_item_snapshot.return_value = (
        {
            "key": "BCDE3456",
            "data": {
                "version": 7,
                "itemType": "journalArticle",
                "title": "Nested version",
            },
        },
        None,
    )

    result = await _registered_tools(zotero)["get_item"]("BCDE3456")

    assert result["item"]["version"] == 7
    assert result["item"]["version_scope"] == "local"
    assert result["server_id"] is None
    assert result["item"]["server_id"] is None


@pytest.mark.asyncio
async def test_get_item_exposes_attachment_replace_preconditions() -> None:
    zotero = AsyncMock()
    zotero.get_item_snapshot.return_value = (
        {
            "key": "BCDE3456",
            "version": 9,
            "data": {
                "itemType": "attachment",
                "title": "Full Text",
                "linkMode": "imported_file",
                "filename": "paper.pdf",
                "contentType": "application/pdf",
                "md5": "a" * 32,
            },
        },
        "server-A",
    )

    result = await _registered_tools(zotero)["get_item"]("BCDE3456")

    assert result["item"]["version"] == 9
    assert result["item"]["server_id"] == "server-A"
    assert result["item"]["md5"] == "a" * 32
    assert result["item"]["linkMode"] == "imported_file"
    assert result["item"]["filename"] == "paper.pdf"
    assert result["item"]["contentType"] == "application/pdf"


@pytest.mark.asyncio
async def test_list_items_uses_the_collection_response_identity() -> None:
    zotero = AsyncMock()
    zotero._local_server_id = "server-B"
    zotero.get_collection_items_snapshot.return_value = (
        [
            {
                "key": "ITEM0001",
                "version": 9,
                "data": {"itemType": "book", "title": "Snapshot item"},
            }
        ],
        "server-A",
    )

    result = await _registered_tools(zotero)["list_items"](limit=10, collection_key="COLL0001")

    assert result["server_id"] == "server-A"
    assert result["items"][0]["server_id"] == "server-A"
    assert result["items"][0]["version"] == 9


@pytest.mark.asyncio
async def test_list_tags_exposes_response_bound_library_cursor() -> None:
    zotero = AsyncMock()
    zotero.get_tags_snapshot.return_value = (
        [{"tag": "reviewed"}, {"tag": "needs PDF"}],
        42,
        "server-A",
    )

    result = await _registered_tools(zotero)["list_tags"]()

    assert result == {
        "count": 2,
        "tags": ["reviewed", "needs PDF"],
        "library_version": 42,
        "server_id": "server-A",
    }
    zotero.get_tags_snapshot.assert_awaited_once_with()
