# Product Context

> 🏗️ 技術架構和實作細節

## 技術棧

### Python MCP Servers
- **Runtime**: Python 3.12+
- **Package Manager**: uv only
- **Framework**: MCP Python SDK v2 `MCPServer` (`mcp>=2,<3`)
- **Current source set**: Zotero Keeper `2.2.0` + PubMed Search MCP `0.6.3`
- **Libraries**:
  - biopython (NCBI Entrez)
  - httpx (async HTTP)
  - pydantic / pydantic-settings (configuration and contracts)
  - structlog (structured MCP tool logging)

### VS Code Extension
- **Runtime**: Node.js 18+
- **Framework**: VS Code Extension API
- **Language**: TypeScript
- **Current stable release**: `0.7.0` / `v0.7.0-ext`（2026-08-12 已發布）
- **Preparing release**: `0.8.0` / `v0.8.0-ext`（Keeper 2.2.0）
- **MCP v2 migration baseline**: `0.6.0` / `v0.6.0-ext`（2026-08-11 已發布）

## 架構

Current collaboration-safe split:

```
┌─────────────────────────────────────────────────────────┐
│                    VS Code Extension                      │
│                  (vscode-zotero-mcp)                     │
├─────────────────────────────────────────────────────────┤
│                   MCP Protocol Layer                      │
├──────────────────────┬──────────────────────────────────┤
│ pubmed-search 0.12.0 │      keeper 2.4.1                │
│ (44 research tools)  │ (50 tools + 6 resources)         │
├──────────────────────┼──────────────────────────────────┤
│   NCBI Entrez API    │     Zotero Desktop App           │
└──────────────────────┴──────────────────────────────────┘
```

## 主要功能模組

### pubmed-search-mcp
- `unified_search`: 單一公開搜尋入口
- `generate_search_queries`: MeSH 擴展搜尋策略
- `validate_pico_plan`: 驗證 Agent 提取的 P/I/C/O 並產生 pipeline（取代已移除的 `parse_pico`）
- `fetch_article_details`: 文章詳情與進一步探索
- `get_citation_metrics`: iCite 引用指標
- `read_session(request={...})`: Session PMID、文章、摘要與 log 讀取
  （取代已移除的 `get_session_pmids` / `get_cached_article` / `get_session_summary`）
- `build_research_chronicle` / `read_research_chronicle`: 可稽核的研究演進紀錄
- full-text、citation tree、multi-source、pipeline/export 與 reference
  verification、research workspace、PRISMA screening 與 `register_fulltext` 工具由同一 44-tool registry 提供（0.12.0）

### zotero-keeper
- MCP SDK v2 server surface：50 tools + 6 resources
- `export_items` / `get_bibliography`: 唯讀引用匯出與 CSL 參考文獻（2.4.0）
- `search_items` / `advanced_search`: 搜尋本地 Zotero 文獻
- `list_collections`: 列出收藏夾
- `check_articles_owned`: 本地 PMID / DOI 重複檢查
- `import_articles`: collaboration-safe PubMed -> Zotero handoff
- `import_pdf`: metadata 或 Zotero auto-recognize PDF 匯入
- `interactive_save` / `quick_save`: 手動存檔與 metadata fetch
- Zotero 10+ 的 17 個 guarded Local API tools：runtime authorization、
  item/collection/saved-search 任務導向 lifecycle、membership、tag deletion、
  stored-file add/replace 與 single/batch full-text writeback

## 資料流

1. User → VS Code Copilot / Claude
2. pubmed-search-mcp `unified_search(..., output_format="json", options="full_records")`
   (0.12.0+ JSON defaults to summary records, which `import_articles` refuses)
3. zotero-keeper `check_articles_owned(...)` → `import_articles(...)`
4. Results → Session Cache / Zotero → User

## 安裝與相容性邊界

- MCP SDK v1 與 v2 不相容。VSIX `0.6.0` 已在 2026-08-11 完成 Keeper
  `2.0.0` 與 PubMed `0.6.1` 的同一 extension-managed venv 原子升級。
- VSIX `0.8.0` source 把 Keeper pin 提升為 `2.2.0`，仍在同一 resolver
  transaction 解析、安裝並驗證兩套固定來源；不得讓 package set 部分升級。
- `external/pubmed-search-mcp` 與 extension installer 固定至 v0.6.3 commit
  `febf53a8ff1ee253a625869ba251365f73a23c68`。
- 截至 2026-08-11，Zotero 官方組織未發布 MCP server。
  `54yyyu/zotero-mcp` 是 MCP Registry 收錄的社群 server，並非 Zotero 官方
  產品；它和 Keeper 都使用 `zotero_mcp` Python namespace，因此只能放在獨立
  Python 環境，不能加入 extension-managed venv。

## 安全邊界

- **Zotero 10+ Local API 模式**：讀取無需 Web API key；寫入先 runtime authorize，
  key 僅存記憶體。preview 前先取得 response-bound Server-ID 並放入
  `expected_server_id`；所有 confirmed mutation 都要求 proposal 中已核准的 identity。
  exact update/delete 使用 object version；tag/full-text 使用 library cursor；
  attachment replacement 同時綁定 old MD5。identity 改變時重新 read、preview
  與取得核准。
- **Zotero 7–9 Connector 相容模式**：保留既有 Connector import/PDF 路徑，不因
  新增 Zotero 10 capability 而中斷。使用者仍需明確選擇 collection，且不得默認
  匯入 root collection。
- **Loopback 限制**：`localhost:23119` 不得 bind、proxy 或 forward 給其他主機；
  desktop runtime authorization 不是遠端服務 authentication。
- **Authenticated service 模式**：若透過可遠端存取的 HTTP transport 提供服務，
  必須獨立設定 authentication、tenant identity、bind host、Host/Origin 驗證及
  每 tenant 的持久化目錄；不可沿用 local stdio 的信任假設。

---
*Updated: 2026-08-19*
