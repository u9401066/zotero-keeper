# Zotero Keeper MCP Server

Zotero Keeper 2.2.0 is an MCP SDK v2 server for managing local Zotero libraries via AI agents. It uses the v2 `MCPServer` API and is intentionally incompatible with an MCP SDK 1.x environment.

> The v0.8.0 VS Code extension is the recommended distribution for this 2.2 runtime. The commands below install from this source checkout. The separately published `uvx`/PyPI package may still be on an older release line until its own publication is complete.

See the [Zotero Keeper feature site](https://u9401066.github.io/zotero-keeper/) for the product tour and the documentation links below for precise tool contracts.

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
# Local Zotero (default; keep port 23119 on loopback)
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
- Do not point `ZOTERO_HOST` at a remotely exposed Local/Connector API. Local reads and Connector endpoints do not require authentication; Zotero 10+ Local writes use a runtime key but are still a loopback-only interface. For remote libraries, use Zotero's authenticated HTTPS Web API or a purpose-built authenticated service.
- `NCBI_EMAIL` and optional `NCBI_API_KEY` are passed through to pubmed-search-mcp for fetch and ownership-check workflows.
- `PUBMED_SEARCH_PATH` is only for local development when you want keeper to import a checked-out pubmed-search-mcp instead of the installed package.

By default, zotero-keeper runs in a collaboration-safe mode: PubMed search/discovery/export stays in pubmed-search-mcp, while zotero-keeper exposes the Zotero-side import and library tools.

## MCP Tools

### 🌟 Unified Import

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

### Public Tool Surface (41 default tools + 6 resources)

The default public surface combines connection, read, collection, save, search, import, analytics, attachment access, and narrow Zotero 10+ Local API write tools. MCP SDK v2 advertises six concrete browsable resources plus four parameterized URI templates.

### Zotero Compatibility

| Zotero Desktop | Read/search/resources | Connector save/import | 17 Local API tools | Attachment path discovery |
| -------------- | --------------------- | --------------------- | ------------------ | ------------------------- |
| 7, 8, 9 | Yes | Yes | No; returns `unsupported_local_write` | `ZOTERO_DATA_DIR` fallback |
| 10+ | Yes | Yes | Yes, after Zotero runtime authorization | Official `/file/view/url`, then fallback |

`interactive_save`, `quick_save`, `import_articles`, and `import_pdf` retain their Connector-based Zotero 7–10+ compatibility. The tools in the next section require Zotero 10+ and [Local API v3](https://www.zotero.org/support/dev/web_api/v3/local_api).

`check_connection()` probes Connector ping plus the non-mutating `GET /api/` capability endpoint and reports Zotero, Connector, Local API/schema, server-ID, and write-availability state. Zotero's Local API uses API version 3 only.

### Zotero 10+ Local Write Tools

```python
authorize_local_writes(require_remembered: bool = False)
create_collection(name, parent_collection_key=None, confirm=False, expected_server_id=None)
add_items_to_collection(item_keys, collection_key, confirm=False, expected_server_id=None)
remove_items_from_collection(item_keys, collection_key, confirm=False, expected_server_id=None)
update_item_fields(item_key, fields, expected_version, confirm=False, expected_server_id=None)
update_collection(collection_key, expected_version, name=None, parent_collection_key=None, move_to_library_root=False, confirm=False, expected_server_id=None)
delete_collection(collection_key, expected_version, confirm=False, expected_server_id=None)
delete_item(item_key, expected_version, confirm=False, expected_server_id=None)
create_note(parent_item_key, note_html, confirm=False, expected_server_id=None)
create_saved_search(name, conditions, confirm=False, expected_server_id=None)
update_saved_search(search_key, expected_version, name=None, conditions=None, confirm=False, expected_server_id=None)
delete_saved_search(search_key, expected_version, confirm=False, expected_server_id=None)
delete_tags(tags, expected_library_version, confirm=False, expected_server_id=None)
attach_file_to_item(item_key, file_path, title="Full Text PDF", confirm=False, expected_server_id=None)
replace_attachment_file(attachment_key, file_path, expected_version, expected_md5, confirm=False, expected_server_id=None)
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
set_attachment_fulltexts(entries, expected_library_version, confirm=False, expected_server_id=None)
```

The surface contains one authorization tool and 16 fail-closed mutation tools.
First obtain a response-bound
`server_id` from an exact Local API read or from `authorize_local_writes`; obtain
the response-bound object version for an update or single-object delete, or the
response-bound library cursor for tag deletion and single/batch full-text writes.
Attachment replacement additionally binds the reviewed object version and old
MD5. Then call the mutation with
`confirm=false` **and that `expected_server_id` already present**. The preview
returns `proposed` plus `confirmation_required=true` and performs no Zotero read,
authorization, filesystem probe, or write. After the user approves that complete
proposal, repeat it unchanged with `confirm=true`.

Call `authorize_local_writes(require_remembered=false)` for a single-write
operation if authorization was not already used to obtain the identity. Zotero
presents **Allow**, **Always Allow**, or **Deny**; Keeper holds the returned key in
memory and never exposes it in a tool schema or result. Before
`attach_file_to_item` or `replace_attachment_file`, call
`authorize_local_writes(require_remembered=true)`: Zotero must grant **Always
Allow** because the stored-file upload spans multiple writes. If authorization
returns a different `server_id` from the reviewed
proposal, discard the proposal, reread all targets/cursors, generate a new preview,
and obtain approval again. Never add or replace identity only after preview.

Safety constraints include:

- Every supplied Zotero object key must be an exact eight-character key.
- `add_items_to_collection` accepts at most 50 distinct items, validates the collection and every item before its single batch write, and preserves every existing collection membership. It does not remove or move items to the library root.
- `remove_items_from_collection` removes only the reviewed membership from up to 50 items. It rereads every item, uses that response's object version, preserves all other memberships, and can leave an item unfiled when the removed collection was its only membership.
- `update_item_fields` accepts only a non-empty mapping of finite scalar metadata. Structural fields such as `key`, `version`, `itemType`, `collections`, `tags`, `creators`, `relations`, `parentItem`, deletion state, and attachment-storage fields are rejected.
- `update_collection`, `update_saved_search`, and the three single-object delete tools accept the fresh exact object's `expected_version`; Keeper rereads that exact target and refuses a mismatch.
- `delete_collection` does not delete its library items, and `delete_saved_search` does not delete matching items. `delete_item` is a permanent single-item operation and may target a bibliographic item, note, attachment, or annotation, so its complete proposal must be reviewed carefully.
- `delete_tags` accepts one to 50 names and a response-bound library cursor because deleting a tag removes it library-wide. `set_attachment_fulltexts` accepts one to 10 attachment entries under one response-bound library cursor. Neither cursor is an attachment object version.
- `replace_attachment_file` is restricted to stored `imported_file`/`imported_url` attachments. It requires remembered authorization, the exact attachment version, and its previous MD5; both authenticated file phases use `If-Match` with that old hash.
- A stale identity, object version, library cursor, or file MD5 is a conflict and is never retried automatically. After HTTP 412, reread, preview, and ask for approval again.
- Keeper is not a raw Local API client. It does not expose arbitrary structural replacement, batch item/collection/saved-search deletion, or group-library writes. The public delete tools each target one reviewed object; `delete_tags` is the deliberately bounded library-cursor exception.

See [MCP Tools Reference](../docs/tools-reference.md#zotero-10-local-write-tools) for complete contracts and [Zotero write requests](https://www.zotero.org/support/dev/web_api/v3/write_requests) for the underlying official protocol.

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
| `create_collection` | Zotero 10+: create a top-level or nested collection after confirmation |
| `add_items_to_collection` | Zotero 10+: add up to 50 items while preserving other memberships |
| `remove_items_from_collection` | Zotero 10+: remove one exact membership from up to 50 items while preserving the rest |
| `update_collection` | Zotero 10+: rename or move one collection with its exact object version |
| `delete_collection` | Zotero 10+: delete one confirmed collection with its exact object version |

### Saved Search Tools 🌟 (execution is Local-only)

| Tool | Description |
| ---- | ----------- |
| `list_saved_searches` | List all saved searches |
| `run_saved_search` | Execute a saved search |
| `get_saved_search_details` | Get search conditions |
| `create_saved_search` | Zotero 10+: create a saved search after confirmation |
| `update_saved_search` | Zotero 10+: change one saved search's name and/or conditions with its exact version |
| `delete_saved_search` | Zotero 10+: delete one confirmed saved search with its exact version |

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
| `attach_file_to_item` | Zotero 10+: attach a stored file to an existing bibliographic item |
| `replace_attachment_file` | Zotero 10+: replace one stored attachment using its object version and old MD5 |
| `set_attachment_fulltext` | Zotero 10+: write indexed full text with a version precondition |
| `set_attachment_fulltexts` | Zotero 10+: write one to 10 indexed full-text entries under one library cursor |

### Metadata & Note Write Helpers

| Tool | Description |
| ---- | ----------- |
| `authorize_local_writes` | Request runtime approval; set `require_remembered=true` before an attachment upload |
| `update_item_fields` | Zotero 10+: update safe scalar metadata with optimistic concurrency |
| `delete_item` | Zotero 10+: delete one exact item with optimistic concurrency |
| `create_note` | Zotero 10+: create an HTML child note beneath an exact parent item |

### Other Read Helpers

| Tool | Description |
| ---- | ----------- |
| `list_tags` | List all tags |
| `delete_tags` | Zotero 10+: remove one to 50 exact tag names library-wide with a library cursor |
| `get_item_types` | Get available item types |

### PubMed Search MCP boundary

The v0.8.0 VSIX pins PubMed Search MCP 0.6.3 at commit
[`febf53a`](https://github.com/u9401066/pubmed-search-mcp/commit/febf53a8ff1ee253a625869ba251365f73a23c68).
That companion MCP SDK v2 server keeps its 45-tool, 16-category surface while
adding a durable SearchRun journal, replay-safe `read_session` views,
deterministic `systematic` search, bounded provider-native `native_semantic`
search, explicit source/run status and provenance, and stricter Research
Chronicle revisions with canonical Mermaid timeline artifacts. `systematic` and
`native_semantic` are mutually exclusive, and replay returns credential-free
arguments without executing another search.

PubMed discovery, session reuse, full text, citation exploration, export, and Research Chronicle work belong to PubMed Search MCP. Zotero Keeper owns the local library, duplicate check, collection choice, and final `import_articles` handoff.

Use the [PubMed Search MCP documentation site](https://u9401066.github.io/pubmed-search-mcp/) for its complete search and Chronicle workflows. Use the [Zotero Keeper feature site](https://u9401066.github.io/zotero-keeper/) for Keeper's library-management overview.

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

On Zotero 10+, `create_collection` can create a confirmed top-level or nested collection before a save. On Zotero 7–9, create the collection in the Zotero UI first. In every version:

1. Resolve or create the destination deliberately.
2. Let the AI classify into that exact collection.
3. Never omit the destination to imply root; use the explicit double-confirmation / `allow_library_root=true` path only when the user truly requests My Library.

---

## 🌟 Saved Search Feature (execution is Local-only)

Zotero APIs can represent saved-search metadata, but the Web API cannot execute saved searches; execution uses the Local API.

### How It Works

1. **Create a Saved Search** in Zotero's UI, or on Zotero 10+ with confirmed `create_saved_search`
2. **AI executes it anytime** via `run_saved_search`

### Step-by-Step Guide

#### Step 1: Create Saved Search

On Zotero 10+, first obtain a response-bound `server_id`, then preview and
confirm the unchanged MCP mutation:

```python
create_saved_search(
    name="Unread",
    conditions=[{"condition": "tag", "operator": "isNot", "value": "read"}],
    expected_server_id=server_id,
    confirm=False,
)
# After the user approves the exact proposal:
create_saved_search(
    name="Unread",
    conditions=[{"condition": "tag", "operator": "isNot", "value": "read"}],
    expected_server_id=server_id,
    confirm=True,
)
```

For Zotero 7–9, or when you prefer the UI:

1. Open Zotero
2. Press `Ctrl+Shift+F` (or **Edit → Advanced Search**)
3. Set conditions (see examples below)
4. Click **Save Search**
5. Give it a memorable name (e.g., "Missing PDF")

#### Step 2: Use via AI

```text
AI: "Which papers don't have PDFs?"
→ list_saved_searches()
→ run_saved_search(search_key="<exact key for Missing PDF>")

AI: "What did I add this week?"
→ list_saved_searches()
→ run_saved_search(search_key="<exact key for Recent Additions>")
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
