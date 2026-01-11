# Zotero + PubMed MCP Extension for VS Code

🔬 **AI-powered research assistant** - Integrates Zotero reference management and PubMed literature search with GitHub Copilot.

## ✨ What's New in v0.5.2

- **📊 Usage Statistics**: Track searches, imports, and full-text accesses
- **🌐 API Status Dashboard**: View and manage 8 connected APIs at a glance
- **📋 Quick Menu**: Click status bar for instant access to all features
- **🔢 Version Display**: Status bar shows current version

## Features

This extension provides two MCP (Model Context Protocol) servers that enable AI assistants like GitHub Copilot to:

### 📚 Zotero Keeper
- Search and browse your Zotero library
- Add references from PubMed or DOI
- Manage collections and tags
- Smart duplicate detection
- Batch import from PubMed searches
- **Library analytics** (stats, orphan detection)

### 🔍 PubMed Search
- Search PubMed literature with MeSH terms
- **Multi-source search** (Europe PMC, CORE, Semantic Scholar)
- Parse PICO clinical questions
- Find related and citing articles
- Get citation metrics (RCR)
- **Full-text access** (Europe PMC, CORE)
- **Session management** (retrieve previous search results)
- Export in multiple formats (RIS, BibTeX, etc.)

### 🌐 Connected APIs

| API | Description |
|-----|-------------|
| PubMed / NCBI | 36M+ biomedical articles |
| Europe PMC | 33M+ articles, full-text, text mining |
| CORE | 200M+ open access papers |
| Semantic Scholar | AI-powered recommendations |
| PubChem | Chemical compound database |
| NCBI Gene | Gene information |
| ClinVar | Clinical variants |
| Zotero Local | Reference management |

## Requirements

- **VS Code** 1.99.0 or later
- **Zotero 7** running locally (for Zotero features)

**Note**: Python is managed automatically by the extension using [uv](https://github.com/astral-sh/uv).

## Installation

1. Install this extension from the VS Code Marketplace
2. The extension will automatically:
   - Download [uv](https://github.com/astral-sh/uv) (fast Python package manager, ~10MB)
   - Create an isolated Python 3.11 environment
   - Install required packages (`zotero-keeper`, `pubmed-search-mcp`)
   - Register MCP servers with VS Code
   - **Install Copilot research workflow guides**

## Usage

Once installed, the MCP tools will be available to GitHub Copilot. Try asking:

- *"Search PubMed for remimazolam sedation"*
- *"Find recent articles about CRISPR gene editing"*
- *"Save this article to my Zotero library"*
- *"Show my recent Zotero references"*
- *"Get my last search results"* (uses session management)

### 📊 Status Bar

Click the status bar item to access:

- **📊 Usage Statistics** - Track your research activity
- **🌐 API Status** - View/configure connected APIs
- **⚙️ Settings** - Quick access to configuration
- **🧙 Setup Wizard** - One-click setup

### 🎯 Copilot Research Skills

The extension installs workflow guides that teach Copilot:

1. **Search → Review → Ask Collection → Import** workflow
2. Use `get_session_pmids` instead of re-searching
3. Use cached articles to save API quota
4. Check for duplicates before importing

Run `Zotero MCP: Install Copilot Research Skills` to manually install/update.

## Extension Settings

| Setting | Default | Description |
|---------|---------|-------------|
| `zoteroMcp.zoteroHost` | `localhost` | Zotero host address |
| `zoteroMcp.zoteroPort` | `23119` | Zotero API port |
| `zoteroMcp.ncbiEmail` | | Email for NCBI API (recommended) |
| `zoteroMcp.enableZoteroKeeper` | `true` | Enable Zotero Keeper server |
| `zoteroMcp.enablePubmedSearch` | `true` | Enable PubMed Search server |

## Commands

| Command | Description |
|---------|-------------|
| `Zotero MCP: Setup Wizard` | One-click setup |
| `Zotero MCP: Quick Menu` | Show quick access menu |
| `Zotero MCP: Show Statistics` | View usage statistics |
| `Zotero MCP: Show API Status` | View connected APIs |
| `Zotero MCP: Check Zotero Connection` | Verify Zotero is accessible |
| `Zotero MCP: Install Copilot Research Skills` | Install workflow guides |
| `Zotero MCP: Reinstall Python Environment` | Reinstall uv and Python packages |
| `Zotero MCP: Show Status` | Show full extension status |
| `Zotero MCP: Open Settings` | Open extension settings |

## How It Works

This extension uses [uv](https://github.com/astral-sh/uv) from Astral to manage Python:

1. **First Run**: Downloads uv binary (~10MB) to extension storage
2. **Environment Setup**: Creates isolated venv with Python 3.11
3. **Package Install**: Installs `zotero-keeper` and `pubmed-search-mcp` (10-100x faster than pip)
4. **MCP Servers**: Starts both servers and registers with VS Code
5. **Copilot Skills**: Installs research workflow guides to workspace

The Python environment is completely isolated from your system Python.

## Troubleshooting

### Cannot connect to Zotero
1. Make sure Zotero 7 is running
2. Check that the API is enabled (Edit → Settings → Advanced → Allow other applications...)
3. Verify host/port settings match your setup

### Extension not activating
1. Check the "Zotero MCP" output channel for errors
2. Try running `Zotero MCP: Reinstall Python Environment` command
3. Restart VS Code

### Copilot not using tools correctly
1. Run `Zotero MCP: Install Copilot Research Skills` to update workflow guides
2. The guides teach Copilot the correct order of operations

### uv download failed
1. Check your internet connection
2. Check if your firewall blocks downloads from `github.com`
3. The extension will retry on next activation

## Related Projects

- [zotero-keeper](https://github.com/u9401066/zotero-keeper) - Zotero MCP server
- [pubmed-search-mcp](https://github.com/u9401066/pubmed-search-mcp) - PubMed MCP server
- [uv](https://github.com/astral-sh/uv) - Fast Python package manager
- [Model Context Protocol](https://modelcontextprotocol.io/) - MCP specification

## License

Apache-2.0

## Contributing

Contributions welcome! Please see [CONTRIBUTING.md](https://github.com/u9401066/zotero-keeper/blob/main/CONTRIBUTING.md).
