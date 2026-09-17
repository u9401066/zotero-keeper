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

## Pinned 0.7.3 Interface (41 tools)

- The agent extracts P/I/C/O, then calls `validate_pico_plan(description=question, p=..., i=..., c=..., o=...)`; pass its pipeline to `unified_search(query=question, pipeline=plan["pipeline"])`.
- Read state with `read_session(request={"action":"pmids","search_index":-1})`, `{"action":"article","pmid":"..."}`, `{"action":"summary"}`, or `{"action":"log"}`. The request object is required; action is not a top-level parameter.
- SearchRun actions include search_runs, search_run and replay_search; replay may call providers again and is not a cache read. Request it only for deliberate reruns.
- Use `verify_reference_list`, `save_literature_notes`, `convert_icd_mesh`, and `prepare_figure_search` when needed. Use `unschedule_pipeline` to stop scheduled execution.
- Never send retired PICO/session tool names. Verify the public tools/schema in the pinned package, not from old installed skills.
- Harness upgrades preserve whole edited skills and use versioned SHA-256 ownership; never overwrite user rules/hooks to make a skill match upstream.
