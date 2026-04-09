"""
Zotero Keeper MCP Server.

A Model Context Protocol server for managing local Zotero libraries.
Provides read operations via Zotero Local API and write operations via Connector API.

Responsibility split when collaborating with pubmed-search-mcp:
        - pubmed-search-mcp owns search, discovery, export, and citation metrics
        - zotero-keeper owns local library queries, collection choice, duplicate checks,
            and importing articles into Zotero
        - legacy PubMed bridge tools remain available only via
            ZOTERO_KEEPER_ENABLE_LEGACY_PUBMED_TOOLS=1

Usage:
        # Development mode with MCP inspector
        mcp dev src/zotero_mcp/infrastructure/mcp/server.py

        # Direct execution (stdio transport, localhost)
    uv run python -m zotero_mcp

        # With remote Zotero host
    ZOTERO_HOST=<your-zotero-ip> uv run python -m zotero_mcp
"""

import logging
from typing import Any, Literal, cast

from mcp.server.fastmcp import FastMCP

from ..zotero_client.client import ZoteroClient, ZoteroConfig, ZoteroConnectionError
from .analytics_tools import register_analytics_tools
from .attachment_tools import register_attachment_tools
from .basic_read_tools import register_basic_read_tools
from .batch_tools import is_batch_import_available, register_batch_tools
from .collection_tools import register_collection_tools
from .config import McpServerConfig, default_config
from .interactive_tools import register_interactive_save_tools
from .pubmed_tools import is_pubmed_available, register_pubmed_tools
from .resources import register_resources
from .saved_search_tools import register_saved_search_tools
from .search_tools import is_search_tools_available, register_search_tools
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

        # Register Interactive Save tools (with elicitation support)
        register_interactive_save_tools(self._mcp, self._zotero)
        logger.info("Save tools enabled (interactive_save, quick_save) 🎯 Uses MCP Elicitation + Auto-fetch metadata!")

        # Register Saved Search tools (Local API exclusive feature!)
        register_saved_search_tools(self._mcp, self._zotero)
        logger.info("Saved Search tools enabled (list_saved_searches, run_saved_search) 🌟 Local API exclusive!")

        # Register search tools. Default mode keeps PubMed search/discovery in pubmed-search-mcp.
        register_search_tools(
            self._mcp,
            self._zotero,
            enable_pubmed_bridge_tools=self._config.enable_legacy_pubmed_tools,
        )
        logger.info("Search tools enabled (advanced_search, check_articles_owned)")
        if self._config.enable_legacy_pubmed_tools:
            if is_search_tools_available():
                logger.info("Legacy PubMed bridge enabled (search_pubmed_exclude_owned)")
            else:
                logger.info("Legacy PubMed bridge requested but pubmed extra is unavailable")
        else:
            logger.info("Collaboration-safe mode: PubMed search/discovery stays in pubmed-search-mcp")

        # Register legacy PubMed import tools only when explicitly requested.
        if self._config.enable_legacy_pubmed_tools:
            if is_pubmed_available():
                register_pubmed_tools(self._mcp, self._zotero)
                logger.info("Legacy PubMed import bridge enabled (import_ris_to_zotero, import_from_pmids, quick_import_pmids)")
            else:
                logger.info("Legacy PubMed import bridge requested but pubmed extra is unavailable")

            if is_batch_import_available():
                register_batch_tools(self._mcp, self._zotero)
                logger.info("Legacy batch PubMed import enabled (batch_import_from_pubmed)")
            else:
                logger.info("Legacy batch PubMed import requested but pubmed-search backend is unavailable")
        else:
            logger.info("Legacy PubMed import tools disabled by default; use import_articles for PubMed → Zotero handoff")

        # Register Analytics tools (library stats, orphan detection)
        register_analytics_tools(self._mcp, self._zotero)
        logger.info("Analytics tools enabled (get_library_stats, find_orphan_items)")

        # Register Unified Import tool (single entry point for all imports)
        register_unified_import_tools(self._mcp, self._zotero)
        logger.info("Unified import enabled (import_articles) ⭐ Single public PubMed → Zotero import entry")

        # Register Attachment & Fulltext tools (PDF access)
        register_attachment_tools(self._mcp, self._zotero)
        logger.info("Attachment tools enabled (get_item_attachments, get_item_fulltext)")

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
                result: dict[str, Any] = {
                    "connected": is_running,
                    "endpoint": self._zotero.config.base_url,
                    "message": "Zotero is running" if is_running else "Cannot connect to Zotero",
                }
                if not is_running:
                    result["hint"] = "Zotero responded but returned unexpected content. Make sure Zotero 7 is running (not just Zotero 6)."
                return result
            except ZoteroConnectionError as e:
                return {
                    "connected": False,
                    "endpoint": self._zotero.config.base_url,
                    "message": str(e),
                    "hint": "Check if Zotero is running and the port is accessible.",
                }

    def run(self, transport: Literal["stdio", "sse", "streamable-http"] = "stdio"):
        """Run the MCP server"""
        logger.info(f"Starting Zotero Keeper MCP Server ({transport} transport)")
        self._mcp.run(transport=cast("Literal['stdio', 'sse', 'streamable-http']", transport))


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
    global _server, mcp
    _server = ZoteroKeeperServer(config)
    mcp = _server.mcp
    return _server


# Export the concrete FastMCP instance for `mcp dev .../server.py` compatibility.
mcp: FastMCP = get_server().mcp


# =============================================================================
# Entry Point
# =============================================================================


def main():
    """Run the MCP server"""
    import sys

    transport: Literal["stdio", "sse", "streamable-http"] = "stdio"
    if "--transport" in sys.argv:
        idx = sys.argv.index("--transport")
        if idx + 1 < len(sys.argv):
            requested_transport = sys.argv[idx + 1]
            if requested_transport not in {"stdio", "sse", "streamable-http"}:
                raise ValueError(f"Unsupported transport: {requested_transport}")
            transport = cast("Literal['stdio', 'sse', 'streamable-http']", requested_transport)

    get_server().run(transport)


if __name__ == "__main__":
    main()
