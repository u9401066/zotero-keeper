"""
Zotero Keeper MCP Server - Module Entry Point

Usage:
    python -m zotero_mcp
    python -m zotero_mcp --host YOUR_ZOTERO_HOST
    ZOTERO_HOST=YOUR_ZOTERO_HOST python -m zotero_mcp
"""

from .main import main

if __name__ == "__main__":
    main()
