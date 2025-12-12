# System Patterns

## Architecture Pattern

### DDD Onion Architecture

```
┌───────────────────────────────────────┐
│     Infrastructure (FastMCP, HTTP)    │
│  ┌─────────────────────────────────┐  │
│  │   Application (Use Cases)       │  │
│  │  ┌───────────────────────────┐  │  │
│  │  │   Domain (Entities, VOs)  │  │  │
│  │  └───────────────────────────┘  │  │
│  └─────────────────────────────────┘  │
└───────────────────────────────────────┘
```

**Dependency Rule**: Inner layers have no knowledge of outer layers.

## Code Patterns

### Repository Pattern

```python
# Domain defines interface
class ItemRepository(Protocol):
    async def get_by_key(self, key: str) -> Optional[Item]: ...
    async def save(self, item: Item) -> str: ...

# Infrastructure implements
class ZoteroItemRepository:
    def __init__(self, client: ZoteroClient):
        self._client = client
    
    async def get_by_key(self, key: str) -> Optional[Item]:
        data = await self._client.get_item(key)
        return Item.from_dict(data) if data else None
```

### Use Case Pattern

```python
@dataclass
class SearchItemsRequest:
    query: str
    limit: int = 25

@dataclass
class SearchItemsResponse:
    items: list[ItemDTO]
    total: int

class SearchItemsUseCase:
    def __init__(self, repo: ItemRepository):
        self._repo = repo
    
    async def execute(self, request: SearchItemsRequest) -> SearchItemsResponse:
        items = await self._repo.search(request.query, request.limit)
        return SearchItemsResponse(items=items, total=len(items))
```

### MCP Tool Pattern

```python
@mcp.tool()
async def search_items(query: str, limit: int = 25) -> dict:
    """Search for bibliographic items"""
    use_case = SearchItemsUseCase(item_repository)
    result = await use_case.execute(SearchItemsRequest(query=query, limit=limit))
    return {"items": [i.to_dict() for i in result.items], "total": result.total}
```

## API Patterns

### Dual API Strategy

```
READ:  GET /api/users/0/items     → Local API (Zotero built-in)
WRITE: POST /connector/saveItems  → Connector API (Browser extension API)
```

### Host Header Pattern

Required for port proxy to work:

```python
headers = {
    "Host": "127.0.0.1:23119",  # Override for port proxy
    "Content-Type": "application/json"
}
```

## Error Handling Pattern

```python
class ZoteroConnectionError(Exception):
    """Network or connection issues"""

class ZoteroAPIError(Exception):
    """API returned error response"""
    def __init__(self, message: str, status_code: int, response_text: str):
        super().__init__(message)
        self.status_code = status_code
        self.response_text = response_text
```

## Testing Patterns

### Unit Tests (Domain)
- Test entities and value objects
- No external dependencies

### Integration Tests (Application)
- Test use cases
- Mock repository

### E2E Tests (Infrastructure)
- Test actual Zotero connection
- Requires running Zotero instance

## Configuration Pattern

```python
@dataclass
class ZoteroConfig:
    host: str = field(default_factory=lambda: os.getenv("ZOTERO_HOST", "localhost"))
    port: int = field(default_factory=lambda: int(os.getenv("ZOTERO_PORT", "23119")))
    timeout: float = 30.0
```
