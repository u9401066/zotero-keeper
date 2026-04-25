# Changelog

All notable changes to Zotero Keeper will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

## [1.12.0] - 2026-04-08

### 🛡️ Collaboration-Safe Defaults & Production Hardening

This release hardens the keeper ↔ pubmed-search-mcp integration for production use.

### Added

- **Collaboration-Safe Tool Surface** ⭐:
  - Legacy PubMed bridge tools (`search_pubmed_exclude_owned`, `import_ris_to_zotero`, `import_from_pmids`, `quick_import_pmids`, `batch_import_from_pubmed`) are **hidden by default**
  - Prevents tool duplication with pubmed-search-mcp
  - Opt-in via `ZOTERO_KEEPER_ENABLE_LEGACY_PUBMED_TOOLS=1`
  - Default public surface: `advanced_search`, `check_articles_owned`, `import_articles`

- **Server Instructions for AI Agents**:
  - Clear tool ownership: pubmed-search-mcp owns search/discovery/export/citation-metrics; keeper owns library reads/collection/duplicate-check/import
  - Recommended collaboration workflow documented in `McpServerConfig.instructions`

- **Environment Variable Documentation**:
  - `ZOTERO_KEEPER_ENABLE_LEGACY_PUBMED_TOOLS` — toggle legacy bridge tools
  - `ZOTERO_HOST` / `ZOTERO_PORT` / `ZOTERO_TIMEOUT` — Zotero connection
  - `NCBI_EMAIL` / `NCBI_API_KEY` — PubMed API credentials
  - `PUBMED_SEARCH_PATH` — override submodule path

### Changed

- **`import_articles` duplicate detection upgraded**:
  - Now uses `batch_check_identifiers()` for PMID + DOI full-library matching
  - Previously only checked first 10 items by DOI search (N+1 queries)
  - Consistent with `batch_tools` quality

- **`fetch_pubmed_articles()` async safety**:
  - Converted to an async helper and awaited end-to-end across keeper callers
  - Matches `pubmed-search-mcp` v0.5.2's async `PubMedClient.fetch_details()` contract
  - Removes the old sync wrapper that leaked blocking/coroutine risk into MCP tool paths

- **`check_articles_owned` graceful fallback**:
  - When pubmed-search-mcp is not installed, falls back to local PMID matching only
  - Previously would fail if the PubMed integration was unavailable

### Fixed

- **RIS parser DRY violation**: Unified `_parse_ris_to_articles()` in `unified_import_tools.py`; legacy `_parse_ris_to_zotero_items()` in `pubmed_tools.py` now delegates to shared logic
- **`import_articles` no input size limit**: Added `max_articles=100` guard with batch hint
- **`import_articles` partial failure handling**: Added per-batch error tracking (50 items per batch)
- **`check_articles_owned` creates new PubMedClient per call**: Replaced with the shared cached client and now threads `NCBI_API_KEY` consistently

### Architecture

- Collaboration-safe default: keeper focuses on Zotero library management; pubmed-search-mcp owns search
- `import_articles` is the single public import gateway
- Legacy tools remain available but require explicit opt-in

---

## [0.5.16] - 2026-03-04

### 🤖 Research Agent + PubMed 0.4.4

Adds a dedicated `@research` Copilot agent for literature search workflows, and upgrades pubmed-search-mcp to v0.4.4.

### Added

- **`@research` Copilot Agent** — Dedicated research assistant deployed to `.github/agents/research.agent.md`. Consolidates 8 PubMed skills into a single agent with restricted tools (no terminal/pylance). Includes: PICO search, systematic search, citation networks, fulltext access, NCBI extended databases, export workflows
- **Agent auto-deployment** — Extension automatically installs research agent on activation, with legacy upgrade support

### Changed

