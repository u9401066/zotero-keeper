# Changelog

All notable changes to the "Zotero + PubMed MCP" extension will be documented in this file.

## [0.5.18] - 2026-03-09

### Fixed

- **Multi-environment installation validation**
  - Re-verified fresh install, upgrade, reinstall, corrupted Python recovery, and idempotent install flows before release
  - Confirmed both new installation and update scenarios complete without extension-managed environment errors

### Changed

- **PubMed access path cleanup**
  - Unified extension-adjacent server code to use the shared PubMed wrapper instead of duplicating direct client access paths

### Test

- **Release verification matrix**
  - `npm run compile`
  - `uv run python tests/test_mac_compatibility.py`
  - `uv run python tests/test_python_env_edge_cases.py`
  - Cleaned `test_mac_compatibility.py` recursive scan helper to avoid `ResourceWarning` noise during verification

## [0.5.17] - 2026-03-04

### Fixed

- **macOS Installation Compatibility** 🍎
  - Fixed VS Code GUI apps on macOS not inheriting shell PATH (Finder/Dock launch)
  - Added `getEnrichedEnv()` to prepend `/opt/homebrew/bin`, `~/.local/bin`, `~/.cargo/bin`, `~/.pyenv/shims` to PATH
  - Added `findFileRecursive()` fallback for tar extraction when `--strip-components` produces unexpected paths
  - Added `findMacPython()` to search well-known macOS Python paths (homebrew, pyenv, Python.framework, Xcode CLI tools)
  - Fixed `checkReadySync()` crash when `uvPath` is empty
  - Fixed error messages referencing "Python 3.11+" → "Python 3.12+"

### Added

- **Cross-platform compatibility tests** (46 tests verifying Mac fix patterns)

## [0.5.16] - 2026-03-04

### Added

- **`@research` Copilot Agent** 🤖
  - Dedicated research assistant at `.github/agents/research.agent.md`
  - Consolidates 8 PubMed skills (quick search, systematic, PICO, paper exploration, fulltext, export, gene/drug, tools reference)
  - Restricted tools: only `editFiles`, `fetch`, `new`, `search` (no terminal/pylance)
  - Auto-deployed on extension activation with legacy upgrade support

### Changed

- **pubmed-search-mcp 0.3.8 → 0.4.4**: citation metrics caching, BM25 ranking, bug fixes
- Updated version references in copilot-instructions.md and research-workflow.md
- Refactored `installCopilotInstructions()` with new `installResearchAgent()` function

## [0.5.15] - 2026-03-04

### Fixed

- **Critical: TCP Port Exhaustion Fix** 🛡️
  - Fixed `metadata_fetcher.py` creating new `httpx.AsyncClient` per DOI query, causing thousands of TIME_WAIT sockets
  - Added module-level shared CrossRef HTTP client with connection pooling (`max_connections=5`, `keepalive_expiry=30`)
  - Added `await self.close()` on `ConnectError` and `TimeoutException` in `client_base.py` to prevent stale connection accumulation
  - These fixes prevent Zotero port 23119 from being overwhelmed by orphaned TCP connections

- **Zotero 8 Annotation Filtering** 🔇
  - Filter out `annotation` itemType from search/list/collection/analytics results (Zotero 8 now returns annotations via Local API)
  - Updated 5 MCP tool files: `basic_read_tools`, `collection_tools`, `analytics_tools`, `resources`, `saved_search_tools`

## [0.5.14] - 2025-06-27

### Added

- **Attachment & Fulltext MCP Tools** 📎
  - `get_item_attachments`: 列出 Zotero 項目的所有附件（含檔案路徑）
  - `get_item_fulltext`: 取得 Zotero 索引的全文內容（PDF/EPUB 純文字）

- **Test Infrastructure** 🧪
  - Mocha + Sinon 測試框架，VS Code mock
  - 5 個模組的單元測試（extension, mcpProvider, statusBar, pythonEnvironment, uvPythonManager）
  - `.mocharc.yml` 配置

- **Logger Module**
  - `logger.ts` 集中式日誌管理
  - `logLevel` 設定選項（debug/info/warn/error）

### Changed

- **Version Unification**: MCP Server 版本統一為 0.5.14（原 1.11.0/1.6.1）
- MCP tools 總計: **32** (新增 2 個 attachment tools)

## [0.5.13] - 2026-02-11

