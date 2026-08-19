---
paths:
  - "src/pubmed_search/presentation/mcp_server/**"
  - "src/pubmed_search/application/**"
  - "src/pubmed_search/infrastructure/sources/**"
  - "scripts/count_mcp_tools.py"
  - ".claude/skills/pubmed-mcp-tools-reference/SKILL.md"
---

# PubMed MCP Tool Rules

## Tool Contract Rules

- Keep `unified_search` as the primary search facade.
- Preserve session-aware flows: cached articles, last PMIDs, session logs, Research Chronicle, and pipeline state.
- Return source counts and warnings when a source fails or contributes zero results.
- Preserve `search_status`, `search_run`, and `source_metadata` so callers can
  distinguish completed, valid empty, partial, and failed searches.
- Reject unknown filters/options/sources and invalid limits before provider I/O.
- Keep output formats stable for markdown, JSON, RIS, BibTeX, CSV, and MEDLINE.
- Do not remove old fields without tolerating them for at least one release cycle.

## Research Workflow Rules

- Use `generate_search_queries` and `analyze_search_query` before complex/systematic searches.
- Use the bounded `systematic`, `native_semantic`, or `trials` option only when
  the requested evidence workflow calls for it.
- Use `parse_pico` for clinical comparison questions.
- Use `build_research_chronicle` and `read_research_chronicle` for persistent research history.
- With the pinned 0.6.3 release, repeat the original chronicle
  topic/PMIDs/year/max-events scope when continuing by `chronicle_id`.
- Recover or audit searches through `read_session` actions `search_runs`,
  `search_run`, and `replay_search`; do not rerun blindly.
- Use `get_fulltext`, `get_article_figures`, and institutional access tools only when full-text retrieval is requested.
- Export to RIS for Zotero/EndNote and BibTeX for LaTeX workflows.

## Documentation Sync

When tools are added, removed, or renamed:

- Run `uv run python scripts/count_mcp_tools.py --update-docs`.
- Update relevant `.claude/skills/pubmed-*` skills.
- Update `.github/agents/research.agent.md` if the research flow changes.
- Add or update MCP protocol tests.
