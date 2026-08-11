# Collaboration-Safe Workflow Guide

> How to run pubmed-search-mcp and zotero-keeper together without overlapping responsibilities.

## Why a Split Workflow?

- **pubmed-search-mcp** owns search, discovery, export, citation metrics, and unified article JSON contracts.
- **zotero-keeper** owns local-library work: duplicate checks, collection targeting, and the single public import handoff into Zotero.
- Default posture: keeper exposes only `import_articles` for PubMed handoff; legacy bridge tools stay hidden unless you opt in.
- Release baseline: VSIX 0.6.0 installs Zotero Keeper 2.0.0 (24 default tools, 6 concrete resources) and PubMed Search MCP 0.6.1 at `ad85dde` (45 tools, 16 categories).

## Setup Checklist

1. **Prerequisites**
   - Zotero 7/8/9 is running on the same machine (`localhost:23119`).
   - Python 3.12+ with `uv` installed (no `pip` usage).
2. **pubmed-search-mcp available**
   - If you work in this monorepo: `git submodule update --init --recursive` to populate `external/pubmed-search-mcp`.
   - Point keeper at a local checkout (optional) with `PUBMED_SEARCH_PATH=/absolute/path/to/pubmed-search-mcp`.
   - Otherwise, install and launch pubmed-search-mcp per its README (MCP SDK v2 `MCPServer`).
3. **keeper environment**
   - From `mcp-server/`: `uv sync --extra all`
   - Start with `uv run python -m zotero_mcp` (or use the VS Code extension’s MCP auto-start).
4. **Recommended env vars**
   - `NCBI_EMAIL` (and optional `NCBI_API_KEY`) for better PubMed throughput.
   - `ZOTERO_KEEPER_ENABLE_LEGACY_PUBMED_TOOLS=1` **only** if you intentionally need the old keeper-only PubMed bridge tools.

## Recommended PubMed → Zotero Flow

```python
# 1) Search in pubmed-search-mcp
results = unified_search("anesthesia AI", output_format="json")

# 2) Optional: filter against your Zotero library via keeper
pmids = [a.get("identifiers", {}).get("pmid") for a in results["articles"]]
owned = check_articles_owned(pmids=[pmid for pmid in pmids if pmid])

# 3) Import through keeper (single public handoff)
import_articles(
    articles=results["articles"],
    collection_name="AI Research",
    tags=["2024", "review"]
)
```

Guidance:
- Keep imports under `max_articles=100` per call.
- Use `collection_name` to route saves safely; keeper validates against existing collections.
- Collection routing is fail-closed. `interactive_save` needs an exact collection key or double-confirmed `ROOT`; `skip_collection_prompt=True` aborts. `quick_save`, `import_articles`, and `import_pdf` reject a missing collection unless explicit user approval is represented by `allow_library_root=true`.
- Skip legacy tools unless a workflow explicitly requires them.
- Use `build_research_chronicle` and `read_research_chronicle` when you need a durable research-history artifact. These two tools replace the former three-tool timeline surface.

## Troubleshooting

- **FileNotFoundError for `external/pubmed-search-mcp/src`**
  Run `git submodule update --init --recursive` (repo checkout) or set `PUBMED_SEARCH_PATH` to a local pubmed-search-mcp tree.

- **No pubmed-search-mcp running**
  `check_articles_owned` falls back to local PMID checks only. `import_articles` still works for JSON/RIS inputs but cannot fetch missing PubMed metadata.

- **Need to override paths**
  Use absolute paths in `PUBMED_SEARCH_PATH` and MCP configs; avoid relative paths when MCP servers start from editors.

- **Old MCP environment after upgrade**
  MCP SDK 2.x is incompatible with 1.x. In VS Code, run **Zotero MCP: Reinstall Python Environment** after upgrading from an older VSIX.

- **Adding another Zotero MCP server**
  Do not install the MCP Registry-listed community project `54yyyu/zotero-mcp` into Keeper's environment. Both distributions expose the `zotero_mcp` Python module; run the community server in a separate virtual environment and MCP process if you need it.

## Quick Verification

- Keeper: `uv run python tests/check_mcp.py` should discover the SDK v2 server surface; the default server has 24 tools.
- PubMed: start the pinned 0.6.1 server per its README and confirm the client discovers 45 tools before making a real `unified_search` call.
- Integration: invoke `check_connection` (keeper) and a small `unified_search` → `import_articles` chain before production use.
