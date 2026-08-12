---
paths:
  - ".github/zotero-research-workflow.md"
  - "mcp-server/src/zotero_mcp/infrastructure/mcp/pubmed_tools.py"
  - "mcp-server/src/zotero_mcp/infrastructure/mcp/unified_import_tools.py"
  - "mcp-server/src/zotero_mcp/infrastructure/mcp/local_api_tools.py"
  - "mcp-server/src/zotero_mcp/infrastructure/zotero_client/client_local.py"
  - "mcp-server/tests/unit/mcp/test_pubmed_tools.py"
  - "mcp-server/tests/unit/mcp/test_unified_import_tools.py"
  - "mcp-server/tests/unit/mcp/test_local_api_tools.py"
  - "mcp-server/tests/unit/infrastructure/test_local_client.py"
---

# Zotero Research Workflow Rules

## Import Invariants

- Ask for the target Zotero collection before importing search results.
- Never save to My Library root unless the user explicitly confirms it; only
  then may a caller set `allow_library_root=true`.
- Check for existing articles before creating new Zotero items.
- Prefer the unified `import_articles` bridge for PubMed JSON, PMID lists, or RIS text.
- Keep RIS and PubMed JSON parsing tolerant, but report skipped records clearly.

## Search-To-Library Flow

Use this shape unless the user asks for a different workflow:

1. Search or retrieve PubMed results.
2. Summarize the candidate articles and ask whether to import.
3. List or confirm the Zotero collection.
4. Check duplicates.
5. Import only the confirmed set.
6. Report created, skipped, duplicate, and failed records.

## Zotero 10+ Mutation Flow

- First obtain a response-bound `server_id` from a Local API read or
  `authorize_local_writes`. Use the exact-item object version for
  `update_item_fields`, or the response-bound library cursor for
  `set_attachment_fulltext`.
- Call each mutation with `confirm=false` and that `expected_server_id`; this
  must perform zero Zotero I/O and return the exact proposed change.
- Ask the user to approve the complete proposal, then repeat it unchanged with
  `confirm=true`. Every confirmed mutation requires the reviewed identity.
- If authorization reports another Server-ID, discard the proposal and redo the
  read, preview, and approval. Never add identity after preview or auto-retry a
  412 conflict.
- Before `attach_file_to_item`, require
  `authorize_local_writes(require_remembered=true)` and **Always Allow**.
- Never expose or forward port 23119 or surface the Local API key.

## Evidence Hygiene

- Keep PMID, DOI, title, journal, year, and URL metadata when available.
- Avoid claiming full-text access unless a PubMed/Europe PMC/CORE/OpenURL tool actually returned it.
- Prefer Zotero item reads for articles already in the library instead of re-fetching details from PubMed.
