# Zotero Keeper MCP Server

MCP Server for managing local Zotero libraries via AI Agents.

## Installation

```bash
# Basic installation
uv pip install -e .

# With PubMed support
uv pip install -e ".[pubmed]"

# All features
uv pip install -e ".[all]"
```

## Usage

```bash
# Run MCP server
python -m zotero_mcp

# Or use the CLI
zotero-keeper
```

## Environment Variables

Copy `.env.example` to `.env` and configure:

```bash
# Local Zotero (default)
ZOTERO_HOST=localhost
ZOTERO_PORT=23119

# Remote Zotero
ZOTERO_HOST=<your-zotero-ip>
ZOTERO_PORT=23119
```

## MCP Tools

### 🌟 Unified Import (NEW in v1.11.0)

| Tool | Description |
|------|-------------|
| `import_articles` | **⭐ One tool for ALL imports** - accepts articles from any pubmed-search-mcp tool |

**Workflow:**
```python
# Step 1: Search with pubmed-search-mcp
results = unified_search("CRISPR gene therapy", limit=10)

# Step 2: Import to Zotero (ANY source works!)
import_articles(
    articles=results["articles"],
    collection_name="CRISPR Research",
    tags=["2024", "review"]
)
```

**Supported sources:** PubMed, Europe PMC, CORE, CrossRef, OpenAlex, Semantic Scholar, RIS

### Core Tools
| Tool | Description |
|------|-------------|
| `check_connection` | Test Zotero connectivity |
| `search_items` | Search references by keyword |
| `get_item` | Get item details by key |
| `list_items` | List recent items |
| `add_reference` | Add new reference (simple) |
| `create_item` | Create with full metadata |

### Smart Tools 🧠
| Tool | Description |
|------|-------------|
| `smart_add_reference` | Validate + duplicate check + add |
| `smart_add_with_collection` | Smart add + auto-classify to collection |
| `suggest_collections` | Suggest collections based on title/tags |
| `check_duplicate` | Check if reference exists |
| `validate_reference` | Validate before adding |

### Collection Tools
| Tool | Description |
|------|-------------|
| `list_collections` | List all collections |
| `get_collection` | Get collection by key |
| `get_collection_items` | Get items in a collection |
| `get_collection_tree` | Get hierarchical tree structure |
| `find_collection` | Find collection by name |

### Saved Search Tools 🌟 (Local API Exclusive!)
| Tool | Description |
|------|-------------|
| `list_saved_searches` | List all saved searches |
| `run_saved_search` | Execute a saved search |
| `get_saved_search_details` | Get search conditions |

### Other Tools
| Tool | Description |
|------|-------------|
| `list_tags` | List all tags |
| `get_item_types` | Get available item types |

---

## 💡 Smart Collection Feature

AI can suggest appropriate collections based on title, abstract, and tags!

### Workflow Options

**Option 1: Ask before saving**
```
User: "Which collection should this AI paper go to?"
AI: suggest_collections(title="AI in Anesthesiology")
    → Suggests: "AI Research" (score: 85)

User: "Add it to AI Research"
AI: add_reference(..., collections=["ABC123KEY"])
```

**Option 2: Auto-classify**
```
User: "Add this paper and auto-classify"
AI: smart_add_with_collection(
        title="AI in Anesthesiology",
        auto_suggest_collection=True
    )
    → Automatically added to "AI Research"
```

**Option 3: Specify by name**
```
User: "Add to 'Machine Learning' collection"
AI: smart_add_with_collection(
        title="...",
        collection_name="Machine Learning"
    )
```

### ⚠️ Important Note

Since Local API cannot create collections:
1. **Create collection structure in Zotero first**
2. **Let AI classify into existing collections**

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

```
AI: "Which papers don't have PDFs?"
→ run_saved_search(search_name="Missing PDF")

AI: "What did I add this week?"
→ run_saved_search(search_name="Recent Additions")
```

### Recommended Saved Searches

Create these once, use forever:

| Name | Conditions | Use Case |
|------|------------|----------|
| **Missing PDF** | `Attachment File Type` `is not` `PDF` | Find papers without PDF |
| **Missing DOI** | `DOI` `is` *(empty)* | Find incomplete metadata |
| **Missing Abstract** | `Abstract` `is` *(empty)* | Find items without abstract |
| **Recent Additions** | `Date Added` `is in the last` `7 days` | Review recent imports |
| **Unread** | `Tag` `is not` `read` | Track reading progress |
| **Reviews** | `Title` `contains` `review` | Find review articles |
| **This Year** | `Date` `is after` `2024-01-01` | Recent publications |

### Condition Reference

| Field | Operators | Example Values |
|-------|-----------|----------------|
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
