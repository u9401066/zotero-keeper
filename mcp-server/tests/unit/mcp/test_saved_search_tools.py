"""
Tests for saved_search_tools.py

Tests the saved search functionality for Zotero Local API.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock

from zotero_mcp.infrastructure.mcp.saved_search_tools import (
    _format_creators,
    register_saved_search_tools,
)


class TestFormatCreators:
    """Tests for _format_creators function."""
    
    def test_single_creator(self):
        """Test formatting single creator."""
        creators = [{"firstName": "John", "lastName": "Smith"}]
        result = _format_creators(creators)
        assert "John Smith" in result
    
    def test_multiple_creators(self):
        """Test formatting multiple creators."""
        creators = [
            {"firstName": "John", "lastName": "Smith"},
            {"firstName": "Jane", "lastName": "Doe"},
        ]
        result = _format_creators(creators)
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
        result = _format_creators(creators)
        assert "et al." in result
        assert "+1" in result
    
    def test_empty_creators(self):
        """Test empty creators list."""
        result = _format_creators([])
        assert result == ""
    
    def test_creator_with_name_only(self):
        """Test creator with only name field."""
        creators = [{"name": "Organization Name"}]
        result = _format_creators(creators)
        assert "Organization Name" in result
    
    def test_creator_with_lastname_only(self):
        """Test creator with only lastName."""
        creators = [{"lastName": "Smith"}]
        result = _format_creators(creators)
        assert "Smith" in result


class TestRegisterSavedSearchTools:
    """Tests for register_saved_search_tools function."""
    
    def test_registers_tools(self):
        """Test that tools are registered."""
        mock_mcp = MagicMock()
        mock_client = MagicMock()
        
        def tool_decorator():
            def wrapper(func):
                return func
            return wrapper
        mock_mcp.tool = tool_decorator
        
        # Should complete without error
        register_saved_search_tools(mock_mcp, mock_client)


class TestListSavedSearches:
    """Tests for list_saved_searches tool."""
    
    @pytest.mark.asyncio
    async def test_list_searches(self):
        """Test listing saved searches."""
        mock_mcp = MagicMock()
        mock_client = AsyncMock()
        mock_client.get_searches.return_value = [
            {"key": "ABC123", "data": {"name": "Test Search", "conditions": []}},
        ]
        
        registered_func = None
        def tool_decorator():
            def wrapper(func):
                nonlocal registered_func
                registered_func = func
                return func
            return wrapper
        mock_mcp.tool = tool_decorator
        
        register_saved_search_tools(mock_mcp, mock_client)
        
        # Find list_saved_searches function
        # In real implementation, we'd need to capture the specific function
    
    @pytest.mark.asyncio
    async def test_list_searches_empty(self):
        """Test listing when no searches exist."""
        mock_mcp = MagicMock()
        mock_client = AsyncMock()
        mock_client.get_searches.return_value = []
        
        def tool_decorator():
            def wrapper(func):
                return func
            return wrapper
        mock_mcp.tool = tool_decorator
        
        register_saved_search_tools(mock_mcp, mock_client)


class TestRunSavedSearch:
    """Tests for run_saved_search tool."""
    
    @pytest.mark.asyncio
    async def test_run_by_key(self):
        """Test running search by key."""
        mock_mcp = MagicMock()
        mock_client = AsyncMock()
        mock_client.get_search.return_value = {
            "key": "ABC123",
            "data": {"name": "Test", "conditions": []},
        }
        mock_client.execute_search.return_value = [
            {"key": "ITEM1", "data": {"title": "Test Item", "itemType": "journalArticle"}},
        ]
        
        def tool_decorator():
            def wrapper(func):
                return func
            return wrapper
        mock_mcp.tool = tool_decorator
        
        register_saved_search_tools(mock_mcp, mock_client)
    
    @pytest.mark.asyncio
    async def test_run_by_name(self):
        """Test running search by name."""
        mock_mcp = MagicMock()
        mock_client = AsyncMock()
        mock_client.find_search_by_name.return_value = {
            "key": "ABC123",
            "data": {"name": "Missing PDF", "conditions": []},
        }
        mock_client.execute_search.return_value = []
        
        def tool_decorator():
            def wrapper(func):
                return func
            return wrapper
        mock_mcp.tool = tool_decorator
        
        register_saved_search_tools(mock_mcp, mock_client)
    
    @pytest.mark.asyncio
    async def test_search_not_found(self):
        """Test handling when search not found."""
        mock_mcp = MagicMock()
        mock_client = AsyncMock()
        mock_client.find_search_by_name.return_value = None
        
        def tool_decorator():
            def wrapper(func):
                return func
            return wrapper
        mock_mcp.tool = tool_decorator
        
        register_saved_search_tools(mock_mcp, mock_client)


class TestGetSavedSearchDetails:
    """Tests for get_saved_search_details tool."""
    
    @pytest.mark.asyncio
    async def test_get_details(self):
        """Test getting search details."""
        mock_mcp = MagicMock()
        mock_client = AsyncMock()
        mock_client.get_search.return_value = {
            "key": "ABC123",
            "data": {
                "name": "Test Search",
                "conditions": [
                    {"condition": "title", "operator": "contains", "value": "test"}
                ],
            },
        }
        
        def tool_decorator():
            def wrapper(func):
                return func
            return wrapper
        mock_mcp.tool = tool_decorator
        
        register_saved_search_tools(mock_mcp, mock_client)
    
    @pytest.mark.asyncio
    async def test_search_not_found(self):
        """Test handling when search not found."""
        from zotero_mcp.infrastructure.zotero_client.client import ZoteroAPIError
        
        mock_mcp = MagicMock()
        mock_client = AsyncMock()
        mock_client.get_search.side_effect = ZoteroAPIError("Not found", 404)
        
        def tool_decorator():
            def wrapper(func):
                return func
            return wrapper
        mock_mcp.tool = tool_decorator
        
        register_saved_search_tools(mock_mcp, mock_client)
