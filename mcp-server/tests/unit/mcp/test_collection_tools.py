"""Contract tests for response-bound collection read identities."""

from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pytest

from zotero_mcp.infrastructure.mcp.collection_tools import register_collection_tools


def _registered_tools(zotero: AsyncMock) -> dict[str, Any]:
    tools: dict[str, Any] = {}
    mcp = MagicMock()

    def tool_decorator():
        def wrapper(function: Any) -> Any:
            tools[function.__name__] = function
            return function

        return wrapper

    mcp.tool = tool_decorator
    register_collection_tools(mcp, zotero)
    return tools


def _collection(key: str = "COLL0001", *, name: str = "Research") -> dict[str, Any]:
    return {
        "key": key,
        "version": 12,
        "data": {
            "name": name,
            "parentCollection": None,
            "numItems": 3,
        },
    }


@pytest.mark.asyncio
async def test_list_collections_uses_response_identity_after_shared_state_switch() -> None:
    zotero = AsyncMock()
    zotero._local_server_id = "server-B"
    zotero.get_collections_snapshot.return_value = ([_collection()], "server-A")

    result = await _registered_tools(zotero)["list_collections"]()

    assert result["server_id"] == "server-A"
    assert result["collections"][0]["server_id"] == "server-A"
    assert result["collections"][0]["version"] == 12


@pytest.mark.asyncio
async def test_get_collection_preserves_pre_zotero_10_missing_identity() -> None:
    zotero = AsyncMock()
    zotero._local_server_id = "stale-server-that-must-not-be-used"
    zotero.get_collection_snapshot.return_value = (_collection(), None)

    result = await _registered_tools(zotero)["get_collection"]("COLL0001")

    assert result["found"] is True
    assert result["server_id"] is None
    assert result["collection"]["server_id"] is None


@pytest.mark.asyncio
async def test_get_collection_items_labels_each_version_from_same_response() -> None:
    zotero = AsyncMock()
    zotero._local_server_id = "server-B"
    zotero.get_collection_items_snapshot.return_value = (
        [
            {
                "key": "ITEM0001",
                "version": 27,
                "data": {"itemType": "journalArticle", "title": "Bound item"},
            }
        ],
        "server-A",
    )

    result = await _registered_tools(zotero)["get_collection_items"]("COLL0001")

    assert result["server_id"] == "server-A"
    assert result["items"][0]["server_id"] == "server-A"
    assert result["items"][0]["version"] == 27


@pytest.mark.asyncio
async def test_find_collection_resolves_parent_and_child_from_one_snapshot() -> None:
    zotero = AsyncMock()
    parent = _collection("PARENT01", name="Parent")
    child = _collection("CHILD001", name="Child")
    child["data"]["parentCollection"] = "PARENT01"
    zotero.get_collections_snapshot.return_value = ([parent, child], "server-A")

    result = await _registered_tools(zotero)["find_collection"]("Child", parent_name="Parent")

    assert result["found"] is True
    assert result["server_id"] == "server-A"
    assert result["collection"]["server_id"] == "server-A"
    zotero.get_collections_snapshot.assert_awaited_once_with()
    zotero.find_collection_by_name.assert_not_awaited()
