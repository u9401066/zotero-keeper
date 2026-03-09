# Active Context

> 🎯 目前工作焦點與下一步行動

## 當前狀態: 結構清理第四輪完成 ✅

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
   - `pubmed_tools.py` 抽出 `_attach_saved_to_info()`
   - `pubmed_tools.py` 抽出 `_build_article_import_items()`
   - `import_ris_to_zotero` / `import_from_pmids` / `quick_import_pmids` 不再各自維護同一份成功回應與 detail-fetch 流程

### 目前版本狀態

| 元件 | 版本 | 狀態 |
| ---- | ---- | ---- |
| pubmed-search-mcp | v0.4.4 | installed ✅ |
| zotero-keeper MCP | repo cleanup in progress | working tree pending commit |
| VS Code Extension | v0.5.17 published | stable ✅ |

### 下一步

- 第五輪：評估 `unified_import_tools.py` 與 `pubmed_tools.py` 間剩餘的回應組裝／article conversion 重複

---
*Updated: 2026-03-09*
*工作模式: Refactor*
