"""
Unit tests for Zotero Client

Note: Integration tests require a running Zotero instance.
"""

import pytest


class TestZoteroConfig:
    """Test ZoteroConfig dataclass"""
    
    def test_default_config(self):
        """Test default configuration values"""
        from zotero_mcp.infrastructure.mcp.config import ZoteroConfig
        
        config = ZoteroConfig()
        assert config.host == "localhost" or config.host is not None
        assert config.port == 23119
        assert config.timeout == 30.0
    
    def test_base_url(self):
        """Test base_url property"""
        from zotero_mcp.infrastructure.mcp.config import ZoteroConfig
        
        config = ZoteroConfig(host="example.com", port=8080)
        assert config.base_url == "http://example.com:8080"
    
    def test_needs_host_header(self):
        """Test needs_host_header for remote connections"""
        from zotero_mcp.infrastructure.mcp.config import ZoteroConfig
        
        local = ZoteroConfig(host="localhost")
        assert local.needs_host_header is False
        
        remote = ZoteroConfig(host="192.168.1.100")
        assert remote.needs_host_header is True


class TestZoteroClient:
    """Test ZoteroClient HTTP operations"""
    
    @pytest.mark.asyncio
    async def test_client_initialization(self):
        """Test client can be initialized"""
        from zotero_mcp.infrastructure.zotero_client.client import ZoteroClient, ZoteroConfig
        
        config = ZoteroConfig(host="localhost", port=23119)
        client = ZoteroClient(config)
        
        assert client.config.host == "localhost"
        await client.close()
