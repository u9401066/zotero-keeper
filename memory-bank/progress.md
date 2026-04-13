# Progress (Updated: 2026-04-13)

## Done

- 安裝 uv（cargo build），建立 mcp-server `.venv` 並安裝 dev 依賴
- 基線檢查：
  - Ruff：`uv run ruff check src/` ✅
  - Mypy：`uv run mypy src/ --ignore-missing-imports` ❌（既有 173 錯誤）
  - Pytest：`uv run pytest tests/ -v --tb=short` ❌（缺少 `external/pubmed-search-mcp/src` 導致 1 failed；其餘 412 passed）
- 確認工作樹乾淨，準備撰寫文件與 README 更新
- 新增 `docs/COLLABORATION_WORKFLOW.md` 並在 README / README.zh-TW 加入 collaboration-safe 摘要與一鍵安裝入口、工具數同步
- 已建立 PR #3（docs 更新），parallel_validation 工具不可用已註記

## Doing

- 等待並追蹤 PR #3 的 review
- 如 reviewer 要求驗證，依需求補充並記錄

## Next

- 回應 review 並同步 Memory Bank
- 視需要補充驗證說明，保持既有測試基線記錄
- 合併後清理 / 更新相關文件（如有）
