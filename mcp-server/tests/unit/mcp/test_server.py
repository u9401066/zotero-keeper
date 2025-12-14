"""
Tests for server.py

Tests the Zotero Keeper MCP Server initialization and tools.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from zotero_mcp.infrastructure.mcp.server import (
    ZoteroKeeperServer,
    _format_creators,
    get_server,
    create_server,
)
from zotero_mcp.infrastructure.mcp.config import McpServerConfig, ZoteroConfig


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
    
    def test_empty_creators(self):
        """Test empty creators list."""
        result = _format_creators([])
        assert result == ""
    
    def test_creator_with_name_only(self):
        """Test creator with only name field."""
        creators = [{"name": "Organization"}]
        result = _format_creators(creators)
        assert "Organization" in result


class TestZoteroKeeperServer:
    """Tests for ZoteroKeeperServer class."""
    
    @patch("zotero_mcp.infrastructure.mcp.server.ZoteroClient")
    @patch("zotero_mcp.infrastructure.mcp.server.FastMCP")
    @patch("zotero_mcp.infrastructure.mcp.server.register_resources")
    @patch("zotero_mcp.infrastructure.mcp.server.register_smart_tools")
    @patch("zotero_mcp.infrastructure.mcp.server.register_interactive_save_tools")
    @patch("zotero_mcp.infrastructure.mcp.server.register_saved_search_tools")
    def test_server_initialization(
        self,
        mock_saved_search,
        mock_interactive,
        mock_smart,
        mock_resources,
        mock_mcp,
        mock_client,
    ):
        """Test server initializes correctly."""
        mock_mcp_instance = MagicMock()
        mock_mcp.return_value = mock_mcp_instance
        
        server = ZoteroKeeperServer()
        
        assert server.mcp == mock_mcp_instance
        mock_mcp.assert_called_once()
    
    @patch("zotero_mcp.infrastructure.mcp.server.ZoteroClient")
    @patch("zotero_mcp.infrastructure.mcp.server.FastMCP")
    @patch("zotero_mcp.infrastructure.mcp.server.register_resources")
    @patch("zotero_mcp.infrastructure.mcp.server.register_smart_tools")
    @patch("zotero_mcp.infrastructure.mcp.server.register_interactive_save_tools")
    @patch("zotero_mcp.infrastructure.mcp.server.register_saved_search_tools")
    def test_server_with_custom_config(
        self,
        mock_saved_search,
        mock_interactive,
        mock_smart,
        mock_resources,
        mock_mcp,
        mock_client,
    ):
        """Test server with custom configuration."""
        config = McpServerConfig(
            name="Custom Server",
            zotero=ZoteroConfig(host="192.168.1.100", port=23119),
        )
        
        server = ZoteroKeeperServer(config)
        
        assert server._config == config


class TestGetServer:
    """Tests for get_server function."""
    
    @patch("zotero_mcp.infrastructure.mcp.server._server", None)
    @patch("zotero_mcp.infrastructure.mcp.server.ZoteroKeeperServer")
    def test_creates_server_if_none(self, mock_server_class):
        """Test that get_server creates server if none exists."""
        mock_instance = MagicMock()
        mock_server_class.return_value = mock_instance
        
        # Import fresh to get clean _server state
        from zotero_mcp.infrastructure.mcp import server as server_module
        server_module._server = None
        
        result = server_module.get_server()
        
        mock_server_class.assert_called_once()


class TestCreateServer:
    """Tests for create_server function."""
    
    @patch("zotero_mcp.infrastructure.mcp.server.ZoteroKeeperServer")
    def test_creates_server_with_config(self, mock_server_class):
        """Test create_server with custom config."""
        config = McpServerConfig(name="Test")
        mock_instance = MagicMock()
        mock_server_class.return_value = mock_instance
        
        from zotero_mcp.infrastructure.mcp import server as server_module
        
        result = server_module.create_server(config)
        
        mock_server_class.assert_called_with(config)
        assert result == mock_instance


class TestServerTools:
    """Integration tests for server tools."""
    
    @pytest.mark.asyncio
    @patch("zotero_mcp.infrastructure.mcp.server.ZoteroClient")
    @patch("zotero_mcp.infrastructure.mcp.server.FastMCP")
    @patch("zotero_mcp.infrastructure.mcp.server.register_resources")
    @patch("zotero_mcp.infrastructure.mcp.server.register_smart_tools")
    @patch("zotero_mcp.infrastructure.mcp.server.register_interactive_save_tools")
    @patch("zotero_mcp.infrastructure.mcp.server.register_saved_search_tools")
    async def test_check_connection_tool(
        self,
        mock_saved_search,
        mock_interactive,
        mock_smart,
        mock_resources,
        mock_mcp,
        mock_client_class,
    ):
        """Test check_connection tool is registered."""
        mock_mcp_instance = MagicMock()
        mock_mcp.return_value = mock_mcp_instance
        
        # Capture registered tools
        registered_tools = {}
        def tool_decorator():
            def wrapper(func):
                registered_tools[func.__name__] = func
                return func
            return wrapper
        mock_mcp_instance.tool = tool_decorator
        
        server = ZoteroKeeperServer()
        
        # Verify check_connection was registered
        assert "check_connection" in registered_tools
    
    @pytest.mark.asyncio
    @patch("zotero_mcp.infrastructure.mcp.server.ZoteroClient")
    @patch("zotero_mcp.infrastructure.mcp.server.FastMCP")
    @patch("zotero_mcp.infrastructure.mcp.server.register_resources")
    @patch("zotero_mcp.infrastructure.mcp.server.register_smart_tools")
    @patch("zotero_mcp.infrastructure.mcp.server.register_interactive_save_tools")
    @patch("zotero_mcp.infrastructure.mcp.server.register_saved_search_tools")
    async def test_search_items_tool(
        self,
        mock_saved_search,
        mock_interactive,
        mock_smart,
        mock_resources,
        mock_mcp,
        mock_client_class,
    ):
        """Test search_items tool is registered."""
        mock_mcp_instance = MagicMock()
        mock_mcp.return_value = mock_mcp_instance
        
        registered_tools = {}
        def tool_decorator():
            def wrapper(func):
                registered_tools[func.__name__] = func
                return func
            return wrapper
        mock_mcp_instance.tool = tool_decorator
        
        server = ZoteroKeeperServer()
        
        assert "search_items" in registered_tools
    
    @pytest.mark.asyncio
    @patch("zotero_mcp.infrastructure.mcp.server.ZoteroClient")
    @patch("zotero_mcp.infrastructure.mcp.server.FastMCP")
    @patch("zotero_mcp.infrastructure.mcp.server.register_resources")
    @patch("zotero_mcp.infrastructure.mcp.server.register_smart_tools")
    @patch("zotero_mcp.infrastructure.mcp.server.register_interactive_save_tools")
    @patch("zotero_mcp.infrastructure.mcp.server.register_saved_search_tools")
    async def test_list_collections_tool(
        self,
        mock_saved_search,
        mock_interactive,
        mock_smart,
        mock_resources,
        mock_mcp,
        mock_client_class,
    ):
        """Test list_collections tool is registered."""
        mock_mcp_instance = MagicMock()
        mock_mcp.return_value = mock_mcp_instance
        
        registered_tools = {}
        def tool_decorator():
            def wrapper(func):
                registered_tools[func.__name__] = func
                return func
            return wrapper
        mock_mcp_instance.tool = tool_decorator
        
        server = ZoteroKeeperServer()
        
        assert "list_collections" in registered_tools
    
    @pytest.mark.asyncio
    @patch("zotero_mcp.infrastructure.mcp.server.ZoteroClient")
    @patch("zotero_mcp.infrastructure.mcp.server.FastMCP")
    @patch("zotero_mcp.infrastructure.mcp.server.register_resources")
    @patch("zotero_mcp.infrastructure.mcp.server.register_smart_tools")
    @patch("zotero_mcp.infrastructure.mcp.server.register_interactive_save_tools")
    @patch("zotero_mcp.infrastructure.mcp.server.register_saved_search_tools")
    async def test_all_basic_tools_registered(
        self,
        mock_saved_search,
        mock_interactive,
        mock_smart,
        mock_resources,
        mock_mcp,
        mock_client_class,
    ):
        """Test all basic tools are registered."""
        mock_mcp_instance = MagicMock()
        mock_mcp.return_value = mock_mcp_instance
        
        registered_tools = {}
        def tool_decorator():
            def wrapper(func):
                registered_tools[func.__name__] = func
                return func
            return wrapper
        mock_mcp_instance.tool = tool_decorator
        
        server = ZoteroKeeperServer()
        
        expected_tools = [
            "check_connection",
            "search_items",
            "get_item",
            "list_items",
            "list_collections",
            "get_collection",
            "get_collection_items",
            "get_collection_tree",
            "find_collection",
            "list_tags",
            "get_item_types",
        ]
        
        for tool_name in expected_tools:
            assert tool_name in registered_tools, f"Tool {tool_name} not registered"


class TestServerRun:
    """Tests for server run method."""
    
    @patch("zotero_mcp.infrastructure.mcp.server.ZoteroClient")
    @patch("zotero_mcp.infrastructure.mcp.server.FastMCP")
    @patch("zotero_mcp.infrastructure.mcp.server.register_resources")
    @patch("zotero_mcp.infrastructure.mcp.server.register_smart_tools")
    @patch("zotero_mcp.infrastructure.mcp.server.register_interactive_save_tools")
    @patch("zotero_mcp.infrastructure.mcp.server.register_saved_search_tools")
    def test_run_method(
        self,
        mock_saved_search,
        mock_interactive,
        mock_smart,
        mock_resources,
        mock_mcp,
        mock_client_class,
    ):
        """Test server run method."""
        mock_mcp_instance = MagicMock()
        mock_mcp.return_value = mock_mcp_instance
        
        server = ZoteroKeeperServer()
        server.run("stdio")
        
        mock_mcp_instance.run.assert_called_once_with(transport="stdio")
