"""Safe Zotero 10+ Local API write tools.

The tools in this module deliberately expose narrow, task-oriented mutations
instead of a generic Local API request or arbitrary item PATCH surface.  Every
library mutation has a fail-closed ``confirm`` gate; Local API authorization is
requested separately through ``authorize_local_writes``.
"""

from __future__ import annotations

import math
import mimetypes
import re
from collections.abc import Mapping
from pathlib import Path
from typing import TYPE_CHECKING, Any

from mcp.server import MCPServer
from mcp.types import ToolAnnotations

from ..zotero_client.client import ZoteroAPIError, ZoteroConnectionError

if TYPE_CHECKING:
    from ..zotero_client.client import ZoteroClient


_ZOTERO_KEY_RE = re.compile(r"[23456789ABCDEFGHIJKLMNPQRSTUVWXYZ]{8}")
_FORBIDDEN_ITEM_FIELDS = {
    "key",
    "version",
    "itemType",
    "collections",
    "tags",
    "creators",
    "relations",
    "parentItem",
    # These fields can change object identity, hierarchy, deletion state, or
    # attachment storage and belong behind dedicated tools.
    "deleted",
    "dateAdded",
    "dateModified",
    "linkMode",
    "filename",
    "contentType",
    "charset",
    "md5",
    "mtime",
    "note",
}
_SEARCH_CONDITION_FIELDS = {"condition", "operator", "value", "required", "mode"}
_CHILD_ITEM_TYPES = {"annotation", "attachment", "note"}


def _write_annotations(
    *,
    idempotent: bool,
    destructive: bool = False,
) -> ToolAnnotations:
    """Return the common closed-world annotations for a safe mutation."""
    return ToolAnnotations(
        read_only_hint=False,
        destructive_hint=destructive,
        idempotent_hint=idempotent,
        open_world_hint=False,
    )


def _error(
    operation: str,
    code: str,
    message: str,
    *,
    http_status: int | None = None,
    retry_after: str | None = None,
    **extra: Any,
) -> dict[str, Any]:
    """Build a stable, machine-readable tool error."""
    error: dict[str, Any] = {
        "code": code,
        "message": message,
        "http_status": http_status,
        "retry_after": retry_after,
    }
    result: dict[str, Any] = {
        "success": False,
        "operation": operation,
        "confirmation_required": False,
        "error": error,
    }
    result.update(extra)
    return result


def _retry_after(exc: BaseException) -> str | None:
    """Read Retry-After from current or future Zotero exception shapes."""
    direct = getattr(exc, "retry_after", None)
    if direct is not None:
        return str(direct)
    for attribute in ("headers", "response_headers"):
        headers = getattr(exc, attribute, None)
        if headers:
            value = headers.get("Retry-After") or headers.get("retry-after")
            if value is not None:
                return str(value)
    return None


def _zotero_error(operation: str, exc: BaseException, **extra: Any) -> dict[str, Any]:
    """Map client exceptions to a stable Local API error code."""
    if isinstance(exc, ZoteroConnectionError):
        return _error(operation, "connection_error", str(exc), **extra)

    raw_status = getattr(exc, "status_code", None)
    status = raw_status if isinstance(raw_status, int) and not isinstance(raw_status, bool) else None
    codes = {
        400: "invalid_request",
        401: "authorization_required",
        403: "authorization_denied",
        404: "not_found",
        409: "library_locked",
        412: "version_conflict",
        413: "file_too_large",
        428: "precondition_required",
        429: "rate_limited",
        501: "unsupported_local_write",
    }
    if status == 412 and "Server-ID changed" in str(exc):
        code = "server_identity_mismatch"
    else:
        code = codes.get(status, "zotero_api_error") if status is not None else "zotero_api_error"
    return _error(
        operation,
        code,
        str(exc),
        http_status=status,
        retry_after=_retry_after(exc),
        **extra,
    )


def _unexpected_error(operation: str, exc: BaseException, **extra: Any) -> dict[str, Any]:
    """Keep unexpected adapter failures structured at the MCP boundary."""
    return _error(operation, "internal_error", str(exc), **extra)


def _attachment_failure_extra(exc: BaseException, **extra: Any) -> dict[str, Any]:
    """Preserve a child attachment key when a later upload phase fails."""
    attachment_key = getattr(exc, "attachment_key", None)
    if isinstance(attachment_key, str) and _valid_key(attachment_key):
        extra["attachment_key"] = attachment_key
        extra["partial"] = True
    return extra


