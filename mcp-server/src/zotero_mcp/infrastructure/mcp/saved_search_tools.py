"""
Saved Search Tools - Local API Exclusive Feature

🌟 這是 Zotero Local API 獨有的功能！
Web API 只能讀取 Saved Search 的 metadata，無法實際執行搜尋。
Local API 可以執行 Saved Search 並返回符合條件的文獻。

使用情境：
- 使用者在 Zotero 預設複雜的搜尋條件（如：缺少 PDF、最近新增、未讀等）
- AI 可以直接執行這些搜尋，幫助使用者管理文獻庫
"""

import logging
from typing import Any, Optional

from mcp.server.fastmcp import FastMCP

from ..zotero_client.client import ZoteroClient, ZoteroConnectionError, ZoteroAPIError

logger = logging.getLogger(__name__)


def register_saved_search_tools(mcp: FastMCP, zotero: ZoteroClient) -> None:
    """
    Register Saved Search MCP tools.
    
    These tools leverage the Local API's unique ability to execute saved searches.
    """
    
    @mcp.tool()
    async def list_saved_searches() -> dict[str, Any]:
        """
        📋 List all saved searches in Zotero
        
        列出所有已儲存的搜尋條件
        
        🌟 Local API 獨有功能！
        
        Returns:
            List of saved searches with names and keys
            
        Example response:
            {
                "count": 3,
                "searches": [
                    {"key": "ABC123", "name": "Missing PDF", "conditions": [...]},
                    {"key": "DEF456", "name": "Unread Papers", "conditions": [...]},
                    {"key": "GHI789", "name": "Recent Additions", "conditions": [...]}
                ]
            }
        """
        try:
            searches = await zotero.get_searches()
            results = []
            for search in searches:
                data = search.get("data", search)
                results.append({
                    "key": search.get("key"),
                    "name": data.get("name", ""),
                    "conditions": data.get("conditions", []),
                })
            return {
                "count": len(results),
                "searches": results,
                "note": "Use run_saved_search with a key or name to execute any search",
            }
        except (ZoteroConnectionError, ZoteroAPIError) as e:
            return {"count": 0, "searches": [], "error": str(e)}
    
    @mcp.tool()
    async def run_saved_search(
        search_key: Optional[str] = None,
        search_name: Optional[str] = None,
        limit: int = 50,
    ) -> dict[str, Any]:
        """
        ▶️ Execute a saved search and return matching items
        
        執行已儲存的搜尋條件並返回符合的文獻
        
        🌟 這是 Local API 獨有的功能！Web API 無法做到這點。
        
        Args:
            search_key: The saved search key (e.g., "ABC12345")
            search_name: OR the saved search name (e.g., "Missing PDF")
            limit: Maximum items to return (default: 50)
            
        Returns:
            List of items matching the saved search conditions
            
        Example:
            # By key
            run_saved_search(search_key="ABC12345")
            
            # By name (case-insensitive)
            run_saved_search(search_name="Missing PDF")
            
        Use cases:
            - "Which papers don't have PDFs?" → run_saved_search(search_name="Missing PDF")
            - "What did I add this week?" → run_saved_search(search_name="Recent Additions")
            - "Show unread papers" → run_saved_search(search_name="Unread")
        """
        try:
            # Resolve search key
            key_to_use = search_key
            search_info = None
            
            if not key_to_use and search_name:
                # Find by name
                found = await zotero.find_search_by_name(search_name)
                if found:
                    key_to_use = found.get("key")
                    search_info = found.get("data", found)
                else:
                    return {
                        "success": False,
                        "error": f"Saved search '{search_name}' not found",
                        "hint": "Use list_saved_searches to see available searches",
                    }
            
            if not key_to_use:
                return {
                    "success": False,
                    "error": "Please provide either search_key or search_name",
                }
            
            # Get search info if we don't have it yet
            if not search_info:
                try:
                    search_obj = await zotero.get_search(key_to_use)
                    search_info = search_obj.get("data", search_obj)
                except ZoteroAPIError:
                    search_info = {"name": key_to_use}
            
            # Execute the search
            items = await zotero.execute_search(key_to_use, limit=limit)
            
            # Format results
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
                "success": True,
                "search": {
                    "key": key_to_use,
                    "name": search_info.get("name", ""),
                    "conditions": search_info.get("conditions", []),
                },
                "count": len(results),
                "items": results,
                "note": "🌟 This feature is exclusive to Local API!",
            }
            
        except (ZoteroConnectionError, ZoteroAPIError) as e:
            return {
                "success": False,
                "error": str(e),
            }
    
    @mcp.tool()
    async def get_saved_search_details(search_key: str) -> dict[str, Any]:
        """
        🔍 Get details of a specific saved search
        
        取得特定已儲存搜尋的詳細條件
        
        Args:
            search_key: The saved search key (e.g., "ABC12345")
            
        Returns:
            Saved search details including all conditions
            
        Example response:
            {
                "found": true,
                "search": {
                    "key": "ABC12345",
                    "name": "Missing PDF",
                    "conditions": [
                        {"condition": "attachment", "operator": "isNot", "value": "PDF"}
                    ]
                }
            }
        """
        try:
            search = await zotero.get_search(search_key)
            data = search.get("data", search)
            return {
                "found": True,
                "search": {
                    "key": search.get("key"),
                    "name": data.get("name", ""),
                    "conditions": data.get("conditions", []),
                },
            }
        except ZoteroAPIError as e:
            if e.status_code == 404:
                return {"found": False, "error": f"Saved search '{search_key}' not found"}
            return {"found": False, "error": str(e)}
        except ZoteroConnectionError as e:
            return {"found": False, "error": str(e)}


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
