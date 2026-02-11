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

from ..zotero_client.client import ZoteroClient, ZoteroConfig, ZoteroConnectionError
from .analytics_tools import register_analytics_tools
from .basic_read_tools import register_basic_read_tools
from .batch_tools import is_batch_import_available, register_batch_tools
from .collection_tools import register_collection_tools
from .config import McpServerConfig, default_config
from .interactive_tools import register_interactive_save_tools
from .pubmed_tools import is_pubmed_available, register_pubmed_tools
from .resources import register_resources
from .saved_search_tools import register_saved_search_tools
from .search_tools import is_search_tools_available, register_search_tools
from .smart_tools import register_smart_tools
from .unified_import_tools import register_unified_import_tools

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

        # Register all tools
        self._register_all_tools()

        logger.info("Zotero Keeper MCP Server initialized")
        logger.info(f"Zotero endpoint: {zotero_config.base_url}")

    @property
    def mcp(self) -> FastMCP:
        """Get the FastMCP server instance"""
        return self._mcp

    def _register_all_tools(self):
        """Register all MCP tools and resources"""
        # Connection check (simple, kept inline)
        self._register_connection_tool()

        # Register tool groups from separate modules
        register_basic_read_tools(self._mcp, self._zotero)
        register_collection_tools(self._mcp, self._zotero)

        # Register MCP Resources (read-only browsable data)
        register_resources(self._mcp, self._zotero)
        logger.info("MCP Resources enabled (zotero://collections, zotero://items, zotero://tags, zotero://searches)")

        # Register Smart tools helpers (internal functions only, no tools)
        register_smart_tools(self._mcp, self._zotero)

        # Register Interactive Save tools (with elicitation support)
        register_interactive_save_tools(self._mcp, self._zotero)
        logger.info("Save tools enabled (interactive_save, quick_save) 🎯 Uses MCP Elicitation + Auto-fetch metadata!")

        # Register Saved Search tools (Local API exclusive feature!)
        register_saved_search_tools(self._mcp, self._zotero)
        logger.info("Saved Search tools enabled (list_saved_searches, run_saved_search) 🌟 Local API exclusive!")

        # Register Integrated Search tools
        register_search_tools(self._mcp, self._zotero)
        logger.info("Search tools enabled (advanced_search)")
        if is_search_tools_available():
            logger.info("PubMed integration enabled (search_pubmed_exclude_owned, check_articles_owned)")
        else:
            logger.info("PubMed integration disabled (install with: uv pip install 'zotero-keeper[pubmed]')")

        # Register PubMed tools if available
        if is_pubmed_available():
            register_pubmed_tools(self._mcp, self._zotero)
            logger.info("PubMed import enabled (import_ris_to_zotero, import_from_pmids)")
        else:
            logger.info("PubMed integration disabled (install with: uv pip install 'zotero-keeper[pubmed]')")

        # Register Batch Import tools
        if is_batch_import_available():
            register_batch_tools(self._mcp, self._zotero)
            logger.info("Batch import enabled (batch_import_from_pubmed)")
        else:
            logger.info("Batch import disabled (pubmed-search submodule not available)")

        # Register Analytics tools (library stats, orphan detection)
        register_analytics_tools(self._mcp, self._zotero)
        logger.info("Analytics tools enabled (get_library_stats, find_orphan_items)")

        # Register Unified Import tool (single entry point for all imports)
        register_unified_import_tools(self._mcp, self._zotero)
        logger.info("Unified import enabled (import_articles) ⭐ One tool for all sources!")

    def _register_connection_tool(self):
        """Register connection check tool"""

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

    def _register_tools(self):
        """Register all MCP tools - DEPRECATED, use _register_all_tools()"""
        pass  # Kept for backwards compatibility, all tools moved to separate modules

    def run(self, transport: str = "stdio"):
        """Run the MCP server"""
        logger.info(f"Starting Zotero Keeper MCP Server ({transport} transport)")
        self._mcp.run(transport=transport)


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
