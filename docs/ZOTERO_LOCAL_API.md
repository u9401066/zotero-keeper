# Zotero Local API v3: Platform Capabilities and Keeper Contract

Last verified: 2026-08-12 against Zotero's official Local API documentation,
updated 2026-07-29.

This document separates two questions that older project documentation mixed
together:

1. What does Zotero's official API support?
2. Which of those operations does Zotero Keeper 2.1 expose safely through MCP?

## Three different interfaces

| Interface | Location | Authentication | Intended use |
|-----------|----------|----------------|--------------|
| Local API v3 | `http://localhost:23119/api/` | Reads are unauthenticated. Zotero 10+ writes require runtime local authorization. | Fast, same-machine access to the currently open Zotero database |
| Connector endpoints | `http://localhost:23119/connector/` | Local browser-connector interface | Keeper's backward-compatible create/import path, including Zotero 7–9 |
| Web API v3 | `https://api.zotero.org/` | zotero.org API key or OAuth for private/write access | Remote and synchronized library access over HTTPS |

The Connector endpoints are not the Local API v3 write contract. A limitation
of Keeper's historical Connector adapter must not be described as a limitation
of Zotero 10+ itself.

## Security boundary

The Local API is a same-machine interface. Zotero explicitly says not to expose
or forward its port. Keep `23119` on loopback (`localhost`, `127.0.0.1`, or
`::1`). Remote access belongs on the authenticated HTTPS Web API or behind a
purpose-built service with TLS, authentication, authorization, and network
controls.

This remains true on Zotero 10+. Runtime write authorization prevents silent
local writes, but a granted local key has no per-library or per-operation scope.
It can write any library that the current Zotero user may edit.

Keeper therefore applies an additional boundary:

- Local write authorization is accepted only over literal loopback.
- The key remains in process memory and is never an MCP parameter/result, log
  field, query parameter, or persisted project asset.
- Public tools build fixed API paths. There is no raw arbitrary Local API tool.
- Collection and item keys are validated before mutation.
- Every mutation preview already contains a response-bound
  `expected_server_id`; every confirmed mutation requires that reviewed
  identity. Authorization cannot be used to supplement identity after approval.
- Root-library import rules remain independent of API authorization. A valid
  Local API key never implies permission to ignore a missing collection.
- A write timeout, conflict, or authorization error is not replayed
  automatically because the first mutation may already have completed.

## Discovery and database identity

A compatible client begins with:

```http
GET /api/
```

The response identifies the active contract with these headers:

- `Zotero-API-Version` — Local API currently supports v3 only.
- `Zotero-Schema-Version` — the local schema can differ from the Web API.
- `Zotero-Server-ID` — Zotero 10+ identity for the currently open database.

Every Zotero 10+ response includes the Server-ID. A write (including
authorization) must send it; missing identity returns `428`, and a mismatch
returns `412`. A read may send it as a consistency check. If the Server-ID
changes, discard cached authorization, object versions, and results tied to the
previous database.

Local object versions are transaction versions for this one Zotero database.
They are not interchangeable with Web API/sync versions or versions from
another Zotero installation. Partition any cache by Server-ID.

Keeper exposes the identity from the same HTTP response as item/collection
versions and full-text library cursors. A caller obtains this response-bound
pair before mutation preview and includes the identity as `expected_server_id`.
Do not combine an object version or library cursor with a separately cached
identity.

## Runtime write authorization (Zotero 10+)

Keeper requests authorization with a fixed application name:

```http
POST /api/local/authorize
Content-Type: application/json
Zotero-Server-ID: <current-server-id>

{"appName":"Zotero Keeper"}
```

Zotero presents Allow, Always Allow, or Deny to the user:

- Allow returns a single-use key (`remember: false`). It is consumed by the
  first successfully authenticated write.
- Always Allow returns a reusable key (`remember: true`) until the user removes
  it in Zotero settings.
- Deny returns `403`.
- Requests that would display more than five dialogs per minute return `429`
  with `Retry-After`.

Writes send the key in `Zotero-API-Key`, never in a URL. `401` means the key is
invalid or consumed and requires a new explicit authorization. Keeper does not
silently open a new dialog or replay the mutation.

The multi-step file-upload flow requires a remembered authorization because it
contains more than one authenticated write. Keeper refuses before creating an
attachment when only a one-shot key is available. Call
`authorize_local_writes(require_remembered=true)` and choose **Always Allow**
before invoking `attach_file_to_item`.

