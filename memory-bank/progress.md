# Progress (Updated: 2026-01-12)

## Done

### v0.1.25 - OpenURL / 機構訂閱整合 (2026-01-12)
- ✅ 實作 OpenURL/機構訂閱整合功能
- ✅ 新增 `sources/openurl.py` 模組 - OpenURL 建構器
- ✅ 新增 `mcp/tools/openurl.py` - 4 個 MCP 工具
  - `configure_institutional_access` - 設定機構 resolver
  - `get_institutional_link` - 產生 OpenURL 連結
  - `list_resolver_presets` - 列出 16 個預設機構
  - `test_institutional_access` - 測試連線
- ✅ 整合 OpenURL 到 `unified_search` 輸出（自動顯示 🏛️ Library 連結）
- ✅ VS Code Extension 設定 UI
  - `zoteroMcp.openUrlResolver` - 自訂 URL
  - `zoteroMcp.openUrlPreset` - 下拉選單選機構
- ✅ 支援 16 個預設機構：
  - 🇹🇼 台灣：ntu, ncku, nthu, nycu
  - 🇺🇸 美國：harvard, stanford, mit, yale
  - 🇬🇧 英國：oxford, cambridge
  - 🔧 通用：sfx, 360link, primo
  - 🆓 測試：test_free, worldcat, pubmed_linkout
- ✅ 新增 `tests/test_openurl.py` - 12 個單元測試全部通過
- ✅ 網路連線測試：Harvard resolver 公開可用 (HTTP 200)

### 之前完成
- ✅ v0.1.24 - Tool documentation 增強
- ✅ v0.1.23 - Vision-to-Literature Search 圖片搜尋
- ✅ VS Code Extension v0.5.2 發布

## Doing

（無進行中任務）

## Next

- 發布 pubmed-search-mcp v0.1.25 到 PyPI
- 發布 VS Code Extension v0.5.3
- 撰寫 OpenURL 使用文檔
- 測試更多機構 URL 是否正確
