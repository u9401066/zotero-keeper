"""
MCP Server Configuration

Configuration for the Zotero Keeper MCP Server.
"""

import os
from dataclasses import dataclass, field


@dataclass
class ZoteroConfig:
    """Zotero connection configuration"""

    host: str = field(default_factory=lambda: os.getenv("ZOTERO_HOST", "localhost"))
    port: int = field(default_factory=lambda: int(os.getenv("ZOTERO_PORT", "23119")))
    timeout: float = field(default_factory=lambda: float(os.getenv("ZOTERO_TIMEOUT", "30")))

    @property
    def base_url(self) -> str:
        return f"http://{self.host}:{self.port}"

    @property
    def host_header(self) -> str:
        """Required header for port proxy (when Zotero is on remote machine)"""
        return f"127.0.0.1:{self.port}"

    @property
    def needs_host_header(self) -> bool:
        """Check if we need to override Host header (remote connection)"""
        return self.host not in ("localhost", "127.0.0.1")


@dataclass
class McpServerConfig:
    """MCP Server configuration"""

    name: str = "Zotero Keeper"
    version: str = "1.2.0"

    # Zotero connection
    zotero: ZoteroConfig = field(default_factory=ZoteroConfig)

    # Server instructions for AI agents
    instructions: str = """
Zotero Keeper - MCP Server for managing local Zotero libraries.

## 🔧 AVAILABLE TOOLS

### Read Operations (via Zotero Local API)
- `search_items(query, limit)` - Search references by title/author/year
- `get_item(key)` - Get detailed metadata for a specific item
- `list_items(limit, collection_key)` - List recent items
- `list_collections()` - List all collections (folders)
- `list_tags()` - List all tags
- `get_item_types()` - Get available item types (journalArticle, book, etc.)

### Write Operations (via Zotero Connector API)
- `add_reference(...)` - Add a new bibliographic reference
- `create_item(item_type, title, ...)` - Create item with full metadata

## 📋 RECOMMENDED WORKFLOW

1. Search existing references: `search_items("machine learning")`
2. Check if reference exists before adding
3. Add new reference: `add_reference(title="...", item_type="journalArticle", ...)`

## ⚠️ NOTES

- All operations are local (no cloud sync required)
- Zotero must be running for operations to work
- Use `check_connection()` to verify connectivity
"""


# Default configuration instance
default_config = McpServerConfig()
