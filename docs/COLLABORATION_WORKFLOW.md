# Collaboration-Safe Workflow Guide

> How to run pubmed-search-mcp and zotero-keeper together without overlapping responsibilities.

## Why a Split Workflow?

- **pubmed-search-mcp** owns search, discovery, export, citation metrics, and unified article JSON contracts.
- **zotero-keeper** owns local-library work: duplicate checks, collection targeting, and the single public import handoff into Zotero.
- Default posture: keeper exposes only `import_articles` for PubMed handoff; legacy bridge tools stay hidden unless you opt in.
- Release baseline: VSIX 0.8.0 installs Zotero Keeper 2.2.0 (41 default tools, 6 concrete resources) and PubMed Search MCP 0.6.3 at `febf53a` (45 tools, 16 categories).

## Setup Checklist

1. **Prerequisites**
   - Zotero 7–10+ is running on the same machine (`127.0.0.1:23119`).
   - Python 3.12+ with `uv` installed (no `pip` usage).
2. **pubmed-search-mcp available**
   - If you work in this monorepo: `git submodule update --init --recursive` to populate `external/pubmed-search-mcp`.
   - Point keeper at a local checkout (optional) with `PUBMED_SEARCH_PATH=/absolute/path/to/pubmed-search-mcp`.
   - Otherwise, install and launch pubmed-search-mcp per its README (MCP SDK v2 `MCPServer`).
3. **keeper environment**
   - From `mcp-server/`: `uv sync --extra all`
   - Start with `uv run python -m zotero_mcp` (or use the VS Code extension’s MCP auto-start).
4. **Recommended env vars**
   - `NCBI_EMAIL` (and optional `NCBI_API_KEY`) for better PubMed throughput.
   - `ZOTERO_KEEPER_ENABLE_LEGACY_PUBMED_TOOLS=1` **only** if you intentionally need the old keeper-only PubMed bridge tools.

## Recommended PubMed → Zotero Flow

```python
# 1) Search in pubmed-search-mcp
results = unified_search("anesthesia AI", output_format="json")

# 2) Optional: filter against your Zotero library via keeper
pmids = [a.get("identifiers", {}).get("pmid") for a in results["articles"]]
owned = check_articles_owned(pmids=[pmid for pmid in pmids if pmid])

# 3) Import through keeper (single public handoff)
import_articles(
    articles=results["articles"],
    collection_name="AI Research",
    tags=["2024", "review"]
)
```

Guidance:
- Keep imports under `max_articles=100` per call.
- Use `collection_name` to route saves safely; Keeper validates against existing collections. On Zotero 10+, a missing destination collection can first be proposed and explicitly confirmed with `create_collection`. On Zotero 7–9, create it in the UI.
- Collection routing is fail-closed. `interactive_save` needs an exact collection key or double-confirmed `ROOT`; `skip_collection_prompt=True` aborts. `quick_save`, `import_articles`, and `import_pdf` reject a missing collection unless explicit user approval is represented by `allow_library_root=true`.
- Skip legacy tools unless a workflow explicitly requires them.
- Use SearchRun status and `read_session` replay instead of silently rerunning a
  partial/failed search. Use `build_research_chronicle` and
  `read_research_chronicle` for durable history; with 0.6.3, explicitly repeat
  the original scope when continuing a chronicle.

## Zotero 7–10+ Capability Matrix

| Workflow | Zotero 7/8/9 | Zotero 10+ |
|----------|--------------|------------|
| Search, reads, saved-search execution, MCP resources | Yes | Yes |
| `interactive_save`, `quick_save`, `import_articles`, `import_pdf` | Yes, through Connector endpoints | Yes, through Connector endpoints |
| Collection/search/note lifecycle, safe metadata, collection membership | UI only | Confirmed Local API v3 tools |
| Delete one exact item or exact tag names | UI only | Confirmed, versioned Local API v3 tools |
| Add/replace a stored file; single/batch indexed full text | UI or external workflow | Confirmed Local API v3 tools |
| Attachment file path | `ZOTERO_DATA_DIR` fallback | Official `/items/{key}/file/view/url`, then fallback |

Zotero 8's top-level annotation representation remains filtered from normal bibliographic search/list/statistics results. The write capability boundary is Zotero 10+, not the MCP client or operating system.

## Confirmed Zotero 10+ Mutations

The 17 Zotero 10+ tools are:

