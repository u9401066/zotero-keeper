"""Wire-level tests for the authorized Zotero 10+ Local API client."""

import json
import re
import asyncio
from pathlib import Path
from typing import Any

import httpx
import pytest

from zotero_mcp.infrastructure.zotero_client.client import (
    ZoteroAPIError,
    ZoteroClient,
    ZoteroConfig,
    ZoteroConnectionError,
)


def _wire_client(handler: Any, *, host: str = "localhost") -> ZoteroClient:
    client = ZoteroClient(config=ZoteroConfig(host=host, port=23119))
    client._client = httpx.AsyncClient(
        base_url=client.config.base_url,
        headers={"Content-Type": "application/json"},
        transport=httpx.MockTransport(handler),
    )
    return client


def _prime_authorization(client: ZoteroClient, *, remembered: bool = True) -> None:
    client._local_api_version = "3"
    client._local_server_id = "server-A"
    client._local_api_key = "K" * 32
    client._local_api_key_server_id = "server-A"
    client._local_api_key_remembered = remembered


class TestLocalDiscoveryAndAuthorization:
    @pytest.mark.asyncio
    async def test_discovery_binds_api_version_schema_and_server_id(self) -> None:
        captured: dict[str, Any] = {}

        def handler(request: httpx.Request) -> httpx.Response:
            captured["method"] = request.method
            captured["path"] = request.url.path
            return httpx.Response(
                200,
                headers={
                    "Zotero-API-Version": "3",
                    "Zotero-Schema-Version": "42",
                    "Zotero-Server-ID": "server-A",
                },
                json={"version": 3},
            )

        client = _wire_client(handler)
        try:
            result = await client.discover_local_api()
        finally:
            await client.close()

        assert captured == {"method": "GET", "path": "/api/"}
        assert result == {"api_version": "3", "schema_version": "42", "server_id": "server-A"}

    @pytest.mark.asyncio
    async def test_discovery_for_new_server_id_discards_bound_authorization(self) -> None:
        client = _wire_client(
            lambda request: httpx.Response(
                200,
                headers={"Zotero-API-Version": "3", "Zotero-Server-ID": "server-B"},
                json={},
            )
        )
        _prime_authorization(client)
        try:
            await client.discover_local_api()
            assert client._local_server_id == "server-B"
            assert client._local_api_key is None
            assert client._local_api_key_remembered is False
        finally:
            await client.close()

    @pytest.mark.asyncio
    @pytest.mark.parametrize(
        ("headers", "message"),
        [
            ({"Zotero-API-Version": "2", "Zotero-Server-ID": "server-A"}, "version 3"),
            ({"Zotero-API-Version": "3"}, "Zotero-Server-ID"),
        ],
    )
    async def test_discovery_rejects_non_v3_or_missing_server_id(
        self,
        headers: dict[str, str],
        message: str,
    ) -> None:
        client = _wire_client(lambda request: httpx.Response(200, headers=headers, json={}))
        try:
            with pytest.raises(ZoteroAPIError, match=message) as captured:
                await client.discover_local_api()
            assert captured.value.status_code == 501
        finally:
            await client.close()

    @pytest.mark.asyncio
    async def test_discovery_downgrade_clears_stale_zotero10_identity_and_key(self) -> None:
        client = _wire_client(
            lambda request: httpx.Response(
                200,
                headers={"Zotero-API-Version": "3"},
                json={"version": 3},
            )
        )
        _prime_authorization(client)
        client._local_schema_version = "42"
        try:
            with pytest.raises(ZoteroAPIError) as captured:
                await client.discover_local_api()
            assert captured.value.status_code == 501
            assert client._local_api_key is None
            assert client._local_api_key_remembered is False
            assert client._local_api_version is None
            assert client._local_schema_version is None
            assert client._local_server_id is None
        finally:
            await client.close()

    @pytest.mark.asyncio
    async def test_non_root_downgrade_read_clears_stale_identity_but_returns_data(self) -> None:
        """A Zotero 7-9 response must never inherit a cached Zotero 10 identity."""
        client = _wire_client(
            lambda request: httpx.Response(
                200,
                headers={"Zotero-API-Version": "3"},
                json={
                    "key": "ABCD2345",
                    "version": 1,
                    "data": {"key": "ABCD2345", "itemType": "book"},
                },
            )
        )
        _prime_authorization(client)
        try:
            item = await client.get_item("ABCD2345")
            assert item["key"] == "ABCD2345"
            assert client._local_api_key is None
            assert client._local_api_key_server_id is None
            assert client._local_api_version is None
            assert client._local_server_id is None
        finally:
            await client.close()

    @pytest.mark.asyncio
    async def test_first_local_read_binds_identity_and_next_read_sends_it(self) -> None:
        seen: list[str | None] = []

        def handler(request: httpx.Request) -> httpx.Response:
            seen.append(request.headers.get("zotero-server-id"))
            return httpx.Response(
                200,
                headers={
                    "Zotero-API-Version": "3",
                    "Zotero-Schema-Version": "42",
                    "Zotero-Server-ID": "server-A",
                },
                json={
                    "key": "ABCD2345",
                    "version": 1,
                    "data": {"key": "ABCD2345", "itemType": "book"},
                },
            )

        client = _wire_client(handler)
        try:
            await client.get_item("ABCD2345")
            assert client._local_server_id == "server-A"
            assert client._local_api_version == "3"
            await client.get_item("ABCD2345")
        finally:
            await client.close()

        assert seen == [None, "server-A"]

    @pytest.mark.asyncio
    async def test_fulltext_read_returns_server_bound_library_cursor(self) -> None:
        captured: list[dict[str, Any]] = []
        cursor_reads = 0

        def handler(request: httpx.Request) -> httpx.Response:
            nonlocal cursor_reads
            captured.append(
                {
                    "path": request.url.path,
                    "query": str(request.url.query),
                    "server_id": request.headers.get("zotero-server-id"),
                }
            )
            headers = {
                "Zotero-API-Version": "3",
                "Zotero-Server-ID": "server-A",
            }
            if request.url.path == "/api/users/0/items":
                cursor_reads += 1
                return httpx.Response(
                    200,
                    headers={**headers, "Last-Modified-Version": "23"},
                    json={"ABCD2345": 8},
                )
            return httpx.Response(
                200,
                headers={**headers, "Last-Modified-Version": "8"},
                json={"content": "indexed", "indexedChars": 7, "totalChars": 7},
            )

        client = _wire_client(handler)
        try:
            result = await client.get_item_fulltext("ABCD2345")
        finally:
            await client.close()

        assert cursor_reads == 2
        assert result == {
            "content": "indexed",
            "indexedChars": 7,
            "totalChars": 7,
            "libraryVersion": 23,
            "serverID": "server-A",
        }
        assert [entry["path"] for entry in captured] == [
            "/api/users/0/items",
            "/api/users/0/items/ABCD2345/fulltext",
            "/api/users/0/items",
        ]
        assert all("itemKey=ABCD2345" in entry["query"] for entry in (captured[0], captured[2]))
        assert all("format=versions" in entry["query"] for entry in (captured[0], captured[2]))
        assert [entry["server_id"] for entry in captured] == [None, "server-A", "server-A"]

    @pytest.mark.asyncio
    async def test_fulltext_read_rejects_cursor_race(self) -> None:
        cursor_versions = iter(("23", "24"))

        def handler(request: httpx.Request) -> httpx.Response:
            headers = {"Zotero-API-Version": "3", "Zotero-Server-ID": "server-A"}
            if request.url.path == "/api/users/0/items":
                return httpx.Response(
                    200,
                    headers={**headers, "Last-Modified-Version": next(cursor_versions)},
                    json={"ABCD2345": 8},
                )
            return httpx.Response(200, headers=headers, json={"content": "indexed"})

        client = _wire_client(handler)
        try:
            with pytest.raises(ZoteroAPIError, match="library changed") as captured:
                await client.get_item_fulltext("ABCD2345")
            assert captured.value.status_code == 412
        finally:
            await client.close()

    @pytest.mark.asyncio
    async def test_capability_probe_downgrade_does_not_report_stale_authorization(self) -> None:
        def handler(request: httpx.Request) -> httpx.Response:
            if request.url.path == "/connector/ping":
                return httpx.Response(
                    200,
                    headers={"X-Zotero-Version": "9.0.3"},
                    text="Zotero is running",
                )
            return httpx.Response(
                200,
                headers={"Zotero-API-Version": "3"},
                json=[],
            )

        client = _wire_client(handler)
        _prime_authorization(client)
        try:
            capabilities = await client.get_capabilities()
        finally:
            await client.close()

        assert capabilities["local_api_write_available"] is False
        assert capabilities["local_api_write_authorized"] is False
        assert capabilities["local_api_write_authorization_remembered"] is False

    @pytest.mark.asyncio
    async def test_security_sensitive_local_methods_refuse_remote_host_before_io(self) -> None:
        calls = 0

        def handler(request: httpx.Request) -> httpx.Response:
            nonlocal calls
            calls += 1
            return httpx.Response(200)

        client = _wire_client(handler, host="192.0.2.10")
        try:
            with pytest.raises(ZoteroConnectionError, match="loopback"):
                await client.discover_local_api()
        finally:
            await client.close()
        assert calls == 0

    @pytest.mark.asyncio
    async def test_authorization_uses_server_binding_and_never_returns_key(self) -> None:
        captured: dict[str, Any] = {}

        def handler(request: httpx.Request) -> httpx.Response:
            if request.url.path == "/api/":
                return httpx.Response(
                    200,
                    headers={
                        "Zotero-API-Version": "3",
                        "Zotero-Schema-Version": "42",
                        "Zotero-Server-ID": "server-A",
                    },
                    json={"version": 3},
                )
            captured["method"] = request.method
            captured["path"] = request.url.path
            captured["server_id"] = request.headers.get("zotero-server-id")
            captured["api_key"] = request.headers.get("zotero-api-key")
            captured["body"] = json.loads(request.content)
            return httpx.Response(
                200,
                headers={"Zotero-Server-ID": "server-A"},
                json={"key": "A" * 32, "remember": True},
            )

        client = _wire_client(handler)
        client._local_api_version = "3"
        client._local_server_id = "server-A"
        try:
            result = await client.authorize_local_writes("Research App")
            assert result == {
                "authorized": True,
                "remembered": True,
                "server_id": "server-A",
            }
            assert "key" not in result
            assert client._local_api_key == "A" * 32
        finally:
            await client.close()

        assert captured == {
            "method": "POST",
            "path": "/api/local/authorize",
            "server_id": "server-A",
            "api_key": None,
            "body": {"appName": "Research App"},
        }

    @pytest.mark.asyncio
    async def test_require_remembered_discards_single_use_authorization(self) -> None:
        def handler(request: httpx.Request) -> httpx.Response:
            if request.url.path == "/api/":
                return httpx.Response(
                    200,
                    headers={"Zotero-API-Version": "3", "Zotero-Server-ID": "server-A"},
                    json={"version": 3},
                )
            return httpx.Response(
                200,
                headers={"Zotero-Server-ID": "server-A"},
                json={"key": "A" * 32, "remember": False},
            )

        client = _wire_client(handler)
        client._local_api_version = "3"
        client._local_server_id = "server-A"
        try:
            with pytest.raises(ZoteroAPIError, match="Always Allow"):
                await client.authorize_local_writes(require_remembered=True)
            assert client._local_api_key is None
        finally:
            await client.close()

    @pytest.mark.asyncio
    async def test_authorization_response_without_server_id_fails_closed(self) -> None:
        def handler(request: httpx.Request) -> httpx.Response:
            if request.url.path == "/api/":
                return httpx.Response(
                    200,
                    headers={"Zotero-API-Version": "3", "Zotero-Server-ID": "server-A"},
                    json={"version": 3},
                )
            return httpx.Response(200, json={"key": "A" * 32, "remember": True})

        client = _wire_client(handler)
        try:
            with pytest.raises(ZoteroAPIError) as captured:
                await client.authorize_local_writes()
            assert captured.value.status_code == 412
            assert client._local_api_key is None
            assert client._local_api_key_server_id is None
            assert client._local_server_id is None
        finally:
            await client.close()

    @pytest.mark.asyncio
    async def test_concurrent_authorization_requests_share_one_prompt(self) -> None:
        prompts = 0

        async def handler(request: httpx.Request) -> httpx.Response:
            nonlocal prompts
            if request.url.path == "/api/":
                return httpx.Response(
                    200,
                    headers={"Zotero-API-Version": "3", "Zotero-Server-ID": "server-A"},
                    json={"version": 3},
                )
            prompts += 1
            await asyncio.sleep(0)
            return httpx.Response(
                200,
                headers={"Zotero-Server-ID": "server-A"},
                json={"key": "A" * 32, "remember": True},
            )

        client = _wire_client(handler)
        client._local_api_version = "3"
        client._local_server_id = "server-A"
        try:
            results = await asyncio.gather(
                client.authorize_local_writes(),
                client.authorize_local_writes(),
            )
        finally:
            await client.close()
        assert prompts == 1
        assert results == [
            {"authorized": True, "remembered": True, "server_id": "server-A"},
            {"authorized": True, "remembered": True, "server_id": "server-A"},
        ]

    @pytest.mark.asyncio
    async def test_authorization_server_switch_fails_once_then_rediscovers(self) -> None:
        requests: list[tuple[str, str, str | None]] = []
        authorize_calls = 0
        discovery_calls = 0

        def handler(request: httpx.Request) -> httpx.Response:
            nonlocal authorize_calls, discovery_calls
            requests.append((request.method, request.url.path, request.headers.get("zotero-server-id")))
            if request.url.path == "/api/":
                discovery_calls += 1
                discovered_server = "server-A" if discovery_calls == 1 else "server-B"
                return httpx.Response(
                    200,
                    headers={
                        "Zotero-API-Version": "3",
                        "Zotero-Schema-Version": "43",
                        "Zotero-Server-ID": discovered_server,
                    },
                    json={"version": 3},
                )
            authorize_calls += 1
            if authorize_calls == 1:
                return httpx.Response(
                    412,
                    headers={"Zotero-Server-ID": "server-B"},
                    text="wrong Zotero instance",
                )
            return httpx.Response(
                200,
                headers={"Zotero-Server-ID": "server-B"},
                json={"key": "B" * 32, "remember": True},
            )

        client = _wire_client(handler)
        client._local_api_version = "3"
        client._local_schema_version = "42"
        client._local_server_id = "server-A"
        try:
            with pytest.raises(ZoteroAPIError) as first_error:
                await client.authorize_local_writes()
            assert first_error.value.status_code == 412
            assert authorize_calls == 1
            assert client._local_api_key is None
            assert client._local_api_version is None
            assert client._local_schema_version is None
            assert client._local_server_id == "server-B"

            result = await client.authorize_local_writes()
        finally:
            await client.close()

        assert result == {
            "authorized": True,
            "remembered": True,
            "server_id": "server-B",
        }
        assert requests == [
            ("GET", "/api/", None),
            ("POST", "/api/local/authorize", "server-A"),
            ("GET", "/api/", None),
            ("POST", "/api/local/authorize", "server-B"),
        ]

    @pytest.mark.asyncio
    async def test_bound_reads_detect_server_switch_without_retry(self) -> None:
        calls = 0

        def handler(request: httpx.Request) -> httpx.Response:
            nonlocal calls
            calls += 1
            assert request.headers.get("zotero-server-id") == "server-A"
            return httpx.Response(
                412,
                headers={"Zotero-Server-ID": "server-B"},
                text="wrong Zotero instance",
            )

        client = _wire_client(handler)
        _prime_authorization(client)
        try:
            with pytest.raises(ZoteroAPIError) as captured:
                await client.get_item("ABCD2345")
            assert captured.value.status_code == 412
            assert calls == 1
            assert client._local_api_key is None
            assert client._local_api_version is None
            assert client._local_server_id == "server-B"
        finally:
            await client.close()


