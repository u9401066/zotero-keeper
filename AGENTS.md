# Zotero + PubMed MCP Codex Harness

These are the workspace instructions for Codex when using Zotero Keeper and
PubMed Search MCP through the VS Code extension.

## Goal

Help the user search biomedical literature, inspect papers, and import selected
articles into Zotero without losing provenance or overwriting user choices.

## Working Style

- Use Traditional Chinese unless the user asks otherwise.
- Explain search/import steps briefly.
- Ask before importing anything into Zotero.
- Keep PubMed search/discovery/export work in PubMed Search MCP.
- Keep persistence, collection selection, and Zotero inspection in Zotero Keeper.

## Core Workflow

1. Start broad literature discovery with `unified_search`.
2. Use `validate_pico_plan(description=question, p=..., i=..., c=..., o=...)` and `generate_search_queries` for clinical or comparison questions.
3. Reuse session state with `read_session(request={"action":"pmids"})`, `read_session(request={"action":"article","pmid":"..."})`, and `read_session(request={"action":"summary"})`.
4. Use related/citing/reference/fulltext tools for follow-up instead of rerunning the same search.
5. Use `build_research_chronicle` and `read_research_chronicle` for persistent research-history artifacts.
6. Before saving to Zotero, call `list_collections` unless the destination is already confirmed.
7. Check duplicates with `check_articles_owned`.
8. Use `import_articles` as the default PubMed-to-Zotero handoff.
9. For Zotero 10+ mutations, first obtain a response-bound `server_id` from a
   read or authorization, include it as `expected_server_id` in the
   `confirm=false` preview, and ask the user to approve that complete proposal.
   Ensure local authorization; if it reports the same identity, repeat the
   proposal unchanged with `confirm=true`.

## Repository Work

- Treat `.codex/skills`, `.claude/skills`, `.cline/skills`, and `.clinerules` as bundled assistant harness assets.
- Run `npm run sync-assets` before packaging the VSIX.
- Keep `vscode-extension/resources/repo-assets/**` synchronized with its source files.
- Preserve custom user `AGENTS.md`, Copilot instructions, and Cline settings during extension install/update flows.

## Guardrails

- Do not import into the Zotero root collection without explicit confirmation.
- Set `allow_library_root=true` only after that explicit confirmation.
- Do not assume the target collection.
- Do not repeat searches when session state already contains the relevant PMIDs.
- Distinguish peer-reviewed articles, preprints, and metadata-only records.
- Keep NCBI email/API-key and institutional access settings intact.
- Never expose or forward Zotero port 23119, request a Local API key, or retry
  a `412` version conflict automatically.
- Every confirmed Local API mutation requires the `expected_server_id` shown in
  its approved preview. If later authorization reports a different identity,
  reread, preview, and request approval again; never add identity after preview.
- Use the response-bound object version for exact updates and single-object
  deletes. Use the response-bound library cursor—not an attachment object
  version—for `delete_tags`, `set_attachment_fulltext`, and
  `set_attachment_fulltexts`. For `replace_attachment_file`, bind the reviewed
  attachment version and previous MD5 to the same response identity.
- Before `attach_file_to_item` or `replace_attachment_file`, call
  `authorize_local_writes(require_remembered=true)` and have the user choose
  **Always Allow** for the three-phase upload.

## Related Files

- `.codex/skills/zotero-keeper-harness/SKILL.md`
- `.codex/skills/pubmed-search-mcp-harness/SKILL.md`
- `.github/zotero-research-workflow.md`
- `.github/agents/research.agent.md`
- `.claude/skills/pubmed-*`

## Current Editing and Harness Contract

- Keeper 2.3 exposes 48 tools. Read `get_item_schema` for fields/creator roles, and `get_item_annotations` for attachment annotations.
- Use `update_item_tags`, `update_item_creators`, `update_note`, `batch_update_item_fields` for scoped edits; use `set_item_trashed` for reversible trash/restore. Permanent deletes remain explicit and irreversible.
- Every edit requires the approved Server-ID and exact object version; batches inspect every per-item result. Full-text updates use the library cursor instead.
- `run_saved_search` preserves child results by default and supports start/limit. Nested groups use groupStart/groupEnd with operator=true; resultLevel selects item/attachment/note/annotation.
- Workspace assets are installed manually by default. Preserve custom files and entire custom/edited skill directories, recorded user deletions, backups, and newer versions. Never overwrite source-repository harness files on extension activation.
