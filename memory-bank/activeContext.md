# Active Context

> 🎯 目前工作焦點與下一步行動

## 當前狀態: Extension tool/runtime 修正完成，待決定是否發版 ✅

### 最新完成 (2026-03-18)

1. ✅ 修正 extension 安裝來源
   - `zotero-keeper` 改由 GitHub tarball 安裝，避開過舊 PyPI 1.11.0
   - `pubmed-search-mcp` 最低版本升到 `0.4.5`

2. ✅ 修正 venv 復原邏輯
   - `UvPythonManager` 現在會驗證 Python 是否為 3.12+
   - 既有 venv 若缺 binary、損壞、或版本過舊，先刪除再重建

3. ✅ 驗證完成
   - `npm test` 通過（47 passing）
   - `test_mac_compatibility.py` 通過（48 passed）
   - 乾淨 venv 實測：`batch_import_from_pubmed` / `import_from_pmids` 均成功
   - 未重現 `Coroutine object is not iterable`

### 已完成 (2026-03-09)

1. ✅ Repo hygiene + docs sync
   - 清掉 pre-commit / test output artifacts
   - 文件全面同步為 uv-first、Marketplace-only

2. ✅ MCP server entrypoint cleanup
   - `server.py` 輸出真實 `FastMCP` instance
   - 移除死碼 `register_smart_tools()`

3. ✅ Shared collection resolution
   - 新增 `collection_support.py`
   - `pubmed_tools.py` / `unified_import_tools.py` / `batch_tools.py` 共用 collection resolution

4. ✅ PubMed import helper consolidation
   - `pubmed_tools.py` 抽出 `_fetch_pubmed_details()`
   - `pubmed_tools.py` 抽出 `_build_article_import_items()`
   - `import_ris_to_zotero` / `import_from_pmids` / `quick_import_pmids` 不再各自維護同一份成功回應與 detail-fetch 流程

5. ✅ Shared saved_to helper
   - `collection_support.py` 新增 `attach_saved_to_info()`
   - `unified_import_tools.py` 與 `pubmed_tools.py` 使用同一份 collection destination response helper

6. ✅ Reuse audit
   - 確認 `pubmed_tools.py` 內的 PMID detail wrapper 曾重複 `infrastructure.pubmed.fetch_pubmed_articles()`
   - 已收斂回既有 shared pubmed integration wrapper

7. ✅ Full PubMed wrapper convergence
   - `infrastructure.pubmed` 新增 `is_pubmed_available()` 與 `search_pubmed_raw()`
   - `search_tools.py` 與 `pubmed_tools.py` 都改用 shared pubmed wrapper
   - MCP tool 層已不再直接 import / instantiate `PubMedClient`

8. ✅ VS Code Extension 0.5.18 release verification
   - `npm run compile` 通過
   - `test_mac_compatibility.py` 46 tests 通過且已清理 `ResourceWarning`
   - `test_python_env_edge_cases.py` 20/20 通過，覆蓋新安裝、升級、重裝、損壞 Python 恢復
   - 版本同步檢查通過：`0.5.18`

### 目前版本狀態

| 元件 | 版本 | 狀態 |
| ---- | ---- | ---- |
| pubmed-search-mcp | v0.4.5 minimum | verified ✅ |
| zotero-keeper MCP | 0.5.16 via GitHub tarball | verified ✅ |
| VS Code Extension | v0.5.18 | code updated, not released |

### 下一步

- 可選下一步：決定是否發新版 extension，讓 Marketplace 使用者拿到新的安裝來源與 recovery 邏輯

---
*Updated: 2026-03-18*
*工作模式: Refactor*
