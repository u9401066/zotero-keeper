"""
Tests for interactive_tools.py

Tests the interactive save tools including metadata fetching and elicitation.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from zotero_mcp.infrastructure.mcp.interactive_tools import (
    _fetch_metadata_from_doi,
    _merge_metadata,
    _format_collection_options,
    _num_to_collection_key,
    _normalize_title,
    _get_required_fields,
    _validate_item,
    CollectionChoiceSchema,
    DuplicateConfirmSchema,
)


class TestFetchMetadataFromDoi:
    """Tests for _fetch_metadata_from_doi function."""
    
    @pytest.mark.asyncio
    async def test_successful_fetch(self):
        """Test successful metadata fetch from CrossRef."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "message": {
                "title": ["Test Article Title"],
                "DOI": "10.1234/test",
                "abstract": "<p>Test abstract</p>",
                "author": [
                    {"given": "John", "family": "Smith"},
                    {"given": "Jane", "family": "Doe"},
                ],
                "container-title": ["Test Journal"],
                "published": {"date-parts": [[2024, 1, 15]]},
                "volume": "10",
                "issue": "2",
                "page": "100-110",
                "URL": "https://example.com/article",
            }
        }
        
        with patch("httpx.AsyncClient") as mock_client:
            mock_client.return_value.__aenter__.return_value.get = AsyncMock(
                return_value=mock_response
            )
            
            result = await _fetch_metadata_from_doi("10.1234/test")
        
        assert result is not None
        assert result["title"] == "Test Article Title"
        assert result["DOI"] == "10.1234/test"
        assert "Test abstract" in result.get("abstractNote", "")
        assert len(result["creators"]) == 2
        assert result["publicationTitle"] == "Test Journal"
        assert "2024" in result["date"]
        assert result["volume"] == "10"
        assert result["issue"] == "2"
        assert result["pages"] == "100-110"
    
    @pytest.mark.asyncio
    async def test_not_found(self):
        """Test handling of 404 response."""
        mock_response = MagicMock()
        mock_response.status_code = 404
        
        with patch("httpx.AsyncClient") as mock_client:
            mock_client.return_value.__aenter__.return_value.get = AsyncMock(
                return_value=mock_response
            )
            
            result = await _fetch_metadata_from_doi("10.9999/notfound")
        
        assert result is None
    
    @pytest.mark.asyncio
    async def test_exception_handling(self):
        """Test exception handling."""
        with patch("httpx.AsyncClient") as mock_client:
            mock_client.return_value.__aenter__.return_value.get = AsyncMock(
                side_effect=Exception("Network error")
            )
            
            result = await _fetch_metadata_from_doi("10.1234/test")
        
        assert result is None


class TestMergeMetadata:
    """Tests for _merge_metadata function."""
    
    def test_user_data_takes_priority(self):
        """Test that user-provided data takes priority."""
        user_input = {"title": "User Title", "itemType": "journalArticle"}
        fetched = {"title": "Fetched Title", "abstract": "Fetched Abstract"}
        
        result = _merge_metadata(user_input, fetched)
        
        assert result["title"] == "User Title"
        assert result["abstract"] == "Fetched Abstract"
    
    def test_fetched_fills_gaps(self):
        """Test that fetched data fills missing fields."""
        user_input = {"title": "User Title"}
        fetched = {"title": "Fetched Title", "abstractNote": "Abstract", "DOI": "10.1234/test"}
        
        result = _merge_metadata(user_input, fetched)
        
        assert result["title"] == "User Title"
        assert result["abstractNote"] == "Abstract"
        assert result["DOI"] == "10.1234/test"
    
    def test_empty_user_values_ignored(self):
        """Test that empty user values don't override fetched."""
        user_input = {"title": "", "abstract": None, "tags": []}
        fetched = {"title": "Fetched Title", "abstract": "Fetched Abstract", "tags": ["tag1"]}
        
        result = _merge_metadata(user_input, fetched)
        
        assert result["title"] == "Fetched Title"
        assert result["abstract"] == "Fetched Abstract"
        assert result["tags"] == ["tag1"]


class TestFormatCollectionOptions:
    """Tests for _format_collection_options function."""
    
    def test_basic_formatting(self):
        """Test basic collection formatting."""
        collections = [
            {"key": "ABC123", "name": "Collection A", "itemCount": 10},
            {"key": "DEF456", "name": "Collection B", "itemCount": 5},
        ]
        
        text, key_to_num = _format_collection_options(collections)
        
        assert "Collection A" in text
        assert "Collection B" in text
        assert "10 items" in text
        assert key_to_num["ABC123"] == 1
        assert key_to_num["DEF456"] == 2
    
    def test_with_suggestions(self):
        """Test formatting with suggestions."""
        collections = [
            {"key": "ABC123", "name": "Collection A", "itemCount": 10},
        ]
        suggestions = [
            {"key": "ABC123", "name": "Collection A", "score": 85, "reason": "Title match"},
        ]
        
        text, key_to_num = _format_collection_options(collections, suggestions)
        
        assert "Suggested" in text
        assert "85%" in text or "match: 85" in text
    
    def test_includes_no_collection_option(self):
        """Test that 'no collection' option is included."""
        collections = [{"key": "ABC123", "name": "Test", "itemCount": 5}]
        
        text, key_to_num = _format_collection_options(collections)
        
        assert "0." in text
        assert "My Library" in text
    
    def test_empty_collections(self):
        """Test handling empty collections."""
        text, key_to_num = _format_collection_options([])
        
        assert "0." in text  # Should still have no-collection option
        assert key_to_num == {}


