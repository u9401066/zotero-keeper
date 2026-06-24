# Zotero + PubMed MCP Extension for VS Code

## What's New in v0.5.35

- **Import PDF files into Zotero** 📎: a new `import_pdf` tool imports a local PDF entirely within the Local/Connector architecture (no Web API key). Two modes — attach the PDF to a parent built from PubMed metadata, or drop a PDF and let Zotero auto-recognize it (extract the DOI/title and build the item).
- **Bundled Zotero Keeper 1.14.0** with the new Connector attachment upload support.

## What's New in v0.5.34

- **Complete, type-aware Zotero metadata**: imports now detect the correct Zotero item type (journal article, book, book chapter, conference paper, thesis, report, web page, preprint, software/repository, dataset, …) and route every field to that type's schema, so books keep ISBN/publisher/edition, chapters keep the book title, conferences keep the conference/proceedings name, and repositories become software items.
- **No metadata is ever lost**: any field that a given item type does not support is preserved in the Zotero `Extra` field instead of being silently dropped.
- **Richer provenance**: imported records now carry `url`, `accessDate`, and `libraryCatalog`, and duplicate detection also reads Zotero's native `PMID` field.
- **Bundled Zotero Keeper 1.13.0** with an expanded RIS importer (publisher, place, edition, ISBN vs ISSN, series, editors).

## What's New in v0.5.33

- **PubMed Search 0.5.17 baseline**: updates the managed PubMed Search MCP source pin, bundled assistant assets, and keeper dependency floor to the latest contact-email fallback release.
- **Managed install refresh**: extension-managed installs now point at the `v0.5.33-ext` archive and the `pubmed-search-mcp` `v0.5.17` commit archive.
- **Fulltext source contact fix**: managed PubMed installs now inherit the runtime contact email for OpenAlex, CrossRef, Unpaywall, and fulltext downloader fallbacks.

## What's New in v0.5.32

- **Zotero 9 readiness**: connection checks now surface Zotero version headers, Connector API version, and Local API read status separately.
- **PubMed Search 0.5.12 baseline**: updates the managed PubMed Search MCP source pin and keeper dependency floor to the latest release.
- **Zotero 7/8/9 docs**: setup copy, walkthroughs, and compatibility docs now reflect Zotero 7, 8, and 9 support.

## What's New in v0.5.31

- **Foam / LLM wiki workflow**: installs new Cline and Codex `llm-wiki-builder` skills for building citation-aware Foam-compatible Markdown note graphs.
- **Wiki rendering rules**: bundles `.clinerules/35-foam-llm-wiki.md` with Foam wikilink, filename, citation, and evidence hygiene guardrails.
- **End-to-end wiki build workflow**: adds `.clinerules/workflows/llm-wiki-build.md` to coordinate Zotero, PubMed, full-text/document tools, Markdown writes, and link validation.

## What's New in v0.5.30

- **Release install stability**: pins the extension-managed Zotero Keeper install to the new `v0.5.30-ext` archive so users receive the latest runtime fixes.
- **PubMed citation metrics compatibility**: accepts both sync and async PubMed Search MCP citation-metrics implementations.
- **CI and VSIX asset checks**: fixes cross-directory Cline skill audits and Windows-safe asset synchronization checks.

## What's New in v0.5.29

- **Codex MCP auto-configuration**: extension now writes `[mcp_servers.zotero-keeper]` and `[mcp_servers.pubmed-search-mcp]` into Codex CLI's `~/.codex/config.toml` automatically (parity with Cline). Honors `$CODEX_HOME`; preserves all unrelated user content.
- **Cline auto-configuration now actually triggers**: added `onStartupFinished` activation event so Cline-only sessions reliably populate `cline_mcp_settings.json` instead of staying empty.

## What's New in v0.5.28

