# Zotero Keeper MCP Server

Zotero Keeper 2.0.0 is an MCP SDK v2 server for managing local Zotero libraries via AI agents. It uses the v2 `MCPServer` API and is intentionally incompatible with an MCP SDK 1.x environment.

> The v0.6.0 VS Code extension is the recommended distribution for this 2.0 runtime. The commands below install from this source checkout. The separately published `uvx`/PyPI package may still be on the older release line until its own publication is complete.

## Installation

```bash
# Basic installation
uv sync

# With PubMed support
uv sync --extra pubmed

# All features
uv sync --extra all
```

## Usage

```bash
# Run MCP server
uv run python -m zotero_mcp

# Or use the CLI
uv run zotero-keeper
```

## Environment Variables

Copy `.env.example` to `.env` and configure:

```bash
# Local Zotero (default; keep the unauthenticated API on loopback)
ZOTERO_HOST=127.0.0.1
ZOTERO_PORT=23119
ZOTERO_TIMEOUT=30

# Optional: PubMed API credentials for higher NCBI rate limits
NCBI_EMAIL=your.email@example.com
# NCBI_API_KEY=your_api_key_here

# Optional: re-enable legacy PubMed bridge/import tools
ZOTERO_KEEPER_ENABLE_LEGACY_PUBMED_TOOLS=1

# Optional: development override for a local pubmed-search-mcp checkout
# PUBMED_SEARCH_PATH=../external/pubmed-search-mcp
```

- `ZOTERO_TIMEOUT` controls Zotero API request timeout in seconds.
- Do not point `ZOTERO_HOST` at a remotely exposed Local/Connector API. For remote libraries, use Zotero's authenticated HTTPS Web API or a purpose-built authenticated service.
- `NCBI_EMAIL` and optional `NCBI_API_KEY` are passed through to pubmed-search-mcp for fetch and ownership-check workflows.
- `PUBMED_SEARCH_PATH` is only for local development when you want keeper to import a checked-out pubmed-search-mcp instead of the installed package.

By default, zotero-keeper runs in a collaboration-safe mode: PubMed search/discovery/export stays in pubmed-search-mcp, while zotero-keeper exposes the Zotero-side import and library tools.

## MCP Tools

### 🌟 Unified Import (Updated in v1.12.0)

| Tool | Description |
| ---- | ----------- |
| `import_articles` | **⭐ One tool for ALL imports** - accepts articles from any pubmed-search-mcp tool |

**Workflow:**

```python
# Step 1: Search with pubmed-search-mcp
results = unified_search("CRISPR gene therapy", limit=10, output_format="json")

# Step 2: Import to Zotero (ANY source works!)
import_articles(
    articles=results["articles"],
    collection_name="CRISPR Research",
    tags=["2024", "review"]
)
```

**Supported sources:** PubMed, Europe PMC, CORE, CrossRef, OpenAlex, Semantic Scholar, RIS

### Public Tool Surface (24 default tools + 6 resources)

The default public surface combines connection, read, collection, save, search, import, analytics, and attachment access tools. MCP SDK v2 advertises six concrete browsable resources plus four parameterized URI templates.

### Smart Save Behavior

Duplicate detection, validation, and collection suggestion are built into `interactive_save` and `quick_save`.

Collection routing is fail-closed:

- `interactive_save` accepts an exact collection key or the explicit `ROOT` sentinel. `ROOT` always triggers a second confirmation.
- `skip_collection_prompt=True` aborts when no destination is confirmed; it never silently falls back to the library root.
- `quick_save`, `import_articles`, and `import_pdf` reject a missing collection by default.
- Root storage is allowed only after the user explicitly confirms it and the caller passes `allow_library_root=true`.

### Legacy PubMed Bridge (Opt-in)

Set `ZOTERO_KEEPER_ENABLE_LEGACY_PUBMED_TOOLS=1` only if you intentionally want the older keeper-only PubMed bridge tools such as `search_pubmed_exclude_owned`, `import_from_pmids`, or `batch_import_from_pubmed`.

### Collection Tools

| Tool | Description |
| ---- | ----------- |
| `list_collections` | List all collections |
| `get_collection` | Get collection by key |
| `get_collection_items` | Get items in a collection |
| `get_collection_tree` | Get hierarchical tree structure |
| `find_collection` | Find collection by name |

### Saved Search Tools 🌟 (Local API Exclusive!)

| Tool | Description |
| ---- | ----------- |
| `list_saved_searches` | List all saved searches |
| `run_saved_search` | Execute a saved search |
| `get_saved_search_details` | Get search conditions |

### Search & Import Tools

| Tool | Description |
| ---- | ----------- |
| `advanced_search` | Multi-condition Zotero search |
| `check_articles_owned` | Check PubMed IDs against the local library |
| `import_articles` | Collaboration-safe PubMed -> Zotero import handoff |
| `import_pdf` | Import a local PDF through Zotero Connector endpoints, with metadata or Zotero recognition |

