# Roadmap

Development roadmap for Zotero Keeper - MCP Server for Zotero integration.

---

## 📊 Overview

| Phase | Status | Target | Description |
|-------|--------|--------|-------------|
| Phase 1 | ✅ Complete | v1.1.0 | Foundation & Discovery |
| Phase 2 | ✅ Complete | v1.2.0 | Core MCP Tools |
| Phase 2.5 | ✅ Complete | v1.4.0 | Dual MCP Architecture |
| Phase 3 | ✅ Complete | v1.5.0 | Smart Features |
| Phase 4 | 📋 Planned | v1.6.0 | Multi-User & Config |
| Phase 5 | 📋 Planned | v2.0.0 | Advanced Features |

---

## ✅ Phase 1: Foundation & Discovery (Complete)

**Target Version**: v1.1.0  
**Status**: ✅ Complete  
**Period**: Dec 2024

### Goals
- [x] Project setup and structure
- [x] Network connectivity research
- [x] Zotero API discovery
- [x] Proof of concept

### Deliverables

| Task | Status | Notes |
|------|--------|-------|
| DDD project structure | ✅ | Python 3.11 + FastMCP |
| Network setup documentation | ✅ | Port proxy, firewall rules |
| Local API discovery | ✅ | `/api/users/0/...` endpoints |
| Connector API discovery | ✅ | `/connector/saveItems` for write |
| ZoteroClient implementation | ✅ | Async HTTP client with httpx |
| Connection test script | ✅ | `test_client.py` |

### Key Findings
- Zotero 7 has comprehensive built-in Local API
- Local API is READ-only
- Connector API supports WRITE via `saveItems`
- Port proxy required for remote access (Zotero binds 127.0.0.1)

---

## ✅ Phase 2: Core MCP Tools (Complete)

**Target Version**: v1.2.0  
**Status**: ✅ Complete  
**Completed**: Dec 2024

### Goals
- [x] Implement all read tools
- [x] Implement write tools
- [x] MCP server integration
- [x] Basic error handling

### MCP Tools Implementation

#### Read Tools (Using Local API)

| Tool | Priority | Status | Description |
|------|----------|--------|-------------|
| `check_connection` | P0 | ✅ | Test Zotero connectivity |
| `search_items` | P0 | ✅ | Search by title/author/year |
| `get_item` | P0 | ✅ | Get item by key |
| `list_items` | P1 | ✅ | List recent items |
| `list_collections` | P1 | ✅ | List all collections |
| `list_tags` | P2 | ✅ | List all tags |
| `get_item_types` | P2 | ✅ | Get available item types |
| `export_citation` | P2 | 📋 | Export in BibTeX/RIS format (Phase 3) |

#### Write Tools (Using Connector API)

| Tool | Priority | Status | Description |
|------|----------|--------|-------------|
| `add_reference` | P0 | ✅ | Add new bibliographic item |
| `create_item` | P1 | ✅ | Create with full metadata |

### Technical Tasks

| Task | Status | Notes |
|------|--------|-------|
| Domain entities (Reference, Collection, Creator) | ✅ | Pydantic dataclasses |
| ZoteroClient | ✅ | HTTP client with dual API support |
| MCP server setup | ✅ | FastMCP integration |
| Tools registration | ✅ | 9 tools via @mcp.tool() decorator |
| Error handling | ✅ | Try-catch with user-friendly messages |
| Logging | ✅ | Print-based logging |

### Acceptance Criteria
- [x] All P0 tools working
- [x] Can search and retrieve items from Zotero
- [x] Can add new references to Zotero
- [ ] Works with VS Code Copilot (pending integration test)

---

## ✅ Phase 2.5: Dual MCP Architecture (Complete)

**Target Version**: v1.4.0  
**Status**: ✅ Complete  
**Completed**: Dec 2024

### Architecture Decision
- **pubmed-search-mcp**: Independent MCP for PubMed search, export, PICO
- **zotero-keeper**: Focused on Zotero integration with import tools
- Agent combines both MCPs for full workflow

