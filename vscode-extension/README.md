# Zotero + PubMed MCP Extension for VS Code

🔬 **AI-powered research assistant** - Integrates Zotero reference management and PubMed literature search with GitHub Copilot.

## Features

This extension provides two MCP (Model Context Protocol) servers that enable AI assistants like GitHub Copilot to:

### 📚 Zotero Keeper
- Search and browse your Zotero library
- Add references from PubMed or DOI
- Manage collections and tags
- Smart duplicate detection
- Batch import from PubMed searches

### 🔍 PubMed Search
- Search PubMed literature with MeSH terms
- Parse PICO clinical questions
- Find related and citing articles
- Get citation metrics (RCR)
- Export in multiple formats (RIS, BibTeX, etc.)

## Requirements

- **VS Code** 1.99.0 or later
- **Python** 3.11 or later
- **Zotero 7** running locally (for Zotero features)

## Installation

1. Install this extension from the VS Code Marketplace
2. The extension will automatically:
   - Detect your Python installation
   - Install required packages (`zotero-keeper`, `pubmed-search-mcp`)
   - Register MCP servers with VS Code

## Usage

Once installed, the MCP tools will be available to GitHub Copilot. Try asking:

- *"Search PubMed for remimazolam sedation"*
- *"Find recent articles about CRISPR gene editing"*
- *"Save this article to my Zotero library"*
- *"Show my recent Zotero references"*

## Extension Settings

| Setting | Default | Description |
|---------|---------|-------------|
| `zoteroMcp.pythonPath` | (auto) | Path to Python interpreter |
| `zoteroMcp.zoteroHost` | `localhost` | Zotero host address |
| `zoteroMcp.zoteroPort` | `23119` | Zotero API port |
| `zoteroMcp.ncbiEmail` | | Email for NCBI API (recommended) |
| `zoteroMcp.enableZoteroKeeper` | `true` | Enable Zotero Keeper server |
| `zoteroMcp.enablePubmedSearch` | `true` | Enable PubMed Search server |
| `zoteroMcp.autoInstallPackages` | `true` | Auto-install Python packages |

## Commands

| Command | Description |
|---------|-------------|
| `Zotero MCP: Check Zotero Connection` | Verify Zotero is accessible |
| `Zotero MCP: Install Python Packages` | Reinstall Python packages |
| `Zotero MCP: Show Status` | Show extension status |
| `Zotero MCP: Open Settings` | Open extension settings |

## Troubleshooting

### Python not found
1. Install Python 3.11+ from [python.org](https://www.python.org/)
2. Or set `zoteroMcp.pythonPath` to your Python interpreter path

### Cannot connect to Zotero
1. Make sure Zotero 7 is running
2. Check that the API is enabled (Edit → Settings → Advanced → Allow other applications...)
3. Verify host/port settings match your setup

### Packages not installing
1. Try running `Zotero MCP: Install Python Packages` command
2. Check the "Zotero MCP" output channel for errors
3. Try installing manually: `pip install zotero-keeper[all] pubmed-search-mcp[mcp]`

## Related Projects

- [zotero-keeper](https://github.com/u9401066/zotero-keeper) - Zotero MCP server
- [pubmed-search-mcp](https://github.com/u9401066/pubmed-search-mcp) - PubMed MCP server
- [Model Context Protocol](https://modelcontextprotocol.io/) - MCP specification

## License

Apache-2.0

## Contributing

Contributions welcome! Please see [CONTRIBUTING.md](https://github.com/u9401066/zotero-keeper/blob/main/CONTRIBUTING.md).
