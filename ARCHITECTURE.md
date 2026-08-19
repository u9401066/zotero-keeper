# Architecture Documentation

This document describes Zotero Keeper 2.2.0, the 41-tool MCP SDK v2 server
bundled by the v0.8.0 VSIX for safe local Zotero library management.

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
│                              │ MCP Protocol (stdio)                       │
│                              │ ├── Tools (41 default + 5 legacy opt-in)   │
│                              │ ├── Resources (6 + 4 URI templates)        │
│                              │ └── Elicitation (interactive input)        │
│                              ▼                                            │
│  ┌───────────────────────────────────────────────────────────────────┐   │
│  │                    ZOTERO KEEPER MCP SERVER                        │   │
│  │  ┌─────────────────────────────────────────────────────────────┐  │   │
│  │  │  MCP Layer (src/zotero_mcp/infrastructure/mcp/)              │  │   │
│  │  │  ├── server.py (connection tool + setup)                     │  │   │
│  │  │  ├── basic_read_tools.py (5 tools)                           │  │   │
│  │  │  ├── collection_tools.py (5 tools)                           │  │   │
│  │  │  ├── local_api_tools.py (17 guarded Zotero 10+ tools)       │  │   │
│  │  │  ├── interactive_tools.py (2 tools + elicitation)            │  │   │
│  │  │  ├── saved_search_tools.py (3 tools)                         │  │   │
│  │  │  ├── search_tools.py (2 public + 1 legacy tool)              │  │   │
│  │  │  ├── unified_import_tools.py (2 tools)                        │  │   │
│  │  │  ├── analytics_tools.py (2 tools)                            │  │   │
│  │  │  ├── attachment_tools.py (2 tools)                           │  │   │
│  │  │  ├── pubmed_tools.py / batch_tools.py (legacy import tools)  │  │   │
│  │  │  ├── resources.py (6 resources + 4 URI templates)            │  │   │
│  │  │  └── smart_tools.py (helpers only, no tools)                 │  │   │
│  │  └──────────────────────────┬──────────────────────────────────┘  │   │
│  │                             │                                      │   │
│  │  ┌──────────────────────────▼──────────────────────────────────┐  │   │
│  │  │  Infrastructure Layer                                        │  │   │
│  │  │  └── Zotero HTTP Client (Local + Connector adapters)         │  │   │
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
│  │  ├── Local API v3 → READ + authorized WRITE (Zotero 10+)          │   │
│  │  └── Connector API → compatibility CREATE/import path             │   │
│  └───────────────────────────────────────────────────────────────────┘   │
└──────────────────────────────────────────────────────────────────────────┘
```

### Dual MCP Collaboration Architecture

Zotero Keeper is designed to work alongside `pubmed-search-mcp` for a complete literature workflow:

The v0.8.0 VSIX pins Keeper 2.2.0 and PubMed Search MCP 0.6.3 at release commit `febf53a`. PubMed contributes 45 MCP SDK v2 tools across 16 categories, including governed SearchRun status/replay, bounded systematic and native-semantic modes, and the two-tool Research Chronicle surface.

```
┌────────────────────────────┐    ┌────────────────────────────┐
│   pubmed-search-mcp        │    │      zotero-keeper         │
│   (Literature Discovery)   │    │   (Reference Management)   │
│                            │    │                            │
│  • unified_search          │    │  • search_items            │
│  • prepare_export (RIS)    │───▶│  • import_articles         │
│  • fetch_article_details   │    │  • check_articles_owned    │
│  • parse_pico              │    │  • interactive_save        │
│  • get_citation_metrics    │    │  • quick_save              │
└────────────────────────────┘    └────────────────────────────┘
```

**Recommended Workflow (Collaboration-safe):**
```
1. [pubmed-search] unified_search("CRISPR") → structured articles
2. [zotero-keeper] check_articles_owned(pmids=[...]) → filter owned
3. [zotero-keeper] import_articles(articles=..., collection_name="CRISPR") → Zotero
```

**Legacy Workflow (requires ZOTERO_KEEPER_ENABLE_LEGACY_PUBMED_TOOLS=1):**
```
1. [zotero-keeper] search_pubmed_exclude_owned("CRISPR") → Only NEW papers
2. [zotero-keeper] batch_import_from_pubmed(pmids, tags=["CRISPR"]) → Zotero
```

**Advanced Workflow (Strategy Building):**
```
1. [pubmed-search] generate_search_queries("CRISPR") → MeSH terms
2. [pubmed-search] unified_search(query='"CRISPR-Cas"[MeSH]') → structured articles
3. [zotero-keeper] check_articles_owned(pmids=[...]) → filter owned
4. [zotero-keeper] import_articles(articles=..., collection_name="CRISPR") → Zotero
```

This two-server environment must not install another Python distribution named `zotero_mcp`. The MCP Registry-listed community project `54yyyu/zotero-mcp` shares that module name with Keeper; coexistence requires a separate virtual environment and MCP process. See [Zotero MCP landscape](docs/ZOTERO_MCP_LANDSCAPE.md).

---

## MCP Interface

### Tools (Default Public Surface)

| File | Count | Tools |
|------|-------|-------|
| server.py | 1 | `check_connection` |
| basic_read_tools.py | 5 | `search_items`, `get_item`, `list_items`, `list_tags`, `get_item_types` |
| collection_tools.py | 5 | `list_collections`, `get_collection`, `get_collection_items`, `get_collection_tree`, `find_collection` |
| local_api_tools.py | 8 | `authorize_local_writes`, `create_collection`, `add_items_to_collection`, `update_item_fields`, `create_note`, `create_saved_search`, `attach_file_to_item`, `set_attachment_fulltext` |
| saved_search_tools.py | 3 | `list_saved_searches`, `run_saved_search`, `get_saved_search_details` |
| search_tools.py | 2 | `advanced_search`, `check_articles_owned` |
| interactive_tools.py | 2 | `interactive_save`, `quick_save` |
| unified_import_tools.py | 2 | `import_articles` ⭐, `import_pdf` 📎 |
| analytics_tools.py | 2 | `get_library_stats`, `find_orphan_items` |
| attachment_tools.py | 2 | `get_item_attachments`, `get_item_fulltext` |

### Legacy Tools (opt-in via ZOTERO_KEEPER_ENABLE_LEGACY_PUBMED_TOOLS=1)

| File | Count | Tools |
|------|-------|-------|
| search_tools.py | 1 | `search_pubmed_exclude_owned` |
| pubmed_tools.py | 3 | `import_ris_to_zotero`, `import_from_pmids`, `quick_import_pmids` |
| batch_tools.py | 1 | `batch_import_from_pubmed` |

### Resources (6 concrete + 4 URI templates)

MCP SDK v2 reports six concrete resources through `resources/list`. Four parameterized routes are advertised separately through `resources/templates/list`.

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

The `interactive_save` tool uses SDK v2 resolver dependencies to prompt users.
It does not call `ctx.elicit()` directly because the current protocol does not
provide an in-tool server-to-client backchannel:

```python
from typing import Annotated
from mcp.server.mcpserver import Elicit, Resolve
from pydantic import BaseModel

