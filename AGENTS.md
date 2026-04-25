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
2. Use `parse_pico` and `generate_search_queries` for clinical or comparison questions.
3. Reuse session state with `get_session_pmids`, `get_cached_article`, and `get_session_summary`.
4. Use related/citing/reference/fulltext tools for follow-up instead of rerunning the same search.
5. Before saving to Zotero, call `list_collections` unless the destination is already confirmed.
6. Check duplicates with `check_articles_owned`.
7. Use `import_articles` as the default PubMed-to-Zotero handoff.

## Repository Work

- Treat `.codex/skills`, `.claude/skills`, `.cline/skills`, and `.clinerules` as bundled assistant harness assets.
- Run `npm run sync-assets` before packaging the VSIX.
- Keep `vscode-extension/resources/repo-assets/**` synchronized with its source files.
- Preserve custom user `AGENTS.md`, Copilot instructions, and Cline settings during extension install/update flows.

## Guardrails

- Do not import into the Zotero root collection without explicit confirmation.
- Do not assume the target collection.
- Do not repeat searches when session state already contains the relevant PMIDs.
- Distinguish peer-reviewed articles, preprints, and metadata-only records.
- Keep NCBI email/API-key and institutional access settings intact.

## Related Files

- `.codex/skills/zotero-keeper-harness/SKILL.md`
- `.codex/skills/pubmed-search-mcp-harness/SKILL.md`
- `.github/zotero-research-workflow.md`
- `.github/agents/research.agent.md`
- `.claude/skills/pubmed-*`
