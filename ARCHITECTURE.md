# Architecture Documentation

This document describes the system architecture of Zotero Keeper, a MCP server for managing local Zotero libraries.

---

## 📖 Table of Contents

- [System Overview](#system-overview)
- [MCP Interface](#mcp-interface)
- [Layer Architecture](#layer-architecture)
- [Component Details](#component-details)
- [API Reference](#api-reference)
- [Data Flow](#data-flow)
- [Design Decisions](#design-decisions)

---

## System Overview

### High-Level Architecture

```
┌──────────────────────────────────────────────────────────────────────────┐
│                           CLIENT LAYER                                   │
│  ┌────────────────┐  ┌────────────────┐  ┌────────────────┐              │
│  │  VS Code       │  │ Claude Desktop │  │   Other MCP    │              │
│  │  Copilot Agent │  │                │  │   Clients      │              │
│  └───────┬────────┘  └───────┬────────┘  └───────┬────────┘              │
│          │                   │                   │                        │
│          └───────────────────┼───────────────────┘                        │
│                              │                                            │
│                              │ MCP Protocol (stdio/sse)                   │
│                              │ ├── Tools (21)                             │
│                              │ ├── Resources (10 URIs)                    │
│                              │ └── Elicitation (interactive input)        │
│                              ▼                                            │
│  ┌───────────────────────────────────────────────────────────────────┐   │
│  │                    ZOTERO KEEPER MCP SERVER                        │   │
│  │  ┌─────────────────────────────────────────────────────────────┐  │   │
│  │  │  MCP Layer (src/zotero_mcp/infrastructure/mcp/)              │  │   │
│  │  │  ├── server.py (11 core tools + setup)                       │  │   │
│  │  │  ├── resources.py (10 Resource URIs)                         │  │   │
│  │  │  ├── interactive_tools.py (2 tools + elicitation)            │  │   │
│  │  │  ├── saved_search_tools.py (3 tools)                         │  │   │
│  │  │  ├── search_tools.py (2 tools)                               │  │   │
│  │  │  ├── pubmed_tools.py (2 tools)                               │  │   │
│  │  │  ├── batch_tools.py (1 tool)                                 │  │   │
│  │  │  └── smart_tools.py (helpers only, no tools)                 │  │   │
│  │  └──────────────────────────┬──────────────────────────────────┘  │   │
│  │                             │                                      │   │
│  │  ┌──────────────────────────▼──────────────────────────────────┐  │   │
│  │  │  Infrastructure Layer                                        │  │   │
│  │  │  └── Zotero HTTP Client (dual API support)                   │  │   │
│  │  └──────────────────────────┬──────────────────────────────────┘  │   │
│  │                             │                                      │   │
│  │  ┌──────────────────────────▼──────────────────────────────────┐  │   │
│  │  │  Domain Layer                                                │  │   │
│  │  │  └── Entities (Reference, Collection, Creator)               │  │   │
│  │  └─────────────────────────────────────────────────────────────┘  │   │
│  └───────────────────────────────────────────────────────────────────┘   │
│                              │                                            │
│                              │ HTTP (port 23119)                          │
│                              ▼                                            │
│  ┌───────────────────────────────────────────────────────────────────┐   │
│  │                    ZOTERO DESKTOP CLIENT                           │   │
│  │  ├── Local API (/api/users/0/...)  → READ Operations              │   │
│  │  └── Connector API (/connector/...) → WRITE Operations            │   │
│  └───────────────────────────────────────────────────────────────────┘   │
└──────────────────────────────────────────────────────────────────────────┘
```

### Dual MCP Collaboration Architecture

Zotero Keeper is designed to work alongside `pubmed-search-mcp` for a complete literature workflow:

```
┌────────────────────────────┐    ┌────────────────────────────┐
│   pubmed-search-mcp        │    │      zotero-keeper         │
│   (Literature Discovery)   │    │   (Reference Management)   │
│                            │    │                            │
│  • search_literature       │    │  • search_items            │
│  • prepare_export (RIS)    │───▶│  • import_ris_to_zotero    │
│  • fetch_article_details   │    │  • batch_import_from_pubmed│
│  • parse_pico              │    │  • interactive_save        │
│  • merge_search_results    │    │  • quick_save              │
└────────────────────────────┘    └────────────────────────────┘
```

**Simple Workflow (Integrated Search):**
```
1. [zotero-keeper] search_pubmed_exclude_owned("CRISPR") → Only NEW papers
2. [zotero-keeper] batch_import_from_pubmed(pmids, tags=["CRISPR"]) → Zotero
```

**Advanced Workflow (Strategy Building):**
```
1. [pubmed-search] generate_search_queries("CRISPR") → MeSH terms
2. [zotero-keeper] search_pubmed_exclude_owned(query='"CRISPR-Cas"[MeSH]')
3. [zotero-keeper] batch_import_from_pubmed(pmids) → Zotero
```

---

## MCP Interface

### Tools (21 Total)

| File | Count | Tools |
|------|-------|-------|
| server.py | 11 | `check_connection`, `search_items`, `get_item`, `list_items`, `list_collections`, `get_collection`, `get_collection_items`, `get_collection_tree`, `find_collection`, `list_tags`, `get_item_types` |
| interactive_tools.py | 2 | `interactive_save`, `quick_save` |
| saved_search_tools.py | 3 | `list_saved_searches`, `run_saved_search`, `get_saved_search_details` |
| search_tools.py | 2 | `search_pubmed_exclude_owned`, `check_articles_owned` |
| pubmed_tools.py | 2 | `import_ris_to_zotero`, `import_from_pmids` |
| batch_tools.py | 1 | `batch_import_from_pubmed` |

### Resources (10 URIs)

| URI | Description |
|-----|-------------|
| `zotero://collections` | List all collections |
| `zotero://collections/tree` | Collection hierarchy |
| `zotero://collections/{key}` | Specific collection details |
| `zotero://collections/{key}/items` | Items in collection |
| `zotero://items` | Recent items |
| `zotero://items/{key}` | Item details |
| `zotero://tags` | All tags |
| `zotero://searches` | Saved searches |
| `zotero://searches/{key}` | Search details |
| `zotero://schema/item-types` | Available item types |

### Elicitation (Interactive Input)

The `interactive_save` tool uses MCP Elicitation to prompt users:

```python
# Example: Collection selection via elicitation
result = await ctx.elicit(
    message=formatted_options,  # Numbered list of collections
    schema={
        "type": "object",
        "properties": {
            "selection": {
                "type": "string",
                "description": "Enter the number of your choice"
            }
        }
    }
)
```

---

## Layer Architecture

### File Structure

```
src/zotero_mcp/
├── infrastructure/
│   ├── mcp/                    # MCP Server Layer
│   │   ├── server.py           # 11 core tools + server setup
│   │   ├── resources.py        # 10 Resource URIs
│   │   ├── interactive_tools.py # 2 save tools with elicitation
│   │   ├── saved_search_tools.py # 3 saved search tools
│   │   ├── search_tools.py     # 2 PubMed integration tools
│   │   ├── pubmed_tools.py     # 2 import tools
│   │   ├── batch_tools.py      # 1 batch import tool
│   │   ├── smart_tools.py      # Helper functions only (no tools)
│   │   └── config.py           # Configuration
│   └── zotero_client/          # Zotero HTTP Client
│       └── client.py           # Dual API (Local + Connector)
└── domain/
    └── entities/               # Domain entities
        ├── reference.py
        ├── collection.py
        └── creator.py
```

### smart_tools.py - Helpers Only

After simplification (v1.7.0), `smart_tools.py` contains only internal helper functions:

```python
# No @mcp.tool() decorators - just internal functions
def _normalize_title(title: str) -> str: ...
def _extract_identifier(item: dict, field: str) -> Optional[str]: ...
async def _suggest_collections(item: dict, zotero_client) -> list[dict]: ...
async def _find_duplicates(item: dict, zotero_client) -> list[dict]: ...
```

These functions are used by `interactive_tools.py` for:
- Collection suggestion (fuzzy matching)
- Duplicate detection (DOI/PMID/title)

---

## Component Details

### MCP Server (server.py)

The main entry point that:
1. Initializes FastMCP server
2. Creates Zotero HTTP client
3. Registers 11 core tools
4. Imports and registers tools from other modules
5. Registers Resources from `resources.py`

```python
class ZoteroKeeperServer:
    def __init__(self, config: ZoteroMcpConfig = None):
        self._mcp = FastMCP(name="zotero-keeper", version="1.7.0")
        self._zotero = ZoteroClient(config.zotero)
        self._register_tools()
        self._register_external_modules()
```

### Interactive Tools (interactive_tools.py)

Two main save tools with different interaction models:

| Tool | Interaction | Use Case |
|------|-------------|----------|
| `interactive_save` | Elicitation (numbered options) | User wants to choose collection |
| `quick_save` | None (direct save) | User specifies collection or skips |

**Auto-fetch Metadata Feature:**
```python
# When DOI or PMID provided, automatically fetch complete metadata
if auto_fetch_metadata:
    if pmid:
        fetched_metadata = await _fetch_metadata_from_pmid(pmid)
    elif doi:
        fetched_metadata = await _fetch_metadata_from_doi(doi)
    
    # Merge: user input takes priority, fetched fills gaps
    item = _merge_metadata(user_input, fetched_metadata)
```

### Resources (resources.py)

Replaces the old `collection_tools.py` with passive browsable data:

```python
@mcp.resource("zotero://collections")
async def list_collections_resource() -> str:
    collections = await zotero_client.get_collections()
    return json.dumps({"collections": collections})

@mcp.resource("zotero://collections/{key}/items")
async def get_collection_items_resource(key: str) -> str:
    items = await zotero_client.get_collection_items(key)
    return json.dumps({"items": items})
```

---

## API Reference

### Zotero Local API (READ)

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/users/0/items` | GET | List all items |
| `/api/users/0/items?q={query}` | GET | Search items |
| `/api/users/0/items/{key}` | GET | Get single item |
| `/api/users/0/collections` | GET | List collections |
| `/api/users/0/collections/{key}/items` | GET | Get collection items |
| `/api/users/0/searches` | GET | List saved searches |
| `/api/users/0/searches/{key}/items` | GET | **Execute saved search** (Local API exclusive!) |
| `/api/users/0/tags` | GET | List all tags |

### Zotero Connector API (WRITE)

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/connector/ping` | GET | Health check |
| `/connector/saveItems` | POST | Save items |

### External APIs (Auto-fetch Metadata)

| API | Purpose | Used By |
|-----|---------|---------|
| CrossRef API | DOI → full metadata | `_fetch_metadata_from_doi()` |
| PubMed E-utilities | PMID → full metadata | `_fetch_metadata_from_pmid()` |

---

## Data Flow

### Interactive Save Flow

```
User Request (title, DOI/PMID)
        │
        ▼
┌──────────────────────────┐
│  Auto-fetch Metadata     │ ← CrossRef/PubMed API
│  (if DOI/PMID provided)  │
└──────────┬───────────────┘
           │
           ▼
┌──────────────────────────┐
│  Validation              │ ← Check required fields
│  Duplicate Check         │ ← _find_duplicates()
└──────────┬───────────────┘
           │
           ▼
┌──────────────────────────┐
│  Suggest Collections     │ ← _suggest_collections()
│  (fuzzy matching)        │
└──────────┬───────────────┘
           │
           ▼
┌──────────────────────────┐
│  MCP Elicitation         │ ← User selects number
│  (numbered options)      │
└──────────┬───────────────┘
           │
           ▼
┌──────────────────────────┐
│  Save to Zotero          │ → Connector API
│  (with collection)       │
└──────────────────────────┘
```

### Resource Browse Flow

```
AI Agent
    │
    │ Request: zotero://collections
    ▼
┌──────────────────────────┐
│  MCP Resource Handler    │
│  (resources.py)          │
└──────────┬───────────────┘
           │
           ▼
┌──────────────────────────┐
│  Zotero Local API        │
│  GET /api/users/0/...    │
└──────────┬───────────────┘
           │
           ▼
┌──────────────────────────┐
│  JSON Response           │
│  (collections list)      │
└──────────────────────────┘
```

---

## Design Decisions

### Why Resources over Collection Tools?

| Aspect | Old (collection_tools.py) | New (resources.py) |
|--------|---------------------------|-------------------|
| Interaction | Active tool calls | Passive browsing |
| Tool Count | 3 tools | 0 tools (10 URIs) |
| Use Case | Explicit queries | Background context |
| AI Decision | Must choose tool | Can browse freely |

### Why Auto-fetch Metadata?

Problem: Users often provide only DOI/PMID, resulting in incomplete records (missing abstract).

Solution: Automatically fetch complete metadata from external APIs when identifiers are provided.

```python
# User provides minimal info
interactive_save(title="My Paper", doi="10.1234/example")

# System auto-fetches from CrossRef
→ Full abstract, all authors, journal name, volume, issue, pages
```

### Why Helpers in smart_tools.py?

The 6 original smart tools were redundant with `interactive_save`/`quick_save`. Consolidating them:
- Reduced tool count from 27 to 21
- Simplified AI decision-making
- Kept useful logic as internal helpers

### Why FastMCP?

- Native Python SDK for MCP
- Simple decorator-based API (`@mcp.tool()`, `@mcp.resource()`)
- Built-in elicitation support (`ctx.elicit()`)
- Active development and community

---

## Network Architecture

### Default (Local) Setup

```
┌──────────────┐     ┌──────────────┐
│  MCP Server  │────▶│   Zotero     │
│ (Same Host)  │HTTP │ (localhost)  │
│              │:23119              │
└──────────────┘     └──────────────┘
```

### Remote Setup (Requires Port Proxy)

```
┌──────────────┐           ┌──────────────┐           ┌──────────────┐
│  MCP Server  │──────────▶│  Port Proxy  │──────────▶│   Zotero     │
│  (Linux VM)  │ HTTP:23119│  (Windows)   │ localhost │  (Windows)   │
│  <MCP_HOST>  │           │    netsh     │  :23119   │ 127.0.0.1    │
└──────────────┘           └──────────────┘           └──────────────┘
```

---

## Security Considerations

1. **No Authentication**: Zotero Local API has no authentication
   - Only expose on trusted networks
   - Use firewall rules to restrict access

2. **Data Validation**: All input validated before sending to Zotero
   - Required field checks
   - Item type validation

3. **No Sensitive Data Stored**: MCP server is stateless
   - No credentials stored
   - No session data

---

## Future Considerations

1. **Multi-Library Support**: Support for group libraries
2. **Caching Layer**: Cache frequently accessed data
3. **WebSocket**: Real-time updates when Zotero changes
4. **Attachment Handling**: PDF management

---

*Last updated: December 14, 2024*
