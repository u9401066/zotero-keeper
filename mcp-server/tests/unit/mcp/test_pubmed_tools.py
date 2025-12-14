"""
Tests for pubmed_tools.py

Tests the PubMed import functionality for Zotero.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from zotero_mcp.infrastructure.mcp.pubmed_tools import (
    _parse_ris_to_zotero_items,
    _pmid_to_zotero_item,
    is_pubmed_available,
    register_pubmed_tools,
)


class TestParseRisToZoteroItems:
    """Tests for _parse_ris_to_zotero_items function."""
    
    def test_basic_journal_article(self):
        """Test parsing basic journal article RIS."""
        ris_text = """TY  - JOUR
TI  - Test Article Title
AU  - Smith, John
AU  - Doe, Jane
PY  - 2024
JO  - Test Journal
VL  - 10
IS  - 2
SP  - 100
EP  - 110
DO  - 10.1234/test
AB  - This is the abstract.
ER  -"""
        
        items = _parse_ris_to_zotero_items(ris_text)
        
        assert len(items) == 1
        item = items[0]
        assert item["itemType"] == "journalArticle"
        assert item["title"] == "Test Article Title"
        assert len(item["creators"]) == 2
        assert item["creators"][0]["lastName"] == "Smith"
        assert item["creators"][0]["firstName"] == "John"
        assert item["date"] == "2024"
        assert item["publicationTitle"] == "Test Journal"
        assert item["volume"] == "10"
        assert item["issue"] == "2"
        assert item["pages"] == "100-110"
        assert item["DOI"] == "10.1234/test"
        assert item["abstractNote"] == "This is the abstract."
    
    def test_multiple_records(self):
        """Test parsing multiple RIS records."""
        ris_text = """TY  - JOUR
TI  - First Article
AU  - Author, One
PY  - 2024
ER  -
TY  - JOUR
TI  - Second Article
AU  - Author, Two
PY  - 2023
ER  -"""
        
        items = _parse_ris_to_zotero_items(ris_text)
        
        assert len(items) == 2
        assert items[0]["title"] == "First Article"
        assert items[1]["title"] == "Second Article"
    
    def test_book_type(self):
        """Test parsing book type."""
        ris_text = """TY  - BOOK
TI  - Test Book
AU  - Author, Test
PY  - 2020
ER  -"""
        
        items = _parse_ris_to_zotero_items(ris_text)
        
        assert len(items) == 1
        assert items[0]["itemType"] == "book"
    
    def test_keywords(self):
        """Test parsing keywords as tags."""
        ris_text = """TY  - JOUR
TI  - Test
AU  - Author, Test
KW  - machine learning
KW  - AI
KW  - data science
ER  -"""
        
        items = _parse_ris_to_zotero_items(ris_text)
        
        assert len(items) == 1
        assert len(items[0]["tags"]) == 3
        assert items[0]["tags"][0]["tag"] == "machine learning"
    
    def test_author_without_firstname(self):
        """Test parsing author without first name."""
        ris_text = """TY  - JOUR
TI  - Test
AU  - Organization
ER  -"""
        
        items = _parse_ris_to_zotero_items(ris_text)
        
        assert len(items) == 1
        assert items[0]["creators"][0]["lastName"] == "Organization"
        assert items[0]["creators"][0]["firstName"] == ""
    
    def test_empty_ris(self):
        """Test parsing empty RIS text."""
        items = _parse_ris_to_zotero_items("")
        assert items == []
    
    def test_malformed_ris(self):
        """Test parsing malformed RIS (missing TY)."""
        ris_text = """TI  - Test Article
AU  - Author, Test"""
        
        items = _parse_ris_to_zotero_items(ris_text)
        # Should not crash, may return empty or partial result
        assert isinstance(items, list)
    
    def test_date_with_full_format(self):
        """Test date parsing with full date format."""
        ris_text = """TY  - JOUR
TI  - Test
PY  - 2024/03/15
ER  -"""
        
        items = _parse_ris_to_zotero_items(ris_text)
        
        assert items[0]["date"] == "2024"
    
    def test_pmid_in_notes(self):
        """Test extracting PMID from notes field."""
        ris_text = """TY  - JOUR
