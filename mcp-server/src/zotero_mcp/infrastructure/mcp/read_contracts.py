"""Shared response-identity contract for multi-request MCP reads."""

from ..zotero_client.client import ZoteroAPIError


def same_server_snapshot(*server_ids: str | None) -> str | None:
    """Accept legacy missing identities, but never mix profiles or API generations."""
    present = {server_id for server_id in server_ids if server_id is not None}
    if present and (len(present) != 1 or any(server_id is None for server_id in server_ids)):
        actual = next((server_id for server_id in reversed(server_ids) if server_id), "")
        raise ZoteroAPIError(
            "Zotero Server-ID changed during a multi-request read",
            status_code=412,
            response_headers={"Zotero-Server-ID": actual},
        )
    return next(iter(present), None)
