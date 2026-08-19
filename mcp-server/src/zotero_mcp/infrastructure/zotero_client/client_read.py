"""
Zotero Client - Read Operations Mixin

Provides read operations:
- Items (get, search, filter)
- Collections
- Tags
- Saved Searches (Local API exclusive!)
- Schema
- Attachments & Fulltext
"""

import json
import logging
import os
from collections.abc import Mapping
from pathlib import Path
from typing import Any, cast

from .client_base import ZoteroAPIError

logger = logging.getLogger(__name__)


class ZoteroReadMixin:
    """Mixin providing read operations for ZoteroClient"""

    async def _request_snapshot(
        self,
        method: str,
        path: str,
        *,
        params: dict[str, Any] | None = None,
    ) -> tuple[Any, str | None]:
        """Return a decoded response together with its own Local API identity.

        ``_local_server_id`` is shared discovery state and may already refer to
        another Zotero profile by the time a caller formats a read result.  A
        mutation proposal must therefore carry the ``Zotero-Server-ID`` from
        the exact HTTP response that supplied its object version.

        Zotero 7--9 responses legitimately omit the header; keep that as
        ``None`` instead of inferring an identity from client state.
        """
        response = await self._request_raw(method, path, params=params)
        payload: Any = None
        if response.text:
            try:
                payload = response.json()
            except (json.JSONDecodeError, ValueError):
                payload = response.text
        return payload, self._header_value(response.headers, "Zotero-Server-ID")

    # ==================== Items ====================

    async def get_items(
        self,
        limit: int = 50,
        start: int = 0,
        sort: str = "dateModified",
        direction: str = "desc",
        item_type: str | None = None,
        q: str | None = None,
        qmode: str = "titleCreatorYear",
        tag: str | list[str] | None = None,
        include_trashed: bool = False,
    ) -> list[dict[str, Any]]:
        """
        Get items from user library with advanced filtering

        Args:
            limit: Maximum number of items to return
            start: Offset for pagination
            sort: Sort field (dateModified, dateAdded, title, creator, etc.)
            direction: Sort direction (asc, desc)
            item_type: Filter by item type (journalArticle, book, etc.)
            q: Quick search query
            qmode: Search mode (titleCreatorYear, everything)
            tag: Filter by tag(s)
            include_trashed: Include items in trash
        """
        params = self._item_query_params(
            limit=limit,
            start=start,
            sort=sort,
            direction=direction,
            item_type=item_type,
            q=q,
            qmode=qmode,
            tag=tag,
            include_trashed=include_trashed,
        )

        return await self._request("GET", "/api/users/0/items", params=params)

    async def get_items_snapshot(
        self,
        limit: int = 50,
        start: int = 0,
        sort: str = "dateModified",
        direction: str = "desc",
        item_type: str | None = None,
        q: str | None = None,
        qmode: str = "titleCreatorYear",
        tag: str | list[str] | None = None,
        include_trashed: bool = False,
    ) -> tuple[list[dict[str, Any]], str | None]:
        """Get items and the Server-ID on that exact HTTP response."""
        params = self._item_query_params(
            limit=limit,
            start=start,
            sort=sort,
            direction=direction,
            item_type=item_type,
            q=q,
            qmode=qmode,
            tag=tag,
            include_trashed=include_trashed,
        )
        payload, server_id = await self._request_snapshot("GET", "/api/users/0/items", params=params)
        return cast(list[dict[str, Any]], payload), server_id

    @staticmethod
    def _item_query_params(
        *,
        limit: int,
        start: int,
        sort: str,
        direction: str,
        item_type: str | None,
        q: str | None,
        qmode: str,
        tag: str | list[str] | None,
        include_trashed: bool,
    ) -> dict[str, Any]:
        """Build the shared item-list query for ordinary and snapshot reads."""
        params: dict[str, Any] = {
            "limit": limit,
            "start": start,
            "sort": sort,
            "direction": direction,
        }
        if item_type:
            params["itemType"] = item_type
        if q:
            params["q"] = q
            params["qmode"] = qmode
        if tag:
            if isinstance(tag, list):
                for t in tag:
                    if "tag" not in params:
                        params["tag"] = t
                    else:
                        if isinstance(params["tag"], list):
                            params["tag"].append(t)
                        else:
                            params["tag"] = [params["tag"], t]
            else:
                params["tag"] = tag
        if include_trashed:
            params["includeTrashed"] = "1"
        return params

    async def get_item(self, item_key: str) -> dict[str, Any]:
        """Get a single item by key"""
        return await self._request("GET", f"/api/users/0/items/{item_key}")

    async def get_item_snapshot(self, item_key: str) -> tuple[dict[str, Any], str | None]:
        """Get an item and the Server-ID on that exact HTTP response."""
        payload, server_id = await self._request_snapshot("GET", f"/api/users/0/items/{item_key}")
        return cast(dict[str, Any], payload), server_id

    async def get_item_children(self, item_key: str) -> list[dict[str, Any]]:
        """Get child items (attachments, notes) of an item"""
        return await self._request("GET", f"/api/users/0/items/{item_key}/children")

    async def get_item_children_snapshot(
        self,
        item_key: str,
    ) -> tuple[list[dict[str, Any]], str | None]:
        """Get child items and the Server-ID on that exact HTTP response."""
        payload, server_id = await self._request_snapshot("GET", f"/api/users/0/items/{item_key}/children")
        return cast(list[dict[str, Any]], payload), server_id

    async def search_items(
        self,
        query: str,
        limit: int = 25,
    ) -> list[dict[str, Any]]:
        """Search for items by title, creator, year"""
        return await self.get_items(q=query, limit=limit)

    async def search_items_snapshot(
        self,
        query: str,
        limit: int = 25,
    ) -> tuple[list[dict[str, Any]], str | None]:
        """Search items and retain the exact response's Server-ID."""
        return await self.get_items_snapshot(q=query, limit=limit)

    # ==================== Collections ====================

    async def get_collections(self) -> list[dict[str, Any]]:
        """Get all collections"""
        return await self._request("GET", "/api/users/0/collections")

    async def get_collections_snapshot(self) -> tuple[list[dict[str, Any]], str | None]:
        """Get collections and the Server-ID on that exact HTTP response."""
        payload, server_id = await self._request_snapshot("GET", "/api/users/0/collections")
        return cast(list[dict[str, Any]], payload), server_id

    async def get_collection(self, collection_key: str) -> dict[str, Any]:
        """Get a single collection"""
        return await self._request("GET", f"/api/users/0/collections/{collection_key}")

    async def get_collection_snapshot(
        self,
        collection_key: str,
    ) -> tuple[dict[str, Any], str | None]:
        """Get a collection and the Server-ID on that exact HTTP response."""
        payload, server_id = await self._request_snapshot("GET", f"/api/users/0/collections/{collection_key}")
        return cast(dict[str, Any], payload), server_id

    async def get_collection_items(
        self,
        collection_key: str,
        limit: int = 50,
    ) -> list[dict[str, Any]]:
        """Get items in a collection"""
        return await self._request(
            "GET",
            f"/api/users/0/collections/{collection_key}/items",
            params={"limit": limit},
        )

    async def get_collection_items_snapshot(
        self,
        collection_key: str,
        limit: int = 50,
    ) -> tuple[list[dict[str, Any]], str | None]:
        """Get collection items and the Server-ID on that HTTP response."""
        payload, server_id = await self._request_snapshot(
            "GET",
            f"/api/users/0/collections/{collection_key}/items",
            params={"limit": limit},
        )
        return cast(list[dict[str, Any]], payload), server_id

    async def find_collection_by_name(
        self,
        name: str,
        parent_key: str | None = None,
    ) -> dict[str, Any] | None:
        """Find a collection by name (case-insensitive)"""
        collections = await self.get_collections()
        name_lower = name.lower().strip()

        for col in collections:
            data = col.get("data", col)
            col_name = data.get("name", "").lower().strip()
            col_parent = data.get("parentCollection")

            if col_name == name_lower and (parent_key is None or col_parent == parent_key):
                return col

        return None

    async def get_collection_tree(self) -> list[dict[str, Any]]:
        """Get collections organized as a tree structure"""
        collections = await self.get_collections()

        return self._build_collection_tree(collections)

    async def get_collection_tree_snapshot(self) -> tuple[list[dict[str, Any]], str | None]:
        """Get a collection tree tied to its source response's Server-ID."""
        collections, server_id = await self.get_collections_snapshot()
        return self._build_collection_tree(collections), server_id

    @staticmethod
    def _build_collection_tree(collections: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """Build a hierarchy without losing the source response identity."""

        col_by_key: dict[str, dict[str, Any]] = {}
        for col in collections:
            key = col.get("key")
            if not isinstance(key, str):
                continue
            data = col.get("data", col)
            col_by_key[key] = {
                "key": key,
                "version": col.get("version", data.get("version")),
                "version_scope": "local",
                "name": data.get("name", ""),
                "parentKey": data.get("parentCollection"),
                "itemCount": data.get("numItems", 0),
                "children": [],
            }

        roots = []
        for _, col in col_by_key.items():
            parent_key = col["parentKey"]
            if parent_key and parent_key in col_by_key:
                col_by_key[parent_key]["children"].append(col)
            else:
                roots.append(col)

        return roots

    # ==================== Tags ====================

    async def get_tags(self) -> list[dict[str, Any]]:
        """Get all tags"""
        return await self._request("GET", "/api/users/0/tags")

    async def get_tags_snapshot(self) -> tuple[list[dict[str, Any]], int | None, str | None]:
        """Get tags with the library cursor and Server-ID on that response."""
        response = await self._request_raw("GET", "/api/users/0/tags")
        try:
            payload = response.json()
        except (json.JSONDecodeError, ValueError) as exc:
            raise ZoteroAPIError(
                "Zotero Local API returned invalid JSON for the tag snapshot",
                status_code=response.status_code,
                response_text=response.text,
                response_headers=response.headers,
            ) from exc
        if not isinstance(payload, list):
            raise ZoteroAPIError(
                "Zotero Local API returned an invalid tag snapshot",
                status_code=response.status_code,
                response_text=response.text,
                response_headers=response.headers,
            )
        server_id = self._header_value(response.headers, "Zotero-Server-ID")
        library_version = self._response_library_version(
            response,
            operation="the tag snapshot",
            required=server_id is not None,
        )
        return cast(list[dict[str, Any]], payload), library_version, server_id

    # ==================== Saved Searches ====================

    async def get_searches(self) -> list[dict[str, Any]]:
        """Get all saved searches (Local API exclusive!)"""
        return await self._request("GET", "/api/users/0/searches")

    async def get_search(self, search_key: str) -> dict[str, Any]:
        """Get a specific saved search by key"""
        return await self._request("GET", f"/api/users/0/searches/{search_key}")

    async def get_search_snapshot(self, search_key: str) -> tuple[dict[str, Any], str | None]:
        """Get one saved search and the Server-ID on that exact response."""
        payload, server_id = await self._request_snapshot(
            "GET",
            f"/api/users/0/searches/{search_key}",
        )
        return cast(dict[str, Any], payload), server_id

    async def execute_search(self, search_key: str, limit: int = 100) -> list[dict[str, Any]]:
        """
        Execute a saved search and return matching items.

        🌟 Local API 獨有功能！Web API 無法執行搜尋。
        """
        return await self._request(
            "GET",
            f"/api/users/0/searches/{search_key}/items",
            params={"limit": limit},
        )

    async def find_search_by_name(self, name: str) -> dict[str, Any] | None:
        """Find a saved search by name (case-insensitive)"""
        searches = await self.get_searches()
        name_lower = name.lower().strip()

        for search in searches:
            data = search.get("data", search)
            search_name = data.get("name", "").lower().strip()
            if search_name == name_lower:
                return search

        return None

    # ==================== Schema ====================

    async def get_item_types(self) -> list[dict[str, Any]]:
        """Get available item types"""
        return await self._request("GET", "/api/itemTypes")

    async def get_item_fields(self, item_type: str) -> list[dict[str, Any]]:
        """Get fields for a specific item type"""
        return await self._request(
            "GET",
            "/api/itemTypeFields",
            params={"itemType": item_type},
        )

    async def get_creator_types(self, item_type: str) -> list[dict[str, Any]]:
        """Get creator types for a specific item type"""
        params = {"itemType": item_type}
        try:
            return await self._request(
                "GET",
                "/api/itemTypeCreatorTypes",
                params=params,
            )
        except ZoteroAPIError as e:
            if e.status_code not in {404, 501}:
                raise
            logger.debug("Falling back to Zotero creatorTypes schema endpoint")
            return await self._request(
                "GET",
                "/api/creatorTypes",
                params=params,
            )

    # ==================== Attachments & Fulltext ====================

    def _response_library_version(
        self,
        response: Any,
        *,
        operation: str,
        required: bool,
    ) -> int | None:
        raw_version = self._header_value(response.headers, "Last-Modified-Version")
        if raw_version is None and not required:
            return None
        try:
            version = int(raw_version) if raw_version is not None else -1
        except (TypeError, ValueError) as exc:
            raise ZoteroAPIError(
                f"Zotero Local API returned an invalid Last-Modified-Version for {operation}",
                status_code=response.status_code,
                response_text=response.text,
                response_headers=response.headers,
            ) from exc
        if version < 0 or str(version) != raw_version:
            raise ZoteroAPIError(
                f"Zotero Local API returned an invalid Last-Modified-Version for {operation}",
                status_code=response.status_code,
                response_text=response.text,
                response_headers=response.headers,
            )
        return version

    async def get_library_cursor(self) -> dict[str, Any]:
        """Read the My Library version cursor with its exact Server-ID.

        Library-wide Local API mutations (for example tag deletion and bulk
        full-text writes) use ``Last-Modified-Version`` rather than an
        individual object's version.  Requesting the compact versions format
        avoids transferring library objects while retaining both response
        headers that bind the cursor to one Zotero database.
        """
        response = await self._request_raw(
            "GET",
            "/api/users/0/items",
            params={"format": "versions", "limit": 1},
        )
        try:
            payload = response.json()
        except (json.JSONDecodeError, ValueError) as exc:
            raise ZoteroAPIError(
                "Zotero Local API returned invalid JSON for the library cursor",
                status_code=response.status_code,
                response_text=response.text,
                response_headers=response.headers,
            ) from exc
        if not isinstance(payload, Mapping):
            raise ZoteroAPIError(
                "Zotero Local API returned an invalid library versions cursor",
                status_code=response.status_code,
                response_text=response.text,
                response_headers=response.headers,
            )

        server_id = self._header_value(response.headers, "Zotero-Server-ID")
        library_version = self._response_library_version(
            response,
            operation="the library cursor",
            required=server_id is not None,
        )
        return {
            "library_version": library_version,
            "server_id": server_id,
        }

    async def get_item_library_cursor(self, item_key: str) -> dict[str, Any]:
        """Read one exact item's object version and containing library cursor."""
        response = await self._request_raw(
            "GET",
            "/api/users/0/items",
            params={"itemKey": item_key, "format": "versions"},
        )
        try:
            payload = response.json()
        except (json.JSONDecodeError, ValueError) as exc:
            raise ZoteroAPIError(
                "Zotero Local API returned invalid JSON for the full-text library cursor",
                status_code=response.status_code,
                response_text=response.text,
                response_headers=response.headers,
            ) from exc
        item_version = payload.get(item_key) if isinstance(payload, Mapping) else None
        if (
            not isinstance(payload, Mapping)
            or set(payload) != {item_key}
            or isinstance(item_version, bool)
            or not isinstance(item_version, int)
            or item_version < 0
        ):
            raise ZoteroAPIError(
                "Zotero Local API returned an invalid item-versions cursor for full text",
                status_code=response.status_code,
                response_text=response.text,
                response_headers=response.headers,
            )

        server_id = self._header_value(response.headers, "Zotero-Server-ID")
        library_version = self._response_library_version(
            response,
            operation="the item library cursor",
            required=server_id is not None,
        )
        return {
            "item_version": item_version,
            "library_version": library_version,
            "server_id": server_id,
        }

    async def get_item_fulltext(self, item_key: str) -> dict[str, Any]:
        """
        Get fulltext content indexed by Zotero for an attachment.

        Zotero automatically indexes PDF/EPUB/HTML attachments.
        This endpoint returns the indexed plain text.

        Args:
            item_key: The attachment item key (NOT the parent item key)

        Returns:
            Dict with 'content', 'indexedPages', 'totalPages', plus the
            snapshot's 'libraryVersion' and 'serverID' on Zotero 10+
            Raises ZoteroAPIError (404) if not indexed

        Example response:
            {"content": "Full text...", "indexedPages": 12, "totalPages": 12}
        """
        # A library cursor on both sides of the content read prevents a
        # concurrent full-text update from being paired with a newer cursor.
        # All three reads are automatically bound to the observed Server-ID by
        # ``ZoteroClientBase``; a profile switch therefore fails with 412.
        before_cursor = await self.get_item_library_cursor(item_key)
        response = await self._request_raw("GET", f"/api/users/0/items/{item_key}/fulltext")
        try:
            payload = response.json()
        except (json.JSONDecodeError, ValueError) as exc:
            raise ZoteroAPIError(
                "Zotero Local API returned invalid JSON for attachment full text",
                status_code=response.status_code,
                response_text=response.text,
                response_headers=response.headers,
            ) from exc
        if not isinstance(payload, dict):
            raise ZoteroAPIError(
                "Zotero Local API returned an invalid attachment full-text response",
                status_code=response.status_code,
                response_text=response.text,
                response_headers=response.headers,
            )

        fulltext_server_id = self._header_value(response.headers, "Zotero-Server-ID")
        after_cursor = await self.get_item_library_cursor(item_key)
        before_server_id = before_cursor["server_id"]
        after_server_id = after_cursor["server_id"]

        server_ids = (before_server_id, fulltext_server_id, after_server_id)
        present_server_ids = {server_id for server_id in server_ids if server_id is not None}
        if present_server_ids and (len(present_server_ids) != 1 or any(server_id is None for server_id in server_ids)):
            raise ZoteroAPIError(
                "Zotero Server-ID changed while reading attachment full text",
                status_code=412,
                response_headers={"Zotero-Server-ID": after_server_id or fulltext_server_id or before_server_id or ""},
            )
        if before_cursor["library_version"] != after_cursor["library_version"]:
            raise ZoteroAPIError(
                "Zotero library changed while reading attachment full text; read it again before writing",
                status_code=412,
                response_headers={"Zotero-Server-ID": after_server_id or ""},
            )

        result = dict(payload)
        if after_cursor["library_version"] is not None:
            result["libraryVersion"] = after_cursor["library_version"]
        if after_server_id is not None:
            result["serverID"] = after_server_id
        return result

    def resolve_attachment_path(self, attachment_key: str, filename: str) -> Path | None:
        """
        Resolve the file system path for a Zotero attachment.

        Zotero stores attachments at:
            {ZOTERO_DATA_DIR}/storage/{ATTACHMENT_KEY}/{filename}

        Args:
            attachment_key: 8-character attachment key
            filename: Original filename (e.g. "paper.pdf")

        Returns:
            Path to the file if ZOTERO_DATA_DIR is configured, None otherwise
        """
        data_dir = os.getenv("ZOTERO_DATA_DIR")
        if not data_dir:
            return None

        path = Path(data_dir) / "storage" / attachment_key / filename
        return path
