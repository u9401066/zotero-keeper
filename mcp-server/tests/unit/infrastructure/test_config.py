"""
Unit tests for ZoteroConfig and McpServerConfig.
"""


class TestZoteroConfig:
    """Test ZoteroConfig dataclass."""

    def test_zotero_config_defaults(self, clean_env):
        """Test ZoteroConfig default values."""
        from zotero_mcp.infrastructure.zotero_client.client import ZoteroConfig

        config = ZoteroConfig()

        assert config.host == "localhost"
        assert config.port == 23119
        assert config.timeout == 30.0

    def test_zotero_config_from_env(self, mock_env):
        """Test ZoteroConfig reads from environment."""
        from zotero_mcp.infrastructure.zotero_client.client import ZoteroConfig

        config = ZoteroConfig()

        assert config.host == "test-host"
        assert config.port == 12345
        assert config.timeout == 60.0

    def test_zotero_config_explicit_values(self):
        """Test ZoteroConfig with explicit values."""
        from zotero_mcp.infrastructure.zotero_client.client import ZoteroConfig

        config = ZoteroConfig(host="custom-host", port=9999, timeout=120.0)

        assert config.host == "custom-host"
        assert config.port == 9999
        assert config.timeout == 120.0

    def test_zotero_config_base_url(self):
        """Test base_url property."""
        from zotero_mcp.infrastructure.zotero_client.client import ZoteroConfig

        config = ZoteroConfig(host="example.com", port=8080)

        assert config.base_url == "http://example.com:8080"

    def test_zotero_config_base_url_localhost(self):
        """Test base_url with localhost."""
        from zotero_mcp.infrastructure.zotero_client.client import ZoteroConfig

        config = ZoteroConfig(host="localhost", port=23119)

        assert config.base_url == "http://localhost:23119"

    def test_zotero_config_host_header(self):
        """Test host_header property."""
        from zotero_mcp.infrastructure.zotero_client.client import ZoteroConfig

        config = ZoteroConfig(host="192.168.1.100", port=23119)

        assert config.host_header == "127.0.0.1:23119"

    def test_zotero_config_needs_host_header_localhost(self):
        """Test needs_host_header is False for localhost."""
        from zotero_mcp.infrastructure.zotero_client.client import ZoteroConfig

        config = ZoteroConfig(host="localhost")
        assert config.needs_host_header is False

    def test_zotero_config_needs_host_header_127(self):
        """Test needs_host_header is False for 127.0.0.1."""
        from zotero_mcp.infrastructure.zotero_client.client import ZoteroConfig

        config = ZoteroConfig(host="127.0.0.1")
        assert config.needs_host_header is False

    def test_zotero_config_needs_host_header_remote(self):
        """Test needs_host_header is True for remote host."""
        from zotero_mcp.infrastructure.zotero_client.client import ZoteroConfig

        config = ZoteroConfig(host="192.168.1.100")
        assert config.needs_host_header is True

    def test_zotero_config_needs_host_header_hostname(self):
        """Test needs_host_header is True for hostname."""
        from zotero_mcp.infrastructure.zotero_client.client import ZoteroConfig

        config = ZoteroConfig(host="zotero-server.local")
        assert config.needs_host_header is True


class TestMcpServerConfig:
    """Test McpServerConfig dataclass."""

    def test_mcp_server_config_defaults(self):
        """Test McpServerConfig default values."""
        from zotero_mcp.infrastructure.mcp.config import McpServerConfig

        config = McpServerConfig()

        assert config.name == "Zotero Keeper"
        assert config.version == "1.2.0"
        assert config.zotero is not None

    def test_mcp_server_config_instructions(self):
        """Test McpServerConfig instructions contain expected content."""
        from zotero_mcp.infrastructure.mcp.config import McpServerConfig

        config = McpServerConfig()

        assert "Zotero Keeper" in config.instructions
        assert "search_items" in config.instructions
        assert "add_reference" in config.instructions

    def test_mcp_server_config_has_zotero_config(self):
        """Test McpServerConfig contains ZoteroConfig."""
        from zotero_mcp.infrastructure.mcp.config import McpServerConfig, ZoteroConfig

        config = McpServerConfig()

        assert isinstance(config.zotero, ZoteroConfig)


class TestDefaultConfig:
    """Test default_config instance."""

    def test_default_config_exists(self):
        """Test default_config is available."""
        from zotero_mcp.infrastructure.mcp.config import default_config

        assert default_config is not None
        assert default_config.name == "Zotero Keeper"


class TestZoteroClientConfig:
    """Test ZoteroConfig from client module."""

    def test_config_dataclass_fields(self):
        """Test ZoteroConfig has expected fields."""
        from zotero_mcp.infrastructure.zotero_client.client import ZoteroConfig

        config = ZoteroConfig()

        assert hasattr(config, "host")
        assert hasattr(config, "port")
        assert hasattr(config, "timeout")
        assert hasattr(config, "base_url")
        assert hasattr(config, "host_header")
        assert hasattr(config, "needs_host_header")


class TestConfigEdgeCases:
    """Test edge cases for configuration."""

    def test_config_zero_timeout(self):
        """Test config with zero timeout."""
        from zotero_mcp.infrastructure.zotero_client.client import ZoteroConfig

        config = ZoteroConfig(timeout=0.0)
        assert config.timeout == 0.0

    def test_config_negative_port(self):
        """Test config with negative port (invalid but accepted)."""
        from zotero_mcp.infrastructure.zotero_client.client import ZoteroConfig

        config = ZoteroConfig(port=-1)
        assert config.port == -1

    def test_config_empty_host(self):
        """Test config with empty host."""
        from zotero_mcp.infrastructure.zotero_client.client import ZoteroConfig

        config = ZoteroConfig(host="")
        assert config.base_url == "http://:23119"

    def test_config_unicode_host(self):
        """Test config with unicode host."""
        from zotero_mcp.infrastructure.zotero_client.client import ZoteroConfig

        config = ZoteroConfig(host="日本語ホスト.local")
        assert "日本語" in config.host
