# Python Packages

The extension needs two Python packages:

| Package | Description |
|---------|-------------|
| `zotero-keeper` | Manages your Zotero library |
| `pubmed-search-mcp` | Searches PubMed literature |

## Automatic Installation

When you activate the extension, it will automatically install these packages using `pip`:

```bash
pip install zotero-keeper[all] pubmed-search-mcp[mcp]
```

## Manual Installation

If automatic installation fails, run in your terminal:

```bash
pip install zotero-keeper[all] pubmed-search-mcp[mcp]
```

## Virtual Environment

We recommend using a virtual environment to avoid conflicts:

```bash
python -m venv ~/.zotero-mcp-venv
source ~/.zotero-mcp-venv/bin/activate  # Linux/macOS
pip install zotero-keeper[all] pubmed-search-mcp[mcp]
```

Then set `zoteroMcp.pythonPath` to `~/.zotero-mcp-venv/bin/python`.
