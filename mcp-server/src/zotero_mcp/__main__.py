"""
Zotero Keeper MCP Server - Module Entry Point

Usage:
    # Local Zotero (default)
    uv run python -m zotero_mcp

Security:
    Keep Zotero's Local/Connector API on loopback. Zotero 10+ write keys are
    runtime-authorized but unscoped; do not expose or forward port 23119.
"""

from .main import main

if __name__ == "__main__":
    main()
