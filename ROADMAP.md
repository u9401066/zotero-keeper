# Roadmap

Development roadmap for Zotero Keeper - A MCP server for local Zotero library management.

---

## Legend

- ✅ Completed
- 🔄 In Progress
- 📋 Planned
- 💡 Future Consideration

---

## Phase 1: Foundation ✅

### v1.0.0 - v1.1.0 (December 2024)

- ✅ Project structure (DDD architecture)
- ✅ FastMCP framework integration
- ✅ Zotero Local API client
- ✅ Basic connectivity (`check_connection`)
- ✅ Configuration management

---

## Phase 2: Core Functionality ✅

### v1.2.0 - v1.4.0 (December 2024)

- ✅ **Item Operations**
  - ✅ `add_reference` - Add new reference
  - ✅ `create_item` - Create with full metadata
  - ✅ `search_items` - Full-text search
  - ✅ `list_items` - Recent items
  - ✅ `get_item` - Get by key

- ✅ **Collection Operations**
  - ✅ `list_collections` - List all
  - ✅ `get_collection` - Get details
  - ✅ `get_collection_items` - Items in collection
  - ✅ `get_collection_tree` - Hierarchical view
  - ✅ `find_collection` - Search by name

- ✅ **Metadata**
  - ✅ `list_tags` - All tags
  - ✅ `get_item_types` - Available types

---

## Phase 3: Advanced Features ✅

### v1.5.0 - v1.6.0 (December 2024)

- ✅ **Dual API Architecture**
  - ✅ Local API for READ operations
  - ✅ Connector API for WRITE operations
  - ✅ Unified HTTP client

- ✅ **PubMed Integration**
  - ✅ `search_pubmed_exclude_owned` - Exclude owned items
  - ✅ `check_articles_owned` - Check ownership
  - ✅ `batch_import_from_pubmed` - Batch import

- ✅ **Saved Search Support** (Local API Exclusive!)
  - ✅ `list_saved_searches` - List searches
  - ✅ `run_saved_search` - Execute search
  - ✅ `get_saved_search_details` - Search conditions

- ✅ **Import Capabilities**
  - ✅ `import_ris_to_zotero` - RIS format
  - ✅ `import_from_pmids` - From PMIDs

### v1.7.0 (December 2024)

- ✅ **Tool Simplification** (21 tools, down from 27)
  - ✅ Consolidated smart tools into save tools
  - ✅ `smart_tools.py` now helpers only

- ✅ **MCP Resources** (10 URIs)
  - ✅ `zotero://collections` (+ tree, key, items)
  - ✅ `zotero://items` (+ key)
  - ✅ `zotero://tags`
  - ✅ `zotero://searches` (+ key)
  - ✅ `zotero://schema/item-types`

- ✅ **MCP Elicitation**
  - ✅ Interactive collection selection
  - ✅ Numbered options for user choice

- ✅ **Auto-fetch Metadata**
  - ✅ DOI → CrossRef API
  - ✅ PMID → PubMed E-utilities
  - ✅ Intelligent merge (user priority)

### v1.8.0 (December 2024) - Current

- ✅ **Collection 防呆機制**
  - ✅ `collection_name` parameter (auto-validates!)
  - ✅ Returns available collections if not found
  - ✅ `collection_info` confirms destination
  - ✅ Warns against raw `collection_key` usage

- ✅ **Citation Metrics Support**
  - ✅ `include_citation_metrics` parameter
  - ✅ iCite API integration (RCR, Percentile)
  - ✅ Metrics stored in Zotero `extra` field

- ✅ **Documentation**
  - ✅ `docs/ZOTERO_LOCAL_API.md` created
  - ✅ API reference and limitations documented

---

## Phase 4: Enhanced User Experience 📋

### v1.9.0 (Planned)

- 📋 **Note & Annotation Support**
  - 📋 Read item notes
  - 📋 Create/update notes
  - 📋 Read PDF annotations (if possible)

- 📋 **Attachment Management**
  - 📋 List item attachments
  - 📋 Get attachment metadata
  - 📋 Attachment search

- 📋 **Better Error Handling**
  - 📋 Detailed error messages
  - 📋 Retry logic for transient failures
  - 📋 Connection recovery

### v2.0.0 (Planned)

- 📋 **Caching Layer**
  - 📋 Cache frequently accessed collections
  - 📋 TTL-based invalidation
  - 📋 Memory-efficient storage

- 📋 **Better Duplicate Detection**
  - 📋 Fuzzy title matching improvements
  - 📋 Author name normalization
  - 📋 ISBN validation

---

## Phase 5: Write Operations via Plugin Integration 🔄

