# Changelog

All notable changes to Zotero Keeper will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

## [1.8.0] - 2025-12-14

### 🛡️ Collection 防呆 & Citation Metrics Release

This release adds robust collection validation and citation metrics support.

### Added

- **Collection 防呆機制** for `batch_import_from_pubmed`:
  - New `collection_name` parameter (recommended!) - auto-validates and resolves to key
  - If collection not found, returns list of available collections
  - `collection_info` in result confirms actual destination
  - Tool description warns against using raw `collection_key`

- **Citation Metrics Support**:
  - New `include_citation_metrics` parameter for `batch_import_from_pubmed`
  - Fetches RCR, NIH Percentile, Citations from iCite API
  - Metrics stored in Zotero `extra` field (visible in Zotero UI!)
  - Fields: `RCR`, `NIH Percentile`, `Citations`, `Citations/Year`, `APT`

- **Documentation**:
  - Created `docs/ZOTERO_LOCAL_API.md` - comprehensive API reference
  - Documents Local API (read-only) vs Connector API (write)
  - Includes test results and known limitations

### Technical Details

- Modified files:
  - `infrastructure/mcp/batch_tools.py`: Added collection validation + citation metrics
  - `infrastructure/mappers/pubmed_mapper.py`: Added RCR fields to extra
  - `docs/ZOTERO_LOCAL_API.md`: New documentation file

### Example Usage

```python
# ✅ Recommended: Use collection_name (auto-validates!)
batch_import_from_pubmed(
    pmids="38353755,37864754",
    collection_name="AI Research",  # Validates existence!
    include_citation_metrics=True    # Fetches RCR from iCite
)

# Result includes confirmation:
{
    "success": true,
    "added": 2,
    "collection_info": {
        "key": "MHT7CZ8U",
        "name": "AI Research",
        "resolved_from": "name"
    }
}
```

---

## [1.7.2] - 2025-12-14

### 🐛 Bug Fix: batch_import_from_pubmed collection support

Fixed a critical bug where `collection_key` parameter in `batch_import_from_pubmed` 
was not actually adding items to the specified collection.

### Fixed

- **`batch_import_from_pubmed`** now correctly adds items to the specified collection
  - Added `collection_keys` parameter to `map_pubmed_to_zotero()` mapper
  - Items now include `collections` field in Zotero item schema
  - Removed "not yet implemented" placeholder code
  
### Technical Details

- Modified files:
  - `infrastructure/mappers/pubmed_mapper.py`: Added `collection_keys` parameter
  - `infrastructure/mcp/batch_tools.py`: Pass `collection_key` to mapper
- **Test Coverage**: 358 tests passing (+3 new tests for collection_keys)

---

## [1.7.1] - 2025-12-14

### 🧹 Code Quality & Static Analysis Release

Comprehensive code quality improvements via ruff static analysis.

### Fixed

- **~750 code issues** identified and fixed by ruff linter:
  - Removed unused imports (F401) - ~15 instances
  - Fixed f-strings without placeholders (F541) - ~5 instances  
  - Fixed unused loop variables (B007) - `for key, col` → `for _, col`
  - Simplified nested if statements (SIM102)
  - Sorted and formatted import blocks (I001) - ~20 instances
  - Modernized type annotations: `Optional[X]` → `X | None` (UP045)
  - Removed trailing whitespace (W293) - ~300+ instances

### Changed

- Added `# noqa` comments for intentional design patterns:
  - `TYPE_CHECKING` imports in `pubmed/__init__.py`
  - Conditional imports in `batch_tools.py`

### Technical Details

- **Test Coverage**: 355 tests passing, 67% coverage
- **Linter Status**: All critical errors resolved (only E501 line length warnings remain)
- **Python**: Requires 3.11+ (modern syntax throughout)

---

## [1.7.0] - 2025-12-14

### 🎯 Tool Simplification & MCP Enhancement Release

This release focuses on reducing complexity while adding powerful MCP features.

### Added

- **MCP Resources** (10 URIs): Passive browsable data endpoints
  - `zotero://collections` - List all collections
  - `zotero://collections/tree` - Collection hierarchy
  - `zotero://collections/{key}` - Collection details
  - `zotero://collections/{key}/items` - Items in collection
  - `zotero://items` - Recent items
  - `zotero://items/{key}` - Item details
  - `zotero://tags` - All tags
  - `zotero://searches` - Saved searches
  - `zotero://searches/{key}` - Search details
  - `zotero://schema/item-types` - Available item types

