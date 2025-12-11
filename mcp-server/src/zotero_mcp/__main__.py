"""
Zotero MCP Server - Main Entry Point

Usage:
    python -m zotero_mcp
    python -m zotero_mcp --zotero-url http://localhost:23120
"""

import argparse
import sys

from .interface.server import create_mcp_server, mcp


def main():
    """Main entry point for the MCP server"""
    parser = argparse.ArgumentParser(
        description="Zotero MCP Server - Bridge between MCP and local Zotero client"
    )
    parser.add_argument(
        "--zotero-url",
        default="http://localhost:23120",
        help="URL of the Zotero plugin HTTP server (default: http://localhost:23120)",
    )
    
    args = parser.parse_args()
    
    # Configure server with provided URL
    server = create_mcp_server(zotero_url=args.zotero_url)
    
    # Run the server
    server.run()


if __name__ == "__main__":
    main()
