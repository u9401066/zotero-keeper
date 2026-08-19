"""
Attachment & Fulltext Tools for Zotero Keeper

Provides PDF/attachment access tools:
- get_item_attachments: List attachments with file paths for a Zotero item
- get_item_fulltext: Get Zotero-indexed fulltext content (plain text)
"""

import logging
import os
import re
from pathlib import Path
from typing import TYPE_CHECKING, Any
from urllib.parse import unquote, urlparse
from urllib.request import url2pathname

from mcp.server import MCPServer

if TYPE_CHECKING:
    from ..zotero_client.client import ZoteroClient

from ..zotero_client.client import ZoteroAPIError, ZoteroConnectionError

logger = logging.getLogger(__name__)


def _same_server_snapshot(*server_ids: str | None) -> str | None:
    """Require all parts of a Zotero 10+ read to come from one database."""
    present = {server_id for server_id in server_ids if server_id is not None}
    if present and (len(present) != 1 or any(server_id is None for server_id in server_ids)):
        actual = next((server_id for server_id in reversed(server_ids) if server_id), "")
        raise ZoteroAPIError(
            "Zotero Server-ID changed while reading attachment metadata",
            status_code=412,
            response_headers={"Zotero-Server-ID": actual},
        )
    return next(iter(present), None)


def _file_url_to_path(value: Any) -> Path | None:
    """Safely convert Zotero's ``file://`` view URL to a local path.

    ``url2pathname`` supplies platform-native decoding.  The explicit handling
    around it preserves Windows drive paths and UNC authorities while rejecting
    non-file URLs and relative paths.
    """
    if not isinstance(value, str):
        return None
    parsed = urlparse(value.strip())
    if parsed.scheme.lower() != "file" or parsed.query or parsed.fragment:
        return None

    decoded = url2pathname(parsed.path)
    authority = unquote(parsed.netloc)
    if authority and authority.lower() != "localhost":
        decoded = f"//{authority}{decoded}"
    elif os.name == "nt" and re.match(r"^/[A-Za-z]:[/\\]", decoded):
        decoded = decoded[1:]

    path = Path(decoded)
    return path if path.is_absolute() else None


