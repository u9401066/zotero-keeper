"""Complete scans reject partial data and database changes without retrying."""

from unittest.mock import AsyncMock, patch

import httpx
import pytest

from zotero_mcp.infrastructure.zotero_client.client import ZoteroAPIError, ZoteroClient


def page(keys, *, server="A", version="7", total=None):
    headers = {}
    if server is not None:
        headers["Zotero-Server-ID"] = server
    if version is not None:
        headers["Last-Modified-Version"] = version
    if total is not None:
        headers["Total-Results"] = str(total)
    return httpx.Response(200, json=[{"key": key} for key in keys], headers=headers)


@pytest.mark.asyncio
async def test_streams_pages_with_response_bound_cursor_and_server():
    client = ZoteroClient()
    client._local_server_id = "unrelated-shared-state"
    with patch.object(client, "_request_raw", AsyncMock(side_effect=[page(["A", "B"], total=3), page(["C"], total=3)])) as request:
        assert [p async for p in client.iter_item_pages(2)] == [[{"key": "A"}, {"key": "B"}], [{"key": "C"}]]
    assert request.await_count == 2
    assert request.call_args.kwargs["params"]["start"] == 2


@pytest.mark.asyncio
@pytest.mark.parametrize("second", [page(["C"], server="B"), page(["C"], version="8"), page(["C"], server=None)])
async def test_rejects_mixed_snapshots_without_retry(second):
    client = ZoteroClient()
    with patch.object(client, "_request_raw", AsyncMock(side_effect=[page(["A", "B"]), second])) as request:
        with pytest.raises(ZoteroAPIError, match="Library changed") as exc:
            _ = [p async for p in client.iter_item_pages(2)]
    assert exc.value.status_code == 412
    assert request.await_count == 2


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "responses",
    [
        [page(["A", "B"]), page(["B"])],
        [page([None])],
        [page(["A"], version=None)],
        [page(["A"], total="invalid")],
        [page(["A", "B"], total=1)],
        [page(["A"], total=2), page([], total=2)],
        [httpx.Response(200, json={"error": "bad"})],
        [httpx.Response(200, text="not JSON")],
    ],
)
async def test_malformed_or_incomplete_pages_fail_closed(responses):
    client = ZoteroClient()
    with patch.object(client, "_request_raw", AsyncMock(side_effect=responses)):
        with pytest.raises(ZoteroAPIError):
            _ = [p async for p in client.iter_item_pages(2)]


@pytest.mark.asyncio
async def test_total_results_handles_server_capped_short_pages():
    client = ZoteroClient()
    with patch.object(client, "_request_raw", AsyncMock(side_effect=[page(["A"], total=2), page(["B"], total=2)])):
        assert len([p async for p in client.iter_item_pages(500)]) == 2


@pytest.mark.asyncio
async def test_legacy_without_headers_terminates_on_short_page():
    client = ZoteroClient()
    with patch.object(client, "_request_raw", AsyncMock(return_value=page(["A"], server=None, version=None))):
        assert [p async for p in client.iter_item_pages(2)] == [[{"key": "A"}]]


@pytest.mark.asyncio
@pytest.mark.parametrize("size", [0, -1, True, 5001])
async def test_invalid_page_size_has_no_io(size):
    client = ZoteroClient()
    with patch.object(client, "_request_raw", AsyncMock()) as request:
        with pytest.raises(ValueError):
            _ = [p async for p in client.iter_item_pages(size)]
    request.assert_not_awaited()
