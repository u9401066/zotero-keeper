"""Behavioral regression tests for Zotero 10 editing and result levels."""

from unittest.mock import AsyncMock, MagicMock

import pytest

from zotero_mcp.infrastructure.mcp.item_edit_tools import register_item_edit_tools
from zotero_mcp.infrastructure.mcp.local_api_tools import _normalize_conditions

KEY = "ABCD2345"
OTHER = "BCDE3456"
SERVER = "profile-1"


@pytest.mark.asyncio
async def test_real_sdk_exposes_editing_schemas_and_annotations():
    from mcp.server import MCPServer

    server = MCPServer("editing")
    register_item_edit_tools(server, AsyncMock())
    listed = {t.name: t for t in await server.list_tools()}
    assert len(listed) == 7
    for name, tool in listed.items():
        if name.startswith("get_"):
            assert tool.annotations.read_only_hint
        else:
            assert not tool.annotations.read_only_hint
            assert tool.input_schema["properties"]["confirm"]["default"] is False
            assert "expected_server_id" in tool.input_schema["properties"]


@pytest.mark.parametrize(
    "conditions",
    [
        [{"condition": "title", "operator": "contains", "value": "AI", "required": True}],
        [{"condition": "groupEnd", "operator": "true"}],
        [{"condition": "groupStart", "operator": "true"}],
        [{"condition": "resultLevel", "operator": "unknown"}],
    ],
)
def test_unsupported_or_unbalanced_search_conditions_fail(conditions):
    _, error = _normalize_conditions("test", conditions)
    assert error["error"]["code"] == "invalid_conditions"


@pytest.fixture
def editing():
    client = AsyncMock()
    client.end_local_operation = MagicMock()
    client.get_item.return_value = {
        "key": KEY,
        "version": 7,
        "data": {"itemType": "journalArticle", "tags": [{"tag": "auto", "type": 1}, {"tag": "keep", "type": 0}]},
    }
    client.get_creator_types.return_value = [{"creatorType": "author"}]
    client.local_update_item.return_value = None
    functions = {}
    server = MagicMock()

    def tool(**kwargs):
        def register(fn):
            functions[fn.__name__] = fn
            return fn

        return register

    server.tool = tool
    register_item_edit_tools(server, client)
    return client, functions


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "name,extra",
    [
        ("update_note", {"note_html": "<p>New</p>"}),
        ("update_item_tags", {"add": ["new"], "remove": ["auto"]}),
        ("update_item_creators", {"creators": [{"creatorType": "author", "name": "Group"}]}),
        ("set_item_trashed", {"trashed": True}),
    ],
)
async def test_preview_has_no_io_and_confirm_requires_identity(editing, name, extra):
    client, tools = editing
    args = dict(item_key=KEY, expected_version=7, **extra)
    result = await tools[name](**args)
    assert result["confirmation_required"]
    assert not client.mock_calls
    result = await tools[name](**args, confirm=True)
    assert result["error"]["code"] == "server_identity_required"
    assert not client.mock_calls


@pytest.mark.asyncio
async def test_tags_preserve_unrelated_automatic_tags(editing):
    client, tools = editing
    result = await tools["update_item_tags"](KEY, 7, add=["new"], remove=["keep"], confirm=True, expected_server_id=SERVER)
    assert result["success"]
    client.local_update_item.assert_awaited_once_with(
        KEY, {"tags": [{"tag": "auto", "type": 1}, {"tag": "new", "type": 0}]}, expected_version=7, replace=False
    )
    client.end_local_operation.assert_called_once()


@pytest.mark.asyncio
async def test_conflict_prevents_write_and_releases_binding(editing):
    client, tools = editing
    result = await tools["set_item_trashed"](KEY, True, 6, confirm=True, expected_server_id=SERVER)
    assert result["error"]["code"] == "version_conflict"
    client.local_update_item.assert_not_awaited()
    client.end_local_operation.assert_called_once()


