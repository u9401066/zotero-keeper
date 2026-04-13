# Collaboration-Safe Workflow Guide

> How to run pubmed-search-mcp and zotero-keeper together without overlapping responsibilities.

## Why a Split Workflow?

- **pubmed-search-mcp** owns search, discovery, export, citation metrics, and unified article JSON contracts.
- **zotero-keeper** owns local-library work: duplicate checks, collection targeting, and the single public import handoff into Zotero.
- Default posture: keeper exposes only `import_articles` for PubMed handoff; legacy bridge tools stay hidden unless you opt in.

## Setup Checklist

1. **Prerequisites**
   - Zotero 7/8 is running on the same machine (`localhost:23119`).
   - Python 3.12+ with `uv` installed (no `pip` usage).
2. **pubmed-search-mcp available**
   - If you work in this monorepo: `git submodule update --init --recursive` to populate `external/pubmed-search-mcp`.
   - Point keeper at a local checkout (optional) with `PUBMED_SEARCH_PATH=/absolute/path/to/pubmed-search-mcp`.
   - Otherwise, install and launch pubmed-search-mcp per its README (FastMCP server).
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
owned = check_articles_owned([a["pmid"] for a in results["articles"] if a.get("pmid")])

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
- Skip legacy tools unless a workflow explicitly requires them.

## Troubleshooting

- **FileNotFoundError for `external/pubmed-search-mcp/src`**  
  Run `git submodule update --init --recursive` (repo checkout) or set `PUBMED_SEARCH_PATH` to a local pubmed-search-mcp tree.

- **No pubmed-search-mcp running**  
  `check_articles_owned` falls back to local PMID checks only. `import_articles` still works for JSON/RIS inputs but cannot fetch missing PubMed metadata.

- **Need to override paths**  
  Use absolute paths in `PUBMED_SEARCH_PATH` and MCP configs; avoid relative paths when MCP servers start from editors.

## Quick Verification

- Keeper: `uv run python -m zotero_mcp --help` should print FastMCP options.
- PubMed: start pubmed-search-mcp per its README, then call `unified_search` once to confirm it responds.
- Integration: invoke `check_connection` (keeper) and a small `unified_search` → `import_articles` chain before production use.
