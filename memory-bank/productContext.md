# Product Context

> 🏗️ 技術架構和實作細節

## 技術棧

### Python MCP Servers
- **Runtime**: Python 3.11+
- **Package Manager**: uv (recommended), pip
- **Framework**: FastMCP
- **Libraries**:
  - biopython (NCBI Entrez)
  - httpx (async HTTP)
  - pyzotero-local (Zotero API)

### VS Code Extension
- **Runtime**: Node.js 18+
- **Framework**: VS Code Extension API
- **Language**: TypeScript

## 架構

```
┌─────────────────────────────────────────────────────────┐
│                    VS Code Extension                      │
│                  (vscode-zotero-mcp)                     │
├─────────────────────────────────────────────────────────┤
│                   MCP Protocol Layer                      │
├──────────────────────┬──────────────────────────────────┤
│  pubmed-search-mcp   │       zotero-keeper              │
│  (PubMed Search)     │    (Zotero Local API)            │
├──────────────────────┼──────────────────────────────────┤
│   NCBI Entrez API    │     Zotero Desktop App           │
└──────────────────────┴──────────────────────────────────┘
```

## 主要功能模組

### pubmed-search-mcp
- `search_literature`: 基本 PubMed 搜尋
- `generate_search_queries`: MeSH 擴展搜尋策略
- `parse_pico`: PICO 臨床問題解析
- `get_citation_metrics`: iCite 引用指標
- `get_session_pmids`: Session PMID 持久化

### zotero-keeper
- `search_items`: 搜尋 Zotero 文獻
- `smart_add_reference`: 智慧新增（含重複檢查）
- `list_collections`: 列出收藏夾

## 資料流

1. User → VS Code Copilot → MCP Server
2. MCP Server → External API (PubMed/Zotero)
3. Results → Session Cache → User

---
*Updated: 2025-12-16*
