"""
Zotero Keeper MCP Server - Module Entry Point

Usage:
    # Local Zotero (default)
    uv run python -m zotero_mcp

Security:
    Keep Zotero's unauthenticated Local/Connector API on loopback. Do not expose
    or forward port 23119 for remote access.
"""

from .main import main

if __name__ == "__main__":
    main()
