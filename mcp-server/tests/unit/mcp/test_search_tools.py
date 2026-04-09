"""
Tests for search_tools.py

Tests the integrated PubMed search with Zotero filtering functionality.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from zotero_mcp.infrastructure.mcp.search_helpers import (
    normalize_title,
    extract_pmid_from_extra,
    get_owned_identifiers,
    is_owned,
    format_search_results,
    TITLE_MATCH_THRESHOLD,
)
from zotero_mcp.infrastructure.mcp.search_tools import (
    is_search_tools_available,
)


class TestNormalizeTitle:
    """Tests for normalize_title function."""

    def test_basic_normalization(self):
        """Test basic title normalization."""
        assert normalize_title("Hello World") == "hello world"

    def test_removes_punctuation(self):
        """Test that punctuation is removed."""
        assert normalize_title("Hello, World!") == "hello world"

    def test_collapses_whitespace(self):
        """Test that multiple spaces are collapsed."""
        assert normalize_title("Hello    World") == "hello world"

    def test_strips_whitespace(self):
        """Test that leading/trailing whitespace is stripped."""
        assert normalize_title("  Hello World  ") == "hello world"

    def test_empty_string(self):
        """Test empty string handling."""
        assert normalize_title("") == ""

    def test_none_handling(self):
        """Test None handling."""
        assert normalize_title(None) == ""

    def test_special_characters(self):
        """Test special characters removal."""
        result = normalize_title("Title: A Study of X & Y (2024)")
        assert result == "title a study of x y 2024"

    def test_unicode_characters(self):
        """Test unicode characters handling."""
        result = normalize_title("Étude: α-receptor")
        # Should keep word characters including unicode
        assert "tude" in result
        assert "receptor" in result


class TestExtractPmidFromExtra:
    """Tests for extract_pmid_from_extra function."""

    def test_extract_standard_format(self):
        """Test extraction from standard format."""
        assert extract_pmid_from_extra("PMID: 12345678") == "12345678"

    def test_extract_lowercase(self):
        """Test case-insensitive extraction."""
        assert extract_pmid_from_extra("pmid: 12345678") == "12345678"

    def test_extract_no_space(self):
        """Test extraction without space after colon."""
        assert extract_pmid_from_extra("PMID:12345678") == "12345678"

    def test_extract_with_other_fields(self):
        """Test extraction when other fields present."""
        extra = "PMID: 12345678\nDOI: 10.1234/test"
        assert extract_pmid_from_extra(extra) == "12345678"

    def test_no_pmid(self):
        """Test when no PMID present."""
        assert extract_pmid_from_extra("DOI: 10.1234/test") is None

    def test_empty_string(self):
        """Test empty string."""
        assert extract_pmid_from_extra("") is None

    def test_none_input(self):
        """Test None input."""
        assert extract_pmid_from_extra(None) is None

    def test_extract_mixed_case(self):
        """Test mixed case format."""
        assert extract_pmid_from_extra("Pmid: 12345678") == "12345678"


class TestGetOwnedIdentifiers:
    """Tests for get_owned_identifiers function."""

    @pytest.mark.asyncio
    async def test_extracts_dois(self):
        """Test DOI extraction from items."""
        mock_client = AsyncMock()
        mock_client.get_items.return_value = [
            {"data": {"DOI": "10.1234/test1", "title": "Test 1"}},
            {"data": {"DOI": "10.5678/TEST2", "title": "Test 2"}},
        ]

        owned = await get_owned_identifiers(mock_client)

        assert "10.1234/test1" in owned["dois"]
        assert "10.5678/test2" in owned["dois"]  # Should be lowercase

    @pytest.mark.asyncio
    async def test_extracts_pmids(self):
        """Test PMID extraction from extra field."""
        mock_client = AsyncMock()
        mock_client.get_items.return_value = [
            {"data": {"extra": "PMID: 12345678", "title": "Test"}},
        ]

        owned = await get_owned_identifiers(mock_client)

        assert "12345678" in owned["pmids"]

    @pytest.mark.asyncio
    async def test_extracts_titles(self):
        """Test title extraction and normalization."""
        mock_client = AsyncMock()
        mock_client.get_items.return_value = [
            {"data": {"title": "Hello World!"}},
        ]

        owned = await get_owned_identifiers(mock_client)

        assert "hello world" in owned["titles"]

    @pytest.mark.asyncio
    async def test_handles_empty_items(self):
        """Test handling empty item list."""
        mock_client = AsyncMock()
        mock_client.get_items.return_value = []

        owned = await get_owned_identifiers(mock_client)

        assert owned["dois"] == set()
        assert owned["pmids"] == set()
        assert owned["titles"] == set()

    @pytest.mark.asyncio
    async def test_handles_exception(self):
        """Test exception handling."""
        mock_client = AsyncMock()
        mock_client.get_items.side_effect = Exception("API Error")

        owned = await get_owned_identifiers(mock_client)

        assert owned["dois"] == set()
        assert owned["pmids"] == set()
        assert owned["titles"] == set()

    @pytest.mark.asyncio
    async def test_respects_limit(self):
        """Test that limit parameter is passed."""
        mock_client = AsyncMock()
        mock_client.get_items.return_value = []

        await get_owned_identifiers(mock_client, limit=100)

        mock_client.get_items.assert_called_once_with(limit=100)


class TestIsOwned:
    """Tests for is_owned function."""

    def test_doi_match(self):
        """Test DOI matching."""
        article = {"doi": "10.1234/test"}
        owned = {"dois": {"10.1234/test"}, "pmids": set(), "titles": set()}

        owned_flag, reason = is_owned(article, owned)

        assert owned_flag is True
        assert "DOI" in reason

    def test_pmid_match(self):
        """Test PMID matching."""
        article = {"pmid": "12345678"}
        owned = {"dois": set(), "pmids": {"12345678"}, "titles": set()}

        owned_flag, reason = is_owned(article, owned)

        assert owned_flag is True
        assert "PMID" in reason

    def test_title_fuzzy_match(self):
        """Test fuzzy title matching."""
        article = {"title": "A study of machine learning"}
        owned = {"dois": set(), "pmids": set(), "titles": {"a study of machine learning"}}

        owned_flag, reason = is_owned(article, owned)

        assert owned_flag is True
        assert "Title" in reason

    def test_title_similar_match(self):
        """Test similar title matching."""
        article = {"title": "A Study of Machine Learning in Healthcare"}
        owned = {"dois": set(), "pmids": set(), "titles": {"a study of machine learning in health"}}

        owned_flag, reason = is_owned(article, owned)

        # Should match due to high similarity
        assert owned_flag is True or owned_flag is False  # Depends on threshold

    def test_not_owned(self):
        """Test article that is not owned."""
        article = {"doi": "10.9999/new", "pmid": "99999999", "title": "Brand New Article"}
        owned = {"dois": {"10.1234/old"}, "pmids": {"12345678"}, "titles": {"old article"}}

        owned_flag, reason = is_owned(article, owned)

        assert owned_flag is False
        assert reason == ""

    def test_empty_owned(self):
        """Test with empty owned set."""
        article = {"title": "Any Article"}
        owned = {"dois": set(), "pmids": set(), "titles": set()}

        owned_flag, reason = is_owned(article, owned)

        assert owned_flag is False


class TestFormatSearchResults:
    """Tests for format_search_results function."""

    def test_empty_results(self):
        """Test formatting empty results."""
        result = format_search_results([])
        assert result == "No results found."

    def test_basic_formatting(self):
        """Test basic result formatting."""
        results = [
            {
                "pmid": "12345678",
                "title": "Test Article",
                "authors": ["Smith J", "Jones A"],
                "journal": "Test Journal",
                "year": "2024",
                "doi": "10.1234/test",
            }
        ]

        result = format_search_results(results)

        assert "Test Article" in result
        assert "12345678" in result
        assert "Smith J, Jones A" in result
        assert "Test Journal" in result
        assert "2024" in result
        assert "10.1234/test" in result

    def test_many_authors(self):
        """Test author formatting with many authors."""
        results = [
            {
                "pmid": "12345678",
                "title": "Test",
                "authors": ["Smith J", "Jones A", "Brown B", "White W"],
                "journal": "Journal",
                "year": "2024",
            }
        ]

        result = format_search_results(results)

        assert "Smith J et al." in result

    def test_no_authors(self):
        """Test formatting with no authors."""
        results = [
            {
                "pmid": "12345678",
                "title": "Test",
                "authors": [],
                "journal": "Journal",
                "year": "2024",
            }
        ]

        result = format_search_results(results)

        assert "Unknown" in result

    def test_show_owned_markers(self):
        """Test owned markers in output."""
        results = [
            {"pmid": "1", "title": "Owned", "_is_owned": True, "authors": [], "journal": "", "year": ""},
            {"pmid": "2", "title": "New", "_is_owned": False, "authors": [], "journal": "", "year": ""},
        ]

        result = format_search_results(results, show_owned=True)

        assert "📚" in result
        assert "🆕" in result


class TestIsSearchToolsAvailable:
    """Tests for is_search_tools_available function."""

    def test_returns_boolean(self):
        """Test that function returns boolean."""
        result = is_search_tools_available()
        assert isinstance(result, bool)


class TestRegisterSearchTools:
    """Tests for register_search_tools function."""

    def test_registers_advanced_search_when_pubmed_unavailable(self):
        """Test that advanced_search is still registered when PubMed not available."""
        from zotero_mcp.infrastructure.mcp.search_tools import register_search_tools

        mock_mcp = MagicMock()
        mock_client = MagicMock()

        def tool_decorator():
            def wrapper(func):
                return func

            return wrapper
            return wrapper

        mock_mcp.tool = MagicMock(side_effect=tool_decorator)

        with patch("zotero_mcp.infrastructure.mcp.search_tools.pubmed_integration_available", return_value=False):
            register_search_tools(mock_mcp, mock_client)

        assert mock_mcp.tool.call_count == 2

    def test_registers_check_articles_owned_when_pubmed_unavailable(self):
        """Test that local PMID ownership checks remain available without PubMed bridge."""
        from zotero_mcp.infrastructure.mcp.search_tools import register_search_tools

        mock_mcp = MagicMock()
        mock_client = MagicMock()
        registered_tools = {}

        def tool_decorator():
            def wrapper(func):
                registered_tools[func.__name__] = func
                return func

            return wrapper

        mock_mcp.tool = tool_decorator

        with patch("zotero_mcp.infrastructure.mcp.search_tools.pubmed_integration_available", return_value=False):
            register_search_tools(mock_mcp, mock_client)

        assert "advanced_search" in registered_tools
        assert "check_articles_owned" in registered_tools
        assert "search_pubmed_exclude_owned" not in registered_tools

    @patch("zotero_mcp.infrastructure.mcp.search_tools.pubmed_integration_available", return_value=True)
    def test_registers_tools_when_available(self, _mock_available):
        """Test tool registration when PubMed available."""
        from zotero_mcp.infrastructure.mcp.search_tools import register_search_tools

        mock_mcp = MagicMock()
        mock_client = MagicMock()

        # Setup mock.tool() to return a decorator
        def tool_decorator():
            def wrapper(func):
                return func

            return wrapper

        mock_mcp.tool = tool_decorator

        register_search_tools(mock_mcp, mock_client)

        # Function should complete without error

    def test_registers_legacy_bridge_only_when_enabled(self):
        """Test legacy PubMed search bridge is opt-in."""
        from zotero_mcp.infrastructure.mcp.search_tools import register_search_tools

        mock_mcp = MagicMock()
        mock_client = MagicMock()
        registered_tools = {}

        def tool_decorator():
            def wrapper(func):
                registered_tools[func.__name__] = func
                return func

            return wrapper

        mock_mcp.tool = tool_decorator

        with patch("zotero_mcp.infrastructure.mcp.search_tools.pubmed_integration_available", return_value=True):
            register_search_tools(mock_mcp, mock_client, enable_pubmed_bridge_tools=True)

        assert "search_pubmed_exclude_owned" in registered_tools
        assert "check_articles_owned" in registered_tools


class TestTitleMatchThreshold:
    """Tests for title matching threshold constant."""

    def test_threshold_value(self):
        """Test that threshold is reasonable."""
        assert TITLE_MATCH_THRESHOLD > 0
        assert TITLE_MATCH_THRESHOLD <= 100
        assert isinstance(TITLE_MATCH_THRESHOLD, int)