- **MCP Elicitation**: Interactive collection selection in `interactive_save`
  - Presents numbered options to user
  - Supports user input validation
  - Graceful fallback if elicitation unavailable

- **Auto-fetch Metadata**:
  - DOI → CrossRef API for complete metadata
  - PMID → PubMed E-utilities for complete metadata
  - User input takes priority, fetched data fills gaps

### Changed

- **Tool Count Reduced**: 27 → 21 tools
- **smart_tools.py**: Now helpers only (no tools registered)
  - `_suggest_collections()` - Internal helper for collection matching
  - `_find_duplicates()` - Internal helper for duplicate detection

### Removed

- **collection_tools.py**: Deleted (replaced by `resources.py`)
- **6 Smart Tools**: Consolidated into `interactive_save`/`quick_save`
  - `smart_add_reference` → use `interactive_save`
  - `smart_add_with_collection` → use `interactive_save`
  - `suggest_collections` → now internal helper
  - `check_duplicate` → now internal helper
  - `validate_reference` → built into save tools
  - `add_reference` → use `quick_save`

### Technical Details

- **Tool Distribution**:
  - server.py: 11 tools (core CRUD operations)
  - interactive_tools.py: 2 tools (`interactive_save`, `quick_save`)
  - saved_search_tools.py: 3 tools
  - search_tools.py: 2 tools
  - pubmed_tools.py: 2 tools
  - batch_tools.py: 1 tool

---

## [1.6.0] - 2024-12-12

### Added

- **PubMed Integration Tools**:
  - `search_pubmed_exclude_owned` - Search PubMed, automatically exclude owned items
  - `check_articles_owned` - Check if PMIDs/DOIs exist in Zotero
  - `batch_import_from_pubmed` - Batch import from PMIDs with collection support

- **Saved Search Support** (Local API Exclusive):
  - `list_saved_searches` - List all saved searches
  - `run_saved_search` - Execute saved search by key or name
  - `get_saved_search_details` - Get search conditions

- **Import Tools**:
  - `import_ris_to_zotero` - Import RIS format data
  - `import_from_pmids` - Import single/multiple PMIDs

### Technical Details

- Module structure reorganized for clarity
- Integration with `pubmed-search-mcp` for literature workflow

---

## [1.5.0] - 2024-12-10

### Added

- **Dual API Support**: Local API (read) + Connector API (write)
- **Smart Add Features**:
  - Collection suggestion (fuzzy matching)
  - Duplicate detection (DOI/PMID/title)
  - Validation before save

### Changed

- HTTP client refactored for dual API support
- Configuration via environment variables

---

## [1.4.0] - 2024-12-08

### Added

- **Collection Management**:
  - `list_collections` - List all collections
  - `get_collection` - Get collection details
  - `get_collection_items` - Items in collection
  - `get_collection_tree` - Hierarchical view
  - `find_collection` - Search by name

---

## [1.3.0] - 2024-12-06

### Added

- **Search Capabilities**:
  - `search_items` - Full-text search
  - `list_items` - Recent items with filters
  - `get_item` - Get item by key

---

## [1.2.0] - 2024-12-04

### Added

- **Basic CRUD Operations**:
  - `add_reference` - Add new reference
  - `create_item` - Create with full metadata
  - `list_tags` - List all tags
  - `get_item_types` - Available item types

---

## [1.1.0] - 2024-12-02

### Added

- **Initial MCP Server Setup**:
  - FastMCP framework integration
  - `check_connection` - Verify Zotero connectivity

---

## [1.0.0] - 2024-12-01

### Added

- Initial release
- Project structure (DDD architecture)
- Zotero HTTP client (Local API)
- Basic configuration

---

## Migration Guides

### From v1.6.x to v1.7.0

**Tool Changes:**
```
# Old (multiple tools)
smart_add_reference(title=..., doi=...)
suggest_collections(title=...)
check_duplicate(title=..., doi=...)

# New (single tool with auto-fetch + elicitation)
interactive_save(title=..., doi=...)
# → Auto-fetches metadata from CrossRef
# → Suggests collections via elicitation
# → Checks duplicates internally
```

**Resources:**
```
# Old (tool call)
list_collections()  # Still available as tool

# New (also available as resource)
zotero://collections  # Passive browsing
```

---

*For detailed architecture, see [ARCHITECTURE.md](ARCHITECTURE.md)*
