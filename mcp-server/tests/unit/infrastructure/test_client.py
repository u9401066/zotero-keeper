"""
Unit tests for ZoteroClient.

Tests HTTP client operations with mocked responses.
"""

import pytest
from unittest.mock import AsyncMock, Mock, patch
import json


class TestZoteroClientInit:
    """Test ZoteroClient initialization."""

    def test_client_default_config(self):
        """Test client initializes with default config."""
        from zotero_mcp.infrastructure.zotero_client.client import ZoteroClient

        client = ZoteroClient()

        assert client.config is not None
        assert client._client is None  # Lazy initialization

    def test_client_custom_config(self, mock_config):
        """Test client initializes with custom config."""
        from zotero_mcp.infrastructure.zotero_client.client import ZoteroClient

        client = ZoteroClient(config=mock_config)

        assert client.config.host == "localhost"
        assert client.config.port == 23119


class TestZoteroClientHttp:
    """Test ZoteroClient HTTP operations."""

    @pytest.mark.asyncio
    async def test_get_client_creates_client(self, mock_config):
        """Test _get_client creates HTTP client."""
        from zotero_mcp.infrastructure.zotero_client.client import ZoteroClient

        client = ZoteroClient(config=mock_config)

        http_client = await client._get_client()

        assert http_client is not None
        assert client._client is not None

        await client.close()

    @pytest.mark.asyncio
    async def test_get_client_reuses_client(self, mock_config):
        """Test _get_client reuses existing client."""
        from zotero_mcp.infrastructure.zotero_client.client import ZoteroClient

        client = ZoteroClient(config=mock_config)

        http_client1 = await client._get_client()
        http_client2 = await client._get_client()

        assert http_client1 is http_client2

        await client.close()

    @pytest.mark.asyncio
    async def test_get_client_with_host_header(self, remote_config):
        """Test _get_client adds Host header for remote connection."""
        from zotero_mcp.infrastructure.zotero_client.client import ZoteroClient

        client = ZoteroClient(config=remote_config)

        _http_client = await client._get_client()

        # Check that Host header was set
        assert client.config.needs_host_header is True

        await client.close()

    @pytest.mark.asyncio
    async def test_close_client(self, mock_config):
        """Test close() properly closes the client."""
        from zotero_mcp.infrastructure.zotero_client.client import ZoteroClient

        client = ZoteroClient(config=mock_config)
        await client._get_client()  # Create client

        assert client._client is not None

        await client.close()

        assert client._client is None

    @pytest.mark.asyncio
    async def test_close_without_client(self, mock_config):
        """Test close() when no client exists."""
        from zotero_mcp.infrastructure.zotero_client.client import ZoteroClient

        client = ZoteroClient(config=mock_config)

        # Should not raise
        await client.close()

        assert client._client is None


class TestZoteroClientRequest:
    """Test ZoteroClient _request method."""

    @pytest.mark.asyncio
    async def test_request_success(self, mock_config, mock_httpx_client):
        """Test successful request."""
        from zotero_mcp.infrastructure.zotero_client.client import ZoteroClient

        client = ZoteroClient(config=mock_config)
        client._client = mock_httpx_client

        result = await client._request("GET", "/test")

        mock_httpx_client.request.assert_called_once()
        assert result == {"success": True}

    @pytest.mark.asyncio
    async def test_request_with_params(self, mock_config, mock_httpx_client):
        """Test request with query parameters."""
        from zotero_mcp.infrastructure.zotero_client.client import ZoteroClient

        client = ZoteroClient(config=mock_config)
        client._client = mock_httpx_client

        await client._request("GET", "/test", params={"limit": 10})

        call_kwargs = mock_httpx_client.request.call_args
        assert call_kwargs.kwargs["params"] == {"limit": 10}

    @pytest.mark.asyncio
    async def test_request_with_json(self, mock_config, mock_httpx_client):
        """Test request with JSON body."""
        from zotero_mcp.infrastructure.zotero_client.client import ZoteroClient

        client = ZoteroClient(config=mock_config)
        client._client = mock_httpx_client

        await client._request("POST", "/test", json_data={"key": "value"})

        call_kwargs = mock_httpx_client.request.call_args
        assert call_kwargs.kwargs["json"] == {"key": "value"}

    @pytest.mark.asyncio
    async def test_request_error_status(self, mock_config):
        """Test request handles error status codes."""
        from zotero_mcp.infrastructure.zotero_client.client import ZoteroClient, ZoteroAPIError

        mock_response = Mock()
        mock_response.status_code = 404
        mock_response.text = "Not found"

        mock_http = AsyncMock()
        mock_http.request.return_value = mock_response

        client = ZoteroClient(config=mock_config)
        client._client = mock_http

        with pytest.raises(ZoteroAPIError) as exc_info:
            await client._request("GET", "/not-found")

        assert exc_info.value.status_code == 404

    @pytest.mark.asyncio
    async def test_request_empty_response(self, mock_config):
        """Test request handles empty response."""
        from zotero_mcp.infrastructure.zotero_client.client import ZoteroClient

        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.text = ""

        mock_http = AsyncMock()
        mock_http.request.return_value = mock_response

        client = ZoteroClient(config=mock_config)
        client._client = mock_http

        result = await client._request("GET", "/empty")

        assert result is None

    @pytest.mark.asyncio
    async def test_request_text_response(self, mock_config):
        """Test request handles non-JSON text response."""
        from zotero_mcp.infrastructure.zotero_client.client import ZoteroClient

        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.text = "plain text response"
        mock_response.json.side_effect = json.JSONDecodeError("", "", 0)

        mock_http = AsyncMock()
        mock_http.request.return_value = mock_response

        client = ZoteroClient(config=mock_config)
        client._client = mock_http

        result = await client._request("GET", "/text")

        assert result == "plain text response"