## Zotero 10+ platform capability matrix

`<prefix>` is `/api/users/0` for the current user or `/api/groups/<groupID>`.
Keeper 2.1 intentionally limits writes to the current user's local library.

| Object | Read | Create | Update | Delete |
|--------|:----:|:------:|:------:|:------:|
| Items, notes, attachments | Yes | `POST <prefix>/items` | `PUT`/`PATCH <prefix>/items/<key>` or batch `POST` | Single or batch `DELETE` |
| Collections | Yes | `POST <prefix>/collections` | `PUT`/`PATCH` or batch `POST` | Single or batch `DELETE` |
| Saved searches | Yes; Local API can also execute them | `POST <prefix>/searches` | Local API supports `PUT`/`PATCH` | Single or batch `DELETE` |
| Tags | Yes | Via item data | Via item data | `DELETE <prefix>/tags?tag=...` |
| Full text | Yes | `PUT <prefix>/items/<key>/fulltext` or bulk `POST <prefix>/fulltext` | Same | Replace through a versioned write; Keeper uses the bulk form |
| Stored files | Metadata + local file URL | Three-phase full upload | Three-phase full upload | Attachment item deletion |

Important write semantics:

- Multi-object requests accept at most 50 items, collections, searches, or
  tags. Bulk full-text writes accept at most 10 entries.
- `PATCH` changes only supplied fields, but arrays such as `collections`,
  `tags`, `creators`, and `relations` replace the complete array. Read, merge,
  and write the full intended array.
- Updates carry either the JSON object's `version` or
  `If-Unmodified-Since-Version`. Keeper uses the explicit header.
- Deletes require a version precondition. Creates use a 32-character
  `Zotero-Write-Token` or a library-version precondition.
- A stale object or library version returns `412`; do not refetch and overwrite
  automatically because the user approved an earlier state.
- Local and Web batch responses have historically used both `success` and
  `successful` in examples. Keeper accepts either and normalizes internally.

## Read endpoints relevant to Keeper

The Local API supports most API v3 reads, including:

- items, children, trash, publications, collections, tags, and groups;
- `qmode=everything`, which includes indexed full text;
- saved-search metadata and Local-only saved-search execution;
- schema endpoints such as `/api/itemTypes`, `/api/itemTypeFields`, and
  `/api/itemTypeCreatorTypes`;
- `?since=<version>` and `format=versions` for incremental reads;
- full-text version/content reads; and
- Local-only attachment file access.

For a stored attachment:

```http
GET <prefix>/items/<attachmentKey>/file/view/url
```

returns the local `file://` URL as plain text. Keeper 2.1 prefers this official
route and retains `ZOTERO_DATA_DIR/storage/<key>/<filename>` only as a fallback
for older Zotero releases or unavailable endpoints.

The Local API does not support Atom output. Local result sets also do not use
the Web API's default/max pagination limits, though `limit`, `start`, and Link
headers remain available.

## Full file upload

Zotero 10+ uses a three-phase full upload for stored (`imported_file` or
`imported_url`) attachments smaller than 4 GiB:

1. Create or identify the attachment item, then POST `md5`, `filename`,
   `filesize`, and millisecond `mtime` to its `/file` endpoint with
   `If-None-Match: *` for a new file (or `If-Match` for replacement).
2. POST the bytes to the returned `/api/local/uploads/<uploadKey>` URL. The
   upload key authorizes only this step, expires after one hour, and must not
   cause the client to send the Local API key to an arbitrary origin.
3. POST `upload=<uploadKey>` to the attachment `/file` endpoint with the same
   condition to register the upload.

Local API uploads are full uploads; binary-diff `PATCH` is a Web API feature and
returns `405` locally. Keeper validates that the upload URL stays on the
configured loopback port before sending bytes. If an upload fails after the
attachment record was created, the result reports a partial operation and its
attachment key instead of attempting an unapproved cleanup delete.

## Keeper 2.1 public Local API tools

Keeper preserves its original 24 public tools and adds these eight:

| Tool | Exposed operation |
|------|-------------------|
| `authorize_local_writes` | Explicitly request Zotero runtime authorization; `require_remembered=true` is required before file upload |
| `create_collection` | Create a top-level or nested collection |
| `add_items_to_collection` | Merge one confirmed collection into up to 50 existing items with one versioned batch write |
| `update_item_fields` | Update approved scalar metadata fields with an expected object version |
| `create_note` | Create a child note under an existing item |
| `create_saved_search` | Create a structured saved search |
| `attach_file_to_item` | Upload a local stored file beneath an existing item |
| `set_attachment_fulltext` | Write indexed text with a response-bound library cursor through bulk `POST /api/users/0/fulltext` |

