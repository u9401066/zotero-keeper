"""
Zotero Client - Read Operations Mixin

Provides read operations:
- Items (get, search, filter)
- Collections
- Tags
- Saved Searches (Local API exclusive!)
- Schema
"""

from typing import Any


class ZoteroReadMixin:
    """Mixin providing read operations for ZoteroClient"""

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

        return await self._request("GET", "/api/users/0/items", params=params)

    async def get_item(self, item_key: str) -> dict[str, Any]:
        """Get a single item by key"""
        return await self._request("GET", f"/api/users/0/items/{item_key}")

    async def get_item_children(self, item_key: str) -> list[dict[str, Any]]:
        """Get child items (attachments, notes) of an item"""
        return await self._request("GET", f"/api/users/0/items/{item_key}/children")

    async def search_items(
        self,
        query: str,
        limit: int = 25,
    ) -> list[dict[str, Any]]:
        """Search for items by title, creator, year"""
        return await self.get_items(q=query, limit=limit)

    # ==================== Collections ====================

    async def get_collections(self) -> list[dict[str, Any]]:
        """Get all collections"""
        return await self._request("GET", "/api/users/0/collections")

    async def get_collection(self, collection_key: str) -> dict[str, Any]:
        """Get a single collection"""
        return await self._request(
            "GET", f"/api/users/0/collections/{collection_key}"
        )

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

            if col_name == name_lower and (
                parent_key is None or col_parent == parent_key
            ):
                return col

        return None

    async def get_collection_tree(self) -> list[dict[str, Any]]:
        """Get collections organized as a tree structure"""
        collections = await self.get_collections()

        col_by_key: dict[str, dict] = {}
        for col in collections:
            key = col.get("key")
            data = col.get("data", col)
            col_by_key[key] = {
                "key": key,
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

    # ==================== Saved Searches ====================

    async def get_searches(self) -> list[dict[str, Any]]:
        """Get all saved searches (Local API exclusive!)"""
        return await self._request("GET", "/api/users/0/searches")

    async def get_search(self, search_key: str) -> dict[str, Any]:
        """Get a specific saved search by key"""
        return await self._request("GET", f"/api/users/0/searches/{search_key}")

    async def execute_search(
        self, search_key: str, limit: int = 100
    ) -> list[dict[str, Any]]:
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
        return await self._request(
            "GET",
            "/api/itemTypeCreatorTypes",
            params={"itemType": item_type},
        )