def _confirmation(operation: str, proposed: dict[str, Any]) -> dict[str, Any]:
    """Return a mutation proposal without touching Zotero."""
    return {
        "success": False,
        "operation": operation,
        "confirmation_required": True,
        "proposed": proposed,
        "message": "Review the proposed Zotero change, then call again with confirm=true.",
    }


def _valid_key(value: str) -> bool:
    return isinstance(value, str) and _ZOTERO_KEY_RE.fullmatch(value.strip()) is not None


def _normalize_key(operation: str, value: str, label: str) -> tuple[str | None, dict[str, Any] | None]:
    normalized = value.strip() if isinstance(value, str) else ""
    if not _valid_key(normalized):
        return None, _error(
            operation,
            "invalid_key",
            f"{label} must be an exact 8-character Zotero key.",
        )
    return normalized, None


def _object_key(obj: Any) -> str | None:
    if not isinstance(obj, Mapping):
        return None
    key = obj.get("key")
    if isinstance(key, str):
        return key
    data = obj.get("data")
    if isinstance(data, Mapping) and isinstance(data.get("key"), str):
        return str(data["key"])
    return None


def _object_data(obj: Any) -> Mapping[str, Any] | None:
    if not isinstance(obj, Mapping):
        return None
    data = obj.get("data")
    return data if isinstance(data, Mapping) else obj


def _exact_object_error(operation: str, obj: Any, expected_key: str, kind: str) -> dict[str, Any] | None:
    returned_key = _object_key(obj)
    if returned_key != expected_key:
        return _error(
            operation,
            "invalid_target",
            f"Zotero did not return the exact requested {kind} key '{expected_key}'.",
        )
    return None


def _object_version(obj: Any) -> int | None:
    if isinstance(obj, Mapping):
        value = obj.get("version")
        if isinstance(value, int) and not isinstance(value, bool):
            return value
        data = obj.get("data")
        if isinstance(data, Mapping):
            value = data.get("version")
            if isinstance(value, int) and not isinstance(value, bool):
                return value
    return None


def _created_object(response: Any) -> Any:
    """Extract index zero from either documented batch response spelling."""
    if not isinstance(response, Mapping):
        raise ZoteroAPIError("Zotero Local API returned an invalid creation response")
    for name in ("successful", "success"):
        values = response.get(name)
        if isinstance(values, Mapping):
            if "0" in values:
                return values["0"]
            if 0 in values:
                return values[0]
    failed = response.get("failed")
    if isinstance(failed, Mapping):
        detail = failed.get("0")
        if detail is None:
            detail = failed.get(0)
        if isinstance(detail, Mapping):
            raw_status = detail.get("code")
            status = raw_status if isinstance(raw_status, int) and not isinstance(raw_status, bool) else 0
            message = detail.get("message")
            suffix = f": {message}" if isinstance(message, str) and message else ""
            raise ZoteroAPIError(
                f"Zotero Local API rejected object creation{suffix}",
                status_code=status,
            )
    raise ZoteroAPIError("Zotero Local API returned no created object")


def _is_json_scalar(value: Any) -> bool:
    if isinstance(value, (str, bool, int)) or value is None:
        return value is not None
    return isinstance(value, float) and math.isfinite(value)


def _safe_fields(operation: str, fields: Mapping[str, Any] | Any) -> tuple[dict[str, Any] | None, dict[str, Any] | None]:
    if not isinstance(fields, Mapping) or not fields:
        return None, _error(operation, "invalid_fields", "fields must be a non-empty mapping of scalar metadata values.")

    normalized: dict[str, Any] = {}
    for raw_name, value in fields.items():
        if not isinstance(raw_name, str) or not raw_name.strip():
            return None, _error(operation, "invalid_fields", "Every metadata field name must be a non-empty string.")
        name = raw_name.strip()
        if name in _FORBIDDEN_ITEM_FIELDS:
            return None, _error(operation, "forbidden_field", f"Field '{name}' requires a dedicated safe tool.")
        if not _is_json_scalar(value):
            return None, _error(operation, "invalid_fields", f"Field '{name}' must contain a finite JSON scalar value.")
        normalized[name] = value
    return normalized, None


def _valid_version(
    operation: str,
    expected_version: int,
    *,
    label: str = "expected_version",
) -> dict[str, Any] | None:
    if isinstance(expected_version, bool) or not isinstance(expected_version, int) or expected_version < 0:
        return _error(operation, "invalid_version", f"{label} must be a non-negative integer.")
    return None


def _normalize_server_id(
    operation: str,
    expected_server_id: str | None,
) -> tuple[str | None, dict[str, Any] | None]:
    if expected_server_id is None:
        return None, None
    normalized = expected_server_id.strip() if isinstance(expected_server_id, str) else ""
    if not normalized:
        return None, _error(
            operation,
            "invalid_server_identity",
            "expected_server_id must be a non-empty Zotero-Server-ID.",
        )
    return normalized, None


