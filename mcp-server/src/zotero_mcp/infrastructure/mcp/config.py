"""
MCP Server Configuration

Configuration for the Zotero Keeper MCP Server.
"""

import os
from dataclasses import dataclass, field

from zotero_mcp import __version__

from ..zotero_client.client_base import ZoteroConfig


def _env_flag(name: str, default: bool = False) -> bool:
    """Parse boolean-like environment flags."""
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


@dataclass
class McpServerConfig:
    """MCP Server configuration"""

    name: str = "Zotero Keeper"
    version: str = __version__

    # Zotero connection
    zotero: ZoteroConfig = field(default_factory=ZoteroConfig)

    # Compatibility mode for legacy PubMed bridge tools.
    # Default OFF to avoid duplicating pubmed-search-mcp's public tool surface.
    enable_legacy_pubmed_tools: bool = field(default_factory=lambda: _env_flag("ZOTERO_KEEPER_ENABLE_LEGACY_PUBMED_TOOLS", False))

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

### Citation Export (read-only)
- `export_items(item_keys, format="bibtex")` - BibTeX/RIS/CSL JSON/... for up to
  50 exact item keys via Zotero's own translators; check `missing_count`
- `get_bibliography(item_keys, style="apa", output="bib")` - CSL-formatted
  references / in-text citations; check `missing_keys`
- Use these on Zotero keys instead of rebuilding citations from search snippets

### Zotero 10+ Local API Management
- `authorize_local_writes(require_remembered=false)` - Ask Zotero for runtime
  write approval; use `true` before file upload. The key stays private inside
  Keeper
- `create_collection(...)` - Create a confirmed top-level or nested collection
- `add_items_to_collection(...)` - Preserve existing memberships while adding
  exact items to one confirmed collection
- `update_item_fields(...)` - Version-protected scalar metadata update
- `create_note(...)` / `create_saved_search(...)` - Confirmed local creation
- `attach_file_to_item(...)` - Attach a local file to an existing item
- `set_attachment_fulltext(...)` - Version-protected indexed-text write

Every Local API mutation first returns a proposal with `confirm=false`. Obtain
explicit user approval before repeating it with `confirm=true`. Never request,
display, or persist the Zotero Local API key, and never replay a 412 conflict.

Never import to My Library root without explicit user confirmation. Only after
that confirmation may a non-interactive tool set `allow_library_root=true`.

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
