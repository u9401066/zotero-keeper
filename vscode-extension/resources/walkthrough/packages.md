# Python Packages

The extension needs two Python packages:

| Package | Description |
|---------|-------------|
| `zotero-keeper` | Manages your Zotero library |
| `pubmed-search-mcp` | Searches PubMed literature |

## Automatic Installation

When you activate the extension, it will automatically install these packages using `uv`:

```bash
uv venv <extension-storage>/venv --python 3.12
uv pip install --upgrade --python <extension-storage>/venv/bin/python \
  "zotero-keeper @ https://github.com/u9401066/zotero-keeper/archive/refs/tags/v0.5.28-ext.tar.gz#subdirectory=mcp-server" \
  "pubmed-search-mcp @ https://github.com/u9401066/pubmed-search-mcp/archive/13292cb91215cff707a4380e955967e5e9b3e765.tar.gz"
```

On Windows the Python path is `<extension-storage>\venv\Scripts\python.exe`.

## Manual Installation

If automatic installation fails, run this VS Code command from the Command Palette:

```text
Zotero MCP: Reinstall Embedded Python
```

## Virtual Environment

We recommend using a virtual environment to avoid conflicts:

```bash
uv venv ~/.zotero-mcp-venv
source ~/.zotero-mcp-venv/bin/activate  # Linux/macOS
uv pip install --python ~/.zotero-mcp-venv/bin/python zotero-keeper pubmed-search-mcp
```

Then set `zoteroMcp.pythonPath` to `~/.zotero-mcp-venv/bin/python`.
