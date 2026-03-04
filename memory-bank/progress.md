# Progress (Updated: 2025-06-27)

## Done

### v0.5.14 - Attachment Tools + Version Unification (2025-06-27)
- ✅ `get_item_attachments` + `get_item_fulltext` MCP tools (2 new)
- ✅ DAL: `client_read.py` 新增 `get_item_fulltext()` + `resolve_attachment_path()`
- ✅ 15 unit tests for attachment tools
- ✅ VS Code test infrastructure (Mocha + Sinon, 5 modules)
- ✅ Structured logging (`logging_config.py` + `logger.ts`)
- ✅ Pre-commit quality gate (ruff, pytest, trailing whitespace)
- ✅ Version unification: MCP Server 1.x → 0.5.14
- ✅ Zotero Plugin Spec (HTTP Bridge design)
- ✅ Total MCP tools: 32

### v0.5.13 - EPERM Fix + Python 3.12 (2025-06-26)
- ✅ EPERM error handling (kill Python processes before reinstall)
- ✅ NCBI email auto-detect (git config user.email)
- ✅ Python 3.12 support
- ✅ Pre-commit hooks

### v0.5.12 - 關鍵 Bug 修復 + PubMed MCP v0.3.8 (2025-06-25)
- ✅ **CRITICAL**: 修復版本檢查無限升級迴圈（`__version__` → `importlib.metadata`）
- ✅ 修復損壞 Python binary 導致 WinError 216 崩潰
- ✅ 強化 `checkReadySync()` 和 `needsUpgradeOnly()` 實際驗證 binary
- ✅ PubMed Search MCP 更新至 v0.3.8（`search_literature` → `unified_search`）
- ✅ 全面移除 pip，只使用 uv
- ✅ 新增 pytest-xdist 多核測試
- ✅ 新增 uv-enforcer skill
- ✅ 20 項 edge case 測試全部通過（兩輪驗證）
- ✅ Copilot instructions 和 research-workflow 更新

### v0.5.11 - PubMed Search MCP v0.2.7 (2026-01-28)
- ✅ 版本同步更新

### v0.5.9 - VS Code Extension 修復 (2026-01-27)
- ✅ 修復 uv venv 沒有 pip 的問題
- ✅ pythonEnvironment.ts 自動偵測並使用 uv pip

### v0.5.8 - PubMed Search MCP v0.2.5 更新 (2026-01-27)
- ✅ 更新 pubmed-search-mcp 子模組到 v0.2.5
- ✅ 修復 server 啟動 bug (session manager 變數名稱)

### v0.5.6 - Marketplace 驗證修復 (2026-01-27)
- ✅ 修復 Marketplace 驗證失敗問題
- ✅ 排除不必要的 AI skill 資料夾 (.agent/, .claude/, .cursor/ 等)
- ✅ 套件大小從 601 檔案 (674KB) 減少到 20 檔案 (46KB)

### v0.5.4 - 安全性與相容性更新 (2026-01-27)
- ✅ 修復 4 個 npm 安全漏洞 (diff, lodash, qs, undici)
- ✅ 新增 32-bit Windows (win32-ia32) 平台支援
- ✅ 更新 pubmed-search-mcp 到 v0.2.4

### v0.5.3 - 更新 pubmed-search-mcp v0.2.3 (2026-01-27)
- ✅ 更新 zotero-keeper MCP 到 v1.11.0

### v0.1.25 - OpenURL / 機構訂閱整合 (2026-01-12)
- ✅ 實作 OpenURL/機構訂閱整合功能
- ✅ 新增 `sources/openurl.py` 模組 - OpenURL 建構器
- ✅ 整合 OpenURL 到 `unified_search` 輸出

## Doing

- 等待 Marketplace v0.5.9 驗證結果（Repository signing 問題）

## Next

- 解決 Marketplace Repository signing 問題（可能需聯繫 Microsoft）
- Open VSX 發布（需要 Open VSX token）
- 測試 v0.5.9 在 Windows 的安裝流程
