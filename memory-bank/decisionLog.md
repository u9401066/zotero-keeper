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

---

## 2025-12-15 (從壓縮摘要)

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

---

## 2025-12 (更早)

### DEC-005: 使用 FastMCP 框架
- **決策**: 使用 FastMCP 而非手動實作
- **理由**: 簡化 tool 定義，自動處理 JSON Schema

### DEC-006: DDD 分層
- **決策**: Domain + Infrastructure，省略 Application 層
- **理由**: 專案規模適中，避免過度工程化

### DEC-007: uv 環境管理
- **決策**: VS Code Extension 優先使用 uv
- **理由**: 更快的安裝速度，更好的鎖定機制

---
*Updated: 2025-12-16*