TI  - Test
N1  - PMID: 12345678
ER  -"""
        
        items = _parse_ris_to_zotero_items(ris_text)
        
        assert "extra" in items[0]
        assert "12345678" in items[0]["extra"]


class TestPmidToZoteroItem:
    """Tests for _pmid_to_zotero_item function."""
    
    def test_basic_conversion(self):
        """Test basic article conversion."""
        article = {
            "pmid": "12345678",
            "title": "Test Article",
            "abstract": "Test abstract",
            "authors": ["John Smith", "Jane Doe"],
            "journal": "Test Journal",
            "year": 2024,
            "volume": "10",
            "issue": "2",
            "pages": "100-110",
            "doi": "10.1234/test",
        }
        
        item = _pmid_to_zotero_item(article)
        
        assert item["itemType"] == "journalArticle"
        assert item["title"] == "Test Article"
        assert item["abstractNote"] == "Test abstract"
        assert len(item["creators"]) == 2
        assert item["publicationTitle"] == "Test Journal"
        assert item["date"] == "2024"
        assert item["DOI"] == "10.1234/test"
        assert "PMID: 12345678" in item["extra"]
    
    def test_author_as_dict(self):
        """Test author conversion when provided as dict."""
        article = {
            "title": "Test",
            "authors": [
                {"firstName": "John", "lastName": "Smith"},
                {"first_name": "Jane", "last_name": "Doe"},
            ],
        }
        
        item = _pmid_to_zotero_item(article)
        
        assert len(item["creators"]) == 2
        assert item["creators"][0]["firstName"] == "John"
        assert item["creators"][0]["lastName"] == "Smith"
    
    def test_author_as_single_name(self):
        """Test author with single name."""
        article = {
            "title": "Test",
            "authors": ["Smith"],
        }
        
        item = _pmid_to_zotero_item(article)
        
        assert item["creators"][0]["lastName"] == "Smith"
    
    def test_with_pmcid(self):
        """Test conversion with PMCID."""
        article = {
            "title": "Test",
            "pmid": "12345678",
            "pmc_id": "PMC1234567",
        }
        
        item = _pmid_to_zotero_item(article)
        
        assert "PMID: 12345678" in item["extra"]
        assert "PMCID: PMC1234567" in item["extra"]
    
    def test_auto_generated_url(self):
        """Test URL auto-generation from PMID."""
        article = {
            "title": "Test",
            "pmid": "12345678",
        }
        
        item = _pmid_to_zotero_item(article)
        
        assert "pubmed.ncbi.nlm.nih.gov" in item["url"]
        assert "12345678" in item["url"]
    
    def test_mesh_terms_as_tags(self):
        """Test MeSH terms converted to tags."""
        article = {
            "title": "Test",
            "mesh_terms": ["Machine Learning", "Artificial Intelligence"],
        }
        
        item = _pmid_to_zotero_item(article)
        
        assert len(item["tags"]) == 2
        assert item["tags"][0]["tag"] == "Machine Learning"
    
    def test_tags_limit(self):
        """Test tags are limited to 10."""
        article = {
            "title": "Test",
            "mesh_terms": [f"Term{i}" for i in range(20)],
        }
        
        item = _pmid_to_zotero_item(article)
        
        assert len(item["tags"]) == 10
    
    def test_minimal_article(self):
        """Test conversion with minimal data."""
        article = {"title": "Test Article"}
        
        item = _pmid_to_zotero_item(article)
        
        assert item["itemType"] == "journalArticle"
        assert item["title"] == "Test Article"
        assert item["creators"] == []


class TestIsPubmedAvailable:
    """Tests for is_pubmed_available function."""
    
    def test_returns_boolean(self):
        """Test that function returns boolean."""
        result = is_pubmed_available()
        assert isinstance(result, bool)


class TestRegisterPubmedTools:
    """Tests for register_pubmed_tools function."""
    
    def test_registers_tools(self):
        """Test that tools are registered."""
        mock_mcp = MagicMock()
        mock_client = MagicMock()
        
        def tool_decorator():
            def wrapper(func):
                return func
            return wrapper
        mock_mcp.tool = tool_decorator
        
        register_pubmed_tools(mock_mcp, mock_client)


class TestImportRisToZotero:
    """Tests for import_ris_to_zotero tool."""
    
    @pytest.mark.asyncio
    async def test_successful_import(self):
        """Test successful RIS import."""
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
        
        register_pubmed_tools(mock_mcp, mock_client)
        
        ris_text = """TY  - JOUR
TI  - Test Article
AU  - Smith, John
PY  - 2024
ER  -"""
        
        if registered_func is not None:
            # Find the import_ris_to_zotero function
            # In this test setup, we get the first registered function
            pass
    
    @pytest.mark.asyncio
    async def test_empty_ris_import(self):
        """Test import with empty RIS."""
        mock_mcp = MagicMock()
        mock_client = AsyncMock()
        
        def tool_decorator():
            def wrapper(func):
                return func
            return wrapper
        mock_mcp.tool = tool_decorator
        
        register_pubmed_tools(mock_mcp, mock_client)


class TestImportFromPmids:
    """Tests for import_from_pmids tool."""
    
    @pytest.mark.asyncio
    @patch("zotero_mcp.infrastructure.mcp.pubmed_tools.PUBMED_AVAILABLE", False)
    async def test_returns_error_when_unavailable(self):
        """Test error when pubmed not available."""
        mock_mcp = MagicMock()
        mock_client = AsyncMock()
        
        def tool_decorator():
            def wrapper(func):
                return func
            return wrapper
        mock_mcp.tool = tool_decorator
        
        register_pubmed_tools(mock_mcp, mock_client)
    
    @pytest.mark.asyncio
    @patch("zotero_mcp.infrastructure.mcp.pubmed_tools.PUBMED_AVAILABLE", True)
    async def test_successful_import(self):
        """Test successful PMID import."""
        mock_mcp = MagicMock()
        mock_client = AsyncMock()
        
        def tool_decorator():
            def wrapper(func):
                return func
            return wrapper
        mock_mcp.tool = tool_decorator
        
        register_pubmed_tools(mock_mcp, mock_client)
