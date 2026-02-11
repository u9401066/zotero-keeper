"""
Pytest Configuration and Shared Fixtures for Zotero Keeper Tests.

Provides common fixtures for unit and integration tests.
"""

import pytest
from unittest.mock import AsyncMock, Mock


# ============================================================
# Configuration Fixtures
# ============================================================


@pytest.fixture
def mock_config():
    """Provide mock ZoteroConfig."""
    from zotero_mcp.infrastructure.zotero_client.client import ZoteroConfig

    return ZoteroConfig(host="localhost", port=23119, timeout=30.0)


@pytest.fixture
def remote_config():
    """Provide remote ZoteroConfig for testing Host header."""
    from zotero_mcp.infrastructure.zotero_client.client import ZoteroConfig

    return ZoteroConfig(host="192.168.1.100", port=23119)


# ============================================================
# Mock Zotero API Responses
# ============================================================


@pytest.fixture
def mock_item_data():
    """Mock Zotero item data."""
    return {
        "key": "ABC12345",
        "data": {
            "key": "ABC12345",
            "itemType": "journalArticle",
            "title": "Test Article: Machine Learning in Medicine",
            "creators": [
                {"firstName": "John", "lastName": "Smith", "creatorType": "author"},
                {"firstName": "Jane", "lastName": "Doe", "creatorType": "author"},
            ],
            "date": "2024-01-15",
            "DOI": "10.1000/test.2024.001",
            "url": "https://example.com/article",
            "abstractNote": "This is a test abstract about machine learning.",
            "publicationTitle": "Journal of Test Medicine",
            "volume": "10",
            "issue": "1",
            "pages": "100-110",
            "tags": [{"tag": "machine learning"}, {"tag": "medicine"}],
            "collections": ["COL12345"],
            "extra": "PMID: 12345678\nPMCID: PMC9876543",
        },
    }


@pytest.fixture
def mock_collection_data():
    """Mock Zotero collection data."""
    return {
        "key": "COL12345",
        "data": {
            "key": "COL12345",
            "name": "AI Research",
            "parentCollection": None,
            "numItems": 25,
        },
    }


@pytest.fixture
def mock_collection_list():
    """Mock list of collections for tree building."""
    return [
        {
            "key": "COL001",
            "data": {"key": "COL001", "name": "Research", "parentCollection": None, "numItems": 10},
        },
        {
            "key": "COL002",
            "data": {"key": "COL002", "name": "AI Papers", "parentCollection": "COL001", "numItems": 5},
        },
        {
            "key": "COL003",
            "data": {"key": "COL003", "name": "ML Papers", "parentCollection": "COL001", "numItems": 3},
        },
        {
            "key": "COL004",
            "data": {"key": "COL004", "name": "Archive", "parentCollection": None, "numItems": 20},
        },
    ]


@pytest.fixture
def mock_search_data():
    """Mock Zotero saved search data."""
    return {
        "key": "SRCH001",
        "data": {
            "key": "SRCH001",
            "name": "Recent AI Papers",
            "conditions": [
                {"condition": "tag", "operator": "contains", "value": "AI"},
                {"condition": "dateAdded", "operator": "isAfter", "value": "2024-01-01"},
            ],
        },
    }


@pytest.fixture
def mock_tags():
    """Mock Zotero tags."""
    return [
        {"tag": "machine learning", "meta": {"numItems": 10}},
        {"tag": "AI", "meta": {"numItems": 15}},
        {"tag": "medicine", "meta": {"numItems": 8}},
    ]


# ============================================================
# Mock PubMed Data
# ============================================================


@pytest.fixture
def mock_pubmed_article():
    """Mock PubMed article from pubmed-search library."""
    return {
        "pmid": "38353755",
        "title": "Artificial Intelligence in Anesthesiology: A Systematic Review",
        "abstract": "Background: AI is transforming anesthesiology. "
        "Methods: We conducted a systematic review. "
        "Results: We found 150 relevant studies. "
        "Conclusion: AI shows promise in anesthesia.",
        "authors": ["Smith J", "Doe J", "Johnson A"],
        "authors_full": [
            {"last_name": "Smith", "fore_name": "John", "initials": "J", "affiliations": ["MIT"]},
            {"last_name": "Doe", "fore_name": "Jane", "initials": "J", "affiliations": ["Stanford"]},
            {"last_name": "Johnson", "fore_name": "Alice", "initials": "A", "affiliations": []},
        ],
        "journal": "Journal of Anesthesiology",
        "journal_abbrev": "J Anesth",
        "year": "2024",
        "month": "Feb",
        "day": "15",
        "volume": "140",
        "issue": "2",
        "pages": "e100-e115",
        "doi": "10.1234/janesth.2024.001",
        "pmc_id": "PMC11111111",
        "issn": "1234-5678",
        "language": "eng",
        "keywords": ["artificial intelligence", "anesthesiology", "machine learning"],
        "mesh_terms": ["Artificial Intelligence", "Anesthesiology", "Systematic Review"],
        "publication_types": ["Systematic Review"],
    }


