"""MCP contract tests for the Zotero 10+ Local API write tools."""

from __future__ import annotations

import asyncio
from pathlib import Path
from typing import Any
from unittest.mock import AsyncMock, MagicMock

from mcp.client import Client
from mcp.server import MCPServer
import pytest

from zotero_mcp.infrastructure.mcp.local_api_tools import register_local_api_tools
from zotero_mcp.infrastructure.zotero_client.client import ZoteroAPIError


COLLECTION_KEY = "QRST9876"
PARENT_KEY = "ABCD2345"
ITEM_KEY = "BCDE3456"
SECOND_ITEM_KEY = "CDEF4567"
ATTACHMENT_KEY = "DEFG5678"
SECOND_ATTACHMENT_KEY = "EFGH6789"
SEARCH_KEY = "FGHJ7892"
SERVER_ID = "test-zotero-server"

TOOL_NAMES = {
    "authorize_local_writes",
    "create_collection",
    "update_collection",
    "delete_collection",
    "add_items_to_collection",
    "remove_items_from_collection",
    "update_item_fields",
    "delete_item",
    "create_note",
    "create_saved_search",
    "update_saved_search",
    "delete_saved_search",
    "delete_tags",
    "attach_file_to_item",
    "replace_attachment_file",
    "set_attachment_fulltext",
    "set_attachment_fulltexts",
}


def _item(
    key: str,
    *,
    version: int = 7,
    item_type: str = "journalArticle",
    collections: list[str] | None = None,
) -> dict[str, Any]:
    return {
        "key": key,
        "version": version,
        "data": {
            "key": key,
            "version": version,
            "itemType": item_type,
            "title": f"Item {key}",
            "collections": list(collections or []),
        },
    }


def _collection(key: str = COLLECTION_KEY, name: str = "Research") -> dict[str, Any]:
    return {"key": key, "version": 3, "data": {"key": key, "version": 3, "name": name}}


def _attachment(key: str = ATTACHMENT_KEY, *, version: int = 9, md5: str = "a" * 32) -> dict[str, Any]:
    item = _item(key, version=version, item_type="attachment")
    item["data"].update({"linkMode": "imported_file", "md5": md5})
    return item


def _search(key: str = SEARCH_KEY, *, version: int = 5) -> dict[str, Any]:
    return {
        "key": key,
        "version": version,
        "data": {
            "key": key,
            "version": version,
            "name": "AI",
            "conditions": [{"condition": "title", "operator": "contains", "value": "AI"}],
        },
    }


def _registered_tools(zotero: AsyncMock) -> tuple[dict[str, Any], dict[str, Any]]:
    functions: dict[str, Any] = {}
    annotations: dict[str, Any] = {}
    mcp = MagicMock()

    def tool_decorator(**kwargs: Any):
        def wrapper(function: Any) -> Any:
            functions[function.__name__] = function
            annotations[function.__name__] = kwargs.get("annotations")
            return function

        return wrapper

    mcp.tool = tool_decorator
    register_local_api_tools(mcp, zotero)
    return functions, annotations


@pytest.fixture
def zotero() -> AsyncMock:
    client = AsyncMock()
    binding = object()
    client.begin_local_operation.return_value = binding
    client.end_local_operation = MagicMock()
    client.authorize_local_writes.return_value = {
        "authorized": True,
        "remembered": True,
        "server_id": SERVER_ID,
        # A defensive fixture: the MCP result must never expose this even if a
        # client adapter accidentally returns it.
        "key": "SECRET-LOCAL-API-KEY",
    }
    client.get_item_library_cursor.return_value = {
        "item_version": 99,
        "library_version": 23,
        "server_id": SERVER_ID,
    }
    client.get_library_cursor.return_value = {
        "library_version": 23,
        "server_id": SERVER_ID,
    }
    client.get_collection.return_value = _collection()
    client.get_item.side_effect = lambda key: _item(key)
    client.get_search.return_value = _search()
    client.local_create_collection.return_value = {"success": {"0": COLLECTION_KEY}}
    client.local_batch_update_items.return_value = {"successful": {"0": ITEM_KEY}, "unchanged": {}, "failed": {}}
    client.local_update_item.return_value = None
    client.local_create_item.return_value = {"successful": {"0": {"key": ATTACHMENT_KEY}}}
    client.local_create_search.return_value = {"successful": {"0": {"key": "EFGH6789"}}}
    client.local_attach_file.return_value = {"attachment_key": ATTACHMENT_KEY, "uploaded": True}
    client.local_replace_attachment_file.return_value = {
        "attachment_key": ATTACHMENT_KEY,
        "uploaded": True,
        "md5": "b" * 32,
    }
    client.local_set_fulltext.return_value = {
        "attachment_key": ATTACHMENT_KEY,
        "library_version": 24,
    }
    client.local_set_fulltexts.return_value = {
        "successful": {
            "0": {"key": ATTACHMENT_KEY},
            "1": {"key": SECOND_ATTACHMENT_KEY},
        },
        "failed": {},
        "library_version": 24,
    }
    return client