class TestLocalWriteContract:
    @pytest.mark.asyncio
    async def test_confirmed_operation_keeps_pinned_headers_during_concurrent_rebind(self) -> None:
        """A confirmed A flow cannot borrow a concurrently installed B key."""
        captured: list[dict[str, str | None]] = []
        operation_ready = asyncio.Event()
        rebound = asyncio.Event()

        def handler(request: httpx.Request) -> httpx.Response:
            if request.url.path == "/api/":
                return httpx.Response(
                    200,
                    headers={"Zotero-API-Version": "3", "Zotero-Server-ID": "server-A"},
                    json={"version": 3},
                )
            captured.append(
                {
                    "method": request.method,
                    "server_id": request.headers.get("zotero-server-id"),
                    "api_key": request.headers.get("zotero-api-key"),
                }
            )
            if request.method == "GET":
                return httpx.Response(
                    200,
                    headers={"Zotero-Server-ID": "server-A"},
                    json={
                        "key": "ABCD2345",
                        "version": 7,
                        "data": {"key": "ABCD2345", "itemType": "book"},
                    },
                )
            return httpx.Response(204, headers={"Zotero-Server-ID": "server-A"})

        client = _wire_client(handler)
        _prime_authorization(client)

        async def confirmed_flow() -> None:
            binding = await client.begin_local_operation("server-A")
            try:
                operation_ready.set()
                await rebound.wait()
                await client.get_item("ABCD2345")
                await client.local_update_item(
                    "ABCD2345",
                    {"title": "Pinned"},
                    expected_version=7,
                )
            finally:
                client.end_local_operation(binding)

        async def concurrent_rebind() -> None:
            await operation_ready.wait()
            client._local_api_version = "3"
            client._local_server_id = "server-B"
            client._local_api_key = "B" * 32
            client._local_api_key_server_id = "server-B"
            client._local_api_key_remembered = True
            rebound.set()

        try:
            await asyncio.gather(confirmed_flow(), concurrent_rebind())
        finally:
            await client.close()

        assert captured == [
            {"method": "GET", "server_id": "server-A", "api_key": None},
            {"method": "PATCH", "server_id": "server-A", "api_key": "K" * 32},
        ]

    @pytest.mark.asyncio
    async def test_concurrent_server_switch_aborts_bound_flow_before_write(self) -> None:
        """A real A-to-B switch yields one 412 and never mutates database B."""
        active_server = "server-A"
        operation_ready = asyncio.Event()
        b_authorized = asyncio.Event()
        write_calls = 0

        def handler(request: httpx.Request) -> httpx.Response:
            nonlocal write_calls
            if request.url.path == "/api/":
                return httpx.Response(
                    200,
                    headers={"Zotero-API-Version": "3", "Zotero-Server-ID": active_server},
                    json={"version": 3},
                )
            request_server = request.headers.get("zotero-server-id")
            if request.url.path == "/api/local/authorize":
                return httpx.Response(
                    200,
                    headers={"Zotero-Server-ID": active_server},
                    json={"key": "B" * 32, "remember": True},
                )
            if request_server != active_server:
                return httpx.Response(
                    412,
                    headers={"Zotero-Server-ID": active_server},
                    text="wrong Zotero instance",
                )
            if request.method != "GET":
                write_calls += 1
            return httpx.Response(
                200,
                headers={"Zotero-Server-ID": active_server},
                json={
                    "key": "ABCD2345",
                    "version": 7,
                    "data": {"key": "ABCD2345", "itemType": "book"},
                },
            )

        client = _wire_client(handler)
        _prime_authorization(client)

        async def flow_a() -> None:
            binding = await client.begin_local_operation("server-A")
            try:
                operation_ready.set()
                await b_authorized.wait()
                await client.get_item("ABCD2345")
                await client.local_update_item(
                    "ABCD2345",
                    {"title": "must not write"},
                    expected_version=7,
                )
            finally:
                client.end_local_operation(binding)

        async def switch_and_authorize_b() -> None:
            nonlocal active_server
            await operation_ready.wait()
            active_server = "server-B"
            result = await client.authorize_local_writes()
            assert result["server_id"] == "server-B"
            b_authorized.set()

        try:
            results = await asyncio.gather(
                flow_a(),
                switch_and_authorize_b(),
                return_exceptions=True,
            )
        finally:
            await client.close()

        assert isinstance(results[0], ZoteroAPIError)
        assert results[0].status_code == 412
        assert results[1] is None
        assert write_calls == 0

    @pytest.mark.asyncio
    async def test_create_item_sends_bound_key_and_exact_write_token(self) -> None:
        captured: dict[str, Any] = {}

        def handler(request: httpx.Request) -> httpx.Response:
            captured["method"] = request.method
            captured["path"] = request.url.path
            captured["headers"] = dict(request.headers)
            captured["body"] = json.loads(request.content)
            return httpx.Response(
                200,
                headers={"Zotero-Server-ID": "server-A"},
                json={"successful": {"0": {"key": "ABCD2345"}}},
            )

        client = _wire_client(handler)
        _prime_authorization(client, remembered=False)
        try:
            result = await client.local_create_item({"itemType": "book", "title": "Safe write"})
            assert result["successful"]["0"]["key"] == "ABCD2345"
            assert client._local_api_key is None
        finally:
            await client.close()

        assert captured["method"] == "POST"
        assert captured["path"] == "/api/users/0/items"
        assert captured["headers"]["zotero-server-id"] == "server-A"
        assert captured["headers"]["zotero-api-key"] == "K" * 32
        assert re.fullmatch(r"[0-9a-f]{32}", captured["headers"]["zotero-write-token"])
        assert captured["body"] == [{"itemType": "book", "title": "Safe write"}]

    @pytest.mark.asyncio
    async def test_single_use_key_cannot_be_raced_by_concurrent_writes(self) -> None:
        calls = 0

        async def handler(request: httpx.Request) -> httpx.Response:
            nonlocal calls
            calls += 1
            await asyncio.sleep(0)
            return httpx.Response(
                200,
                headers={"Zotero-Server-ID": "server-A"},
                json={"successful": {"0": {"key": "ABCD2345"}}},
            )

        client = _wire_client(handler)
        _prime_authorization(client, remembered=False)
        try:
            results = await asyncio.gather(
                client.local_create_item({"itemType": "book", "title": "one"}),
                client.local_create_item({"itemType": "book", "title": "two"}),
                return_exceptions=True,
            )
        finally:
            await client.close()

        assert calls == 1
        assert isinstance(results[0], dict)
        assert isinstance(results[1], ZoteroAPIError)
        assert results[1].status_code == 401

    @pytest.mark.asyncio
    @pytest.mark.parametrize("status_code", [401, 412, 428])
    async def test_security_statuses_fail_closed_without_retry(self, status_code: int) -> None:
        calls = 0

        def handler(request: httpx.Request) -> httpx.Response:
            nonlocal calls
            calls += 1
            return httpx.Response(status_code, text="precondition/auth failure")

        client = _wire_client(handler)
        _prime_authorization(client, remembered=True)
        try:
            with pytest.raises(ZoteroAPIError) as exc_info:
                await client.local_update_item(
                    "ABCD2345",
                    {"title": "No retry"},
                    expected_version=7,
                )
            assert exc_info.value.status_code == status_code
            assert calls == 1
            if status_code == 401:
                assert client._local_api_key is None
        finally:
            await client.close()

    @pytest.mark.asyncio
    async def test_412_preserves_headers_and_clears_auth_for_changed_server(self) -> None:
        def handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(
                412,
                text="wrong server",
                headers={"Zotero-Server-ID": "server-B", "Retry-After": "7"},
            )

        client = _wire_client(handler)
        _prime_authorization(client)
        try:
            with pytest.raises(ZoteroAPIError) as exc_info:
                await client.local_delete_item("ABCD2345", expected_version=2)
            assert exc_info.value.response_headers["zotero-server-id"] == "server-B"
            assert exc_info.value.server_id == "server-B"
            assert exc_info.value.retry_after == "7"
            assert client._local_api_key is None
            assert client._local_server_id == "server-B"
            assert client._local_api_version is None
        finally:
            await client.close()

    def test_api_error_ignores_non_mapping_mock_headers(self) -> None:
        error = ZoteroAPIError("safe", response_headers=object())  # type: ignore[arg-type]
        assert error.response_headers == {}

    @pytest.mark.asyncio
    async def test_item_collection_and_search_updates_and_deletes_require_version_header(self) -> None:
        captured: list[dict[str, Any]] = []

        def handler(request: httpx.Request) -> httpx.Response:
            captured.append(
                {
                    "method": request.method,
                    "path": request.url.path,
                    "version": request.headers.get("if-unmodified-since-version"),
                }
            )
            return httpx.Response(204, headers={"Zotero-Server-ID": "server-A"})

        client = _wire_client(handler)
        _prime_authorization(client)
        try:
            await client.local_update_item("ABCD2345", {"title": "x"}, expected_version=1)
            await client.local_delete_item("ABCD2345", expected_version=2)
            await client.local_update_collection(
                "BCDE3456",
                {"name": "x"},
                expected_version=3,
                replace=True,
            )
            await client.local_delete_collection("BCDE3456", expected_version=4)
            await client.local_update_search("CDEF4567", {"name": "x"}, expected_version=5)
            await client.local_delete_search("CDEF4567", expected_version=6)
        finally:
            await client.close()

        assert captured == [
            {"method": "PATCH", "path": "/api/users/0/items/ABCD2345", "version": "1"},
            {"method": "DELETE", "path": "/api/users/0/items/ABCD2345", "version": "2"},
            {"method": "PUT", "path": "/api/users/0/collections/BCDE3456", "version": "3"},
            {"method": "DELETE", "path": "/api/users/0/collections/BCDE3456", "version": "4"},
            {"method": "PATCH", "path": "/api/users/0/searches/CDEF4567", "version": "5"},
            {"method": "DELETE", "path": "/api/users/0/searches/CDEF4567", "version": "6"},
        ]

    @pytest.mark.asyncio
    @pytest.mark.parametrize(
        ("method_name", "payload", "expected_path"),
        [
            ("local_create_collection", {"name": "New"}, "/api/users/0/collections"),
            (
                "local_create_search",
                {"name": "Recent", "conditions": []},
                "/api/users/0/searches",
            ),
        ],
    )
    async def test_collection_and_search_creation_use_write_token(
        self,
        method_name: str,
        payload: dict[str, Any],
        expected_path: str,
    ) -> None:
        captured: dict[str, Any] = {}

        def handler(request: httpx.Request) -> httpx.Response:
            captured["path"] = request.url.path
            captured["token"] = request.headers.get("zotero-write-token")
            captured["body"] = json.loads(request.content)
            return httpx.Response(
                200,
                headers={"Zotero-Server-ID": "server-A"},
                json={"successful": {"0": {"key": "ABCD2345"}}},
            )

        client = _wire_client(handler)
        _prime_authorization(client)
        try:
            await getattr(client, method_name)(payload)
        finally:
            await client.close()

        assert captured["path"] == expected_path
        assert captured["body"] == [payload]
        assert re.fullmatch(r"[0-9a-f]{32}", captured["token"])

    @pytest.mark.asyncio
    @pytest.mark.parametrize(
        "payload",
        [
            {"successful": {}, "unchanged": {}, "failed": {}},
            {
                "successful": {},
                "unchanged": {},
                "failed": {"0": {"code": 409, "message": "library locked"}},
            },
        ],
    )
    async def test_create_rejects_empty_or_failed_multiwrite_result(
        self,
        payload: dict[str, Any],
    ) -> None:
        client = _wire_client(
            lambda request: httpx.Response(
                200,
                headers={"Zotero-Server-ID": "server-A"},
                json=payload,
            )
        )
        _prime_authorization(client)
        try:
            with pytest.raises(ZoteroAPIError) as captured:
                await client.local_create_collection({"name": "Rejected"})
        finally:
            await client.close()

        if payload["failed"]:
            assert captured.value.status_code == 409
            assert "library locked" in str(captured.value)
        else:
            assert "no created object" in str(captured.value)

    @pytest.mark.asyncio
    @pytest.mark.parametrize("success_field", ["successful", "success"])
    async def test_batch_update_normalizes_documented_success_maps(self, success_field: str) -> None:
        calls = 0
        captured: dict[str, Any] = {}

        def handler(request: httpx.Request) -> httpx.Response:
            nonlocal calls
            calls += 1
            captured["method"] = request.method
            captured["path"] = request.url.path
            captured["body"] = json.loads(request.content)
            return httpx.Response(
                200,
                json={
                    success_field: {"0": {"key": "ABCD2345"}},
                    "unchanged": {"1": "BCDE3456"},
                    "failed": {"2": {"code": 409, "message": "locked"}},
                },
            )

        items = [
            {"key": "ABCD2345", "version": 1, "collections": ["EFGH5678"]},
            {"key": "BCDE3456", "version": 2, "collections": ["EFGH5678"]},
            {"key": "CDEF4567", "version": 3, "collections": ["EFGH5678"]},
        ]
        client = _wire_client(handler)
        _prime_authorization(client)
        try:
            result = await client.local_batch_update_items(items)
        finally:
            await client.close()

        assert calls == 1
        assert captured == {"method": "POST", "path": "/api/users/0/items", "body": items}
        assert result == {
            "successful": {"0": {"key": "ABCD2345"}},
            "unchanged": {"1": "BCDE3456"},
            "failed": {"2": {"code": 409, "message": "locked"}},
        }

    @pytest.mark.asyncio
    @pytest.mark.parametrize(
        "items",
        [
            [],
            [{}],
            [{"key": "ABCD2345"}],
            [{"version": 1}],
            [{"key": "not-a-key", "version": 1}],
            [{"key": "ABCD2345", "version": True}],
            [{"key": "ABCD2345", "version": 1}] * 51,
        ],
    )
    async def test_batch_update_rejects_invalid_payload_before_io(self, items: list[dict[str, Any]]) -> None:
        calls = 0

        def handler(request: httpx.Request) -> httpx.Response:
            nonlocal calls
            calls += 1
            return httpx.Response(
                200,
                headers={"Zotero-Server-ID": "server-A"},
                json={},
            )

        client = _wire_client(handler)
        _prime_authorization(client)
        try:
            with pytest.raises(ValueError):
                await client.local_batch_update_items(items)
        finally:
            await client.close()
        assert calls == 0

    @pytest.mark.asyncio
    async def test_delete_tags_and_bulk_fulltext_send_library_preconditions(self) -> None:
        captured: list[dict[str, Any]] = []

        def handler(request: httpx.Request) -> httpx.Response:
            captured.append(
                {
                    "method": request.method,
                    "path": request.url.path,
                    "query": str(request.url.query),
                    "version": request.headers.get("if-unmodified-since-version"),
                    "body": json.loads(request.content) if request.content else None,
                }
            )
            if request.method == "DELETE":
                return httpx.Response(204, headers={"Zotero-Server-ID": "server-A"})
            return httpx.Response(
                200,
                headers={
                    "Last-Modified-Version": "11",
                    "Zotero-Server-ID": "server-A",
                },
                json={
                    "successful": {"0": {"key": "ABCD2345"}},
                    "success": {"0": "ABCD2345"},
                    "unchanged": {},
                    "failed": {},
                },
            )

        client = _wire_client(handler)
        _prime_authorization(client)
        try:
            await client.local_delete_tags(["one", "two words"], expected_version=9)
            result = await client.local_set_fulltext(
                "ABCD2345",
                {"content": "text", "indexedChars": 4, "totalChars": 4},
                expected_library_version=10,
            )
        finally:
            await client.close()

        assert captured[0]["method"] == "DELETE"
        assert captured[0]["path"] == "/api/users/0/tags"
        assert captured[0]["query"].count("tag=") == 1
        assert captured[0]["query"] == "b'tag=one%7C%7Ctwo+words'"
        assert captured[0]["version"] == "9"
        assert captured[1] == {
            "method": "POST",
            "path": "/api/users/0/fulltext",
            "query": "b''",
            "version": "10",
            "body": [{"key": "ABCD2345", "content": "text", "indexedChars": 4, "totalChars": 4}],
        }
        assert result == {"attachment_key": "ABCD2345", "library_version": 11}

    @pytest.mark.asyncio
    async def test_bulk_fulltexts_send_one_ten_entry_request_and_preserve_partial_results(self) -> None:
        captured: dict[str, Any] = {}

        def handler(request: httpx.Request) -> httpx.Response:
            captured["method"] = request.method
            captured["path"] = request.url.path
            captured["version"] = request.headers.get("if-unmodified-since-version")
            captured["body"] = json.loads(request.content)
            return httpx.Response(
                200,
                headers={
                    "Last-Modified-Version": "13",
                    "Zotero-Server-ID": "server-A",
                },
                json={
                    "successful": {"0": {"key": "ABCD2345"}},
                    "failed": {"1": {"key": "BCDE3456", "code": 400, "message": "unsupported"}},
                },
            )

        fulltexts = [
            {"key": "ABCD2345", "content": "one", "indexedChars": 3, "totalChars": 3},
            {"key": "BCDE3456", "content": "two", "indexedPages": 1, "totalPages": 1},
        ]
        client = _wire_client(handler)
        _prime_authorization(client)
        try:
            result = await client.local_set_fulltexts(fulltexts, expected_library_version=12)
        finally:
            await client.close()

        assert captured == {
            "method": "POST",
            "path": "/api/users/0/fulltext",
            "version": "12",
            "body": fulltexts,
        }
        assert result == {
            "successful": {"0": {"key": "ABCD2345"}},
            "failed": {"1": {"key": "BCDE3456", "code": 400, "message": "unsupported"}},
            "library_version": 13,
        }

    @pytest.mark.asyncio
    async def test_library_cursor_reads_response_bound_last_modified_version(self) -> None:
        captured: dict[str, Any] = {}

        def handler(request: httpx.Request) -> httpx.Response:
            captured["path"] = request.url.path
            captured["params"] = dict(request.url.params)
            return httpx.Response(
                200,
                headers={
                    "Last-Modified-Version": "0",
                    "Zotero-Server-ID": "server-A",
                },
                json={},
            )

        client = _wire_client(handler)
        client._local_server_id = "server-A"
        try:
            result = await client.get_library_cursor()
        finally:
            await client.close()

        assert captured == {
            "path": "/api/users/0/items",
            "params": {"format": "versions", "limit": "1"},
        }
        assert result == {"library_version": 0, "server_id": "server-A"}

    @pytest.mark.asyncio
    async def test_bulk_fulltext_surfaces_per_index_failure(self) -> None:
        client = _wire_client(
            lambda request: httpx.Response(
                200,
                headers={
                    "Last-Modified-Version": "10",
                    "Zotero-Server-ID": "server-A",
                },
                json={
                    "successful": {},
                    "failed": {"0": {"key": "ABCD2345", "code": 409, "message": "library locked"}},
                },
            )
        )
        _prime_authorization(client)
        try:
            with pytest.raises(ZoteroAPIError, match="library locked") as captured:
                await client.local_set_fulltext(
                    "ABCD2345",
                    {"content": "text", "indexedChars": 4, "totalChars": 4},
                    expected_library_version=10,
                )
            assert captured.value.status_code == 409
        finally:
            await client.close()

    @pytest.mark.asyncio
    @pytest.mark.parametrize(
        "payload",
        [
            {"successful": {}, "failed": {}},
            {"successful": {"0": {"key": "BCDE3456"}}, "failed": {}},
            {"successful": {"0": "ABCD2345"}, "failed": {}},
            {
                "successful": {"0": {"key": "ABCD2345"}},
                "failed": {"0": {"key": "ABCD2345", "code": 409, "message": "locked"}},
            },
            {"success": {"0": "ABCD2345"}, "failed": {}},
            {
                "successful": {"0": {"key": "ABCD2345"}, "1": {"key": "BCDE3456"}},
                "failed": {},
            },
        ],
    )
    async def test_bulk_fulltext_rejects_malformed_result_maps(self, payload: dict[str, Any]) -> None:
        client = _wire_client(
            lambda request: httpx.Response(
                200,
                headers={
                    "Last-Modified-Version": "11",
                    "Zotero-Server-ID": "server-A",
                },
                json=payload,
            )
        )
        _prime_authorization(client)
        try:
            with pytest.raises(ZoteroAPIError):
                await client.local_set_fulltext(
                    "ABCD2345",
                    {"content": "text", "indexedChars": 4, "totalChars": 4},
                    expected_library_version=10,
                )
        finally:
            await client.close()

    @pytest.mark.asyncio
    async def test_bulk_fulltext_412_is_never_retried(self) -> None:
        calls = 0

        def handler(request: httpx.Request) -> httpx.Response:
            nonlocal calls
            calls += 1
            return httpx.Response(
                412,
                headers={"Zotero-Server-ID": "server-A"},
                text="Library changed",
            )

        client = _wire_client(handler)
        _prime_authorization(client)
        try:
            with pytest.raises(ZoteroAPIError) as captured:
                await client.local_set_fulltext(
                    "ABCD2345",
                    {"content": "text", "indexedChars": 4, "totalChars": 4},
                    expected_library_version=10,
                )
            assert captured.value.status_code == 412
        finally:
            await client.close()
        assert calls == 1


