"""
MCP Server Configuration

Configuration for the Zotero Keeper MCP Server.
"""

import os
from dataclasses import dataclass, field


def _env_flag(name: str, default: bool = False) -> bool:
    """Parse boolean-like environment flags."""
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


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
    version: str = "1.12.0"

    # Zotero connection
    zotero: ZoteroConfig = field(default_factory=ZoteroConfig)

    # Compatibility mode for legacy PubMed bridge tools.
    # Default OFF to avoid duplicating pubmed-search-mcp's public tool surface.
    enable_legacy_pubmed_tools: bool = field(
        default_factory=lambda: _env_flag("ZOTERO_KEEPER_ENABLE_LEGACY_PUBMED_TOOLS", False)
    )

    # Server instructions for AI agents
    instructions: str = """
Zotero Keeper - MCP Server for managing local Zotero libraries.

## Tool Ownership

- pubmed-search-mcp owns search, discovery, export, and citation-metrics tools
- zotero-keeper owns Zotero library reads, collection selection, duplicate checks, and import/persist into Zotero
- Default mode is collaboration-safe: legacy PubMed bridge tools are hidden unless
    `ZOTERO_KEEPER_ENABLE_LEGACY_PUBMED_TOOLS=1`

## Recommended Tools

### Library Query
- `search_items(query, limit)` - Search existing Zotero items
- `advanced_search(...)` - Multi-condition Zotero search
- `get_item(key)` - Get a Zotero item by key
- `list_items(limit, collection_key)` - List recent items
- `list_collections()` - List available collections before import
- `run_saved_search(key)` - Execute a saved Zotero search

### Import & Persist
- `import_articles(articles=..., ris_text=..., collection_name=...)` - Single import gateway
- `interactive_save(...)` - Manual save with elicitation and optional metadata fetch
- `quick_save(...)` - Manual save without prompts
- `check_articles_owned(pmids=[...])` - Check whether PubMed records already exist locally

## Recommended Collaboration Workflow

1. Use pubmed-search-mcp to search and enrich articles
2. Use zotero-keeper `check_articles_owned()` if local duplicate filtering is needed
3. Use zotero-keeper `list_collections()` to choose a target collection
4. Use zotero-keeper `import_articles()` to persist results into Zotero

## Notes

- All operations are local to Zotero
- Zotero must be running for operations to work
- Use `check_connection()` to verify connectivity
"""


# Default configuration instance
default_config = McpServerConfig()