@pytest.mark.asyncio
async def test_real_mcp_surface_has_seventeen_closed_world_write_tools(zotero: AsyncMock) -> None:
    server: MCPServer[Any] = MCPServer("local-api-tools-test")
    register_local_api_tools(server, zotero)

    listed = {tool.name: tool for tool in await server.list_tools()}
    assert set(listed) == TOOL_NAMES
    destructive_tools = {
        "update_collection",
        "delete_collection",
        "remove_items_from_collection",
        "update_item_fields",
        "delete_item",
        "update_saved_search",
        "delete_saved_search",
        "delete_tags",
        "replace_attachment_file",
        "set_attachment_fulltext",
        "set_attachment_fulltexts",
    }
    for name, tool in listed.items():
        assert tool.annotations is not None
        assert tool.annotations.read_only_hint is False
        assert tool.annotations.destructive_hint is (name in destructive_tools)
        assert tool.annotations.open_world_hint is False

    assert listed["create_collection"].input_schema["properties"]["confirm"]["default"] is False
    assert listed["update_item_fields"].input_schema["required"] == ["item_key", "fields", "expected_version"]
    assert listed["set_attachment_fulltext"].input_schema["required"] == [
        "attachment_key",
        "content",
        "expected_library_version",
    ]
    assert listed["replace_attachment_file"].input_schema["required"] == [
        "attachment_key",
        "file_path",
        "expected_version",
        "expected_md5",
    ]
    assert listed["set_attachment_fulltexts"].input_schema["required"] == [
        "entries",
        "expected_library_version",
    ]
    assert "key" not in listed["authorize_local_writes"].input_schema["properties"]
    assert "api_key" not in str({tool.name: tool.input_schema for tool in listed.values()}).lower()


@pytest.mark.asyncio
async def test_in_memory_client_confirmation_smoke_performs_zero_io(zotero: AsyncMock) -> None:
    server: MCPServer[Any] = MCPServer("local-api-confirmation-test")
    register_local_api_tools(server, zotero)

    async with Client(server) as client:
        result = await client.call_tool("create_collection", {"name": "  New Research  "})

    assert result.is_error is False
    assert result.structured_content == {
        "success": False,
        "operation": "create_collection",
        "confirmation_required": True,
        "proposed": {
            "name": "New Research",
            "parent_collection_key": None,
            "expected_server_id": None,
        },
        "message": "Review the proposed Zotero change, then call again with confirm=true.",
    }
    zotero.get_collection.assert_not_awaited()
    zotero.local_create_collection.assert_not_awaited()
    zotero.authorize_local_writes.assert_not_awaited()


@pytest.mark.asyncio
async def test_confirm_false_is_zero_io_for_every_mutation(zotero: AsyncMock, tmp_path: Path) -> None:
    tools, _ = _registered_tools(zotero)
    proposed_file = tmp_path / "does-not-need-to-exist.pdf"
    calls = [
        tools["create_collection"]("Research", None, False),
        tools["update_collection"](COLLECTION_KEY, 3, name="Renamed", confirm=False),
        tools["delete_collection"](COLLECTION_KEY, 3, False),
        tools["add_items_to_collection"]([ITEM_KEY], COLLECTION_KEY, False),
        tools["remove_items_from_collection"]([ITEM_KEY], COLLECTION_KEY, False),
        tools["update_item_fields"](ITEM_KEY, {"title": "New"}, 7, False),
        tools["delete_item"](ITEM_KEY, 7, False),
        tools["create_note"](PARENT_KEY, "<p>Note</p>", False),
        tools["create_saved_search"](
            "AI",
            [{"condition": "title", "operator": "contains", "value": "AI"}],
            False,
        ),
        tools["update_saved_search"](SEARCH_KEY, 5, name="Renamed", confirm=False),
        tools["delete_saved_search"](SEARCH_KEY, 5, False),
        tools["delete_tags"](["reviewed"], 23, False),
        tools["attach_file_to_item"](PARENT_KEY, str(proposed_file), "Full Text PDF", False),
        tools["replace_attachment_file"](
            ATTACHMENT_KEY,
            str(proposed_file),
            9,
            "a" * 32,
            False,
        ),
        tools["set_attachment_fulltext"](
            ATTACHMENT_KEY,
            "content",
            8,
            indexed_pages=1,
            total_pages=1,
            confirm=False,
        ),
        tools["set_attachment_fulltexts"](
            [
                {
                    "attachment_key": ATTACHMENT_KEY,
                    "content": "content",
                    "indexed_chars": 7,
                    "total_chars": 7,
                }
            ],
            23,
            False,
        ),
    ]
    results = await asyncio.gather(*calls)

    assert all(result["confirmation_required"] is True for result in results)
    assert all("proposed" in result for result in results)
    for method_name in (
        "authorize_local_writes",
        "begin_local_operation",
        "verify_local_server",
        "get_collection",
        "get_item",
        "get_item_library_cursor",
        "get_library_cursor",
        "get_search",
        "local_create_collection",
        "local_update_collection",
        "local_delete_collection",
        "local_batch_update_items",
        "local_update_item",
        "local_delete_item",
        "local_create_item",
        "local_create_search",
        "local_update_search",
        "local_delete_search",
        "local_delete_tags",
        "local_attach_file",
        "local_replace_attachment_file",
        "local_set_fulltext",
        "local_set_fulltexts",
    ):
        getattr(zotero, method_name).assert_not_awaited()


