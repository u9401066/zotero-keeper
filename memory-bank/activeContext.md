# Active Context

## 當前焦點
準備 Zotero Keeper `2.2.0` 與 VS Code extension / VSIX `0.8.0`。
本次擴充 Zotero 10+ Local API 的任務導向 lifecycle、tag、stored-file
replacement 與 batch full-text 工具，將 PubMed Search MCP 固定至正式
`0.6.3` release commit，並新增 Keeper GitHub Pages 功能網站。`v0.7.0-ext`
仍是目前已發布的 stable release。

## 相關檔案
- `mcp-server/pyproject.toml` - Keeper `2.2.0` 與 `mcp>=2.0,<3`
- `mcp-server/src/zotero_mcp/infrastructure/mcp/server.py` - SDK v2
  `MCPServer` 組裝與 Keeper 的 41 tools / 6 resources
- `mcp-server/src/zotero_mcp/infrastructure/zotero_client/client_local.py` -
  Zotero 10+ Local API discovery、runtime authorization、Server-ID、local version
  與三階段 attachment upload
- `mcp-server/src/zotero_mcp/infrastructure/mcp/local_api_tools.py` - 17 個
  guarded Local API tools（1 auth + 16 confirmed mutations）
- `mcp-server/src/zotero_mcp/infrastructure/pubmed/__init__.py` - PubMed
  v0.6.3 公開 Python API 整合
- `external/pubmed-search-mcp` - upstream v0.6.3 release commit
  `febf53a8ff1ee253a625869ba251365f73a23c68`（45 tools，含 SearchRun 與
  Research Chronicle）
- `vscode-extension/src/uvPythonManager.ts` / `pythonEnvironment.ts` - 同一
  managed venv 的 package-set 升級、來源與版本驗證
- `vscode-extension/src/zoteroKeeperPackage.ts` / `pubmedSearchPackage.ts` -
  Keeper `2.2.0` 與 PubMed `0.6.3` reproducible pins；兩者仍由同一 resolver
  transaction 管理
- `vscode-extension/package.json` / `CHANGELOG.md` - VSIX `0.8.0` 發布面
- `docs/index.html` / `.github/workflows/pages.yml` - Keeper 功能網站與 Pages 部署
- `.github/workflows/publish-extension.yml` / `scripts/check_version_sync.py` -
  同一個已檢查 VSIX artifact 的 Marketplace / GitHub Release 發布 invariant
- `README.md` / `README.zh-TW.md` / `.github/**` - MCP v2、Research
  Chronicle、Zotero MCP 生態與安全邊界說明

## 待解決問題
- [x] VSIX `0.5.35` / Keeper `1.14.0`（`import_pdf`）已完成發布
- [x] VSIX `0.6.0` / Keeper `2.0.0` / PubMed `0.6.1` 已於
  2026-08-11 完成 MCP SDK v2 breaking release
- [x] 實作 Zotero 10+ `/api/local/authorize` 與每次寫入的 Server-ID 驗證；
  runtime key 僅存記憶體
- [x] 新增 collection/item/note/saved-search/file/full-text 共 8 個 guarded tools，
  Keeper 預設工具面由 24 增為 32
- [x] 實作 response-bound item object version、full-text library cursor + bulk
  POST optimistic concurrency、三階段檔案 upload、真實 loopback simulator smoke
  與 opt-in Zotero live smoke
- [x] 保留 Zotero 7–9 的 Connector 匯入相容路徑與 managed-venv 單一 resolver
  invariant
- [x] 同步最終 assets、分段提交、推送 `main` 與 `v0.7.0-ext` tag；GitHub
  Actions `31560040966` 已驗證並把同一 VSIX artifact 發布至 Marketplace 與
  GitHub Release（SHA256
  `11df8af38a6fd804691262dc6182c5ba6f345f5a5cb1c615b218720693eb6c1f`）
- [x] 稽核 Zotero 10 寫入類別與 Keeper 公開 surface，補齊 9 個
  任務工具並修正 multi-tag delete wire contract
- [x] 將 PubMed 固定至正式 0.6.3 `febf53a`，同步新版 skills/hooks
- [ ] 完成 Keeper 2.2.0 / VSIX 0.8.0 全套 tests、網站視覺 QA 與 VSIX 產物檢查

## 上下文
- MCP SDK v2 以 `mcp.server.MCPServer` 取代 v1 `FastMCP` surface；Keeper
  與 PubMed 共同約束 `mcp>=2,<3`。這個相容性基線已由 `v0.6.0-ext` 發布，
  `v0.7.0-ext` 不改變 PubMed pin。
- PubMed Search MCP v0.6.3 提供 45 個 tools；`read_session` 可查閱/重播
  SearchRun，Research Chronicle 的
  `build_research_chronicle` / `read_research_chronicle` 取代舊 timeline
  公開工具面。
- 截至 2026-08-11，Zotero 官方組織未發布 MCP server。
  `54yyyu/zotero-mcp` 是 MCP Registry 收錄的社群 server，不是 Zotero
  官方產品；它與 Keeper 使用相同的 `zotero_mcp` Python namespace，禁止安裝
  在同一 managed venv，若評估使用必須採獨立環境與獨立 server 設定。
- Keeper 的 local/Connector 模式以使用者桌面 Zotero 為信任邊界。Zotero 10+
  mutation preview 前先由 response-bound read/authorize 取得 Server-ID，並以
  `expected_server_id` 放進 proposal；所有 confirmed mutation 都要求該 identity。
  若 authorization identity 不同，必須重新 read、preview 與取得核准。runtime key
  不寫入設定或 log。
- Exact update/single delete 使用 response-bound object version；tag/full-text 批次
  操作使用 library cursor；stored-file replacement 額外綁定 attachment
  version 與 old MD5。所有 cursor 不得與 Web API 或其他 profile 混用。
- `localhost:23119` 是 loopback trust boundary，禁止 bind、proxy 或 forward 給其他
  主機。任何可遠端存取的 authenticated service 模式都必須另行設計 authentication、
  tenant、Host/Origin 與資料隔離，不可沿用 local-mode 假設。
- Collection name 解析必須取得非空 Zotero key；malformed response、取消、無
  elicitation capability 與所有未確認 destination 都必須 fail closed。即使開啟
  legacy PubMed tools，也必須以 `allow_library_root=true` 攜帶 root 授權。

## 更新時間
2026-08-19 UTC
