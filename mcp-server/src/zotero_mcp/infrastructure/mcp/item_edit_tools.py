"""Version-bound Zotero 10 item editing and schema/annotation discovery."""

from typing import Any

from mcp.server import MCPServer
from mcp.types import ToolAnnotations

from ..zotero_client.client import ZoteroAPIError, ZoteroClient, ZoteroConnectionError
from .read_contracts import same_server_snapshot as _same_server_snapshot
from .local_api_tools import (
    _batch_membership_result,
    _begin_server_operation,
    _confirmation,
    _error,
    _exact_object_error,
    _exact_version_error,
    _normalize_key,
    _normalize_server_id,
    _object_data,
    _safe_fields,
    _valid_version,
    _write_annotations,
    _zotero_error,
)

READ = ToolAnnotations(read_only_hint=True, destructive_hint=False, idempotent_hint=True, open_world_hint=False)


def register_item_edit_tools(mcp: MCPServer[Any], zotero: ZoteroClient) -> None:
    """Register narrow editing tasks; previews never read Zotero or the filesystem."""

    async def apply_edit(
        operation: str,
        item_key: str,
        expected_version: int,
        changes: dict[str, Any],
        confirm: bool,
        expected_server_id: str | None,
    ) -> dict[str, Any]:
        key, error = _normalize_key(operation, item_key, "item_key")
        if error:
            return error
        error = _valid_version(operation, expected_version)
        if error:
            return error
        server_id, error = _normalize_server_id(operation, expected_server_id)
        if error:
            return error
        proposed = dict(item_key=key, expected_version=expected_version, changes=changes, expected_server_id=server_id)
        if not confirm:
            return _confirmation(operation, proposed)
        binding = None
        try:
            binding, error = await _begin_server_operation(operation, zotero, server_id)
            if error:
                return error
            assert key is not None
            item = await zotero.get_item(key)
            error = _exact_object_error(operation, item, key, "item") or _exact_version_error(
                operation, item, expected_version, kind="item"
            )
            if error:
                return error
            data = _object_data(item) or {}
            payload = dict(changes)
            if operation == "update_note" and data.get("itemType") != "note":
                return _error(operation, "invalid_target", "update_note requires an exact note item.")
            if operation == "update_item_creators":
                if data.get("itemType") in {"attachment", "annotation", "note"}:
                    return _error(operation, "invalid_target", "Creators require a bibliographic item.")
                allowed = {row["creatorType"] for row in await zotero.get_creator_types(str(data.get("itemType", "")))}
                if any(c["creatorType"] not in allowed for c in changes["creators"]):
                    return _error(operation, "invalid_creators", "Creator type is not supported for this item type.")
            if operation == "update_item_tags":
                existing = data.get("tags", [])
                if not isinstance(existing, list) or any(not isinstance(t, dict) or not isinstance(t.get("tag"), str) for t in existing):
                    return _error(operation, "invalid_response", "Item tags are malformed.")
                tags = [dict(t) for t in existing if t["tag"] not in changes["remove"]]
                names = {t["tag"] for t in tags}
                tags.extend({"tag": name, "type": 0} for name in changes["add"] if name not in names)
                payload = {"tags": tags}
            response = await zotero.local_update_item(key, payload, expected_version=expected_version, replace=False)
            return {"success": True, "operation": operation, "confirmation_required": False, "item_key": key, "result": response}
        except (ZoteroAPIError, ZoteroConnectionError) as exc:
            return _zotero_error(operation, exc)
        finally:
            if binding is not None:
                zotero.end_local_operation(binding)

    @mcp.tool(annotations=_write_annotations(idempotent=True, destructive=True))
    async def update_item_tags(
        item_key: str,
        expected_version: int,
        add: list[str] | None = None,
        remove: list[str] | None = None,
        confirm: bool = False,
        expected_server_id: str | None = None,
    ) -> dict[str, Any]:
        """Add/remove exact tags on one item, preserving unrelated tags and their manual/automatic type."""
        operation = "update_item_tags"
        if any(
            values is not None and (not isinstance(values, list) or any(not isinstance(v, str) or not v.strip() for v in values))
            for values in (add, remove)
        ):
            return _error(operation, "invalid_tags", "add/remove must be lists of non-empty tag names.")
        added, removed = list(dict.fromkeys(add or [])), list(dict.fromkeys(remove or []))
        if not (added or removed) or set(added) & set(removed) or len(added) + len(removed) > 100:
            return _error(operation, "invalid_tags", "Supply 1–100 disjoint tag additions/removals.")
        return await apply_edit(operation, item_key, expected_version, {"add": added, "remove": removed}, confirm, expected_server_id)

    @mcp.tool(annotations=_write_annotations(idempotent=True, destructive=True))
    async def update_item_creators(
        item_key: str,
        creators: list[dict[str, str]],
        expected_version: int,
        confirm: bool = False,
        expected_server_id: str | None = None,
    ) -> dict[str, Any]:
        """Replace the reviewed ordered creator list; use get_item_schema to discover valid creator types. Empty clears all."""
        operation = "update_item_creators"
        if not isinstance(creators, list) or len(creators) > 1000:
            return _error(operation, "invalid_creators", "creators must be a list of at most 1000 entries.")
        for creator in creators:
            if not isinstance(creator, dict) or set(creator) - {"creatorType", "firstName", "lastName", "name"}:
                return _error(operation, "invalid_creators", "Unsupported creator fields.")
            if any(not isinstance(v, str) for v in creator.values()) or not creator.get("creatorType", "").strip():
                return _error(operation, "invalid_creators", "Creator fields must be strings with a creatorType.")
            if "name" in creator:
                valid = bool(creator["name"].strip()) and not ({"firstName", "lastName"} & set(creator))
            else:
                valid = bool(creator.get("lastName", "").strip())
            if not valid:
                return _error(operation, "invalid_creators", "Use a non-empty name OR lastName with optional firstName.")
        return await apply_edit(operation, item_key, expected_version, {"creators": creators}, confirm, expected_server_id)

    @mcp.tool(annotations=_write_annotations(idempotent=True, destructive=True))
    async def update_note(
        item_key: str,
        note_html: str,
        expected_version: int,
        confirm: bool = False,
        expected_server_id: str | None = None,
    ) -> dict[str, Any]:
        """Replace one exact note's HTML without changing its parent; read get_item first. Empty HTML clears the note."""
        if not isinstance(note_html, str):
            return _error("update_note", "invalid_note", "note_html must be a string.")
        return await apply_edit("update_note", item_key, expected_version, {"note": note_html}, confirm, expected_server_id)

    @mcp.tool(annotations=_write_annotations(idempotent=True, destructive=True))
    async def set_item_trashed(
        item_key: str,
        trashed: bool,
        expected_version: int,
        confirm: bool = False,
        expected_server_id: str | None = None,
    ) -> dict[str, Any]:
        """Move one exact item to Trash (true), or restore it (false). Unlike delete_item, this is recoverable."""
        if not isinstance(trashed, bool):
            return _error("set_item_trashed", "invalid_state", "trashed must be boolean.")
        return await apply_edit("set_item_trashed", item_key, expected_version, {"deleted": int(trashed)}, confirm, expected_server_id)

    @mcp.tool(annotations=_write_annotations(idempotent=True, destructive=True))
    async def batch_update_item_fields(
        updates: list[dict[str, Any]],
        confirm: bool = False,
        expected_server_id: str | None = None,
    ) -> dict[str, Any]:
        """Edit scalar metadata on 1–50 bibliographic items. Each entry requires item_key, expected_version and fields.

        Preview the whole batch. All exact objects/versions are rechecked before one POST;
        Zotero may partially accept that POST, so inspect each returned item status and never replay blindly.
        """
        operation = "batch_update_item_fields"
        if not isinstance(updates, list) or not 1 <= len(updates) <= 50:
            return _error(operation, "invalid_batch", "updates must contain 1–50 entries.")
        normalized, keys = [], []
        for entry in updates:
            if not isinstance(entry, dict) or set(entry) != {"item_key", "expected_version", "fields"}:
                return _error(operation, "invalid_batch", "Each entry needs only item_key, expected_version and fields.")
            key, error = _normalize_key(operation, entry["item_key"], "item_key")
            error = error or _valid_version(operation, entry["expected_version"])
            if error:
                return error
            fields, error = _safe_fields(operation, entry["fields"])
            if error:
                return error
            if key in keys:
                return _error(operation, "duplicate_key", "Each item may appear only once.")
            assert key is not None and fields is not None
            keys.append(key)
            normalized.append({"key": key, "version": entry["expected_version"], **fields})
        server_id, error = _normalize_server_id(operation, expected_server_id)
        if error:
            return error
        if not confirm:
            return _confirmation(operation, {"updates": updates, "expected_server_id": server_id})
        binding = None
        try:
            binding, error = await _begin_server_operation(operation, zotero, server_id)
            if error:
                return error
            for entry in normalized:
                item = await zotero.get_item(entry["key"])
                error = _exact_object_error(operation, item, entry["key"], "item") or _exact_version_error(
                    operation, item, entry["version"], kind="item"
                )
                if error:
                    return error
                if (_object_data(item) or {}).get("itemType") in {"attachment", "annotation", "note"}:
                    return _error(operation, "invalid_target", "Only bibliographic items support scalar batch editing.")
            response = await zotero.local_batch_update_items(normalized)
            result = _batch_membership_result(operation, response, item_keys=keys, collection={}, already_present=set(), updates=normalized)
            result.pop("collection")
            return result
        except (ZoteroAPIError, ZoteroConnectionError) as exc:
            return _zotero_error(operation, exc)
        finally:
            if binding is not None:
                zotero.end_local_operation(binding)

    @mcp.tool(annotations=READ)
    async def get_item_schema(item_type: str) -> dict[str, Any]:
        """Discover fields and ordered creator types supported by this Zotero instance, e.g. journalArticle."""
        try:
            fields, creators, server_id = await zotero.get_item_schema_snapshot(item_type)
            return {"success": True, "item_type": item_type, "fields": fields, "creator_types": creators, "server_id": server_id}
        except (ZoteroAPIError, ZoteroConnectionError, ValueError) as exc:
            return {"success": False, "error": str(exc)}

    @mcp.tool(annotations=READ)
    async def get_item_annotations(attachment_key: str) -> dict[str, Any]:
        """Read all annotation children of one exact attachment, including text/comment/color/page and position."""
        key, error = _normalize_key("get_item_annotations", attachment_key, "attachment_key")
        if error:
            return error
        assert key is not None
        try:
            parent, parent_id = await zotero.get_item_snapshot(key)
            if (
                _exact_object_error("get_item_annotations", parent, key, "attachment")
                or (_object_data(parent) or {}).get("itemType") != "attachment"
            ):
                return _error("get_item_annotations", "invalid_target", "Provide an exact attachment key, not its bibliographic parent.")
            children, child_id = await zotero.get_item_children_snapshot(key)
            server_id = _same_server_snapshot(parent_id, child_id)
            annotations = [
                {**item, "server_id": server_id} for item in children if (_object_data(item) or {}).get("itemType") == "annotation"
            ]
            return {"success": True, "attachment_key": key, "server_id": server_id, "count": len(annotations), "annotations": annotations}
        except (ZoteroAPIError, ZoteroConnectionError) as exc:
            return _zotero_error("get_item_annotations", exc)
