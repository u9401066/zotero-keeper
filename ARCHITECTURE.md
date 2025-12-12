# Architecture Documentation

This document describes the system architecture of Zotero Keeper, a MCP server for managing local Zotero libraries.

---

## 📖 Table of Contents

- [System Overview](#system-overview)
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
│                              ▼                                            │
│  ┌───────────────────────────────────────────────────────────────────┐   │
│  │                    ZOTERO KEEPER MCP SERVER                        │   │
│  │  ┌─────────────────────────────────────────────────────────────┐  │   │
│  │  │  Infrastructure Layer                                        │  │   │
│  │  │  ├── FastMCP Server (Tools Registration)                     │  │   │
│  │  │  ├── MCP Tools Handler                                       │  │   │
│  │  │  └── Zotero HTTP Client                                      │  │   │
│  │  └──────────────────────────┬──────────────────────────────────┘  │   │
│  │                             │                                      │   │
│  │  ┌──────────────────────────▼──────────────────────────────────┐  │   │
│  │  │  Application Layer                                           │  │   │
│  │  │  └── Use Cases (SearchItems, AddReference, ValidateRef)      │  │   │
│  │  └──────────────────────────┬──────────────────────────────────┘  │   │
│  │                             │                                      │   │
│  │  ┌──────────────────────────▼──────────────────────────────────┐  │   │
│  │  │  Domain Layer                                                │  │   │
│  │  │  ├── Entities (Item, Collection, Creator, Tag)               │  │   │
│  │  │  ├── Value Objects (ItemType, DOI, ISBN)                     │  │   │
│  │  │  └── Repository Interfaces                                   │  │   │
│  │  └─────────────────────────────────────────────────────────────┘  │   │
│  └───────────────────────────────────────────────────────────────────┘   │
│                              │                                            │
│                              │ HTTP (port 23119)                          │
│                              ▼                                            │
│  ┌───────────────────────────────────────────────────────────────────┐   │
│  │                    ZOTERO DESKTOP CLIENT                           │   │
│  │  ┌─────────────────────────────────────────────────────────────┐  │   │
│  │  │  Built-in HTTP Server (127.0.0.1:23119)                      │  │   │
│  │  │  ├── Local API (/api/users/0/...)  → READ Operations         │  │   │
│  │  │  │   - GET /api/users/0/items                                │  │   │
│  │  │  │   - GET /api/users/0/collections                          │  │   │
│  │  │  │   - GET /api/users/0/tags                                 │  │   │
│  │  │  │                                                           │  │   │
│  │  │  └── Connector API (/connector/...)  → WRITE Operations      │  │   │
│  │  │      - POST /connector/saveItems                             │  │   │
│  │  │      - GET /connector/ping                                   │  │   │
│  │  └─────────────────────────────────────────────────────────────┘  │   │
│  │                              │                                     │   │
│  │                              ▼                                     │   │
│  │  ┌─────────────────────────────────────────────────────────────┐  │   │
│  │  │  SQLite Database (zotero.sqlite)                             │  │   │
│  │  └─────────────────────────────────────────────────────────────┘  │   │
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
│  • fetch_article_details   │    │  • import_from_pmids       │
│  • parse_pico              │    │  • add_reference           │
│  • merge_search_results    │    │  • list_collections        │
└────────────────────────────┘    └────────────────────────────┘
```

**Simple Workflow (v1.6.0+, Integrated Search):**
```
1. [zotero-keeper] search_pubmed_exclude_owned("CRISPR") → Only NEW papers
2. [zotero-keeper] import_from_pmids(pmids, tags=["CRISPR"]) → Zotero
```

**Advanced Workflow (Strategy Building):**
```
1. [pubmed-search] generate_search_queries("CRISPR") → MeSH terms
2. [zotero-keeper] search_pubmed_exclude_owned(query='"CRISPR-Cas"[MeSH]')
3. [zotero-keeper] import_from_pmids(pmids) → Zotero
```

| MCP Server | Responsibility | Key Tools |
|------------|----------------|-----------|
| **pubmed-search-mcp** | Strategy Building | generate_search_queries, parse_pico, merge_search_results, search_literature |
| **zotero-keeper** | Integrated Search & Import | search_pubmed_exclude_owned, import_from_pmids, smart_add_reference |
| **zotero-keeper** | Library Management | search_items, check_duplicate, list_collections |

---

## Layer Architecture

### DDD Onion Architecture

We follow Domain-Driven Design with an onion (clean) architecture:

```
          ┌─────────────────────────────────────┐
          │     Infrastructure Layer            │
          │   (FastMCP, HTTP Client, Adapters)  │
          │  ┌───────────────────────────────┐  │
          │  │    Application Layer          │  │
          │  │  (Use Cases, DTOs, Services)  │  │
          │  │  ┌─────────────────────────┐  │  │
          │  │  │    Domain Layer         │  │  │
          │  │  │  (Entities, Value Obj,  │  │  │
          │  │  │   Repository Interface) │  │  │
          │  │  └─────────────────────────┘  │  │
          │  └───────────────────────────────┘  │
          └─────────────────────────────────────┘
```

### Layer Responsibilities

| Layer | Responsibilities | Dependencies |
|-------|-----------------|--------------|
| **Domain** | Business entities, value objects, repository interfaces | None (pure Python) |
| **Application** | Use cases, DTOs, business logic orchestration | Domain |
| **Infrastructure** | MCP server, HTTP client, external integrations | Application, Domain |

---

## Component Details

### Domain Layer

#### Entities

```python
# src/zotero_mcp/domain/entities/item.py

@dataclass
class Item:
    """Zotero bibliographic item"""
    key: str
    item_type: ItemType
    title: str
    creators: list[Creator]
    date: Optional[str]
    abstract: Optional[str]
    doi: Optional[DOI]
    url: Optional[str]
    tags: list[Tag]
    collections: list[str]  # collection keys
    
@dataclass
class Creator:
    """Author, editor, or other contributor"""
    first_name: str
    last_name: str
    creator_type: CreatorType  # author, editor, translator, etc.

@dataclass
class Collection:
    """Zotero collection (folder)"""
    key: str
    name: str
    parent_key: Optional[str]

@dataclass
class Tag:
    """Item tag"""
    name: str
    type: int  # 0 = user, 1 = automatic
```

#### Value Objects

```python
# src/zotero_mcp/domain/value_objects.py

class ItemType(StrEnum):
    """Supported Zotero item types"""
    JOURNAL_ARTICLE = "journalArticle"
    BOOK = "book"
    BOOK_SECTION = "bookSection"
    CONFERENCE_PAPER = "conferencePaper"
    THESIS = "thesis"
    REPORT = "report"
    WEBPAGE = "webpage"
    # ... more types

@dataclass(frozen=True)
class DOI:
    """Digital Object Identifier value object"""
    value: str
    
    def __post_init__(self):
        if not self._is_valid():
            raise ValueError(f"Invalid DOI: {self.value}")
    
    def _is_valid(self) -> bool:
        return self.value.startswith("10.")
    
    @property
    def url(self) -> str:
        return f"https://doi.org/{self.value}"
```

#### Repository Interfaces

```python
# src/zotero_mcp/domain/repositories/item_repository.py

from abc import ABC, abstractmethod
from typing import Protocol

class ItemRepository(Protocol):
    """Interface for item persistence"""
    
    async def get_by_key(self, key: str) -> Optional[Item]: ...
    async def search(self, query: str, limit: int = 25) -> list[Item]: ...
    async def list_recent(self, limit: int = 50) -> list[Item]: ...
    async def save(self, item: Item) -> str: ...
    async def check_duplicate(self, title: str, doi: Optional[str]) -> Optional[Item]: ...
```

### Application Layer

#### Use Cases

```python
# src/zotero_mcp/application/use_cases/search_items.py

@dataclass
class SearchItemsRequest:
    query: str
    limit: int = 25
    item_type: Optional[str] = None

@dataclass
class SearchItemsResponse:
    items: list[ItemDTO]
    total: int
    query: str

class SearchItemsUseCase:
    def __init__(self, item_repository: ItemRepository):
        self._repo = item_repository
    
    async def execute(self, request: SearchItemsRequest) -> SearchItemsResponse:
        items = await self._repo.search(
            query=request.query,
            limit=request.limit
        )
        return SearchItemsResponse(
            items=[ItemDTO.from_entity(item) for item in items],
            total=len(items),
            query=request.query
        )
```

```python
# src/zotero_mcp/application/use_cases/add_reference.py

@dataclass
class AddReferenceRequest:
    item_type: str
    title: str
    creators: list[CreatorDTO]
    date: Optional[str] = None
    doi: Optional[str] = None
    url: Optional[str] = None
    abstract: Optional[str] = None
    tags: list[str] = field(default_factory=list)
    check_duplicate: bool = True

@dataclass
class AddReferenceResponse:
    success: bool
    item_key: Optional[str]
    is_duplicate: bool = False
    existing_key: Optional[str] = None
    message: str = ""

class AddReferenceUseCase:
    def __init__(self, item_repository: ItemRepository):
        self._repo = item_repository
    
    async def execute(self, request: AddReferenceRequest) -> AddReferenceResponse:
        # Check for duplicates
        if request.check_duplicate:
            existing = await self._repo.check_duplicate(
                title=request.title,
                doi=request.doi
            )
            if existing:
                return AddReferenceResponse(
                    success=False,
                    item_key=None,
                    is_duplicate=True,
                    existing_key=existing.key,
                    message=f"Duplicate found: {existing.title}"
                )
        
        # Create and save item
        item = Item(
            key="",  # Will be assigned by Zotero
            item_type=ItemType(request.item_type),
            title=request.title,
            creators=[c.to_entity() for c in request.creators],
            date=request.date,
            doi=DOI(request.doi) if request.doi else None,
            # ... more fields
        )
        
        item_key = await self._repo.save(item)
        
        return AddReferenceResponse(
            success=True,
            item_key=item_key,
            message=f"Item created successfully"
        )
```

### Infrastructure Layer

#### MCP Server

```python
# src/zotero_mcp/infrastructure/mcp/server.py

from mcp.server.fastmcp import FastMCP

from .config import ZoteroMcpConfig, default_config
from .handlers import ZoteroToolsHandler

class ZoteroKeeperServer:
    """MCP Server for Zotero integration"""
    
    def __init__(self, config: ZoteroMcpConfig = None):
        self._config = config or default_config
        
        self._mcp = FastMCP(
            name=self._config.name,
            version=self._config.version,
            instructions=self._config.instructions,
        )
        
        # Initialize components
        self._zotero_client = ZoteroClient(self._config.zotero)
        self._item_repo = ZoteroItemRepository(self._zotero_client)
        
        # Register handlers
        self._tools_handler = ZoteroToolsHandler(
            mcp=self._mcp,
            item_repo=self._item_repo,
        )
    
    def run(self, transport: str = "stdio"):
        """Run the MCP server"""
        self._mcp.run(transport=transport)
```

#### MCP Tools Handler

```python
# src/zotero_mcp/infrastructure/mcp/handlers/tools_handler.py

class ZoteroToolsHandler:
    """Registers and handles MCP tools"""
    
    def __init__(self, mcp: FastMCP, item_repo: ItemRepository):
        self._mcp = mcp
        self._item_repo = item_repo
        self._register_tools()
    
    def _register_tools(self):
        """Register all MCP tools"""
        
        @self._mcp.tool()
        async def search_items(
            query: str,
            limit: int = 25
        ) -> dict:
            """
            🔍 Search for bibliographic items in Zotero
            
            搜尋 Zotero 中的書目資料
            
            Args:
                query: Search terms (title, author, year)
                limit: Maximum results to return
                
            Returns:
                List of matching items with metadata
            """
            use_case = SearchItemsUseCase(self._item_repo)
            result = await use_case.execute(
                SearchItemsRequest(query=query, limit=limit)
            )
            return {
                "items": [item.to_dict() for item in result.items],
                "total": result.total,
                "query": result.query
            }
        
        @self._mcp.tool()
        async def add_reference(
            item_type: str,
            title: str,
            authors: list[dict] = None,
            date: str = None,
            doi: str = None,
            url: str = None,
            abstract: str = None,
            tags: list[str] = None,
            check_duplicate: bool = True
        ) -> dict:
            """
            ➕ Add a new bibliographic reference to Zotero
            
            新增書目參考文獻到 Zotero
            
            Args:
                item_type: Type of item (journalArticle, book, etc.)
                title: Item title
                authors: List of authors [{"firstName": "...", "lastName": "..."}]
                date: Publication date
                doi: Digital Object Identifier
                url: Web URL
                abstract: Abstract text
                tags: List of tags
                check_duplicate: Check for existing duplicates
                
            Returns:
                Result with item key or duplicate info
            """
            # ... implementation
```

#### Zotero HTTP Client

```python
# src/zotero_mcp/infrastructure/zotero_client/client.py

class ZoteroClient:
    """HTTP Client for Zotero APIs"""
    
    # READ operations via Local API
    async def get_items(self, limit: int = 50, q: str = None) -> list[dict]:
        return await self._request("GET", "/api/users/0/items", params={...})
    
    async def get_item(self, key: str) -> dict:
        return await self._request("GET", f"/api/users/0/items/{key}")
    
    async def get_collections(self) -> list[dict]:
        return await self._request("GET", "/api/users/0/collections")
    
    async def get_tags(self) -> list[dict]:
        return await self._request("GET", "/api/users/0/tags")
    
    # WRITE operations via Connector API
    async def save_items(self, items: list[dict]) -> dict:
        return await self._request("POST", "/connector/saveItems", json_data={
            "items": items,
            "uri": "http://zotero-keeper.local",
            "title": "Zotero Keeper Import"
        })
```

---

## API Reference

### Zotero Local API (READ)

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/users/0/items` | GET | List all items |
| `/api/users/0/items?q={query}` | GET | Search items |
| `/api/users/0/items/{key}` | GET | Get single item |
| `/api/users/0/items/{key}/children` | GET | Get item attachments/notes |
| `/api/users/0/collections` | GET | List collections |
| `/api/users/0/collections/{key}` | GET | Get single collection |
| `/api/users/0/collections/{key}/items` | GET | Get collection items |
| `/api/users/0/tags` | GET | List all tags |
| `/api/itemTypes` | GET | Get item type schema |
| `/api/itemTypeFields?itemType={type}` | GET | Get fields for item type |

### Zotero Connector API (WRITE)

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/connector/ping` | GET | Health check |
| `/connector/saveItems` | POST | Save items |

#### saveItems Payload

```json
{
  "items": [
    {
      "itemType": "journalArticle",
      "title": "Article Title",
      "creators": [
        {"firstName": "John", "lastName": "Doe", "creatorType": "author"}
      ],
      "date": "2024",
      "DOI": "10.1234/example",
      "publicationTitle": "Journal Name",
      "abstract": "Abstract text...",
      "tags": [
        {"tag": "machine learning"},
        {"tag": "ai"}
      ]
    }
  ],
  "uri": "http://source.url",
  "title": "Page Title"
}
```

---

## Data Flow

### Search Flow

```
User Query → MCP Tool → Use Case → Repository → HTTP Client → Zotero API
                                                                  ↓
User Response ← MCP Response ← DTO ← Entity ← JSON Parser ← API Response
```

### Add Reference Flow

```
Reference Data → MCP Tool → Use Case (validate, check duplicate)
                               ↓
                         [Duplicate?] ─Yes→ Return existing item
                               │No
                               ↓
                         Repository.save()
                               ↓
                         HTTP Client → Connector API → Zotero
                               ↓
                         Return new item key
```

---

## Design Decisions

### Why Built-in API over Custom Plugin?

| Factor | Custom Plugin | Built-in API |
|--------|---------------|--------------|
| **Maintenance** | Need to update with Zotero versions | Maintained by Zotero team |
| **Deployment** | Requires plugin installation | No installation needed |
| **Security** | Custom network binding needed | Uses existing Zotero server |
| **Features** | Can add custom endpoints | Limited to existing API |

**Decision**: Use built-in API for simplicity and maintainability. Only READ is supported natively, but Connector API covers WRITE needs.

### Why DDD Architecture?

1. **Testability**: Domain logic can be tested without infrastructure
2. **Maintainability**: Clear separation of concerns
3. **Flexibility**: Easy to swap infrastructure (e.g., different HTTP client)
4. **Scalability**: Can add features without affecting existing code

### Why FastMCP?

- Native Python SDK for MCP
- Simple decorator-based API
- Built-in stdio/sse transport support
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
│  MCP Server  │────────────▶│  Port Proxy  │────────────▶│   Zotero     │
│  (Linux VM)  │ HTTP:23119│  (Windows)   │ localhost │  (Windows)   │
│  <MCP_HOST>  │           │    netsh     │  :23119   │ 127.0.0.1    │
└──────────────┘           └──────────────┘           └──────────────┘
                          (0.0.0.0:23119)
```

**Note**: Host header `127.0.0.1:23119` required for port proxy to route correctly.

---

## Security Considerations

1. **No Authentication**: Zotero Local API has no authentication
   - Only expose on trusted networks
   - Use firewall rules to restrict access

2. **Data Validation**: All input validated before sending to Zotero
   - DOI format validation
   - Required field checks
   - Item type validation

3. **No Sensitive Data Stored**: MCP server is stateless
   - No credentials stored
   - No session data

---

## Future Architecture Considerations

1. **Multi-Library Support**: Support for group libraries
2. **Caching Layer**: Redis/memory cache for frequently accessed data
3. **Event Sourcing**: Track all changes for audit/undo
4. **WebSocket**: Real-time updates when Zotero changes