- **pubmed-search-mcp 0.3.8 → 0.4.4** — Citation metrics caching (30min TTL), BM25 ranking, mypy strict bug fixes
- Updated copilot-instructions.md and research-workflow.md to reference v0.4.4
- Extension deployment refactored: `installResearchAgent()` for `.github/agents/` directory

---

## [0.5.15] - 2026-03-04

### 🐛 Critical Bug Fixes + Zotero 8 Compatibility

This release fixes multiple critical async/await bugs that prevented PubMed import tools from working, adds Zotero 8 annotation filtering, and fixes TCP port exhaustion from httpx connection leaks.

### Fixed

- **Critical: Async/Await Missing** — 12 call sites across 6 files were calling async PubMed functions without `await`, returning coroutine objects instead of data. Affected tools: `batch_import_from_pubmed`, `import_from_pmids`, `quick_import_pmids`, `search_pubmed_exclude_owned`, `check_articles_owned`
- **Critical: `list_collections()` → `get_collections()`** — 8 call sites used non-existent `list_collections()` method on ZoteroClient, causing AttributeError on all import tools with collection targeting
- **Critical: Collection Name Resolution** — 3 call sites used `col.get("name")` instead of `col.get("data", {}).get("name", "")`, causing collection name matching to always fail
- **TCP Port Exhaustion** — `metadata_fetcher.py` created a new `httpx.AsyncClient` per CrossRef request, exhausting ephemeral ports on Windows. Now uses module-level shared client with connection pooling
- **Wrapper Functions Made Async** — `fetch_pubmed_articles()`, `fetch_citation_metrics()`, `enrich_articles_with_metrics()` in `pubmed/__init__.py` converted from sync to async

### Added

- **Zotero 8 Annotation Filtering** — All item-listing tools now filter out `annotation` itemType (Zotero 8 stores PDF annotations as top-level items). Affected: `search_items`, `list_items`, `get_collection_items`, `get_library_stats`, `find_orphan_items`, MCP resources
- **VS Code Extension v0.5.15** — Zotero 8 compatibility docs, dependency updates
- **`.vscode/mcp.json`** — Dev MCP config template using `uv run`

### Changed

- **pubmed-search-mcp upgraded 0.3.8 → 0.4.4** — citation metrics caching (30min TTL), mypy strict bug fixes, BM25 ranking improvements
- Zotero documentation updated for Zotero 8 (port 23119 confirmed)
- VS Code Extension: npm dependency updates

---

## [0.5.14] - 2025-06-27

### 🔍 Attachment & Fulltext Access + Version Unification

This release adds PDF attachment access tools and unifies version numbering across the monorepo.

### Added

- **Attachment Tools** 📎:
  - `get_item_attachments`: List all attachments for a Zotero item with file paths and metadata
  - `get_item_fulltext`: Get Zotero-indexed plain text content from PDF/EPUB attachments
  - PDF priority sorting, file existence checks, ZOTERO_DATA_DIR support
  - DAL layer: `get_item_fulltext()` and `resolve_attachment_path()` in `client_read.py`

- **VS Code Extension Test Infrastructure**:
  - Mocha + Sinon test framework with VS Code mock
  - Unit tests for extension, mcpProvider, statusBar, pythonEnvironment, uvPythonManager
  - `.mocharc.yml` configuration

- **Structured Logging**:
  - `logging_config.py` with `log_tool_call` decorator
  - VS Code `logger.ts` unified output channel
  - `logLevel` configuration setting

- **Pre-commit Quality Gate**:
  - `scripts/pre-commit`: ruff lint/format, pytest, trailing whitespace, conflict marker checks
  - `scripts/install-hooks.sh`: one-command hook installation

- **Zotero Plugin Spec**: `docs/design/ZOTERO_PLUGIN_SPEC.md` (HTTP Bridge Server design)

### Changed

- **Version Unification**: MCP Server version changed from `1.11.0`/`1.6.1` → `0.5.14` to align with VS Code extension versioning
- Total MCP tools: **32** (was 30, +2 attachment tools)

---

