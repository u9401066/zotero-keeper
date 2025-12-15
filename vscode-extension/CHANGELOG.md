# Changelog

All notable changes to the "Zotero + PubMed MCP" extension will be documented in this file.

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