class CollectionChoice(BaseModel):
    choice: str

async def choose_collection(...) -> CollectionChoice | Elicit[CollectionChoice]:
    return Elicit(formatted_options, CollectionChoice)

collection_dependency = Resolve(choose_collection)

@mcp.tool()
async def interactive_save(
    ...,
    collection_choice: Annotated[CollectionChoice, collection_dependency],
):
    # The final tool body is the only write boundary.
    ...
```

`ROOT` always enters a second confirmation step. `skip_collection_prompt=True` aborts rather than choosing root. Non-interactive `quick_save`, `import_articles`, and `import_pdf` calls require a collection unless explicit user approval is carried as `allow_library_root=true`.

---

## Layer Architecture

### File Structure

```
src/zotero_mcp/
├── infrastructure/
│   ├── mcp/                    # MCP Server Layer
│   │   ├── server.py           # Connection tool + server setup
│   │   ├── basic_read_tools.py # 5 read tools
│   │   ├── collection_tools.py # 5 collection tools
│   │   ├── local_api_tools.py # 17 guarded Zotero 10+ write tools
│   │   ├── resources.py        # 6 resources + 4 URI templates
│   │   ├── interactive_tools.py # 2 save tools with elicitation
│   │   ├── saved_search_tools.py # 3 saved search tools
│   │   ├── search_tools.py     # 2 public search tools + 1 legacy bridge
│   │   ├── unified_import_tools.py # import_articles + import_pdf
│   │   ├── analytics_tools.py  # 2 analytics tools
│   │   ├── attachment_tools.py # 2 attachment/fulltext tools
│   │   ├── pubmed_tools.py     # 3 legacy import tools
│   │   ├── batch_tools.py      # 1 legacy batch import tool
│   │   ├── smart_tools.py      # Helper functions only (no tools)
│   │   └── config.py           # Configuration
│   └── zotero_client/          # Zotero HTTP Client
│       ├── client.py           # Composed client facade
│       ├── client_base.py      # HTTP, discovery state, capability probe
│       ├── client_read.py      # Local API reads
│       ├── client_local.py     # Authorized Zotero 10+ CRUD/upload primitives
│       └── client_write.py     # Connector compatibility writes
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
1. Initializes the MCP SDK v2 `MCPServer`
2. Creates Zotero HTTP client
3. Registers the connection tool and shared resources
4. Imports and registers tools from other modules
5. Registers Resources from `resources.py`