### Goals
- [x] Separate concerns: search vs import
- [x] Add pubmed-search-mcp as git submodule
- [x] Create import-only tools for Zotero
- [x] Fix API consistency (fetch_details in pubmed-search-mcp v0.1.9)

### New MCP Tools (zotero-keeper)

| Tool | Description |
|------|-------------|
| `import_ris_to_zotero` | 📥 匯入 RIS 格式到 Zotero |
| `import_from_pmids` | 📥 直接透過 PMID 匯入 |

### Installation

```bash
# Option 1: Both MCPs (recommended)
pip install pubmed-search-mcp zotero-keeper

# Option 2: zotero-keeper with built-in PubMed
pip install "zotero-keeper[pubmed]"
```

### Dual MCP Workflow

```
┌─────────────────────┐    ┌─────────────────────┐
│  pubmed-search-mcp  │    │   zotero-keeper     │
│  (搜尋 + 匯出)       │    │  (匯入 + 管理)       │
│                     │    │                     │
│  search_literature  │    │  import_from_pmids  │
│  prepare_export     │    │  import_ris_to_zotero│
│  fetch_details      │    │  search_items       │
│  parse_pico         │    │  add_reference      │
└─────────────────────┘    └─────────────────────┘
          │                          │
          └──────────┬───────────────┘
                     ▼
              Agent 自由組合
```

### Example Workflow

```
User: 「幫我找 CRISPR 相關論文並加入 Zotero」

Agent:
1. pubmed: search_literature("CRISPR", limit=10) → PMIDs
2. pubmed: prepare_export(pmids, format="ris") → RIS text
3. keeper: import_ris_to_zotero(ris_text, tags=["CRISPR"])

Or directly:
1. pubmed: search_literature("CRISPR", limit=10) → PMIDs  
2. keeper: import_from_pmids(pmids, tags=["CRISPR"])
```

---

## ✅ Phase 3: Smart Features (Complete)

**Target Version**: v1.5.0  
**Status**: ✅ Complete  
**Completed**: Dec 2024

### Design Philosophy

> **MCP Server 內部功能**：所有智慧功能都在 MCP Server 內部實現。
> Agent 只需調用 MCP 工具並等待結果，不需要自行處理邏輯。

### Goals
- [x] Duplicate detection (using rapidfuzz)
- [x] Reference validation (MCP internal)
- [x] Smart add with auto-check
- [ ] Better error messages (future)
- [ ] Search improvements (future)

### Dependencies Added
- `rapidfuzz>=3.0.0` - Fuzzy string matching for duplicate detection

### New MCP Tools

| Tool | Status | Description |
|------|--------|-------------|
| `check_duplicate` | ✅ | 檢查重複：模糊標題比對 + 精確 DOI/ISBN/PMID 比對 |
| `validate_reference` | ✅ | 驗證欄位：檢查必填欄位，回傳驗證結果及錯誤訊息 |
| `smart_add_reference` | ✅ | 智慧新增：自動檢查重複 + 驗證後新增，回傳完整結果 |

### Technical Implementation

- **Fuzzy Matching**: Uses `rapidfuzz.fuzz.token_sort_ratio` with 85% threshold
- **Exact Matching**: DOI, ISBN, PMID identifiers
- **Validation**: Type-specific required fields
- **Confidence Levels**: high (exact/95%+), medium (90-95%), low (<90%)
| `_normalize_doi()` | DOI 格式正規化 |
| `_normalize_isbn()` | ISBN-10/13 正規化 |
| `_validate_fields()` | 欄位驗證邏輯 |
| `_find_similar_items()` | 搜尋相似項目 |

### Technical Tasks

| Task | Description |
|------|-------------|
| Add `rapidfuzz` dependency | 高效模糊字串比對 |
| Duplicate detection service | 內部服務類別 |
| Validation service | 欄位驗證服務 |
| Error response schema | 統一錯誤回應格式 |

### Example: `smart_add_reference` Response

