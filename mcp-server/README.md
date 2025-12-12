# Zotero Keeper MCP Server

MCP Server for managing local Zotero libraries via AI Agents.

## Installation

```bash
# Basic installation
pip install -e .

# With PubMed support
pip install -e ".[pubmed]"

# All features
pip install -e ".[all]"
```

## Usage

```bash
# Run MCP server
python -m zotero_mcp

# Or use the CLI
zotero-keeper
```

## Environment Variables

```bash
ZOTERO_HOST=YOUR_ZOTERO_HOST  # Zotero machine IP
ZOTERO_PORT=23119        # Zotero HTTP port
```

## MCP Tools

- `check_connection` - Test Zotero connectivity
- `search_items` - Search references
- `get_item` - Get item by key
- `list_items` - List recent items
- `list_collections` - List collections
- `list_tags` - List tags
- `get_item_types` - Get available types
- `add_reference` - Add new reference
- `create_item` - Create with full metadata

### PubMed Tools (optional)

- `search_pubmed_and_import` - Search PubMed and import to Zotero
- `import_pubmed_articles` - Import by PMID
- `get_pubmed_article_details` - Get article details

## Documentation

See [main README](../README.md) for full documentation.
