"""Read-only citation export and CSL bibliography rendering through Zotero's Local API."""

import re
from typing import Any

from mcp.server import MCPServer
from mcp.types import ToolAnnotations

from ..zotero_client.client import ZoteroAPIError, ZoteroClient, ZoteroConnectionError
from .local_api_tools import _error, _normalize_key, _zotero_error

READ = ToolAnnotations(read_only_hint=True, destructive_hint=False, idempotent_hint=True, open_world_hint=False)

MAX_EXPORT_ITEMS = 50
EXPORT_FORMATS = frozenset(
    {
        "bibtex",
        "biblatex",
        "bookmarks",
        "coins",
        "csljson",
        "csv",
        "mods",
        "refer",
        "rdf_bibliontology",
        "rdf_dc",
        "rdf_zotero",
        "ris",
        "tei",
        "wikipedia",
    }
)
BIBLIOGRAPHY_PARTS = {"bib": "bib", "citation": "citation", "both": "bib,citation"}
_STYLE_RE = re.compile(r"[A-Za-z0-9][A-Za-z0-9._-]{0,99}")
_LOCALE_RE = re.compile(r"[A-Za-z]{2,3}(?:-[A-Za-z0-9]{2,8}){0,3}")


def _normalize_keys(operation: str, item_keys: Any) -> tuple[list[str] | None, dict[str, Any] | None]:
    if not isinstance(item_keys, list) or not 1 <= len(item_keys) <= MAX_EXPORT_ITEMS:
        return None, _error(operation, "invalid_keys", f"Provide 1-{MAX_EXPORT_ITEMS} exact Zotero item keys.")
    keys: list[str] = []
    for raw in item_keys:
        key, error = _normalize_key(operation, raw, "item_keys entry")
        if error:
            return None, error
        assert key is not None
        if key not in keys:
            keys.append(key)
    return keys, None


def register_export_tools(mcp: MCPServer[Any], zotero: ZoteroClient) -> None:
    """Register exact-key export tools; they never mutate Zotero."""

    @mcp.tool(annotations=READ)
    async def export_items(item_keys: list[str], format: str = "bibtex") -> dict[str, Any]:
        """Export up to 50 exact items as BibTeX/BibLaTeX/RIS/CSL JSON/etc. using Zotero's own translators.

        Prefer this over rebuilding citations from search results. Keys absent from the library are reported
        in `missing_count` so a partial export is never mistaken for a complete one.
        """
        operation = "export_items"
        keys, error = _normalize_keys(operation, item_keys)
        if error:
            return error
        assert keys is not None
        export_format = format.strip().lower() if isinstance(format, str) else ""
        if export_format not in EXPORT_FORMATS:
            return _error(operation, "invalid_format", f"format must be one of: {', '.join(sorted(EXPORT_FORMATS))}.")
        try:
            content, server_id, total = await zotero.export_items_snapshot(keys, export_format)
        except (ZoteroAPIError, ZoteroConnectionError) as exc:
            return _zotero_error(operation, exc)
        return {
            "success": True,
            "operation": operation,
            "format": export_format,
            "requested_count": len(keys),
            "exported_count": total,
            "missing_count": None if total is None else max(len(keys) - total, 0),
            "server_id": server_id,
            "content": content,
        }

    @mcp.tool(annotations=READ)
    async def get_bibliography(
        item_keys: list[str],
        style: str = "apa",
        output: str = "bib",
        locale: str | None = None,
        linkwrap: bool = False,
    ) -> dict[str, Any]:
        """Render formatted bibliography entries and/or in-text citations (HTML) for up to 50 exact items.

        `style` is an installed CSL style id such as apa, vancouver or chicago-note-bibliography.
        `output` is bib, citation or both. Items Zotero cannot render are listed in `missing_keys`.
        """
        operation = "get_bibliography"
        keys, error = _normalize_keys(operation, item_keys)
        if error:
            return error
        assert keys is not None
        if not isinstance(style, str) or not _STYLE_RE.fullmatch(style.strip()):
            return _error(operation, "invalid_style", "style must be a CSL style id (letters, digits, '.', '_' or '-').")
        part = BIBLIOGRAPHY_PARTS.get(output.strip().lower()) if isinstance(output, str) else None
        if part is None:
            return _error(operation, "invalid_output", "output must be bib, citation or both.")
        if locale is not None and (not isinstance(locale, str) or not _LOCALE_RE.fullmatch(locale.strip())):
            return _error(operation, "invalid_locale", "locale must be a BCP 47 tag such as en-US or zh-TW.")
        try:
            rows, server_id = await zotero.get_bibliography_snapshot(
                keys,
                style=style.strip(),
                include=part,
                linkwrap=bool(linkwrap),
                locale=locale.strip() if locale else None,
            )
        except (ZoteroAPIError, ZoteroConnectionError) as exc:
            return _zotero_error(operation, exc)
        entries = []
        for row in rows:
            key = row.get("key")
            if not isinstance(key, str) or key not in keys:
                continue
            entry: dict[str, Any] = {"key": key}
            for field in ("bib", "citation"):
                if field in part and isinstance(row.get(field), str):
                    entry[field] = row[field]
            entries.append(entry)
        returned = {entry["key"] for entry in entries}
        return {
            "success": True,
            "operation": operation,
            "style": style.strip(),
            "requested_count": len(keys),
            "count": len(entries),
            "missing_keys": [key for key in keys if key not in returned],
            "server_id": server_id,
            "entries": entries,
        }
