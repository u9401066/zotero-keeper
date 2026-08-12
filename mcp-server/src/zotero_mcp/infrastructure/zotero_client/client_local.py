"""Security-sensitive Zotero 10+ Local API operations.

This mixin is intentionally separate from :mod:`client_write`, which preserves
the existing Connector API compatibility path. Local API credentials and
server identity are kept only on the client instance and are never returned to
callers.
"""

import asyncio
import hashlib
import json
import mimetypes
import re
import secrets
from collections.abc import AsyncIterator, Mapping
from ipaddress import ip_address
from pathlib import Path
from typing import Any

import httpx

from .client_base import LocalOperationBinding, ZoteroAPIError, ZoteroConnectionError

_OBJECT_KEY_RE = re.compile(r"^[23456789ABCDEFGHIJKLMNPQRSTUVWXYZ]{8}$")
_MAX_BATCH_SIZE = 50
_MAX_LOCAL_FILE_SIZE = 4 * 1024**3
_FILE_CHUNK_SIZE = 1024 * 1024


class ZoteroLocalMixin:
    """Mixin implementing the authorized Zotero 10+ Local API contract."""

    _local_api_version: str | None
    _local_schema_version: str | None
    _local_server_id: str | None
    _local_api_key: str | None
    _local_api_key_server_id: str | None
    _local_api_key_remembered: bool
    _local_write_lock: asyncio.Lock
    _local_operation_lock: asyncio.Lock

    def _require_local_loopback(self) -> None:
        if not self.config.is_loopback:
            raise ZoteroConnectionError(
                "Zotero Local API operations require a literal loopback host "
                "(localhost, 127.0.0.0/8, or ::1); remote/forwarded endpoints are refused"
            )

    @staticmethod
    def _validate_object_key(key: Any, *, label: str) -> str:
        if not isinstance(key, str) or not _OBJECT_KEY_RE.fullmatch(key):
            raise ValueError(f"{label} must be an 8-character Zotero object key")
        return key

    @staticmethod
    def _validate_expected_version(expected_version: Any) -> int:
        if isinstance(expected_version, bool) or not isinstance(expected_version, int) or expected_version < 0:
            raise ValueError("expected_version must be a non-negative integer")
        return expected_version

    @staticmethod
    def _parse_json_response(response: httpx.Response, *, operation: str) -> Any:
        if not response.text:
            return None
        try:
            return response.json()
        except (json.JSONDecodeError, ValueError) as exc:
            raise ZoteroAPIError(
                f"Zotero Local API returned invalid JSON for {operation}",
                status_code=response.status_code,
                response_text=response.text,
                response_headers=response.headers,
            ) from exc

    def clear_local_authorization(self) -> None:
        """Forget the in-memory Local API key without changing Zotero settings."""
        self._local_api_key = None
        self._local_api_key_server_id = None
        self._local_api_key_remembered = False

    async def discover_local_api(self) -> dict[str, str | None]:
        """Discover and bind to a Zotero 10+ Local API instance via ``GET /api/``."""
        self._require_local_loopback()
        response = await self._request_raw("GET", "/api/")

        api_version = self._header_value(response.headers, "Zotero-API-Version")
        schema_version = self._header_value(response.headers, "Zotero-Schema-Version")
        server_id = self._header_value(response.headers, "Zotero-Server-ID")

        if api_version != "3":
            raise ZoteroAPIError(
                "Zotero Local API version 3 is required",
                # Normalize a successful discovery of an older, incompatible
                # local contract into the public unsupported-operation code.
                status_code=501,
                response_text=response.text,
                response_headers=response.headers,
            )
        if not server_id:
            raise ZoteroAPIError(
                "Zotero 10+ Local API did not provide Zotero-Server-ID",
                # API v3 reads without a Server-ID identify the supported
                # Zotero 7-9 compatibility path, not a usable write surface.
                status_code=501,
                response_text=response.text,
                response_headers=response.headers,
            )

        if self._local_server_id is not None and self._local_server_id != server_id:
            self.clear_local_authorization()

        self._local_api_version = api_version
        self._local_schema_version = schema_version
        self._local_server_id = server_id
        return {
            "api_version": api_version,
            "schema_version": schema_version,
            "server_id": server_id,
        }

    async def _ensure_local_discovery(self) -> None:
        self._require_local_loopback()
        if self._local_api_version != "3" or not self._local_server_id:
            await self.discover_local_api()

    async def verify_local_server(self, expected_server_id: str) -> dict[str, str | None]:
        """Freshly bind a confirmed mutation to one exact Zotero instance.

        Local object and library versions cannot be reused across Zotero
        databases.  Mutation tools call this immediately after their explicit
        confirmation gate; discovery is intentionally repeated and never
        retried so a profile/database switch fails closed before mutation.
        """
        if not isinstance(expected_server_id, str) or not expected_server_id.strip():
            raise ValueError("expected_server_id must be a non-empty string")
        expected = expected_server_id.strip()
        identity = await self.discover_local_api()
        actual = identity.get("server_id")
        if actual != expected:
            raise ZoteroAPIError(
                "Zotero Server-ID changed after the operation was reviewed",
                status_code=412,
                response_headers={"Zotero-Server-ID": str(actual or "")},
            )
        return identity

    async def begin_local_operation(self, expected_server_id: str) -> LocalOperationBinding:
        """Pin one confirmed mutation to an immutable identity/key snapshot.

        MCP tools may run concurrently on one client.  Serializing complete
        confirmed mutations and using task-local request headers prevents a
        database switch or concurrent authorization from lending one flow a
        different Zotero key after its proposal was approved.
        """
        if not isinstance(expected_server_id, str) or not expected_server_id.strip():
            raise ValueError("expected_server_id must be a non-empty string")
        expected = expected_server_id.strip()

        await self._local_operation_lock.acquire()
        try:
            async with self._local_write_lock:
                identity = await self.discover_local_api()
                actual = identity.get("server_id")
                if actual != expected:
                    raise ZoteroAPIError(
                        "Zotero Server-ID changed after the operation was reviewed",
                        status_code=412,
                        response_headers={"Zotero-Server-ID": str(actual or "")},
                    )
                if self._local_api_key is None or self._local_api_key_server_id != expected:
                    raise ZoteroAPIError(
                        "Zotero Local API write authorization is required for this Server-ID",
                        status_code=401,
                    )

                server_token = self._operation_server_id.set(expected)
                key_token = self._operation_api_key.set(self._local_api_key)
                remembered_token = self._operation_key_remembered.set(self._local_api_key_remembered)
                return LocalOperationBinding(
                    server_token=server_token,
                    key_token=key_token,
                    remembered_token=remembered_token,
                )
        except BaseException:
            self._local_operation_lock.release()
            raise

    def end_local_operation(self, binding: LocalOperationBinding) -> None:
        """Release a binding returned by :meth:`begin_local_operation`."""
        try:
            self._operation_key_remembered.reset(binding.remembered_token)
            self._operation_api_key.reset(binding.key_token)
            self._operation_server_id.reset(binding.server_token)
        finally:
            self._local_operation_lock.release()

    async def authorize_local_writes(
        self,
        app_name: str = "Zotero Keeper",
        *,
        require_remembered: bool = False,
    ) -> dict[str, Any]:
        """Request runtime write permission without exposing the returned key."""
        if not isinstance(app_name, str) or not app_name.strip():
            raise ValueError("app_name must be a non-empty string")

        async with self._local_write_lock:
            # Authorization is also the public source of expected_server_id.
            # Always refresh the root identity before reusing or requesting a
            # key so callers never receive a cached Server-ID as current.
            await self.discover_local_api()
            if self._local_api_key is not None:
                if not require_remembered or self._local_api_key_remembered:
                    return {
                        "authorized": True,
                        "remembered": self._local_api_key_remembered,
                        "server_id": self._local_server_id,
                    }
                self.clear_local_authorization()

            authorization_server_id = self._local_server_id
            response = await self._request_raw(
                "POST",
                "/api/local/authorize",
                json_data={"appName": app_name.strip()},
                headers={
                    "Content-Type": "application/json",
                    "Zotero-API-Version": "3",
                    "Zotero-Server-ID": authorization_server_id,
                },
            )
            response_server_id = self._header_value(response.headers, "Zotero-Server-ID")
            if response_server_id != authorization_server_id or response_server_id is None:
                self.clear_local_authorization()
                raise ZoteroAPIError(
                    "Zotero Server-ID changed during Local API authorization",
                    status_code=412,
                    response_text=response.text,
                    response_headers=response.headers,
                )
            payload = self._parse_json_response(response, operation="write authorization")
            if not isinstance(payload, dict):
                raise ZoteroAPIError("Zotero Local API returned an invalid authorization response")

            key = payload.get("key")
            remembered = payload.get("remember")
            if (
                not isinstance(key, str)
                or len(key) != 32
                or not key.isascii()
                or any(ord(char) < 33 or ord(char) > 126 for char in key)
                or not isinstance(remembered, bool)
            ):
                raise ZoteroAPIError("Zotero Local API returned an invalid authorization response")

            self._local_api_key = key
            self._local_api_key_server_id = self._local_server_id
            self._local_api_key_remembered = remembered
            if require_remembered and not remembered:
                self.clear_local_authorization()
                raise ZoteroAPIError(
                    "This operation requires an 'Always Allow' Local API authorization",
                    status_code=403,
                )

            return {
                "authorized": True,
                "remembered": remembered,
                "server_id": self._local_server_id,
            }

    async def _ensure_local_write_ready(self, *, require_remembered: bool = False) -> None:
        operation_server_id = self._operation_server_id.get()
        if operation_server_id is not None:
            operation_key = self._operation_api_key.get()
            operation_remembered = self._operation_key_remembered.get()
            if operation_key is None:
                raise ZoteroAPIError(
                    "Zotero Local API write authorization is required",
                    status_code=401,
                )
            if require_remembered and not operation_remembered:
                raise ZoteroAPIError(
                    "This operation requires an 'Always Allow' Local API authorization",
                    status_code=403,
                )
            return

        await self._ensure_local_discovery()
        if self._local_api_key is None or self._local_api_key_server_id != self._local_server_id:
            raise ZoteroAPIError(
                "Zotero Local API write authorization is required",
                status_code=401,
            )
        if require_remembered and not self._local_api_key_remembered:
            raise ZoteroAPIError(
                "This operation requires an 'Always Allow' Local API authorization",
                status_code=403,
            )

    async def _local_write_raw(
        self,
        method: str,
        path: str,
        *,
        json_data: Any = None,
        params: dict[str, Any] | None = None,
        data: Mapping[str, Any] | None = None,
        headers: dict[str, str] | None = None,
        require_remembered: bool = False,
    ) -> httpx.Response:
        """Issue one authorized write and never retry it automatically."""
        async with self._local_write_lock:
            return await self._local_write_raw_unlocked(
                method,
                path,
                json_data=json_data,
                params=params,
                data=data,
                headers=headers,
                require_remembered=require_remembered,
            )

    async def _local_write_raw_unlocked(
        self,
        method: str,
        path: str,
        *,
        json_data: Any = None,
        params: dict[str, Any] | None = None,
        data: Mapping[str, Any] | None = None,
        headers: dict[str, str] | None = None,
        require_remembered: bool = False,
    ) -> httpx.Response:
        """Issue one authorized write while holding ``_local_write_lock``."""
        await self._ensure_local_write_ready(require_remembered=require_remembered)
        operation_server_id = self._operation_server_id.get()
        request_server_id = operation_server_id or self._local_server_id
        request_api_key = self._operation_api_key.get() if operation_server_id is not None else self._local_api_key
        request_remembered = self._operation_key_remembered.get() if operation_server_id is not None else self._local_api_key_remembered
        if request_server_id is None or request_api_key is None:
            raise ZoteroAPIError(
                "Zotero Local API write authorization is required",
                status_code=401,
            )
        request_headers = dict(headers or {})
        request_headers.update(
            {
                "Zotero-API-Version": "3",
                "Zotero-Server-ID": request_server_id,
                "Zotero-API-Key": request_api_key,
            }
        )
        single_use = not request_remembered

        try:
            return await self._request_raw(
                method,
                path,
                json_data=json_data,
                params=params,
                data=data,
                headers=request_headers,
            )
        except ZoteroAPIError as exc:
            if exc.status_code == 401:
                if operation_server_id is not None:
                    self._operation_api_key.set(None)
                    self._operation_key_remembered.set(False)
                if self._local_api_key == request_api_key and self._local_api_key_server_id == request_server_id:
                    self.clear_local_authorization()
            elif exc.status_code == 412 and exc.server_id and exc.server_id != request_server_id:
                if self._local_api_key == request_api_key and self._local_api_key_server_id == request_server_id:
                    self.clear_local_authorization()
                    self._local_api_version = None
                    self._local_schema_version = None
                    self._local_server_id = exc.server_id
            # 401/412/428 and all other failures propagate without a retry.
            raise
        finally:
            if single_use:
                if operation_server_id is not None:
                    self._operation_api_key.set(None)
                    self._operation_key_remembered.set(False)
                if self._local_api_key == request_api_key and self._local_api_key_server_id == request_server_id:
                    self.clear_local_authorization()

    @staticmethod
    def _write_token() -> str:
        token = secrets.token_hex(16)
        if len(token) != 32:  # pragma: no cover - secrets contract guard
            raise RuntimeError("Unable to generate a 32-character write token")
        return token

    @staticmethod
    def _expected_version_headers(expected_version: int) -> dict[str, str]:
        return {"If-Unmodified-Since-Version": str(expected_version)}

    async def _local_create(self, endpoint: str, obj: dict[str, Any], *, operation: str) -> dict[str, Any]:
        if not isinstance(obj, dict) or not obj:
            raise ValueError(f"{operation} payload must be a non-empty object")
        response = await self._local_write_raw(
            "POST",
            endpoint,
            json_data=[dict(obj)],
            headers={
                "Content-Type": "application/json",
                "Zotero-Write-Token": self._write_token(),
            },
        )
        payload = self._parse_json_response(response, operation=operation)
        if not isinstance(payload, dict):
            raise ZoteroAPIError(f"Zotero Local API returned an invalid {operation} response")
        successful = payload.get("successful")
        if not isinstance(successful, Mapping):
            successful = payload.get("success")
        created = None
        if isinstance(successful, Mapping):
            created = successful.get("0")
            if created is None:
                created = successful.get(0)
        if created is None:
            failed = payload.get("failed")
            detail = None
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
                    f"Zotero Local API rejected {operation}{suffix}",
                    status_code=status,
                    response_text=response.text,
                    response_headers=response.headers,
                )
            raise ZoteroAPIError(
                f"Zotero Local API returned no created object for {operation}",
                response_text=response.text,
                response_headers=response.headers,
            )
        return payload

    async def _local_update(
        self,
        endpoint: str,
        changes: dict[str, Any],
        *,
        expected_version: int,
        replace: bool,
        operation: str,
    ) -> dict[str, Any] | None:
        if not isinstance(changes, dict) or not changes:
            raise ValueError(f"{operation} payload must be a non-empty object")
        version = self._validate_expected_version(expected_version)
        if "version" in changes:
            payload_version = self._validate_expected_version(changes["version"])
            if payload_version != version:
                raise ValueError("payload version must match expected_version")
        response = await self._local_write_raw(
            "PUT" if replace else "PATCH",
            endpoint,
            json_data=dict(changes),
            headers={
                "Content-Type": "application/json",
                **self._expected_version_headers(version),
            },
        )
        payload = self._parse_json_response(response, operation=operation)
        if payload is not None and not isinstance(payload, dict):
            raise ZoteroAPIError(f"Zotero Local API returned an invalid {operation} response")
        return payload

    async def _local_delete(self, endpoint: str, *, expected_version: int) -> None:
        version = self._validate_expected_version(expected_version)
        await self._local_write_raw(
            "DELETE",
            endpoint,
            headers=self._expected_version_headers(version),
        )

    async def local_create_item(self, item: dict[str, Any]) -> dict[str, Any]:
        return await self._local_create("/api/users/0/items", item, operation="item creation")

    async def local_update_item(
        self,
        item_key: str,
        changes: dict[str, Any],
        *,
        expected_version: int,
        replace: bool = False,
    ) -> dict[str, Any] | None:
        key = self._validate_object_key(item_key, label="item_key")
        return await self._local_update(
            f"/api/users/0/items/{key}",
            changes,
            expected_version=expected_version,
            replace=replace,
            operation="item update",
        )

    async def local_delete_item(self, item_key: str, *, expected_version: int) -> None:
        key = self._validate_object_key(item_key, label="item_key")
        await self._local_delete(f"/api/users/0/items/{key}", expected_version=expected_version)

    async def local_batch_update_items(self, items: list[dict[str, Any]]) -> dict[str, Any]:
        """Update 1..50 items in one request, returning normalized result maps."""
        if not isinstance(items, list) or not 1 <= len(items) <= _MAX_BATCH_SIZE:
            raise ValueError("items must contain between 1 and 50 objects")

        payload_items: list[dict[str, Any]] = []
        for index, item in enumerate(items):
            if not isinstance(item, dict):
                raise ValueError(f"items[{index}] must be an object")
            key = item.get("key")
            version = item.get("version")
            self._validate_object_key(key, label=f"items[{index}].key")
            self._validate_expected_version(version)
            payload_items.append(dict(item))

        response = await self._local_write_raw(
            "POST",
            "/api/users/0/items",
            json_data=payload_items,
            headers={"Content-Type": "application/json"},
        )
        payload = self._parse_json_response(response, operation="batch item update")
        if not isinstance(payload, dict):
            raise ZoteroAPIError("Zotero Local API returned an invalid batch item update response")

        successful = payload.get("successful")
        if successful is None:
            successful = payload.get("success", {})
        unchanged = payload.get("unchanged", {})
        failed = payload.get("failed", {})
        if not all(isinstance(section, dict) for section in (successful, unchanged, failed)):
            raise ZoteroAPIError("Zotero Local API returned malformed batch result maps")

        return {
            "successful": dict(successful),
            "unchanged": dict(unchanged),
            "failed": dict(failed),
        }

    async def local_create_collection(self, collection: dict[str, Any]) -> dict[str, Any]:
        return await self._local_create(
            "/api/users/0/collections",
            collection,
            operation="collection creation",
        )

    async def local_update_collection(
        self,
        collection_key: str,
        changes: dict[str, Any],
        *,
        expected_version: int,
        replace: bool = False,
    ) -> dict[str, Any] | None:
        key = self._validate_object_key(collection_key, label="collection_key")
        return await self._local_update(
            f"/api/users/0/collections/{key}",
            changes,
            expected_version=expected_version,
            replace=replace,
            operation="collection update",
        )

    async def local_delete_collection(self, collection_key: str, *, expected_version: int) -> None:
        key = self._validate_object_key(collection_key, label="collection_key")
        await self._local_delete(
            f"/api/users/0/collections/{key}",
            expected_version=expected_version,
        )

    async def local_create_search(self, search: dict[str, Any]) -> dict[str, Any]:
        return await self._local_create("/api/users/0/searches", search, operation="saved search creation")

    async def local_update_search(
        self,
        search_key: str,
        changes: dict[str, Any],
        *,
        expected_version: int,
        replace: bool = False,
    ) -> dict[str, Any] | None:
        key = self._validate_object_key(search_key, label="search_key")
        return await self._local_update(
            f"/api/users/0/searches/{key}",
            changes,
            expected_version=expected_version,
            replace=replace,
            operation="saved search update",
        )

    async def local_delete_search(self, search_key: str, *, expected_version: int) -> None:
        key = self._validate_object_key(search_key, label="search_key")
        await self._local_delete(f"/api/users/0/searches/{key}", expected_version=expected_version)

    async def local_delete_tags(self, tags: list[str], *, expected_version: int) -> None:
        if not isinstance(tags, list) or not 1 <= len(tags) <= _MAX_BATCH_SIZE:
            raise ValueError("tags must contain between 1 and 50 names")
        if any(not isinstance(tag, str) or not tag for tag in tags):
            raise ValueError("every tag must be a non-empty string")
        version = self._validate_expected_version(expected_version)
        await self._local_write_raw(
            "DELETE",
            "/api/users/0/tags",
            params={"tag": tags},
            headers=self._expected_version_headers(version),
        )

    async def local_set_fulltext(
        self,
        attachment_key: str,
        fulltext: dict[str, Any],
        *,
        expected_library_version: int,
    ) -> dict[str, Any]:
        key = self._validate_object_key(attachment_key, label="attachment_key")
        if not isinstance(fulltext, dict) or not fulltext:
            raise ValueError("fulltext must be a non-empty object")
        if "key" in fulltext:
            raise ValueError("fulltext must not contain the reserved key field")
        library_version = self._validate_expected_version(expected_library_version)
        response = await self._local_write_raw(
            "POST",
            "/api/users/0/fulltext",
            json_data=[{"key": key, **dict(fulltext)}],
            headers={
                "Content-Type": "application/json",
                **self._expected_version_headers(library_version),
            },
        )
        if response.status_code != 200:
            raise ZoteroAPIError(
                "Zotero Local API returned an invalid bulk full-text status",
                status_code=response.status_code,
                response_text=response.text,
                response_headers=response.headers,
            )

        payload = self._parse_json_response(response, operation="bulk full-text update")
        if not isinstance(payload, dict):
            raise ZoteroAPIError(
                "Zotero Local API returned an invalid bulk full-text response",
                response_text=response.text,
                response_headers=response.headers,
            )
        successful = payload.get("successful")
        failed = payload.get("failed")
        if not isinstance(successful, Mapping) or not isinstance(failed, Mapping) or set(successful) - {"0"} or set(failed) - {"0"}:
            raise ZoteroAPIError(
                "Zotero Local API returned malformed bulk full-text result maps",
                response_text=response.text,
                response_headers=response.headers,
            )

        success_detail = successful.get("0")
        failure_detail = failed.get("0")
        if success_detail is not None and failure_detail is not None:
            raise ZoteroAPIError(
                "Zotero Local API returned conflicting bulk full-text results",
                response_text=response.text,
                response_headers=response.headers,
            )
        if failure_detail is not None:
            failure_key = failure_detail.get("key") if isinstance(failure_detail, Mapping) else None
            failure_code = failure_detail.get("code") if isinstance(failure_detail, Mapping) else None
            failure_message = failure_detail.get("message") if isinstance(failure_detail, Mapping) else None
            if (
                failure_key != key
                or isinstance(failure_code, bool)
                or not isinstance(failure_code, int)
                or not 400 <= failure_code <= 599
                or not isinstance(failure_message, str)
                or not failure_message
            ):
                raise ZoteroAPIError(
                    "Zotero Local API returned a malformed bulk full-text failure",
                    response_text=response.text,
                    response_headers=response.headers,
                )
            raise ZoteroAPIError(
                f"Zotero Local API rejected bulk full-text update: {failure_message}",
                status_code=failure_code,
                response_text=response.text,
                response_headers=response.headers,
            )
        if not isinstance(success_detail, Mapping) or success_detail.get("key") != key:
            raise ZoteroAPIError(
                "Zotero Local API returned no matching bulk full-text success",
                response_text=response.text,
                response_headers=response.headers,
            )

        raw_result_version = self._header_value(response.headers, "Last-Modified-Version")
        try:
            result_version = int(raw_result_version) if raw_result_version is not None else -1
        except (TypeError, ValueError) as exc:
            raise ZoteroAPIError(
                "Zotero Local API returned an invalid full-text library version",
                response_text=response.text,
                response_headers=response.headers,
            ) from exc
        if result_version < 0 or str(result_version) != raw_result_version:
            raise ZoteroAPIError(
                "Zotero Local API returned an invalid full-text library version",
                response_text=response.text,
                response_headers=response.headers,
            )
        return {"attachment_key": key, "library_version": result_version}

    async def get_item_file_view_url_snapshot(
        self,
        attachment_key: str,
    ) -> tuple[str, str | None]:
        """Return a view URL with the identity on that exact response."""
        key = self._validate_object_key(attachment_key, label="attachment_key")
        await self._ensure_local_discovery()
        response = await self._request_raw(
            "GET",
            f"/api/users/0/items/{key}/file/view/url",
            headers={"Zotero-API-Version": "3"},
        )
        url = response.text.strip()
        if not url:
            raise ZoteroAPIError("Zotero Local API returned an empty attachment view URL")
        return url, self._header_value(response.headers, "Zotero-Server-ID")

    async def get_item_file_view_url(self, attachment_key: str) -> str:
        """Return the Local API's plain-text attachment view URL."""
        url, _ = await self.get_item_file_view_url_snapshot(attachment_key)
        return url

    @staticmethod
    def _file_metadata(path: Path) -> tuple[int, int, str]:
        if not path.is_file():
            raise ValueError(f"Attachment path is not a regular file: {path}")
        before = path.stat()
        if before.st_size >= _MAX_LOCAL_FILE_SIZE:
            raise ValueError("Zotero Local API attachments must be smaller than 4 GB")

        digest = hashlib.md5(usedforsecurity=False)
        with path.open("rb") as file_handle:
            while chunk := file_handle.read(_FILE_CHUNK_SIZE):
                digest.update(chunk)

        after = path.stat()
        if before.st_size != after.st_size or before.st_mtime_ns != after.st_mtime_ns:
            raise ValueError("Attachment file changed while its upload metadata was prepared")
        return before.st_size, before.st_mtime_ns // 1_000_000, digest.hexdigest()

    @staticmethod
    async def _stream_file(path: Path, prefix: bytes = b"", suffix: bytes = b"") -> AsyncIterator[bytes]:
        if prefix:
            yield prefix
        file_handle = await asyncio.to_thread(path.open, "rb")
        try:
            while chunk := await asyncio.to_thread(file_handle.read, _FILE_CHUNK_SIZE):
                yield chunk
        finally:
            await asyncio.to_thread(file_handle.close)
        if suffix:
            yield suffix

    @staticmethod
    def _is_loopback_host(host: str | None) -> bool:
        if not host:
            return False
        if host.lower() == "localhost":
            return True
        try:
            return ip_address(host.strip("[]")).is_loopback
        except ValueError:
            return False

    def _validated_upload_url(self, raw_url: Any, upload_key: str) -> httpx.URL:
        if not isinstance(raw_url, str) or not raw_url:
            raise ZoteroAPIError("Zotero Local API returned an invalid upload URL")
        if not isinstance(upload_key, str) or not upload_key or "/" in upload_key:
            raise ZoteroAPIError("Zotero Local API returned an invalid upload key")

        base_url = httpx.URL(self.config.base_url)
        upload_url = base_url.join(httpx.URL(raw_url))
        expected_path = f"/api/local/uploads/{upload_key}"
        if (
            upload_url.scheme != base_url.scheme
            or not self._is_loopback_host(upload_url.host)
            or upload_url.port != base_url.port
            or upload_url.path != expected_path
        ):
            raise ZoteroAPIError("Zotero Local API upload URL escaped the configured loopback origin")
        return upload_url

    @staticmethod
    def _created_object(payload: dict[str, Any]) -> tuple[str, Any]:
        successful = payload.get("successful")
        if successful is None:
            successful = payload.get("success")
        if not isinstance(successful, dict):
            raise ZoteroAPIError("Zotero Local API item creation response has no success map")

        created = successful.get("0")
        if created is None:
            created = successful.get(0)
        if isinstance(created, str):
            key = created
        elif isinstance(created, dict):
            key = created.get("key")
            if not isinstance(key, str) and isinstance(created.get("data"), dict):
                key = created["data"].get("key")
        else:
            key = None
        if not isinstance(key, str) or not _OBJECT_KEY_RE.fullmatch(key):
            raise ZoteroAPIError("Zotero Local API item creation response has no valid item key")
        return key, created

    async def local_attach_file(
        self,
        parent_item_key: str,
        file_path: str | Path,
        *,
        title: str | None = None,
        content_type: str | None = None,
        source_url: str = "",
    ) -> dict[str, Any]:
        """Create and fully upload a stored attachment below an existing item."""
        parent_key = self._validate_object_key(parent_item_key, label="parent_item_key")
        await self._ensure_local_write_ready(require_remembered=True)

        path = Path(file_path).expanduser()
        size, mtime, md5 = await asyncio.to_thread(self._file_metadata, path)
        mime_type = content_type or mimetypes.guess_type(path.name)[0] or "application/octet-stream"
        if not isinstance(mime_type, str) or not mime_type or not mime_type.isascii() or "\r" in mime_type or "\n" in mime_type:
            raise ValueError("content_type must be a safe ASCII media type")

        attachment_payload = {
            "itemType": "attachment",
            "parentItem": parent_key,
            "linkMode": "imported_file",
            "title": title or path.name,
            "accessDate": "",
            "url": source_url,
            "note": "",
            "tags": [],
            "relations": {},
            "contentType": mime_type,
            "charset": "",
            "filename": path.name,
        }
        creation = await self.local_create_item(attachment_payload)
        attachment_key, created = self._created_object(creation)
        file_endpoint = f"/api/users/0/items/{attachment_key}/file"
        condition_headers = {
            "Content-Type": "application/x-www-form-urlencoded",
            "If-None-Match": "*",
        }

        try:
            authorization_response = await self._local_write_raw(
                "POST",
                file_endpoint,
                data={
                    "md5": md5,
                    "filename": path.name,
                    "filesize": str(size),
                    "mtime": str(mtime),
                },
                headers=condition_headers,
                require_remembered=True,
            )
            authorization = self._parse_json_response(
                authorization_response,
                operation="attachment upload authorization",
            )
            if not isinstance(authorization, dict):
                raise ZoteroAPIError("Zotero Local API returned an invalid upload authorization")
            if authorization.get("exists") == 1:
                return {
                    "attachment_key": attachment_key,
                    "attachment": created,
                    "uploaded": False,
                    "exists": True,
                    "last_modified_version": self._header_value(
                        authorization_response.headers,
                        "Last-Modified-Version",
                    ),
                }

            upload_key = authorization.get("uploadKey")
            upload_content_type = authorization.get("contentType")
            prefix = authorization.get("prefix")
            suffix = authorization.get("suffix")
            if not isinstance(upload_key, str) or not isinstance(upload_content_type, str):
                raise ZoteroAPIError("Zotero Local API returned incomplete upload authorization")
            if not isinstance(prefix, str) or not isinstance(suffix, str):
                raise ZoteroAPIError("Zotero Local API returned invalid upload framing")
            if not upload_content_type or not upload_content_type.isascii() or "\r" in upload_content_type or "\n" in upload_content_type:
                raise ZoteroAPIError("Zotero Local API returned an invalid upload content type")

            upload_url = self._validated_upload_url(authorization.get("url"), upload_key)
            prefix_bytes = prefix.encode("utf-8")
            suffix_bytes = suffix.encode("utf-8")
            upload_response = await self._request_raw(
                "POST",
                str(upload_url),
                content=self._stream_file(path, prefix_bytes, suffix_bytes),
                headers={
                    "Content-Type": upload_content_type,
                    "Content-Length": str(len(prefix_bytes) + size + len(suffix_bytes)),
                },
            )
            if upload_response.status_code != 201:
                raise ZoteroAPIError(
                    "Zotero Local API did not accept the attachment bytes",
                    status_code=upload_response.status_code,
                    response_text=upload_response.text,
                    response_headers=upload_response.headers,
                )

            register_response = await self._local_write_raw(
                "POST",
                file_endpoint,
                data={"upload": upload_key},
                headers=condition_headers,
                require_remembered=True,
            )
            if register_response.status_code != 204:
                raise ZoteroAPIError(
                    "Zotero Local API did not register the attachment upload",
                    status_code=register_response.status_code,
                    response_text=register_response.text,
                    response_headers=register_response.headers,
                )

            return {
                "attachment_key": attachment_key,
                "attachment": created,
                "uploaded": True,
                "exists": False,
                "last_modified_version": self._header_value(
                    register_response.headers,
                    "Last-Modified-Version",
                ),
            }
        except Exception as exc:
            # The child item is a durable partial result. Never attempt cleanup:
            # callers need its key to inspect or resume the failed upload.
            setattr(exc, "attachment_key", attachment_key)
            setattr(exc, "partial", True)
            raise
