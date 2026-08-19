# Decision Log

## 2026-08-19

### DEC-032: Zotero 10 任務導向寫入覆蓋、PubMed 0.6.3 與 Keeper Pages

#### 決定

- Keeper `2.2.0` 將 Local API allowlist 由 8 個擴充為 17 個 tools；
  新增 collection membership removal，collection/item/saved-search 的
  精確 update/delete，tag batch delete，existing stored-file replacement
  與 full-text batch write。仍不提供 raw endpoint、arbitrary structural
  replacement、batch object delete 或 group-library write。
- 所有 mutation 維持 `confirm=false` 零 I/O，proposal 必須先攜帶
  response-bound Server-ID。Exact update/single delete 使用 object version；
  tag/full-text 使用 library cursor；file replacement 使用 exact
  attachment version + old MD5 並要求 remembered authorization。412 不重試。
- Extension `0.8.0` 固定 PubMed Search MCP 正式 v0.6.3 release commit
  `febf53a8ff1ee253a625869ba251365f73a23c68`，不采用未發 tag/PyPI 的
  master 0.6.5 snapshot。新版仍為 45 tools / 16 categories，主要擴充
  SearchRun、systematic/native-semantic 與 Research Chronicle contracts。
- 新增無框架 GitHub Pages 網站，只介紹 Zotero Keeper 功能、
  Zotero 10 能力與安全流程；PubMed 只連結至其獨立功能站。

#### 理由

正式 release commit 讓 VSIX 安裝可重現；任務導向 allowlist 能覆蓋
Zotero 10 實用寫入類別，卻不需將未分 scope 的 local key 變成任意
HTTP escape hatch。Pages 提供產品層功能說明，避免與 PubMed 獨立站重複。

## 2026-08-12

### DEC-031: Zotero 10+ authorized Local API 寫入與單一 VSIX 發布 artifact

#### 背景
Zotero 10+ 的 desktop Local API 已能在 loopback 上執行 items、collections、saved
searches、full text 與 attachment upload 寫入。它使用 runtime
`/api/local/authorize`、Zotero instance 的 Server-ID 與 database-local version；這些
契約不同於既有無 Web API key 的 Connector 匯入，也不能把 Web API version 或另一個
Zotero profile 的 version 套用於本機更新。同時，`v0.6.0-ext` / Keeper `2.0.0`
已於 2026-08-11 完成發布，下一條發布線需要在不破壞 Zotero 7–9 相容性的前提下
擴充功能。

#### 選項
1. 繼續只使用 Connector writes：相容面最單純，但無法安全更新既有 item、建立
   collection/note/saved search、附檔到既有 item 或寫回 full text。
2. 把 Local API key 當作長期設定或 Web API key：實作較容易，但違反 desktop
   runtime authorization 模型，增加 credential 泄漏與跨 instance 誤用風險，否決。
3. 以 Server-ID-bound runtime authorization、local optimistic concurrency、
   confirm guard 與 loopback 限制新增明確的 Local API tools，同時保留 Connector
   compatibility path：功能與安全邊界可共同驗證，採用。

#### 決定
- Zotero Keeper 升級為 `2.1.0`，預設工具面由 24 增至 32 tools（另有 6
  resources）。新增 8 個 guarded tools：授權 local writes、建立 collection、將 items
  加入 collection、更新安全 scalar fields、建立 child note、建立 saved search、將
  本機檔案附加到既有 item，以及寫入 attachment full text。
- mutation tools 預設 `confirm=false` 且不得送出網路請求；preview 前由
  response-bound read 或 authorize 取得 Server-ID，並在 proposal 中先帶
  `expected_server_id`。七個 confirmed mutations 全部要求該 identity；只有明確
  `confirm=true` 才能寫入。若 authorization identity 不同，必須重新 read、preview
  與取得核准，不能在 preview 後才補 identity。公開 MCP surface 不提供任意
  delete，collection/item keys 必須由呼叫者明確指定。
