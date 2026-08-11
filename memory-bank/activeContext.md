# Active Context

## 當前焦點
發布 breaking release：Zotero Keeper `2.0.0` 與 VS Code extension / VSIX
`0.6.0`。兩個 bundled MCP servers 都必須在同一個 extension-managed venv
切換到 MCP SDK v2；SDK v1 與 v2 不相容，不允許只升級其中一套。

## 相關檔案
- `mcp-server/pyproject.toml` - Keeper `2.0.0` 與 `mcp>=2.0,<3`
- `mcp-server/src/zotero_mcp/infrastructure/mcp/server.py` - SDK v2
  `MCPServer` 組裝與 Keeper 的 24 tools / 6 resources
- `mcp-server/src/zotero_mcp/infrastructure/pubmed/__init__.py` - PubMed
  v0.6.1 公開 Python API 整合
- `external/pubmed-search-mcp` - upstream v0.6.1 commit
  `ad85dde08269dbb59eff69d2e92f4d3c5b5bf21d`（45 tools，含 Research
  Chronicle）
- `vscode-extension/src/uvPythonManager.ts` / `pythonEnvironment.ts` - 同一
  managed venv 的 package-set 升級、來源與版本驗證
- `vscode-extension/src/zoteroKeeperPackage.ts` / `pubmedSearchPackage.ts` -
  Keeper `2.0.0` 與 PubMed `0.6.1` reproducible pins
- `vscode-extension/package.json` / `CHANGELOG.md` - VSIX `0.6.0` 發布面
- `README.md` / `README.zh-TW.md` / `.github/**` - MCP v2、Research
  Chronicle、Zotero MCP 生態與安全邊界說明

## 待解決問題
- [x] VSIX `0.5.35` / Keeper `1.14.0`（`import_pdf`）已完成發布
- [x] 盤點 PubMed Search MCP v0.6.1 與 MCP SDK v2 breaking surface
- [x] Keeper server 與 PubMed Python client adapter 遷移至 SDK v2 API
- [x] 確保兩套 MCP package 以單一解析/安裝單元升級至同一 managed venv
- [x] 同步 bundled assistant assets，完成 full checks 與 VSIX content smoke
- [ ] 分段提交、推送 `main` 與 `v0.6.0-ext` tag，驗證發布 workflow

## 上下文
- MCP SDK v2 以 `mcp.server.MCPServer` 取代 v1 `FastMCP` surface；Keeper
  與 PubMed 共同約束 `mcp>=2,<3`。
- PubMed Search MCP v0.6.1 提供 45 個 tools；Research Chronicle 的
  `build_research_chronicle` / `read_research_chronicle` 取代舊 timeline
  公開工具面。
- 截至 2026-08-11，Zotero 官方組織未發布 MCP server。
  `54yyyu/zotero-mcp` 是 MCP Registry 收錄的社群 server，不是 Zotero
  官方產品；它與 Keeper 使用相同的 `zotero_mcp` Python namespace，禁止安裝
  在同一 managed venv，若評估使用必須採獨立環境與獨立 server 設定。
- Keeper 的 local/Connector 模式以使用者桌面 Zotero 為信任邊界，可在不使用
  Zotero Web API key 的情況讀取本地資料並執行 Connector 匯入。任何可遠端存取
  的 authenticated service 模式都必須另外處理 token、tenant、bind host、
  origin/host 驗證與資料目錄隔離，不可沿用 local-mode 假設。
- Collection name 解析必須取得非空 Zotero key；malformed response、取消、無
  elicitation capability 與所有未確認 destination 都必須 fail closed。即使開啟
  legacy PubMed tools，也必須以 `allow_library_root=true` 攜帶 root 授權。

## 更新時間
2026-08-11 16:44 UTC
