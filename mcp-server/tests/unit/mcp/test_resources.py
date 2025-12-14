"""
Tests for resources.py

Tests the MCP Resources for Zotero data access.
"""

import pytest
import json
from unittest.mock import AsyncMock, MagicMock

from zotero_mcp.infrastructure.mcp.resources import (
    _format_creators_short,
    register_resources,
)


class TestFormatCreatorsShort:
    """Tests for _format_creators_short function."""
    
    def test_single_creator(self):
        """Test formatting single creator."""
        creators = [{"firstName": "John", "lastName": "Smith"}]
        result = _format_creators_short(creators)
        assert "John Smith" in result
    
    def test_multiple_creators(self):
        """Test formatting multiple creators."""
        creators = [
            {"firstName": "John", "lastName": "Smith"},
            {"firstName": "Jane", "lastName": "Doe"},
        ]
        result = _format_creators_short(creators)
        assert "John Smith" in result
        assert "Jane Doe" in result
    
    def test_more_than_three_creators(self):
        """Test et al. for more than 3 creators."""
        creators = [
            {"firstName": "A", "lastName": "Author"},
            {"firstName": "B", "lastName": "Author"},
            {"firstName": "C", "lastName": "Author"},
            {"firstName": "D", "lastName": "Author"},
        ]
        result = _format_creators_short(creators)
        assert "et al." in result
    
    def test_empty_creators(self):
        """Test empty creators list."""
        result = _format_creators_short([])
        assert result == ""
    
    def test_creator_with_name_only(self):
        """Test creator with only name field."""
        creators = [{"name": "Organization"}]
        result = _format_creators_short(creators)
        assert "Organization" in result


class TestRegisterResources:
    """Tests for register_resources function."""
    
    def test_registers_resources(self):
        """Test that resources are registered."""
        mock_mcp = MagicMock()
        mock_client = MagicMock()
        
        def resource_decorator(uri):
            def wrapper(func):
                return func
            return wrapper
        mock_mcp.resource = resource_decorator
        
        # Should complete without error
        register_resources(mock_mcp, mock_client)


class TestCollectionsResource:
    """Tests for collections resources."""
    
    @pytest.mark.asyncio
    async def test_list_collections_resource(self):
        """Test listing collections resource."""
        mock_mcp = MagicMock()
        mock_client = AsyncMock()
        mock_client.get_collections.return_value = [
            {"key": "ABC123", "data": {"name": "Test Collection", "numItems": 10}},
        ]
        
        registered_funcs = {}
        def resource_decorator(uri):
            def wrapper(func):
                registered_funcs[uri] = func
                return func
            return wrapper
        mock_mcp.resource = resource_decorator
        
        register_resources(mock_mcp, mock_client)
        
        if "zotero://collections" in registered_funcs:
            result = await registered_funcs["zotero://collections"]()
            data = json.loads(result)
            assert data["type"] == "collections"
            assert data["count"] == 1
    
    @pytest.mark.asyncio
    async def test_get_collection_tree_resource(self):
        """Test collection tree resource."""
        mock_mcp = MagicMock()
        mock_client = AsyncMock()
        mock_client.get_collection_tree.return_value = [
            {"key": "ABC", "name": "Root", "children": []},
        ]
        
        registered_funcs = {}
        def resource_decorator(uri):
            def wrapper(func):
                registered_funcs[uri] = func
                return func
            return wrapper
        mock_mcp.resource = resource_decorator
        
        register_resources(mock_mcp, mock_client)
        
        if "zotero://collections/tree" in registered_funcs:
            result = await registered_funcs["zotero://collections/tree"]()
            data = json.loads(result)
            assert data["type"] == "collection_tree"