@pytest.mark.asyncio
async def test_note_does_not_patch_a_parent(editing):
    client, tools = editing
    result = await tools["update_note"](KEY, "", 7, confirm=True, expected_server_id=SERVER)
    assert result["error"]["code"] == "invalid_target"
    client.local_update_item.assert_not_awaited()


@pytest.mark.asyncio
async def test_creator_schema_rejects_unsupported_roles(editing):
    client, tools = editing
    result = await tools["update_item_creators"](
        KEY, [{"creatorType": "inventor", "lastName": "Lee"}], 7, confirm=True, expected_server_id=SERVER
    )
    assert result["error"]["code"] == "invalid_creators"
    client.local_update_item.assert_not_awaited()


@pytest.mark.asyncio
async def test_batch_prevalidates_all_versions_before_any_write(editing):
    client, tools = editing
    client.get_item.side_effect = lambda key: {"key": key, "version": 7, "data": {"itemType": "journalArticle"}}
    updates = [
        {"item_key": KEY, "expected_version": 7, "fields": {"title": "one"}},
        {"item_key": OTHER, "expected_version": 6, "fields": {"title": "two"}},
    ]
    result = await tools["batch_update_item_fields"](updates, expected_server_id=SERVER)
    assert result["confirmation_required"] and not client.mock_calls
    result = await tools["batch_update_item_fields"](updates, confirm=True, expected_server_id=SERVER)
    assert result["error"]["code"] == "version_conflict"
    client.local_batch_update_items.assert_not_awaited()


@pytest.mark.asyncio
async def test_batch_reports_partial_and_missing_outcomes(editing):
    client, tools = editing
    client.get_item.side_effect = lambda key: {"key": key, "version": 7, "data": {"itemType": "journalArticle"}}
    client.local_batch_update_items.return_value = {
        "successful": {"0": {"key": KEY, "version": 8}},
        "failed": {"1": {"code": 412, "message": "changed"}},
    }
    updates = [{"item_key": key, "expected_version": 7, "fields": {"title": "new"}} for key in [KEY, OTHER]]
    result = await tools["batch_update_item_fields"](updates, confirm=True, expected_server_id=SERVER)
    assert not result["success"] and result["partial"]
    assert result["failed_count"] == 1
    client.local_batch_update_items.assert_awaited_once()


@pytest.mark.asyncio
async def test_annotations_keep_content_and_identity(editing):
    client, tools = editing
    client.get_item_snapshot.return_value = ({"key": KEY, "data": {"itemType": "attachment"}}, SERVER)
    client.get_item_children_snapshot.return_value = (
        [{"key": OTHER, "version": 4, "data": {"itemType": "annotation", "annotationText": "Evidence", "annotationColor": "#ffff00"}}],
        SERVER,
    )
    result = await tools["get_item_annotations"](KEY)
    assert result["annotations"][0]["data"]["annotationText"] == "Evidence"
    assert result["annotations"][0]["server_id"] == SERVER
    client.get_item_children_snapshot.return_value = ([], "other-profile")
    result = await tools["get_item_annotations"](KEY)
    assert result["error"]["http_status"] == 412


def test_zotero10_nested_conditions_and_mode_wire_format():
    conditions = [
        {"condition": "resultLevel", "operator": "annotation"},
        {"condition": "groupStart", "operator": "true"},
        {"condition": "joinMode", "operator": "any"},
        {"condition": "fulltextContent", "operator": "contains", "value": "test", "mode": "regexp"},
        {"condition": "groupEnd", "operator": "true"},
    ]
    result, error = _normalize_conditions("test", conditions)
    assert error is None
    assert result[3]["condition"] == "fulltextContent/regexp"
    assert "mode" not in result[3]
    assert _normalize_conditions("test", conditions[:-1])[1]
    assert _normalize_conditions("test", [{"condition": "title", "operator": "contains", "value": "x", "required": True}])[1]