```json
{
  "success": true,
  "action": "created",
  "item_key": "ABC12345",
  "checks": {
    "duplicate": {"passed": true, "similar_items": []},
    "validation": {"passed": true, "errors": []}
  }
}
```

```json
{
  "success": false,
  "action": "rejected",
  "reason": "duplicate_found",
  "checks": {
    "duplicate": {
      "passed": false,
      "similar_items": [
        {"key": "XYZ789", "title": "...", "similarity": 0.95}
      ]
    }
  }
}
```

---

## 📋 Phase 4: Multi-User & Configuration

**Target Version**: v1.4.0  
**Status**: 📋 Planned  
**Target Date**: Feb 2025

### Goals
- [ ] Environment variable configuration
- [ ] Multiple Zotero instances
- [ ] Connection profiles
- [ ] Health monitoring

### Features

| Feature | Description |
|---------|-------------|
| Config via env vars | ZOTERO_HOST, ZOTERO_PORT |
| Named profiles | Switch between different Zotero instances |
| Connection status tool | Check Zotero connectivity |
| Auto-reconnect | Handle temporary disconnections |

### Configuration Schema

```python
# Environment variables
ZOTERO_HOST=YOUR_ZOTERO_HOST
ZOTERO_PORT=23119
ZOTERO_TIMEOUT=30

# Or profile-based
ZOTERO_PROFILES=~/.zotero-keeper/profiles.yaml
ZOTERO_ACTIVE_PROFILE=work
```

---

## 📋 Phase 5: Advanced Features

**Target Version**: v2.0.0  
**Status**: 📋 Planned  
**Target Date**: Q2 2025

### Goals
- [ ] Metadata enrichment
- [ ] Collection management
- [ ] Full-text search
- [ ] Export/import

### Features

| Feature | Description |
|---------|-------------|
| DOI lookup | Auto-fill metadata from DOI (CrossRef API) |
| ISBN lookup | Auto-fill book metadata (OpenLibrary API) |
| arXiv integration | Fetch preprint metadata |
| Collection tools | Create/manage collections |
| Tag management | Add/remove/bulk update tags |
| Full-text search | Search in PDFs (if available) |
| BibTeX import | Import from .bib files |

### External Integrations

| Service | Purpose |
|---------|---------|
| CrossRef API | DOI metadata resolution |
| OpenLibrary API | ISBN metadata resolution |
| Semantic Scholar | Paper metadata & citations |
| arXiv API | Preprint metadata |

---

## 📈 Metrics & Success Criteria

### Phase 2 Success
- [x] 100% of P0 tools implemented (9 tools)
- [x] < 500ms response time for search
- [x] Zero data loss in write operations
- [ ] Works in VS Code Copilot Chat (pending)

### Phase 3 Success
- [ ] 95% duplicate detection accuracy
- [ ] < 1% false positive duplicates
- [ ] Clear validation error messages

### Overall Project Success
- [ ] Used by 10+ users
- [ ] < 5 critical bugs
- [ ] Positive community feedback

---

## 🔗 Dependencies

### External Dependencies
- Zotero 7.0+ with Local API enabled
- Python 3.11+
- Network access to Zotero instance

### Development Dependencies
- FastMCP SDK
- httpx
- pytest
- ruff / mypy

---

## 📝 Notes

### Limitations (Known)
1. Local API is READ-only (by Zotero design)
2. Connector API format differs from Web API
3. No real-time sync notification from Zotero
4. Port proxy needed for remote access

### Future Considerations
1. WebSocket support when Zotero adds it
2. Group library support
3. Attachment handling (PDFs)
4. Citation style formatting

---

## 📅 Release Schedule

| Version | Date | Milestone |
|---------|------|-----------|
| v1.1.0 | Dec 2024 | Foundation complete |
| v1.2.0 | Dec 2024 | Core tools working |
| v1.3.0 | Jan 2025 | Smart features |
| v1.4.0 | Feb 2025 | Multi-user ready |
| v2.0.0 | Q2 2025 | Full-featured release |

---

*Last updated: December 12, 2024*