```python
class ZoteroKeeperServer:
    def __init__(self, config: ZoteroMcpConfig = None):
        self._mcp = MCPServer(
            name="zotero-keeper",
            version="2.2.0",
            instructions="Zotero library management and import",
        )
        self._zotero = ZoteroClient(config.zotero)
        self._register_tools()
        self._register_external_modules()
```

### Interactive Tools (interactive_tools.py)

Two main save tools with different interaction models:

| Tool | Interaction | Use Case |
|------|-------------|----------|
| `interactive_save` | Elicitation (exact collection key; double-confirmed `ROOT`) | User wants to choose collection |
| `quick_save` | None (direct save) | User specifies a collection, or explicitly approves root with `allow_library_root=true` |

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

### Zotero Local API v3

The adapter begins with `GET /api/`. Zotero 10+ responses carry
`Zotero-Server-ID`; write authorization uses `/api/local/authorize`, and every
confirmed mutation is bound to the response identity already present in its
approved preview. Object updates and full-text writes additionally use their
respective optimistic-concurrency cursor so a stale read returns 412 instead of
overwriting a newer local transaction.

| Endpoint | Methods | Keeper use |
|----------|---------|------------|
| `/api/` | GET | Discover API/schema version and Server-ID without prompting |
| `/api/local/authorize` | POST | Runtime user authorization; key remains private in memory |
| `/api/users/0/items[/<key>]` | GET/POST/PATCH/DELETE | Reads, guarded note creation, scalar update, exact delete, batch organization |
| `/api/users/0/collections[/<key>]` | GET/POST/PATCH/DELETE | Reads and confirmed collection create/update/move/delete |
| `/api/users/0/searches[/<key>][/items]` | GET/POST/PATCH/DELETE | Saved-search reads/execution and confirmed lifecycle operations |
| `/api/users/0/tags` | GET/DELETE | Read tags and delete exact names with a library cursor |
| `/api/users/0/items/<key>/file/view/url` | GET | Official local attachment path discovery |
| `/api/users/0/items/<key>/file` | POST | Three-phase stored-file creation or MD5-guarded replacement |
| `/api/users/0/items/<key>/fulltext` | GET | Indexed full-text read and response-bound library cursor |
| `/api/users/0/fulltext` | POST | Bulk full-text replacement with `If-Unmodified-Since-Version` library cursor |

The MCP layer exposes task-oriented, versioned lifecycle operations but no
arbitrary raw endpoint, unrestricted structural-array replacement, batch object
deletion, or group-library write surface.

### Zotero Connector compatibility path

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/connector/ping` | GET | Desktop health/version check |
| `/connector/saveItems` | POST | Existing create/import tools, including Zotero 7–9 |
| `/connector/saveAttachment` | POST | Attach within a Connector session that created the parent |
| `/connector/saveStandaloneAttachment` | POST | Standalone import/recognition |

### External APIs (Auto-fetch Metadata)

| API | Purpose | Used By |
|-----|---------|---------|
| CrossRef API | DOI → full metadata | `_fetch_metadata_from_doi()` |
| PubMed E-utilities | PMID → full metadata | `_fetch_metadata_from_pmid()` |
| NIH iCite API | PMID → citation metrics (RCR) | `batch_import_from_pubmed(include_citation_metrics=True)` |

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
│  MCP Elicitation         │ ← User submits exact key
│  (ROOT = confirm again)  │
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

### Zotero 10+ Mutation Flow

```text
response-bound Local API read or authorize
  ├── Zotero-Server-ID
  ├── exact object version (update or single-object delete),
  ├── library cursor (tag or full-text batch), or
  └── attachment version + previous MD5 (stored-file replacement)
        │
        ▼
