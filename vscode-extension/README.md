# Zotero + PubMed MCP Extension for VS Code

🔬 **AI-powered research assistant** - Integrates Zotero reference management and PubMed literature search with GitHub Copilot.

## ✨ What's New in v0.5.20

- **📦 Official Copilot Assets Bundled**: extension 會隨套件帶入 keeper / pubmed-search-mcp 的正式 Copilot 指令、workflow、agent 與 hook scripts
- **🛡️ Collaboration-safe Workflow Refresh**: 內建文件改為預設引導 Search → Review → Ask Collection → Import，避免直接暴露舊版 legacy PubMed 匯入路徑
- **🔄 Embedded Package Upgrade Path**: embedded Python 會升級到 zotero-keeper 1.12.0 與 pubmed-search-mcp 0.5.2，並透過新 tag 的 source archive 觸發乾淨更新

## Features

This extension provides two MCP (Model Context Protocol) servers that enable AI assistants like GitHub Copilot to:

### 📚 Zotero Keeper
- Search and browse your Zotero library
- Add references from PubMed or DOI
- Manage collections and tags
- Smart duplicate detection
- Batch import from PubMed searches
- **Library analytics** (stats, orphan detection)
- **PDF attachment access** (list attachments, get indexed fulltext)

### 🔍 PubMed Search (v0.5.2)

- **`unified_search`** - 統一搜尋入口，自動合併去重多來源結果
- **Multi-source search** (PubMed, Europe PMC, CORE)
- **預印本搜尋** - 支援 arXiv、medRxiv、bioRxiv（`include_preprints`）
- **同行審查篩選** - 只顯示同行審查文章（`peer_reviewed_only`）
- Parse PICO clinical questions
- Find related and citing articles
- Get citation metrics (RCR)
- **ICD ↔ MeSH 轉換** - 自動轉換 ICD 代碼和 MeSH 術語
- **研究時間軸** - 建構與比較研究領域的歷史演進
- **生物醫學圖片搜尋** - 搜尋 Open-i 和 Europe PMC 圖片
- **Full-text access** (Europe PMC, CORE)
- **Session management** (retrieve previous search results)
- **NCBI 延伸** (Gene, PubChem, ClinVar)
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
- **Zotero 7 or 8** running locally (for Zotero features)

**Note**: Python is managed automatically by the extension using [uv](https://github.com/astral-sh/uv).

## Installation

1. Install this extension from the VS Code Marketplace
2. The extension will automatically:
   - Download [uv](https://github.com/astral-sh/uv) (fast Python package manager, ~10MB)
   - Create an isolated Python 3.12 environment
   - Install required packages (`zotero-keeper`, `pubmed-search-mcp`)
   - Register MCP servers with VS Code
   - **Install official Copilot instructions, workflow guides, `@research` agent, and collaboration hook assets**

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

Run `Zotero MCP: Install Official Copilot Assets` to manually install/update.

## Extension Settings

| Setting | Default | Description |
|---------|---------|-------------|
| `zoteroMcp.zoteroHost` | `localhost` | Zotero host address |
| `zoteroMcp.zoteroPort` | `23119` | Zotero API port |
| `zoteroMcp.ncbiEmail` | | Email for NCBI API (自動偵測 git email，通常不需手動設定) |
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
| `Zotero MCP: Install Official Copilot Assets` | Install or refresh the bundled official Copilot assets |
| `Zotero MCP: Reinstall Python Environment` | Reinstall uv and Python packages |
| `Zotero MCP: Show Status` | Show full extension status |
| `Zotero MCP: Open Settings` | Open extension settings |

## How It Works

This extension uses [uv](https://github.com/astral-sh/uv) from Astral to manage Python:

1. **First Run**: Downloads uv binary (~10MB) to extension storage
2. **Environment Setup**: Creates isolated venv with Python 3.12
3. **Package Install**: Installs `zotero-keeper` and `pubmed-search-mcp` (10-100x faster than pip)
4. **MCP Servers**: Starts both servers and registers with VS Code
5. **Copilot Skills**: Installs research workflow guides to workspace

The Python environment is completely isolated from your system Python.

## Troubleshooting

### Cannot connect to Zotero
1. Make sure Zotero is running
2. Check that the API is enabled (Edit → Settings → Advanced → Allow other applications...)
3. Verify host/port settings match your setup

### Extension not activating
1. Check the "Zotero MCP" output channel for errors
2. Try running `Zotero MCP: Reinstall Python Environment` command
3. Restart VS Code

### Copilot not using tools correctly
1. Run `Zotero MCP: Install Official Copilot Assets` to update workflow guides
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
