"""Utility script to list all MCP tools."""

import os
import re

mcp_dir = "src/zotero_mcp/infrastructure/mcp"
tools = []

for fname in os.listdir(mcp_dir):
    if fname.endswith(".py") and fname != "__init__.py":
        fpath = os.path.join(mcp_dir, fname)
        with open(fpath, "r", encoding="utf-8") as f:
            content = f.read()

        # Find @mcp.tool() or @self._mcp.tool() followed by async def
        pattern = r"@(?:mcp|self\._mcp)\.tool\(\)\s+async def (\w+)"
        matches = re.findall(pattern, content)
        for m in matches:
            tools.append((fname, m))

print(f"Total tools: {len(tools)}")
print()
for fname, tool in sorted(tools, key=lambda x: (x[0], x[1])):
    print(f"{fname:30} -> {tool}")