@pytest.mark.asyncio
async def test_authorize_result_never_exposes_local_api_key(zotero: AsyncMock) -> None:
    tools, _ = _registered_tools(zotero)
    result = await tools["authorize_local_writes"]()

    assert result["success"] is True
    assert result["authorized"] is True
    assert result["remembered"] is True
    assert result["remembered_required"] is False
    assert result["server_id"] == "test-zotero-server"
    assert "SECRET-LOCAL-API-KEY" not in str(result)
    zotero.authorize_local_writes.assert_awaited_once_with(require_remembered=False)


@pytest.mark.asyncio
async def test_authorize_can_require_always_allow_for_attachment_uploads(zotero: AsyncMock) -> None:
    tools, _ = _registered_tools(zotero)

    result = await tools["authorize_local_writes"](require_remembered=True)

    assert result["success"] is True
    assert result["remembered"] is True
    assert result["remembered_required"] is True
    zotero.authorize_local_writes.assert_awaited_once_with(require_remembered=True)


@pytest.mark.asyncio
async def test_authorize_reports_pre_zotero_10_as_unsupported(zotero: AsyncMock) -> None:
    tools, _ = _registered_tools(zotero)
    zotero.authorize_local_writes.side_effect = ZoteroAPIError(
        "Zotero 10+ Local API did not provide Zotero-Server-ID",
        status_code=501,
    )

    result = await tools["authorize_local_writes"]()

    assert result["success"] is False
    assert result["error"]["code"] == "unsupported_local_write"
    assert result["error"]["http_status"] == 501


@pytest.mark.asyncio
async def test_authorize_maps_412_to_server_identity_mismatch(zotero: AsyncMock) -> None:
    tools, _ = _registered_tools(zotero)
    zotero.authorize_local_writes.side_effect = ZoteroAPIError(
        "wrong server",
        status_code=412,
        response_headers={"Zotero-Server-ID": "server-B"},
    )

    result = await tools["authorize_local_writes"]()

    assert result["error"]["code"] == "server_identity_mismatch"
    assert result["error"]["http_status"] == 412
    assert result["actual_server_id"] == "server-B"
    assert "reread" in result["error"]["message"]


@pytest.mark.asyncio
async def test_create_nested_collection_validates_parent_then_writes(zotero: AsyncMock) -> None:
    tools, _ = _registered_tools(zotero)
    zotero.get_collection.return_value = _collection(PARENT_KEY, "Parent")

    result = await tools["create_collection"](" Child ", PARENT_KEY, True, expected_server_id=SERVER_ID)

    assert result["success"] is True
    zotero.get_collection.assert_awaited_once_with(PARENT_KEY)
    zotero.local_create_collection.assert_awaited_once_with({"name": "Child", "parentCollection": PARENT_KEY})


@pytest.mark.asyncio
async def test_create_collection_does_not_report_failed_batch_entry_as_success(zotero: AsyncMock) -> None:
    tools, _ = _registered_tools(zotero)
    zotero.local_create_collection.return_value = {
        "successful": {},
        "unchanged": {},
        "failed": {"0": {"code": 409, "message": "library locked"}},
    }

    result = await tools["create_collection"]("Rejected", None, True, expected_server_id=SERVER_ID)

    assert result["success"] is False
    assert result["error"]["code"] == "library_locked"
    assert result["error"]["http_status"] == 409


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("tool_name", "client_method", "args"),
    [
        ("create_note", "local_create_item", (PARENT_KEY, "<p>Rejected</p>")),
        (
            "create_saved_search",
            "local_create_search",
            ("Rejected", [{"condition": "title", "operator": "contains", "value": "AI"}]),
        ),
    ],
)
async def test_create_tools_do_not_report_failed_batch_entry_as_success(
    zotero: AsyncMock,
    tool_name: str,
    client_method: str,
    args: tuple[Any, ...],
) -> None:
    tools, _ = _registered_tools(zotero)
    getattr(zotero, client_method).return_value = {
        "successful": {},
        "unchanged": {},
        "failed": {"0": {"code": 409, "message": "library locked"}},
    }

    result = await tools[tool_name](
        *args,
        confirm=True,
        expected_server_id=SERVER_ID,
    )

    assert result["success"] is False
    assert result["error"]["code"] == "library_locked"
    assert result["error"]["http_status"] == 409