def register_attachment_tools(mcp: MCPServer, zotero: "ZoteroClient") -> None:
    """Register attachment and fulltext tools with the MCP server"""

    @mcp.tool()
    async def get_item_attachments(
        item_key: str,
    ) -> dict[str, Any]:
        """
        📎 Get attachments for a Zotero item (PDFs, snapshots, etc.)

        取得文獻的所有附件資訊，包含檔案路徑。
        回傳的 file_path 可以直接交給其他 MCP 工具（如 PDF reader）使用。

        Zotero 10+ 會透過 Local API 回傳實際路徑；舊版 Zotero 或不支援該
        endpoint 時，才使用可選的 ZOTERO_DATA_DIR 推導 storage 路徑。

        Args:
            item_key: Zotero item key (8-character, e.g. "ABCD1234")

        Returns:
            Dict with:
            - item_key: The parent item key
            - title: Parent item title
            - library_version: Library cursor for version-protected full-text writes
            - server_id: Zotero 10+ database identity paired with that cursor
            - attachment_count: Number of attachments
            - attachments: List of attachment info dicts, each containing:
                - key: Attachment item key
                - version: Zotero instance-local object version, used as the
                  expected_version for object-version-protected writes
                - object_version: Explicit alias of version
                - server_id: Database identity in which the object version is valid
                - md5: Current imported-file MD5 for safe If-Match replacement
                - title: Attachment title
                - filename: Original filename
                - content_type: MIME type (e.g. "application/pdf")
                - file_path: Absolute path to file (if ZOTERO_DATA_DIR set)
                - file_exists: Whether the file exists on disk
                - file_size: File size in bytes (0 if not accessible)
                - link_mode: How the file is stored (imported_file, linked_file, etc.)

        Example:
            get_item_attachments(item_key="X42A7DEE")
            → {
                "item_key": "X42A7DEE",
                "title": "Deep Learning in Medicine",
                "attachment_count": 1,
                "attachments": [{
                    "key": "NHZFE5A7",
                    "title": "Full Text PDF",
                    "filename": "paper.pdf",
                    "content_type": "application/pdf",
                    "file_path": "/home/user/Zotero/storage/NHZFE5A7/paper.pdf",
                    "file_exists": true,
                    "file_size": 1048576,
                    "link_mode": "imported_file"
                }]
            }
        """
        try:
            # Get parent item title
            parent, parent_server_id = await zotero.get_item_snapshot(item_key)
            parent_data = parent.get("data", parent)
            parent_title = parent_data.get("title", "Untitled")

            # Get children
            children, children_server_id = await zotero.get_item_children_snapshot(item_key)
            cursor = await zotero.get_item_library_cursor(item_key)
            library_version = cursor.get("library_version")
            cursor_server_id = cursor.get("server_id")
            server_id = _same_server_snapshot(
                parent_server_id,
                children_server_id,
                cursor_server_id,
            )

            attachments = []
            for child in children:
                data = child.get("data", child)
                if data.get("itemType") != "attachment":
                    continue

                att_key = child.get("key", data.get("key", ""))
                filename = data.get("filename", "")
                content_type = data.get("contentType", "")
                link_mode = data.get("linkMode", "")

                # Prefer Zotero 10+'s documented Local API file view URL.  A
                # missing/unsupported endpoint is attachment-local and must not
                # make the entire list fail.
                file_path_str = ""
                file_exists = False
                file_size = 0
                file_path_source = ""

                resolved: Path | None = None
                try:
                    file_url, file_server_id = await zotero.get_item_file_view_url_snapshot(att_key)
                    _same_server_snapshot(server_id, file_server_id)
                    resolved = _file_url_to_path(file_url)
                    if resolved is not None:
                        file_path_source = "local_api"
                except ZoteroAPIError as exc:
                    _same_server_snapshot(server_id, exc.server_id)
                    # Older Zotero releases and unsupported attachment modes
                    # can lack this endpoint. Identity/auth/conflict errors are
                    # not fallback conditions: swallowing a 412 could combine
                    # attachment metadata from one database with a cursor from
                    # another.
                    if exc.status_code not in {404, 405, 501}:
                        raise
                    logger.debug("Local API attachment path unsupported for %s: %s", att_key, exc)

                if resolved is None:
                    resolved = zotero.resolve_attachment_path(att_key, filename)
                    if resolved is not None:
                        file_path_source = "data_dir"
                if resolved:
                    file_path_str = str(resolved)
                    file_exists = resolved.exists()
                    if file_exists:
                        file_size = resolved.stat().st_size

                attachments.append(
                    {
                        "key": att_key,
                        "version": child.get("version", data.get("version")),
                        "object_version": child.get("version", data.get("version")),
                        "version_scope": "local",
                        "server_id": server_id,
                        "md5": data.get("md5"),
                        "title": data.get("title", ""),
                        "filename": filename,
                        "content_type": content_type,
                        "file_path": file_path_str,
                        "file_exists": file_exists,
                        "file_size": file_size,
                        "file_path_source": file_path_source,
                        "link_mode": link_mode,
                    }
                )

            return {
                "item_key": item_key,
                "title": parent_title,
                "library_version": library_version,
                "server_id": server_id,
                "attachment_count": len(attachments),
                "attachments": attachments,
                "hint": "Use file_path with a PDF reader MCP tool to extract content"
                if attachments
                else "No attachments found for this Zotero item.",
            }

        except (ZoteroConnectionError, ZoteroAPIError) as e:
            return {"item_key": item_key, "attachment_count": 0, "attachments": [], "error": str(e)}

    @mcp.tool()
    async def get_item_fulltext(
        item_key: str,
    ) -> dict[str, Any]:
        """
        📄 Get fulltext content of a Zotero item (indexed by Zotero)

        取得 Zotero 已索引的全文純文字內容。
        Zotero 會自動為 PDF/EPUB/HTML 附件建立全文索引。

        此工具會自動找到該文獻的附件，並嘗試取得已索引的全文。
        不需要外部 PDF 解析工具 — 直接回傳純文字。

        Args:
            item_key: Zotero item key (parent item or attachment key)

        Returns:
            Dict with:
            - item_key: The item key
            - title: Item title
            - content: Fulltext content (plain text)
            - indexed_pages: Number of pages indexed
            - total_pages: Total pages in document
            - library_version: Library cursor to pass to set_attachment_fulltext
            - server_id: Zotero database identity paired with the cursor
            - source: Which attachment provided the fulltext

        Example:
            get_item_fulltext(item_key="X42A7DEE")
            → {
                "item_key": "X42A7DEE",
                "title": "Deep Learning in Medicine",
                "content": "Abstract: Deep learning has...",
                "indexed_pages": 12,
                "total_pages": 12,
                "source": "NHZFE5A7 (Full Text PDF)"
            }
        """
        try:
            # Get the item metadata
            item, item_server_id = await zotero.get_item_snapshot(item_key)
            item_data = item.get("data", item)
            title = item_data.get("title", "Untitled")
            item_type = item_data.get("itemType", "")

            # If this IS an attachment, try fulltext directly
            if item_type == "attachment":
                try:
                    ft = await zotero.get_item_fulltext(item_key)
                    _same_server_snapshot(item_server_id, ft.get("serverID"))
                    return {
                        "item_key": item_key,
                        "title": title,
                        "content": ft.get("content", ""),
                        "indexed_pages": ft.get("indexedPages", 0),
                        "total_pages": ft.get("totalPages", 0),
                        "library_version": ft.get("libraryVersion"),
                        "server_id": ft.get("serverID"),
                        "source": f"{item_key} (direct attachment)",
                    }
                except ZoteroAPIError as exc:
                    _same_server_snapshot(item_server_id, exc.server_id)
                    if exc.status_code != 404:
                        raise
                    return {
                        "item_key": item_key,
                        "title": title,
                        "content": "",
                        "error": "Fulltext not indexed for this attachment",
                    }

            # It's a parent item — find its PDF/EPUB attachments
            children, children_server_id = await zotero.get_item_children_snapshot(item_key)
            read_server_id = _same_server_snapshot(item_server_id, children_server_id)

            # Prioritize: PDF > EPUB > HTML > any
            pdf_attachments = []
            other_attachments = []
            for child in children:
                data = child.get("data", child)
                if data.get("itemType") != "attachment":
                    continue
                ct = data.get("contentType", "")
                if ct == "application/pdf":
                    pdf_attachments.append(child)
                elif ct in (
                    "application/epub+zip",
                    "text/html",
                    "text/plain",
                ):
                    other_attachments.append(child)

            candidates = pdf_attachments + other_attachments
            if not candidates:
                return {
                    "item_key": item_key,
                    "title": title,
                    "content": "",
                    "error": "No suitable attachments found for fulltext extraction",
                }

            # Try each attachment until we get fulltext
            errors = []
            for att in candidates:
                att_key = att.get("key", att.get("data", {}).get("key", ""))
                att_title = att.get("data", att).get("title", "")
                try:
                    ft = await zotero.get_item_fulltext(att_key)
                    _same_server_snapshot(read_server_id, ft.get("serverID"))
                    content = ft.get("content", "")
                    if content:
                        return {
                            "item_key": item_key,
                            "title": title,
                            "content": content,
                            "indexed_pages": ft.get("indexedPages", 0),
                            "total_pages": ft.get("totalPages", 0),
                            "library_version": ft.get("libraryVersion"),
                            "server_id": ft.get("serverID"),
                            "source": f"{att_key} ({att_title})",
                        }
                except ZoteroAPIError as e:
                    _same_server_snapshot(read_server_id, e.server_id)
                    if e.status_code != 404:
                        raise
                    errors.append(f"{att_key}: {e}")

            return {
                "item_key": item_key,
                "title": title,
                "content": "",
                "error": "Fulltext not indexed for any attachment",
                "details": errors,
                "hint": "Zotero may need time to index. Or use get_item_attachments() to get file paths for external PDF parsing.",
            }

        except (ZoteroConnectionError, ZoteroAPIError) as e:
            return {"item_key": item_key, "content": "", "error": str(e)}