async def _begin_server_operation(
    operation: str,
    zotero: "ZoteroClient",
    expected_server_id: str | None,
) -> tuple[Any | None, dict[str, Any] | None]:
    """Start one task-local mutation binding for the reviewed database."""
    if expected_server_id is None:
        return (
            None,
            _error(
                operation,
                "server_identity_required",
                "Read or authorize Zotero first and pass its server_id as expected_server_id.",
            ),
        )
    try:
        binding = await zotero.begin_local_operation(expected_server_id)
    except ZoteroAPIError as exc:
        if exc.status_code == 412:
            return (
                None,
                _error(
                    operation,
                    "server_identity_mismatch",
                    str(exc),
                    http_status=412,
                    expected_server_id=expected_server_id,
                    actual_server_id=getattr(exc, "server_id", None),
                ),
            )
        return None, _zotero_error(operation, exc)
    except ZoteroConnectionError as exc:
        return None, _zotero_error(operation, exc)
    return binding, None


def _normalize_conditions(
    operation: str, conditions: list[dict[str, Any]] | Any
) -> tuple[list[dict[str, Any]] | None, dict[str, Any] | None]:
    if not isinstance(conditions, list) or not conditions:
        return None, _error(operation, "invalid_conditions", "conditions must be a non-empty list.")
    normalized: list[dict[str, Any]] = []
    for index, raw in enumerate(conditions):
        if not isinstance(raw, Mapping):
            return None, _error(operation, "invalid_conditions", f"Condition {index} must be an object.")
        unknown = set(raw) - _SEARCH_CONDITION_FIELDS
        if unknown:
            return None, _error(operation, "invalid_conditions", f"Condition {index} has unsupported fields: {sorted(unknown)}")
        condition = raw.get("condition")
        operator = raw.get("operator")
        value = raw.get("value")
        if not isinstance(condition, str) or not condition.strip():
            return None, _error(operation, "invalid_conditions", f"Condition {index} needs a non-empty condition name.")
        if not isinstance(operator, str) or not operator.strip():
            return None, _error(operation, "invalid_conditions", f"Condition {index} needs a non-empty operator.")
        if not _is_json_scalar(value):
            return None, _error(operation, "invalid_conditions", f"Condition {index} value must be a JSON scalar.")
        entry: dict[str, Any] = {
            "condition": condition.strip(),
            "operator": operator.strip(),
            "value": value,
        }
        if "required" in raw:
            if not isinstance(raw["required"], bool):
                return None, _error(operation, "invalid_conditions", f"Condition {index} required must be boolean.")
            entry["required"] = raw["required"]
        if "mode" in raw:
            if not isinstance(raw["mode"], str):
                return None, _error(operation, "invalid_conditions", f"Condition {index} mode must be a string.")
            entry["mode"] = raw["mode"]
        normalized.append(entry)
    return normalized, None


def _batch_index(mapping: Mapping[Any, Any], index: int) -> Any:
    if str(index) in mapping:
        return mapping[str(index)]
    return mapping.get(index)


