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

from zotero_mcp.infrastructure.zotero_client.client import ZoteroAPIError


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


class TestFileUrlToPath:
    """Test safe parsing of Zotero's Local API file URL response."""

    def test_decodes_file_url_and_rejects_non_file_scheme(self):
        from zotero_mcp.infrastructure.mcp.attachment_tools import _file_url_to_path

        assert _file_url_to_path("file:///tmp/folder%20name/paper.pdf") == Path("/tmp/folder name/paper.pdf")
        assert _file_url_to_path("https://example.test/paper.pdf") is None

    def test_preserves_unc_authority(self):
        from zotero_mcp.infrastructure.mcp.attachment_tools import _file_url_to_path

        result = _file_url_to_path("file://research-server/library/paper.pdf")
        assert result is not None
        assert result.as_posix() == "//research-server/library/paper.pdf"


# ============================================================================
# MCP Tool: get_item_attachments
# ============================================================================


class TestGetItemAttachments:
    """Test the get_item_attachments MCP tool"""

    @pytest.fixture
    def mock_zotero(self):
        client = AsyncMock()
        parent = {
            "key": "PARENT01",
            "data": {
                "title": "Deep Learning in Medicine",
                "itemType": "journalArticle",
            },
        }
        children = [
            {
                "key": "ATT00001",
                "version": 12,
                "data": {
                    "itemType": "attachment",
                    "title": "Full Text PDF",
                    "filename": "paper.pdf",
                    "contentType": "application/pdf",
                    "linkMode": "imported_file",
                    "md5": "a" * 32,
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
        client.get_item_snapshot.return_value = (parent, "server-A")
        client.get_item_children_snapshot.return_value = (children, "server-A")
        client.get_item_file_view_url_snapshot.side_effect = ZoteroAPIError(
            "Local API view URL unsupported",
            status_code=404,
            response_headers={"Zotero-Server-ID": "server-A"},
        )
        client.get_item_library_cursor.return_value = {
            "item_version": 11,
            "library_version": 73,
            "server_id": "server-A",
        }
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
        assert result["attachments"][0]["version"] == 12
        assert result["attachments"][0]["version_scope"] == "local"
        assert result["attachments"][0]["object_version"] == 12
        assert result["attachments"][0]["server_id"] == "server-A"
        assert result["attachments"][0]["md5"] == "a" * 32
        assert result["attachments"][0]["content_type"] == "application/pdf"
        assert result["library_version"] == 73
        assert result["server_id"] == "server-A"

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
        assert att["file_path_source"] == "data_dir"

    @pytest.mark.asyncio
    async def test_prefers_decoded_local_api_file_url(self, mock_zotero, register_tools, tmp_path):
        """Zotero 10+ file/view/url should take priority over data-dir guessing."""
        attachment_dir = tmp_path / "folder with spaces"
        attachment_dir.mkdir()
        pdf = attachment_dir / "paper.pdf"
        pdf.write_bytes(b"%PDF-1.7")
        mock_zotero.get_item_file_view_url_snapshot.side_effect = None
        mock_zotero.get_item_file_view_url_snapshot.return_value = (pdf.as_uri(), "server-A")
        mock_zotero.resolve_attachment_path.return_value = Path("/wrong/fallback.pdf")

        result = await register_tools["get_item_attachments"](item_key="PARENT01")

        attachment = result["attachments"][0]
        assert Path(attachment["file_path"]) == pdf
        assert attachment["file_exists"] is True
        assert attachment["file_size"] == len(b"%PDF-1.7")
        assert attachment["file_path_source"] == "local_api"
        mock_zotero.resolve_attachment_path.assert_not_called()

    @pytest.mark.asyncio
    async def test_invalid_or_unsupported_view_url_falls_back_per_attachment(self, mock_zotero, register_tools):
        """A view-URL failure must not discard otherwise valid attachment metadata."""
        fallback = Path("/home/user/Zotero/storage/ATT00001/paper.pdf")
        mock_zotero.get_item_file_view_url_snapshot.side_effect = ZoteroAPIError(
            "not supported",
            status_code=404,
            response_headers={"Zotero-Server-ID": "server-A"},
        )
        mock_zotero.resolve_attachment_path.return_value = fallback

        result = await register_tools["get_item_attachments"](item_key="PARENT01")

        assert result["attachment_count"] == 1
        assert Path(result["attachments"][0]["file_path"]) == fallback
        assert result["attachments"][0]["file_path_source"] == "data_dir"

    @pytest.mark.asyncio
    async def test_server_switch_during_file_lookup_fails_without_mixing_cursors(
        self,
        mock_zotero,
        register_tools,
    ):
        """A 412 is an identity boundary, never a data-dir fallback signal."""
        mock_zotero.get_item_file_view_url_snapshot.side_effect = ZoteroAPIError(
            "wrong Zotero instance",
            status_code=412,
            response_headers={"Zotero-Server-ID": "server-B"},
        )

        result = await register_tools["get_item_attachments"](item_key="PARENT01")

        assert result["attachment_count"] == 0
        assert "Server-ID changed" in result["error"]
        mock_zotero.get_item_library_cursor.assert_awaited_once_with("PARENT01")
        mock_zotero.resolve_attachment_path.assert_not_called()

    @pytest.mark.asyncio
    async def test_parent_children_and_cursor_must_share_one_server_snapshot(
        self,
        mock_zotero,
        register_tools,
    ):
        mock_zotero.get_item_children_snapshot.return_value = (
            mock_zotero.get_item_children_snapshot.return_value[0],
            "server-B",
        )

        result = await register_tools["get_item_attachments"](item_key="PARENT01")

        assert result["attachment_count"] == 0
        assert "Server-ID changed" in result["error"]
        mock_zotero.get_item_file_view_url_snapshot.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_no_attachments(self, mock_zotero, register_tools):
        """Item with no children → empty attachments list"""
        mock_zotero.get_item_children_snapshot.return_value = ([], "server-A")

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

        mock_zotero.get_item_snapshot.side_effect = ZoteroConnectionError("timeout")

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
        parent = {
            "key": "PARENT01",
            "data": {
                "title": "Deep Learning in Medicine",
                "itemType": "journalArticle",
            },
        }
        children = [
            {
                "key": "PDFATT01",
                "data": {
                    "itemType": "attachment",
                    "title": "Full Text PDF",
                    "contentType": "application/pdf",
                },
            },
        ]
        client.get_item_snapshot.return_value = (parent, "server-A")
        client.get_item_children_snapshot.return_value = (children, "server-A")
        client.get_item_fulltext.return_value = {
            "content": "Abstract: Deep learning has revolutionized...",
            "indexedPages": 12,
            "totalPages": 12,
            "libraryVersion": 73,
            "serverID": "server-A",
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
        assert result["library_version"] == 73
        assert result["server_id"] == "server-A"
        assert "PDFATT01" in result["source"]

    @pytest.mark.asyncio
    async def test_direct_attachment_key(self, mock_zotero, register_tools):
        """Passing an attachment key directly → tries fulltext directly"""
        mock_zotero.get_item_snapshot.return_value = (
            {
                "key": "PDFATT01",
                "data": {
                    "title": "Full Text PDF",
                    "itemType": "attachment",
                    "contentType": "application/pdf",
                },
            },
            "server-A",
        )

        get_item_fulltext = register_tools["get_item_fulltext"]
        result = await get_item_fulltext(item_key="PDFATT01")

        assert "Deep learning" in result["content"]
        assert "direct attachment" in result["source"]
        assert result["library_version"] == 73
        assert result["server_id"] == "server-A"

    @pytest.mark.asyncio
    async def test_server_identity_conflict_is_not_reported_as_unindexed(self, mock_zotero, register_tools):
        """A 412 is a snapshot failure, not an attachment-local indexing miss."""
        from zotero_mcp.infrastructure.zotero_client.client import ZoteroAPIError

        mock_zotero.get_item_snapshot.return_value = (
            {
                "key": "PDFATT01",
                "data": {"title": "Full Text PDF", "itemType": "attachment"},
            },
            "server-A",
        )
        mock_zotero.get_item_fulltext.side_effect = ZoteroAPIError(
            "server changed",
            status_code=412,
        )

        result = await register_tools["get_item_fulltext"](item_key="PDFATT01")

        assert result["content"] == ""
        assert "Server-ID changed" in result["error"]
        assert "not indexed" not in result["error"].lower()

    @pytest.mark.asyncio
    async def test_no_attachments_error(self, mock_zotero, register_tools):
        """Item with no attachments → returns error"""
        mock_zotero.get_item_children_snapshot.return_value = (
            [
                {
                    "key": "NOTE0001",
                    "data": {"itemType": "note"},
                }
            ],
            "server-A",
        )

        get_item_fulltext = register_tools["get_item_fulltext"]
        result = await get_item_fulltext(item_key="PARENT01")

        assert result["content"] == ""
        assert "error" in result

    @pytest.mark.asyncio
    async def test_fulltext_not_indexed(self, mock_zotero, register_tools):
        """Attachment exists but not indexed → returns error with hint"""
        from zotero_mcp.infrastructure.zotero_client.client import ZoteroAPIError

        mock_zotero.get_item_fulltext.side_effect = ZoteroAPIError(
            "Not Found",
            status_code=404,
            response_headers={"Zotero-Server-ID": "server-A"},
        )

        get_item_fulltext = register_tools["get_item_fulltext"]
        result = await get_item_fulltext(item_key="PARENT01")

        assert result["content"] == ""
        assert "error" in result

    @pytest.mark.asyncio
    async def test_prioritizes_pdf_over_html(self, mock_zotero, register_tools):
        """Multiple attachments → PDF should be tried first"""
        mock_zotero.get_item_children_snapshot.return_value = (
            [
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
            ],
            "server-A",
        )

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

        mock_zotero.get_item_snapshot.side_effect = ZoteroConnectionError("connection refused")

        get_item_fulltext = register_tools["get_item_fulltext"]
        result = await get_item_fulltext(item_key="PARENT01")

        assert "error" in result
        assert result["content"] == ""
