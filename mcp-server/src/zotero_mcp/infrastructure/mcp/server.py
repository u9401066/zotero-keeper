"""
Zotero Keeper MCP Server

A Model Context Protocol server for managing local Zotero libraries.
Provides read operations via Zotero Local API and write operations via Connector API.

Usage:
    # Development mode with MCP inspector
    mcp dev src/zotero_mcp/infrastructure/mcp/server.py
    
    # Direct execution (stdio transport)
    python -m zotero_mcp

    # With custom Zotero host
    ZOTERO_HOST=YOUR_ZOTERO_HOST python -m zotero_mcp
"""

import logging
import os
from typing import Any, Optional

from mcp.server.fastmcp import FastMCP

from ..zotero_client.client import ZoteroClient, ZoteroConfig, ZoteroConnectionError, ZoteroAPIError
from ...domain.entities.reference import Reference, Creator, ItemType
from ...domain.entities.collection import Collection
from .config import McpServerConfig, default_config
from .pubmed_tools import register_pubmed_tools, is_pubmed_available
from .smart_tools import register_smart_tools
from .search_tools import register_search_tools, is_search_tools_available


logger = logging.getLogger(__name__)


class ZoteroKeeperServer:
    """
    MCP Server for Zotero integration
    
    Provides MCP tools for:
    - Reading items, collections, tags from local Zotero
    - Adding new references via Connector API
    """
    
    def __init__(self, config: Optional[McpServerConfig] = None):
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
        
        # Register Smart tools (duplicate detection, validation)
        register_smart_tools(self._mcp, self._zotero)
        logger.info("Smart tools enabled (check_duplicate, validate_reference, smart_add_reference)")
        
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
        
        logger.info(f"Zotero Keeper MCP Server initialized")
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
            collection_key: Optional[str] = None,
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
        
        # ==================== Write: Add Reference ====================
        
        @self._mcp.tool()
        async def add_reference(
            title: str,
            item_type: str = "journalArticle",
            authors: Optional[list[str]] = None,
            date: Optional[str] = None,
            doi: Optional[str] = None,
            url: Optional[str] = None,
            abstract: Optional[str] = None,
            publication_title: Optional[str] = None,
            volume: Optional[str] = None,
            issue: Optional[str] = None,
            pages: Optional[str] = None,
            publisher: Optional[str] = None,
            tags: Optional[list[str]] = None,
        ) -> dict[str, Any]:
            """
            ➕ Add a new reference to Zotero
            
            新增書目參考文獻到 Zotero
            
            Args:
                title: Reference title (required)
                item_type: Type - journalArticle, book, bookSection, conferencePaper, thesis, webpage, etc.
                authors: List of author names ["First Last", "First Last"]
                date: Publication date (2024, 2024-01, 2024-01-15)
                doi: Digital Object Identifier
                url: Web URL
                abstract: Abstract text
                publication_title: Journal/book name
                volume: Volume number
                issue: Issue number
                pages: Page range (e.g., "1-10")
                publisher: Publisher name
                tags: List of tags
                
            Returns:
                Success status and created item info
                
            Example:
                add_reference(
                    title="Deep Learning for NLP",
                    item_type="journalArticle",
                    authors=["Yann LeCun", "Geoffrey Hinton"],
                    date="2024",
                    doi="10.1234/example",
                    publication_title="Nature"
                )
            """
            try:
                # Build item data
                item: dict[str, Any] = {
                    "itemType": item_type,
                    "title": title,
                }
                
                # Add creators
                if authors:
                    item["creators"] = []
                    for author in authors:
                        parts = author.strip().split(maxsplit=1)
                        if len(parts) == 1:
                            item["creators"].append({
                                "lastName": parts[0],
                                "creatorType": "author",
                            })
                        else:
                            item["creators"].append({
                                "firstName": parts[0],
                                "lastName": parts[1],
                                "creatorType": "author",
                            })
                
                # Add optional fields
                if date:
                    item["date"] = date
                if doi:
                    item["DOI"] = doi
                if url:
                    item["url"] = url
                if abstract:
                    item["abstractNote"] = abstract
                if publication_title:
                    item["publicationTitle"] = publication_title
                if volume:
                    item["volume"] = volume
                if issue:
                    item["issue"] = issue
                if pages:
                    item["pages"] = pages
                if publisher:
                    item["publisher"] = publisher
                if tags:
                    item["tags"] = [{"tag": t} for t in tags]
                
                # Save via Connector API
                result = await self._zotero.save_items([item])
                
                return {
                    "success": True,
                    "message": f"Reference '{title}' added successfully",
                    "result": result,
                }
            except (ZoteroConnectionError, ZoteroAPIError) as e:
                return {
                    "success": False,
                    "message": f"Failed to add reference: {str(e)}",
                }
        
        @self._mcp.tool()
        async def create_item(
            item_type: str,
            title: str,
            creators: Optional[list[dict[str, str]]] = None,
            **fields,
        ) -> dict[str, Any]:
            """
            ➕ Create item with full metadata
            
            使用完整元資料建立文獻（進階用法）
            
            Args:
                item_type: Type (journalArticle, book, etc.)
                title: Item title
                creators: Full creator dicts [{"firstName": "...", "lastName": "...", "creatorType": "author"}]
                **fields: Any Zotero fields (date, DOI, abstractNote, publicationTitle, etc.)
                
            Returns:
                Success status and result
                
            Example:
                create_item(
                    item_type="journalArticle",
                    title="My Paper",
                    creators=[{"firstName": "John", "lastName": "Doe", "creatorType": "author"}],
                    date="2024",
                    DOI="10.1234/example"
                )
            """
            try:
                result = await self._zotero.create_item(
                    item_type=item_type,
                    title=title,
                    creators=creators,
                    **fields,
                )
                return {
                    "success": True,
                    "message": f"Item '{title}' created successfully",
                    "result": result,
                }
            except (ZoteroConnectionError, ZoteroAPIError) as e:
                return {
                    "success": False,
                    "message": f"Failed to create item: {str(e)}",
                }
    
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

_server: Optional[ZoteroKeeperServer] = None


def get_server() -> ZoteroKeeperServer:
    """Get or create the server instance"""
    global _server
    if _server is None:
        _server = ZoteroKeeperServer()
    return _server


def create_server(config: Optional[McpServerConfig] = None) -> ZoteroKeeperServer:
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
