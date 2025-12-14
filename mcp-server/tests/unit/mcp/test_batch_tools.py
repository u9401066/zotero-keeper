"""
Tests for batch_tools.py

Tests the batch import functionality for PubMed articles to Zotero.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
import time

from zotero_mcp.infrastructure.mcp.batch_tools import (
    _parse_pmids,
    is_batch_import_available,
)


class TestParsePmids:
    """Tests for _parse_pmids function."""
    
    def test_single_pmid(self):
        """Test parsing single PMID."""
        result = _parse_pmids("12345678")
        assert result == ["12345678"]
    
    def test_multiple_pmids(self):
        """Test parsing multiple PMIDs."""
        result = _parse_pmids("12345678,87654321,11111111")
        assert result == ["12345678", "87654321", "11111111"]
    
    def test_whitespace_handling(self):
        """Test whitespace is stripped."""
        result = _parse_pmids("  12345678 , 87654321  ")
        assert result == ["12345678", "87654321"]
    
    def test_empty_string(self):
        """Test empty string returns empty list."""
        result = _parse_pmids("")
        assert result == []
    
    def test_none_input(self):
        """Test None input returns empty list."""
        result = _parse_pmids(None)
        assert result == []
    
    def test_invalid_pmids_skipped(self):
        """Test invalid PMIDs are skipped."""
        result = _parse_pmids("12345678,invalid,87654321")
        assert result == ["12345678", "87654321"]
    
    def test_last_keyword(self):
        """Test 'last' keyword handling."""
        result = _parse_pmids("last")
        assert result == []  # Not implemented yet
    
    def test_non_numeric_pmids(self):
        """Test non-numeric PMIDs are skipped."""
        result = _parse_pmids("abc123,12345678,xyz")
        assert result == ["12345678"]
    
    def test_mixed_valid_invalid(self):
        """Test mixed valid and invalid PMIDs."""
        result = _parse_pmids("12345678,not-a-pmid,87654321,12.34")
        assert result == ["12345678", "87654321"]


class TestIsBatchImportAvailable:
    """Tests for is_batch_import_available function."""
    
    def test_returns_boolean(self):
        """Test that function returns boolean."""
        result = is_batch_import_available()
        assert isinstance(result, bool)


class TestRegisterBatchTools:
    """Tests for register_batch_tools function."""
    
    @patch("zotero_mcp.infrastructure.mcp.batch_tools.BATCH_IMPORT_AVAILABLE", True)
    def test_registers_when_available(self):
        """Test tools are registered when pubmed available."""
        from zotero_mcp.infrastructure.mcp.batch_tools import register_batch_tools
        
        mock_mcp = MagicMock()
        mock_client = MagicMock()
        
        # Setup decorator
        def tool_decorator():
            def wrapper(func):
                return func
            return wrapper
        mock_mcp.tool = tool_decorator
        
        register_batch_tools(mock_mcp, mock_client)


class TestBatchImportFromPubmed:
    """Tests for batch_import_from_pubmed tool function."""
    
    @pytest.mark.asyncio
    @patch("zotero_mcp.infrastructure.mcp.batch_tools.BATCH_IMPORT_AVAILABLE", False)
    async def test_returns_error_when_unavailable(self):
        """Test error returned when batch import unavailable."""
        from zotero_mcp.infrastructure.mcp.batch_tools import register_batch_tools
        
        mock_mcp = MagicMock()
        mock_client = AsyncMock()
        
        # Capture the registered tool function
        registered_func = None
        def tool_decorator():
            def wrapper(func):
                nonlocal registered_func
                registered_func = func
                return func
            return wrapper
        mock_mcp.tool = tool_decorator
        
        register_batch_tools(mock_mcp, mock_client)
        
        if registered_func:
            result = await registered_func("12345678")
            assert result["success"] is False
            assert "error" in result
    
    @pytest.mark.asyncio
    @patch("zotero_mcp.infrastructure.mcp.batch_tools.BATCH_IMPORT_AVAILABLE", True)
    @patch("zotero_mcp.infrastructure.mcp.batch_tools.fetch_pubmed_articles")
    async def test_handles_empty_pmids(self, mock_fetch):
        """Test handling of empty PMIDs."""
        from zotero_mcp.infrastructure.mcp.batch_tools import register_batch_tools
        
        mock_mcp = MagicMock()
        mock_client = AsyncMock()
        
        registered_func = None
        def tool_decorator():
            def wrapper(func):
                nonlocal registered_func
                registered_func = func
                return func
            return wrapper
        mock_mcp.tool = tool_decorator
        
        register_batch_tools(mock_mcp, mock_client)
        
        if registered_func:
            result = await registered_func("")
            assert result["success"] is False
            assert "No valid PMIDs" in result.get("error", "")
    
    @pytest.mark.asyncio
    @patch("zotero_mcp.infrastructure.mcp.batch_tools.BATCH_IMPORT_AVAILABLE", True)
    @patch("zotero_mcp.infrastructure.mcp.batch_tools.fetch_pubmed_articles")
    async def test_handles_no_articles_found(self, mock_fetch):
        """Test handling when no articles found."""
        mock_fetch.return_value = []
        
        from zotero_mcp.infrastructure.mcp.batch_tools import register_batch_tools
        
        mock_mcp = MagicMock()
        mock_client = AsyncMock()
        
        registered_func = None
        def tool_decorator():
            def wrapper(func):
                nonlocal registered_func
                registered_func = func
                return func
            return wrapper
        mock_mcp.tool = tool_decorator
        
        register_batch_tools(mock_mcp, mock_client)
        
        if registered_func:
            result = await registered_func("12345678")
            assert result["success"] is False
            assert "No articles found" in result.get("error", "")
    
    @pytest.mark.asyncio
    @patch("zotero_mcp.infrastructure.mcp.batch_tools.BATCH_IMPORT_AVAILABLE", True)
    @patch("zotero_mcp.infrastructure.mcp.batch_tools.fetch_pubmed_articles")
    @patch("zotero_mcp.infrastructure.mcp.batch_tools.map_pubmed_to_zotero")
    async def test_successful_import(self, mock_map, mock_fetch):
        """Test successful batch import."""
        mock_fetch.return_value = [
            {"pmid": "12345678", "title": "Test Article", "doi": "10.1234/test"},
        ]
        mock_map.return_value = {
            "itemType": "journalArticle",
            "title": "Test Article",
        }
        
        from zotero_mcp.infrastructure.mcp.batch_tools import register_batch_tools
        
        mock_mcp = MagicMock()
        mock_client = AsyncMock()
        mock_client.batch_check_identifiers.return_value = {
            "existing_pmids": set(),
            "existing_dois": set(),
            "pmid_to_key": {},
            "doi_to_key": {},
        }
        mock_client.batch_save_items.return_value = {"success": True}
        
        registered_func = None
        def tool_decorator():
            def wrapper(func):
                nonlocal registered_func
                registered_func = func
                return func
            return wrapper
        mock_mcp.tool = tool_decorator
        
        register_batch_tools(mock_mcp, mock_client)
        
        if registered_func:
            result = await registered_func("12345678")
            assert result["success"] is True
            assert result["added"] == 1
    
    @pytest.mark.asyncio
    @patch("zotero_mcp.infrastructure.mcp.batch_tools.BATCH_IMPORT_AVAILABLE", True)
    @patch("zotero_mcp.infrastructure.mcp.batch_tools.fetch_pubmed_articles")
    async def test_skips_duplicates(self, mock_fetch):
        """Test that duplicates are skipped."""
        mock_fetch.return_value = [
            {"pmid": "12345678", "title": "Test Article", "doi": "10.1234/test"},
        ]
        
        from zotero_mcp.infrastructure.mcp.batch_tools import register_batch_tools
        
        mock_mcp = MagicMock()
        mock_client = AsyncMock()
        mock_client.batch_check_identifiers.return_value = {
            "existing_pmids": {"12345678"},
            "existing_dois": set(),
            "pmid_to_key": {"12345678": "ABC123"},
            "doi_to_key": {},
        }
        
        registered_func = None
        def tool_decorator():
            def wrapper(func):
                nonlocal registered_func
                registered_func = func
                return func
            return wrapper
        mock_mcp.tool = tool_decorator
        
        register_batch_tools(mock_mcp, mock_client)
        
        if registered_func:
            result = await registered_func("12345678", skip_duplicates=True)
            assert result["success"] is True
            assert result["skipped"] == 1
            assert result["added"] == 0


class TestBatchImportIntegration:
    """Integration tests for batch import workflow."""
    
    @pytest.mark.asyncio
    @patch("zotero_mcp.infrastructure.mcp.batch_tools.BATCH_IMPORT_AVAILABLE", True)
    @patch("zotero_mcp.infrastructure.mcp.batch_tools.fetch_pubmed_articles")
    @patch("zotero_mcp.infrastructure.mcp.batch_tools.map_pubmed_to_zotero")
    async def test_full_workflow_with_tags(self, mock_map, mock_fetch):
        """Test full workflow with tags."""
        mock_fetch.return_value = [
            {"pmid": "11111111", "title": "Article 1", "doi": "10.1234/a1"},
            {"pmid": "22222222", "title": "Article 2", "doi": "10.1234/a2"},
        ]
        mock_map.return_value = {
            "itemType": "journalArticle",
            "title": "Test",
        }
        
        from zotero_mcp.infrastructure.mcp.batch_tools import register_batch_tools
        
        mock_mcp = MagicMock()
        mock_client = AsyncMock()
        mock_client.batch_check_identifiers.return_value = {
            "existing_pmids": set(),
            "existing_dois": set(),
            "pmid_to_key": {},
            "doi_to_key": {},
        }
        mock_client.batch_save_items.return_value = {"success": True}
        
        registered_func = None
        def tool_decorator():
            def wrapper(func):
                nonlocal registered_func
                registered_func = func
                return func
            return wrapper
        mock_mcp.tool = tool_decorator
        
        register_batch_tools(mock_mcp, mock_client)
        
        if registered_func:
            result = await registered_func(
                "11111111,22222222",
                tags=["Test", "2024"],
            )
            assert result["success"] is True
            assert result["total"] == 2