def _batch_membership_result(
    operation: str,
    response: Any,
    *,
    item_keys: list[str],
    collection: dict[str, Any],
    already_present: set[str],
    updates: list[dict[str, Any]],
) -> dict[str, Any]:
    """Normalize Zotero's per-index batch response into per-item statuses."""
    statuses: dict[str, dict[str, Any]] = {key: {"key": key, "status": "unchanged"} for key in item_keys if key in already_present}
    successful: Mapping[Any, Any] = {}
    unchanged: Mapping[Any, Any] = {}
    failed: Mapping[Any, Any] = {}
    all_succeeded = False

    if isinstance(response, Mapping):
        successful_value = response.get("successful")
        if not isinstance(successful_value, Mapping):
            successful_value = response.get("success")
        if isinstance(successful_value, Mapping):
            successful = successful_value
        elif successful_value is True or response.get("success") is True:
            all_succeeded = True
        if isinstance(response.get("unchanged"), Mapping):
            unchanged = response["unchanged"]
        if isinstance(response.get("failed"), Mapping):
            failed = response["failed"]

    for index, update in enumerate(updates):
        key = str(update["key"])
        successful_value = _batch_index(successful, index)
        unchanged_value = _batch_index(unchanged, index)
        failed_value = _batch_index(failed, index)
        if all_succeeded or successful_value is not None:
            status: dict[str, Any] = {"key": key, "status": "updated"}
            if isinstance(successful_value, Mapping):
                version = _object_version(successful_value)
                if version is not None:
                    status["version"] = version
            statuses[key] = status
        elif unchanged_value is not None:
            statuses[key] = {"key": key, "status": "unchanged"}
        elif failed_value is not None:
            detail = failed_value if isinstance(failed_value, Mapping) else {"message": str(failed_value)}
            statuses[key] = {
                "key": key,
                "status": "failed",
                "error": {
                    "code": detail.get("code", "zotero_api_error"),
                    "message": detail.get("message", "Zotero rejected this item update."),
                },
            }
        else:
            statuses[key] = {
                "key": key,
                "status": "failed",
                "error": {
                    "code": "invalid_response",
                    "message": "Zotero omitted this item from the batch result.",
                },
            }

    ordered = [statuses[key] for key in item_keys]
    updated_count = sum(item["status"] == "updated" for item in ordered)
    unchanged_count = sum(item["status"] == "unchanged" for item in ordered)
    failed_count = sum(item["status"] == "failed" for item in ordered)
    return {
        "success": failed_count == 0,
        "operation": operation,
        "confirmation_required": False,
        "partial": failed_count > 0 and (updated_count + unchanged_count) > 0,
        "requested_count": len(item_keys),
        "changed_count": updated_count,
        "unchanged_count": unchanged_count,
        "failed_count": failed_count,
        "collection": collection,
        "items": ordered,
    }


