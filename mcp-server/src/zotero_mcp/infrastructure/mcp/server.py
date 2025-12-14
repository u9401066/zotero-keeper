"""
Zotero Keeper MCP Server

A Model Context Protocol server for managing local Zotero libraries.
Provides read operations via Zotero Local API and write operations via Connector API.

Usage:
    # Development mode with MCP inspector
    mcp dev src/zotero_mcp/infrastructure/mcp/server.py

    # Direct execution (stdio transport, localhost)
    python -m zotero_mcp

    # With remote Zotero host
    ZOTERO_HOST=<your-zotero-ip> python -m zotero_mcp
"""

import logging
from typing import Any

from mcp.server.fastmcp import FastMCP

from ..zotero_client.client import ZoteroAPIError, ZoteroClient, ZoteroConfig, ZoteroConnectionError
from .batch_tools import is_batch_import_available, register_batch_tools
from .config import McpServerConfig, default_config
from .interactive_tools import register_interactive_save_tools
from .pubmed_tools import is_pubmed_available, register_pubmed_tools
from .resources import register_resources
from .saved_search_tools import register_saved_search_tools
from .search_tools import is_search_tools_available, register_search_tools
from .smart_tools import register_smart_tools

logger = logging.getLogger(__name__)


class ZoteroKeeperServer:
    """
    MCP Server for Zotero integration

    Provides MCP tools for:
    - Reading items, collections, tags from local Zotero
    - Adding new references via Connector API
    """

    def __init__(self, config: McpServerConfig | None = None):
        self._config = config or default_config

        # Create FastMCP server
        self._mcp = FastMCP(
            name=self._config.name,
            instructions=self._config.instructions,
        )

        # Create Zotero client
        zotero_config = ZoteroConfig(
            host=self._config.zotero.host,
            port=self._config.zotero.port,
            timeout=self._config.zotero.timeout,
        )
        self._zotero = ZoteroClient(zotero_config)

        # Register tools
        self._register_tools()

        # Register MCP Resources (read-only browsable data)
        register_resources(self._mcp, self._zotero)
        logger.info("MCP Resources enabled (zotero://collections, zotero://items, zotero://tags, zotero://searches)")

        # Register Smart tools helpers (internal functions only, no tools)
        register_smart_tools(self._mcp, self._zotero)
        # Note: Smart tools (check_duplicate, validate_reference, etc.) have been
        # integrated into interactive_save/quick_save - see interactive_tools.py

        # Register Interactive Save tools (with elicitation support)
        # These are the MAIN save tools now! (方案 A 精簡後)
        register_interactive_save_tools(self._mcp, self._zotero)
        logger.info("Save tools enabled (interactive_save, quick_save) 🎯 Uses MCP Elicitation + Auto-fetch metadata!")

        # Register Saved Search tools (Local API exclusive feature!)
        register_saved_search_tools(self._mcp, self._zotero)
        logger.info("Saved Search tools enabled (list_saved_searches, run_saved_search) 🌟 Local API exclusive!")

        # Register Integrated Search tools (PubMed + Zotero filtering)
        if is_search_tools_available():
            register_search_tools(self._mcp, self._zotero)
            logger.info("Integrated search enabled (search_pubmed_exclude_owned, check_articles_owned)")
        else:
            logger.info("Integrated search disabled (install with: pip install 'zotero-keeper[pubmed]')")

        # Register PubMed tools if available
        if is_pubmed_available():
            register_pubmed_tools(self._mcp, self._zotero)
            logger.info("PubMed import enabled (import_ris_to_zotero, import_from_pmids)")
        else:
            logger.info("PubMed integration disabled (install with: pip install 'zotero-keeper[pubmed]')")

        # Register Batch Import tools (requires pubmed-search submodule)
        if is_batch_import_available():
            register_batch_tools(self._mcp, self._zotero)
            logger.info("Batch import enabled (batch_import_from_pubmed)")
        else:
            logger.info("Batch import disabled (pubmed-search submodule not available)")

        logger.info("Zotero Keeper MCP Server initialized")
        logger.info(f"Zotero endpoint: {zotero_config.base_url}")

    @property
    def mcp(self) -> FastMCP:
        """Get the FastMCP server instance"""
        return self._mcp

    def _register_tools(self):
        """Register all MCP tools"""

        # ==================== Connection ====================

        @self._mcp.tool()
        async def check_connection() -> dict[str, Any]:
            """
            🔌 Check connection to Zotero

            Verifies that Zotero is running and accessible.

            Returns:
                Connection status and endpoint info
            """
            try:
                is_running = await self._zotero.ping()
                return {
                    "connected": is_running,
                    "endpoint": self._zotero.config.base_url,
                    "message": "Zotero is running" if is_running else "Cannot connect to Zotero",
                }
            except ZoteroConnectionError as e:
                return {
                    "connected": False,
                    "endpoint": self._zotero.config.base_url,
                    "message": str(e),
                }

        # ==================== Read: Items ====================

        @self._mcp.tool()
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
                items = await self._zotero.search_items(query=query, limit=limit)
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

        @self._mcp.tool()
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
                item = await self._zotero.get_item(key)
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

        @self._mcp.tool()
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
                    items = await self._zotero.get_collection_items(collection_key, limit=limit)
                else:
                    items = await self._zotero.get_items(limit=limit)

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

        # ==================== Read: Collections ====================

        @self._mcp.tool()
        async def list_collections() -> dict[str, Any]:
            """
            📁 List all collections

            列出所有收藏夾

            Returns:
                List of collections with item counts
            """
            try:
                collections = await self._zotero.get_collections()
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

        @self._mcp.tool()
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
                col = await self._zotero.get_collection(key)
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

        @self._mcp.tool()
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
                items = await self._zotero.get_collection_items(collection_key, limit=limit)
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

        @self._mcp.tool()
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
                tree = await self._zotero.get_collection_tree()
                return {
                    "count": len(tree),
                    "tree": tree,
                }
            except (ZoteroConnectionError, ZoteroAPIError) as e:
                return {"count": 0, "tree": [], "error": str(e)}

        @self._mcp.tool()
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
                    parent = await self._zotero.find_collection_by_name(parent_name)
                    if parent:
                        parent_key = parent.get("key")
                    else:
                        return {
                            "found": False,
                            "error": f"Parent collection '{parent_name}' not found",
                        }

                col = await self._zotero.find_collection_by_name(name, parent_key)
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
                    all_collections = await self._zotero.get_collections()
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

        # ==================== Read: Tags ====================

        @self._mcp.tool()
        async def list_tags() -> dict[str, Any]:
            """
            🏷️ List all tags

            列出所有標籤

            Returns:
                List of tags
            """
            try:
                tags = await self._zotero.get_tags()
                tag_list = [t.get("tag", str(t)) for t in tags]
                return {
                    "count": len(tag_list),
                    "tags": tag_list[:100],  # Limit to first 100
                }
            except (ZoteroConnectionError, ZoteroAPIError) as e:
                return {"count": 0, "tags": [], "error": str(e)}

        # ==================== Read: Schema ====================

        @self._mcp.tool()
        async def get_item_types() -> dict[str, Any]:
            """
            📝 Get available item types

            取得可用的文獻類型

            Returns:
                List of item types (journalArticle, book, etc.)
            """
            try:
                types = await self._zotero.get_item_types()
                return {
                    "count": len(types),
                    "itemTypes": [t.get("itemType", str(t)) for t in types],
                }
            except (ZoteroConnectionError, ZoteroAPIError) as e:
                return {"count": 0, "itemTypes": [], "error": str(e)}

        # ==================== Write: Use interactive_save or quick_save ====================
        # Note: add_reference and create_item have been removed in favor of:
        # - interactive_save: Interactive collection selection with elicitation
        # - quick_save: Direct save with optional collection specification
        # See interactive_tools.py for implementation

    def run(self, transport: str = "stdio"):
        """Run the MCP server"""
        logger.info(f"Starting Zotero Keeper MCP Server ({transport} transport)")
        self._mcp.run(transport=transport)


# =============================================================================
# Helper Functions
# =============================================================================

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


# =============================================================================
# Module-level Access
# =============================================================================

_server: ZoteroKeeperServer | None = None


def get_server() -> ZoteroKeeperServer:
    """Get or create the server instance"""
    global _server
    if _server is None:
        _server = ZoteroKeeperServer()
    return _server


def create_server(config: McpServerConfig | None = None) -> ZoteroKeeperServer:
    """Create a new server instance with custom config"""
    global _server
    _server = ZoteroKeeperServer(config)
    return _server


# Export mcp instance for FastMCP compatibility
mcp = property(lambda self: get_server().mcp)


# =============================================================================
# Entry Point
# =============================================================================

def main():
    """Run the MCP server"""
    import sys

    transport = "stdio"
    if "--transport" in sys.argv:
        idx = sys.argv.index("--transport")
        if idx + 1 < len(sys.argv):
            transport = sys.argv[idx + 1]

    get_server().run(transport)


if __name__ == "__main__":
    main()