- Keeper 從 `GET /api/` discovery 取得 API/schema capability 與 Server-ID，透過
  `POST /api/local/authorize` 取得 runtime key。key 只存在 process memory，不寫入
  config、install state、tool output 或 log；authorize 與每個 write request 都攜帶
  Server-ID，401/412/428 等身份或 instance 錯誤不得盲目重試。
- item metadata 更新使用 exact-item response 綁定的 object version；full-text
  replacement 使用 response-bound library cursor，透過 bulk
  `POST /api/users/0/fulltext` 與 `If-Unmodified-Since-Version` 寫入，不使用
  attachment object version。這些 cursor 只在配對的 Zotero Server-ID 有意義，
  不與 Web API、其他 profile 或 desktop instance 混用。陣列欄位的 PATCH
  replacement 語意不得被誤當成 merge，因此公開 item update 僅接受封閉的安全
  scalar fields。
- attachment 使用 Zotero 定義的三階段流程：建立 attachment item、取得
  `uploadKey`/prefix/suffix 並串流上傳、最後註冊 upload。任一後段失敗需回報已建立的
  attachment key，避免把部分成功誤報成完全失敗或再次建立重複 item。
- Local API writes 僅允許 loopback。禁止把 `localhost:23119` bind、proxy 或
  forward 給其他主機；遠端 MCP service 仍需獨立的 authentication、tenant、
  Host/Origin 與資料隔離設計。
- Zotero 7–9 繼續使用既有 Connector import/PDF path；Zotero 10+ capability 不可用
  時不得把 local-write failure 偷偷降級為不同語意的 Connector mutation。
- VS Code extension 發布版為 `0.7.0` / `v0.7.0-ext`，維持 Keeper `2.1.0` 與
  PubMed Search MCP `0.6.1`（commit
  `ad85dde08269dbb59eff69d2e92f4d3c5b5bf21d`、45 tools）在同一 managed venv、
  同一 resolver transaction 的 invariant。
- 發布流程必須先通過 version、managed install、tag archive 與 Local API loopback
  smoke；tag workflow 再只 package 一次。該具名 VSIX 經 content inspection 後，
  同一檔案才可同時送往 Marketplace 與 GitHub Release，禁止 publish 階段重新產生
  artifact。

#### 驗證與發布狀態
- 自動化涵蓋 Local API wire contract、authorization/Server-ID、version conflict、
  三階段 upload、`confirm=false` 零 I/O、真實 loopback simulator，以及 opt-in 的
  本機 Zotero read-only live smoke。
- `v0.7.0-ext` / Keeper `2.1.0` 已於 2026-08-12 發布。GitHub Actions run
  `31560040966` 從 tag archive 安裝並完成全套 gates，只封裝一次 VSIX，再把同一
  檔案送往 Marketplace 與 GitHub Release；公開 artifact SHA256 為
  `11df8af38a6fd804691262dc6182c5ba6f345f5a5cb1c615b218720693eb6c1f`。

## 2026-08-11

### DEC-030: MCP SDK v2 breaking release 與雙 server 原子升級邊界

#### 背景
PubMed Search MCP v0.6.1 已全面遷移到 MCP SDK v2；v2 與既有 SDK v1
runtime 不相容。Zotero Keeper 與 PubMed Search MCP 由同一個 VS Code
extension-managed venv 啟動，因此任何只升級其中一套的方案都可能讓共用的
`mcp` dependency 落在另一套無法啟動的版本。同時，Zotero MCP 生態出現功能豐富
的社群 server，需要明確區分專案來源、Python namespace 與服務安全模型。

#### 選項
1. 保留 Keeper SDK v1、只升級 PubMed - 變更較小，但同一 venv 無法同時滿足
   不相容 runtime，否決。
2. 將兩套 server 一起遷移到 SDK v2，並在同一 managed venv 以單一 package
   set 解析、安裝及驗證 - 有 breaking release 成本，但能維持可重現與可修復安裝。
