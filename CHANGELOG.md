# Changelog

All notable changes to Zotero Keeper will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

## [Unreleased]

### Planned
- Phase 3: Smart features (duplicate detection, validation)
- Phase 4: Multi-user support

---

## [1.4.0] - 2024-12-12

### 📥 PubMed Import Integration (Redesigned)

Redesigned PubMed integration to complement `pubmed-search-mcp` instead of duplicating.

### Added
- **Import Tools** (focused on Zotero import only)
  - `import_ris_to_zotero`: Import RIS format citations (works with any RIS source)
  - `import_from_pmids`: Direct PMID import (requires pubmed extra)
- **RIS Parser**: Full RIS format parsing with field mapping
  - Supports: JOUR, BOOK, CHAP, CONF, THES, RPRT, ELEC types
  - Maps: Title, Authors, Year, Journal, DOI, Abstract, Keywords

### Changed
- **Architecture**: Separated concerns between search (pubmed-search-mcp) and storage (zotero-keeper)
- **Workflow**: Recommended 2-MCP workflow for best experience

### Removed
- `search_pubmed_and_import`: Use pubmed-search-mcp's `search_literature` instead
- `get_pubmed_article_details`: Use pubmed-search-mcp's `fetch_article_details` instead

### Recommended Workflow
```
1. pubmed: search_literature("query") → PMIDs
2. pubmed: prepare_export(pmids, format="ris") → RIS text
3. keeper: import_ris_to_zotero(ris_text) → Zotero
```

---

## [1.3.0] - 2024-12-12 (Superseded)

### 🔬 PubMed Integration (Initial)

Initial PubMed integration - superseded by v1.4.0 redesign.

### Added
- PubMed Integration Module (pubmed_tools.py)
- Optional dependencies for PubMed features

---

## [1.2.0] - 2024-12-12

### 🛠️ Core MCP Tools (Phase 2 Complete)

Implemented all core MCP tools for read/write operations.

### Added
- **9 MCP Tools** via FastMCP:
  - `check_connection` - Test Zotero connectivity
  - `search_items` - Search by title/author/year
  - `get_item` - Get item by key
  - `list_items` - List recent items
  - `list_collections` - List all collections
  - `list_tags` - List all tags
  - `get_item_types` - Get available item types
  - `add_reference` - Add new reference (simple API)
  - `create_item` - Create with full metadata (advanced)
- **Test Script**: `test_mcp_tools.py` for all tools validation

### Changed
- Refactored from use_cases architecture to direct MCP tools
- Renamed project to "zotero-keeper"

### Removed
- Legacy `application/use_cases/` layer
- Legacy `domain/repositories/` interfaces
- Duplicate README in mcp-server/

---

## [1.1.0] - 2024-12-11

### 🎉 Major Discovery - Built-in API
This release pivots from custom plugin development to using Zotero 7's built-in HTTP APIs.

### Added
- **ZoteroClient**: Full HTTP client implementation for Zotero APIs
  - Local API integration (`/api/users/0/...`) for READ operations
  - Connector API integration (`/connector/saveItems`) for WRITE operations
  - Proper Host header handling for port proxy setup
- **API Documentation**: Complete endpoint documentation in README
- **Network Setup Guide**: Step-by-step instructions for Windows port proxy

### Changed
- **Architecture**: Switched from custom plugin to built-in Zotero APIs
  - Eliminated need for Zotero plugin development
  - Simplified deployment (no plugin installation required)
- **Project Structure**: Reorganized to DDD onion architecture

### Discovered
- Zotero 7 has comprehensive built-in Local API (previously undocumented)
- Connector API supports write operations via `POST /connector/saveItems`
- Port proxy required because Zotero binds only to `127.0.0.1`

### Technical Notes
```
- Local API: /api/users/0/items, /collections, /tags
- Connector API: /connector/saveItems, /connector/ping
- Network: netsh portproxy for external access
- Header: Host: 127.0.0.1:23119 required
```

---

## [1.0.3] - 2024-12-10

### Attempted
- Custom HTTP server in Zotero Plugin (external binding)

### Issues
- Zotero's XPCOMUtils.jsm restrictions prevent binding to external interfaces
- ServerSocket hardcoded to loopback only

---

## [1.0.2] - 2024-12-10

### Attempted
- Zotero Plugin v1.0.2 with custom HTTP endpoint
- Manifest updates for Zotero 7 compatibility

### Issues
- Bootstrap initialization errors
- HTTP server failed to bind external interface

---

## [1.0.1] - 2024-12-09

### Added
- Initial Zotero Plugin for Zotero 7
  - `manifest.json` with proper schema
  - `bootstrap.js` with lifecycle handlers
  - Fixed `update_url` and `strict_max_version` issues
- Successfully installed on Windows Zotero 7.0.30

### Issues
- Custom HTTP server not functioning as expected

---

## [1.0.0] - 2024-12-08

### Added
- **Project Initialization**
  - MCP Server skeleton with FastMCP
  - DDD directory structure
  - Basic `pyproject.toml` configuration
  - Initial README documentation

### Technical Stack
- Python 3.11+
- FastMCP SDK
- httpx for HTTP client
- Pydantic for data validation

---

## Development Notes

### Version Naming Convention
- **Major**: Breaking changes or major feature releases
- **Minor**: New features, significant improvements
- **Patch**: Bug fixes, documentation updates

### Related Issues
- Zotero Local API only supports READ (as of 2024-12)
- Connector API required for WRITE operations
- Port proxy needed for network access

---

[Unreleased]: https://github.com/u9401066/zotero-keeper/compare/v1.4.0...HEAD
[1.4.0]: https://github.com/u9401066/zotero-keeper/compare/v1.3.0...v1.4.0
[1.3.0]: https://github.com/u9401066/zotero-keeper/compare/v1.2.0...v1.3.0
[1.2.0]: https://github.com/u9401066/zotero-keeper/compare/v1.1.0...v1.2.0
[1.1.0]: https://github.com/u9401066/zotero-keeper/compare/v1.0.0...v1.1.0
[1.0.3]: https://github.com/u9401066/zotero-keeper/compare/v1.0.2...v1.0.3
[1.0.2]: https://github.com/u9401066/zotero-keeper/compare/v1.0.1...v1.0.2
[1.0.1]: https://github.com/u9401066/zotero-keeper/compare/v1.0.0...v1.0.1
[1.0.0]: https://github.com/u9401066/zotero-keeper/releases/tag/v1.0.0