@pytest.fixture
def mock_pubmed_articles(mock_pubmed_article):
    """List of mock PubMed articles."""
    article2 = dict(mock_pubmed_article)
    article2.update(
        {
            "pmid": "37864754",
            "title": "Deep Learning for Sedation Monitoring",
            "doi": "10.1234/deep.2024.002",
        }
    )

    article3 = dict(mock_pubmed_article)
    article3.update(
        {
            "pmid": "38215710",
            "title": "Neural Networks in Critical Care",
            "doi": "10.1234/nn.2024.003",
        }
    )

    return [mock_pubmed_article, article2, article3]


# ============================================================
# Mock Client Fixtures
# ============================================================


@pytest.fixture
def mock_zotero_client(mock_item_data, mock_collection_data, mock_collection_list):
    """Create a mock ZoteroClient."""
    client = AsyncMock()

    # Configure basic methods
    client.ping.return_value = True
    client.get_items.return_value = [mock_item_data]
    client.get_item.return_value = mock_item_data
    client.search_items.return_value = [mock_item_data]
    client.get_collections.return_value = mock_collection_list
    client.get_collection.return_value = mock_collection_data
    client.get_collection_items.return_value = [mock_item_data]
    client.get_tags.return_value = [{"tag": "AI"}, {"tag": "ML"}]
    client.get_item_types.return_value = [
        {"itemType": "journalArticle"},
        {"itemType": "book"},
        {"itemType": "bookSection"},
    ]
    client.save_items.return_value = {"success": True, "items": []}
    client.batch_save_items.return_value = {"success": True}
    client.batch_check_identifiers.return_value = {
        "existing_pmids": set(),
        "existing_dois": set(),
        "pmid_to_key": {},
        "doi_to_key": {},
    }
    client.close.return_value = None

    return client


@pytest.fixture
def mock_pubmed_client(mock_pubmed_articles):
    """Create a mock PubMedClient."""
    client = Mock()
    client.fetch_details.return_value = mock_pubmed_articles
    client.search_raw.return_value = mock_pubmed_articles
    return client


# ============================================================
# HTTP Mock Fixtures
# ============================================================


@pytest.fixture
def mock_httpx_client():
    """Mock httpx AsyncClient for testing HTTP operations."""
    mock_response = Mock()
    mock_response.status_code = 200
    mock_response.text = '{"success": true}'
    mock_response.json.return_value = {"success": True}

    client = AsyncMock()
    client.request.return_value = mock_response
    client.aclose.return_value = None

    return client


# ============================================================
# Test Data Fixtures
# ============================================================


@pytest.fixture
def sample_reference_dict():
    """Sample dictionary for Reference.from_zotero_dict()."""
    return {
        "key": "REF001",
        "itemType": "journalArticle",
        "title": "Sample Reference",
        "creators": [
            {"firstName": "Test", "lastName": "Author", "creatorType": "author"},
        ],
        "date": "2024",
        "DOI": "10.1234/sample",
        "tags": [{"tag": "test"}, "plain_tag"],
    }


@pytest.fixture
def sample_creator_names():
    """Sample creator names for testing parsing."""
    return [
        "John Smith",
        "Jane",
        "Alice B. Johnson",
        "Dr. Robert Williams Jr.",
    ]


# ============================================================
# Environment Fixtures
# ============================================================


@pytest.fixture
def clean_env(monkeypatch):
    """Clean environment variables for testing."""
    monkeypatch.delenv("ZOTERO_HOST", raising=False)
    monkeypatch.delenv("ZOTERO_PORT", raising=False)
    monkeypatch.delenv("ZOTERO_TIMEOUT", raising=False)
    monkeypatch.delenv("NCBI_EMAIL", raising=False)
    monkeypatch.delenv("NCBI_API_KEY", raising=False)


@pytest.fixture
def mock_env(monkeypatch):
    """Set up mock environment variables."""
    monkeypatch.setenv("ZOTERO_HOST", "test-host")
    monkeypatch.setenv("ZOTERO_PORT", "12345")
    monkeypatch.setenv("ZOTERO_TIMEOUT", "60")
    monkeypatch.setenv("NCBI_EMAIL", "test@example.com")
    monkeypatch.setenv("NCBI_API_KEY", "fake-api-key")


# ============================================================
# Async Test Support
# ============================================================


@pytest.fixture
def event_loop_policy():
    """Provide event loop policy for async tests."""
    import asyncio

    return asyncio.DefaultEventLoopPolicy()