### Fixed

- **EPERM: 重新安裝時無法刪除 python.exe** ⭐
  - MCP server 持有 Python 程序鎖，導致 `unlink python.exe` 失敗 (EPERM)
  - 新增 `killPythonProcesses()`：自動偵測並終止佔用 venv 的程序
    - Windows：WMIC 查找 venv 路徑下的 python.exe PID → `taskkill /F`
    - Unix：`pgrep -f` → `kill -9`
  - 新增 `rmWithRetry()`：最多重試 3 次，指數退避（2s × attempt）
  - `cleanup()` 重寫：先終止程序 → 重試刪除 venv → 重試刪除 uv

### Added

- **NCBI Email 自動偵測** ⭐
  - 不再需要手動設定 `zoteroMcp.ncbiEmail`
  - 自動讀取 `git config user.email` 作為 NCBI API 的 email
  - 優先順序：設定值 > Git email > 空值
  - 新增 `getGitEmail()` 方法（5 秒 timeout，失敗時靜默降級）

### Changed

- **Python 3.11 → Python 3.12** - 環境升級
  - `PYTHON_VERSION` 更新為 `'3.12'`
  - 更好的 async 效能和現代語法支持
- **Pre-commit hooks** 加入開發流程
  - ruff lint/format、detect-secrets、version-sync、no-pip-usage

## [0.5.12] - 2026-02-11

### Fixed

- **CRITICAL: 版本檢查無限升級迴圈** ⭐
  - `verifyReady()` 使用 `__version__` 屬性判斷套件版本，但 `__version__` 與 PyPI 版本不一致
  - zotero-keeper: `__version__`=1.6.1 vs installed=1.11.0
  - pubmed-search-mcp: `__version__`=0.3.6 vs installed=0.3.8
  - **每次啟動都誤判套件過舊，觸發無效升級**
  - 修復：改用 `importlib.metadata.version()` 取得正確的安裝版本

- **損壞 Python binary 導致崩潰**
  - 損壞的 `python.exe` 導致 WinError 216 未處理崩潰
  - 修復：`verifyReady()` 加入 try/catch，偵測損壞後自動刪除 venv 並重建

- **`checkReadySync()` 過度樂觀**
  - 只檢查檔案是否存在，不驗證 binary 是否可執行
  - 修復：實際執行 `python --version` 驗證完整性

- **`needsUpgradeOnly()` 過度樂觀**
  - 同上，只做 `fs.existsSync()` 檢查
  - 修復：加入 binary 可執行驗證

### Updated

- **PubMed Search MCP v0.3.8** - 重大版本更新
  - `search_literature` → `unified_search` 統一搜尋入口
  - 支援多來源搜尋（PubMed、Europe PMC、CORE 等）
  - 自動合併去重搜尋結果
- **Copilot Instructions** - 更新 `search_literature` → `unified_search`
- **Research Workflow Guide** - 更新搜尋步驟與工具名稱

### Changed

- 全面移除 pip，只使用 uv 進行套件管理
- `pythonEnvironment.ts` 移除 pip fallback，改用 uv-only

## [0.5.11] - 2026-01-28

### Updated

- **PubMed Search MCP v0.2.7** - Version sync and stability improvements
- 版本同步更新，準備上傳 Marketplace

## [0.5.10] - 2026-01-27

### Fixed

- 修復 PubMed Search MCP 無法啟動的問題
- 修正啟動模組路徑：`pubmed_search.mcp` → `pubmed_search.presentation.mcp_server`

## [0.5.9] - 2026-01-27

### Fixed

- 修復 uv 建立的 venv 沒有 pip 的問題
- 現在 installPackages() 會自動使用 uv pip 安裝套件
- 提升跨平台相容性

## [0.5.8] - 2026-01-27

### Updated

- PubMed Search MCP 更新至 v0.2.5
  - 修復 server 啟動 bug (session manager 變數名稱)
- 重試修復 Marketplace Repository signing 錯誤

## [0.5.7] - 2026-01-27

### Fixed

- 重試修復 Marketplace Repository signing 錯誤

## [0.5.6] - 2026-01-27

### Fixed

- 修復 Marketplace 驗證失敗問題
- 從 VSIX 移除不必要的 AI 技能資料夾（.agent/, .claude/ 等）
- 套件大小從 601 個檔案減少至約 20 個