> ⚠️ **Zotero Local API 限制**: DELETE/PATCH/PUT 回傳 501 Not Implemented
> 
> 解決方案：整合 Zotero 外掛，透過外掛的內部 API 實現寫入操作

### v2.0.0 - Plugin Bridge (Planned)

- 📋 **Actions & Tags 整合** ⭐ 推薦
  - 📋 研究 Actions & Tags 的 customScript API
  - 📋 設計 MCP → Plugin 的通訊機制
  - 📋 實作常用操作腳本模板
  - 📋 文檔化腳本安裝步驟

- 📋 **可能的寫入操作** (需 Plugin)
  - 📋 `delete_items` - 刪除文獻 (`item.eraseTx()`)
  - 📋 `move_to_collection` - 移動文獻 (`item.addToCollection()`)
  - 📋 `remove_from_collection` - 從 Collection 移除
  - 📋 `update_item_field` - 更新欄位 (`item.setField()`)
  - 📋 `batch_add_tags` - 批次加標籤
  - 📋 `batch_remove_tags` - 批次移除標籤

- 📋 **實作方式探索**
  - 💡 方案 A: MCP 輸出腳本 → 使用者貼到 Actions & Tags
  - 💡 方案 B: 透過 Zotero 的 `Run JavaScript` 功能
  - 💡 方案 C: 等待 Zotero 官方開放 Local API 寫入

### 相關外掛資源

| 外掛 | Stars | 功能 | 連結 |
|------|-------|------|------|
| **Actions & Tags** | 2.5k | 自訂腳本、事件觸發 | [GitHub](https://github.com/windingwind/zotero-actions-tags) |
| **Zutilo** | 1.7k | 批次操作、快捷鍵 | [GitHub](https://github.com/wshanks/Zutilo) |
| **Better BibTeX** | - | 引用鍵管理 | [GitHub](https://github.com/retorquere/zotero-better-bibtex) |

### 常用腳本範例 (Actions & Tags)

```javascript
// 刪除選中文獻
if (items?.length > 0) {
    for (const item of items) {
        await item.eraseTx();
    }
}

// 移動到指定 Collection
const targetKey = "MHT7CZ8U";
if (items?.length > 0) {
    for (const item of items) {
        item.addToCollection(targetKey);
        await item.saveTx();
    }
}
```

---

## Phase 6: Multi-Library & Collaboration 💡

### v2.x.0 (Future Consideration)

- 💡 **Group Library Support**
  - 💡 List available libraries
  - 💡 Switch library context
  - 💡 Permission-aware operations

- 💡 **Sync Status**
  - 💡 Check sync status
  - 💡 Show sync conflicts
  - 💡 Trigger sync (if possible)

- 💡 **Collection Management** (等待 Zotero API 支援)
  - 💡 Create collections
  - 💡 Move items between collections
  - 💡 Rename collections

---

## Phase 7: Advanced Integration 💡

### Future Releases

- 💡 **Citation Export**
  - 💡 Generate citations in multiple styles
  - 💡 Integration with document editors

- 💡 **AI-Powered Features**
  - 💡 Automatic tagging based on content
  - 💡 Smart collection assignment
  - 💡 Related paper suggestions

- 💡 **Real-time Updates**
  - 💡 WebSocket support (if Zotero supports)
  - 💡 Push notifications for library changes

- 💡 **等待 Zotero 官方支援**
  - 💡 Local API Write Support ([Issue #1320](https://github.com/zotero/zotero/issues/1320))
  - 💡 當支援後，直接實作原生寫入操作

---

## Tool Count Evolution

| Version | Total Tools | Notes |
|---------|-------------|-------|
| v1.1.0  | 1 | `check_connection` only |
| v1.2.0  | 5 | + CRUD basics |
| v1.3.0  | 8 | + Search |
| v1.4.0  | 13 | + Collections |
| v1.5.0  | 19 | + Smart tools |
| v1.6.0  | 27 | + PubMed + Saved Search |
| v1.7.0 | 21 | Simplification |
| **v1.8.0** | **21** | **Collection 防呆 + RCR (current)** |
| v1.9.0  | ~24 | + Notes + Attachments |

---

## MCP Features Evolution

| Feature | Version | Status |
|---------|---------|--------|
| Tools | v1.1.0 | ✅ |
| Resources | v1.7.0 | ✅ |
| Elicitation | v1.7.0 | ✅ |
| Prompts | - | 💡 Future |
| Sampling | - | 💡 Future |

---

## Contributing

Have ideas for new features? Open an issue on GitHub!

Priority considerations:
1. Does it improve the literature management workflow?
2. Is it possible with Zotero's Local/Connector API?
3. Does it reduce complexity (not add more tools)?

---

*Last updated: December 14, 2024*