@pytest.mark.asyncio
async def test_confirmed_mutation_requires_server_identity_before_io(zotero: AsyncMock) -> None:
    tools, _ = _registered_tools(zotero)

    result = await tools["create_collection"]("Research", None, True)

    assert result["error"]["code"] == "server_identity_required"
    zotero.begin_local_operation.assert_not_awaited()
    zotero.local_create_collection.assert_not_awaited()


@pytest.mark.asyncio
async def test_confirmed_mutation_fails_closed_on_server_switch(zotero: AsyncMock) -> None:
    tools, _ = _registered_tools(zotero)
    zotero.begin_local_operation.side_effect = ZoteroAPIError(
        "Zotero Server-ID changed after review",
        status_code=412,
        response_headers={"Zotero-Server-ID": "different-server"},
    )

    result = await tools["create_collection"]("Research", None, True, expected_server_id=SERVER_ID)

    assert result["error"]["code"] == "server_identity_mismatch"
    assert result["error"]["http_status"] == 412
    zotero.local_create_collection.assert_not_awaited()


@pytest.mark.asyncio
async def test_invalid_exact_key_fails_before_any_io(zotero: AsyncMock) -> None:
    tools, _ = _registered_tools(zotero)

    result = await tools["create_collection"]("Child", "bad-key", True)

    assert result["error"]["code"] == "invalid_key"
    zotero.get_collection.assert_not_awaited()
    zotero.local_create_collection.assert_not_awaited()


@pytest.mark.asyncio
async def test_add_items_merges_memberships_and_normalizes_partial_result(zotero: AsyncMock) -> None:
    tools, _ = _registered_tools(zotero)

    async def get_item(key: str) -> dict[str, Any]:
        if key == ITEM_KEY:
            return _item(key, version=10, collections=["FGHJ7892"])
        return _item(key, version=11, collections=[COLLECTION_KEY, "GHJK8923"])

    zotero.get_item.side_effect = get_item
    zotero.local_batch_update_items.return_value = {
        "successful": {},
        "unchanged": {},
        "failed": {"0": {"code": 400, "message": "bad item"}},
    }

    result = await tools["add_items_to_collection"](
        [ITEM_KEY, SECOND_ITEM_KEY],
        COLLECTION_KEY,
        True,
        expected_server_id=SERVER_ID,
    )

    zotero.local_batch_update_items.assert_awaited_once_with(
        [{"key": ITEM_KEY, "version": 10, "collections": ["FGHJ7892", COLLECTION_KEY]}]
    )
    assert result["success"] is False
    assert result["partial"] is True
    assert result["failed_count"] == 1
    assert result["unchanged_count"] == 1
    assert result["items"] == [
        {"key": ITEM_KEY, "status": "failed", "error": {"code": 400, "message": "bad item"}},
        {"key": SECOND_ITEM_KEY, "status": "unchanged"},
    ]


@pytest.mark.asyncio
async def test_add_items_finishes_validation_before_batch_write(zotero: AsyncMock) -> None:
    tools, _ = _registered_tools(zotero)

    async def mismatched_second(key: str) -> dict[str, Any]:
        if key == SECOND_ITEM_KEY:
            return _item("DEFG5678")
        return _item(key)

    zotero.get_item.side_effect = mismatched_second
    result = await tools["add_items_to_collection"](
        [ITEM_KEY, SECOND_ITEM_KEY],
        COLLECTION_KEY,
        True,
        expected_server_id=SERVER_ID,
    )

    assert result["error"]["code"] == "invalid_target"
    assert zotero.get_item.await_count == 2
    zotero.local_batch_update_items.assert_not_awaited()


@pytest.mark.asyncio
async def test_add_items_does_not_retry_batch_version_conflict(zotero: AsyncMock) -> None:
    tools, _ = _registered_tools(zotero)
    zotero.local_batch_update_items.side_effect = ZoteroAPIError("stale", status_code=412)

    result = await tools["add_items_to_collection"]([ITEM_KEY], COLLECTION_KEY, True, expected_server_id=SERVER_ID)

    assert result["error"]["code"] == "version_conflict"
    assert result["partial"] is False
    assert result["items"][0]["status"] == "failed"
    zotero.local_batch_update_items.assert_awaited_once()