MCP mutation (confirm=false, expected_server_id=...)
        │
        └── complete proposal only; zero Zotero/filesystem I/O

explicit user approval
        │
        ▼
authorize_local_writes (separate Zotero UI prompt, if needed)
        ├── same Server-ID → continue
        └── different Server-ID → restart read + preview + approval
        │
        ▼
same MCP mutation (confirm=true, unchanged proposal)
  ├── Zotero-Server-ID
  ├── private Zotero-API-Key
  └── object/library-version or write-token precondition
        │
        ├── success → structured result
        └── 401/412/428/timeout → fail closed, never replay mutation
```

One-shot authorizations and mutations are serialized. Multi-phase attachment
creation and replacement require an Always Allow authorization; replacement
uses the same reviewed MD5 as `If-Match` for authorization and registration.
Upload bytes are sent only to a validated loopback
`/api/local/uploads/<key>` URL, without the API-key header.

---

## Design Decisions

### Why both Resources and Collection Tools?

| Surface | Best use |
|---------|----------|
| Collection tools | Explicit, parameterized actions and clients that primarily operate through tools |
| Six concrete resources | Passive browsing of stable library entry points |
| Four URI templates | Direct lookup of a known item, collection, collection contents, or saved search |

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

### Why MCP SDK v2 `MCPServer`?

- Current native Python SDK API for MCP 2.x
- Simple decorator-based API (`@mcp.tool()`, `@mcp.resource()`)
- Protocol-portable elicitation via `Resolve(...)` dependencies that return
  `Elicit(...)`, without relying on a direct context backchannel
- Explicit resources and resource-template discovery

MCP SDK 2.0 is intentionally incompatible with the old 1.x `FastMCP` interface. Keeper 2.2.0 and PubMed Search MCP 0.6.3 therefore share one SDK v2 runtime in the extension-managed environment.

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

### Remote libraries

Do not forward Zotero's Local/Connector port to another host. Zotero 10+ Local
writes require runtime approval, but the key is unscoped and local reads remain
unauthenticated. Use Zotero's authenticated HTTPS Web API, or an authenticated
service with TLS and explicit access control. Local/Connector workflows require
Keeper and Zotero Desktop on the same machine, communicating over literal
loopback.

---

## Security Considerations

1. **Loopback and authorization**: Local reads and Connector endpoints retain a
   same-machine trust boundary; Zotero 10+ write keys are runtime-authorized but
   unscoped
   - Keep port 23119 on loopback and never forward it
   - Keep the key in process memory; never return/log/persist it
   - Bind every confirmed mutation to the response-bound Server-ID included in
     its approved preview; a changed authorization identity requires a fresh
     read, preview, and approval
   - Pair object versions, tag/full-text library cursors, and attachment MD5s
     with the identity from the same response; never add identity after preview

2. **Data Validation**: All input validated before sending to Zotero
   - Required field checks
   - Item type validation

3. **No Sensitive Data Stored**: MCP server keeps only ephemeral runtime state
   - Local write credentials remain in memory and clear on process close
   - Authorization capability and local-version caches are Server-ID scoped and
     are never durable application state

---

## Future Considerations

1. **Multi-Library Support**: Support for group libraries
2. **Caching Layer**: Cache frequently accessed data
3. **WebSocket**: Real-time updates when Zotero changes
4. **Attachment Handling**: broader annotation workflows; creation and
   replacement of stored files are delivered in 2.2
5. **Optional Zotero Plugin**: annotations, real-time events, Zotero-native UI,
   selected internal-only operations, and a possible Zotero 7–9 write fallback.
   Zotero 10+ basic CRUD and stored-file upload no longer require a plugin.

---

*Last updated: August 19, 2026 (Keeper 2.2.0 / MCP SDK v2)*
