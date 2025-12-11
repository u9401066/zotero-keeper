# Changelog

All notable changes to Zotero Keeper will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

## [Unreleased]

### Planned
- MCP Tools implementation (read/write)
- Duplicate detection
- Metadata validation
- DOI-based enrichment

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

[Unreleased]: https://github.com/your-username/zotero-keeper/compare/v1.1.0...HEAD
[1.1.0]: https://github.com/your-username/zotero-keeper/compare/v1.0.0...v1.1.0
[1.0.3]: https://github.com/your-username/zotero-keeper/compare/v1.0.2...v1.0.3
[1.0.2]: https://github.com/your-username/zotero-keeper/compare/v1.0.1...v1.0.2
[1.0.1]: https://github.com/your-username/zotero-keeper/compare/v1.0.0...v1.0.1
[1.0.0]: https://github.com/your-username/zotero-keeper/releases/tag/v1.0.0
