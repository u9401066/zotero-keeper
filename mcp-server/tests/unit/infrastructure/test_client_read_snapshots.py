"""Unit tests for response-bound Zotero Local API read snapshots."""

from unittest.mock import AsyncMock, Mock, patch

import pytest

from zotero_mcp.infrastructure.zotero_client.client import ZoteroAPIError, ZoteroClient, ZoteroConfig


def _response(
    payload: object,
    *,
    server_id: str | None,
    library_version: str | None = None,
) -> Mock:
    response = Mock()
    response.status_code = 200
    response.text = "{}"
    response.json.return_value = payload
    response.headers = {}
    if server_id is not None:
        response.headers["Zotero-Server-ID"] = server_id
    if library_version is not None:
        response.headers["Last-Modified-Version"] = library_version
    return response


@pytest.mark.asyncio
async def test_item_snapshot_returns_response_id_after_shared_state_changes() -> None:
    client = ZoteroClient(ZoteroConfig())
    client._local_server_id = "server-A"

    async def switched_response(*args: object, **kwargs: object) -> Mock:
        del args, kwargs
        client._local_server_id = "server-B"
        return _response({"key": "ITEM0001", "version": 8}, server_id="server-A")

    with patch.object(client, "_request_raw", AsyncMock(side_effect=switched_response)):
        item, server_id = await client.get_item_snapshot("ITEM0001")

    assert item["version"] == 8
    assert client._local_server_id == "server-B"
    assert server_id == "server-A"


@pytest.mark.asyncio
async def test_collection_snapshot_does_not_infer_missing_server_id() -> None:
    client = ZoteroClient(ZoteroConfig())
    client._local_server_id = "stale-server"

    with patch.object(
        client,
        "_request_raw",
        AsyncMock(return_value=_response([{"key": "COLL0001"}], server_id=None)),
    ):
        collections, server_id = await client.get_collections_snapshot()

    assert collections == [{"key": "COLL0001"}]
    assert server_id is None


@pytest.mark.asyncio
async def test_tag_snapshot_accepts_zero_library_cursor_and_binds_server_id() -> None:
    client = ZoteroClient(ZoteroConfig())
    response = _response(
        [{"tag": "reviewed"}],
        server_id="server-A",
        library_version="0",
    )
    with patch.object(client, "_request_raw", AsyncMock(return_value=response)):
        tags, library_version, server_id = await client.get_tags_snapshot()

    assert tags == [{"tag": "reviewed"}]
    assert library_version == 0
    assert server_id == "server-A"


@pytest.mark.asyncio
@pytest.mark.parametrize("raw_version", [None, "", "-1", "01", "not-a-version"])
async def test_tag_snapshot_rejects_missing_or_malformed_zotero10_library_cursor(
    raw_version: str | None,
) -> None:
    client = ZoteroClient(ZoteroConfig())
    response = _response(
        [],
        server_id="server-A",
        library_version=raw_version,
    )
    with patch.object(client, "_request_raw", AsyncMock(return_value=response)):
        with pytest.raises(ZoteroAPIError, match="Last-Modified-Version"):
            await client.get_tags_snapshot()


@pytest.mark.asyncio
async def test_saved_search_snapshot_returns_exact_response_identity() -> None:
    client = ZoteroClient(ZoteroConfig())
    response = _response(
        {"key": "ABCD2345", "version": 7},
        server_id="server-A",
    )
    with patch.object(client, "_request_raw", AsyncMock(return_value=response)):
        search, server_id = await client.get_search_snapshot("ABCD2345")

    assert search == {"key": "ABCD2345", "version": 7}
    assert server_id == "server-A"