## [0.5.13] - 2025-06-26

### 🔧 EPERM Fix & Python 3.12

- EPERM error handling for embedded Python
- NCBI email auto-detect for PubMed MCP
- Python 3.12 support
- Documentation updates

---

## [0.5.12] - 2025-06-25

### 🐛 Critical Fix

- Fix version check infinite loop
- PubMed MCP v0.3.8 integration
- uv-only package management

---

## [1.11.0] - 2026-01-12

### 🚀 Unified Import & Multi-Source Support

This release introduces a unified import architecture supporting articles from ANY source.

### Added

- **Unified Import Tool** ⭐ (`import_articles`):
  - Single entry point for ALL article imports
  - Accepts articles from pubmed-search-mcp (any search tool)
  - Supports: PubMed, Europe PMC, CORE, CrossRef, OpenAlex, Semantic Scholar
  - Also accepts RIS text for legacy compatibility
  - Full collection validation (防呆機制)
  - Optional duplicate detection

- **Collection Validation** for all import tools:
  - If collection not found → returns error + available collections
  - If no collection specified → saves to root with warning
  - Success response includes `saved_to` confirmation

- **New file**: `unified_import_tools.py`

### Changed

- **Deprecated** (but still functional):
  - `import_ris_to_zotero` → use `import_articles` instead
  - `import_from_pmids` → use `import_articles` instead
  - `quick_import_pmids` still recommended for simple PMID imports

- **Enhanced existing tools** with collection parameters:
  - `import_ris_to_zotero`: added `collection_name`, `collection_key`
  - `import_from_pmids`: added `collection_name`, `collection_key`

### Architecture

- Two-MCP communication via standardized `UnifiedArticle` format
- pubmed-search-mcp (search) → articles → zotero-keeper (import)

### Tool Count

- Total tools: **26** (was 25)
  - +1 unified import tool (import_articles)

---

## [1.10.1] - 2025-12-16

### 🚀 One-Click Install & Library Analytics

This release improves user experience with one-click installation and library analytics tools.

### Added

- **One-Click Install Button** ⭐:
  - Added `vscode:mcp/install` URL to README
  - VS Code users can now install with a single click
  - Also supports VS Code Insiders

- **Library Analytics Tools** (analytics_tools.py):
  - `get_library_stats`: Library statistics (year/author/journal distribution)
  - `find_orphan_items`: Find items without collection or tags

- **Quick Import Tool** (pubmed_tools.py):
  - `quick_import_pmids`: Simplest way to import from PubMed
  - Just provide PMIDs, optional collection and tags
  - Uses best available method automatically

### Changed

- **Code Refactoring**:
  - Split `server.py` (586 → 202 lines)
  - New `basic_read_tools.py` (207 lines)
  - New `collection_tools.py` (226 lines)
  - Better maintainability following bylaws

### Tool Count

- Total tools: **25** (was 22)
  - +2 analytics tools (get_library_stats, find_orphan_items)
  - +1 quick import tool (quick_import_pmids)

---

## [1.10.0] - 2025-12-15

### 🚀 PyPI Release & VS Code Extension v0.3.1

This release marks the official PyPI publication and VS Code extension improvements.

### Added

- **PyPI Publication** ⭐:
  - `zotero-keeper` now available on PyPI
  - `uv pip install zotero-keeper` works out of the box
  - All dependencies properly declared

### VS Code Extension v0.3.1