3. 以 `54yyyu/zotero-mcp` 取代或與 Keeper 混裝 - 可取得不同功能面，但該專案
   並非 Zotero 官方 server，且其 Python module 同樣命名為 `zotero_mcp`，同環境
   會有 namespace/entrypoint 衝突，否決混裝。

#### 決定
- Zotero Keeper 發布 `2.0.0`，改用 `mcp.server.MCPServer`，runtime 約束為
  `mcp>=2.0,<3`。
- PubMed Search MCP 固定至 upstream v0.6.1 commit
  `ad85dde08269dbb59eff69d2e92f4d3c5b5bf21d`；其公開工具面為 45 tools，研究
  演進工作流使用 `build_research_chronicle` 與 `read_research_chronicle`。
- VS Code extension / VSIX 發布 `0.6.0`，把 Keeper `2.0.0` 與 PubMed
  `0.6.1` 視為不可拆分的 runtime package set：停止舊 process，在同一 managed
  venv 共同解析/安裝，再同時驗證版本、direct source 與 server tool listing。
- 截至決策日，Zotero 官方組織沒有發布 MCP server。
  `54yyyu/zotero-mcp` 僅標示為 MCP Registry 收錄的社群 server；若使用，必須放在
  Keeper managed venv 之外的獨立環境並使用不同 server 設定。
- 保留雙 MCP 職責：PubMed Search 負責搜尋、探索、full text、pipeline、session
  與 Research Chronicle；Keeper 負責本地 Zotero 檢視、重複檢查、collection
  選擇及 Connector 匯入。

#### 理由
1. 單一 SDK major 與單一 resolver transaction 可消除共用 venv 的半升級狀態。
2. 固定 release commit、direct URL 與 install state 能讓 VSIX 安裝可重現，也能
   在 breaking upgrade 時強制 refresh，而非誤用舊 venv。
3. Keeper 的 Local API/Connector 路徑能在不要求 Zotero Web API key 的情況下
   服務桌面使用者，符合既有 product boundary。
4. 來源與 namespace 說明可避免把 Registry 收錄誤稱為 Zotero 官方背書，也避免
   兩個 `zotero_mcp` distribution 在同一 interpreter 中互相覆蓋。
5. local stdio 與 authenticated HTTP service 的威脅模型不同；明確分界能避免
   把 localhost 無認證假設錯誤套用到可遠端存取的服務。

#### 影響
- 所有 Keeper MCP registration、context 型別、測試與文件由 `FastMCP` 名稱遷移
  至 SDK v2 `MCPServer`；SDK v1 環境不再支援。
- Extension upgrade 必須同時刷新兩套 packages；安裝 smoke 必須建立兩個 server
  並列出 tools，而不能只測試 Python import。
- Packaged assistant assets 必須同步 PubMed v0.6.1 的 45-tool surface 與
  `pubmed-research-chronicle` skill，移除舊 timeline 公開工具假設。
- Collection resolution 只有取得非空 Zotero key 才算成功；主工具與 opt-in
  legacy imports 都不得把 malformed/missing destination 降級成 My Library root。
- local/Connector 模式以桌面 Zotero 與 loopback 為信任邊界；authenticated
  service 模式必須額外實施 token、tenant、bind host、Host/Origin 驗證與資料目錄
  隔離，兩者不得混為同一安全設定。
- `v0.5.35-ext` 已完成；`v0.6.0-ext` / Keeper `2.0.0` 已於
  2026-08-11 完成發布，後續 Local API 擴充由 DEC-031 接續。

## 2026-06-24

### DEC-029: PDF import via Connector API (Keeper 1.14.0 / VSIX v0.5.35)
- **Decision**: Support importing local PDF files into Zotero entirely within
  the Local/Connector architecture (no Web API key), via a new `import_pdf` tool.
