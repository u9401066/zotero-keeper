# Zotero MCP Landscape

> Status checked: 2026-08-12. This document distinguishes project ownership from registry or connector distribution.

## Short answer

We did not find a Zotero-organization repository or Zotero documentation that publishes an official Zotero MCP server. A listing in an MCP registry, a curated connector catalog, or an app marketplace does not make a project an official Zotero product.

[`54yyyu/zotero-mcp`](https://github.com/54yyyu/zotero-mcp) is a feature-rich community server listed in the MCP Registry. It is not maintained by the Zotero organization. An OpenAI-curated Zotero connector is a separate connector product; it must not be described as Zotero's official MCP server, and this repository does not invent or promise a tool schema for it.

## Compared surfaces

| Surface | Ownership / status | Verified positioning | Installation boundary |
|---------|--------------------|----------------------|-----------------------|
| Zotero Keeper 2.1.0 | This repository | Local Zotero workflow with 32 default tools and 6 concrete resources: reads, fail-closed Connector imports, and eight confirmed/authorized Zotero 10+ mutations without a raw delete tool | Installed with PubMed Search MCP 0.6.1 in the v0.7.0 VSIX managed environment |
| `54yyyu/zotero-mcp` | Community project; MCP Registry-listed | Its own documentation describes library/collection/tag browsing, metadata and full-text access, semantic search, annotations and notes, adding records/files, and library-maintenance operations. Consult that project for its current tool contract | Must use a separate virtual environment and MCP process from Keeper |
| OpenAI-curated Zotero connector | Curated connector product; not a Zotero-organization server | Treat only its installed, discoverable connector contract as authoritative | Configure independently; do not assume its tools match either Python server |
| Zotero Web API | Official Zotero HTTPS API | Authenticated remote library access and supported CRUD operations | Preferred foundation for remote access |
| Zotero Local API v3 | Official Zotero Desktop local interface | Reads on supported Zotero releases; Zotero 10+ adds runtime-authorized item/collection/search/fulltext/file writes and instance/version preconditions | Loopback only; never expose port 23119 directly |
| Zotero Connector API | Official Zotero Desktop local interface | Session-scoped save/import operations used by Keeper's Zotero 7–10+ compatibility tools | Loopback only; not a general update/delete API |

## Why the Python environments must be separate

Zotero Keeper and the community `54yyyu/zotero-mcp` distribution both expose the Python module/package name `zotero_mcp`. Installing them into one environment can overwrite or shadow imports and console entry points. Version constraints alone cannot make two distributions safely own the same import namespace.

Use two isolated environments and two MCP server definitions:

```text
VS Code / MCP client
├─ Zotero Keeper process
│  └─ VSIX-managed venv: Keeper 2.1.0 + PubMed Search MCP 0.6.1
└─ Optional community Zotero MCP process
   └─ separate venv owned by that project
```

Do not add the community distribution to the VSIX-managed environment. Reinstalling or upgrading either project in the shared environment could silently change which `zotero_mcp` module starts.

## What the v0.7.0 VSIX guarantees

- Zotero Keeper 2.1.0 on `mcp>=2.0,<3`, using the SDK v2 `MCPServer` API.
- 32 default Keeper tools and 6 concrete resources; four parameterized resource templates are advertised separately.
- Fail-closed collection routing: exact-key or double-confirmed `ROOT` for `interactive_save`, and explicit `allow_library_root=true` after user confirmation for non-interactive root saves.
- Eight Zotero 10+ Local API tools: `authorize_local_writes` plus seven narrow mutations. Each preview already carries a response-bound `expected_server_id`; `confirm=false` has zero Zotero interactions, runtime keys never cross MCP, and no raw delete tool is exposed.
- Every confirmed mutation uses the Server-ID from its approved preview. Metadata updates use response-bound object versions; full-text replacement uses a response-bound library cursor and bulk `POST /api/users/0/fulltext`. HTTP 412 conflicts are surfaced and never retried automatically.
- Official three-phase stored-file upload for attaching a file to an existing parent, and `/items/{key}/file/view/url` path discovery with a `ZOTERO_DATA_DIR` fallback.
- PubMed Search MCP 0.6.1 pinned to commit `ad85dde`, with 45 tools in 16 categories.
- `build_research_chronicle` and `read_research_chronicle` in place of the former three timeline tools.
- An isolated Python 3.12 environment. MCP SDK 1.x and 2.x are not mixed.

The separately published PyPI/`uvx` package can remain on an older release line. Use the Marketplace VSIX when you need this exact paired runtime.

## Zotero 7–10+ boundary

| Surface | Zotero 7/8/9 | Zotero 10+ |
|---------|--------------|------------|
| Keeper read/search/resource tools | Supported | Supported |
| Connector-based save/import tools | Supported | Supported |
| Authorized Local API write tools | Not available | Supported |
| Attachment path discovery | `ZOTERO_DATA_DIR` fallback | Official file-view URL, then fallback |

The official Zotero 10+ Local API can POST/PUT/PATCH/DELETE items, collections, and saved searches, write full text, and upload stored files. Keeper exposes a deliberately narrower, confirmation-gated task surface: create a collection/note/saved search, add collection membership, update safe scalar metadata, attach a file, and set indexed full text. Metadata/full-text replacement is accurately marked destructive in MCP annotations, while generic requests and delete tools remain unexposed. API capability does not imply that Keeper provides the full raw API through MCP.

Local writes require a key obtained from Zotero's own approval dialog. **Allow**
is single-use; **Always Allow** is reusable. Keeper requests the latter
explicitly with `authorize_local_writes(require_remembered=true)` before its
multi-write file upload. Every Local API response identifies the instance with
`Zotero-Server-ID`. Keeper obtains that response-bound identity before preview,
includes it in the approved proposal, and requires it on confirmed execution.
If authorization identifies another database, the read, preview, and approval
must be repeated; identity is never added after preview. Stored-file attachment
follows Zotero's [three-phase upload protocol](https://www.zotero.org/support/dev/web_api/v3/file_upload).

## Remote-access safety

Zotero's Local reads and Connector endpoints do not require authentication and are intended for local applications. Zotero 10+ Local writes add runtime authorization, but port 23119 is still not a remotely hardened service. Keep it bound to loopback and run Keeper beside Zotero Desktop on the same trusted host. Do not expose or forward it to a LAN or the Internet.

For remote access, use the [official Zotero Web API](https://www.zotero.org/support/dev/web_api/v3/start) over authenticated HTTPS, or a purpose-built authenticated service with TLS, authorization, auditing, and explicit network access control.

## Source links

- [Zotero organization on GitHub](https://github.com/zotero)
- [Zotero developer documentation](https://www.zotero.org/support/dev/start)
- [Zotero Local API](https://www.zotero.org/support/dev/web_api/v3/local_api)
- [Zotero write requests and version preconditions](https://www.zotero.org/support/dev/web_api/v3/write_requests)
- [Zotero file upload](https://www.zotero.org/support/dev/web_api/v3/file_upload)
- [Zotero full-text content](https://www.zotero.org/support/dev/web_api/v3/fulltext_content)
- [`54yyyu/zotero-mcp` community project](https://github.com/54yyyu/zotero-mcp)
- [Model Context Protocol Registry](https://registry.modelcontextprotocol.io/)
- [Zotero Web API v3](https://www.zotero.org/support/dev/web_api/v3/start)
