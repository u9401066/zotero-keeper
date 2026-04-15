# Active Context

## 當前焦點
完成 3 個文件 draft PR 整併，將 `external/pubmed-search-mcp` 對齊到最新 `origin/master`，同步 extension 內建 repo-assets，並清理已合併的遠端分支。

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
- [x] 完成第 3 個 draft PR 的 merge 衝突收尾
- [x] 更新 submodule pointer 並同步 extension repo-assets
- [x] 執行同步後的最小驗證並推送 `main`
- [x] 刪除已合併的遠端分支

## 上下文
- `main` 已合併 3 個文件 draft branches，GitHub open PR 已降為 0。
- submodule 已更新到 `e39f901`，root repo 的 submodule pointer 與 extension repo-assets 已同步。
- extension 新增 `openAlexApiKey` 設定，會將 `OPENALEX_API_KEY` 傳入 PubMed Search MCP 環境。
- submodule 原本未提交的 `uv.lock` 版本差異已安全保存在 `external/pubmed-search-mcp` 的 stash `pre-sync-2026-04-15-uvlock`。

## 更新時間
2026-04-15
