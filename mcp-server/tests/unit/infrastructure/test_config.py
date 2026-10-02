"""Configuration contract and edge tests (environment parsing, loopback rules, single config type)."""

import pytest

from zotero_mcp import __version__
from zotero_mcp.infrastructure.mcp.config import McpServerConfig
from zotero_mcp.infrastructure.mcp.config import ZoteroConfig as McpLayerZoteroConfig
from zotero_mcp.infrastructure.zotero_client.client import ZoteroConfig


def test_one_zotero_config_type_serves_both_layers():
    assert McpLayerZoteroConfig is ZoteroConfig
    assert isinstance(McpServerConfig().zotero, ZoteroConfig)


def test_defaults_and_environment_are_read(clean_env, monkeypatch):
    config = ZoteroConfig()
    assert (config.host, config.port, config.timeout) == ("localhost", 23119, 30.0)

    monkeypatch.setenv("ZOTERO_HOST", "127.0.0.1")
    monkeypatch.setenv("ZOTERO_PORT", " 12345 ")
    monkeypatch.setenv("ZOTERO_TIMEOUT", "2.5")
    config = ZoteroConfig()
    assert (config.host, config.port, config.timeout) == ("127.0.0.1", 12345, 2.5)


@pytest.mark.parametrize("value", ["abc", "0", "-1", "65536", "1.5", "23119; rm"])
def test_invalid_port_environment_fails_with_actionable_message(clean_env, monkeypatch, value):
    monkeypatch.setenv("ZOTERO_PORT", value)
    with pytest.raises(ValueError, match="ZOTERO_PORT must be an integer between 1 and 65535"):
        ZoteroConfig()


@pytest.mark.parametrize("value", ["abc", "0", "-5", "inf", "nan"])
def test_invalid_timeout_environment_fails_with_actionable_message(clean_env, monkeypatch, value):
    monkeypatch.setenv("ZOTERO_TIMEOUT", value)
    with pytest.raises(ValueError, match="ZOTERO_TIMEOUT"):
        ZoteroConfig()


def test_blank_environment_values_fall_back_to_defaults(clean_env, monkeypatch):
    monkeypatch.setenv("ZOTERO_PORT", "  ")
    monkeypatch.setenv("ZOTERO_TIMEOUT", "")
    config = ZoteroConfig()
    assert (config.port, config.timeout) == (23119, 30.0)


@pytest.mark.parametrize(
    ("host", "loopback", "base_url"),
    [
        ("localhost", True, "http://localhost:23119"),
        ("127.0.0.1", True, "http://127.0.0.1:23119"),
        ("::1", True, "http://[::1]:23119"),
        ("192.168.1.100", False, "http://192.168.1.100:23119"),
        ("zotero-server.local", False, "http://zotero-server.local:23119"),
    ],
)
def test_loopback_detection_and_url_formation(host, loopback, base_url):
    config = ZoteroConfig(host=host)
    assert config.is_loopback is loopback
    assert config.needs_host_header is (not loopback)
    assert config.base_url == base_url


def test_server_version_has_a_single_source_and_instructions_cover_core_tools():
    config = McpServerConfig()
    assert config.version == __version__
    for name in (
        "import_articles",
        "check_articles_owned",
        "export_items",
        "get_bibliography",
        "ZOTERO_KEEPER_ENABLE_LEGACY_PUBMED_TOOLS=1",
    ):
        assert name in config.instructions