## [0.5.5] - 2026-01-27

### Fixed

- 修復 Open VSX 發布問題（Repository signing failed）
- 手動重新發布到 Open VSX

## [0.5.4] - 2026-01-27

### 🔧 Compatibility Update

- **PubMed Search MCP v0.2.4** - Updated to latest release with tool registry refactoring
  - Now provides 26 integrated tools (up from 20)
  - Improved API compatibility

### ✨ Features

- **Full PubMed Integration** - All search and import tools now available:
  - `search_pubmed_exclude_owned` - Search PubMed excluding articles already in Zotero
  - `batch_import_from_pubmed` - Batch import with RCR citation metrics
  - `quick_import_pmids` - Fast PMID import
  - `import_articles` - Unified import from multiple sources

### 🔒 Security

- All npm dependencies updated and audited (0 vulnerabilities)

## [0.5.3] - 2026-01-27

### 🔒 Security Fixes

- Fixed 4 npm security vulnerabilities:
  - `diff` DoS vulnerability in parsePatch/applyPatch (GHSA-73rr-hh4g-fpgx)
  - `lodash` Prototype Pollution in _.unset/_.omit (GHSA-xxjr-mmjv-4gpg)
  - `qs` arrayLimit bypass DoS (GHSA-6rw7-vpxm-498p) - **High severity**
  - `undici` unbounded decompression chain DoS (GHSA-g9mf-h72j-4rw9)

### Updated

- **PubMed Search MCP v0.2.3** (from v0.1.24)
  - Major version bump with improved search capabilities
- **Zotero Keeper MCP v1.11.0** (from v1.10.4)
  - New unified import tools
  - Enhanced PubMed integration

### Added

- **32-bit Windows support** (win32-ia32) - Added uv download for i686-pc-windows-msvc

### Fixed

- Synced MIN_VERSIONS with REQUIRED_PACKAGES to ensure proper version verification
- Updated MCP server version strings in mcpProvider.ts

## [0.5.2] - 2026-01-12

### ✨ New Features

**Enhanced Status Bar with Quick Menu**

- **Version display** in status bar when ready (e.g., "Zotero MCP: Ready v0.5.2")
- **Click for Quick Menu** - Access all features from status bar:
  - 📊 Usage Statistics
  - 🌐 API Status & Management
  - ⚙️ Settings
  - 🧙 Setup Wizard
  - And more...

**Usage Statistics Tracking**

- Track searches performed, articles imported, full-texts accessed
- Session counter
- Beautiful statistics panel with dashboard view
- Data stored locally, never shared

**API Status Dashboard**

- View all 8 connected APIs at a glance:
  - PubMed / NCBI E-utilities
  - Europe PMC
  - CORE (Open Access)
  - Semantic Scholar
  - PubChem
  - NCBI Gene
  - ClinVar
  - Zotero Local API
- Quick access to configure API keys
- Shows rate limits and configuration status

### 📚 Enhanced Tool Documentation

**PubMed Search MCP v0.1.24** - Better documentation for AI agents.

- **Citation Network Tools** with complete workflow guides
- **Vision Search Tools** with 5-step workflow
- Added Reference Repositories learning guide (6 key Python libraries)

---

## [0.5.1] - 2026-01-11

### 🚀 Python 3.12+ Performance Upgrade

**Now requires Python 3.12+** for modern async features and better performance.

#### Updated Dependencies

- **PubMed Search MCP v0.1.22**
  - New core module with unified exception handling
  - Token bucket rate limiting for API compliance
  - Exponential backoff retry with circuit breaker
  - Python 3.12+ type parameter syntax (PEP 695)
  - asyncio.TaskGroup for structured concurrency

- **Zotero Keeper MCP v1.10.4**
  - Updated to Python 3.12+ requirement

#### Python 3.12+ Features Used

```python
# Type parameter syntax (PEP 695)
async def gather_with_errors[T](*coros: Awaitable[T]) -> list[T]: ...

# Frozen dataclass with slots
@dataclass(frozen=True, slots=True)
class ErrorContext:
    tool_name: str | None = None
```

#### Why Python 3.12?

- ⚡ **Performance**: Improved interpreter and async performance
- 🔧 **Modern Syntax**: Type parameter syntax reduces boilerplate
- 🛡️ **Error Handling**: ExceptionGroup for multi-error scenarios
- 🔄 **Structured Concurrency**: asyncio.TaskGroup for reliable cleanup