- **Windows-safe installs and upgrades**: system/custom Python fallback now creates a writable extension-managed venv before `uv pip install`, avoiding protected paths such as `C:\Python314\Lib\site-packages`.
- **Codex/Cline harness refresh**: VSIX installs Codex `AGENTS.md`, `.codex/skills`, Cline MCP settings, and curated assistant skills while preserving user customizations.
- **VSIX release guards**: packaging, asset sync, version sync, and direct VSIX content checks now verify the shipped harness and package sources.

![Zotero + PubMed MCP banner](https://raw.githubusercontent.com/u9401066/zotero-keeper/main/vscode-extension/resources/branding/vsx-banner.png)

🔬 **AI-powered research assistant** - Integrates Zotero reference management and PubMed literature search with GitHub Copilot.

## ✨ What's New in v0.5.26

- **PubMed Search 0.5.12 baseline**: updates the bundled PubMed Search MCP snapshot to the latest upstream tag with Entrez runtime stability fixes.
- **Cline asset compatibility**: fixes strict YAML frontmatter for bundled skills and packages Zotero/PubMed Cline rules into the VSIX.
- **Marketplace banner fix**: uses a GitHub raw image URL so the VSIX details page renders the banner correctly.

## ✨ What's New in v0.5.25

- **🚀 Ready-to-publish maintenance**: this release aligns VSIX metadata and installer source URL after the 0.5.24 hotfix.

## ✨ What's New in v0.5.24

- **🎨 Marketplace Branding Refresh**: keeper icon 與 VSX banner 改為新的系列化品牌視覺，對齊 Academic Figures MCP / MedPaper Assistant 的產品語言
- **🔐 OpenAlex API Key Support**: extension 新增 `zoteroMcp.openAlexApiKey` 設定，會將 `OPENALEX_API_KEY` 傳給 PubMed Search MCP
- **🔄 Bundled Asset Refresh**: extension 重新同步最新 pubmed-search-mcp agents / hooks / skills，並更新到包含修正 `os` import 的版本
- **PubMed Search baseline upgraded to 0.5.4**: embedded environment now requires `pubmed-search-mcp>=0.5.4`, and startup now injects `PUBMED_WORKSPACE_DIR` to avoid VS Code regressions.
- **Fixed PubMed package source**: embedded/manual 安裝改用已修正的 upstream snapshot，避免直接安裝有問題的 `0.5.4` PyPI 套件

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

### 🔍 PubMed Search (v0.5.17)

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
- **Zotero 7, 8, or 9** running locally (for Zotero features)

**Note**: Python is managed automatically by the extension using [uv](https://github.com/astral-sh/uv).

## Installation

1. Install this extension from the VS Code Marketplace
2. The extension will automatically:
   - Download [uv](https://github.com/astral-sh/uv) (fast Python package manager, ~10MB)
   - Create an isolated Python 3.12 environment
   - Install required packages (`zotero-keeper`, fixed `pubmed-search-mcp` snapshot)
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

### 🎯 Assistant Research Assets

The extension installs workflow guides that teach Copilot and Cline:

1. **Search → Review → Ask Collection → Import** workflow
2. Use `get_session_pmids` instead of re-searching
3. Use cached articles to save API quota
4. Check for duplicates before importing

Run `Zotero MCP: Install Official Assistant Assets` to manually install/update.

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
| `Zotero MCP: Install Official Assistant Assets` | Install or refresh the bundled official Copilot and Cline assets |
| `Zotero MCP: Reinstall Python Environment` | Reinstall uv and Python packages |
| `Zotero MCP: Show Status` | Show full extension status |
| `Zotero MCP: Open Settings` | Open extension settings |

## How It Works

This extension uses [uv](https://github.com/astral-sh/uv) from Astral to manage Python:

1. **First Run**: Downloads uv binary (~10MB) to extension storage
2. **Environment Setup**: Creates isolated venv with Python 3.12
3. **Package Install**: Installs `zotero-keeper` and the fixed `pubmed-search-mcp` snapshot (10-100x faster than pip)
4. **MCP Servers**: Starts both servers and registers with VS Code
5. **Assistant Assets**: Installs research workflow guides to workspace

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
1. Run `Zotero MCP: Install Official Assistant Assets` to update workflow guides
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
