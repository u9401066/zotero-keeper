# Active Context

> 🎯 目前工作焦點與下一步行動

## 當前狀態: 撰寫文件與 README 更新，準備提交 PR（分支：codex/update-documentation-and-readme）

### 已確認 (2026-04-13)

1. ✅ 基線檢查（mcp-server）
   - `uv venv` + `uv pip install -e .[dev]`
   - Ruff：`uv run ruff check src/` ✅
   - Mypy：`uv run mypy src/ --ignore-missing-imports` ❌（既有 173 個錯誤）
   - Pytest：`uv run pytest tests/ -v --tb=short` ❌（因缺少 `external/pubmed-search-mcp/src`，1 failed）

2. ✅ 工作樹乾淨，尚未有檔案變更

### 目前正在做

1. 撰寫面向使用者的協作/安裝文件，梳理 README（含中文版）對齊最新功能與工具數
2. 設計 PR 內容與檢查清單，確保符合憲法與子法（文檔優先、Memory Bank 同步）

### 下一步

- 編寫新的文件頁面並更新 README / README.zh-TW 的功能概覽與協作引導
- 再次檢查變更範圍與文件連結，準備提交 PR
- 視需要補充測試或說明，維持現有測試基線記錄

---
*Updated: 2026-04-13*
*工作模式: Documentation Refresh*
