# MCP Tools Reference

Complete reference for all 23 public MCP tools exposed by Zotero Keeper.

> **Tip**: Most read operations can also be performed via [MCP Resources](../README.md#-mcp-resources-browsable-data) (e.g. `zotero://collections`) without calling a tool.

---

## Table of Contents

1. [Core Tools](#core-tools)
2. [Collection Tools](#collection-tools)
3. [Save Tools](#save-tools)
4. [Saved Search Tools](#saved-search-tools)
5. [Advanced Search Tools](#advanced-search-tools)
6. [Import Tools](#import-tools)
7. [Analytics Tools](#analytics-tools)
8. [Attachment & Fulltext Tools](#attachment--fulltext-tools)
9. [Legacy Tools (opt-in)](#legacy-tools-opt-in)

---

## Core Tools

### `check_connection`

Test connectivity to the local Zotero application.

**Parameters**: none

**Returns**:
```json
{
  "connected": true,
  "endpoint": "http://localhost:23119"
}
```

**Example prompt**: *"Is Zotero running?"*

---

### `search_items`

Full-text search across your Zotero library.

**Parameters**:

| Name | Type | Default | Description |
|------|------|---------|-------------|
| `query` | `str` | required | Search terms (title, author, year) |
| `limit` | `int` | `25` | Maximum results to return |

**Returns**:
```json
{
  "count": 3,
  "query": "CRISPR",
  "items": [
    { "key": "ABC12345", "title": "...", "itemType": "journalArticle", "date": "2024", "creators": "Smith J", "DOI": "10.1000/xyz" }
  ]
}
```

**Example prompt**: *"Find papers about CRISPR from 2024"*

---

### `get_item`

Retrieve full metadata for a single Zotero item by its key.

**Parameters**:

| Name | Type | Default | Description |
|------|------|---------|-------------|
| `key` | `str` | required | 8-character Zotero item key (e.g. `"ABC12345"`) |

**Returns**: Full item metadata including abstract, DOI, authors, journal, year, tags, collections.

**Example prompt**: *"Show me the abstract for key:ABC12345"*

---

### `list_items`

List recent items in the library or a specific collection.

**Parameters**:

| Name | Type | Default | Description |
|------|------|---------|-------------|
| `limit` | `int` | `25` | Maximum number of items |
| `collection_key` | `str` | `None` | Filter to a specific collection key |
| `sort` | `str` | `"dateAdded"` | Sort field (`dateAdded`, `dateModified`, `title`) |
| `direction` | `str` | `"desc"` | Sort direction (`asc`, `desc`) |

**Example prompt**: *"List the last 10 papers I added"*

---

### `list_tags`

List all tags used in the Zotero library with usage counts.

**Parameters**: none

**Returns**:
```json
{
  "count": 42,
  "tags": [
    { "tag": "AI", "count": 15 },
    { "tag": "review", "count": 8 }
  ]
}
```

**Example prompt**: *"What tags have I used in my library?"*

---

### `get_item_types`

List all valid Zotero item types (journalArticle, book, thesis, etc.).

**Parameters**: none

**Example prompt**: *"What item types can I save?"*

---

## Collection Tools

> These tools are also accessible via `zotero://collections/...` MCP Resources.

### `list_collections`

List all collections (folders) in the Zotero library.

**Parameters**: none

**Returns**: Flat list of all collections with keys, names, and parent keys.

**Equivalent resource**: `zotero://collections`

---

### `get_collection`

Get details for a specific collection.

**Parameters**:

| Name | Type | Default | Description |
|------|------|---------|-------------|
| `key` | `str` | required | Collection key |

**Equivalent resource**: `zotero://collections/{key}`

---

### `get_collection_items`

Get all items within a collection.

**Parameters**:

| Name | Type | Default | Description |
|------|------|---------|-------------|
| `key` | `str` | required | Collection key |
| `limit` | `int` | `50` | Maximum items |

**Equivalent resource**: `zotero://collections/{key}/items`

---

### `get_collection_tree`

Get hierarchical tree of all collections (nested folder structure).

**Parameters**: none

**Returns**: Nested JSON tree showing parent/child collection relationships.

**Equivalent resource**: `zotero://collections/tree`

---

### `find_collection`

Find a collection by name (fuzzy match supported).

**Parameters**:

| Name | Type | Default | Description |
|------|------|---------|-------------|
| `name` | `str` | required | Collection name to search |
| `fuzzy` | `bool` | `True` | Enable fuzzy (approximate) matching |

**Returns**: Matching collection(s) with keys and names.

**Example prompt**: *"Find the 'AI Research 2024' collection"*

---

## Save Tools

> **Auto-fetch**: When a DOI or PMID is provided, these tools automatically fetch complete metadata from CrossRef/PubMed and store the Relative Citation Ratio (RCR) in Zotero's extra field.

### `interactive_save` ⭐

Save a reference with an interactive collection picker. Uses **MCP Elicitation** to show all available collections as numbered options and let you choose one.

**Parameters**:

| Name | Type | Default | Description |
|------|------|---------|-------------|
| `item_type` | `str` | required | Zotero item type (e.g. `"journalArticle"`) |
| `title` | `str` | required | Article/book title |
| `creators` | `list[dict]` | `None` | Author list `[{"firstName": "...", "lastName": "..."}]` |
| `doi` | `str` | `None` | DOI → auto-fetches full metadata from CrossRef |
| `pmid` | `str` | `None` | PubMed ID → auto-fetches full metadata + RCR |
| `isbn` | `str` | `None` | ISBN (for books) |
| `publication_title` | `str` | `None` | Journal/book name |
| `date` | `str` | `None` | Publication date (e.g. `"2024"`) |
| `abstract` | `str` | `None` | Abstract text |
| `url` | `str` | `None` | URL |
| `tags` | `list[str]` | `None` | Tags to apply |
| `skip_collection_prompt` | `bool` | `False` | Save to root without asking |
| `auto_fetch_metadata` | `bool` | `True` | Auto-fetch from CrossRef/PubMed |
| `include_citation_metrics` | `bool` | `True` | Fetch RCR from iCite |

**Example prompt**: *"Save DOI:10.1000/xyz to my Zotero"*

---

### `quick_save`

Save a reference directly to a named collection without the interactive picker.

**Parameters**:

| Name | Type | Default | Description |
|------|------|---------|-------------|
| `item_type` | `str` | required | Zotero item type |
| `title` | `str` | required | Article/book title |
| `collection_name` | `str` | `None` | Target collection name |
| `collection_key` | `str` | `None` | Target collection key |
| `doi` | `str` | `None` | DOI → auto-fetches metadata |
| `pmid` | `str` | `None` | PubMed ID → auto-fetches metadata + RCR |
| `creators` | `list[dict]` | `None` | Author list |
| `tags` | `list[str]` | `None` | Tags to apply |
| `auto_fetch_metadata` | `bool` | `True` | Auto-fetch from CrossRef/PubMed |

**Example prompt**: *"Quick save PMID:12345678 to 'AI Research'"*

---

## Saved Search Tools

> **Local API exclusive**: Saved searches can only be executed via the local Zotero API—the Zotero web API cannot run them.

### `list_saved_searches`

List all saved searches defined in Zotero.

**Parameters**: none

**Returns**: List of saved searches with keys, names, and condition counts.

**Equivalent resource**: `zotero://searches`

**Example prompt**: *"What saved searches do I have?"*

---

### `run_saved_search`

Execute a saved search and return matching items.

**Parameters**:

| Name | Type | Default | Description |
|------|------|---------|-------------|
| `search_key` | `str` | required | Saved search key |
| `limit` | `int` | `50` | Maximum results |

**Returns**: Items matching the saved search criteria.

**Example prompt**: *"Run the 'Missing PDF' saved search"*

---

### `get_saved_search_details`

Get the conditions/criteria defined in a saved search.

**Parameters**:

| Name | Type | Default | Description |
|------|------|---------|-------------|
| `search_key` | `str` | required | Saved search key |

**Equivalent resource**: `zotero://searches/{key}`

**Example prompt**: *"What conditions are in the 'Unread' saved search?"*

---

## Advanced Search Tools

### `advanced_search` ⭐

Multi-condition search with itemType filter, tag filter, sort, and search mode options.

**Parameters**:

| Name | Type | Default | Description |
|------|------|---------|-------------|
| `q` | `str` | `None` | Quick search query |
| `item_type` | `str` | `None` | Filter by type; prefix with `-` to exclude (e.g. `"-attachment"`) |
| `tag` | `str` | `None` | Single tag filter; use `\|\|` for OR (e.g. `"AI \|\| ML"`) |
| `tags` | `list[str]` | `None` | Multiple tags (AND logic) |
| `sort` | `str` | `"dateModified"` | Sort field (`dateModified`, `dateAdded`, `title`, `date`) |
| `direction` | `str` | `"desc"` | Sort direction (`asc`, `desc`) |
| `qmode` | `str` | `"titleCreatorYear"` | Search mode: `titleCreatorYear` or `everything` (searches abstracts too) |
| `limit` | `int` | `50` | Maximum results |
| `include_trashed` | `bool` | `False` | Include items in the trash |

**Examples**:
```python
# Find all journal articles
advanced_search(item_type="journalArticle")

# Search abstracts for "deep learning"
advanced_search(q="deep learning", qmode="everything")

# Find tagged AI papers sorted by date added
advanced_search(tag="AI", sort="dateAdded", direction="desc")

# Combined conditions
advanced_search(q="CRISPR", item_type="journalArticle", tags=["gene", "therapy"])
```

---

### `check_articles_owned`

Check whether a list of PMIDs already exist in your Zotero library.

**Parameters**:

| Name | Type | Default | Description |
|------|------|---------|-------------|
| `pmids` | `list[str]` | required | List of PubMed IDs to check |

**Returns**:
```json
{
  "owned": ["12345678"],
  "not_owned": ["99999999"],
  "owned_count": 1,
  "not_owned_count": 1
}
```

**Example prompt**: *"Do I already have PMID:12345678 in my library?"*

---

## Import Tools

### `import_articles` ⭐

The **single unified import entry point** for all article imports to Zotero. Accepts structured article dicts from pubmed-search-mcp or raw RIS text.

**Parameters**:

| Name | Type | Default | Description |
|------|------|---------|-------------|
| `articles` | `list[dict]` | `None` | Articles from `unified_search(..., output_format="json")` |
| `ris_text` | `str` | `None` | Alternative: RIS-format text to parse and import |
| `collection_name` | `str` | `None` | Target collection name (recommended) |
| `collection_key` | `str` | `None` | Target collection key (alternative) |
| `tags` | `list[str]` | `None` | Additional tags to apply to all imported items |
| `skip_duplicates` | `bool` | `True` | Skip articles already in Zotero (by PMID/DOI) |

> ⚠️ If `collection_name` or `collection_key` is provided but not found, the tool returns an error listing all available collections.

**Returns**:
```json
{
  "success": true,
  "imported": 8,
  "skipped": 2,
  "saved_to": "AI Research",
  "items": ["Title A", "Title B", "..."],
  "errors": []
}
```

**Example workflow**:
```python
# 1. Search with pubmed-search-mcp
results = unified_search("machine learning anesthesia", output_format="json")

# 2. (Optional) Filter out already-owned articles
owned = check_articles_owned([a["pmid"] for a in results["articles"] if a.get("pmid")])

# 3. Import to Zotero
import_articles(
    articles=results["articles"],
    collection_name="ML Anesthesia",
    tags=["ML", "2024"]
)
```

---

## Analytics Tools

### `get_library_stats`

Get statistics and distribution analysis of your entire Zotero library.

**Parameters**: none

**Returns**:
```json
{
  "total_items": 450,
  "by_type": { "journalArticle": 380, "book": 40, "thesis": 15 },
  "by_year": { "2024": 60, "2023": 90, "2022": 75 },
  "top_authors": [["Smith J", 20], ["Lee K", 15]],
  "top_journals": [["Nature", 12], ["Science", 10]],
  "tag_stats": { "total_unique_tags": 85, "most_used": [["AI", 30], ["review", 20]] },
  "collection_stats": { "total_collections": 12, "items_without_collection": 45 }
}
```

**Example prompt**: *"Give me a summary of my library"*

---

### `find_orphan_items`

Find items that are not assigned to any collection and/or have no tags—useful for library housekeeping.

**Parameters**:

| Name | Type | Default | Description |
|------|------|---------|-------------|
| `without_collection` | `bool` | `True` | Include items not in any collection |
| `without_tags` | `bool` | `False` | Include items with no tags |
| `limit` | `int` | `50` | Maximum results |

**Example prompt**: *"Which papers aren't organized into any collection?"*

---

## Attachment & Fulltext Tools

> Requires Zotero to have indexed the PDF. Set `ZOTERO_DATA_DIR` (e.g. `~/Zotero`) to get absolute file paths in the response.

### `get_item_attachments`

List all attachments (PDFs, snapshots, etc.) for a Zotero item.

**Parameters**:

| Name | Type | Default | Description |
|------|------|---------|-------------|
| `item_key` | `str` | required | Parent item key (8 characters, e.g. `"X42A7DEE"`) |

**Returns**:
```json
{
  "item_key": "X42A7DEE",
  "title": "Deep Learning in Medicine",
  "attachment_count": 1,
  "attachments": [
    {
      "key": "NHZFE5A7",
      "title": "Full Text PDF",
      "filename": "paper.pdf",
      "content_type": "application/pdf",
      "file_path": "/home/user/Zotero/storage/NHZFE5A7/paper.pdf",
      "file_exists": true,
      "file_size": 1048576,
      "link_mode": "imported_file"
    }
  ]
}
```

**Example prompt**: *"Does key:X42A7DEE have a PDF attached?"*

---

### `get_item_fulltext`

Get Zotero-indexed fulltext content for an item's PDF attachment.

**Parameters**:

| Name | Type | Default | Description |
|------|------|---------|-------------|
| `item_key` | `str` | required | Item key (parent item or attachment key) |

**Returns**:
```json
{
  "item_key": "X42A7DEE",
  "title": "Deep Learning in Medicine",
  "content": "Abstract: This paper describes...",
  "indexed_pages": 12,
  "total_pages": 15,
  "source": "NHZFE5A7 (Full Text PDF)"
}
```

> If fulltext is not yet indexed, Zotero may need time to process the PDF. You can use `get_item_attachments()` to get the file path for external PDF parsing tools.

**Example prompt**: *"Read the full text of key:X42A7DEE"*

---

## Legacy Tools (opt-in)

The following tools are **hidden by default** to avoid duplicating functionality with pubmed-search-mcp. Enable them by setting:

```bash
ZOTERO_KEEPER_ENABLE_LEGACY_PUBMED_TOOLS=1
```

| Tool | Description |
|------|-------------|
| `search_pubmed_exclude_owned` | Search PubMed and filter out articles already in Zotero |
| `import_from_pmids` | Import directly from a list of PMIDs |
| `quick_import_pmids` | Quick batch import from PMIDs |
| `import_ris_to_zotero` | Import from RIS file text |
| `batch_import_from_pubmed` | Batch import with PubMed search + collection targeting |

> These tools are intended for standalone use when pubmed-search-mcp is not available. For normal use, prefer the collaboration-safe workflow with `import_articles`.

---

## Environment Variables Summary

| Variable | Default | Description |
|----------|---------|-------------|
| `ZOTERO_HOST` | `localhost` | Zotero host address |
| `ZOTERO_PORT` | `23119` | Zotero local API port |
| `ZOTERO_TIMEOUT` | `30` | API request timeout (seconds) |
| `ZOTERO_DATA_DIR` | `""` | Path to Zotero data directory (for attachment file paths) |
| `NCBI_EMAIL` | `""` | Email for NCBI/PubMed API (higher rate limits) |
| `NCBI_API_KEY` | `""` | NCBI API key (optional; raises rate limit from 3 to 10 requests/second) |
| `ZOTERO_KEEPER_ENABLE_LEGACY_PUBMED_TOOLS` | `0` | Enable legacy PubMed bridge tools |
| `PUBMED_SEARCH_PATH` | `""` | Override pubmed-search-mcp path (dev only) |