- **Rationale**:
  1. Zotero's Connector API exposes `/connector/saveAttachment` and
     `/connector/saveStandaloneAttachment` (confirmed from server_connector.js),
     which accept the file as the raw request body with an `X-Metadata` header —
     no Web API key needed, matching the existing architecture.
  2. Metadata mode reuses the type-aware `_unified_article_to_zotero` mapping
     (save_items with a session + connector key, then save_attachment);
     auto-recognize mode lets Zotero build the parent from the PDF.
  3. `X-Metadata` is ASCII-escaped JSON so non-ASCII (CJK) titles stay
     header-safe; a 200 "not editable" body is treated as a failure.
- **Limitation**: cannot attach to a pre-existing library item (Connector
  sessions only know items created in that session).
- **Release line**: `v0.5.35-ext` (bundled keeper `1.14.0`).

### DEC-028: Type-aware Zotero metadata mapping (Keeper 1.13.0 / VSIX v0.5.34)
- **Decision**: Make the PubMed/RIS → Zotero importer detect the correct Zotero
  item type and route fields to that type's schema, instead of forcing every
  record into `journalArticle`.
- **Rationale**:
  1. Books, book chapters, conference papers, web pages, software repositories
     and datasets each have different valid fields in Zotero; sending journal
     fields to them caused silent metadata loss via the Connector API.
  2. A verified field registry (`mappers/zotero_schema.py`) plus
     `finalize_item_for_schema()` keeps only valid fields and preserves the rest
     in the Zotero `Extra` field, so no metadata is ever dropped.
  3. `detect_item_type()` infers the type from source vocabularies and
     identifier/field heuristics (arXiv → preprint, repo URL → computerProgram,
     ISBN without journal → book/bookSection, website fields → webpage).
  4. `mcpProvider.ts` now consumes `ZOTERO_KEEPER_VERSION` instead of a
     hardcoded string so the bundled keeper version cannot drift again.
- **Delivery**: extension downloads `v{X}-ext.tar.gz#subdirectory=mcp-server`,
  so the keeper change ships via the `v0.5.34-ext` release line (bundled keeper
  `1.13.0`).
- **Release line**: `v0.5.34-ext`.

## 2026-06-22

### DEC-027: VSIX v0.5.33 upgrades managed PubMed Search to v0.5.17
- **Decision**: Keep extension-managed PubMed Search installs on a fixed GitHub
  commit archive, but advance the baseline from `0.5.12` to `0.5.17`.
- **Rationale**:
  1. `pubmed-search-mcp v0.5.17` fixes source API contact email propagation for
     OpenAlex, CrossRef, Unpaywall, and fulltext downloader fallbacks.
  2. The VSIX installer must remain reproducible and refresh when direct URL
     package sources change, so `pubmedSearchPackage.ts` continues to pin a
     specific upstream commit archive.
  3. Keeper optional/dev dependency metadata should accept the PyPI `0.5.17`
     release while the extension package path keeps the exact commit source.
- **Release line**: `v0.5.33-ext`.

## 2026-04-25

### DEC-026: VSIX v0.5.28 production install hardening
- **Decision**: Treat the VSIX as the canonical installer for Zotero Keeper,
  PubMed Search MCP, and assistant harness assets.
- **Rationale**:
  1. System/custom Python installs must use an extension-managed writable venv.
  2. Package sources must be pinned direct URLs and validated through
     `direct_url.json` plus `install-state.json`.
  3. Codex support requires root `AGENTS.md` and packaged `.codex/skills`.
  4. Release tags must be guarded by asset-sync, no-pip, version-sync, and VSIX
     content checks.
- **Release line**: `v0.5.28-ext`.

> 📝 重要架構和實作決策記錄

## 2026-04-20

### DEC-025: VS Code extension 對 PubMed 0.5.4 採固定 snapshot 安裝策略
- **決策**: extension 不直接安裝 PyPI `pubmed-search-mcp==0.5.4`，改為固定到上游已修正 commit archive，並在 MCP 啟動時傳入 `PUBMED_WORKSPACE_DIR`
- **理由**:
  1. `0.5.4` 的 PyPI 發行版缺少啟動所需 import，會在 VS Code 內直接造成 PubMed MCP server 啟動失敗
  2. extension 使用者需要可重現、可自動修復的安裝來源，不能依賴手動 hotfix
  3. 以固定 commit archive 安裝可維持 `uv` 工作流與跨平台一致性，不需要額外 git 步驟