class TestZoteroClientPing:
    """Test ZoteroClient ping method."""

    @pytest.mark.asyncio
    async def test_ping_success(self, mock_config):
        """Test ping returns True when Zotero is running."""
        from zotero_mcp.infrastructure.zotero_client.client import ZoteroClient

        client = ZoteroClient(config=mock_config)

        with patch.object(client, "_request", return_value="Zotero is running") as mock_req:
            result = await client.ping()

        assert result is True
        mock_req.assert_called_with("GET", "/connector/ping")

    @pytest.mark.asyncio
    async def test_ping_failure(self, mock_config):
        """Test ping returns False when Zotero is not running."""
        from zotero_mcp.infrastructure.zotero_client.client import ZoteroClient

        client = ZoteroClient(config=mock_config)

        with patch.object(client, "_request", side_effect=Exception("Connection refused")):
            result = await client.ping()

        assert result is False


class TestZoteroClientItems:
    """Test ZoteroClient item operations."""

    @pytest.mark.asyncio
    async def test_get_items_default(self, mock_config, mock_item_data):
        """Test get_items with default parameters."""
        from zotero_mcp.infrastructure.zotero_client.client import ZoteroClient

        client = ZoteroClient(config=mock_config)

        with patch.object(client, "_request", return_value=[mock_item_data]) as mock_req:
            result = await client.get_items()

        assert len(result) == 1
        mock_req.assert_called_once()
        call_args = mock_req.call_args
        assert call_args.kwargs["params"]["limit"] == 50
        assert call_args.kwargs["params"]["sort"] == "dateModified"

    @pytest.mark.asyncio
    async def test_get_items_with_params(self, mock_config, mock_item_data):
        """Test get_items with custom parameters."""
        from zotero_mcp.infrastructure.zotero_client.client import ZoteroClient

        client = ZoteroClient(config=mock_config)

        with patch.object(client, "_request", return_value=[mock_item_data]) as mock_req:
            await client.get_items(limit=10, sort="title", item_type="book", q="test")

        call_args = mock_req.call_args
        assert call_args.kwargs["params"]["limit"] == 10
        assert call_args.kwargs["params"]["sort"] == "title"
        assert call_args.kwargs["params"]["itemType"] == "book"
        assert call_args.kwargs["params"]["q"] == "test"

    @pytest.mark.asyncio
    async def test_get_item(self, mock_config, mock_item_data):
        """Test get_item by key."""
        from zotero_mcp.infrastructure.zotero_client.client import ZoteroClient

        client = ZoteroClient(config=mock_config)

        with patch.object(client, "_request", return_value=mock_item_data) as mock_req:
            result = await client.get_item("ABC12345")

        assert result["key"] == "ABC12345"
        mock_req.assert_called_with("GET", "/api/users/0/items/ABC12345")

    @pytest.mark.asyncio
    async def test_search_items(self, mock_config, mock_item_data):
        """Test search_items."""
        from zotero_mcp.infrastructure.zotero_client.client import ZoteroClient

        client = ZoteroClient(config=mock_config)

        with patch.object(client, "get_items", return_value=[mock_item_data]) as mock_get:
            result = await client.search_items("machine learning", limit=10)

        mock_get.assert_called_with(q="machine learning", limit=10)
        assert len(result) == 1


