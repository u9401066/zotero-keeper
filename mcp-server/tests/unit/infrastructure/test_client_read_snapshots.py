"""Unit tests for response-bound Zotero Local API read snapshots."""

from unittest.mock import AsyncMock, Mock, patch

import pytest

from zotero_mcp.infrastructure.zotero_client.client import ZoteroClient, ZoteroConfig


def _response(payload: object, *, server_id: str | None) -> Mock:
    response = Mock()
    response.status_code = 200
    response.text = "{}"
    response.json.return_value = payload
    response.headers = {} if server_id is None else {"Zotero-Server-ID": server_id}
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
