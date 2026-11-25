---
name: pubmed-search-mcp-harness
description: "Codex harness for PubMed Search MCP. Triggers: pubmed search, literature search, unified_search, pipeline, fulltext, release checklist, Codex."
---

# PubMed Search MCP: Codex Harness Skill

Use this skill when working with Codex on PubMed Search MCP research workflows,
pipeline state, fulltext access, exports, and release checks.

## What To Read First

- `AGENTS.md` for Codex workspace instructions.
- `.github/agents/research.agent.md` for research-agent behavior.
- `.github/hooks/` and `scripts/hooks/copilot/` for pipeline enforcement assets.
- `.claude/skills/pubmed-*` and `.claude/skills/pipeline-persistence` for user-facing workflows.
- `.clinerules/` for project/release rules that also apply to Codex.

## Canonical Commands

- Lint: `uv run ruff check .`
- Format check: `uv run ruff format --check .`
- Types: `uv run mypy src/ tests/`
- Tests: `uv run pytest`
- Tool docs sync: `uv run python scripts/count_mcp_tools.py --update-docs`
- Skill audit: `python scripts/check_cline_skills.py`

## Research Guardrails

- Prefer `unified_search` as the primary multi-source entrypoint.
- Preserve session/pipeline state instead of relying on agent memory.
- Use `build_research_chronicle` and `read_research_chronicle` for durable
  research-history artifacts; the former timeline tools are no longer public.
- Respect NCBI email/API-key policy and institutional access configuration.
- Keep exported citations reproducible with PMIDs, DOI, source, date filters, and query strategy.

## Pinned 0.11.0 Interface (43 tools)

- 0.11.0 (`eb7b2ee`) exposes 43 tools in 16 categories: 0.10.0 added `research_workspace` and 0.11.0 added `pipeline_screening`; no tool was removed after 0.7.3. Since 0.7.5 one input contract applies to every tool: safe auto-correction of JSON containers/code fences, numeric/boolean text, enum spelling and PMID/PMCID/DOI batches (URLs, lists, JSON). Invalid input returns a structured pre-execution error with a stable code and JSON Pointer; fix the named argument and retry once. Only argument validation asserts `executed: false`.
- `unified_search(fulltext="prefetch")` (0.7.6) opts in to non-blocking PMC XML preparation for the top three results; each prefetch row carries a native `get_fulltext` `read_request`. Do not poll; read directly, and never treat abstract-only XML as full text.
- The agent extracts P/I/C/O, then calls `validate_pico_plan(description=question, p=..., i=..., c=..., o=...)`; pass its pipeline to `unified_search(query=question, pipeline=plan["pipeline"])`.
- Read state with `read_session(request={"action":"pmids","search_index":-1})`, `{"action":"article","pmid":"..."}`, `{"action":"summary"}`, or `{"action":"log"}`. The request object is required; action is not a top-level parameter.
- SearchRun actions include search_runs, search_run and replay_search; replay may call providers again and is not a cache read. Request it only for deliberate reruns.
- Use `verify_reference_list`, `save_literature_notes`, `convert_icd_mesh`, and `prepare_figure_search` when needed. Use `unschedule_pipeline` to stop scheduled execution; `delete_pipeline` keeps a screening log with decisions unless `delete_screening_log=true`.
- Never send retired PICO/session tool names. Verify the public tools/schema in the pinned package, not from old installed skills.
- Deep `unified_search` is precision-first: the caller's query fills the limit before any broadening. Report `broadening.summary`; records with `retrieval.broadened=true` (Markdown 🔻) are lower-precision fill ranked after exact matches. `options="no_relax"` disables broadening.
- MeSH is confirmed only on an exact preferred/entry-term match. When PubMed reports a `[Mesh]` clause as not found, the server re-runs the exact tier with a disclosed `mesh_correction` (`options="no_mesh_correction"` opts out); saved pipelines are never rewritten, only annotated.
- Systematic reviews: save a PubMed step with `retrieval: exhaustive` (`max_records` ≤ 10000; larger counts are refused, not truncated), run `unified_search(pipeline="saved:<name>")`, read `get_pipeline_history(view="records"|"run"|"prisma_s")`, export with `prepare_export(pipeline_run=...)`, audit concept blocks with a `block_analysis` step, and record title/abstract and full-text decisions with `pipeline_screening` (PRISMA 2020 flow counts).
- `research_workspace` keeps a question, its decisions, evidence locators and open actions across sessions: resume with `action="read"`, record with a stable `record_id` and `evidence_scope`, and retry an ambiguous write with the same ID and payload.
- `verify_reference_list` may return `corrections` for a real but mis-cited reference; they require corroborating fields. `get_fulltext` falls back to NCBI PMC and reports `sources_skipped`/typed `source_errors`; never treat `front_matter_only` as full text.
- Research Chronicle labels entries by PubMed publication type (`[heuristic]` marks a fallback) and quotes verbatim abstract sentences with offsets; cite them as the authors' words.
- Workspace data lives in `<workspace>/.pubmed-search/` (run record sets with titles/abstracts and the screening log); a newly created directory ignores itself in git.
- Harness upgrades preserve whole edited skills and use versioned SHA-256 ownership; never overwrite user rules/hooks to make a skill match upstream.
