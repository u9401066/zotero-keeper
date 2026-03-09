"""Tests for shared collection support helpers."""

from unittest.mock import AsyncMock

import pytest

from zotero_mcp.infrastructure.mcp.collection_support import (
    apply_collection_and_tags,
    resolve_collection_target,
)


class TestResolveCollectionTarget:
    """Tests for collection resolution helper."""

    @pytest.mark.asyncio
    async def test_returns_empty_resolution_when_no_collection_provided(self):
        mock_client = AsyncMock()

        result = await resolve_collection_target(mock_client)

        assert result["success"] is True
        assert result["target_key"] is None
        assert result["collection_info"] is None

    @pytest.mark.asyncio
    async def test_resolves_collection_key(self):
        mock_client = AsyncMock()
        mock_client.get_collection.return_value = {"data": {"name": "AI Research"}}

        result = await resolve_collection_target(mock_client, collection_key="ABC123")

        assert result["success"] is True
        assert result["target_key"] == "ABC123"
        assert result["target_name"] == "AI Research"
        assert result["collection_info"]["resolved_from"] == "key"

    @pytest.mark.asyncio
    async def test_returns_available_collections_when_key_not_found(self):
        mock_client = AsyncMock()
        mock_client.get_collection.side_effect = Exception("not found")
        mock_client.get_collections.return_value = [{"key": "DEF456", "data": {"name": "ML"}}]

        result = await resolve_collection_target(mock_client, collection_key="BADKEY")

        assert result["success"] is False
        assert "available_collections" in result
        assert result["available_collections"][0]["name"] == "ML"

    @pytest.mark.asyncio
    async def test_can_fallback_to_unvalidated_key(self):
        mock_client = AsyncMock()
        mock_client.get_collection.side_effect = Exception("network issue")

        result = await resolve_collection_target(
            mock_client,
            collection_key="ABC123",
            fallback_to_unvalidated_key=True,
        )

        assert result["success"] is True
        assert result["target_key"] == "ABC123"
        assert result["collection_info"]["warning"] == "network issue"

    @pytest.mark.asyncio
    async def test_resolves_collection_name(self):
        mock_client = AsyncMock()
        mock_client.find_collection_by_name.return_value = {"key": "ABC123", "data": {"name": "AI Research"}}

        result = await resolve_collection_target(mock_client, collection_name="AI Research")

        assert result["success"] is True
        assert result["target_key"] == "ABC123"
        assert result["collection_info"]["resolved_from"] == "name"

    @pytest.mark.asyncio
    async def test_returns_similar_names_when_requested(self):
        mock_client = AsyncMock()
        mock_client.find_collection_by_name.return_value = None
        mock_client.get_collections.return_value = [
            {"key": "A1", "data": {"name": "AI Research"}},
            {"key": "A2", "data": {"name": "AI Reviews"}},
        ]

        result = await resolve_collection_target(
            mock_client,
            collection_name="AI",
            include_similar=True,
        )

        assert result["success"] is False
        assert "Similar collections" in result["hint"]


class TestApplyCollectionAndTags:
    """Tests for item mutation helper."""

    def test_applies_collection_and_tags(self):
        item = {"title": "Test", "tags": [{"tag": "existing"}]}

        result = apply_collection_and_tags(item, collection_key="ABC123", tags=["new"])

        assert result["collections"] == ["ABC123"]
        assert {"tag": "existing"} in result["tags"]
        assert {"tag": "new"} in result["tags"]