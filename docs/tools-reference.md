# MCP Tools Reference

Complete reference for all 32 default MCP tools exposed by Zotero Keeper 2.1.0
on MCP SDK v2, plus five legacy opt-in tools.

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
9. [Zotero 10+ Local Write Tools](#zotero-10-local-write-tools)
10. [Legacy Tools (opt-in)](#legacy-tools-opt-in)
11. [Environment Variables Summary](#environment-variables-summary)

---

## Core Tools

### `check_connection`

Test connectivity to the local Zotero application.

**Parameters**: none

**Returns**:
```json
{
  "connected": true,
  "endpoint": "http://localhost:23119",
  "zotero_version": "10.x",
  "connector_api_version": "3",
  "local_api_readable": true,
  "local_api_version": "3",
  "capabilities": {
    "local_api_server_id": "current-zotero-instance-id",
    "local_api_write_available": true,
    "local_api_write_authorized": false
  }
}
```

Keeper probes the bare Local API `GET /api/` capability endpoint. Zotero's Local API speaks only API v3; `local_api_write_available=true` additionally requires the Zotero 10+ `Zotero-Server-ID` contract. Capability probing does not mutate the library.

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

**Returns**: Full item metadata including the response-bound `server_id`, object
`version`, `version_scope: "local"`, abstract, DOI, authors, journal, year, tags,
and collections. The identity and object version come from the same HTTP
response snapshot; use that pair for `update_item_fields` and never combine a
version with a separately cached identity.

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

**Returns**: Flat list of all collections with keys, names, parent keys, local
object versions, and the response-bound `server_id` for that one collection-list
snapshot.

**Equivalent resource**: `zotero://collections`

---

### `get_collection`

Get details for a specific collection.

**Parameters**:

| Name | Type | Default | Description |
|------|------|---------|-------------|
| `key` | `str` | required | Collection key |

**Returns**: Collection details with a local object version and the
response-bound `server_id` from the same exact-collection response.

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

Save a reference with an interactive collection picker. MCP v2
`Resolve`/`Elicit` dependencies ask for duplicate approval and an exact
collection key across both modern and legacy protocol connections. Choosing
`ROOT` triggers a second explicit confirmation.

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
| `skip_collection_prompt` | `bool` | `False` | Deprecated safety switch; `True` aborts instead of writing to root |
| `auto_fetch_metadata` | `bool` | `True` | Auto-fetch from CrossRef/PubMed |
| `include_citation_metrics` | `bool` | `True` | Fetch RCR from iCite |
| `extra_fields` | `dict` | `None` | Additional Zotero fields as an object |

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
| `force_add` | `bool` | `False` | Explicitly bypass duplicate blocking |
| `allow_library_root` | `bool` | `False` | Explicitly allow saving outside every collection |
| `auto_fetch_metadata` | `bool` | `True` | Auto-fetch from CrossRef/PubMed |
| `include_citation_metrics` | `bool` | `True` | Fetch RCR from iCite |
| `extra_fields` | `dict` | `None` | Additional Zotero fields as an object |

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
  "new": ["99999999"],
  "owned_count": 1,
  "new_count": 1,
  "total": 2,
  "details": {}
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
| `allow_library_root` | `bool` | `False` | Explicitly allow importing outside every collection |

> ⚠️ A collection is required by default. If a named/keyed collection is not
> found, the tool returns an error. Set `allow_library_root=true` only after the
> user explicitly confirms a My Library root import.

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
pmids = [a.get("identifiers", {}).get("pmid") for a in results["articles"]]
owned = check_articles_owned(pmids=[pmid for pmid in pmids if pmid])

# 3. Import to Zotero
import_articles(
    articles=results["articles"],
    collection_name="ML Anesthesia",
    tags=["ML", "2024"]
)
```

---

### `import_pdf` 📎

Import a **local PDF file** into Zotero using the Connector API — **no Web API key required** (stays within the Local/Connector architecture).

**Two modes**:
- **Metadata mode** (recommended): provide `article` (a unified article dict, e.g. from `fetch_article_details`) or a `title`. Creates a parent item with that metadata in the chosen collection and attaches the PDF to it.
- **Auto-recognize mode** (default when no metadata): saves the PDF as a standalone attachment and lets Zotero extract the DOI/title and build the parent item automatically.

**Parameters**:

| Name | Type | Default | Description |
|------|------|---------|-------------|
| `file_path` | `str` | — | Absolute path to a local PDF on the machine running the MCP server |
| `title` | `str` | `None` | Parent-item title when no `article` is given |
| `article` | `dict` | `None` | Unified article dict to build a rich parent item |
| `collection_name` | `str` | `None` | Target collection name (metadata mode) |
| `collection_key` | `str` | `None` | Target collection key (metadata mode) |
| `tags` | `list[str]` | `None` | Extra tags for the parent item (metadata mode) |
| `allow_library_root` | `bool` | `False` | Explicitly allow a parent/standalone PDF outside every collection |

> `import_pdf` remains a Connector/session-scoped Zotero 7–10+ workflow: it creates the parent itself or uses standalone auto-recognition. On Zotero 10+, use the separate confirmed `attach_file_to_item` tool to upload a file beneath a **pre-existing** bibliographic item.

**Example**:
```python
# Auto-recognize writes a standalone attachment to My Library, so confirm it.
import_pdf(file_path="/home/me/papers/smith2024.pdf", allow_library_root=True)

# Attach a PDF to a parent built from PubMed metadata
details = fetch_article_details(pmid="38353755")
import_pdf(
    file_path="/home/me/papers/ai-anesthesia.pdf",
    article=details,
    collection_name="AI Anesthesia",
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

> Zotero must have indexed a PDF before `get_item_fulltext` can return its text. On Zotero 10+, attachment paths are discovered first through the official Local API `/items/{key}/file/view/url` response. Keeper URL-decodes the returned `file://` URL and handles local platform paths; a missing or unsupported endpoint falls back to `ZOTERO_DATA_DIR` when configured.

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
  "library_version": 314,
  "server_id": "current-zotero-instance-id",
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
      "file_path_source": "local_api",
      "version": 42,
      "object_version": 42,
      "server_id": "current-zotero-instance-id",
      "link_mode": "imported_file"
    }
  ]
}
```

`library_version` and `server_id` form the response-bound cursor pair for
`set_attachment_fulltext`. The per-attachment `object_version` is for object
metadata operations and must not be substituted for that library cursor.

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
  "library_version": 314,
  "server_id": "current-zotero-instance-id",
  "source": "NHZFE5A7 (Full Text PDF)"
}
```

The full-text response binds its `library_version` cursor to `server_id`; pass
that pair into the preview of `set_attachment_fulltext`.

> If fulltext is not yet indexed, Zotero may need time to process the PDF. You can use `get_item_attachments()` to get the file path for external PDF parsing tools.

**Example prompt**: *"Read the full text of key:X42A7DEE"*

---

## Zotero 10+ Local Write Tools

These eight tools use Zotero 10+'s official [Local API v3](https://www.zotero.org/support/dev/web_api/v3/local_api). Zotero 7–9 continue to support Keeper's read and Connector-based save/import tools, but calls to this section's Local write surface return `unsupported_local_write`.

### Confirmation and authorization workflow

For each of the seven mutation tools:

1. Obtain a response-bound `server_id` from an exact Local API read or from
   `authorize_local_writes`. For `update_item_fields`, obtain the response-bound
   object version from the exact-item read. For `set_attachment_fulltext`,
   obtain the response-bound library cursor from `get_item_attachments` or
   `get_item_fulltext`.
2. Call the mutation with `confirm=false` and include that identity as
   `expected_server_id` (and the relevant version cursor). This performs **zero
   Zotero reads, authorization requests, filesystem probes, or writes**.
3. Obtain the user's explicit approval for the complete proposal, including its
   identity and version cursor.
4. If authorization is still needed, call
   `authorize_local_writes(require_remembered=false)`. Before
   `attach_file_to_item`, use `require_remembered=true`; Zotero must grant
   **Always Allow** because the upload spans multiple writes. If authorization
   returns a different identity, discard the proposal, reread, preview again,
   and obtain new approval.
5. Call the mutation again with unchanged arguments, `confirm=true`, and the
   reviewed `expected_server_id`.

The runtime Local API key is retained only in the Keeper process. It is never
an MCP input and never appears in a tool result. Every confirmed mutation
requires its reviewed response-bound `expected_server_id`; identity cannot be
added only after preview. A missing server precondition is reported as HTTP
428, while a changed server or stale version cursor is reported as HTTP 412.
Keeper does not retry a 412 write.

All mutation tools are annotated `readOnlyHint=false` and `openWorldHint=false`.
The two replacement-style operations, `update_item_fields` and
`set_attachment_fulltext`, honestly advertise `destructiveHint=true`; the
additive create/organize/upload tools advertise `false`. The collection,
metadata, and full-text update tools are idempotent; create/upload tools and
authorization are not. Keeper 2.1.0 deliberately exposes no raw delete MCP
tool.

The common preview shape is:

```json
{
  "success": false,
  "operation": "create_collection",
  "confirmation_required": true,
  "proposed": {
    "name": "AI Research",
    "parent_collection_key": null,
    "expected_server_id": "current-zotero-instance-id"
  }
}
```

Failures use a stable `error` object with `code`, `message`, `http_status`, and `retry_after`. See Zotero's official [write-request preconditions](https://www.zotero.org/support/dev/web_api/v3/write_requests).

### `authorize_local_writes`

```python
authorize_local_writes(require_remembered: bool = False)
```

Requests Zotero's own runtime write-authorization dialog through `POST /api/local/authorize`. This is a permission action, not a library mutation.

**Parameters**:

| Name | Type | Default | Description |
|------|------|---------|-------------|
| `require_remembered` | `bool` | `False` | Require reusable **Always Allow** authorization; set `True` before `attach_file_to_item` |

**Returns**:

```json
{
  "success": true,
  "operation": "authorize_local_writes",
  "authorized": true,
  "remembered": true,
  "remembered_required": true,
  "server_id": "current-zotero-instance-id"
}
```

`remembered=true` corresponds to reusable **Always Allow** approval. A one-use **Allow** key is consumed by the first validated write. When `require_remembered=true`, authorization succeeds only with reusable approval; the secret itself is never returned.

---

### `create_collection`

```python
create_collection(name, parent_collection_key=None, confirm=False, expected_server_id=None)
```

Create a top-level collection, or a child beneath an exact existing collection.

| Name | Type | Default | Description |
|------|------|---------|-------------|
| `name` | `str` | required | Non-empty collection name |
| `parent_collection_key` | `str` | `None` | Exact eight-character parent collection key; omit for top level |
| `confirm` | `bool` | `False` | `False` previews only; `True` performs the confirmed write |
| `expected_server_id` | `str` | `None` | Response-bound Zotero identity; operationally required in preview and confirmed execution |

When a parent is supplied, Keeper reads and verifies that exact parent before writing. This tool creates collection structure; it does not imply permission to save items to My Library root.

---

### `add_items_to_collection`

```python
add_items_to_collection(item_keys, collection_key, confirm=False, expected_server_id=None)
```

Add between one and 50 distinct exact items to a collection.

| Name | Type | Default | Description |
|------|------|---------|-------------|
| `item_keys` | `list[str]` | required | One to 50 exact eight-character item keys; duplicates are coalesced |
| `collection_key` | `str` | required | Exact eight-character destination collection key |
| `confirm` | `bool` | `False` | `False` previews only; `True` performs the confirmed batch write |
| `expected_server_id` | `str` | `None` | Identity from the same response snapshot used to select the collection/items; required for the reviewed operation |

With `confirm=true`, Keeper first completes every destination/item read and exact-key validation. It then merges the destination into each item's **complete** `collections` array, preserving all other memberships, and sends at most one 50-item batch POST. Items already present are `unchanged`. A mixed Zotero batch response has `partial=true` and an ordered per-item `updated`, `unchanged`, or `failed` status; 412 failures are not retried. This tool never removes a membership or moves an item to My Library root.

---

### `update_item_fields`

```python
update_item_fields(item_key, fields, expected_version, confirm=False, expected_server_id=None)
```

Patch safe scalar metadata on one exact bibliographic parent item.

| Name | Type | Default | Description |
|------|------|---------|-------------|
| `item_key` | `str` | required | Exact eight-character bibliographic item key |
| `fields` | `dict[str, scalar]` | required | Non-empty mapping of strings to finite JSON string/number/boolean scalars |
| `expected_version` | `int` | required | Response-bound object version from the fresh exact-item read |
| `confirm` | `bool` | `False` | `False` previews only; `True` performs the confirmed PATCH |
| `expected_server_id` | `str` | `None` | `server_id` paired with `expected_version` in that exact-item response; required for preview and execution |

The tool rejects child notes, attachments, and annotations. It also rejects structural or sensitive fields including `key`, `version`, `itemType`, `collections`, `tags`, `creators`, `relations`, `parentItem`, `deleted`, `dateAdded`, `dateModified`, `linkMode`, `filename`, `contentType`, `charset`, `md5`, `mtime`, and `note`. Use a dedicated safe tool for structure. A stale version returns `version_conflict` with HTTP 412 and no retry.

---

### `create_note`

```python
create_note(parent_item_key, note_html, confirm=False, expected_server_id=None)
```

Create an HTML child note beneath an exact bibliographic parent.

| Name | Type | Default | Description |
|------|------|---------|-------------|
| `parent_item_key` | `str` | required | Exact eight-character bibliographic parent key |
| `note_html` | `str` | required | Non-empty Zotero note HTML |
| `confirm` | `bool` | `False` | `False` previews the complete HTML; `True` creates the note |
| `expected_server_id` | `str` | `None` | Response-bound Zotero identity included in the approved preview; required for execution |

Keeper validates the exact parent and rejects attachment, annotation, or note parents. Treat all HTML in the preview as untrusted content when rendering it outside Zotero.

---

### `create_saved_search`

```python
create_saved_search(name, conditions, confirm=False, expected_server_id=None)
```

Create a saved-search definition that `run_saved_search` can execute locally.

| Name | Type | Default | Description |
|------|------|---------|-------------|
| `name` | `str` | required | Non-empty saved-search name |
| `conditions` | `list[dict]` | required | Non-empty condition list |
| `confirm` | `bool` | `False` | `False` previews only; `True` creates the search |
| `expected_server_id` | `str` | `None` | Response-bound Zotero identity included in the approved preview; required for execution |

Each condition requires scalar `condition`, `operator`, and `value` fields. Optional supported fields are boolean `required` and string `mode`; unknown fields are rejected. Saved-search metadata can be represented by Zotero APIs, but execution is a Zotero Local API feature.

---

### `attach_file_to_item`

```python
attach_file_to_item(item_key, file_path, title="Full Text PDF", confirm=False, expected_server_id=None)
```

Upload a stored local file beneath an exact existing bibliographic parent.

| Name | Type | Default | Description |
|------|------|---------|-------------|
| `item_key` | `str` | required | Exact eight-character bibliographic parent key |
| `file_path` | `str` | required | Path on the same machine as Keeper and Zotero Desktop |
| `title` | `str` | `"Full Text PDF"` | Non-empty attachment title |
| `confirm` | `bool` | `False` | `False` previews without inspecting the filesystem; `True` uploads |
| `expected_server_id` | `str` | `None` | Identity returned by the remembered authorization/read and included in the approved preview; required for execution |

After confirmation, Keeper verifies the file and parent, creates the attachment object, authorizes the file with MD5/name/size/mtime and a version precondition, uploads bytes to the loopback upload URL, and finalizes the attachment. This implements Zotero's official [three-phase file upload](https://www.zotero.org/support/dev/web_api/v3/file_upload). Local uploads are stored files under 4 GB; the Local API does not provide binary-diff uploads.

Call `authorize_local_writes(require_remembered=true)` before this tool and grant **Always Allow** in Zotero. If a later upload phase fails after the attachment child was created, the structured error can include `partial=true` and `attachment_key`, allowing explicit cleanup in the Zotero UI. No raw delete tool is exposed.

---

### `set_attachment_fulltext`

```python
set_attachment_fulltext(
    attachment_key,
    content,
    expected_library_version,
    indexed_pages=None,
    total_pages=None,
    indexed_chars=None,
    total_chars=None,
    confirm=False,
    expected_server_id=None,
)
```

Write indexed text for one exact attachment using Zotero's [full-text content endpoint](https://www.zotero.org/support/dev/web_api/v3/fulltext_content).

| Name | Type | Default | Description |
|------|------|---------|-------------|
| `attachment_key` | `str` | required | Exact eight-character attachment key |
| `content` | `str` | required | Non-empty extracted/indexed text |
| `expected_library_version` | `int` | required | Response-bound library cursor from `get_item_attachments` or `get_item_fulltext`; not an attachment object version |
| `indexed_pages`, `total_pages` | `int` | `None` | Supply this complete non-negative pair for paged content |
| `indexed_chars`, `total_chars` | `int` | `None` | Or supply this complete non-negative pair for character-counted content |
| `confirm` | `bool` | `False` | `False` previews only; `True` performs the confirmed bulk write |
| `expected_server_id` | `str` | `None` | `server_id` paired with `expected_library_version`; required for preview and execution |

Supply exactly one complete count pair, and keep the indexed count less than or
equal to its total. The tool verifies the response-bound Server-ID/library
cursor pair and the exact attachment target, then uses bulk
`POST /api/users/0/fulltext` with `If-Unmodified-Since-Version`. A stale library
cursor or changed identity returns HTTP 412 without a write or retry. This sets
Zotero's searchable index content and does not replace the attachment binary.

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
| `ZOTERO_DATA_DIR` | `""` | Optional attachment-path fallback when the official file-view URL is unavailable |
| `NCBI_EMAIL` | `""` | Email for NCBI/PubMed API (higher rate limits) |
| `NCBI_API_KEY` | `""` | NCBI API key (optional; raises rate limit from 3 to 10 requests/second) |
| `ZOTERO_KEEPER_ENABLE_LEGACY_PUBMED_TOOLS` | `0` | Enable legacy PubMed bridge tools |
| `PUBMED_SEARCH_PATH` | `""` | Override pubmed-search-mcp path (dev only) |
