"""
Zotero Keeper MCP Server - Main Entry Point

Usage:
    # Default (stdio transport)
    python -m zotero_mcp
    
    # With custom Zotero host
    ZOTERO_HOST=YOUR_ZOTERO_HOST python -m zotero_mcp
    
    # With MCP inspector
    mcp dev src/zotero_mcp/infrastructure/mcp/server.py

Environment Variables:
    ZOTERO_HOST     Zotero machine IP (default: localhost)
    ZOTERO_PORT     Zotero HTTP port (default: 23119)
    ZOTERO_TIMEOUT  Request timeout in seconds (default: 30)
"""

import argparse
import logging
import os
import sys

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(
        description="Zotero Keeper MCP Server",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Local MCP mode (default)
  python -m zotero_mcp
  
  # With remote Zotero
  ZOTERO_HOST=YOUR_ZOTERO_HOST python -m zotero_mcp

VS Code Copilot Configuration:
  {
    "github.copilot.chat.agent.mcpServers": {
      "zotero-keeper": {
        "command": "python",
        "args": ["-m", "zotero_mcp"],
        "cwd": "/path/to/zotero-keeper/mcp-server"
      }
    }
  }
        """
    )
    
    parser.add_argument(
        "--transport", "-t",
        choices=["stdio", "sse"],
        default="stdio",
        help="Transport mode (default: stdio)"
    )
    parser.add_argument(
        "--host",
        default=os.environ.get("ZOTERO_HOST", "localhost"),
        help="Zotero host (default: localhost or ZOTERO_HOST env)"
    )
    parser.add_argument(
        "--port",
        type=int,
        default=int(os.environ.get("ZOTERO_PORT", "23119")),
        help="Zotero port (default: 23119 or ZOTERO_PORT env)"
    )
    
    args = parser.parse_args()
    
    # Set environment variables for config
    os.environ["ZOTERO_HOST"] = args.host
    os.environ["ZOTERO_PORT"] = str(args.port)
    
    logger.info("=" * 60)
    logger.info("Zotero Keeper MCP Server")
    logger.info("=" * 60)
    logger.info(f"Transport: {args.transport}")
    logger.info(f"Zotero: http://{args.host}:{args.port}")
    logger.info("=" * 60)
    
    # Import and run server
    from .infrastructure.mcp.server import get_server
    
    server = get_server()
    server.run(transport=args.transport)


if __name__ == "__main__":
    main()
