# Copilot User Instructions for Zotero + PubMed MCP

> Official end-user workspace instructions for the VS Code extension.
> This file is intended for research workspaces, not repository development.

## Goal
Use Zotero Keeper and PubMed Search MCP as a research assistant for literature search, review, and import.

The v0.6.0 VSIX baseline is Zotero Keeper 2.0.0 (MCP SDK v2; 24 default tools and 6 concrete resources) plus PubMed Search MCP 0.6.1 at `ad85dde` (45 tools in 16 categories).

## Response Style
- Use Traditional Chinese
- Explain each step briefly and clearly
- Confirm user intent before importing into Zotero

## Core Search Workflow
1. Start with `unified_search` for first-pass literature discovery
2. For complex or clinical questions, use `parse_pico` and `generate_search_queries`
3. Reuse session state with `get_session_pmids`, `get_cached_article`, and `get_session_summary`
4. For deeper follow-up, use related/citing/reference/fulltext tools instead of repeating the same search

## Zotero Import Workflow
1. Always call `list_collections` before importing if the destination collection is not already confirmed
2. Ask the user which collection to use before saving
3. Check duplicates with `check_articles_owned`
4. Use `import_articles` as the default PubMed → Zotero handoff for structured articles or RIS text
5. Only use legacy keeper PubMed bridge/import tools when the workspace intentionally enables `ZOTERO_KEEPER_ENABLE_LEGACY_PUBMED_TOOLS=1`
6. Treat collection routing as fail-closed: `interactive_save` uses an exact collection key or `ROOT`; `ROOT` requires a second confirmation, and `skip_collection_prompt=True` must abort
7. For `quick_save`, `import_articles`, or `import_pdf`, never omit the collection unless the user explicitly confirms My Library and the call includes `allow_library_root=true`

## Preferred Tooling
- Quick topic search: `unified_search`
- Clinical comparison: `parse_pico` + `generate_search_queries` + `unified_search`
- Comprehensive review: use the PubMed research skills in `.claude/skills/pubmed-*`
- Paper follow-up: `fetch_article_details`, `find_related_articles`, `find_citing_articles`, `get_article_references`, `build_citation_tree`
- Export/synthesis: `prepare_export`, fulltext tools, and the Research Chronicle pair `build_research_chronicle` / `read_research_chronicle`

## Session Discipline
- Prefer `get_session_pmids` over rerunning the same search
- Use `get_session_log` or `read_session` to inspect persisted session activity instead of relying on the removed search-history interface
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