@pytest.mark.asyncio
@pytest.mark.parametrize("field", ["key", "collections", "tags", "creators", "relations", "parentItem", "deleted"])
async def test_update_item_fields_rejects_structural_fields_without_io(zotero: AsyncMock, field: str) -> None:
    tools, _ = _registered_tools(zotero)

    result = await tools["update_item_fields"](ITEM_KEY, {field: "unsafe"}, 7, True)

    assert result["error"]["code"] == "forbidden_field"
    zotero.get_item.assert_not_awaited()
    zotero.local_update_item.assert_not_awaited()


@pytest.mark.asyncio
async def test_update_item_fields_uses_scalar_patch_and_expected_version(zotero: AsyncMock) -> None:
    tools, _ = _registered_tools(zotero)
    zotero.get_item.side_effect = None
    zotero.get_item.return_value = _item(ITEM_KEY, version=12)

    result = await tools["update_item_fields"](
        ITEM_KEY,
        {"title": "Updated", "DOI": "10.1/example"},
        12,
        True,
        expected_server_id=SERVER_ID,
    )

    assert result["success"] is True
    zotero.local_update_item.assert_awaited_once_with(
        ITEM_KEY,
        {"title": "Updated", "DOI": "10.1/example"},
        expected_version=12,
        replace=False,
    )


@pytest.mark.asyncio
async def test_update_item_fields_preflight_version_conflict_is_zero_write(zotero: AsyncMock) -> None:
    tools, _ = _registered_tools(zotero)
    zotero.get_item.side_effect = None
    zotero.get_item.return_value = _item(ITEM_KEY, version=13)

    result = await tools["update_item_fields"](
        ITEM_KEY,
        {"title": "Updated"},
        12,
        True,
        expected_server_id=SERVER_ID,
    )

    assert result["error"]["code"] == "version_conflict"
    assert result["error"]["http_status"] == 412
    zotero.local_update_item.assert_not_awaited()


@pytest.mark.asyncio
async def test_create_note_validates_exact_parent_and_uses_child_payload(zotero: AsyncMock) -> None:
    tools, _ = _registered_tools(zotero)
    zotero.get_item.side_effect = None
    zotero.get_item.return_value = _item(PARENT_KEY)

    result = await tools["create_note"](
        PARENT_KEY,
        " <p>Evidence note</p> ",
        True,
        expected_server_id=SERVER_ID,
    )

    assert result["success"] is True
    zotero.local_create_item.assert_awaited_once_with({"itemType": "note", "parentItem": PARENT_KEY, "note": "<p>Evidence note</p>"})


@pytest.mark.asyncio
async def test_create_saved_search_validates_and_preserves_supported_condition_fields(zotero: AsyncMock) -> None:
    tools, _ = _registered_tools(zotero)
    conditions = [{"condition": "title", "operator": "contains", "value": "AI", "required": True}]

    result = await tools["create_saved_search"](" AI papers ", conditions, True, expected_server_id=SERVER_ID)

    assert result["success"] is True
    zotero.local_create_search.assert_awaited_once_with({"name": "AI papers", "conditions": conditions})


@pytest.mark.asyncio
async def test_attach_file_to_item_uses_local_file_contract(zotero: AsyncMock, tmp_path: Path) -> None:
    tools, _ = _registered_tools(zotero)
    zotero.get_item.side_effect = None
    zotero.get_item.return_value = _item(PARENT_KEY)
    pdf = tmp_path / "paper.pdf"
    pdf.write_bytes(b"%PDF-1.7\n")

    result = await tools["attach_file_to_item"](
        PARENT_KEY,
        str(pdf),
        " Full Text ",
        True,
        expected_server_id=SERVER_ID,
    )

    resolved = pdf.resolve()
    assert result["success"] is True
    zotero.local_attach_file.assert_awaited_once_with(
        PARENT_KEY,
        resolved,
        title="Full Text",
        content_type="application/pdf",
        source_url="",
    )


@pytest.mark.asyncio
async def test_attach_file_reports_partial_child_when_upload_fails(zotero: AsyncMock, tmp_path: Path) -> None:
    tools, _ = _registered_tools(zotero)
    zotero.get_item.side_effect = None
    zotero.get_item.return_value = _item(PARENT_KEY)
    pdf = tmp_path / "paper.pdf"
    pdf.write_bytes(b"%PDF-1.7\n")
    error = ZoteroAPIError("upload failed", status_code=409)
    error.attachment_key = ATTACHMENT_KEY
    zotero.local_attach_file.side_effect = error

    result = await tools["attach_file_to_item"](
        PARENT_KEY,
        str(pdf),
        "Full Text",
        True,
        expected_server_id=SERVER_ID,
    )

    assert result["success"] is False
    assert result["partial"] is True
    assert result["attachment_key"] == ATTACHMENT_KEY
    assert result["error"]["code"] == "library_locked"
    zotero.local_attach_file.assert_awaited_once()


