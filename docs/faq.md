# FAQ — Frequently Asked Questions

Common questions about installing, configuring, and using Zotero Keeper.

---

## Installation

### Do I need to install Python myself?

**If you use the VS Code Extension**: No. The extension automatically downloads [uv](https://docs.astral.sh/uv/) and creates an isolated Python 3.12 environment for you.

**If you use the MCP server directly** (e.g. with Claude Desktop): Yes, you need [Python 3.12+](https://www.python.org/downloads/) and [uv](https://docs.astral.sh/uv/getting-started/installation/).

---

### What is the easiest way to install?

For VS Code users, install the v0.6.0 VSIX from the [VS Code Marketplace](https://marketplace.visualstudio.com/items?itemName=u9401066.vscode-zotero-mcp). It is the recommended distribution for Zotero Keeper 2.0.0 and PubMed Search MCP 0.6.1.

For Claude Desktop or manual setups, use a source checkout with `uv sync`. The separately published `uvx`/PyPI package may still be on the older pre-2.0 line; do not assume this command installs Keeper 2.0.0 until the PyPI release is updated:

```bash
# Legacy pre-2.0 PyPI line only
uvx zotero-keeper
```

Or install permanently:

```bash
# Legacy pre-2.0 PyPI line only
uv tool install zotero-keeper
```

---

### Can I use Zotero Keeper without GitHub Copilot?

Yes. Zotero Keeper is a standard [MCP server](https://modelcontextprotocol.io/). It works with any MCP-compatible client:

- **Claude Desktop** — add the server to `claude_desktop_config.json`
- **VS Code + Copilot** — add to `.vscode/mcp.json`
- **Any MCP-compatible app** — start the server and connect via stdio

---

## Connectivity

### Zotero is running but I can't connect. What should I check?

1. Confirm Zotero is open and not minimized
2. Test the local API directly:
   ```bash
   curl http://127.0.0.1:23119/connector/ping
   ```
   Expected response: `Zotero is running`
3. Check that local security software is not blocking loopback traffic. Do not create an inbound rule or expose port `23119`.
4. On Windows, check that Zotero's local server is enabled under **Edit > Preferences > Advanced > Allow other applications to communicate with Zotero**

---

### I'm connecting to a remote Zotero instance. What should I set?

Do not expose Zotero's unauthenticated Local/Connector API port to another host. Keep it bound to loopback and run Keeper beside Zotero Desktop on the same trusted machine.

For a genuinely remote library, use Zotero's authenticated HTTPS Web API or a purpose-built authenticated service with TLS, authorization, and explicit network access controls.

---

## Tools & Features

### What's the difference between `interactive_save` and `quick_save`?

| | `interactive_save` | `quick_save` |
|--|--|--|
| Collection picker | ✅ Shows choices and requires an exact collection key; `ROOT` is confirmed twice | ❌ You must specify `collection_name` |
| Best for | Interactive use with Copilot | Automated workflows |
| Duplicate check | ✅ | ✅ |
| Auto-fetch metadata | ✅ (DOI/PMID) | ✅ (DOI/PMID) |

---

### How does auto-fetch metadata work?

When you provide a **DOI** or **PMID**, the save tools call external APIs to fill in all fields automatically:

- **DOI** → [CrossRef](https://www.crossref.org/) API (title, authors, journal, year, abstract)
- **PMID** → [PubMed](https://pubmed.ncbi.nlm.nih.gov/) API (all fields + MeSH terms) + [iCite](https://icite.od.nih.gov/) (Relative Citation Ratio)

The fetched data is merged with any fields you provided. Your explicit values always take priority.

---

### What is the Relative Citation Ratio (RCR)?

RCR is a field-normalized citation metric from NIH's [iCite](https://icite.od.nih.gov/) service. An RCR of `1.0` means the paper is cited at the field average; `2.0` means twice the average. Zotero Keeper stores it in the item's **Extra** field when a PMID is provided.

---

### How do I import PubMed search results to Zotero?

The recommended workflow uses [pubmed-search-mcp](https://github.com/u9401066/pubmed-search-mcp) for search and Zotero Keeper for import:

```
1. Search:  unified_search("CRISPR gene therapy", output_format="json")
2. Import:  import_articles(articles=results["articles"], collection_name="CRISPR")
```

Both steps can be done in a single Copilot chat message:
> *"Search PubMed for CRISPR gene therapy and save the results to my 'CRISPR' collection"*

---

### Can I import from a RIS file?

Yes. Pass the RIS text directly to `import_articles`:

```python
import_articles(
    ris_text=open("export.ris").read(),
    collection_name="My Collection"
)
```

---

### What does "collaboration-safe mode" mean?

By default, Zotero Keeper hides its legacy PubMed bridge tools (`search_pubmed_exclude_owned`, `import_from_pmids`, etc.) to avoid duplicating what pubmed-search-mcp already does. This prevents an AI agent from calling both and getting confused.

The public surface is:
- **Search**: handled by pubmed-search-mcp
- **Import handoff**: `import_articles` (Zotero Keeper)
- **Library reads**: all read tools (Zotero Keeper)

All writes fail closed on collection routing. `skip_collection_prompt=True` aborts; `quick_save`, `import_articles`, and `import_pdf` reject a missing collection. Saving to My Library requires explicit user confirmation plus `allow_library_root=true` (and `interactive_save` confirms `ROOT` a second time).

To restore the legacy tools (e.g. for standalone use without pubmed-search-mcp):

```bash
ZOTERO_KEEPER_ENABLE_LEGACY_PUBMED_TOOLS=1
```

---

### Can I read the full text of a PDF?

Yes, using `get_item_fulltext`. This returns text that Zotero has already indexed from the PDF. Requirements:

1. The PDF must be attached to the Zotero item
2. Zotero must have indexed it (happens automatically in the background)
3. If you need the file path for external PDF tools, use `get_item_attachments` and set `ZOTERO_DATA_DIR`

---

## Zotero API Limitations

### Why can't I delete or move items?

Zotero's local API is **read-only** for most operations. The Connector API (used by Zotero Keeper for writing) only supports **creating new items**; it cannot update, delete, or move them. See the [API Limitations section in the README](../README.md#️-zotero-api-limitations-important).

**Workarounds:**
- Delete duplicates: Zotero > Tools > **Merge Duplicates**
- Move items: **drag and drop** in Zotero's GUI
- Bulk operations: [Zutilo](https://github.com/wshanks/Zutilo) or [Zotero Actions & Tags](https://github.com/windingwind/zotero-actions-tags) plugins

---

### Why do I get a duplicate when importing the same article twice?

The Connector API always creates new items. `import_articles` uses `skip_duplicates: true` by default to check for existing PMIDs/DOIs before importing. If a duplicate appears, check whether:

- The existing item has a PMID/DOI in the correct Zotero field
- You are importing via a legacy tool that doesn't run duplicate checks

---

### Does Zotero 8 work differently from Zotero 7?

Zotero 8 stores PDF annotations as top-level items with `itemType: "annotation"`. Zotero Keeper automatically filters these out from all search, list, and statistics results.

---

## PubMed Integration

The v0.6.0 VSIX pins PubMed Search MCP 0.6.1 at commit `ad85dde`. It exposes 45 MCP SDK v2 tools in 16 categories. `build_research_chronicle` and `read_research_chronicle` replace the three former timeline tools.

### Do I need pubmed-search-mcp installed?

Only if you want to **search PubMed** from within Copilot. `import_articles` and the core library tools work without it. Install with:

```bash
uv sync --extra pubmed   # in the mcp-server directory
```

For the MCP SDK v2 release, prefer the v0.6.0 VSIX or a current source checkout; the PyPI/`uvx` package may still resolve the older release line.

---

### Why is the PubMed search slow?

NCBI's public API has rate limits. Provide your email (and optionally an API key) for higher limits:

```bash
NCBI_EMAIL=your.email@example.com
NCBI_API_KEY=your_api_key_here  # optional, get from https://account.ncbi.nlm.nih.gov/settings/
```

---

## Troubleshooting

### The MCP server starts but no tools appear in Copilot

1. Restart VS Code (Copilot re-discovers MCP servers on startup)
2. Check the MCP server logs for errors
3. Verify the path in `.vscode/mcp.json` is absolute and correct

### I get `ModuleNotFoundError: No module named 'zotero_mcp'`

The Python environment may not be activated. Use the full `uv run` command:

```bash
uv run --directory /path/to/zotero-keeper/mcp-server python -m zotero_mcp
```

### PubMed tools are missing

The `[pubmed]` extra is not installed. Run:

```bash
cd mcp-server
uv sync --extra all
```

If this started immediately after a VSIX upgrade, run **Zotero MCP: Reinstall Python Environment**. MCP SDK 2.x is incompatible with 1.x, so an older managed venv cannot safely host the new servers.

### Is there an official Zotero MCP server?

As of 2026-08-11, we could not find a Zotero-organization repository or Zotero documentation publishing an official MCP server. [`54yyyu/zotero-mcp`](https://github.com/54yyyu/zotero-mcp) is an MCP Registry-listed **community** server with a broad feature set, not a Zotero-official server. An OpenAI-curated Zotero connector is also a separate connector product; it is not evidence of a Zotero-official MCP server, and its tool schema should not be guessed.

The community server and Keeper both use the Python module name `zotero_mcp`. If you need both, put them in separate virtual environments and run them as separate MCP processes. Never install the community distribution into the extension-managed environment. See [Zotero MCP landscape](ZOTERO_MCP_LANDSCAPE.md).

---

## Contributing & Development

### How do I run the tests?

```bash
cd mcp-server
uv sync --extra dev
uv run pytest
```

### How do I contribute?

See [CONTRIBUTING.md](../CONTRIBUTING.md) for the full contribution guide.
