# Active Context

## Current Focus

**Phase 3 Planning**: Smart features - duplicate detection, validation, batch operations.

## Recent Changes

### 2024-12-12

1. **Phase 2 Complete**: Core MCP Tools v1.2.0
   - Implemented 9 MCP tools via FastMCP:
     - `check_connection` - 測試連線
     - `search_items` - 搜尋文獻
     - `get_item` - 取得單一項目
     - `list_items` - 列出項目
     - `list_collections` - 列出收藏夾
     - `list_tags` - 列出標籤
     - `get_item_types` - 取得項目類型
     - `add_reference` - 新增參考文獻
     - `create_item` - 建立項目
   - All tools tested successfully

2. **Project Cleanup**:
   - Removed legacy application/use_cases layer
   - Removed unused domain/repositories
   - Removed duplicate README and test files
   - Clean structure: domain/entities + infrastructure/mcp + infrastructure/zotero_client

### 2024-12-11

1. **Major Discovery**: Zotero 7 built-in Local API (port 23119)
2. **API Strategy**: READ via Local API, WRITE via Connector API
3. **Network Setup**: Windows netsh port proxy + firewall
4. **Documentation**: README, CHANGELOG, ARCHITECTURE, ROADMAP

## Working Environment

- **MCP Server Location**: Linux VM (`YOUR_MCP_HOST` / `YOUR_ZOTERO_HOST04`)
- **Zotero Client Location**: Windows (`YOUR_ZOTERO_HOST`)
- **Zotero Port**: 23119
- **Python Version**: 3.11+

## Key Files

| File | Purpose |
|------|---------|
| `mcp-server/src/zotero_mcp/infrastructure/mcp/server.py` | MCP Server with 9 tools |
| `mcp-server/src/zotero_mcp/infrastructure/zotero_client/client.py` | HTTP client for Zotero APIs |
| `mcp-server/test_mcp_tools.py` | MCP tools test script |
| `mcp-server/pyproject.toml` | Project configuration (zotero-keeper v1.2.0) |

## Next Steps

1. Design duplicate detection algorithm
2. Add ISBN/DOI validation
3. Implement batch operations
4. PDF attachment handling
5. Multi-user support architecture

## Open Questions

1. Should we support batch operations?
2. How to handle PDF attachments?
3. Cache strategy for frequent queries?

## Blockers

None currently.
