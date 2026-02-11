# Decision Log

> 📝 重要架構和實作決策記錄

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
