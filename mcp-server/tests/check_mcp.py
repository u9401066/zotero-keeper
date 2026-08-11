"""Fail-fast MCP SDK v2 surface diagnostic used by release checks."""

from __future__ import annotations

import asyncio

from mcp.server import MCPServer
from mcp.server.mcpserver import Elicit, Resolve

from zotero_mcp.infrastructure.mcp.server import create_server


async def main() -> None:
    """Verify the SDK v2 primitives and Keeper's discoverable surface."""
    server = create_server().mcp
    if not isinstance(server, MCPServer):
        raise TypeError(f"Expected MCPServer, got {type(server).__name__}")

    # Importing these classes is the v2 elicitation contract. The removed
    # mcp.types.ElicitationRequest name was a v1-era diagnostic and must not be
    # treated as a capability check.
    if not callable(Resolve) or not callable(Elicit):
        raise TypeError("MCP SDK v2 Resolve/Elicit primitives are unavailable")

    tools = await server.list_tools()
    resources = await server.list_resources()
    templates = await server.list_resource_templates()
    tool_names = {tool.name for tool in tools}

    required_tools = {
        "interactive_save",
        "quick_save",
        "check_articles_owned",
        "import_articles",
        "import_pdf",
    }
    missing = sorted(required_tools - tool_names)
    if missing:
        raise RuntimeError(f"Missing required Keeper tools: {missing}")
    if len(tools) != 24 or len(resources) != 6 or len(templates) != 4:
        raise RuntimeError(
            "Unexpected Keeper surface: "
            f"{len(tools)} tools, {len(resources)} resources, {len(templates)} templates"
        )

    print("MCP SDK v2 surface check passed")
    print(f"  server: {type(server).__name__}")
    print(f"  tools: {len(tools)}")
    print(f"  resources: {len(resources)}")
    print(f"  resource templates: {len(templates)}")


if __name__ == "__main__":
    asyncio.run(main())