- **實作**:
  - `vscode-extension/src/pubmedSearchPackage.ts` 統一管理 PubMed package source / version / entrypoint
  - `pythonEnvironment.ts` 與 `uvPythonManager.ts` 改安裝固定 snapshot 並做最小版本檢查
  - `mcpProvider.ts` 傳入 `PUBMED_WORKSPACE_DIR` 讓 VS Code workspace 啟動路徑一致

## 2026-03-04

## 2026-03-18

### DEC-024: pre-tag edge-case 測試改用本地 mcp-server 作為安裝來源
- **決策**: `vscode-extension/tests/test_python_env_edge_cases.py` 預設改為安裝目前工作樹的 `mcp-server/`，並保留 `ZOTERO_KEEPER_PACKAGE_SOURCE` 覆寫能力
- **理由**:
  1. release 前本地驗證時，`v0.5.20-ext` GitHub archive 尚未存在，直接抓 release tarball 會造成假性失敗
  2. edge-case suite 的目的在驗證 `UvPythonManager` 的安裝/重建/版本檢查邏輯，而不是驗證 Git tag 是否已發布
  3. 本地 path 安裝可以驗證當前工作樹的 keeper 版本與匯入流程，同時保留覆寫能力給真正的 release-archive smoke test

### DEC-021: VS Code Extension 必須避開過舊 PyPI zotero-keeper
- **決策**: extension 改為從 GitHub release tarball 安裝 `zotero-keeper`，而非直接信任 PyPI `>=1.11.0`
- **理由**:
  1. PyPI 最新 `zotero-keeper==1.11.0` 仍缺少 repo 內已修復的 PubMed import/tool async 修正
  2. 使用者實際會因此持續遇到舊 tool 問題（包含 coroutine 類錯誤）
  3. `uv` 可直接安裝 GitHub tarball，不需 git，跨平台可用
- **實作**:
  - `vscode-extension/src/uvPythonManager.ts` 改為安裝 `v0.5.19-ext` tag 的 `mcp-server` subdirectory
  - `pubmed-search-mcp` 最低版本提升到 `0.4.5`

### DEC-022: uv-managed venv 必須先驗證 Python 版本並清除壞環境
- **決策**: `UvPythonManager` 對既有 venv 先做 Python 版本驗證；若缺 binary、binary 壞掉、或版本低於 3.12，先刪除再重建
- **理由**:
  1. `uv venv --python 3.12` 不保證會覆寫既有錯誤/舊版 venv
  2. 原本 ready check 只驗證「可執行」，不足以防止 3.11 舊環境殘留
  3. 這會在 macOS / Linux / Windows 都影響修復與重裝成功率

### DEC-023: 用 install-state 判斷 extension 管理環境是否需要一次性遷移
- **決策**: 在 extension global storage 寫入 `install-state.json`，用來辨識「這個環境是不是由新版 extension 安裝」
- **理由**:
  1. 舊 PyPI `zotero-keeper==1.11.0` 的版本號數值比 `0.5.16` 大，單靠 package version 會誤判成已最新
  2. 新版需要把舊環境自動遷移到 GitHub tarball 安裝來源，但不應每次開資料夾都重裝
  3. install-state 可做到「升級時補一次、之後穩定重用」

### DEC-019: Async/Await 全面修復策略
- **決策**: 一次修復所有 PubMed API 呼叫的 async/await 問題，而非逐個修
- **理由**:
  1. PubMedClient 所有方法都是 async，但 wrapper 和 tool 呼叫端多數遺漏 await
  2. 逐個修會遺漏，應全面搜索並一次修正
