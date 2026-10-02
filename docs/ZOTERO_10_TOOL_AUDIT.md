# Zotero 10.0.5 / Keeper 2.4 tool audit

Audit date: 2026-10-02 (previous audit: 2026-09-17 against 10.0.2). Default MCP
SDK v2 surface: **50 tools, 6 concrete resources, 4 resource templates**. Legacy
PubMed bridge tools stay opt-in.

Zotero 10.0.3–10.0.5 contain no Local API contract change that Keeper depends on.
10.0.5 fixes object writes that supply **client-chosen keys**; Keeper never
supplies keys (Zotero allocates them), so no code path is affected. 10.0.5 also
stops matching an item through a trashed child in searches, which only makes
`advanced_search`/saved-search results more accurate.

The baseline is the official [Zotero changelog](https://www.zotero.org/support/changelog),
[Local API v3 contract](https://www.zotero.org/support/dev/web_api/v3/local_api),
and [10.0.2 endpoint implementation](https://github.com/zotero/zotero/blob/d9e553b60cf0a06aac3029e7117c5666b6cc1e6a/chrome/content/zotero/xpcom/server/server_localAPI.js).
Search serialization was checked against [search.js](https://github.com/zotero/zotero/blob/d9e553b60cf0a06aac3029e7117c5666b6cc1e6a/chrome/content/zotero/xpcom/data/search.js)
and [search conditions](https://github.com/zotero/zotero/blob/d9e553b60cf0a06aac3029e7117c5666b6cc1e6a/chrome/content/zotero/xpcom/data/searchConditions.js).

## All default tools

| Group | Tools reviewed | Design / coverage |
|---|---|---|
| Connection (1) | `check_connection` | Read discovery and capabilities; never returns authorization key |
| Basic reads (5) | `search_items`, `get_item`, `list_items`, `list_tags`, `get_item_types` | Response-bound versions/identity where applicable; exact item retains note/annotation/attachment fields; all returned tags retained |
| Collections (5) | `list_collections`, `get_collection`, `get_collection_items`, `get_collection_tree`, `find_collection` | Hierarchy and exact keys; duplicate names now fail instead of selecting the first |
| Save (2) | `interactive_save`, `quick_save` | Connector compatibility, metadata enrichment, duplicate/destination checks; explicit root opt-in |
| Saved-search reads (3) | `list_saved_searches`, `get_saved_search_details`, `run_saved_search` | Existing Zotero search execution, start/limit pagination, four result levels, profile-switch rejection |
| Search/ownership (2) | `advanced_search`, `check_articles_owned` | Structured filters and pagination; ownership traverses pages, read failures no longer become empty ownership |
| Import (2) | `import_articles`, `import_pdf` | Structured/RIS and local PDF handoff; validates destination; no silent root import |
| Analytics (2) | `get_library_stats`, `find_orphan_items` | Bounded 5,000-record scan, now explicitly reports scanned_count/scan_limit/possibly_truncated; not an unbounded full-library guarantee |
| Attachments (2) | `get_item_attachments`, `get_item_fulltext` | Children, official file URL/path and indexed text; response-bound fulltext library cursor |
| Authorization (1) | `authorize_local_writes` | Zotero-controlled prompt, Server-ID binding, no key in result |
| Collection writes (5) | `create_collection`, `update_collection`, `delete_collection`, `add_items_to_collection`, `remove_items_from_collection` | Narrow reviewed changes, exact objects; membership preserves unrelated collections; partial batch status |
| Item writes (3) | `update_item_fields`, `delete_item`, `create_note` | Scalar metadata only, irreversible exact deletion explicit, child-note parent validated |
| Search writes (3) | `create_saved_search`, `update_saved_search`, `delete_saved_search` | Exact object version for edit/delete; nested groups, resultLevel and condition/mode wire format |
| Tag deletion (1) | `delete_tags` | Exact tag names, library cursor, proper multi-tag encoding |
| File writes (2) | `attach_file_to_item`, `replace_attachment_file` | Three-phase upload, remembered permission, size/checksum/identity checks, no blind replay |
| Fulltext writes (2) | `set_attachment_fulltext`, `set_attachment_fulltexts` | Library cursor (not object version), bulk POST, max 10, individual failure reporting |
| New item reads (2) | `get_item_schema`, `get_item_annotations` | Runtime item-type fields/creator roles; exact attachment annotations retaining text/comment/color/position fields |
| New item writes (5) | `update_item_tags`, `update_item_creators`, `update_note`, `set_item_trashed`, `batch_update_item_fields` | Exact object versions; preserve unrelated tags, ordered creator replacement, exact note HTML, recoverable trash/restore, max 50 metadata patches |
| Export (2) | `export_items`, `get_bibliography` | Read-only. Zotero translators (`format=bibtex/ris/csljson/…`) and CSL rendering (`include=bib,citation&style=`) for ≤50 exact keys; missing keys reported, never silently dropped |

## Zotero 10 search semantics

- `groupStart` / `groupEnd` have the string operator `"true"`, balanced nesting;
  `joinMode` uses `all` or `any`. Keeper accepts up to 200 conditions / 10 levels.
- `resultLevel` selects `item`, `attachment`, `note`, or `annotation`.
  `run_saved_search` no longer silently removes child results. To request the old
  parent-oriented view use `include_children=false`; page offsets count raw rows.
- Fulltext modes serialize as `fulltextContent/regexp` (or supply `mode="regexp"`
  for normalization). Zotero's JSON loader ignores a separate `required` property;
  Keeper rejects `required=true` rather than promising semantics that won't run.
- New server-recognized fields/operators (annotation type/color/author, attachment
  storage, counts, empty/nonempty) pass through saved-search conditions; Zotero
  validates them. `advanced_search` is a quick-filter tool, not a substitute for
  nested saved-search conditions.

## Endpoint families and intentional boundaries

| Local API family | Keeper mapping / limitation |
|---|---|
| Root + local authorization | Discovery/check_connection + authorize_local_writes |
| Item types/type fields/type creator roles | get_item_types + get_item_schema; whole raw schema/itemFields/creatorFields not separately exposed |
| Items/list/top/trash/search/children | Read/search/import/edit/annotation tasks; trash included via advanced_search; `format=` translators and `include=bib,citation` through `export_items`/`get_bibliography`; specialized publications, `format=keys/versions`, `since` and `/deleted` incremental reads not exposed |
| Collections and nested collections | Read/tree/lifecycle/membership tasks; no raw batch collection deletion |
| Saved searches and search items | Full task lifecycle + execution; no raw batch search deletion |
| Tags | Read/add/remove/delete; no dedicated single-tag endpoint wrapper |
| File/file-view/upload | Official paths, attach/replace tasks; no browser-launching or raw upload-key tool |
| Item fulltext/library fulltext | Read text/cursor and guarded single/bulk text setting; no index-maintenance or OCR guarantee |
| Groups, settings, publications | Not exposed as public MCP operations; current scope is My Library, not cross-library administration |

This is **not unrestricted API parity**. Arbitrary PUT/PATCH, arbitrary item
creation through raw Local API, relation/reparent/type changes, annotation
creation/editing, duplicate merge, raw batch object deletion and group-library
operations remain outside the public allowlist. Connector imports remain the
cross-version creation route. Desktop-only GUI undo, events and advanced search
UI are not Local API features; do not promise them through MCP.

## Reviewed and deliberately not implemented

| Candidate | Decision |
|---|---|
| Replay a timed-out create with the same `Zotero-Write-Token` | Rejected. Keeper already sends a fresh token on every create, but tokens live only in Zotero's memory and a first request may have committed; the no-replay rule stays. Callers re-read and decide. |
| Native `POST /items` creation for imports | Deferred. Connector `saveItems` remains the cross-version route (Zotero 7–9) and gives translator-quality parent/attachment handling; a 10+-only second path needs live-GUI validation first. |
| Read-only group libraries, `since`/`/deleted` incremental sync | Candidates for a later release; need an explicit library-scoping design because local keys are unscoped. |
| Relations / reparent / item-type change, annotation creation | Remain outside the allowlist (data-loss and identity risk). |

## Confirmation and verification

All 21 confirmed Local API mutations use zero-I/O previews, require the approved
Server-ID on execution, and do not retry a 412. Previews are proposals, not server
validation. Reads supply the exact object version, library cursor, or attachment
MD5 required by the task. Authorization that changes identity invalidates approval.
Creator replacement and note replacement may clear existing values; empty lists/HTML
are explicit operations. Batch metadata writes preflight all keys/versions, but
the final Zotero POST can still partially succeed: inspect each result.

Verification includes SDK schema discovery, mocked HTTP/version/identity tests,
actual tool-function tests, managed-venv installation against pinned PubMed 0.7.7,
and extension/VSIX harness checks. These do **not** claim a live GUI authorization
or mutation test against the user's Zotero library; no such writes are performed.
