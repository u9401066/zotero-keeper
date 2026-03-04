"""
Tests for DAL-level Collection Guard

Verifies that save_items validates collection keys before writing to Zotero,
preventing items from being silently misplaced by invalid collection references.
"""

import pytest
from unittest.mock import AsyncMock, patch

from zotero_mcp.infrastructure.zotero_client.client_write import (
    InvalidCollectionError,
    ZoteroWriteMixin,
)


class MockClient(ZoteroWriteMixin):
    """Mock client for testing write mixin"""

    def __init__(self, collections: list[dict] | None = None):
        self._collections = collections or []
        self._request = AsyncMock(return_value={"success": True})

    async def get_collections(self) -> list[dict]:
        return self._collections


@pytest.fixture
def mock_collections():
    """Sample valid collections"""
    return [
        {"key": "ABC123", "data": {"name": "Machine Learning"}},
        {"key": "DEF456", "data": {"name": "Anesthesia"}},
        {"key": "GHI789", "data": {"name": "Clinical Trials"}},
    ]


class TestCollectionGuard:
    """Tests for _validate_collection_keys"""

    @pytest.mark.asyncio
    async def test_no_collections_passes(self, mock_collections):
        """Items without collections should pass validation"""
        client = MockClient(mock_collections)
        items = [{"itemType": "journalArticle", "title": "Test"}]
        # Should not raise
        await client._validate_collection_keys(items)

    @pytest.mark.asyncio
    async def test_valid_collection_key_passes(self, mock_collections):
        """Items with valid collection keys should pass"""
        client = MockClient(mock_collections)
        items = [
            {"itemType": "journalArticle", "title": "Test", "collections": ["ABC123"]}
        ]
        await client._validate_collection_keys(items)

    @pytest.mark.asyncio
    async def test_invalid_collection_key_raises(self, mock_collections):
        """Items with invalid collection keys should raise InvalidCollectionError"""
        client = MockClient(mock_collections)
        items = [
            {"itemType": "journalArticle", "title": "Test", "collections": ["INVALID"]}
        ]
        with pytest.raises(InvalidCollectionError, match="INVALID"):
            await client._validate_collection_keys(items)

    @pytest.mark.asyncio
    async def test_mixed_valid_invalid_raises(self, mock_collections):
        """Mix of valid and invalid keys should still raise"""
        client = MockClient(mock_collections)
        items = [
            {"itemType": "journalArticle", "title": "Valid", "collections": ["ABC123"]},
            {"itemType": "journalArticle", "title": "Invalid", "collections": ["BOGUS"]},
        ]
        with pytest.raises(InvalidCollectionError, match="BOGUS"):
            await client._validate_collection_keys(items)

    @pytest.mark.asyncio
    async def test_multiple_collections_on_item(self, mock_collections):
        """Item with multiple valid collections should pass"""
        client = MockClient(mock_collections)
        items = [
            {"itemType": "journalArticle", "title": "Test", "collections": ["ABC123", "DEF456"]}
        ]
        await client._validate_collection_keys(items)

    @pytest.mark.asyncio
    async def test_empty_collections_list_passes(self, mock_collections):
        """Items with empty collections list should pass"""
        client = MockClient(mock_collections)
        items = [
            {"itemType": "journalArticle", "title": "Test", "collections": []}
        ]
        await client._validate_collection_keys(items)

    @pytest.mark.asyncio
    async def test_error_message_includes_available(self, mock_collections):
        """Error message should include available collections"""
        client = MockClient(mock_collections)
        items = [
            {"itemType": "journalArticle", "title": "Test", "collections": ["WRONG"]}
        ]
        with pytest.raises(InvalidCollectionError, match="Available collections"):
            await client._validate_collection_keys(items)

    @pytest.mark.asyncio
    async def test_zotero_unreachable_fails_open(self):
        """If Zotero is unreachable during validation, fail-open with warning"""
        client = MockClient()
        # Simulate Zotero being unreachable
        client.get_collections = AsyncMock(side_effect=ConnectionError("unreachable"))
        items = [
            {"itemType": "journalArticle", "title": "Test", "collections": ["ABC123"]}
        ]
        # Should NOT raise — fail-open
        await client._validate_collection_keys(items)


class TestSaveItemsIntegration:
    """Tests that save_items calls the collection guard"""

    @pytest.mark.asyncio
    async def test_save_items_validates_collections(self, mock_collections):
        """save_items should validate collection keys before saving"""
        client = MockClient(mock_collections)
        items = [
            {"itemType": "journalArticle", "title": "Test", "collections": ["INVALID"]}
        ]
        with pytest.raises(InvalidCollectionError):
            await client.save_items(items)

    @pytest.mark.asyncio
    async def test_save_items_passes_valid_collections(self, mock_collections):
        """save_items should proceed when collections are valid"""
        client = MockClient(mock_collections)
        items = [
            {"itemType": "journalArticle", "title": "Test", "collections": ["ABC123"]}
        ]
        result = await client.save_items(items)
        assert result == {"success": True}
        # Verify _request was actually called (item was saved)
        client._request.assert_called_once()

    @pytest.mark.asyncio
    async def test_save_items_no_collections(self, mock_collections):
        """save_items should work fine when no collections specified"""
        client = MockClient(mock_collections)
        items = [{"itemType": "journalArticle", "title": "Test"}]
        result = await client.save_items(items)
        assert result == {"success": True}
        client._request.assert_called_once()

    @pytest.mark.asyncio
    async def test_batch_save_items_validates(self, mock_collections):
        """batch_save_items also goes through save_items guard"""
        client = MockClient(mock_collections)
        items = [
            {"itemType": "journalArticle", "title": "Test", "collections": ["INVALID"]}
        ]
        with pytest.raises(InvalidCollectionError):
            await client.batch_save_items(items)
