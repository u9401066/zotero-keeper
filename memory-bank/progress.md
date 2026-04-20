# Progress

## Done
- [x] 用 AFM 生成 keeper icon 與 banner 初稿，確認直接生成會混入錯誤文字 (2026-04-15)
- [x] 用 AFM multi-turn edit 產出無文字 icon 與無文字 banner (2026-04-15)
- [x] 確認 AFM 圖仍不夠貼近系列品牌後，改用手作 SVG 重建 icon 與 banner (2026-04-15)
- [x] 使用 `rsvg-convert` 將 `keeper-icon.svg` 與 `vsx-banner.svg` 渲染為正式 PNG (2026-04-15)
- [x] 在 `vscode-extension/README.md` 掛上 `vsx-banner.png`，並在 `vscode-extension/package.json` 保留 `galleryBanner` 配色 (2026-04-15)
- [x] 盤點 3 個 draft PR 的檔案差異與提交內容 (2026-04-15)
- [x] 合併 `origin/copilot/add-documentation-and-readme-again` 到 `main` (2026-04-15)
- [x] 解決 README 衝突並合併 `origin/copilot/add-documentation-and-readme` 到 `main` (2026-04-15)
- [x] 將 README / README.zh-TW 的文件導覽整合為 FAQ + tools reference + collaboration workflow 入口 (2026-04-15)
- [x] 解決 `origin/codex/update-documentation-and-readme` 衝突並完成 merge (2026-04-15)
- [x] 將 `external/pubmed-search-mcp` 更新到最新 `origin/master` `e39f901` (2026-04-15)
- [x] 執行 `vscode-extension` 的 `sync-assets`、`compile` 與 focused unit tests (2026-04-15)
- [x] 推送 `main` 並刪除已 merged 的遠端分支 (2026-04-15)
- [x] 完成 PubMed Search 啟動回歸修復的 release 前驗證，包含 lint、compile、focused mocha tests 與 VSIX package (2026-04-20)

## Doing
- [ ] 準備發布 VS Code extension v0.5.23

## Next
- [ ] 建立 release commit 並推送 `main`
- [ ] 推送 `v0.5.23-ext` tag 觸發 Marketplace 發布
- [ ] 視需要處理 `external/pubmed-search-mcp` stash `pre-sync-2026-04-15-uvlock`

## Blocked
- [ ] 無
