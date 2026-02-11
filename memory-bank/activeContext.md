# Active Context

> 🎯 目前工作焦點與下一步行動

## 當前狀態: VS Code Extension v0.5.12 準備發布 🚀

### 已完成 (2026-02-11)

1. ✅ PubMed Search MCP 更新至 v0.3.8
   - uvPythonManager.ts, mcpProvider.ts, pyproject.toml 版本更新
   - Instructions 更新: `search_literature` → `unified_search`

2. ✅ pytest-xdist 多核測試
   - 強制使用 `-n auto --dist worksteal`

3. ✅ pip → uv 全面遷移
   - 16+ 檔案中移除所有 pip 參考
   - pythonEnvironment.ts 移除 pip fallback
   - 新增 uv-enforcer skill

4. ✅ **CRITICAL Bug Fixes (uvPythonManager.ts)**
   - 修復版本檢查無限升級迴圈（改用 `importlib.metadata.version()`）
   - 修復損壞 Python binary 崩潰（auto-detect + auto-repair）
   - 強化 `checkReadySync()` 和 `needsUpgradeOnly()` 驗證
   - 20/20 edge case tests 通過（兩輪驗證）

---

## 版本狀態

| 元件 | 版本 | 狀態 |
|------|------|------|
| pubmed-search-mcp | v0.3.8 | PyPI ✅ |
| zotero-keeper MCP | v1.11.0 | PyPI ✅ |
| VS Code Extension | v0.5.12 | 準備發布 🚀 |

---
*Updated: 2026-02-11*
*工作模式: Release*
