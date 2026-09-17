"""Keep the human tool reference aligned with the real SDK's input schemas."""

import ast
from pathlib import Path
import re

import pytest

from zotero_mcp.infrastructure.mcp.server import create_server


@pytest.mark.asyncio
async def test_tool_reference_names_and_parameter_tables_match_sdk(monkeypatch):
    monkeypatch.delenv("ZOTERO_KEEPER_ENABLE_LEGACY_PUBMED_TOOLS", raising=False)
    text = (Path(__file__).resolve().parents[4] / "docs" / "tools-reference.md").read_text()
    tools = {tool.name: tool for tool in await create_server().mcp.list_tools()}
    sections = re.split(r"(?m)^### `([^`]+)`[^\n]*\n", text)
    documented = set(re.findall(r"(?m)^\| `(\w+)\(", text))
    for name, section in zip(sections[1::2], sections[2::2], strict=True):
        assert name in tools, f"Unknown documented tool: {name}"
        documented.add(name)
        section = re.split(r"(?m)^#{1,3} ", section)[0]
        rows = re.findall(r"(?m)^\| (`[^|]+`) \| [^|]+ \| ([^|]+) \|", section)
        defaults = {}
        for names, default in rows:
            for parameter in re.findall(r"`(\w+)`", names):
                assert parameter not in defaults, (name, parameter)
                defaults[parameter] = default.strip().strip("`")
        schema = tools[name].input_schema
        assert set(defaults) == set(schema["properties"]), f"Parameter drift: {name}"
        for parameter, default in defaults.items():
            if parameter in schema.get("required", []):
                assert default in {"required", "—"}, (name, parameter)
            else:
                assert ast.literal_eval(default) == schema["properties"][parameter]["default"], (name, parameter)
    assert documented == set(tools), "Every public tool needs a reference entry"