---

## [0.5.0] - 2026-01-11

### 🎉 Major Update: Simplified Tool Architecture

**PubMed Search MCP v0.1.20** - True tool consolidation from 34 to **19 tools** (-44%)!

#### Simplified for Better AI Experience

Now there's just **one main entry point**: `unified_search`
- 🔍 Auto-analyzes query complexity and intent
- 🌐 Auto-searches multiple sources (PubMed, OpenAlex, Europe PMC, CORE)
- 🔄 Auto-merges and deduplicates results
- 📊 Smart ranking by relevance, impact, or recency

#### Removed Redundant Tools (Merged into unified_search)

- ~~search_literature~~ → Use `unified_search`
- ~~search_europe_pmc~~ → Auto-integrated
- ~~search_core~~ → Auto-integrated
- ~~search_openalex~~ → Auto-integrated
- ~~expand_search_queries~~ → Auto-executed when results < 10
- ~~merge_search_results~~ → Auto-executed
- ~~get_article_fulltext_links~~ → Merged into get_fulltext
- ~~analyze_fulltext_access~~ → Auto-handled

#### The New 19 Core Tools

| Category | Tools |
|----------|-------|
| Search | `unified_search`, `parse_pico` |
| Query | `generate_search_queries`, `analyze_search_query` |
| Articles | `fetch_article_details`, `find_related/citing/references`, `get_citation_metrics` |
| Export | `prepare_export` |
| NCBI | `search_gene/compound`, `get_gene/compound_details`, `search_clinvar`, `get_*_literature` |
| Citation | `build_citation_tree`, `suggest_citation_tree` |

### Updated

- **Zotero Keeper MCP v1.10.3** - Synced with simplified architecture

### Benefits

- 🤖 **Simpler for AI Agents** - Fewer decisions, one main entry point
- ⚡ **Same Power** - All features preserved through integration
- 📖 **Cleaner Docs** - Less confusion about which tool to use

## [0.4.4] - 2026-01-11

### Updated

- **PubMed Search MCP v0.1.19** 🎉
  - All 34 tools now use InputNormalizer for agent-friendly parameter handling
  - Accepts flexible parameter types: Union[int, str], Union[bool, str]
  - Fixed all mypy type annotation errors (77 errors resolved)
  - Fixed all ruff linting errors (12 errors resolved)
  - Stable release ready for production use
- **Zotero Keeper MCP v1.10.2**
  - Synced with latest PubMed Search MCP improvements
  - Added research documentation on Agent-MCP collaboration patterns

### Technical Improvements

- Type-safe with strict mypy checking
- Consistent parameter normalization across all tools
- Better error handling and validation
- Improved code quality and maintainability

## [0.4.3] - 2025-12-26

### Fixed
- **🐛 Critical: Extension update breaks existing installation**
  - Previously, `verifyReady()` only checked if packages could be imported, not their versions
  - Extension updates requiring newer package versions would silently fail at runtime
  - Now performs version verification against `MIN_VERSIONS` requirements
  - Auto-upgrades packages when version requirements increase

- **🔒 Security: Improved Python script execution**
  - Version check script now uses temp file instead of command-line string escaping
  - Eliminates potential shell injection risks from malformed package versions

### Added
- **Linux ARM64 support** - Now supports Raspberry Pi and ARM-based Linux devices
- **Rich status bar tooltip** - Hover over status bar to see:
  - Python environment status
  - Package installation status
  - Zotero connection status with host:port
  - Quick action links (Settings, Check Connection, Full Status)
- **New command**: `zoteroMcp.showQuickStatus` - Refresh status bar info

### Changed
- Updated `pubmed-search-mcp` requirement from `>=0.1.15` to `>=0.1.18`
  - New features: Europe PMC, CORE API, NCBI Extended (Gene/PubChem/ClinVar)
  - Now provides 35+ MCP tools (up from ~20)
- Package installation now uses `--upgrade` flag to ensure version requirements
- Added `packaging` dependency for proper version comparison
- `ensureReady()` now auto-upgrades packages instead of triggering full reinstall
- Removed unused `exec` import from child_process
- Check Connection now shows brief status bar message instead of popup when connected
- Status bar click refreshes connection status (like Git extension)

## [0.4.2] - 2025-12-26

