# Active Context

## 當前焦點
發布 VS Code extension v0.5.34 / Zotero Keeper 1.13.0：讓 PubMed/RIS → Zotero 匯入具備型別感知，正確對應書本、章節、研討會論文、網頁、軟體 repo、資料集等所有 Zotero 類型，且不支援欄位一律保存到 `Extra` 不遺失。

## 相關檔案
- `mcp-server/src/zotero_mcp/infrastructure/mappers/zotero_schema.py` - 14 種類型欄位註冊表 + detect_item_type + finalize_item_for_schema
- `mcp-server/src/zotero_mcp/infrastructure/mcp/unified_import_tools.py` - 型別感知 `_unified_article_to_zotero` 與擴充 RIS parser
- `mcp-server/src/zotero_mcp/infrastructure/mappers/pubmed_mapper.py` - url/accessDate/libraryCatalog + 原生 PMID 抽取
- `mcp-server/src/zotero_mcp/infrastructure/mcp/search_helpers.py` / `zotero_client/client_write.py` - 原生 PMID 去重
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