- **New Python Manager Using uv** ⭐:
  - Replaced embedded Python with [uv](https://github.com/astral-sh/uv)
  - 10-100x faster package installation
  - Automatic legacy Python download and management
  - Smaller extension size (~30KB, uv ~10MB on first run)

- **Fixed**:
  - Windows "Failed to set up Python environment" error
  - Package name issues (removed `[all]` extras)
  - Concurrent setup race conditions (added mutex)

### Changed

- Extension now uses `uvPythonManager.ts` instead of `embeddedPython.ts`
- Removed bundled wheel infrastructure (no longer needed)

---

## [1.8.2] - 2025-12-14

### 📊 RCR Citation Metrics Default ON

This release enables automatic citation metrics (RCR) fetching for all PubMed-related save/import tools.

### Changed

- **RCR Now Default ON** for all PubMed tools:
  - `interactive_save`: Auto-fetches RCR when PMID provided
  - `quick_save`: Auto-fetches RCR when PMID provided
  - `import_from_pmids`: Auto-fetches RCR for all PMIDs
  - `batch_import_from_pubmed`: Changed from `include_citation_metrics=False` to `True`

### Added

- **Shared Citation Metrics Functions** in `infrastructure/pubmed/__init__.py`:
  - `fetch_citation_metrics(pmids)`: Get RCR/percentile from iCite
  - `enrich_articles_with_metrics(articles)`: Add metrics to article dicts
  - Reusable across all tools

- **New Parameter** `include_citation_metrics`:
  - Added to `interactive_save` (default: True)
  - Added to `quick_save` (default: True)
  - Added to `import_from_pmids` (default: True)

### Technical Details

When a PMID is provided, tools now automatically:
1. Fetch article metadata from PubMed
2. Fetch citation metrics from NIH iCite API
3. Store RCR, percentile, citation count in Zotero's `extra` field

Example extra field content:
```
PMID: 12345678
RCR: 2.45
NIH Percentile: 85.2
Citation Count: 127
```

### Note

- RCR (Relative Citation Ratio) is a field-normalized citation metric
- RCR = 1.0 means average for the field
- RCR > 2.0 indicates highly cited paper
- Set `include_citation_metrics=False` to disable if needed

---

## [1.8.1] - 2025-12-14

### 🔍 Advanced Search & Documentation Release

This release adds powerful search capabilities and comprehensive API limitation documentation.

### Added

- **`advanced_search` Tool** ⭐:
  - Multi-condition search using Zotero Local API parameters
  - `item_type`: Filter by type (journalArticle, book, -attachment, etc.)
  - `tag`: Single tag filter with OR support (`AI || ML`)
  - `tags`: Multiple tags filter with AND logic
  - `qmode`: Search mode (`titleCreatorYear` or `everything` for abstract)
  - `sort` / `direction`: Flexible sorting options
  - `include_trashed`: Include items in trash

- **Enhanced Documentation**:
  - Detailed API Capability Matrix in README
  - Technical explanation of Local API vs Connector API
  - Clear "Cannot Do" vs "Can Do" examples
  - One-click installation roadmap section

### Changed

- **Tool Count**: 21 → 22 tools
- **README Updates**: Both EN and zh-TW with:
  - API limitation technical details
  - `advanced_search` usage examples
  - Future installation plans section

### Technical Details

- Modified files:
  - `infrastructure/zotero_client/client.py`: Extended `get_items()` with `tag`, `include_trashed`
  - `infrastructure/mcp/search_tools.py`: Added `advanced_search` tool
  - `infrastructure/mcp/server.py`: Always register search_tools
  - `README.md` & `README.zh-TW.md`: Enhanced documentation

### Example Usage

```python
# 🔍 Search by item type
advanced_search(item_type="journalArticle")  # Journal articles only
advanced_search(item_type="-attachment")     # Exclude attachments

# 🏷️ Search by tags
advanced_search(tag="AI")                    # Single tag
advanced_search(tags=["AI", "Review"])       # Multiple tags (AND)
advanced_search(tag="AI || ML")              # Either tag (OR)

# 📝 Full-text search (including abstract)
advanced_search(q="XGBoost", qmode="everything")

# 🌟 Combined search
advanced_search(
    q="machine learning",
    item_type="journalArticle",
    tag="AI",
    sort="dateAdded",
    direction="desc"
)
```

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
- **Python**: Requires the legacy pre-3.12 baseline used by that historical release

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