### Fixed
- **🐛 Critical: Python environment priority bug**
  - Previously, extension always used system Python first, ignoring `useEmbeddedPython` setting
  - Now correctly prioritizes uv-managed Python 3.11 when `useEmbeddedPython=true` (default)
  - This ensures consistent behavior regardless of user's system Python version
  - Users without Python installed can now use the extension out-of-box
  - Users with incompatible Python versions (e.g., 3.9, 3.14) won't encounter errors

### Changed
- Improved error handling with fallback to system Python if uv fails
- Better user feedback when Python environment setup fails
- Added "Enable Embedded Python" option in error dialogs

## [0.4.1] - 2025-12-22

### Fixed
- **Skills Installation Safety**: Never overwrite user's existing `copilot-instructions.md`
- Automatic skill installation now checks for our marker before modifying
- Manual `installSkills` command preserves user's custom configurations
- Only updates files that were originally installed by this extension

## [0.4.0] - 2025-12-22

### Added
- **🎯 Copilot Research Skills** ⭐
  - Auto-installs workflow guides on first activation
  - Teaches Copilot the correct research workflow
  - `resources/skills/copilot-instructions.md` - Core instructions
  - `resources/skills/research-workflow.md` - Detailed workflow guide
- **New Command**: `Zotero MCP: Install Copilot Research Skills`
  - Manually install/update workflow guides
  - Creates `.github/copilot-instructions.md` in workspace
  - Creates `.github/zotero-research-workflow.md`

### Changed
- **Enhanced MCP Tool Descriptions**:
  - `search_pubmed_exclude_owned`: Added complete workflow guidance
  - `quick_import_pmids`: Emphasizes asking Collection first
  - `list_collections`: Marked as "must use before import"
  - `get_session_pmids`: Added avoid-repeat-search guidance
  - `get_cached_article`: Prioritize cache usage hint

### Updated
- PubMed Search MCP server to v0.1.16
  - Session Tools for PMID persistence
  - Multi-source search (Semantic Scholar, OpenAlex)
- Zotero Keeper MCP server to v1.10.1

## [0.3.1] - 2025-12-15

### Changed
- **Switched to uv for Python management** ⭐
  - Replaced embedded Python with uv-managed environment
  - uv automatically downloads Python 3.11 if needed
  - 10-100x faster package installation
  - More reliable dependency resolution
  - Smaller extension size (~30KB, uv downloaded on first run ~10MB)

### Fixed
- **Windows installation error**: Fixed "Failed to set up Python environment" error
  - `zotero-keeper` package is now available on PyPI
  - Simplified package names (removed `[all]` extras that caused pip resolution issues)
  - Added mutex to prevent concurrent setup attempts
- Fixed pip corruption from concurrent package downloads
- Fixed `pubmed-search-mcp` missing `mcp` dependency (now in core deps)

### Updated
- Zotero Keeper MCP server to v1.10.0
- PubMed Search MCP server to v0.1.15

### Removed
- Removed old `embeddedPython.ts` (replaced by `uvPythonManager.ts`)
- Removed bundled wheel scripts (no longer needed)

## [0.3.0] - 2025-12-14

### Added
- **Self-contained mode**: Extension can now download and manage its own Python environment
- One-click setup wizard for non-technical users
- Embedded Python support using python-build-standalone (Python 3.11)
- Platform support: Windows x64, Linux x64, macOS x64/ARM64
- New setting `zoteroMcp.useEmbeddedPython` (default: true)
- New command `Zotero MCP: Reinstall Embedded Python`
- Welcome walkthrough for first-time users

## [0.2.0] - 2025-12-13

### Added
- Status bar indicator showing extension state
- Improved error messages and troubleshooting hints
- Configuration for NCBI email (recommended for PubMed API)

### Changed
- Better Python environment detection
- Improved package installation reliability

## [0.1.0] - 2025-12-12

### Added
- Initial release
- Zotero Keeper MCP server integration
  - Search Zotero library
  - Add references (from PubMed, DOI, or manual)
  - Manage collections
  - Batch import from PubMed
- PubMed Search MCP server integration
  - Literature search with MeSH expansion
  - PICO question parsing
  - Citation metrics (RCR)
  - Export in RIS/BibTeX formats
- Automatic Python environment detection
- Auto-install of required packages
- Status bar indicator
- Configuration settings for Zotero connection