All seven mutation tools accept `expected_server_id`; every confirmed call
requires it. Before preview, obtain that identity from a response-bound read or
authorization. `update_item_fields` also receives the object version paired with
the exact-item response. `set_attachment_fulltext` instead receives the library
cursor paired with `get_item_attachments` or `get_item_fulltext`; the attachment
object version is not a full-text write precondition.

The confirmation-only first pass includes `expected_server_id` (and any version
cursor) in `proposed`. Without `confirm=true`, it performs no Zotero read,
authorization, filesystem probe, or write. If authorization later returns a
different Server-ID, discard that proposal and repeat the read, preview, and
approval. Identity cannot be supplied only after preview. A 412 starts the same
fresh workflow and is never replayed automatically.

Collection membership validates the destination and every item before the
single batch request. Metadata updates reject structural fields such as keys,
versions, item types, parent relations, creators, tags, and collection arrays;
those require dedicated merge-aware tools rather than a raw PATCH.

Keeper 2.1 does not publicly expose general deletes, arbitrary endpoint access,
group writes, or replacement of complete structural arrays. The underlying
client implements the official versioned CRUD primitives for controlled future
tools and tests, but destructive library maintenance remains in Zotero's UI.

## Compatibility matrix

| Zotero version | Local reads | Connector create/import | Authorized Local writes |
|----------------|:-----------:|:-----------------------:|:-----------------------:|
| 7 | Yes | Yes | No |
| 8 | Yes | Yes | No |
| 9 | Yes, subject to Zotero's Local API setting | Yes | No |
| 10+ | Yes | Yes (compatibility path) | Yes, after runtime authorization |

`check_connection` is read-only. It discovers and reports the Local API version,
schema version, Server-ID presence, and whether Keeper currently holds an
authorization, but it never opens Zotero's authorization dialog.

## Error handling

| Status | Meaning | Keeper behavior |
|--------|---------|-----------------|
| `400` | Invalid fields, key, or unsupported content | Return a stable invalid-request error; no retry |
| `401` | Invalid/consumed Local API key | Clear in-memory authorization; require explicit authorization |
| `403` | Local API disabled or authorization denied | Explain the relevant Zotero setting or denial |
| `404` | Object or endpoint not found | Fail closed; never reinterpret as My Library root |
| `405` | Unsupported local binary-diff file PATCH | Use the documented full-upload flow |
| `412` | Stale version or wrong Server-ID | Clear database-bound state as needed; never overwrite/replay |
| `428` | Missing Server-ID or write precondition | Treat as a client protocol error; no retry |
| `429` | Too many authorization dialogs | Return `Retry-After`; do not prompt-loop |
| `501` | Unsupported API version/format (for example Atom) | Report the unsupported operation |

## Smoke and release verification

Every release runs:

1. wire-level unit tests for JSON arrays, headers, authorization outcomes,
   one-shot/remembered keys, Server-ID changes, conflicts, and upload phases;
2. an ephemeral loopback Zotero simulator exercised through the public MCP v2
   `Client`, including `check_connection`, authorization, and a real guarded
   mutation;
3. a no-listener test proving connection failure is structured and bounded;
4. managed-venv installation that creates both Keeper and PubMed MCP servers,
   lists their exact surfaces, and verifies installed versions; and
5. package-once VSIX inspection before the same artifact is sent to Marketplace
   and GitHub Release.

An optional live smoke is enabled only with an explicit environment flag. It is
read-only by default; live writes require a separate opt-in and a dedicated
test collection, never My Library root.

## Official references

- [Local API](https://www.zotero.org/support/dev/web_api/v3/local_api)
- [API v3 basics and read endpoints](https://www.zotero.org/support/dev/web_api/v3/basics)
- [Write requests](https://www.zotero.org/support/dev/web_api/v3/write_requests)
- [File uploads](https://www.zotero.org/support/dev/web_api/v3/file_upload)
- [Full-text content](https://www.zotero.org/support/dev/web_api/v3/fulltext_content)
- [Item types and fields](https://www.zotero.org/support/dev/web_api/v3/types_and_fields)

These Zotero sources define the platform contract. Community MCP projects and
curated connector products are useful ecosystem references, but they are not
Zotero's official API specification.
