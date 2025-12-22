"""
Collection tools for Zotero MCP Server

Provides collection management tools:
- list_collections: List all collections
- get_collection: Get collection by key
- get_collection_items: Get items in a collection
- get_collection_tree: Get hierarchical tree structure
- find_collection: Find collection by name
"""

import logging
from typing import TYPE_CHECKING, Any

from mcp.server.fastmcp import FastMCP

if TYPE_CHECKING:
    from ..zotero_client.client import ZoteroClient

from ..zotero_client.client import ZoteroAPIError, ZoteroConnectionError
from .basic_read_tools import _format_creators

logger = logging.getLogger(__name__)


def register_collection_tools(mcp: FastMCP, zotero: "ZoteroClient") -> None:
    """Register collection tools with the MCP server"""

    @mcp.tool()
    async def list_collections() -> dict[str, Any]:
        """
        📁 List all collections in Zotero library

        列出所有收藏夾

        ⭐ IMPORTANT: Use this tool BEFORE importing articles!
        Show the user available collections so they can choose where to save.

        💡 WORKFLOW:
        1. Search articles (search_pubmed_exclude_owned)
        2. Call list_collections to show options
        3. Ask user: "Which collection should I save these to?"
        4. Import with collection_name parameter

        Returns:
            List of collections with item counts
        """
        try:
            collections = await zotero.get_collections()
            results = []
            for col in collections:
                data = col.get("data", col)
                results.append({
                    "key": col.get("key"),
                    "name": data.get("name", ""),
                    "parentKey": data.get("parentCollection"),
                    "itemCount": data.get("numItems", 0),
                })
            return {
                "count": len(results),
                "collections": results,
            }
        except (ZoteroConnectionError, ZoteroAPIError) as e:
            return {"count": 0, "collections": [], "error": str(e)}

    @mcp.tool()
    async def get_collection(key: str) -> dict[str, Any]:
        """
        📁 Get a specific collection by key

        取得特定收藏夾的詳細資訊

        Args:
            key: Collection key (e.g., "ABC12345")

        Returns:
            Collection details including name and item count
        """
        try:
            col = await zotero.get_collection(key)
            data = col.get("data", col)
            return {
                "found": True,
                "collection": {
                    "key": col.get("key"),
                    "name": data.get("name", ""),
                    "parentKey": data.get("parentCollection"),
                    "itemCount": data.get("numItems", 0),
                },
            }
        except ZoteroAPIError as e:
            if e.status_code == 404:
                return {"found": False, "error": f"Collection '{key}' not found"}
            return {"found": False, "error": str(e)}
        except ZoteroConnectionError as e:
            return {"found": False, "error": str(e)}

    @mcp.tool()
    async def get_collection_items(
        collection_key: str,
        limit: int = 50,
    ) -> dict[str, Any]:
        """
        📚 Get items in a specific collection

        取得特定收藏夾內的所有文獻

        Args:
            collection_key: Collection key (e.g., "ABC12345")
            limit: Maximum items to return (default: 50)

        Returns:
            List of items in the collection
        """
        try:
            items = await zotero.get_collection_items(collection_key, limit=limit)
            results = []
            for item in items:
                data = item.get("data", item)
                if data.get("itemType") == "attachment":
                    continue
                results.append({
                    "key": item.get("key"),
                    "title": data.get("title", ""),
                    "itemType": data.get("itemType", ""),
                    "date": data.get("date", ""),
                    "creators": _format_creators(data.get("creators", [])),
                })
            return {
                "collection_key": collection_key,
                "count": len(results),
                "items": results,
            }
        except (ZoteroConnectionError, ZoteroAPIError) as e:
            return {"collection_key": collection_key, "count": 0, "items": [], "error": str(e)}

    @mcp.tool()
    async def get_collection_tree() -> dict[str, Any]:
        """
        🌳 Get collections as a hierarchical tree

        取得收藏夾的樹狀結構（含子收藏夾）

        Returns:
            Tree structure with nested children

        Example response:
            {
                "count": 2,
                "tree": [
                    {
                        "key": "ABC123",
                        "name": "AI Research",
                        "itemCount": 10,
                        "children": [
                            {"key": "DEF456", "name": "Deep Learning", ...}
                        ]
                    }
                ]
            }
        """
        try:
            tree = await zotero.get_collection_tree()
            return {
                "count": len(tree),
                "tree": tree,
            }
        except (ZoteroConnectionError, ZoteroAPIError) as e:
            return {"count": 0, "tree": [], "error": str(e)}

    @mcp.tool()
    async def find_collection(
        name: str,
        parent_name: str | None = None,
    ) -> dict[str, Any]:
        """
        🔍 Find a collection by name

        用名稱查找收藏夾（不區分大小寫）

        Args:
            name: Collection name to search for
            parent_name: Optional parent collection name to narrow search

        Returns:
            Collection if found, or suggestions if not found

        Example:
            find_collection(name="AI Research")
            find_collection(name="Deep Learning", parent_name="AI Research")
        """
        try:
            # First find parent if specified
            parent_key = None
            if parent_name:
                parent = await zotero.find_collection_by_name(parent_name)
                if parent:
                    parent_key = parent.get("key")
                else:
                    return {
                        "found": False,
                        "error": f"Parent collection '{parent_name}' not found",
                    }

            col = await zotero.find_collection_by_name(name, parent_key)
            if col:
                data = col.get("data", col)
                return {
                    "found": True,
                    "collection": {
                        "key": col.get("key"),
                        "name": data.get("name", ""),
                        "parentKey": data.get("parentCollection"),
                        "itemCount": data.get("numItems", 0),
                    },
                }
            else:
                # Provide suggestions
                all_collections = await zotero.get_collections()
                suggestions = []
                name_lower = name.lower()
                for c in all_collections:
                    cdata = c.get("data", c)
                    cname = cdata.get("name", "")
                    if name_lower in cname.lower():
                        suggestions.append(cname)
                return {
                    "found": False,
                    "error": f"Collection '{name}' not found",
                    "suggestions": suggestions[:5] if suggestions else None,
                }
        except (ZoteroConnectionError, ZoteroAPIError) as e:
            return {"found": False, "error": str(e)}

    logger.info("Collection tools registered (list_collections, get_collection, get_collection_items, get_collection_tree, find_collection)")
