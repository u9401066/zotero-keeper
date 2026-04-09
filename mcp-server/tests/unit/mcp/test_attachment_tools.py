"""
Tests for Attachment & Fulltext Tools

Tests:
- get_item_attachments: List attachments with file paths
- get_item_fulltext: Get Zotero-indexed fulltext
- resolve_attachment_path: File system path resolution
"""

from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

import pytest


# ============================================================================
# DAL Layer: resolve_attachment_path
# ============================================================================


class TestResolveAttachmentPath:
    """Test ZoteroReadMixin.resolve_attachment_path()"""

    def _make_client(self):
        """Create a minimal client with resolve_attachment_path"""
        from zotero_mcp.infrastructure.zotero_client.client_read import (
            ZoteroReadMixin,
        )

        return ZoteroReadMixin()

    def test_returns_none_without_env_var(self, monkeypatch):
        """No ZOTERO_DATA_DIR → returns None"""
        monkeypatch.delenv("ZOTERO_DATA_DIR", raising=False)
        client = self._make_client()
        result = client.resolve_attachment_path("ABCD1234", "paper.pdf")
        assert result is None

    def test_returns_path_with_env_var(self, monkeypatch):
        """ZOTERO_DATA_DIR set → returns correct path"""
        monkeypatch.setenv("ZOTERO_DATA_DIR", "/home/user/Zotero")
        client = self._make_client()
        result = client.resolve_attachment_path("ABCD1234", "paper.pdf")
        assert result == Path("/home/user/Zotero/storage/ABCD1234/paper.pdf")

    def test_path_structure(self, monkeypatch):
        """Verify the Zotero storage path structure"""
        monkeypatch.setenv("ZOTERO_DATA_DIR", "/data/zotero")
        client = self._make_client()
        result = client.resolve_attachment_path("XY789012", "doc.epub")
        assert result is not None
        assert result.parts[-3] == "storage"
        assert result.parts[-2] == "XY789012"
        assert result.parts[-1] == "doc.epub"


# ============================================================================
# MCP Tool: get_item_attachments
# ============================================================================


class TestGetItemAttachments:
    """Test the get_item_attachments MCP tool"""

    @pytest.fixture
    def mock_zotero(self):
        client = AsyncMock()
        client.get_item.return_value = {
            "key": "PARENT01",
            "data": {
                "title": "Deep Learning in Medicine",
                "itemType": "journalArticle",
            },
        }
        client.get_item_children.return_value = [
            {
                "key": "ATT00001",
                "data": {
                    "itemType": "attachment",
                    "title": "Full Text PDF",
                    "filename": "paper.pdf",
                    "contentType": "application/pdf",
                    "linkMode": "imported_file",
                },
            },
            {
                "key": "NOTE0001",
                "data": {
                    "itemType": "note",
                    "note": "<p>Some note</p>",
                },
            },
        ]
        # resolve_attachment_path is sync, not async
        client.resolve_attachment_path = MagicMock(return_value=None)
        return client

    @pytest.fixture
    def register_tools(self, mock_zotero):
        """Register attachment tools and return the tool functions"""
        from unittest.mock import MagicMock

        from zotero_mcp.infrastructure.mcp.attachment_tools import (
            register_attachment_tools,
        )

        tools = {}
        mock_mcp = MagicMock()

        def tool_decorator():
            def wrapper(func):
                tools[func.__name__] = func
                return func

            return wrapper

        mock_mcp.tool = tool_decorator
        register_attachment_tools(mock_mcp, mock_zotero)
        return tools

    @pytest.mark.asyncio
    async def test_returns_attachments_only(self, register_tools):
        """Should filter out notes and only return attachments"""
        get_item_attachments = register_tools["get_item_attachments"]
        result = await get_item_attachments(item_key="PARENT01")

        assert result["attachment_count"] == 1
        assert result["attachments"][0]["key"] == "ATT00001"
        assert result["attachments"][0]["content_type"] == "application/pdf"

    @pytest.mark.asyncio
    async def test_includes_parent_title(self, register_tools):
        """Should include the parent item title"""
        get_item_attachments = register_tools["get_item_attachments"]
        result = await get_item_attachments(item_key="PARENT01")

        assert result["title"] == "Deep Learning in Medicine"
        assert result["item_key"] == "PARENT01"

    @pytest.mark.asyncio
    async def test_no_file_path_without_data_dir(self, register_tools):
        """Without ZOTERO_DATA_DIR, file_path should be empty"""
        get_item_attachments = register_tools["get_item_attachments"]
        result = await get_item_attachments(item_key="PARENT01")

        att = result["attachments"][0]
        assert att["file_path"] == ""
        assert att["file_exists"] is False

    @pytest.mark.asyncio
    async def test_file_path_with_data_dir(self, mock_zotero, register_tools):
        """With ZOTERO_DATA_DIR, should resolve file path"""
        mock_zotero.resolve_attachment_path.return_value = Path("/home/user/Zotero/storage/ATT00001/paper.pdf")

        get_item_attachments = register_tools["get_item_attachments"]
        result = await get_item_attachments(item_key="PARENT01")

        att = result["attachments"][0]
        assert Path(att["file_path"]).as_posix() == "/home/user/Zotero/storage/ATT00001/paper.pdf"

    @pytest.mark.asyncio
    async def test_no_attachments(self, mock_zotero, register_tools):
        """Item with no children → empty attachments list"""
        mock_zotero.get_item_children.return_value = []

        get_item_attachments = register_tools["get_item_attachments"]
        result = await get_item_attachments(item_key="PARENT01")

        assert result["attachment_count"] == 0
        assert result["attachments"] == []

    @pytest.mark.asyncio
    async def test_connection_error(self, mock_zotero, register_tools):
        """Connection error → returns error in result"""
        from zotero_mcp.infrastructure.zotero_client.client import (
            ZoteroConnectionError,
        )

        mock_zotero.get_item.side_effect = ZoteroConnectionError("timeout")

        get_item_attachments = register_tools["get_item_attachments"]
        result = await get_item_attachments(item_key="PARENT01")

        assert "error" in result
        assert result["attachment_count"] == 0