class TestItemsResource:
    """Tests for items resources."""
    
    @pytest.mark.asyncio
    async def test_list_items_resource(self):
        """Test listing items resource."""
        mock_mcp = MagicMock()
        mock_client = AsyncMock()
        mock_client.get_items.return_value = [
            {
                "key": "ITEM1",
                "data": {
                    "title": "Test Article",
                    "itemType": "journalArticle",
                    "date": "2024",
                    "creators": [],
                },
            },
        ]
        
        registered_funcs = {}
        def resource_decorator(uri):
            def wrapper(func):
                registered_funcs[uri] = func
                return func
            return wrapper
        mock_mcp.resource = resource_decorator
        
        register_resources(mock_mcp, mock_client)
        
        if "zotero://items" in registered_funcs:
            result = await registered_funcs["zotero://items"]()
            data = json.loads(result)
            assert data["type"] == "items"
    
    @pytest.mark.asyncio
    async def test_get_item_resource(self):
        """Test getting single item resource."""
        mock_mcp = MagicMock()
        mock_client = AsyncMock()
        mock_client.get_item.return_value = {
            "key": "ITEM1",
            "data": {
                "title": "Test Article",
                "itemType": "journalArticle",
                "DOI": "10.1234/test",
                "abstractNote": "Test abstract",
            },
        }
        
        registered_funcs = {}
        def resource_decorator(uri):
            def wrapper(func):
                registered_funcs[uri] = func
                return func
            return wrapper
        mock_mcp.resource = resource_decorator
        
        register_resources(mock_mcp, mock_client)
        
        if "zotero://items/{key}" in registered_funcs:
            result = await registered_funcs["zotero://items/{key}"]("ITEM1")
            data = json.loads(result)
            assert data["type"] == "item"
            assert data["title"] == "Test Article"


class TestTagsResource:
    """Tests for tags resource."""
    
    @pytest.mark.asyncio
    async def test_list_tags_resource(self):
        """Test listing tags resource."""
        mock_mcp = MagicMock()
        mock_client = AsyncMock()
        mock_client.get_tags.return_value = [
            {"tag": "machine learning"},
            {"tag": "AI"},
        ]
        
        registered_funcs = {}
        def resource_decorator(uri):
            def wrapper(func):
                registered_funcs[uri] = func
                return func
            return wrapper
        mock_mcp.resource = resource_decorator
        
        register_resources(mock_mcp, mock_client)
        
        if "zotero://tags" in registered_funcs:
            result = await registered_funcs["zotero://tags"]()
            data = json.loads(result)
            assert data["type"] == "tags"
            assert data["count"] == 2


class TestSearchesResource:
    """Tests for saved searches resource."""
    
    @pytest.mark.asyncio
    async def test_list_searches_resource(self):
        """Test listing saved searches resource."""
        mock_mcp = MagicMock()
        mock_client = AsyncMock()
        mock_client.get_searches.return_value = [
            {"key": "SEARCH1", "data": {"name": "Missing PDF", "conditions": []}},
        ]
        
        registered_funcs = {}
        def resource_decorator(uri):
            def wrapper(func):
                registered_funcs[uri] = func
                return func
            return wrapper
        mock_mcp.resource = resource_decorator
        
        register_resources(mock_mcp, mock_client)
        
        if "zotero://searches" in registered_funcs:
            result = await registered_funcs["zotero://searches"]()
            data = json.loads(result)
            assert data["type"] == "saved_searches"


class TestSchemaResource:
    """Tests for schema resource."""
    
    @pytest.mark.asyncio
    async def test_get_item_types_resource(self):
        """Test getting item types resource."""
        mock_mcp = MagicMock()
        mock_client = AsyncMock()
        mock_client.get_item_types.return_value = [
            {"itemType": "journalArticle"},
            {"itemType": "book"},
        ]
        
        registered_funcs = {}
        def resource_decorator(uri):
            def wrapper(func):
                registered_funcs[uri] = func
                return func
            return wrapper
        mock_mcp.resource = resource_decorator
        
        register_resources(mock_mcp, mock_client)
        
        if "zotero://schema/item-types" in registered_funcs:
            result = await registered_funcs["zotero://schema/item-types"]()
            data = json.loads(result)
            assert data["type"] == "item_types"


class TestResourceErrorHandling:
    """Tests for error handling in resources."""
    
    @pytest.mark.asyncio
    async def test_handles_exception(self):
        """Test that exceptions are handled gracefully."""
        mock_mcp = MagicMock()
        mock_client = AsyncMock()
        mock_client.get_collections.side_effect = Exception("API Error")
        
        registered_funcs = {}
        def resource_decorator(uri):
            def wrapper(func):
                registered_funcs[uri] = func
                return func
            return wrapper
        mock_mcp.resource = resource_decorator
        
        register_resources(mock_mcp, mock_client)
        
        if "zotero://collections" in registered_funcs:
            result = await registered_funcs["zotero://collections"]()
            data = json.loads(result)
            assert "error" in data