- **影響**: 12 call sites + 3 wrapper functions across 6 files
- **結果**: 所有 PubMed import/search tools 恢復正常

### DEC-020: pubmed-search-mcp 0.3.8 → 0.4.4 升級
- **決策**: 升級 submodule 至最新 0.4.4，pyproject.toml 同步更新
- **理由**: 新版本含 citation metrics 快取、mypy strict 修正、BM25 排序改進
- **相容性**: 無 breaking changes，我們用的 API (PubMedClient, LiteratureSearcher, SearchResult) 簽名完全不變

## 2025-06-27

### DEC-018: Version Unification (MCP Server 1.x → 0.5.x)
- **決策**: 統一 MCP Server 版本號，與 VS Code Extension 同步
- **理由**:
  1. MCP Server 版本 (1.11.0/1.6.1) 與 VS Code Extension (0.5.x) 不一致
  2. monorepo 中各元件版本應統一，便於追蹤
- **實作**: pyproject.toml, __init__.py, package.json, statusBar.ts 全部改為 0.5.14

### DEC-017: Attachment Tools 實作策略
- **決策**: 透過 Zotero Local API 存取附件和全文，不直接讀取 PDF 二進位
- **理由**:
  1. Zotero 已自動索引 PDF/EPUB/HTML，提供全文純文字 API
  2. 直接讀取 PDF 需要 pymupdf 等重量級依賴
  3. 傳送大量 PDF 二進位到 AI 不實際
- **實作**:
  - `get_item_fulltext`: 呼叫 `/api/users/0/items/{key}/fulltext`
  - `resolve_attachment_path`: 組合 `ZOTERO_DATA_DIR/storage/{key}/{filename}`
  - PDF 優先排序，file existence check

## 2026-01-12

### DEC-016: OpenURL 機構訂閱整合
- **決策**: 新增 OpenURL Link Resolver 整合，讓使用者透過機構訂閱存取全文
- **理由**:
  1. 現有全文來源 (Europe PMC, Unpaywall, CORE) 只提供 OA 版本
  2. 許多使用者有機構訂閱但無法利用
  3. OpenURL 是 NISO 標準 (Z39.88)，廣泛支援
- **實作**:
  - 新增 `sources/openurl.py` - OpenURLBuilder 類別
  - 新增 `mcp/tools/openurl.py` - 4 個 MCP 工具
  - 整合到 `unified_search` 輸出
  - VS Code Extension 設定 UI
- **預設機構**: 16 個 (台大、成大、Harvard、MIT...)
- **環境變數**: `OPENURL_PRESET`, `OPENURL_RESOLVER`

### DEC-014: 統一匯入工具 import_articles
- **決策**: 建立單一 `import_articles` 工具處理所有來源的匯入
- **理由**:
  1. 原有多個 import 工具 (import_ris_to_zotero, import_from_pmids, quick_import_pmids) 功能重疊
  2. pubmed-search-mcp 已有 `UnifiedArticle` 標準格式，支援 PubMed/Europe PMC/CORE/CrossRef/OpenAlex/Semantic Scholar
  3. 統一接口讓 Agent 更容易使用
  4. 兩個 MCP 間透過標準化格式通訊
- **實作**:
  - 新增 `unified_import_tools.py`
  - 接受 `UnifiedArticle.to_dict()` 格式或 RIS 文字
  - 自動轉換為 Zotero 格式
  - 保留 collection 防呆機制
- **工作流**: `pubmed-search-mcp (search) → articles → zotero-keeper (import_articles)`

### DEC-015: Collection 防呆機制完善
- **決策**: 所有 import 工具必須有 collection 驗證
- **實作**:
  - 如果 `collection_name` 找不到 → 回傳錯誤 + 可用 collections 清單
  - 如果沒指定 collection → 存到 root 但加 warning
  - 成功時回傳 `saved_to` 資訊確認
- **修改工具**: import_ris_to_zotero, import_from_pmids, quick_import_pmids, import_articles

