#!/usr/bin/env python3
"""
Test script for Zotero Keeper MCP Tools

Tests all MCP tools against a live Zotero instance.

Usage:
    # Local Zotero (default)
    python test_mcp_tools.py

Security:
    Keep Zotero's unauthenticated Local/Connector API on loopback. Do not expose
    or forward port 23119 for remote testing.
"""

import asyncio
import os
import json

# Default to localhost if not set (set via .env or environment)
if "ZOTERO_HOST" not in os.environ:
    os.environ["ZOTERO_HOST"] = "localhost"

from zotero_mcp.infrastructure.mcp.server import ZoteroKeeperServer


async def main():
    print("=" * 60)
    print("Zotero Keeper MCP Tools Test")
    print("=" * 60)

    # Create server instance
    server = ZoteroKeeperServer()

    # Get the registered tools
    tools = server._mcp._tool_manager._tools
    print(f"\n📦 Registered Tools ({len(tools)}):")
    for name in sorted(tools.keys()):
        print(f"   - {name}")

    print("\n" + "=" * 60)
    print("Testing Tools...")
    print("=" * 60)

    # Test 1: check_connection
    print("\n1. 🔌 check_connection()")
    result = await tools["check_connection"].fn()
    print(f"   Result: {json.dumps(result, indent=2)}")

    if not result.get("connected"):
        print("\n❌ Cannot connect to Zotero. Make sure:")
        print("   1. Zotero is running")
        print("   2. Local API is enabled")
        print("   3. Keeper and Zotero share a host, with port 23119 on loopback only")
        return

    # Test 2: list_items
    print("\n2. 📋 list_items(limit=5)")
    result = await tools["list_items"].fn(limit=5)
    print(f"   Count: {result.get('count')}")
    for item in result.get("items", [])[:3]:
        print(f"   - [{item.get('itemType')}] {item.get('title', '')[:50]}")

    # Test 3: search_items
    print("\n3. 🔍 search_items(query='test')")
    result = await tools["search_items"].fn(query="test", limit=5)
    print(f"   Found: {result.get('count')}")
    for item in result.get("items", [])[:3]:
        print(f"   - {item.get('title', '')[:50]}")

    # Test 4: list_collections
    print("\n4. 📁 list_collections()")
    result = await tools["list_collections"].fn()
    print(f"   Count: {result.get('count')}")
    for col in result.get("collections", [])[:5]:
        print(f"   - {col.get('name')}")

    # Test 5: list_tags
    print("\n5. 🏷️ list_tags()")
    result = await tools["list_tags"].fn()
    print(f"   Count: {result.get('count')}")
    if result.get("tags"):
        print(f"   Tags: {', '.join(result.get('tags', [])[:10])}")

    # Test 6: get_item_types
    print("\n6. 📝 get_item_types()")
    result = await tools["get_item_types"].fn()
    print(f"   Count: {result.get('count')}")
    if result.get("itemTypes"):
        print(f"   Types: {', '.join(result.get('itemTypes', [])[:10])}")

    # Default mode intentionally omits the old add_reference write tool.
    # Keep this live diagnostic read-only; write flows require an explicitly
    # confirmed collection through interactive_save/import_articles.
    print("\n7. 🛡️ Default write-surface policy")
    required = {"interactive_save", "quick_save", "import_articles", "import_pdf"}
    missing = sorted(required - set(tools))
    if missing:
        raise RuntimeError(f"Missing required write tools: {missing}")
    print("   Read-only live smoke complete; no test item was created.")

    print("\n" + "=" * 60)
    print("✅ All tests completed!")
    print("=" * 60)

    # Cleanup
    await server._zotero.close()


if __name__ == "__main__":
    asyncio.run(main())