### Analytics Tools

| Tool | Description |
| ---- | ----------- |
| `get_library_stats` | Summaries by year, author, and journal |
| `find_orphan_items` | Find items that are not organized into collections |

### Attachment & Fulltext Tools

| Tool | Description |
| ---- | ----------- |
| `get_item_attachments` | List attachment metadata and resolved file paths |
| `get_item_fulltext` | Read Zotero-indexed full text for PDF/EPUB attachments |

### Other Read Helpers

| Tool | Description |
| ---- | ----------- |
| `list_tags` | List all tags |
| `get_item_types` | Get available item types |

### PubMed Search MCP boundary

The v0.6.0 VSIX installs PubMed Search MCP 0.6.1 from commit `ad85dde`. That companion MCP SDK v2 server exposes 45 tools in 16 categories. Its two Research Chronicle tools, `build_research_chronicle` and `read_research_chronicle`, replace the previous three timeline tools.

PubMed discovery, session reuse, full text, citation exploration, export, and Research Chronicle work belong to PubMed Search MCP. Zotero Keeper owns the local library, duplicate check, collection choice, and final `import_articles` handoff.

See [Zotero MCP landscape](../docs/ZOTERO_MCP_LANDSCAPE.md) before adding another Zotero server. In particular, the MCP Registry-listed community project `54yyyu/zotero-mcp` uses the same Python module name, `zotero_mcp`; it must run in a separate environment and process from Keeper.

---

## 💡 Smart Collection Feature

AI can suggest appropriate collections based on title, abstract, and tags!

### Workflow Options

#### Option 1: Ask before saving

```text
User: "Which collection should this AI paper go to?"
AI: interactive_save(item_type="journalArticle", title="AI in Anesthesiology")
    → Shows collections and suggested matches interactively

User: "Add it to AI Research"
AI: quick_save(item_type="journalArticle", title="AI in Anesthesiology", collection_name="AI Research")
```

#### Option 2: Save directly when collection is known

```text
User: "Add this paper to AI Research"
AI: quick_save(
        item_type="journalArticle",
        title="AI in Anesthesiology",
        collection_name="AI Research"
    )
```

#### Option 3: Import structured PubMed results

```text
User: "Import these PubMed results to 'Machine Learning'"
AI: import_articles(
        articles=results["articles"],
        collection_name="Machine Learning"
    )
```

### ⚠️ Important Note

Since Local API cannot create collections:

1. **Create collection structure in Zotero first**
2. **Let AI classify into existing collections**
3. **Never omit the destination to imply root**; use the explicit double-confirmation / `allow_library_root=true` path only when the user truly requests My Library

---

## 🌟 Saved Search Feature (Local API Exclusive!)

This is a **unique feature** only available via Local API - Web API cannot execute saved searches!

### How It Works

1. **Create Saved Search in Zotero** (one-time setup)
2. **AI executes it anytime** via `run_saved_search`

### Step-by-Step Guide

#### Step 1: Create Saved Search in Zotero

1. Open Zotero
2. Press `Ctrl+Shift+F` (or **Edit → Advanced Search**)
3. Set conditions (see examples below)
4. Click **Save Search**
5. Give it a memorable name (e.g., "Missing PDF")

#### Step 2: Use via AI

```text
AI: "Which papers don't have PDFs?"
→ run_saved_search(search_name="Missing PDF")

AI: "What did I add this week?"
→ run_saved_search(search_name="Recent Additions")
```

### Recommended Saved Searches

Create these once, use forever:

| Name | Conditions | Use Case |
| ---- | ---------- | -------- |
| **Missing PDF** | `Attachment File Type` `is not` `PDF` | Find papers without PDF |
| **Missing DOI** | `DOI` `is` *(empty)* | Find incomplete metadata |
| **Missing Abstract** | `Abstract` `is` *(empty)* | Find items without abstract |
| **Recent Additions** | `Date Added` `is in the last` `7 days` | Review recent imports |
| **Unread** | `Tag` `is not` `read` | Track reading progress |
| **Reviews** | `Title` `contains` `review` | Find review articles |
| **This Year** | `Date` `is after` `2024-01-01` | Recent publications |

### Condition Reference

| Field | Operators | Example Values |
| ----- | --------- | -------------- |
| Title | contains, is, is not | "machine learning" |
| Creator | contains, is | "Zhang" |
| Date | is, is after, is before | "2024-01-01" |
| Date Added | is in the last | "7 days", "1 month" |
| Tag | is, is not | "read", "important" |
| DOI | is, is not | *(leave empty for "is empty")* |
| Attachment File Type | is, is not | "PDF" |
| Item Type | is | "journalArticle", "book" |

---

## Documentation

See [main README](../README.md) for full documentation.
