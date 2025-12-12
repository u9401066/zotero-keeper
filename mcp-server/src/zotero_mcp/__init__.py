"""
Zotero Keeper - MCP Server for Zotero Integration

A MCP server that enables AI agents to read and write bibliographic references
to local Zotero libraries using Zotero's built-in APIs.
"""

__version__ = "1.2.0"

# Lazy imports to avoid circular dependencies
def get_server():
    """Get the MCP server instance"""
    from .infrastructure.mcp.server import get_server as _get_server
    return _get_server()

def create_server(config=None):
    """Create a new MCP server instance"""
    from .infrastructure.mcp.server import create_server as _create_server
    return _create_server(config)

__all__ = ["get_server", "create_server", "__version__"]