class TestLocalFileAccess:
    @pytest.mark.asyncio
    async def test_file_view_url_uses_server_binding(self) -> None:
        captured: dict[str, Any] = {}

        def handler(request: httpx.Request) -> httpx.Response:
            captured["path"] = request.url.path
            captured["server_id"] = request.headers.get("zotero-server-id")
            return httpx.Response(
                200,
                headers={"Zotero-Server-ID": "server-A"},
                text="file:///zotero/storage/ABCD2345/paper.pdf\n",
            )

        client = _wire_client(handler)
        client._local_api_version = "3"
        client._local_server_id = "server-A"
        try:
            result = await client.get_item_file_view_url("ABCD2345")
        finally:
            await client.close()

        assert result == "file:///zotero/storage/ABCD2345/paper.pdf"
        assert captured == {
            "path": "/api/users/0/items/ABCD2345/file/view/url",
            "server_id": "server-A",
        }

    @pytest.mark.asyncio
    async def test_attach_file_requires_remembered_key_before_mutation(self, tmp_path: Path) -> None:
        attachment = tmp_path / "paper.pdf"
        attachment.write_bytes(b"%PDF")
        calls = 0

        def handler(request: httpx.Request) -> httpx.Response:
            nonlocal calls
            calls += 1
            return httpx.Response(500)

        client = _wire_client(handler)
        _prime_authorization(client, remembered=False)
        try:
            with pytest.raises(ZoteroAPIError, match="Always Allow"):
                await client.local_attach_file("ABCD2345", attachment)
        finally:
            await client.close()
        assert calls == 0

    @pytest.mark.asyncio
    async def test_attach_file_uses_child_create_and_three_phase_local_upload(self, tmp_path: Path) -> None:
        attachment = tmp_path / "paper.pdf"
        attachment.write_bytes(b"%PDF-1.7 safe bytes")
        captured: list[dict[str, Any]] = []

        async def handler(request: httpx.Request) -> httpx.Response:
            body = await request.aread()
            captured.append(
                {
                    "method": request.method,
                    "path": request.url.path,
                    "content_type": request.headers.get("content-type"),
                    "content_length": request.headers.get("content-length"),
                    "server_id": request.headers.get("zotero-server-id"),
                    "api_key": request.headers.get("zotero-api-key"),
                    "if_none_match": request.headers.get("if-none-match"),
                    "body": body,
                }
            )
            if request.url.path == "/api/users/0/items":
                return httpx.Response(
                    200,
                    headers={"Zotero-Server-ID": "server-A"},
                    json={"successful": {"0": {"key": "BCDE3456", "version": 2}}},
                )
            if request.url.path == "/api/users/0/items/BCDE3456/file" and b"md5=" in body:
                return httpx.Response(
                    200,
                    headers={"Zotero-Server-ID": "server-A"},
                    json={
                        "url": "http://localhost:23119/api/local/uploads/upload-key",
                        "uploadKey": "upload-key",
                        "contentType": "application/octet-stream",
                        "prefix": "前綴:",
                        "suffix": ":suffix",
                    },
                )
            if request.url.path == "/api/local/uploads/upload-key":
                return httpx.Response(201)
            if request.url.path == "/api/users/0/items/BCDE3456/file" and b"upload=" in body:
                return httpx.Response(
                    204,
                    headers={
                        "Last-Modified-Version": "8",
                        "Zotero-Server-ID": "server-A",
                    },
                )
            return httpx.Response(500, text="unexpected request")

        client = _wire_client(handler)
        _prime_authorization(client)
        try:
            result = await client.local_attach_file(
                "ABCD2345",
                attachment,
                title="Full Text PDF",
                content_type="application/pdf",
                source_url="https://example.test/paper.pdf",
            )
        finally:
            await client.close()

        assert result == {
            "attachment_key": "BCDE3456",
            "attachment": {"key": "BCDE3456", "version": 2},
            "uploaded": True,
            "exists": False,
            "last_modified_version": "8",
        }
        assert [entry["path"] for entry in captured] == [
            "/api/users/0/items",
            "/api/users/0/items/BCDE3456/file",
            "/api/local/uploads/upload-key",
            "/api/users/0/items/BCDE3456/file",
        ]
        child = json.loads(captured[0]["body"])[0]
        assert child["parentItem"] == "ABCD2345"
        assert child["linkMode"] == "imported_file"
        assert child["filename"] == "paper.pdf"
        assert captured[1]["server_id"] == "server-A"
        assert captured[1]["api_key"] == "K" * 32
        assert captured[1]["if_none_match"] == "*"
        assert captured[2]["server_id"] is None
        assert captured[2]["api_key"] is None
        expected_upload = "前綴:".encode() + attachment.read_bytes() + b":suffix"
        assert captured[2]["content_length"] == str(len(expected_upload))
        assert captured[2]["body"] == expected_upload
        assert captured[3]["server_id"] == "server-A"
        assert captured[3]["if_none_match"] == "*"

    @pytest.mark.asyncio
    async def test_replace_file_uses_old_md5_if_match_on_both_authenticated_phases(self, tmp_path: Path) -> None:
        replacement = tmp_path / "replacement.pdf"
        replacement.write_bytes(b"new replacement bytes")
        captured: list[dict[str, Any]] = []
        old_md5 = "a" * 32

        async def handler(request: httpx.Request) -> httpx.Response:
            body = await request.aread()
            captured.append(
                {
                    "path": request.url.path,
                    "if_match": request.headers.get("if-match"),
                    "if_none_match": request.headers.get("if-none-match"),
                    "server_id": request.headers.get("zotero-server-id"),
                    "api_key": request.headers.get("zotero-api-key"),
                    "body": body,
                }
            )
            if request.url.path == "/api/users/0/items/ABCD2345/file" and b"md5=" in body:
                return httpx.Response(
                    200,
                    headers={"Zotero-Server-ID": "server-A"},
                    json={
                        "url": "http://localhost:23119/api/local/uploads/replacement-key",
                        "uploadKey": "replacement-key",
                        "contentType": "application/octet-stream",
                        "prefix": "",
                        "suffix": "",
                    },
                )
            if request.url.path == "/api/local/uploads/replacement-key":
                return httpx.Response(201)
            if request.url.path == "/api/users/0/items/ABCD2345/file" and b"upload=" in body:
                return httpx.Response(
                    204,
                    headers={
                        "Last-Modified-Version": "14",
                        "Zotero-Server-ID": "server-A",
                    },
                )
            return httpx.Response(500, text="unexpected request")

        client = _wire_client(handler)
        _prime_authorization(client)
        try:
            result = await client.local_replace_attachment_file(
                "ABCD2345",
                replacement,
                expected_md5=old_md5,
            )
        finally:
            await client.close()

        assert result["attachment_key"] == "ABCD2345"
        assert result["previous_md5"] == old_md5
        assert result["uploaded"] is True
        assert result["last_modified_version"] == "14"
        assert [entry["path"] for entry in captured] == [
            "/api/users/0/items/ABCD2345/file",
            "/api/local/uploads/replacement-key",
            "/api/users/0/items/ABCD2345/file",
        ]
        for index in (0, 2):
            assert captured[index]["if_match"] == old_md5
            assert captured[index]["if_none_match"] is None
            assert captured[index]["server_id"] == "server-A"
            assert captured[index]["api_key"] == "K" * 32
        assert captured[1]["if_match"] is None
        assert captured[1]["server_id"] is None
        assert captured[1]["api_key"] is None

    @pytest.mark.asyncio
    async def test_replace_file_requires_remembered_authorization_before_io(self, tmp_path: Path) -> None:
        replacement = tmp_path / "replacement.pdf"
        replacement.write_bytes(b"replacement")
        calls = 0

        def handler(request: httpx.Request) -> httpx.Response:
            nonlocal calls
            calls += 1
            return httpx.Response(500)

        client = _wire_client(handler)
        _prime_authorization(client, remembered=False)
        try:
            with pytest.raises(ZoteroAPIError, match="Always Allow"):
                await client.local_replace_attachment_file(
                    "ABCD2345",
                    replacement,
                    expected_md5="a" * 32,
                )
        finally:
            await client.close()
        assert calls == 0

    @pytest.mark.asyncio
    async def test_replace_file_register_412_is_not_retried(self, tmp_path: Path) -> None:
        replacement = tmp_path / "replacement.pdf"
        replacement.write_bytes(b"replacement")
        calls = 0

        async def handler(request: httpx.Request) -> httpx.Response:
            nonlocal calls
            calls += 1
            body = await request.aread()
            if request.url.path.endswith("/file") and b"md5=" in body:
                return httpx.Response(
                    200,
                    headers={"Zotero-Server-ID": "server-A"},
                    json={
                        "url": "http://localhost:23119/api/local/uploads/replacement-key",
                        "uploadKey": "replacement-key",
                        "contentType": "application/octet-stream",
                        "prefix": "",
                        "suffix": "",
                    },
                )
            if request.url.path == "/api/local/uploads/replacement-key":
                return httpx.Response(201)
            return httpx.Response(
                412,
                headers={"Zotero-Server-ID": "server-A"},
                text="file changed",
            )

        client = _wire_client(handler)
        _prime_authorization(client)
        try:
            with pytest.raises(ZoteroAPIError) as captured:
                await client.local_replace_attachment_file(
                    "ABCD2345",
                    replacement,
                    expected_md5="a" * 32,
                )
            assert captured.value.status_code == 412
        finally:
            await client.close()
        assert calls == 3

    @pytest.mark.asyncio
    async def test_attach_file_rejects_upload_url_outside_same_origin(self, tmp_path: Path) -> None:
        attachment = tmp_path / "paper.pdf"
        attachment.write_bytes(b"%PDF")
        paths: list[str] = []

        async def handler(request: httpx.Request) -> httpx.Response:
            body = await request.aread()
            paths.append(request.url.path)
            if request.url.path == "/api/users/0/items":
                return httpx.Response(
                    200,
                    headers={"Zotero-Server-ID": "server-A"},
                    json={"success": {"0": "BCDE3456"}},
                )
            if b"md5=" in body:
                return httpx.Response(
                    200,
                    headers={"Zotero-Server-ID": "server-A"},
                    json={
                        "url": "http://example.com/api/local/uploads/upload-key",
                        "uploadKey": "upload-key",
                        "contentType": "application/octet-stream",
                        "prefix": "",
                        "suffix": "",
                    },
                )
            return httpx.Response(500)

        client = _wire_client(handler)
        _prime_authorization(client)
        try:
            with pytest.raises(ZoteroAPIError, match="loopback origin"):
                await client.local_attach_file("ABCD2345", attachment)
        finally:
            await client.close()

        assert paths == [
            "/api/users/0/items",
            "/api/users/0/items/BCDE3456/file",
        ]

    @pytest.mark.asyncio
    async def test_attach_file_allows_loopback_alias_upload_url(self, tmp_path: Path) -> None:
        attachment = tmp_path / "paper.pdf"
        attachment.write_bytes(b"%PDF")

        async def handler(request: httpx.Request) -> httpx.Response:
            body = await request.aread()
            if request.url.path == "/api/users/0/items":
                return httpx.Response(
                    200,
                    headers={"Zotero-Server-ID": "server-A"},
                    json={"success": {"0": "BCDE3456"}},
                )
            if request.url.path == "/api/users/0/items/BCDE3456/file" and b"md5=" in body:
                return httpx.Response(
                    200,
                    headers={"Zotero-Server-ID": "server-A"},
                    json={
                        "url": "http://127.0.0.1:23119/api/local/uploads/upload-key",
                        "uploadKey": "upload-key",
                        "contentType": "application/octet-stream",
                        "prefix": "",
                        "suffix": "",
                    },
                )
            if request.url.path == "/api/local/uploads/upload-key":
                return httpx.Response(201)
            if request.url.path == "/api/users/0/items/BCDE3456/file" and b"upload=" in body:
                return httpx.Response(204, headers={"Zotero-Server-ID": "server-A"})
            return httpx.Response(500)

        client = _wire_client(handler)
        _prime_authorization(client)
        try:
            result = await client.local_attach_file("ABCD2345", attachment)
        finally:
            await client.close()
        assert result["uploaded"] is True

    @pytest.mark.asyncio
    async def test_attach_failure_reports_durable_partial_child_key(self, tmp_path: Path) -> None:
        attachment = tmp_path / "paper.pdf"
        attachment.write_bytes(b"%PDF")

        async def handler(request: httpx.Request) -> httpx.Response:
            if request.url.path == "/api/users/0/items":
                return httpx.Response(
                    200,
                    headers={"Zotero-Server-ID": "server-A"},
                    json={"success": {"0": "BCDE3456"}},
                )
            return httpx.Response(500, text="upload authorization failed")

        client = _wire_client(handler)
        _prime_authorization(client)
        try:
            with pytest.raises(ZoteroAPIError) as exc_info:
                await client.local_attach_file("ABCD2345", attachment)
            assert exc_info.value.attachment_key == "BCDE3456"
            assert exc_info.value.partial is True
        finally:
            await client.close()

    @pytest.mark.asyncio
    async def test_close_forgets_local_authorization(self) -> None:
        client = _wire_client(lambda request: httpx.Response(200))
        _prime_authorization(client)
        await client.close()
        assert client._local_api_key is None
        assert client._local_server_id is None
        assert client._local_api_key_remembered is False