```python
authorize_local_writes(require_remembered: bool = False)
create_collection(name, parent_collection_key=None, confirm=False, expected_server_id=None)
update_collection(..., expected_version, confirm=False, expected_server_id=None)
delete_collection(collection_key, expected_version, confirm=False, expected_server_id=None)
add_items_to_collection(item_keys, collection_key, confirm=False, expected_server_id=None)
remove_items_from_collection(item_keys, collection_key, confirm=False, expected_server_id=None)
update_item_fields(item_key, fields, expected_version, confirm=False, expected_server_id=None)
delete_item(item_key, expected_version, confirm=False, expected_server_id=None)
create_note(parent_item_key, note_html, confirm=False, expected_server_id=None)
create_saved_search(name, conditions, confirm=False, expected_server_id=None)
update_saved_search(..., expected_version, confirm=False, expected_server_id=None)
delete_saved_search(search_key, expected_version, confirm=False, expected_server_id=None)
delete_tags(tags, expected_library_version, confirm=False, expected_server_id=None)
attach_file_to_item(item_key, file_path, title="Full Text PDF", confirm=False, expected_server_id=None)
replace_attachment_file(attachment_key, file_path, expected_version, expected_md5, confirm=False, expected_server_id=None)
set_attachment_fulltext(
    attachment_key, content, expected_library_version,
    indexed_pages=None, total_pages=None,
    indexed_chars=None, total_chars=None,
    confirm=False, expected_server_id=None,
)
set_attachment_fulltexts(entries, expected_library_version, confirm=False, expected_server_id=None)
```

Use this sequence for every mutation:

1. Before preview, obtain a response-bound `server_id` from an exact Local API
   read or `authorize_local_writes`. Use exact object versions for updates and
   single-object deletes; use a response-bound library cursor for tag deletion
   and full-text writes. Replacement also binds the exact attachment version
   and old MD5.
2. Call the intended mutation with `confirm=false` and include that identity as
   `expected_server_id` (plus the relevant version cursor). It returns a complete
   proposal and performs no reads, authorization, filesystem probes, or writes.
3. Ask the user to approve the exact target, identity, version cursor, and content.
   Collection/root choices are never inferred.
4. If not already authorized, call
   `authorize_local_writes(require_remembered=false)`. For
   `attach_file_to_item` or `replace_attachment_file`, use
   `require_remembered=true` and grant **Always Allow**.
   If authorization reports a different identity, discard the preview, reread,
   preview again, and obtain new approval.
5. Repeat the unchanged mutation with `confirm=true` and the reviewed
   `expected_server_id`.
6. Report the structured result. Do not retry a 412 conflict; start again from a
   fresh response-bound read/identity and approval.

Keeper never puts the runtime authorization key in MCP schema or output. Every
confirmed mutation is bound to the `Zotero-Server-ID` included in its preview.
Exact updates and single-object deletes use their response-bound object
version; tag deletion and full-text tools use a response-bound library version and bulk
`POST /api/users/0/fulltext` with `If-Unmodified-Since-Version`. Never supplement
identity only after preview. See Zotero's official [Local API](https://www.zotero.org/support/dev/web_api/v3/local_api), [write-request](https://www.zotero.org/support/dev/web_api/v3/write_requests), and [full-text](https://www.zotero.org/support/dev/web_api/v3/fulltext_content) documentation.

Collection membership tools validate the exact collection and all one-to-50
items before one batch write, preserve every unrelated membership, and report
per-item partial failures. Destructive tools delete only an exact reviewed
object or exact tag names; Keeper 2.2 still exposes no raw API, arbitrary
structural-array replacement, batch object delete, or group write.

`attach_file_to_item` and `replace_attachment_file` implement Zotero's
[three-phase stored-file upload](https://www.zotero.org/support/dev/web_api/v3/file_upload).
Replacement uses the same old MD5 as `If-Match` during authorization and
registration. A failure after child creation may return `partial=true` and
`attachment_key`; inspect the item in Zotero rather than blindly retrying.

## Troubleshooting

- **FileNotFoundError for `external/pubmed-search-mcp/src`**
  Run `git submodule update --init --recursive` (repo checkout) or set `PUBMED_SEARCH_PATH` to a local pubmed-search-mcp tree.

- **No pubmed-search-mcp running**
  `check_articles_owned` falls back to local PMID checks only. `import_articles` still works for JSON/RIS inputs but cannot fetch missing PubMed metadata.

- **Need to override paths**
  Use absolute paths in `PUBMED_SEARCH_PATH` and MCP configs; avoid relative paths when MCP servers start from editors.

- **Old MCP environment after upgrade**
  MCP SDK 2.x is incompatible with 1.x. In VS Code, run **Zotero MCP: Reinstall Python Environment** after upgrading from an older VSIX.

- **Adding another Zotero MCP server**
  Do not install the MCP Registry-listed community project `54yyyu/zotero-mcp` into Keeper's environment. Both distributions expose the `zotero_mcp` Python module; run the community server in a separate virtual environment and MCP process if you need it.

## Quick Verification

- Keeper: `uv run python tests/check_mcp.py` should discover the SDK v2 server surface; the default server has 41 tools, 6 concrete resources, and 4 URI templates.
- PubMed: start the pinned 0.6.3 server per its README and confirm the client discovers 45 tools before making a real `unified_search` call.
- Integration: invoke `check_connection` (keeper) and a small `unified_search` → `import_articles` chain before production use.
