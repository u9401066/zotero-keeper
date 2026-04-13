# Progress (Updated: 2026-04-13)

## Done

- 安裝 uv（cargo build），建立 mcp-server `.venv` 並安裝 dev 依賴
- 基線檢查：
  - Ruff：`uv run ruff check src/` ✅
  - Mypy：`uv run mypy src/ --ignore-missing-imports` ❌（既有 173 錯誤）
  - Pytest：`uv run pytest tests/ -v --tb=short` ❌（缺少 `external/pubmed-search-mcp/src` 導致 1 failed；其餘 412 passed）
- 確認工作樹乾淨，準備撰寫文件與 README 更新

## Doing

- 規劃並撰寫新的使用者導向文件，整理 README 與 README.zh-TW 對齊最新功能與協作流程
- 設定 PR 檢查清單與 Memory Bank 更新節奏

## Next

- 完成文件草稿與 README 對齊，確定連結與指引正確
- 覆核文字與格式後提交 PR
- 視需要追加測試/驗證說明，保持基線狀態記錄
