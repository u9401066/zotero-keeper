"""
Basic read tools for Zotero MCP Server

Provides item reading and searching tools:
- search_items: Search Zotero library
- get_item: Get item details
- list_items: List recent items
- list_tags: List all tags
- get_item_types: Get available item types
"""

import logging
from typing import TYPE_CHECKING, Any

from mcp.server.fastmcp import FastMCP

if TYPE_CHECKING:
    from ..zotero_client.client import ZoteroClient

from ..zotero_client.client import ZoteroAPIError, ZoteroConnectionError

logger = logging.getLogger(__name__)


def _format_creators(creators: list[dict]) -> str:
    """Format creators list as string"""
    if not creators:
        return ""
    names = []
    for c in creators[:3]:  # Limit to first 3
        if c.get("firstName"):
            names.append(f"{c.get('firstName', '')} {c.get('lastName', '')}")
        else:
            names.append(c.get("lastName", c.get("name", "")))
    result = ", ".join(names)
    if len(creators) > 3:
        result += f" et al. (+{len(creators) - 3})"
    return result


def register_basic_read_tools(mcp: FastMCP, zotero: "ZoteroClient") -> None:
    """Register basic read tools with the MCP server"""

    @mcp.tool()
    async def search_items(
        query: str,
        limit: int = 25,
    ) -> dict[str, Any]:
        """
        🔍 Search for references in Zotero

        搜尋 Zotero 中的書目資料

        Args:
            query: Search terms (title, author, year)
            limit: Maximum results to return (default: 25)

        Returns:
            List of matching items with metadata
        """
        try:
            items = await zotero.search_items(query=query, limit=limit)
            results = []
            for item in items:
                data = item.get("data", item)
                if data.get("itemType") == "attachment":
                    continue  # Skip attachments
                results.append({
                    "key": item.get("key"),
                    "title": data.get("title", ""),
                    "itemType": data.get("itemType", ""),
                    "date": data.get("date", ""),
                    "creators": _format_creators(data.get("creators", [])),
                    "DOI": data.get("DOI", ""),
                })
            return {
                "count": len(results),
                "query": query,
                "items": results,
            }
        except (ZoteroConnectionError, ZoteroAPIError) as e:
            return {"count": 0, "query": query, "items": [], "error": str(e)}

    @mcp.tool()
    async def get_item(key: str) -> dict[str, Any]:
        """
        📖 Get detailed item by key

        取得單一文獻的完整資料

        Args:
            key: Zotero item key (e.g., "ABC12345")

        Returns:
            Full item metadata
        """
        try:
            item = await zotero.get_item(key)
            data = item.get("data", item)
            return {
                "found": True,
                "item": {
                    "key": item.get("key"),
                    "itemType": data.get("itemType", ""),
                    "title": data.get("title", ""),
                    "creators": data.get("creators", []),
                    "date": data.get("date", ""),
                    "DOI": data.get("DOI", ""),
                    "url": data.get("url", ""),
                    "abstract": data.get("abstractNote", ""),
                    "publicationTitle": data.get("publicationTitle", ""),
                    "volume": data.get("volume", ""),
                    "issue": data.get("issue", ""),
                    "pages": data.get("pages", ""),
                    "tags": [t.get("tag", t) if isinstance(t, dict) else t for t in data.get("tags", [])],
                    "collections": data.get("collections", []),
                },
            }
        except ZoteroAPIError as e:
            if e.status_code == 404:
                return {"found": False, "error": f"Item '{key}' not found"}
            return {"found": False, "error": str(e)}
        except ZoteroConnectionError as e:
            return {"found": False, "error": str(e)}

    @mcp.tool()
    async def list_items(
        limit: int = 20,
        collection_key: str | None = None,
    ) -> dict[str, Any]:
        """
        📋 List recent items

        列出最近的文獻

        Args:
            limit: Maximum items to return (default: 20)
            collection_key: Optional - filter by collection

        Returns:
            List of items with basic metadata
        """
        try:
            if collection_key:
                items = await zotero.get_collection_items(collection_key, limit=limit)
            else:
                items = await zotero.get_items(limit=limit)

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
                "count": len(results),
                "items": results,
            }
        except (ZoteroConnectionError, ZoteroAPIError) as e:
            return {"count": 0, "items": [], "error": str(e)}

    @mcp.tool()
    async def list_tags() -> dict[str, Any]:
        """
        🏷️ List all tags

        列出所有標籤

        Returns:
            List of tags
        """
        try:
            tags = await zotero.get_tags()
            tag_list = [t.get("tag", str(t)) for t in tags]
            return {
                "count": len(tag_list),
                "tags": tag_list[:100],  # Limit to first 100
            }
        except (ZoteroConnectionError, ZoteroAPIError) as e:
            return {"count": 0, "tags": [], "error": str(e)}

    @mcp.tool()
    async def get_item_types() -> dict[str, Any]:
        """
        📝 Get available item types

        取得可用的文獻類型

        Returns:
            List of item types (journalArticle, book, etc.)
        """
        try:
            types = await zotero.get_item_types()
            return {
                "count": len(types),
                "itemTypes": [t.get("itemType", str(t)) for t in types],
            }
        except (ZoteroConnectionError, ZoteroAPIError) as e:
            return {"count": 0, "itemTypes": [], "error": str(e)}

    logger.info("Basic read tools registered (search_items, get_item, list_items, list_tags, get_item_types)")