### DEC-017: keeper 採 collaboration-safe 預設工具面
- **決策**: 當 zotero-keeper 與 pubmed-search-mcp 協作時，keeper 預設不再公開重複的 PubMed bridge/import 工具
- **理由**:
  1. 避免兩個 MCP 同時暴露 PubMed 搜尋/匯入橋接工具，讓 Agent 選錯責任邊界
  2. keeper 已有 `import_articles` 可作為單一 PubMed → Zotero handoff
  3. `search_pubmed_exclude_owned`、`quick_import_pmids`、`batch_import_from_pubmed` 會讓工具面再次碎片化
  4. 預設收斂可減少重複 citation-metrics / PubMed metadata 工作流
- **實作**:
  - `McpServerConfig` 新增 `enable_legacy_pubmed_tools`
  - 環境變數：`ZOTERO_KEEPER_ENABLE_LEGACY_PUBMED_TOOLS=1`
  - 預設只保留 `advanced_search`、`check_articles_owned`、`import_articles`
  - legacy 模式才註冊 `search_pubmed_exclude_owned`、`import_ris_to_zotero`、`import_from_pmids`、`quick_import_pmids`、`batch_import_from_pubmed`
  - README / server instructions 同步改寫責任分界
- **工作流**: `pubmed-search-mcp (search/enrich/export) → zotero-keeper check_articles_owned/import_articles`

### DEC-018: 以跨 repo 契約測試與 docs guard 固化 collaboration-safe 工作流
- **決策**: keeper / pubmed-search 的整合不只靠文件約定，也要用自動化測試與 CI guard 固化
- **理由**:
  1. `UnifiedArticle.to_dict()` 是兩個 repo 之間的真正資料契約，單靠各自單元測試不足以防 drift
  2. README / 設計文件 / agent workflow 很容易在後續修改時回流到舊版 keeper PubMed bridge 語言
  3. production-grade 整合需要同時鎖定 runtime 契約與文件表面
- **實作**:
  - `test_unified_import_tools.py` 新增跨 repo 契約測試
  - `scripts/check_collaboration_safe_docs.py` 檢查 canonical docs 與 agent workflow
  - `ci.yml` checkout submodules 並執行 docs guard
- **限制**:
  - external submodule 的 dirty state 仍需靠 submodule repo 內 commit 或 revert 才能清除

### DEC-019: submodule research agent 變更採 upstream commit，而非在主 repo 保留 dirty state

- **決策**: `external/pubmed-search-mcp/.github/agents/research.agent.md` 的 collaboration-safe workflow 變更直接提交到 pubmed-search-mcp 上游，再由主 repo 更新 submodule pointer
- **理由**:
  1. 如果只讓主 repo 指向一個本地 dirty submodule，release 不可重現
  2. root repo 的 docs guard 與 VSIX bundled repo-assets 已依賴這份 agent workflow 的新內容
  3. 先把 submodule commit 推到遠端，主 repo 才能安全記錄新的 gitlink
- **實作**:
  - submodule upstream commit: `23fb483` (`docs: align research agent with collaboration-safe import workflow`)
  - 下一步由主 repo 記錄新的 `external/pubmed-search-mcp` pointer

---

## 2025-12-16

### DEC-001: 專案整理優先順序
- **決策**: 先更新 Memory Bank，暫緩大檔案拆分
- **理由**:
  1. 目前功能運作正常，拆分屬於 nice-to-have
  2. Memory Bank 需要先記錄現狀，才能追蹤未來改進
  3. 拆分需要更多時間和測試
- **後續**: 記錄待拆分清單於 architect.md

### DEC-002: Template 整合範圍
- **決策**: 排除 `.claude/skills/` 目錄
- **理由**: Claude Code 相關，Copilot 不需要
- **保留**: memory-bank, bylaws, chatmodes, CONSTITUTION.md, AGENTS.md

