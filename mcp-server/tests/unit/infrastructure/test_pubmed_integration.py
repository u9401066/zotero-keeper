"""Tests for async PubMed integration helpers."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from zotero_mcp.infrastructure.pubmed import fetch_pubmed_articles


class TestFetchPubmedArticles:
    """Tests for the async article fetch helper."""

    @pytest.mark.asyncio
    @patch("zotero_mcp.infrastructure.pubmed.get_pubmed_client")
    async def test_awaits_client_fetch_details(self, mock_get_client):
        """The helper should await the v0.5.6 async PubMed client."""
        mock_client = MagicMock()
        mock_client.fetch_details = AsyncMock(return_value=[{"pmid": "12345678"}])
        mock_get_client.return_value = mock_client

        result = await fetch_pubmed_articles(["12345678"])

        assert result == [{"pmid": "12345678"}]
        mock_client.fetch_details.assert_awaited_once_with(["12345678"])

    @pytest.mark.asyncio
    @patch("zotero_mcp.infrastructure.pubmed.get_pubmed_client")
    async def test_skips_client_creation_for_empty_identifier_lists(self, mock_get_client):
        """Empty fetch requests should short-circuit before creating a client."""
        result = await fetch_pubmed_articles([])

        assert result == []
        mock_get_client.assert_not_called()
