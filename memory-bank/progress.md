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
- [x] 完成 VSIX `0.5.35` / Keeper `1.14.0` 發布與 PDF 匯入交付 (2026-06-24)
- [x] 盤點 PubMed Search MCP v0.6.1：固定 commit `ad85dde`、45 tools、Research Chronicle 與 SDK v2 契約 (2026-08-11)
- [x] 將 Keeper 升級為 `2.0.0`，改用 `mcp.server.MCPServer` 與 `mcp>=2,<3` (2026-08-11)
- [x] 將 Keeper 的 PubMed adapter 升級為 v0.6.1 `PubMedSearchClient` API (2026-08-11)
- [x] 確認 Zotero 官方組織未發布 MCP；Registry 收錄的 `54yyyu/zotero-mcp` 為社群 server，且與 Keeper 有 Python namespace 衝突 (2026-08-11)
- [x] 將 Keeper 2.0.0 與 PubMed 0.6.1 合併為單一 `uv pip install` resolver transaction，並以真實雙 server tool listing 驗證 managed venv (2026-08-11)
- [x] 完成 assistant assets / Research Chronicle 同步、521 個 Keeper tests、63 個 PubMed protocol/release tests、84 個 extension tests、mypy、ruff 與 VSIX 內容 smoke (2026-08-11)
- [x] 封閉 malformed collection-name 與 legacy import 的 My Library fail-open 路徑，所有無 collection 寫入皆需明確 root 授權 (2026-08-11)
- [x] 發布 VS Code extension / VSIX `0.6.0`（tag `v0.6.0-ext`）、Keeper
  `2.0.0` 與 PubMed Search MCP `0.6.1` 的 MCP SDK v2 breaking baseline
  (2026-08-11)
- [x] 實作 Zotero 10+ Local API discovery、runtime `/api/local/authorize`、
  Server-ID-bound writes 與 memory-only key (2026-08-12)
- [x] 新增 8 個 `confirm=true` guarded management tools；Keeper 預設 surface
  由 24 增至 32 tools，仍維持 6 resources (2026-08-12)
- [x] 新增 response-bound item object version、full-text library cursor + bulk
  POST optimistic concurrency、三階段 attachment upload、部分成功資訊與
  `/file/view/url` path resolution (2026-08-12)
- [x] 保留 Zotero 7–9 Connector 匯入/PDF 相容路徑，並禁止將 Local API writes
  對非 loopback host 啟用 (2026-08-12)
- [x] 新增 Local API wire tests、真實 loopback simulator smoke、opt-in Zotero live
  smoke，以及單一已檢查 VSIX artifact 的 release workflow guard (2026-08-12)
- [x] 以三段 commits 推送 `main`，並發布 VSIX `0.7.0` / Keeper `2.1.0` / PubMed
  `0.6.1` 的 `v0.7.0-ext`；tag workflow、GitHub Release、Marketplace publish 與
  公開 VSIX checksum 驗證完成 (2026-08-12)
- [x] 將 PubMed Search MCP 固定至正式 v0.6.3 release commit `febf53a`，
  同步 SearchRun/systematic/Chronicle skills 與 hooks (2026-08-19)
- [x] 稽核 Zotero 10 Local API 寫入類別，擴充為 17 個 guarded tools /
  41 個 default tools，並修正 multi-tag delete contract (2026-08-19)
- [x] 新增 Keeper-only GitHub Pages 功能網站；PubMed 仅連結其獨立站
  (2026-08-19)

## Doing
正在完成 Keeper 2.2.0 / VSIX 0.8.0 的全套測試、網站 QA 與可重現
VSIX 封裝。

## Next
- [ ] 發布 `v0.8.0-ext` 前先在 GitHub Settings 啟用 Pages / GitHub Actions
- [ ] 監看 `0.8.0` 的 Local API destructive confirmation 與 file replacement 回饋
- [ ] 保持 PubMed `0.6.3` fixed-source pin 與雙 server SDK v2 相容性 smoke

## Blocked
- [ ] 無
