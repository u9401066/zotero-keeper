"""
Zotero Keeper MCP Server - Module Entry Point

Usage:
    # Local Zotero (default)
    uv run python -m zotero_mcp

    # Remote Zotero
    uv run python -m zotero_mcp --host <your-zotero-ip>
    ZOTERO_HOST=<your-zotero-ip> uv run python -m zotero_mcp
"""

from .main import main

if __name__ == "__main__":
    main()