@pytest.mark.asyncio
async def test_set_attachment_fulltext_requires_one_complete_index_pair(zotero: AsyncMock) -> None:
    tools, _ = _registered_tools(zotero)

    result = await tools["set_attachment_fulltext"](
        ATTACHMENT_KEY,
        "text",
        8,
        indexed_pages=2,
        confirm=True,
    )

    assert result["error"]["code"] == "invalid_index_counts"
    zotero.get_item.assert_not_awaited()
    zotero.local_set_fulltext.assert_not_awaited()


@pytest.mark.asyncio
async def test_set_attachment_fulltext_validates_attachment_and_writes(zotero: AsyncMock) -> None:
    tools, _ = _registered_tools(zotero)
    zotero.get_item.side_effect = None
    # Object and library versions are distinct cursors. The object version is
    # deliberately unrelated to the reviewed library version.
    zotero.get_item.return_value = _item(ATTACHMENT_KEY, version=99, item_type="attachment")

    result = await tools["set_attachment_fulltext"](
        ATTACHMENT_KEY,
        "indexed content",
        23,
        indexed_pages=2,
        total_pages=3,
        confirm=True,
        expected_server_id=SERVER_ID,
    )

    assert result["success"] is True
    assert result["result"] == {
        "attachment_key": ATTACHMENT_KEY,
        "library_version": 24,
    }
    zotero.begin_local_operation.assert_awaited_once_with(SERVER_ID)
    zotero.get_item_library_cursor.assert_awaited_once_with(ATTACHMENT_KEY)
    zotero.local_set_fulltext.assert_awaited_once_with(
        ATTACHMENT_KEY,
        {"content": "indexed content", "indexedPages": 2, "totalPages": 3},
        expected_library_version=23,
    )


@pytest.mark.asyncio
async def test_set_attachment_fulltext_bulk_412_is_reported_without_tool_retry(zotero: AsyncMock) -> None:
    tools, _ = _registered_tools(zotero)
    zotero.get_item.side_effect = None
    zotero.get_item.return_value = _item(ATTACHMENT_KEY, version=99, item_type="attachment")
    zotero.local_set_fulltext.side_effect = ZoteroAPIError("library changed", status_code=412)

    result = await tools["set_attachment_fulltext"](
        ATTACHMENT_KEY,
        "indexed content",
        23,
        indexed_pages=2,
        total_pages=3,
        confirm=True,
        expected_server_id=SERVER_ID,
    )

    assert result["error"]["code"] == "version_conflict"
    assert result["error"]["http_status"] == 412
    assert result["expected_library_version"] == 23
    zotero.local_set_fulltext.assert_awaited_once()


@pytest.mark.asyncio
async def test_set_attachment_fulltext_stale_library_cursor_is_zero_write(zotero: AsyncMock) -> None:
    tools, _ = _registered_tools(zotero)
    zotero.get_item_library_cursor.return_value = {
        "item_version": 99,
        "library_version": 24,
        "server_id": SERVER_ID,
    }

    result = await tools["set_attachment_fulltext"](
        ATTACHMENT_KEY,
        "indexed content",
        23,
        indexed_chars=15,
        total_chars=15,
        confirm=True,
        expected_server_id=SERVER_ID,
    )

    assert result["error"]["code"] == "version_conflict"
    assert result["error"]["http_status"] == 412
    assert result["expected_library_version"] == 23
    assert result["actual_library_version"] == 24
    zotero.get_item.assert_not_awaited()
    zotero.local_set_fulltext.assert_not_awaited()


@pytest.mark.asyncio
async def test_set_attachment_fulltext_requires_reviewed_server_identity(zotero: AsyncMock) -> None:
    tools, _ = _registered_tools(zotero)

    result = await tools["set_attachment_fulltext"](
        ATTACHMENT_KEY,
        "indexed content",
        23,
        indexed_chars=15,
        total_chars=15,
        confirm=True,
    )

    assert result["error"]["code"] == "server_identity_required"
    zotero.get_item.assert_not_awaited()
    zotero.local_set_fulltext.assert_not_awaited()


@pytest.mark.asyncio
async def test_zotero_error_shape_is_stable(zotero: AsyncMock) -> None:
    tools, _ = _registered_tools(zotero)
    zotero.local_create_search.side_effect = ZoteroAPIError("locked", status_code=409)

    result = await tools["create_saved_search"](
        "AI",
        [{"condition": "title", "operator": "contains", "value": "AI"}],
        True,
        expected_server_id=SERVER_ID,
    )

    assert result == {
        "success": False,
        "operation": "create_saved_search",
        "confirmation_required": False,
        "error": {
            "code": "library_locked",
            "message": "locked",
            "http_status": 409,
            "retry_after": None,
        },
    }


