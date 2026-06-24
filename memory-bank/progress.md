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
- [x] 確認 `pubmed-search-mcp v0.5.17` GitHub release commit 與 PyPI resolver 皆可用 (2026-06-22)
- [x] 將 `external/pubmed-search-mcp` 更新到 `v0.5.17` commit `60ea753` (2026-06-22)
- [x] 參考 ZotMeta 強化 keeper→Zotero metadata：新增 url/accessDate/libraryCatalog 並用原生 PMID 欄位做去重 (2026-06-24)
- [x] 新增 `infrastructure/mappers/zotero_schema.py`：14 種 Zotero 類型欄位註冊表、`detect_item_type()`、`finalize_item_for_schema()`（不支援欄位保存到 extra）(2026-06-24)
- [x] 讓 `_unified_article_to_zotero` 與 RIS parser 具備型別感知（書本/章節/研討會/網頁/軟體/資料集 + editors）(2026-06-24)
- [x] 新增型別感知測試（test_zotero_schema + 匯入/RIS），mcp-server 單元測試 464 passing (2026-06-24)
- [x] bump：mcp-server `1.13.0`、extension `0.5.34`、keeper archive 指向 `v0.5.34-ext`，mcpProvider 改用 `ZOTERO_KEEPER_VERSION` 常數 (2026-06-24)
- [x] 從 Zotero 原始碼確認 Connector API 可上傳檔案（saveAttachment / saveStandaloneAttachment），無需 Web API key (2026-06-24)
- [x] 新增 `import_pdf` 工具：metadata 模式（save_items session + save_attachment）與 auto-recognize 模式（standalone）(2026-06-24)
- [x] 新增 client 二進位/附件支援（_request_raw content+headers、save_attachment、save_standalone_attachment、save_items session_id）(2026-06-24)
- [x] 完整測試：wire-level（httpx MockTransport）+ 端到端 + 錯誤分支 + 真實 FastMCP 註冊，494 passing；import_pdf 與附件方法 100% 覆蓋 (2026-06-24)
- [x] bump：mcp-server `1.14.0`、extension `0.5.35`、keeper archive 指向 `v0.5.35-ext` (2026-06-24)

## Doing
- [ ] 發布 VS Code extension v0.5.35 / Zotero Keeper 1.14.0（PDF 匯入）

## Next
- [ ] 推送 `main` 並推送 `v0.5.35-ext` tag 觸發 Marketplace/VSIX 發布
- [ ] 驗證 GitHub Actions release/publish workflow 結果

## Blocked
- [ ] 無