### DEC-008: v1.10.1 發布流程
- **決策**: 使用 Git Tag 觸發自動 PyPI 發布
- **流程**:
  1. 建立 Git tag: `git tag -a vX.Y.Z`
  2. 推送到 GitHub: `git push origin vX.Y.Z`
  3. GitHub Actions 自動執行 build + publish (Trusted Publishing)
- **新增功能**: 一鍵安裝按鈕、analytics tools、quick_import_pmids
- **工具數**: 22 → 25

---

## 2025-12-15

### DEC-003: P0 修復 - 搜尋計數
- **決策**: 在 `_search_metadata` 被刪除前先取得 `total_count`
- **位置**: `pubmed-search-mcp/discovery.py`
- **原因**: Bug 導致搜尋計數顯示錯誤

### DEC-004: P1a - Session Tools
- **決策**: 新增 4 個 session 工具
- **工具**:
  - `get_session_pmids` - 取得 Session 中的 PMID
  - `list_search_history` - 列出搜尋歷史
  - `get_cached_article` - 取得快取文章
  - `get_session_summary` - Session 摘要
- **原因**: 解決 Agent 記憶體滿載，PMID 遺失問題

### DEC-009: VS Code Extension 使用 uv
- **決策**: v0.3.1 使用 uv 取代 embedded Python
- **理由**:
  1. uv 比 pip 快 10-100x
  2. 不需要預先安裝 Python - uv 自動下載 Python 3.12
  3. Extension 大小從 ~35MB 降到 ~30KB
  4. 解決 Windows 上的 pip 安裝問題
- **檔案變更**: `embeddedPython.ts` → `uvPythonManager.ts`

### DEC-010: McpServerDefinitionProvider API
- **決策**: 使用 VS Code 1.99+ 官方 MCP 整合方式
- **實作**: 透過 `vscode.lm.registerMcpServerDefinitionProvider()` 動態註冊 MCP servers

---

## 2025-12-12

### DEC-011: 雙 MCP 架構
- **決策**: PubMed search (pubmed-search-mcp) 與 Zotero import (zotero-keeper) 分離
- **理由**:
  1. pubmed-search-mcp 已有 11+ 完整搜尋工具
  2. 避免重複功能
  3. 職責清晰：搜尋 vs 儲存
  4. RIS 格式作為標準交換格式

### DEC-012: Phase 3.5 整合搜尋
- **決策**: 實作 `search_pubmed_exclude_owned` 工具
- **功能**: 結合 PubMed 搜尋與 Zotero 書庫過濾，一次找出「尚未擁有」的新文獻

### DEC-013: Batch Import v1.7.0 設計
- **決策**:
  1. 新增 `collection_key` 參數直接分類
  2. 等待完成後回傳摘要（簡單方案）
  3. 衝突項目加警告標記而非跳過
- **理由**: 平衡功能與簡潔，避免資料遺失

---

## 待處理問題清單 (2025-12-15 觀察)

### 🔴 P0: 搜尋結果數量錯誤 ✅ 已修復
### 🟠 P1: PMID 暫存機制 ✅ 已實作 Session Tools
### 🟠 P1: PubMed → Zotero 直送 (待處理)
### 🟡 P2: Collection 選擇流程
### 🟡 P2: 從 Zotero 讀摘要
### 🟢 P3: 全文連結檢索
### 🟢 P3: IF 查詢機制

---

## 更早決策

### DEC-005: 使用 FastMCP 框架
- **決策**: 使用 FastMCP 而非手動實作
- **理由**: 簡化 tool 定義，自動處理 JSON Schema

### DEC-006: DDD 分層
- **決策**: Domain + Infrastructure，省略 Application 層
- **理由**: 專案規模適中，避免過度工程化

---
*Updated: 2025-12-22*
| 2025-12-26 | VS Code Extension 使用臨時 Python 腳本檔案進行版本檢查，而非命令行內嵌腳本 | 避免 shell 字串跳脫問題和潛在的注入風險，使用臨時檔案更安全可靠 |