@pytest.mark.asyncio
async def test_remove_items_from_collection_uses_fresh_item_versions(zotero: AsyncMock) -> None:
    tools, _ = _registered_tools(zotero)

    async def get_item(key: str) -> dict[str, Any]:
        if key == ITEM_KEY:
            return _item(key, version=10, collections=[COLLECTION_KEY, "GHJK8923"])
        return _item(key, version=11, collections=["GHJK8923"])

    zotero.get_item.side_effect = get_item
    zotero.local_batch_update_items.return_value = {
        "successful": {"0": {"key": ITEM_KEY, "version": 12}},
        "unchanged": {},
        "failed": {},
    }

    result = await tools["remove_items_from_collection"](
        [ITEM_KEY, ITEM_KEY, SECOND_ITEM_KEY],
        COLLECTION_KEY,
        True,
        expected_server_id=SERVER_ID,
    )

    assert result["success"] is True
    assert result["requested_count"] == 2
    assert result["changed_count"] == 1
    assert result["unchanged_count"] == 1
    zotero.local_batch_update_items.assert_awaited_once_with([{"key": ITEM_KEY, "version": 10, "collections": ["GHJK8923"]}])


@pytest.mark.asyncio
async def test_update_collection_checks_exact_version_and_moves_to_root(zotero: AsyncMock) -> None:
    tools, _ = _registered_tools(zotero)
    zotero.get_collection.return_value = _collection(COLLECTION_KEY, "Before")

    result = await tools["update_collection"](
        COLLECTION_KEY,
        3,
        name=" After ",
        move_to_library_root=True,
        confirm=True,
        expected_server_id=SERVER_ID,
    )

    assert result["success"] is True
    zotero.local_update_collection.assert_awaited_once_with(
        COLLECTION_KEY,
        {"name": "After", "parentCollection": False},
        expected_version=3,
        replace=False,
    )


@pytest.mark.asyncio
async def test_update_collection_stale_version_is_zero_write(zotero: AsyncMock) -> None:
    tools, _ = _registered_tools(zotero)
    stale = _collection()
    stale["version"] = 4
    stale["data"]["version"] = 4
    zotero.get_collection.return_value = stale

    result = await tools["update_collection"](
        COLLECTION_KEY,
        3,
        name="After",
        confirm=True,
        expected_server_id=SERVER_ID,
    )

    assert result["error"]["code"] == "version_conflict"
    zotero.local_update_collection.assert_not_awaited()


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("tool_name", "key", "version", "read_method", "delete_method", "result_key"),
    [
        ("delete_collection", COLLECTION_KEY, 3, "get_collection", "local_delete_collection", "collection_key"),
        ("delete_item", ITEM_KEY, 7, "get_item", "local_delete_item", "item_key"),
        ("delete_saved_search", SEARCH_KEY, 5, "get_search", "local_delete_search", "search_key"),
    ],
)
async def test_single_delete_tools_use_exact_object_version(
    zotero: AsyncMock,
    tool_name: str,
    key: str,
    version: int,
    read_method: str,
    delete_method: str,
    result_key: str,
) -> None:
    tools, _ = _registered_tools(zotero)
    if read_method == "get_item":
        zotero.get_item.side_effect = None
        zotero.get_item.return_value = _item(key, version=version)
    elif read_method == "get_search":
        zotero.get_search.return_value = _search(key, version=version)

    result = await tools[tool_name](
        key,
        version,
        True,
        expected_server_id=SERVER_ID,
    )

    assert result["success"] is True
    assert result[result_key] == key
    getattr(zotero, delete_method).assert_awaited_once_with(key, expected_version=version)


@pytest.mark.asyncio
async def test_update_saved_search_uses_exact_version_and_validated_patch(zotero: AsyncMock) -> None:
    tools, _ = _registered_tools(zotero)
    conditions = [{"condition": "title", "operator": "contains", "value": "evidence"}]

    result = await tools["update_saved_search"](
        SEARCH_KEY,
        5,
        name=" Evidence ",
        conditions=conditions,
        confirm=True,
        expected_server_id=SERVER_ID,
    )

    assert result["success"] is True
    zotero.get_search.assert_awaited_once_with(SEARCH_KEY)
    zotero.local_update_search.assert_awaited_once_with(
        SEARCH_KEY,
        {"name": "Evidence", "conditions": conditions},
        expected_version=5,
        replace=False,
    )


@pytest.mark.asyncio
async def test_delete_tags_refreshes_exact_library_cursor(zotero: AsyncMock) -> None:
    tools, _ = _registered_tools(zotero)

    result = await tools["delete_tags"](
        ["reviewed", "reviewed", "needs PDF"],
        23,
        True,
        expected_server_id=SERVER_ID,
    )

    assert result["success"] is True
    zotero.get_library_cursor.assert_awaited_once_with()
    zotero.local_delete_tags.assert_awaited_once_with(
        ["reviewed", "needs PDF"],
        expected_version=23,
    )


