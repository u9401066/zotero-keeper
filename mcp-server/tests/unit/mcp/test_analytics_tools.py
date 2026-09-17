"""Behavioral tests for honest coverage, partial failures and orphan categories."""

from unittest.mock import AsyncMock, MagicMock

import pytest

from zotero_mcp.infrastructure.mcp.analytics_tools import register_analytics_tools
from zotero_mcp.infrastructure.zotero_client.client import ZoteroAPIError


@pytest.fixture
def analytics():
    client = AsyncMock()
    client.get_items_snapshot.return_value = ([], "A")
    client.get_collections_snapshot.return_value = ([], "A")
    client.get_tags_snapshot.return_value = ([], 7, "A")
    tools = {}
    server = MagicMock()

    def register(**kwargs):
        def decorate(fn):
            tools[fn.__name__] = fn
            return fn

        return decorate

    server.tool = register
    register_analytics_tools(server, client)
    return client, tools


@pytest.mark.asyncio
async def test_failed_supplemental_reads_are_unknown_not_zero(analytics):
    client, tools = analytics
    client.get_collections_snapshot.side_effect = ZoteroAPIError("busy", status_code=409)
    result = await tools["get_library_stats"]()
    assert result["collection_stats"]["total_collections"] is None
    assert result["tag_stats"]["total_tags"] == 0
    assert result["warnings"] == [{"section": "collections", "error": "busy"}]


@pytest.mark.asyncio
async def test_stats_never_combine_databases(analytics):
    client, tools = analytics
    client.get_tags_snapshot.return_value = ([], 7, "B")
    result = await tools["get_library_stats"]()
    assert "Server-ID changed" in result["error"]
    assert "total_items" not in result


@pytest.mark.asyncio
@pytest.mark.parametrize("name", ["get_library_stats", "find_orphan_items"])
async def test_empty_library_still_returns_coverage(analytics, name):
    _, tools = analytics
    result = await tools[name]()
    assert result["scanned_count"] == 0
    assert result["scan_limit"] == 5000
    assert result["possibly_truncated"] is False
    assert result["server_id"] == "A"


@pytest.mark.asyncio
async def test_orphan_lists_agree_with_inclusive_summary_and_respect_limits(analytics):
    client, tools = analytics
    client.get_items_snapshot.return_value = (
        [
            {"key": "A", "data": {"itemType": "book", "title": "Unfiled"}},
            {"key": "B", "data": {"itemType": "book", "title": "Untagged", "collections": ["C"]}},
            {"key": "C", "data": {"itemType": "note", "title": "Ignore"}},
        ],
        "A",
    )
    result = await tools["find_orphan_items"](limit=1)
    assert result["summary"] == {"no_collection": 1, "no_tags": 2, "completely_orphan": 1}
    for field in ("no_collection", "no_tags", "completely_orphan"):
        assert [item["key"] for item in result[field]] == ["A"]
    result = await tools["find_orphan_items"](include_no_collection=False, include_no_tags=False)
    assert "no_collection" not in result and "no_tags" not in result
    assert result["summary"]["no_tags"] == 2


@pytest.mark.asyncio
@pytest.mark.parametrize("limit", [0, -1, True, 1001])
async def test_invalid_orphan_limit_has_no_io(analytics, limit):
    client, tools = analytics
    assert "error" in await tools["find_orphan_items"](limit=limit)
    assert not client.mock_calls
