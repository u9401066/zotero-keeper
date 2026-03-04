"""
Attachment & Fulltext Tools for Zotero Keeper

Provides PDF/attachment access tools:
- get_item_attachments: List attachments with file paths for a Zotero item
- get_item_fulltext: Get Zotero-indexed fulltext content (plain text)
"""

import logging
from typing import TYPE_CHECKING, Any

from mcp.server.fastmcp import FastMCP

if TYPE_CHECKING:
    from ..zotero_client.client import ZoteroClient

from ..zotero_client.client import ZoteroAPIError, ZoteroConnectionError

logger = logging.getLogger(__name__)


def register_attachment_tools(mcp: FastMCP, zotero: "ZoteroClient") -> None:
    """Register attachment and fulltext tools with the MCP server"""

    @mcp.tool()
    async def get_item_attachments(
        item_key: str,
    ) -> dict[str, Any]:
        """
        📎 Get attachments for a Zotero item (PDFs, snapshots, etc.)

        取得文獻的所有附件資訊，包含檔案路徑。
        回傳的 file_path 可以直接交給其他 MCP 工具（如 PDF reader）使用。

        需要設定環境變數 ZOTERO_DATA_DIR 才能取得檔案路徑。
        例如: ZOTERO_DATA_DIR=~/Zotero

        Args:
            item_key: Zotero item key (8-character, e.g. "ABCD1234")

        Returns:
            Dict with:
            - item_key: The parent item key
            - title: Parent item title
            - attachment_count: Number of attachments
            - attachments: List of attachment info dicts, each containing:
                - key: Attachment item key
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
            parent = await zotero.get_item(item_key)
            parent_data = parent.get("data", parent)
            parent_title = parent_data.get("title", "Untitled")

            # Get children
            children = await zotero.get_item_children(item_key)

            attachments = []
            for child in children:
                data = child.get("data", child)
                if data.get("itemType") != "attachment":
                    continue

                att_key = child.get("key", data.get("key", ""))
                filename = data.get("filename", "")
                content_type = data.get("contentType", "")
                link_mode = data.get("linkMode", "")

                # Resolve file path
                file_path_str = ""
                file_exists = False
                file_size = 0

                resolved = zotero.resolve_attachment_path(att_key, filename)
                if resolved:
                    file_path_str = str(resolved)
                    file_exists = resolved.exists()
                    if file_exists:
                        file_size = resolved.stat().st_size

                attachments.append(
                    {
                        "key": att_key,
                        "title": data.get("title", ""),
                        "filename": filename,
                        "content_type": content_type,
                        "file_path": file_path_str,
                        "file_exists": file_exists,
                        "file_size": file_size,
                        "link_mode": link_mode,
                    }
                )

            return {
                "item_key": item_key,
                "title": parent_title,
                "attachment_count": len(attachments),
                "attachments": attachments,
                "hint": "Use file_path with a PDF reader MCP tool to extract content"
                if attachments
                else "No attachments found. Set ZOTERO_DATA_DIR env var for file access.",
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
            item = await zotero.get_item(item_key)
            item_data = item.get("data", item)
            title = item_data.get("title", "Untitled")
            item_type = item_data.get("itemType", "")

            # If this IS an attachment, try fulltext directly
            if item_type == "attachment":
                try:
                    ft = await zotero.get_item_fulltext(item_key)
                    return {
                        "item_key": item_key,
                        "title": title,
                        "content": ft.get("content", ""),
                        "indexed_pages": ft.get("indexedPages", 0),
                        "total_pages": ft.get("totalPages", 0),
                        "source": f"{item_key} (direct attachment)",
                    }
                except ZoteroAPIError:
                    return {
                        "item_key": item_key,
                        "title": title,
                        "content": "",
                        "error": "Fulltext not indexed for this attachment",
                    }

            # It's a parent item — find its PDF/EPUB attachments
            children = await zotero.get_item_children(item_key)

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
                    content = ft.get("content", "")
                    if content:
                        return {
                            "item_key": item_key,
                            "title": title,
                            "content": content,
                            "indexed_pages": ft.get("indexedPages", 0),
                            "total_pages": ft.get("totalPages", 0),
                            "source": f"{att_key} ({att_title})",
                        }
                except ZoteroAPIError as e:
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
