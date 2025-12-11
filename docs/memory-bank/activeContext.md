# Active Context

## Current Focus

**Phase 2**: Implementing core MCP tools for read and write operations.

## Recent Changes

### 2024-12-11

1. **Major Discovery**: Zotero 7 has built-in Local API
   - Eliminated need for custom plugin
   - Simplified architecture significantly
   
2. **API Strategy**:
   - READ: Use Local API (`/api/users/0/...`)
   - WRITE: Use Connector API (`/connector/saveItems`)

3. **Network Setup**:
   - Windows port proxy via `netsh interface portproxy`
   - Host header required: `Host: 127.0.0.1:23119`
   - Firewall rule for port 23119

4. **Documentation**:
   - Created comprehensive README.md
   - Created CHANGELOG.md with version history
   - Created ARCHITECTURE.md with DDD design
   - Created ROADMAP.md with 5 phases

## Working Environment

- **MCP Server Location**: Linux VM (`YOUR_MCP_HOST` / `YOUR_ZOTERO_HOST04`)
- **Zotero Client Location**: Windows (`YOUR_ZOTERO_HOST`)
- **Zotero Port**: 23119
- **Python Version**: 3.11+

## Key Files

| File | Purpose |
|------|---------|
| `mcp-server/src/zotero_mcp/infrastructure/zotero_client/client.py` | HTTP client for Zotero APIs |
| `mcp-server/test_client.py` | Connection test script |
| `mcp-server/pyproject.toml` | Project configuration |

## Next Steps

1. Create domain entities (Item, Collection, Creator)
2. Define repository interfaces
3. Implement ZoteroItemRepository
4. Setup FastMCP server
5. Register MCP tools

## Open Questions

1. Should we support batch operations?
2. How to handle PDF attachments?
3. Cache strategy for frequent queries?

## Blockers

None currently.
