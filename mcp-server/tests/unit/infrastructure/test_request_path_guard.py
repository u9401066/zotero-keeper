"""A key interpolated into a read path must never redirect the request to another endpoint."""

import httpx
import pytest

from zotero_mcp.infrastructure.zotero_client.client import ZoteroAPIError, ZoteroClient, ZoteroConfig


def _client(seen: list[str]) -> ZoteroClient:
    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(request.url.raw_path.decode())
        return httpx.Response(200, json={"key": "ABCD2345", "data": {}})

    client = ZoteroClient(config=ZoteroConfig(host="localhost", port=23119))
    client._client = httpx.AsyncClient(base_url=client.config.base_url, transport=httpx.MockTransport(handler))
    return client


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "key",
    [
        "../collections",
        "../../groups",
        "ABCD2345?limit=1",
        "ABCD2345#frag",
        "%2e%2e/collections",
        "ABCD 2345",
        "ABCD2345\n",
        "..",
        ".",
        "ABCD2345/../../tags",
        "ünï",
    ],
)
async def test_unsafe_keys_are_refused_before_any_request(key):
    seen: list[str] = []
    client = _client(seen)
    try:
        for call in (client.get_item, client.get_item_children, client.get_collection, client.get_search):
            with pytest.raises(ZoteroAPIError) as caught:
                await call(key)
            assert caught.value.status_code == 400
    finally:
        await client.close()
    assert seen == []


@pytest.mark.asyncio
async def test_well_formed_keys_still_reach_their_exact_endpoint():
    seen: list[str] = []
    client = _client(seen)
    try:
        await client.get_item("ABCD2345")
        await client.get_item_children("ABCD2345")
        await client.get_collection("BCDE3456")
    finally:
        await client.close()
    assert seen == ["/api/users/0/items/ABCD2345", "/api/users/0/items/ABCD2345/children", "/api/users/0/collections/BCDE3456"]
