"""
Zotero MCP Server - Domain Driven Design Architecture

A FastMCP server that bridges MCP clients with local Zotero desktop application.
"""

__version__ = "0.1.0"

from .interface.server import create_mcp_server, mcp

__all__ = ["create_mcp_server", "mcp", "__version__"]