@pytest.mark.asyncio
async def test_delete_tags_stale_library_cursor_is_zero_write(zotero: AsyncMock) -> None:
    tools, _ = _registered_tools(zotero)
    zotero.get_library_cursor.return_value = {
        "library_version": 24,
        "server_id": SERVER_ID,
    }

    result = await tools["delete_tags"](
        ["reviewed"],
        23,
        True,
        expected_server_id=SERVER_ID,
    )

    assert result["error"]["code"] == "version_conflict"
    zotero.local_delete_tags.assert_not_awaited()


@pytest.mark.asyncio
async def test_replace_attachment_file_checks_version_md5_and_imported_mode(
    zotero: AsyncMock,
    tmp_path: Path,
) -> None:
    tools, _ = _registered_tools(zotero)
    replacement = tmp_path / "replacement.pdf"
    replacement.write_bytes(b"replacement")
    zotero.get_item.side_effect = None
    zotero.get_item.return_value = _attachment(version=9, md5="a" * 32)

    result = await tools["replace_attachment_file"](
        ATTACHMENT_KEY,
        str(replacement),
        9,
        "A" * 32,
        True,
        expected_server_id=SERVER_ID,
    )

    assert result["success"] is True
    zotero.local_replace_attachment_file.assert_awaited_once_with(
        ATTACHMENT_KEY,
        replacement.resolve(),
        expected_md5="a" * 32,
    )


@pytest.mark.asyncio
async def test_replace_attachment_file_md5_conflict_is_zero_write(
    zotero: AsyncMock,
    tmp_path: Path,
) -> None:
    tools, _ = _registered_tools(zotero)
    replacement = tmp_path / "replacement.pdf"
    replacement.write_bytes(b"replacement")
    zotero.get_item.side_effect = None
    zotero.get_item.return_value = _attachment(version=9, md5="b" * 32)

    result = await tools["replace_attachment_file"](
        ATTACHMENT_KEY,
        str(replacement),
        9,
        "a" * 32,
        True,
        expected_server_id=SERVER_ID,
    )

    assert result["error"]["code"] == "version_conflict"
    zotero.local_replace_attachment_file.assert_not_awaited()


@pytest.mark.asyncio
async def test_set_attachment_fulltexts_validates_all_targets_then_writes_once(zotero: AsyncMock) -> None:
    tools, _ = _registered_tools(zotero)
    zotero.get_item.side_effect = lambda key: _attachment(key)
    entries = [
        {
            "attachment_key": ATTACHMENT_KEY,
            "content": "one",
            "indexed_pages": 1,
            "total_pages": 2,
        },
        {
            "attachment_key": SECOND_ATTACHMENT_KEY,
            "content": "two",
            "indexed_chars": 3,
            "total_chars": 3,
        },
    ]

    result = await tools["set_attachment_fulltexts"](
        entries,
        23,
        True,
        expected_server_id=SERVER_ID,
    )

    assert result["success"] is True
    assert result["updated_count"] == 2
    zotero.get_library_cursor.assert_awaited_once_with()
    zotero.local_set_fulltexts.assert_awaited_once_with(
        [
            {"key": ATTACHMENT_KEY, "content": "one", "indexedPages": 1, "totalPages": 2},
            {"key": SECOND_ATTACHMENT_KEY, "content": "two", "indexedChars": 3, "totalChars": 3},
        ],
        expected_library_version=23,
    )


@pytest.mark.asyncio
async def test_set_attachment_fulltexts_rejects_more_than_ten_without_io(zotero: AsyncMock) -> None:
    tools, _ = _registered_tools(zotero)
    entry = {
        "attachment_key": ATTACHMENT_KEY,
        "content": "text",
        "indexed_chars": 4,
        "total_chars": 4,
    }

    result = await tools["set_attachment_fulltexts"]([entry] * 11, 23, True, expected_server_id=SERVER_ID)

    assert result["error"]["code"] == "invalid_entries"
    zotero.begin_local_operation.assert_not_awaited()
    zotero.local_set_fulltexts.assert_not_awaited()


@pytest.mark.asyncio
async def test_set_attachment_fulltexts_rejects_empty_content_without_io(zotero: AsyncMock) -> None:
    tools, _ = _registered_tools(zotero)

    result = await tools["set_attachment_fulltexts"](
        [
            {
                "attachment_key": ATTACHMENT_KEY,
                "content": "",
                "indexed_chars": 0,
                "total_chars": 0,
            }
        ],
        23,
        True,
        expected_server_id=SERVER_ID,
    )

    assert result["error"]["code"] == "invalid_content"
    zotero.begin_local_operation.assert_not_awaited()
    zotero.local_set_fulltexts.assert_not_awaited()