class TestNumToCollectionKey:
    """Tests for _num_to_collection_key function."""
    
    def test_valid_number(self):
        """Test valid number conversion."""
        key_to_num = {"ABC123": 1, "DEF456": 2}
        
        assert _num_to_collection_key("1", key_to_num) == "ABC123"
        assert _num_to_collection_key("2", key_to_num) == "DEF456"
    
    def test_zero_returns_none(self):
        """Test that 0 returns None (no collection)."""
        key_to_num = {"ABC123": 1}
        
        result = _num_to_collection_key("0", key_to_num)
        
        assert result is None
    
    def test_invalid_number(self):
        """Test invalid number handling."""
        key_to_num = {"ABC123": 1}
        
        assert _num_to_collection_key("99", key_to_num) is None
        assert _num_to_collection_key("-1", key_to_num) is None
    
    def test_non_numeric_input(self):
        """Test non-numeric input handling."""
        key_to_num = {"ABC123": 1}
        
        assert _num_to_collection_key("abc", key_to_num) is None
        assert _num_to_collection_key("", key_to_num) is None
    
    def test_whitespace_handling(self):
        """Test whitespace is stripped."""
        key_to_num = {"ABC123": 1}
        
        assert _num_to_collection_key("  1  ", key_to_num) == "ABC123"


class TestNormalizeTitle:
    """Tests for _normalize_title function."""
    
    def test_basic_normalization(self):
        """Test basic title normalization."""
        assert _normalize_title("Hello World") == "hello world"
    
    def test_punctuation_removal(self):
        """Test punctuation removal."""
        assert _normalize_title("Hello, World!") == "hello world"
    
    def test_empty_string(self):
        """Test empty string."""
        assert _normalize_title("") == ""
    
    def test_none_handling(self):
        """Test None handling."""
        assert _normalize_title(None) == ""


class TestGetRequiredFields:
    """Tests for _get_required_fields function."""
    
    def test_journal_article(self):
        """Test required fields for journal article."""
        fields = _get_required_fields("journalArticle")
        assert "title" in fields
        assert "creators" in fields
    
    def test_book(self):
        """Test required fields for book."""
        fields = _get_required_fields("book")
        assert "title" in fields
        assert "creators" in fields
    
    def test_book_section(self):
        """Test required fields for book section."""
        fields = _get_required_fields("bookSection")
        assert "bookTitle" in fields
    
    def test_thesis(self):
        """Test required fields for thesis."""
        fields = _get_required_fields("thesis")
        assert "university" in fields
    
    def test_webpage(self):
        """Test required fields for webpage."""
        fields = _get_required_fields("webpage")
        assert "url" in fields
    
    def test_unknown_type(self):
        """Test unknown type returns minimal fields."""
        fields = _get_required_fields("unknown")
        assert "title" in fields


class TestValidateItem:
    """Tests for _validate_item function."""
    
    def test_valid_journal_article(self):
        """Test validation of valid journal article."""
        item = {
            "itemType": "journalArticle",
            "title": "Test Article",
            "creators": [{"firstName": "John", "lastName": "Smith", "creatorType": "author"}],
            "publicationTitle": "Test Journal",
            "DOI": "10.1234/test",
        }
        
        result = _validate_item(item)
        
        assert result["valid"] is True
        assert result["errors"] == []
    
    def test_missing_title(self):
        """Test validation fails for missing title."""
        item = {
            "itemType": "journalArticle",
            "creators": [{"firstName": "John", "lastName": "Smith"}],
        }
        
        result = _validate_item(item)
        
        assert result["valid"] is False
        assert any("title" in err for err in result["errors"])
    
    def test_missing_creators(self):
        """Test validation fails for missing creators."""
        item = {
            "itemType": "journalArticle",
            "title": "Test",
            "creators": [],
        }
        
        result = _validate_item(item)
        
        assert result["valid"] is False
        assert any("creators" in err for err in result["errors"])
    
    def test_warnings_for_recommended_fields(self):
        """Test warnings for recommended fields."""
        item = {
            "itemType": "journalArticle",
            "title": "Test",
            "creators": [{"firstName": "John", "lastName": "Smith"}],
            # Missing publicationTitle and DOI
        }
        
        result = _validate_item(item)
        
        assert len(result["warnings"]) > 0


class TestPydanticSchemas:
    """Tests for Pydantic schemas."""
    
    def test_collection_choice_schema(self):
        """Test CollectionChoiceSchema."""
        schema = CollectionChoiceSchema(choice="1")
        assert schema.choice == "1"
    
    def test_duplicate_confirm_schema(self):
        """Test DuplicateConfirmSchema."""
        schema = DuplicateConfirmSchema(confirm="yes")
        assert schema.confirm == "yes"


class TestRegisterInteractiveSaveTools:
    """Tests for register_interactive_save_tools function."""
    
    def test_registration(self):
        """Test that tools are registered."""
        from zotero_mcp.infrastructure.mcp.interactive_tools import register_interactive_save_tools
        
        mock_mcp = MagicMock()
        mock_client = MagicMock()
        
        # Setup mock.tool() decorator
        def tool_decorator():
            def wrapper(func):
                return func
            return wrapper
        mock_mcp.tool = tool_decorator
        
        # Should complete without error
        register_interactive_save_tools(mock_mcp, mock_client)
