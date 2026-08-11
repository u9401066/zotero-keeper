"""Tests for PubMed Search MCP v0.6.1 facade integration."""

import sys
from types import SimpleNamespace

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

import zotero_mcp.infrastructure.pubmed as pubmed_integration
from zotero_mcp.infrastructure.pubmed import (
    fetch_citation_metrics,
    fetch_pubmed_articles,
    get_pubmed_client,
    search_pubmed_raw,
)


def test_get_pubmed_client_builds_v061_facade_from_config(monkeypatch):
    created = {}

    class FakeConfig:
        def __init__(self, *, email, api_key):
            created["config"] = {"email": email, "api_key": api_key}

    class FakeClient:
        def __init__(self, config):
            created["client_config"] = config

    fake_module = SimpleNamespace(
        PubMedSearchClient=FakeClient,
        PubMedSearchConfig=FakeConfig,
    )
    monkeypatch.setitem(sys.modules, "pubmed_search", fake_module)
    monkeypatch.setattr(pubmed_integration, "_configure_pubmed_search", lambda: True)
    monkeypatch.setattr(pubmed_integration, "_pubmed_client", None)
    monkeypatch.setattr(pubmed_integration, "_pubmed_client_signature", None)
    monkeypatch.setenv("NCBI_EMAIL", "researcher@example.com")
    monkeypatch.setenv("NCBI_API_KEY", "test-key")

    client = get_pubmed_client()

    assert isinstance(client, FakeClient)
    assert created["config"] == {
        "email": "researcher@example.com",
        "api_key": "test-key",
    }
    assert created["client_config"] is not None


@pytest.mark.asyncio
@patch("zotero_mcp.infrastructure.pubmed.get_pubmed_client")
async def test_search_pubmed_raw_uses_v061_search_pubmed(mock_get_client):
    client = MagicMock()
    client.search_pubmed = AsyncMock(return_value=[{"pmid": "12345678"}])
    mock_get_client.return_value = client

    result = await search_pubmed_raw(
        "anesthesia AI",
        limit=25,
        min_year=2024,
        strategy="date",
    )

    assert result == [{"pmid": "12345678"}]
    client.search_pubmed.assert_awaited_once_with(
        query="anesthesia AI",
        limit=25,
        min_year=2024,
        max_year=None,
        date_from=None,
        date_to=None,
        article_type=None,
        strategy="date",
    )


@pytest.mark.asyncio
@patch("zotero_mcp.infrastructure.pubmed.get_pubmed_client")
async def test_fetch_citation_metrics_uses_v061_searcher_facade(mock_get_client):
    client = MagicMock()
    client.searcher.get_citation_metrics = AsyncMock(
        return_value={"12345678": {"relative_citation_ratio": 1.5}}
    )
    mock_get_client.return_value = client

    result = await fetch_citation_metrics(["12345678"])

    assert result["12345678"]["relative_citation_ratio"] == 1.5
    client.searcher.get_citation_metrics.assert_awaited_once_with(["12345678"])


class TestFetchPubmedArticles:
    """Tests for the async article fetch helper."""

    @pytest.mark.asyncio
    @patch("zotero_mcp.infrastructure.pubmed.get_pubmed_client")
    async def test_awaits_client_fetch_details(self, mock_get_client):
        """The helper should await async PubMed clients."""
        mock_client = MagicMock()
        mock_client.fetch_details = AsyncMock(return_value=[{"pmid": "12345678"}])
        mock_get_client.return_value = mock_client

        result = await fetch_pubmed_articles(["12345678"])

        assert result == [{"pmid": "12345678"}]
        mock_client.fetch_details.assert_awaited_once_with(["12345678"])

    @pytest.mark.asyncio
    @patch("zotero_mcp.infrastructure.pubmed.get_pubmed_client")
    async def test_accepts_sync_client_fetch_details(self, mock_get_client):
        """The helper should tolerate older or mocked sync PubMed clients."""
        mock_client = MagicMock()
        mock_client.fetch_details.return_value = [{"pmid": "12345678"}]
        mock_get_client.return_value = mock_client

        result = await fetch_pubmed_articles(["12345678"])

        assert result == [{"pmid": "12345678"}]
        mock_client.fetch_details.assert_called_once_with(["12345678"])

    @pytest.mark.asyncio
    @patch("zotero_mcp.infrastructure.pubmed.get_pubmed_client")
    async def test_skips_client_creation_for_empty_identifier_lists(self, mock_get_client):
        """Empty fetch requests should short-circuit before creating a client."""
        result = await fetch_pubmed_articles([])

        assert result == []
        mock_get_client.assert_not_called()
