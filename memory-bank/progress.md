# Progress (Updated: 2026-04-13)

## Done

- 安裝 uv（cargo build），建立 mcp-server `.venv` 並安裝 dev 依賴
- 基線檢查：
  - Ruff：`uv run ruff check src/` ✅
  - Mypy：`uv run mypy src/ --ignore-missing-imports` ❌（既有 173 錯誤）
  - Pytest：`uv run pytest tests/ -v --tb=short` ❌（缺少 `external/pubmed-search-mcp/src` 導致 1 failed；其餘 412 passed）
- 確認工作樹乾淨，準備撰寫文件與 README 更新
- 新增 `docs/COLLABORATION_WORKFLOW.md` 並在 README / README.zh-TW 加入 collaboration-safe 摘要與一鍵安裝入口、工具數同步

## Doing

- 自檢文件與 README 文字、連結與格式，整理 PR 內容
- 規劃最終回報（parallel_validation、Memory Bank 更新、PR 建立）

## Next

- 確認交叉連結與說明清楚後提交 PR
- 視需要補充驗證說明，保持既有測試基線記錄
- 執行 parallel_validation 並更新 PR 描述 / Memory Bank
