"""
MCP Resources for Zotero Keeper

Expose Zotero data as browsable resources using MCP Resource protocol.
This allows AI clients to browse collections and items without explicit tool calls.

Resources:
- zotero://collections - List all collections
- zotero://collections/{key} - Get collection details
- zotero://collections/{key}/items - Get items in a collection
- zotero://items - List recent items  
- zotero://items/{key} - Get item details
- zotero://tags - List all tags
- zotero://searches - List saved searches
"""

import json
import logging
from typing import Any

logger = logging.getLogger(__name__)


def register_resources(mcp, zotero_client):
    """
    Register MCP Resources for Zotero data access.
    
    Resources provide a read-only browsable interface to Zotero data,
    reducing the need for explicit tool calls for read operations.
    """
    
    # ==================== Collections ====================
    
    @mcp.resource("zotero://collections")
    async def list_collections_resource() -> str:
        """
        📁 Browse all Zotero collections
        
        列出所有收藏夾（用於瀏覽和選擇）
        
        Returns JSON with all collections including:
        - key: Collection identifier
        - name: Collection name
        - parentKey: Parent collection (if nested)
        - itemCount: Number of items
        """
        try:
            collections = await zotero_client.get_collections()
            result = []
            for col in collections:
                data = col.get("data", col)
                result.append({
                    "key": col.get("key"),
                    "name": data.get("name", ""),
                    "parentKey": data.get("parentCollection"),
                    "itemCount": data.get("numItems", 0),
                })
            return json.dumps({
                "type": "collections",
                "count": len(result),
                "collections": result,
            }, ensure_ascii=False, indent=2)
        except Exception as e:
            return json.dumps({"error": str(e)})
    
    @mcp.resource("zotero://collections/tree")
    async def get_collection_tree_resource() -> str:
        """
        🌳 Browse collections as a hierarchical tree
        
        以樹狀結構瀏覽收藏夾（含子收藏夾）
        """
        try:
            tree = await zotero_client.get_collection_tree()
            return json.dumps({
                "type": "collection_tree",
                "count": len(tree),
                "tree": tree,
            }, ensure_ascii=False, indent=2)
        except Exception as e:
            return json.dumps({"error": str(e)})
    
    @mcp.resource("zotero://collections/{key}")
    async def get_collection_resource(key: str) -> str:
        """
        📁 Get details of a specific collection
        
        取得特定收藏夾的詳細資訊
        """
        try:
            col = await zotero_client.get_collection(key)
            data = col.get("data", col)
            return json.dumps({
                "type": "collection",
                "key": col.get("key"),
                "name": data.get("name", ""),
                "parentKey": data.get("parentCollection"),
                "itemCount": data.get("numItems", 0),
            }, ensure_ascii=False, indent=2)
        except Exception as e:
            return json.dumps({"error": str(e), "key": key})
    
    @mcp.resource("zotero://collections/{key}/items")
    async def get_collection_items_resource(key: str) -> str:
        """
        📚 Browse items in a specific collection
        
        瀏覽特定收藏夾內的文獻
        """
        try:
            items = await zotero_client.get_collection_items(key, limit=50)
            result = []
            for item in items:
                data = item.get("data", item)
                if data.get("itemType") == "attachment":
                    continue
                result.append({
                    "key": item.get("key"),
                    "title": data.get("title", ""),
                    "itemType": data.get("itemType", ""),
                    "date": data.get("date", ""),
                    "creators": _format_creators_short(data.get("creators", [])),
                })
            return json.dumps({
                "type": "collection_items",
                "collection_key": key,
                "count": len(result),
                "items": result,
            }, ensure_ascii=False, indent=2)
        except Exception as e:
            return json.dumps({"error": str(e), "collection_key": key})
    
    # ==================== Items ====================
    
    @mcp.resource("zotero://items")
    async def list_items_resource() -> str:
        """
        📋 Browse recent items in library
        
        瀏覽最近的文獻（前50筆）
        """
        try:
            items = await zotero_client.get_items(limit=50)
            result = []
            for item in items:
                data = item.get("data", item)
                if data.get("itemType") == "attachment":
                    continue
                result.append({
                    "key": item.get("key"),
                    "title": data.get("title", ""),
                    "itemType": data.get("itemType", ""),
                    "date": data.get("date", ""),
                    "creators": _format_creators_short(data.get("creators", [])),
                })
            return json.dumps({
                "type": "items",
                "count": len(result),
                "items": result,
            }, ensure_ascii=False, indent=2)
        except Exception as e:
            return json.dumps({"error": str(e)})
    
    @mcp.resource("zotero://items/{key}")
    async def get_item_resource(key: str) -> str:
        """
        📖 Get detailed metadata for a specific item
        
        取得特定文獻的完整資料
        """
        try:
            item = await zotero_client.get_item(key)
            data = item.get("data", item)
            return json.dumps({
                "type": "item",
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
            }, ensure_ascii=False, indent=2)
        except Exception as e:
            return json.dumps({"error": str(e), "key": key})
    
    # ==================== Tags ====================
    
    @mcp.resource("zotero://tags")
    async def list_tags_resource() -> str:
        """
        🏷️ Browse all tags in library
        
        瀏覽所有標籤
        """
        try:
            tags = await zotero_client.get_tags()
            tag_list = [t.get("tag", str(t)) for t in tags]
            return json.dumps({
                "type": "tags",
                "count": len(tag_list),
                "tags": tag_list[:100],  # Limit to first 100
            }, ensure_ascii=False, indent=2)
        except Exception as e:
            return json.dumps({"error": str(e)})
    
    # ==================== Saved Searches ====================
    
    @mcp.resource("zotero://searches")
    async def list_searches_resource() -> str:
        """
        🔍 Browse saved searches
        
        瀏覽已儲存的搜尋條件（Local API 獨有功能！）
        """
        try:
            searches = await zotero_client.get_searches()
            result = []
            for search in searches:
                data = search.get("data", search)
                result.append({
                    "key": search.get("key"),
                    "name": data.get("name", ""),
                    "conditions": data.get("conditions", []),
                })
            return json.dumps({
                "type": "saved_searches",
                "count": len(result),
                "note": "Use run_saved_search tool to execute these searches",
                "searches": result,
            }, ensure_ascii=False, indent=2)
        except Exception as e:
            return json.dumps({"error": str(e)})
    
    @mcp.resource("zotero://searches/{key}")
    async def get_search_resource(key: str) -> str:
        """
        🔍 Get details of a specific saved search
        
        取得特定已儲存搜尋的詳細條件
        """
        try:
            search = await zotero_client.get_search(key)
            data = search.get("data", search)
            return json.dumps({
                "type": "saved_search",
                "key": search.get("key"),
                "name": data.get("name", ""),
                "conditions": data.get("conditions", []),
                "hint": "Use run_saved_search tool to execute this search",
            }, ensure_ascii=False, indent=2)
        except Exception as e:
            return json.dumps({"error": str(e), "key": key})
    
    # ==================== Schema ====================
    
    @mcp.resource("zotero://schema/item-types")
    async def get_item_types_resource() -> str:
        """
        📝 Browse available item types
        
        瀏覽可用的文獻類型（journalArticle, book 等）
        """
        try:
            types = await zotero_client.get_item_types()
            return json.dumps({
                "type": "item_types",
                "count": len(types),
                "itemTypes": [t.get("itemType", str(t)) for t in types],
            }, ensure_ascii=False, indent=2)
        except Exception as e:
            return json.dumps({"error": str(e)})
    
    logger.info("MCP Resources registered (zotero://collections, zotero://items, zotero://tags, zotero://searches)")


# =============================================================================
# Helper Functions
# =============================================================================

def _format_creators_short(creators: list[dict]) -> str:
    """Format creators list as short string"""
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
        result += f" et al."
    return result
