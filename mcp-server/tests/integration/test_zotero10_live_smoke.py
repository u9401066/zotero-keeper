"""Opt-in read-only smoke against a running Zotero desktop instance."""

from __future__ import annotations

import os

from mcp.client import Client
import pytest

from zotero_mcp.infrastructure.mcp.server import create_server


@pytest.mark.live_zotero
@pytest.mark.asyncio
async def test_live_zotero_connection_and_local_identity() -> None:
    """Verify the public read-only capability surface when explicitly enabled."""
    if os.getenv("ZOTERO_LIVE_TEST") != "1":
        pytest.skip("Set ZOTERO_LIVE_TEST=1 to run the live Zotero smoke")

    keeper = create_server()
    try:
        async with Client(keeper.mcp) as client:
            result = await client.call_tool("check_connection", {})
    finally:
        await keeper._zotero.close()

    assert result.is_error is False
    payload = result.structured_content
    assert payload["connected"] is True, payload
    assert payload["local_api_readable"] is True, payload
    assert payload["capabilities"]["local_api_version"] == "3", payload

    # Zotero 10+ provides a Server-ID. Older supported releases remain valid
    # read/Connector targets, so the live smoke does not require it globally.
    version = str(payload.get("zotero_version") or "")
    if version.split(".", 1)[0].isdigit() and int(version.split(".", 1)[0]) >= 10:
        assert payload["capabilities"]["local_api_server_id"], payload
