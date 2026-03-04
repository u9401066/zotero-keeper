# Active Context

> 🎯 目前工作焦點與下一步行動

## 當前狀態: v0.5.15 已完成 ✅

### 已完成 (2026-03-04)

1. ✅ Critical Async/Await Bug Fixes (12 call sites, 6 files)
   - `fetch_pubmed_articles`, `fetch_details`, `search_raw`, `get_citation_metrics` 全部加上 await
   - `pubmed/__init__.py` 三個 wrapper 函數改為 async
   - 影響工具: batch_import, import_from_pmids, quick_import, search_pubmed, check_articles

2. ✅ `list_collections()` → `get_collections()` (8 處)
   - ZoteroClient 方法名修正

3. ✅ Collection Name Resolution Fix (3 處)
   - `col.get("name")` → `col.get("data",{}).get("name","")` 修正資料結構存取

4. ✅ Zotero 8 Annotation Filtering (5 tool files + resources)
   - 過濾 `annotation` itemType（Zotero 8 新增的 PDF 標註項目）

5. ✅ TCP Port Exhaustion Fix
   - `metadata_fetcher.py` 使用共享 httpx.AsyncClient 避免連線洩漏

6. ✅ VS Code Extension v0.5.15
   - Zotero 8 相容性文件、npm 依賴更新

7. ✅ `.vscode/mcp.json` 開發用 MCP 設定

---

## 版本狀態

| 元件 | 版本 | 狀態 |
|------|------|------|
| pubmed-search-mcp | v0.4.4 | installed ✅ |
| zotero-keeper MCP | v0.5.15 | ready to push 🚀 |
| VS Code Extension | v0.5.15 | ready to push 🚀 |

---
*Updated: 2026-03-04*
*工作模式: Release*
