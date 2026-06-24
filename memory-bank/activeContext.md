# Active Context

## 當前焦點
發布 VS Code extension v0.5.35 / Zotero Keeper 1.14.0：新增 `import_pdf` 工具，可在現有 Local/Connector 架構內（無需 Web API key）匯入本機 PDF — metadata 模式（建立父項目並掛 PDF）或 auto-recognize 模式（讓 Zotero 從 PDF 抽出 metadata 建立項目）。

## 相關檔案
- `mcp-server/src/zotero_mcp/infrastructure/zotero_client/client_base.py` - `_request_raw` 支援二進位 body + per-request headers
- `mcp-server/src/zotero_mcp/infrastructure/zotero_client/client_write.py` - `save_attachment`、`save_standalone_attachment`、`save_items(session_id=...)`
- `mcp-server/src/zotero_mcp/infrastructure/mcp/unified_import_tools.py` - `import_pdf` 工具（重用型別感知對應）
- `vscode-extension/src/zoteroKeeperPackage.ts` - keeper archive 指向 `v0.5.35-ext`，`ZOTERO_KEEPER_VERSION` = 1.14.0
- `docs/ZOTERO_LOCAL_API.md` / `docs/tools-reference.md` - Connector 附件端點與 import_pdf 說明
- `vscode-extension/src/zoteroKeeperPackage.ts` - keeper archive 指向 `v0.5.34-ext`，`ZOTERO_KEEPER_VERSION` = 1.13.0
- `vscode-extension/src/mcpProvider.ts` - 改用 `ZOTERO_KEEPER_VERSION` 常數避免版本漂移
- `CHANGELOG.md` / `vscode-extension/CHANGELOG.md` / `vscode-extension/README.md` - 版本說明

## 待解決問題
- [x] mcp-server 單元測試 464 passing、ruff clean
- [x] extension tsc/eslint/mocha 82 passing、version-sync OK (0.5.34)
- [ ] 推送 `main` 並推送 `v0.5.34-ext` tag 觸發 VSIX 更新

## 上下文
- 參考 RoadToDream/ZotMeta 的 metadata 完整性做法，但改為「匯入時即型別感知」而非事後補。
- extension 透過下載 `v{X}-ext.tar.gz#subdirectory=mcp-server` 安裝 keeper，故 metadata 改進需透過 `-ext` release 才會送達使用者。
- `finalize_item_for_schema()` 確保任何類型不支援的欄位改寫進 Zotero `Extra`，避免 Connector API 靜默丟棄 metadata。

## 更新時間
2026-06-24