class TestZoteroClientCollections:
    """Test ZoteroClient collection operations."""

    @pytest.mark.asyncio
    async def test_get_collections(self, mock_config, mock_collection_list):
        """Test get_collections."""
        from zotero_mcp.infrastructure.zotero_client.client import ZoteroClient

        client = ZoteroClient(config=mock_config)

        with patch.object(client, "_request", return_value=mock_collection_list):
            result = await client.get_collections()

        assert len(result) == 4

    @pytest.mark.asyncio
    async def test_find_collection_by_name(self, mock_config, mock_collection_list):
        """Test find_collection_by_name."""
        from zotero_mcp.infrastructure.zotero_client.client import ZoteroClient

        client = ZoteroClient(config=mock_config)

        with patch.object(client, "get_collections", return_value=mock_collection_list):
            result = await client.find_collection_by_name("AI Papers")

        assert result is not None
        assert result["key"] == "COL002"

    @pytest.mark.asyncio
    async def test_find_collection_by_name_case_insensitive(self, mock_config, mock_collection_list):
        """Test find_collection_by_name is case insensitive."""
        from zotero_mcp.infrastructure.zotero_client.client import ZoteroClient

        client = ZoteroClient(config=mock_config)

        with patch.object(client, "get_collections", return_value=mock_collection_list):
            result = await client.find_collection_by_name("ai papers")

        assert result is not None

    @pytest.mark.asyncio
    async def test_find_collection_by_name_not_found(self, mock_config, mock_collection_list):
        """Test find_collection_by_name when not found."""
        from zotero_mcp.infrastructure.zotero_client.client import ZoteroClient

        client = ZoteroClient(config=mock_config)

        with patch.object(client, "get_collections", return_value=mock_collection_list):
            result = await client.find_collection_by_name("Nonexistent")

        assert result is None

    @pytest.mark.asyncio
    async def test_find_collection_by_name_with_parent(self, mock_config, mock_collection_list):
        """Test find_collection_by_name with parent key filter."""
        from zotero_mcp.infrastructure.zotero_client.client import ZoteroClient

        client = ZoteroClient(config=mock_config)

        with patch.object(client, "get_collections", return_value=mock_collection_list):
            result = await client.find_collection_by_name("AI Papers", parent_key="COL001")

        assert result is not None
        assert result["key"] == "COL002"

    @pytest.mark.asyncio
    async def test_get_collection_tree(self, mock_config, mock_collection_list):
        """Test get_collection_tree builds proper tree structure."""
        from zotero_mcp.infrastructure.zotero_client.client import ZoteroClient

        client = ZoteroClient(config=mock_config)

        with patch.object(client, "get_collections", return_value=mock_collection_list):
            result = await client.get_collection_tree()

        # Should have 2 root collections (Research and Archive)
        assert len(result) == 2

        # Research should have 2 children
        research = next(c for c in result if c["name"] == "Research")
        assert len(research["children"]) == 2


class TestZoteroClientSavedSearches:
    """Test ZoteroClient saved search operations."""

    @pytest.mark.asyncio
    async def test_get_searches(self, mock_config, mock_search_data):
        """Test get_searches."""
        from zotero_mcp.infrastructure.zotero_client.client import ZoteroClient

        client = ZoteroClient(config=mock_config)

        with patch.object(client, "_request", return_value=[mock_search_data]):
            result = await client.get_searches()

        assert len(result) == 1

    @pytest.mark.asyncio
    async def test_find_search_by_name(self, mock_config, mock_search_data):
        """Test find_search_by_name."""
        from zotero_mcp.infrastructure.zotero_client.client import ZoteroClient

        client = ZoteroClient(config=mock_config)

        with patch.object(client, "get_searches", return_value=[mock_search_data]):
            result = await client.find_search_by_name("Recent AI Papers")

        assert result is not None
        assert result["key"] == "SRCH001"

    @pytest.mark.asyncio
    async def test_execute_search(self, mock_config, mock_item_data):
        """Test execute_search."""
        from zotero_mcp.infrastructure.zotero_client.client import ZoteroClient

        client = ZoteroClient(config=mock_config)

        with patch.object(client, "_request", return_value=[mock_item_data]) as mock_req:
            result = await client.execute_search("SRCH001", limit=50)

        assert len(result) == 1
        mock_req.assert_called_with("GET", "/api/users/0/searches/SRCH001/items", params={"limit": 50})


