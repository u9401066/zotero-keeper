# Decision Log

> 📝 重要架構和實作決策記錄

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
