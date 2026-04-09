# Decision Log

> 📝 重要架構和實作決策記錄

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
  2. 不需要預先安裝 Python - uv 自動下載 Python 3.11
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