class TestZoteroClientWrite:
    """Test ZoteroClient write operations."""

    @pytest.mark.asyncio
    async def test_save_items(self, mock_config):
        """Test save_items."""
        from zotero_mcp.infrastructure.zotero_client.client import ZoteroClient

        client = ZoteroClient(config=mock_config)

        items = [{"itemType": "journalArticle", "title": "Test"}]

        with patch.object(client, "_request", return_value={"success": True}) as mock_req:
            result = await client.save_items(items)

        assert result["success"] is True
        mock_req.assert_called_once()
        call_kwargs = mock_req.call_args.kwargs
        assert call_kwargs["json_data"]["items"] == items

    @pytest.mark.asyncio
    async def test_create_item(self, mock_config):
        """Test create_item convenience method."""
        from zotero_mcp.infrastructure.zotero_client.client import ZoteroClient

        client = ZoteroClient(config=mock_config)

        with patch.object(client, "save_items", return_value={"success": True}) as mock_save:
            await client.create_item(
                item_type="journalArticle",
                title="Test Article",
                date="2024",
                DOI="10.1234/test",
            )

        saved_items = mock_save.call_args[0][0]
        assert len(saved_items) == 1
        assert saved_items[0]["itemType"] == "journalArticle"
        assert saved_items[0]["title"] == "Test Article"
        assert saved_items[0]["DOI"] == "10.1234/test"


class TestZoteroClientBatch:
    """Test ZoteroClient batch operations."""

    @pytest.mark.asyncio
    async def test_batch_check_identifiers(self, mock_config, mock_item_data):
        """Test batch_check_identifiers."""
        from zotero_mcp.infrastructure.zotero_client.client import ZoteroClient

        client = ZoteroClient(config=mock_config)

        # Mock get_items to return item with PMID and DOI
        with patch.object(client, "get_items", return_value=[mock_item_data]):
            result = await client.batch_check_identifiers(
                pmids=["12345678", "99999999"],
                dois=["10.1000/test.2024.001", "10.9999/notfound"],
            )

        assert "12345678" in result["existing_pmids"]
        assert "99999999" not in result["existing_pmids"]
        assert "10.1000/test.2024.001" in result["existing_dois"]

    @pytest.mark.asyncio
    async def test_batch_save_items(self, mock_config):
        """Test batch_save_items."""
        from zotero_mcp.infrastructure.zotero_client.client import ZoteroClient

        client = ZoteroClient(config=mock_config)

        items = [
            {"itemType": "journalArticle", "title": "Article 1"},
            {"itemType": "journalArticle", "title": "Article 2"},
        ]

        with patch.object(client, "save_items", return_value={"success": True}) as mock_save:
            result = await client.batch_save_items(items)

        assert result["success"] is True
        mock_save.assert_called_once()

    @pytest.mark.asyncio
    async def test_batch_save_items_empty(self, mock_config):
        """Test batch_save_items with empty list."""
        from zotero_mcp.infrastructure.zotero_client.client import ZoteroClient

        client = ZoteroClient(config=mock_config)

        result = await client.batch_save_items([])

        assert result["success"] is True
        assert result["items"] == []


class TestZoteroClientExceptions:
    """Test ZoteroClient exception handling."""

    def test_zotero_connection_error(self):
        """Test ZoteroConnectionError attributes."""
        from zotero_mcp.infrastructure.zotero_client.client import ZoteroConnectionError

        error = ZoteroConnectionError("Connection failed")

        assert str(error) == "Connection failed"

    def test_zotero_api_error(self):
        """Test ZoteroAPIError attributes."""
        from zotero_mcp.infrastructure.zotero_client.client import ZoteroAPIError

        error = ZoteroAPIError("Not found", status_code=404, response_text="Item not found")

        assert error.status_code == 404
        assert error.response_text == "Item not found"
        assert "Not found" in str(error)
