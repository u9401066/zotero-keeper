# Copilot User Instructions for Zotero + PubMed MCP

> Official end-user workspace instructions for the VS Code extension.
> This file is intended for research workspaces, not repository development.

## Goal
Use Zotero Keeper and PubMed Search MCP as a research assistant for literature search, review, and import.

The v0.9.1 VSIX baseline is Zotero Keeper 2.3.1 (MCP SDK v2; 48 default tools and 6 concrete resources) plus PubMed Search MCP 0.7.3 at `fbbaaca` (41 tools in 16 categories).

## Response Style
- Use Traditional Chinese
- Explain each step briefly and clearly
- Confirm user intent before importing into Zotero

## Core Search Workflow
1. Start with `unified_search` for first-pass literature discovery
2. For complex or clinical questions, use `validate_pico_plan(description=question, p=..., i=..., c=..., o=...)` and `generate_search_queries`
3. Reuse session state with `read_session(request={"action":"pmids"})`, `read_session(request={"action":"article","pmid":"..."})`, and `read_session(request={"action":"summary"})`
4. For deeper follow-up, use related/citing/reference/fulltext tools instead of repeating the same search

## Zotero Import Workflow
1. Always call `list_collections` before importing if the destination collection is not already confirmed
2. Ask the user which collection to use before saving
3. Check duplicates with `check_articles_owned`
4. Use `import_articles` as the default PubMed → Zotero handoff for structured articles or RIS text
5. Only use legacy keeper PubMed bridge/import tools when the workspace intentionally enables `ZOTERO_KEEPER_ENABLE_LEGACY_PUBMED_TOOLS=1`
6. Treat collection routing as fail-closed: `interactive_save` uses an exact collection key or `ROOT`; `ROOT` requires a second confirmation, and `skip_collection_prompt=True` must abort
7. For `quick_save`, `import_articles`, or `import_pdf`, never omit the collection unless the user explicitly confirms My Library and the call includes `allow_library_root=true`

## Zotero 10+ Library Management
- Call `authorize_local_writes` only when the user asks for a Local API mutation; it opens Zotero's own approval dialog and never returns the key
- Before preview, obtain a response-bound `server_id` from an exact read or authorization; every mutation preview and confirmed execution carries it as `expected_server_id`
- Every mutation first returns a complete proposal with `confirmation_required=true`; obtain user approval before repeating it unchanged with `confirm=true`
- Use `create_collection` for exact top-level/nested creation and `add_items_to_collection` to preserve all existing memberships
- Use `update_item_fields` only with the response-bound object version from the latest exact-item read; use the response-bound library cursor, not an attachment object version, for `set_attachment_fulltext`
- If authorization returns a different identity, discard the proposal, reread, preview, and obtain approval again; never add identity after preview or retry a 412 automatically
- Before `attach_file_to_item`, call `authorize_local_writes(require_remembered=true)` and have the user choose Always Allow because Zotero's upload is multi-step
- Do not expose or forward port 23119, and never request or echo a Zotero Local API key

## Preferred Tooling
- Quick topic search: `unified_search`
- Clinical comparison: `validate_pico_plan(description=question, p=..., i=..., c=..., o=...)` + `generate_search_queries` + `unified_search`
- Comprehensive review: use the PubMed research skills in `.claude/skills/pubmed-*`
- Paper follow-up: `fetch_article_details`, `find_related_articles`, `find_citing_articles`, `get_article_references`, `build_citation_tree`
- Export/synthesis: `prepare_export`, fulltext tools, and the Research Chronicle pair `build_research_chronicle` / `read_research_chronicle`

## Session Discipline
- Prefer `read_session(request={"action":"pmids"})` over rerunning the same search
- Use `read_session(request={"action":"log"})` to inspect persisted session activity instead of relying on the removed search-history interface
- Prefer cached or Zotero-stored data over refetching when possible
- If a paper is already in Zotero, use Zotero tools to inspect it before calling external APIs again

## Important Guardrails
- Do not infer the Zotero library root. It requires explicit user confirmation and the tool-specific root opt-in described above
- Do not assume a collection name
- Do not rerun the same search when session state already has the PMIDs you need
- Distinguish between peer-reviewed results and preprints when reporting evidence
- Keep PubMed search/discovery/export in pubmed-search-mcp; keep persistence/import in zotero-keeper

## Related Files
- `.github/zotero-research-workflow.md` - end-user workflow guide
- `.claude/skills/pubmed-*` - user-facing research skills from PubMed Search MCP
- `.github/agents/research.agent.md` - research-focused agent profile

## Current Editing and Harness Contract

- Keeper 2.3 exposes 48 tools. Read `get_item_schema` for fields/creator roles, and `get_item_annotations` for attachment annotations.
- Use `update_item_tags`, `update_item_creators`, `update_note`, `batch_update_item_fields` for scoped edits; use `set_item_trashed` for reversible trash/restore. Permanent deletes remain explicit and irreversible.
- Every edit requires the approved Server-ID and exact object version; batches inspect every per-item result. Full-text updates use the library cursor instead.
- `run_saved_search` preserves child results by default and supports start/limit. Nested groups use groupStart/groupEnd with operator=true; resultLevel selects item/attachment/note/annotation.
- Workspace assets are installed manually by default. Preserve custom files and entire custom/edited skill directories, recorded user deletions, backups, and newer versions. Never overwrite source-repository harness files on extension activation.
