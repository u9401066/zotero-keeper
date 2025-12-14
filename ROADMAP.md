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

## Phase 5: Multi-Library & Collaboration 💡

### v2.0.0 (Future Consideration)

- 💡 **Group Library Support**
  - 💡 List available libraries
  - 💡 Switch library context
  - 💡 Permission-aware operations

- 💡 **Sync Status**
  - 💡 Check sync status
  - 💡 Show sync conflicts
  - 💡 Trigger sync (if possible)

- 💡 **Collection Management**
  - 💡 Create collections
  - 💡 Move items between collections
  - 💡 Rename collections

---

## Phase 6: Advanced Integration 💡

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