# ============================================================================
# MCP Tool: get_item_fulltext
# ============================================================================


class TestGetItemFulltext:
    """Test the get_item_fulltext MCP tool"""

    @pytest.fixture
    def mock_zotero(self):
        client = AsyncMock()
        client.get_item.return_value = {
            "key": "PARENT01",
            "data": {
                "title": "Deep Learning in Medicine",
                "itemType": "journalArticle",
            },
        }
        client.get_item_children.return_value = [
            {
                "key": "PDFATT01",
                "data": {
                    "itemType": "attachment",
                    "title": "Full Text PDF",
                    "contentType": "application/pdf",
                },
            },
        ]
        client.get_item_fulltext.return_value = {
            "content": "Abstract: Deep learning has revolutionized...",
            "indexedPages": 12,
            "totalPages": 12,
        }
        return client

    @pytest.fixture
    def register_tools(self, mock_zotero):
        from unittest.mock import MagicMock

        from zotero_mcp.infrastructure.mcp.attachment_tools import (
            register_attachment_tools,
        )

        tools = {}
        mock_mcp = MagicMock()

        def tool_decorator():
            def wrapper(func):
                tools[func.__name__] = func
                return func

            return wrapper

        mock_mcp.tool = tool_decorator
        register_attachment_tools(mock_mcp, mock_zotero)
        return tools

    @pytest.mark.asyncio
    async def test_gets_fulltext_from_parent_item(self, register_tools):
        """Parent item → finds PDF attachment → returns fulltext"""
        get_item_fulltext = register_tools["get_item_fulltext"]
        result = await get_item_fulltext(item_key="PARENT01")

        assert result["title"] == "Deep Learning in Medicine"
        assert "Deep learning" in result["content"]
        assert result["indexed_pages"] == 12
        assert "PDFATT01" in result["source"]

    @pytest.mark.asyncio
    async def test_direct_attachment_key(self, mock_zotero, register_tools):
        """Passing an attachment key directly → tries fulltext directly"""
        mock_zotero.get_item.return_value = {
            "key": "PDFATT01",
            "data": {
                "title": "Full Text PDF",
                "itemType": "attachment",
                "contentType": "application/pdf",
            },
        }

        get_item_fulltext = register_tools["get_item_fulltext"]
        result = await get_item_fulltext(item_key="PDFATT01")

        assert "Deep learning" in result["content"]
        assert "direct attachment" in result["source"]

    @pytest.mark.asyncio
    async def test_no_attachments_error(self, mock_zotero, register_tools):
        """Item with no attachments → returns error"""
        mock_zotero.get_item_children.return_value = [
            {
                "key": "NOTE0001",
                "data": {"itemType": "note"},
            }
        ]

        get_item_fulltext = register_tools["get_item_fulltext"]
        result = await get_item_fulltext(item_key="PARENT01")

        assert result["content"] == ""
        assert "error" in result

    @pytest.mark.asyncio
    async def test_fulltext_not_indexed(self, mock_zotero, register_tools):
        """Attachment exists but not indexed → returns error with hint"""
        from zotero_mcp.infrastructure.zotero_client.client import ZoteroAPIError

        mock_zotero.get_item_fulltext.side_effect = ZoteroAPIError("Not Found", status_code=404)

        get_item_fulltext = register_tools["get_item_fulltext"]
        result = await get_item_fulltext(item_key="PARENT01")

        assert result["content"] == ""
        assert "error" in result

    @pytest.mark.asyncio
    async def test_prioritizes_pdf_over_html(self, mock_zotero, register_tools):
        """Multiple attachments → PDF should be tried first"""
        mock_zotero.get_item_children.return_value = [
            {
                "key": "HTML0001",
                "data": {
                    "itemType": "attachment",
                    "title": "Snapshot",
                    "contentType": "text/html",
                },
            },
            {
                "key": "PDFATT01",
                "data": {
                    "itemType": "attachment",
                    "title": "Full Text PDF",
                    "contentType": "application/pdf",
                },
            },
        ]

        call_order = []
        original_fulltext = mock_zotero.get_item_fulltext

        async def track_calls(key):
            call_order.append(key)
            return await original_fulltext(key)

        mock_zotero.get_item_fulltext = track_calls

        get_item_fulltext = register_tools["get_item_fulltext"]
        await get_item_fulltext(item_key="PARENT01")

        # PDF should be tried first
        assert call_order[0] == "PDFATT01"

    @pytest.mark.asyncio
    async def test_connection_error(self, mock_zotero, register_tools):
        """Connection error → returns error"""
        from zotero_mcp.infrastructure.zotero_client.client import (
            ZoteroConnectionError,
        )

        mock_zotero.get_item.side_effect = ZoteroConnectionError("connection refused")

        get_item_fulltext = register_tools["get_item_fulltext"]
        result = await get_item_fulltext(item_key="PARENT01")

        assert "error" in result
        assert result["content"] == ""