def register_local_api_tools(mcp: MCPServer[Any], zotero: "ZoteroClient") -> None:
    """Register narrow, confirmed Zotero 10+ Local API write tools."""

    @mcp.tool(annotations=_write_annotations(idempotent=False))
    async def authorize_local_writes(
        require_remembered: bool = False,
    ) -> dict[str, Any]:
        """Request Zotero's runtime approval for Local API writes.

        Set ``require_remembered=true`` before a three-phase attachment upload;
        Zotero must grant ``Always Allow`` so one authorization remains valid
        across all upload phases. The key itself never crosses the MCP boundary.
        """
        operation = "authorize_local_writes"
        try:
            response = await zotero.authorize_local_writes(
                require_remembered=require_remembered,
            )
            if isinstance(response, Mapping) and response.get("denied") is True:
                return _error(operation, "authorization_denied", "The user denied Zotero Local API write access.", http_status=403)
            remembered = False
            server_id: str | None = None
            if isinstance(response, Mapping):
                remembered = bool(response.get("remember", response.get("remembered", False)))
                raw_server_id = response.get("server_id")
                if isinstance(raw_server_id, str):
                    server_id = raw_server_id
            # Never return the Local API key from the MCP boundary.
            return {
                "success": True,
                "operation": operation,
                "authorized": True,
                "remembered": remembered,
                "remembered_required": require_remembered,
                "server_id": server_id,
            }
        except ZoteroAPIError as exc:
            if exc.status_code == 412:
                return _error(
                    operation,
                    "server_identity_mismatch",
                    "Zotero switched databases. Rediscover the Local API and reread all keys/versions before confirming.",
                    http_status=412,
                    actual_server_id=getattr(exc, "server_id", None),
                )
            return _zotero_error(operation, exc)
        except ZoteroConnectionError as exc:
            return _zotero_error(operation, exc)
        except Exception as exc:
            return _unexpected_error(operation, exc)

    @mcp.tool(annotations=_write_annotations(idempotent=False))
    async def create_collection(
        name: str,
        parent_collection_key: str | None = None,
        confirm: bool = False,
        expected_server_id: str | None = None,
    ) -> dict[str, Any]:
        """Create a top-level or nested Zotero collection after explicit confirmation."""
        operation = "create_collection"
        normalized_name = name.strip() if isinstance(name, str) else ""
        if not normalized_name:
            return _error(operation, "invalid_name", "Collection name must not be empty.")
        parent_key: str | None = None
        if parent_collection_key is not None:
            parent_key, key_error = _normalize_key(operation, parent_collection_key, "parent_collection_key")
            if key_error:
                return key_error

        server_id, server_id_error = _normalize_server_id(operation, expected_server_id)
        if server_id_error:
            return server_id_error

        proposed = {
            "name": normalized_name,
            "parent_collection_key": parent_key,
            "expected_server_id": server_id,
        }
        if not confirm:
            return _confirmation(operation, proposed)

        binding = None
        try:
            binding, identity_error = await _begin_server_operation(operation, zotero, server_id)
            if identity_error:
                return identity_error
            if parent_key:
                parent = await zotero.get_collection(parent_key)
                exact_error = _exact_object_error(operation, parent, parent_key, "parent collection")
                if exact_error:
                    return exact_error
            payload: dict[str, Any] = {"name": normalized_name}
            if parent_key:
                payload["parentCollection"] = parent_key
            response = await zotero.local_create_collection(payload)
            return {
                "success": True,
                "operation": operation,
                "confirmation_required": False,
                "collection": _created_object(response),
            }
        except (ZoteroAPIError, ZoteroConnectionError) as exc:
            return _zotero_error(operation, exc)
        except Exception as exc:
            return _unexpected_error(operation, exc)
        finally:
            if binding is not None:
                zotero.end_local_operation(binding)

    @mcp.tool(annotations=_write_annotations(idempotent=True))
    async def add_items_to_collection(
        item_keys: list[str],
        collection_key: str,
        confirm: bool = False,
        expected_server_id: str | None = None,
    ) -> dict[str, Any]:
        """Add up to 50 exact items to a collection while preserving all memberships."""
        operation = "add_items_to_collection"
        target_key, key_error = _normalize_key(operation, collection_key, "collection_key")
        if key_error:
            return key_error
        if not isinstance(item_keys, list) or not item_keys:
            return _error(operation, "invalid_items", "item_keys must contain between 1 and 50 exact Zotero keys.")
        normalized_items: list[str] = []
        seen: set[str] = set()
        for raw_key in item_keys:
            key, item_error = _normalize_key(operation, raw_key, "item key")
            if item_error:
                return item_error
            assert key is not None
            if key not in seen:
                seen.add(key)
                normalized_items.append(key)
        if len(normalized_items) > 50:
            return _error(operation, "batch_too_large", "At most 50 distinct items can be updated in one batch.")

        server_id, server_id_error = _normalize_server_id(operation, expected_server_id)
        if server_id_error:
            return server_id_error

        proposed = {
            "item_keys": normalized_items,
            "collection_key": target_key,
            "expected_server_id": server_id,
        }
        if not confirm:
            return _confirmation(operation, proposed)

        assert target_key is not None
        binding = None
        try:
            binding, identity_error = await _begin_server_operation(operation, zotero, server_id)
            if identity_error:
                return identity_error
            collection_obj = await zotero.get_collection(target_key)
            exact_error = _exact_object_error(operation, collection_obj, target_key, "collection")
            if exact_error:
                return exact_error
            collection_data = _object_data(collection_obj)
            collection_name = collection_data.get("name", target_key) if collection_data else target_key
            collection = {"key": target_key, "name": collection_name}

            # Finish every exact read and payload validation before the sole
            # batch write boundary below.
            read_items: list[tuple[str, Any]] = []
            for item_key in normalized_items:
                item = await zotero.get_item(item_key)
                exact_error = _exact_object_error(operation, item, item_key, "item")
                if exact_error:
                    return exact_error
                read_items.append((item_key, item))

            updates: list[dict[str, Any]] = []
            already_present: set[str] = set()
            for item_key, item in read_items:
                data = _object_data(item)
                version = _object_version(item)
                if data is None or version is None:
                    return _error(operation, "invalid_response", f"Item '{item_key}' has no editable data/version.")
                memberships = data.get("collections", [])
                if not isinstance(memberships, list) or not all(isinstance(value, str) for value in memberships):
                    return _error(operation, "invalid_response", f"Item '{item_key}' returned malformed collection memberships.")
                if target_key in memberships:
                    already_present.add(item_key)
                    continue
                updates.append(
                    {
                        "key": item_key,
                        "version": version,
                        "collections": [*memberships, target_key],
                    }
                )

            if not updates:
                return _batch_membership_result(
                    operation,
                    {"success": True},
                    item_keys=normalized_items,
                    collection=collection,
                    already_present=already_present,
                    updates=[],
                )

            try:
                response = await zotero.local_batch_update_items(updates)
            except (ZoteroAPIError, ZoteroConnectionError) as exc:
                failed_code = _zotero_error(operation, exc)["error"]["code"]
                statuses = [
                    {"key": key, "status": "unchanged"}
                    if key in already_present
                    else {
                        "key": key,
                        "status": "failed",
                        "error": {"code": failed_code, "message": str(exc)},
                    }
                    for key in normalized_items
                ]
                return _zotero_error(
                    operation,
                    exc,
                    partial=bool(already_present),
                    requested_count=len(normalized_items),
                    changed_count=0,
                    unchanged_count=len(already_present),
                    failed_count=len(updates),
                    collection=collection,
                    items=statuses,
                )

            return _batch_membership_result(
                operation,
                response,
                item_keys=normalized_items,
                collection=collection,
                already_present=already_present,
                updates=updates,
            )
        except (ZoteroAPIError, ZoteroConnectionError) as exc:
            return _zotero_error(operation, exc)
        except Exception as exc:
            return _unexpected_error(operation, exc)
        finally:
            if binding is not None:
                zotero.end_local_operation(binding)

    @mcp.tool(annotations=_write_annotations(idempotent=True, destructive=True))
    async def update_item_fields(
        item_key: str,
        fields: dict[str, Any],
        expected_version: int,
        confirm: bool = False,
        expected_server_id: str | None = None,
    ) -> dict[str, Any]:
        """Update safe scalar metadata fields on one exact bibliographic item."""
        operation = "update_item_fields"
        key, key_error = _normalize_key(operation, item_key, "item_key")
        if key_error:
            return key_error
        version_error = _valid_version(operation, expected_version)
        if version_error:
            return version_error
        normalized_fields, fields_error = _safe_fields(operation, fields)
        if fields_error:
            return fields_error
        server_id, server_id_error = _normalize_server_id(operation, expected_server_id)
        if server_id_error:
            return server_id_error
        assert key is not None and normalized_fields is not None
        proposed = {
            "item_key": key,
            "fields": normalized_fields,
            "expected_version": expected_version,
            "expected_server_id": server_id,
        }
        if not confirm:
            return _confirmation(operation, proposed)

        binding = None
        try:
            binding, identity_error = await _begin_server_operation(operation, zotero, server_id)
            if identity_error:
                return identity_error
            item = await zotero.get_item(key)
            exact_error = _exact_object_error(operation, item, key, "item")
            if exact_error:
                return exact_error
            data = _object_data(item)
            if data and data.get("itemType") in _CHILD_ITEM_TYPES:
                return _error(operation, "invalid_target", "update_item_fields only accepts bibliographic parent items.")
            current_version = _object_version(item)
            if current_version is None:
                return _error(operation, "invalid_response", "Zotero did not return the item's current version.")
            if current_version != expected_version:
                return _error(
                    operation,
                    "version_conflict",
                    f"Expected item version {expected_version}, but Zotero returned {current_version}.",
                    http_status=412,
                )
            response = await zotero.local_update_item(
                key,
                normalized_fields,
                expected_version=expected_version,
                replace=False,
            )
            return {
                "success": True,
                "operation": operation,
                "confirmation_required": False,
                "item_key": key,
                "updated_fields": sorted(normalized_fields),
                "result": response,
            }
        except (ZoteroAPIError, ZoteroConnectionError) as exc:
            return _zotero_error(operation, exc, item_key=key)
        except Exception as exc:
            return _unexpected_error(operation, exc, item_key=key)
        finally:
            if binding is not None:
                zotero.end_local_operation(binding)

    @mcp.tool(annotations=_write_annotations(idempotent=False))
    async def create_note(
        parent_item_key: str,
        note_html: str,
        confirm: bool = False,
        expected_server_id: str | None = None,
    ) -> dict[str, Any]:
        """Create one child note beneath an exact bibliographic item."""
        operation = "create_note"
        parent_key, key_error = _normalize_key(operation, parent_item_key, "parent_item_key")
        if key_error:
            return key_error
        normalized_note = note_html.strip() if isinstance(note_html, str) else ""
        if not normalized_note:
            return _error(operation, "invalid_note", "note_html must not be empty.")
        server_id, server_id_error = _normalize_server_id(operation, expected_server_id)
        if server_id_error:
            return server_id_error
        assert parent_key is not None
        proposed = {
            "parent_item_key": parent_key,
            "note_html": normalized_note,
            "expected_server_id": server_id,
        }
        if not confirm:
            return _confirmation(operation, proposed)

        binding = None
        try:
            binding, identity_error = await _begin_server_operation(operation, zotero, server_id)
            if identity_error:
                return identity_error
            parent = await zotero.get_item(parent_key)
            exact_error = _exact_object_error(operation, parent, parent_key, "parent item")
            if exact_error:
                return exact_error
            parent_data = _object_data(parent)
            if parent_data and parent_data.get("itemType") in _CHILD_ITEM_TYPES:
                return _error(operation, "invalid_target", "Notes can only be created beneath a bibliographic parent item.")
            response = await zotero.local_create_item({"itemType": "note", "parentItem": parent_key, "note": normalized_note})
            return {
                "success": True,
                "operation": operation,
                "confirmation_required": False,
                "parent_item_key": parent_key,
                "note": _created_object(response),
            }
        except (ZoteroAPIError, ZoteroConnectionError) as exc:
            return _zotero_error(operation, exc, parent_item_key=parent_key)
        except Exception as exc:
            return _unexpected_error(operation, exc, parent_item_key=parent_key)
        finally:
            if binding is not None:
                zotero.end_local_operation(binding)

    @mcp.tool(annotations=_write_annotations(idempotent=False))
    async def create_saved_search(
        name: str,
        conditions: list[dict[str, Any]],
        confirm: bool = False,
        expected_server_id: str | None = None,
    ) -> dict[str, Any]:
        """Create a Zotero saved search from validated conditions."""
        operation = "create_saved_search"
        normalized_name = name.strip() if isinstance(name, str) else ""
        if not normalized_name:
            return _error(operation, "invalid_name", "Saved-search name must not be empty.")
        normalized_conditions, conditions_error = _normalize_conditions(operation, conditions)
        if conditions_error:
            return conditions_error
        server_id, server_id_error = _normalize_server_id(operation, expected_server_id)
        if server_id_error:
            return server_id_error
        assert normalized_conditions is not None
        payload = {"name": normalized_name, "conditions": normalized_conditions}
        proposed = {**payload, "expected_server_id": server_id}
        if not confirm:
            return _confirmation(operation, proposed)
        binding = None
        try:
            binding, identity_error = await _begin_server_operation(operation, zotero, server_id)
            if identity_error:
                return identity_error
            response = await zotero.local_create_search(payload)
            return {
                "success": True,
                "operation": operation,
                "confirmation_required": False,
                "saved_search": _created_object(response),
            }
        except (ZoteroAPIError, ZoteroConnectionError) as exc:
            return _zotero_error(operation, exc)
        except Exception as exc:
            return _unexpected_error(operation, exc)
        finally:
            if binding is not None:
                zotero.end_local_operation(binding)

    @mcp.tool(annotations=_write_annotations(idempotent=False))
    async def attach_file_to_item(
        item_key: str,
        file_path: str,
        title: str = "Full Text PDF",
        confirm: bool = False,
        expected_server_id: str | None = None,
    ) -> dict[str, Any]:
        """Upload a local stored file beneath an exact existing Zotero item."""
        operation = "attach_file_to_item"
        key, key_error = _normalize_key(operation, item_key, "item_key")
        if key_error:
            return key_error
        raw_path = file_path.strip() if isinstance(file_path, str) else ""
        normalized_title = title.strip() if isinstance(title, str) else ""
        if not raw_path:
            return _error(operation, "invalid_file", "file_path must not be empty.")
        if not normalized_title:
            return _error(operation, "invalid_title", "Attachment title must not be empty.")
        server_id, server_id_error = _normalize_server_id(operation, expected_server_id)
        if server_id_error:
            return server_id_error
        assert key is not None
        proposed = {
            "item_key": key,
            "file_path": raw_path,
            "title": normalized_title,
            "expected_server_id": server_id,
        }
        if not confirm:
            return _confirmation(operation, proposed)

        path = Path(raw_path).expanduser()
        if not path.exists() or not path.is_file():
            return _error(operation, "file_not_found", f"Local file does not exist: {raw_path}")
        resolved = path.resolve()
        content_type = mimetypes.guess_type(resolved.name)[0] or "application/octet-stream"
        binding = None
        try:
            binding, identity_error = await _begin_server_operation(operation, zotero, server_id)
            if identity_error:
                return identity_error
            parent = await zotero.get_item(key)
            exact_error = _exact_object_error(operation, parent, key, "parent item")
            if exact_error:
                return exact_error
            parent_data = _object_data(parent)
            if parent_data and parent_data.get("itemType") in _CHILD_ITEM_TYPES:
                return _error(operation, "invalid_target", "Files can only be attached beneath a bibliographic parent item.")
            response = await zotero.local_attach_file(
                key,
                resolved,
                title=normalized_title,
                content_type=content_type,
                # A local filesystem URI is not bibliographic provenance and
                # must not be persisted into Zotero's public ``url`` field.
                source_url="",
            )
            return {
                "success": True,
                "operation": operation,
                "confirmation_required": False,
                "item_key": key,
                "file_path": str(resolved),
                "attachment": response,
            }
        except (ZoteroAPIError, ZoteroConnectionError) as exc:
            return _zotero_error(
                operation,
                exc,
                **_attachment_failure_extra(exc, item_key=key, file_path=str(resolved)),
            )
        except Exception as exc:
            return _unexpected_error(
                operation,
                exc,
                **_attachment_failure_extra(exc, item_key=key, file_path=str(resolved)),
            )
        finally:
            if binding is not None:
                zotero.end_local_operation(binding)

    @mcp.tool(annotations=_write_annotations(idempotent=True, destructive=True))
    async def set_attachment_fulltext(
        attachment_key: str,
        content: str,
        expected_library_version: int,
        indexed_pages: int | None = None,
        total_pages: int | None = None,
        indexed_chars: int | None = None,
        total_chars: int | None = None,
        confirm: bool = False,
        expected_server_id: str | None = None,
    ) -> dict[str, Any]:
        """Set indexed full text using one Server-ID-bound library cursor."""
        operation = "set_attachment_fulltext"
        key, key_error = _normalize_key(operation, attachment_key, "attachment_key")
        if key_error:
            return key_error
        version_error = _valid_version(
            operation,
            expected_library_version,
            label="expected_library_version",
        )
        if version_error:
            return version_error
        normalized_content = content if isinstance(content, str) else ""
        if not normalized_content:
            return _error(operation, "invalid_content", "content must not be empty.")

        page_values = (indexed_pages, total_pages)
        char_values = (indexed_chars, total_chars)
        has_pages = any(value is not None for value in page_values)
        has_chars = any(value is not None for value in char_values)
        if has_pages == has_chars:
            return _error(operation, "invalid_index_counts", "Provide exactly one complete pages pair or chars pair.")
        selected = page_values if has_pages else char_values
        if any(isinstance(value, bool) or not isinstance(value, int) or value < 0 for value in selected):
            return _error(operation, "invalid_index_counts", "Index counts must be non-negative integers supplied as a complete pair.")
        assert selected[0] is not None and selected[1] is not None
        if selected[0] > selected[1]:
            return _error(operation, "invalid_index_counts", "The indexed count cannot exceed the total count.")

        fulltext: dict[str, Any] = {"content": normalized_content}
        if has_pages:
            fulltext.update({"indexedPages": indexed_pages, "totalPages": total_pages})
        else:
            fulltext.update({"indexedChars": indexed_chars, "totalChars": total_chars})
        server_id, server_id_error = _normalize_server_id(operation, expected_server_id)
        if server_id_error:
            return server_id_error
        assert key is not None
        proposed = {
            "attachment_key": key,
            "expected_library_version": expected_library_version,
            "expected_server_id": server_id,
            "fulltext": fulltext,
        }
        if not confirm:
            return _confirmation(operation, proposed)

        binding = None
        try:
            binding, identity_error = await _begin_server_operation(operation, zotero, server_id)
            if identity_error:
                return identity_error
            cursor = await zotero.get_item_library_cursor(key)
            cursor_server_id = cursor.get("server_id") if isinstance(cursor, Mapping) else None
            current_library_version = cursor.get("library_version") if isinstance(cursor, Mapping) else None
            if cursor_server_id != server_id:
                return _error(
                    operation,
                    "server_identity_mismatch",
                    "Zotero Server-ID changed while refreshing the full-text library cursor.",
                    http_status=412,
                    expected_server_id=server_id,
                    actual_server_id=cursor_server_id,
                )
            if isinstance(current_library_version, bool) or not isinstance(current_library_version, int) or current_library_version < 0:
                return _error(
                    operation,
                    "invalid_response",
                    "Zotero did not return a valid current library version.",
                    attachment_key=key,
                )
            if current_library_version != expected_library_version:
                return _error(
                    operation,
                    "version_conflict",
                    (f"Expected library version {expected_library_version}, but Zotero returned {current_library_version}."),
                    http_status=412,
                    attachment_key=key,
                    expected_library_version=expected_library_version,
                    actual_library_version=current_library_version,
                )
            attachment = await zotero.get_item(key)
            exact_error = _exact_object_error(operation, attachment, key, "attachment")
            if exact_error:
                return exact_error
            data = _object_data(attachment)
            if data is None or data.get("itemType") != "attachment":
                return _error(operation, "invalid_target", "Full text can only be set on an attachment item.")
            response = await zotero.local_set_fulltext(
                key,
                fulltext,
                expected_library_version=expected_library_version,
            )
            return {
                "success": True,
                "operation": operation,
                "confirmation_required": False,
                "attachment_key": key,
                "result": response,
            }
        except (ZoteroAPIError, ZoteroConnectionError) as exc:
            return _zotero_error(
                operation,
                exc,
                attachment_key=key,
                expected_library_version=expected_library_version,
            )
        except Exception as exc:
            return _unexpected_error(operation, exc, attachment_key=key)
        finally:
            if binding is not None:
                zotero.end_local_operation(binding)


__all__ = ["register_local_api_tools"]
