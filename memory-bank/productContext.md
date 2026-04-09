# Product Context

> 🏗️ 技術架構和實作細節

## 技術棧

### Python MCP Servers
- **Runtime**: Python 3.12+
- **Package Manager**: uv only
- **Framework**: FastMCP
- **Libraries**:
  - biopython (NCBI Entrez)
  - httpx (async HTTP)
  - pyzotero-local (Zotero API)
  - structlog (structured MCP tool logging)

### VS Code Extension
- **Runtime**: Node.js 18+
- **Framework**: VS Code Extension API
- **Language**: TypeScript

## 架構

Current collaboration-safe split:

```
┌─────────────────────────────────────────────────────────┐
│                    VS Code Extension                      │
│                  (vscode-zotero-mcp)                     │
├─────────────────────────────────────────────────────────┤
│                   MCP Protocol Layer                      │
├──────────────────────┬──────────────────────────────────┤
│  pubmed-search-mcp   │       zotero-keeper              │
│ (search/discovery)   │ (local library + import)         │
├──────────────────────┼──────────────────────────────────┤
│   NCBI Entrez API    │     Zotero Desktop App           │
└──────────────────────┴──────────────────────────────────┘
```

## 主要功能模組

### pubmed-search-mcp
- `unified_search`: 單一公開搜尋入口
- `generate_search_queries`: MeSH 擴展搜尋策略
- `parse_pico`: PICO 臨床問題解析
- `fetch_article_details`: 文章詳情與進一步探索
- `get_citation_metrics`: iCite 引用指標
- `get_session_pmids`: Session PMID 持久化

### zotero-keeper
- `search_items` / `advanced_search`: 搜尋本地 Zotero 文獻
- `list_collections`: 列出收藏夾
- `check_articles_owned`: 本地 PMID / DOI 重複檢查
- `import_articles`: collaboration-safe PubMed -> Zotero handoff
- `interactive_save` / `quick_save`: 手動存檔與 metadata fetch

## 資料流

1. User → VS Code Copilot / Claude
2. pubmed-search-mcp `unified_search(..., output_format="json")`
3. zotero-keeper `check_articles_owned(...)` → `import_articles(...)`
4. Results → Session Cache / Zotero → User

---
*Updated: 2026-04-09*
