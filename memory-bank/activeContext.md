# Active Context

## 當前焦點
整併 3 個文件 draft PR，將 `external/pubmed-search-mcp` 對齊到最新 `origin/master`，同步 extension 內建 repo-assets，並清理已合併的遠端分支。

## 相關檔案
- `README.md` - 英文主 README，整合 tools reference、FAQ 與 collaboration workflow 導覽
- `README.zh-TW.md` - 繁中 README，與英文版同步工具清單與文件入口
- `docs/COLLABORATION_WORKFLOW.md` - collaboration-safe 工作流說明
- `docs/faq.md` - 安裝與疑難排解 FAQ
- `docs/tools-reference.md` - 公開工具參數總表
- `external/pubmed-search-mcp` - submodule，需更新到最新 `origin/master`
- `vscode-extension/scripts/sync-copilot-assets.mjs` - 將 submodule 資產同步到 extension 打包樹
- `memory-bank/progress.md` - 任務進度追蹤

## 待解決問題
- [ ] 完成第 3 個 draft PR 的 merge 衝突收尾
- [ ] 更新 submodule pointer 並同步 extension repo-assets
- [ ] 執行同步後的最小驗證並推送 `main`
- [ ] 刪除已合併的遠端分支

## 上下文
- `main` 已經合併 `origin/copilot/add-documentation-and-readme-again` 與 `origin/copilot/add-documentation-and-readme`。
- `origin/codex/update-documentation-and-readme` 正在 merge，衝突集中在 README 與 memory-bank 任務紀錄。
- submodule 本地 `HEAD` 仍停在 `8d2f249`，落後 superproject 目前記錄的 `23fb483`，也落後 submodule 遠端 `origin/master` `e39f901`。
- extension 的 `sync-assets` 會從 `external/pubmed-search-mcp` 複製 agent / hooks / skills 到 `vscode-extension/resources/repo-assets/pubmed-search-mcp`，submodule 更新後必須同步一次。

## 更新時間
2026-04-15
