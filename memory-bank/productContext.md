# Product Context

> 🏗️ 技術架構和實作細節

## 技術棧

### Python MCP Servers
- **Runtime**: Python 3.12+
- **Package Manager**: uv only
- **Framework**: MCP Python SDK v2 `MCPServer` (`mcp>=2,<3`)
- **Release set**: Zotero Keeper `2.0.0` + PubMed Search MCP `0.6.1`
- **Libraries**:
  - biopython (NCBI Entrez)
  - httpx (async HTTP)
  - pydantic / pydantic-settings (configuration and contracts)
  - structlog (structured MCP tool logging)

### VS Code Extension
- **Runtime**: Node.js 18+
- **Framework**: VS Code Extension API
- **Language**: TypeScript
- **Release**: `0.6.0` / `v0.6.0-ext`

## 架構

Current collaboration-safe split:

```
┌─────────────────────────────────────────────────────────┐
│                    VS Code Extension                      │
│                  (vscode-zotero-mcp)                     │
├─────────────────────────────────────────────────────────┤
│                   MCP Protocol Layer                      │
├──────────────────────┬──────────────────────────────────┤
│ pubmed-search 0.6.1  │      keeper 2.0.0                │
│ (45 research tools)  │ (24 tools + 6 resources)         │
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
- `get_session_pmids` / `get_cached_article` / `get_session_summary`: Session
  PMID 與文章狀態持久化
- `build_research_chronicle` / `read_research_chronicle`: 可稽核的研究演進紀錄
- full-text、citation tree、multi-source、pipeline/export 與 reference
  verification 工具由同一 45-tool registry 提供

### zotero-keeper
- MCP SDK v2 server surface：24 tools + 6 resources
- `search_items` / `advanced_search`: 搜尋本地 Zotero 文獻
- `list_collections`: 列出收藏夾
- `check_articles_owned`: 本地 PMID / DOI 重複檢查
- `import_articles`: collaboration-safe PubMed -> Zotero handoff
- `import_pdf`: metadata 或 Zotero auto-recognize PDF 匯入
- `interactive_save` / `quick_save`: 手動存檔與 metadata fetch

## 資料流

1. User → VS Code Copilot / Claude
2. pubmed-search-mcp `unified_search(..., output_format="json")`
3. zotero-keeper `check_articles_owned(...)` → `import_articles(...)`
4. Results → Session Cache / Zotero → User

## 安裝與相容性邊界

- MCP SDK v1 與 v2 不相容。VSIX `0.6.0` 必須在同一 extension-managed
  venv 原子升級 Keeper `2.0.0` 與 PubMed `0.6.1`，並共同驗證固定來源；不得
  讓新舊 package set 混用。
- `external/pubmed-search-mcp` 與 extension installer 固定至 v0.6.1 commit
  `ad85dde08269dbb59eff69d2e92f4d3c5b5bf21d`。
- 截至 2026-08-11，Zotero 官方組織未發布 MCP server。
  `54yyyu/zotero-mcp` 是 MCP Registry 收錄的社群 server，並非 Zotero 官方
  產品；它和 Keeper 都使用 `zotero_mcp` Python namespace，因此只能放在獨立
  Python 環境，不能加入 extension-managed venv。

## 安全邊界

- **Local/Connector 模式**：Zotero Desktop loopback API 與 Connector endpoints
  是主要產品邊界；讀取與匯入不需要 Zotero Web API key，使用者仍需明確選擇
  collection，且不得默認匯入 root collection。
- **Authenticated service 模式**：若透過可遠端存取的 HTTP transport 提供服務，
  必須獨立設定 authentication、tenant identity、bind host、Host/Origin 驗證及
  每 tenant 的持久化目錄；不可沿用 local stdio 的信任假設。

---
*Updated: 2026-08-11*
