# Decision Log

> 📝 重要架構和實作決策記錄

## 2025-12-16

### 採用 template-is-all-you-need 結構
- **決策**: 整合 template 專案的 Memory Bank、bylaws、chatmode 等結構
- **原因**: 統一 AI 輔助開發工作流
- **排除**: Claude Code 相關檔案 (.claude/skills)

## 2025-12-15

### P0-P3 改進方案
- **P0**: 修復搜尋數量回報 - `_search_metadata` 傳遞邏輯 bug
- **P1a**: Session PMID 持久化 - 新增 4 個 session 工具
- **P1b**: PubMed → Zotero 直送 - 計劃使用 RIS 中繼

### VS Code Extension uv 管理
- **決策**: 使用 uv 作為 Python 環境管理器
- **原因**: 更快、更可靠的依賴安裝
- **實作**: uvPythonManager.ts

### Tag-based PyPI Release
- **決策**: 使用 Git tag 觸發 CI 自動發布到 PyPI
- **原因**: 版本控制清晰、自動化流程
- **格式**: `v*` (e.g., v0.1.15)

## 2025-12-14

### 本地 Zotero API
- **決策**: 使用 Zotero 本地 HTTP API (port 23119) 而非雲端 API
- **原因**: 隱私、速度、離線支援
- **限制**: 無法直接指定 collection (需手動拖曳)

---
*Updated: 2025-12-16*
