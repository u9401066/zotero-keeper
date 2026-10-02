"""
Zotero Keeper MCP Server - Main Entry Point

Usage:
    # Default (stdio transport, localhost)
  uv run python -m zotero_mcp

    # With MCP inspector
  uv run mcp dev src/zotero_mcp/infrastructure/mcp/server.py

Environment Variables:
    ZOTERO_HOST     Zotero Desktop loopback host (default: localhost)
    ZOTERO_PORT     Zotero HTTP port (default: 23119)
    ZOTERO_TIMEOUT  Request timeout in seconds (default: 30)

See .env.example for configuration reference.
"""

import argparse
import logging
import os

from .infrastructure.zotero_client.client_base import ZoteroConfig, env_int

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


def build_parser() -> argparse.ArgumentParser:
    """Build the CLI parser; defaults are resolved later so bad env values yield a clean usage error."""
    parser = argparse.ArgumentParser(
        prog="zotero-keeper",
        description="Zotero Keeper MCP Server",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Local Zotero (default)
  uv run python -m zotero_mcp

VS Code Copilot Configuration:
  {
    "github.copilot.chat.agent.mcpServers": {
      "zotero-keeper": {
        "command": "uv",
        "args": ["run", "python", "-m", "zotero_mcp"],
        "cwd": "/path/to/zotero-keeper/mcp-server"
      }
    }
  }
        """,
    )

    parser.add_argument("--transport", "-t", choices=["stdio", "sse"], default="stdio", help="Transport mode (default: stdio)")
    parser.add_argument(
        "--host",
        default=None,
        help="Zotero Desktop loopback host (default: ZOTERO_HOST or localhost; do not expose port 23119)",
    )
    parser.add_argument("--port", type=int, default=None, help="Zotero port (default: ZOTERO_PORT or 23119)")
    return parser


def main(argv: list[str] | None = None) -> None:
    """Main entry point"""
    parser = build_parser()
    args = parser.parse_args(argv)

    try:
        host = args.host or os.environ.get("ZOTERO_HOST", "localhost")
        if args.port is not None:
            if not 1 <= args.port <= 65535:
                raise ValueError(f"--port must be between 1 and 65535, got {args.port}")
            port = args.port
        else:
            port = env_int("ZOTERO_PORT", 23119, minimum=1, maximum=65535)
        # Validate every setting before importing the server, which reads them at import time.
        os.environ["ZOTERO_HOST"] = host
        os.environ["ZOTERO_PORT"] = str(port)
        ZoteroConfig()
    except ValueError as exc:
        parser.error(str(exc))

    logger.info("=" * 60)
    logger.info("Zotero Keeper MCP Server")
    logger.info("=" * 60)
    logger.info(f"Transport: {args.transport}")
    logger.info(f"Zotero: http://{host}:{port}")
    logger.info("=" * 60)

    # Import and run server
    from .infrastructure.mcp.server import get_server

    server = get_server()
    server.run(transport=args.transport)


if __name__ == "__main__":
    main()
