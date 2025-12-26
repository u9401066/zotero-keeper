# Changelog

All notable changes to the "Zotero + PubMed MCP" extension will be documented in this file.

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
