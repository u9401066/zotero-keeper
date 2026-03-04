# Zotero Keeper 📚

Let AI manage your references! A MCP Server connecting VS Code Copilot / Claude Desktop to your local Zotero library.

[![Python 3.12+](https://img.shields.io/badge/python-3.12+-blue.svg)](https://www.python.org/downloads/)
[![MCP SDK](https://img.shields.io/badge/MCP-FastMCP-green.svg)](https://github.com/modelcontextprotocol/python-sdk)
[![License](https://img.shields.io/badge/license-Apache%202.0-blue.svg)](LICENSE)
[![Zotero 7/8](https://img.shields.io/badge/Zotero-7%20%2F%208-red.svg)](https://www.zotero.org/)
[![CI](https://github.com/u9401066/zotero-keeper/actions/workflows/ci.yml/badge.svg)](https://github.com/u9401066/zotero-keeper/actions/workflows/ci.yml)
[![PRs Welcome](https://img.shields.io/badge/PRs-welcome-brightgreen.svg)](CONTRIBUTING.md)

> 🌐 **English** | **[繁體中文](README.zh-TW.md)**

---

## 🚀 One-Click Install (VS Code)

> **Prerequisites**: [Zotero 7 or 8](https://www.zotero.org/download/) must be running

<a href="vscode:mcp/install?%7B%22name%22%3A%22zotero-keeper%22%2C%22command%22%3A%22uvx%22%2C%22args%22%3A%5B%22zotero-keeper%22%5D%7D"><img src="https://img.shields.io/badge/VS%20Code-Install%20MCP%20Server-007ACC?style=for-the-badge&logo=visualstudiocode" alt="Install in VS Code"></a>
<a href="vscode-insiders:mcp/install?%7B%22name%22%3A%22zotero-keeper%22%2C%22command%22%3A%22uvx%22%2C%22args%22%3A%5B%22zotero-keeper%22%5D%7D"><img src="https://img.shields.io/badge/VS%20Code%20Insiders-Install%20MCP%20Server-24bfa5?style=for-the-badge&logo=visualstudiocode" alt="Install in VS Code Insiders"></a>

> 💡 **Requires [uv](https://docs.astral.sh/uv/getting-started/installation/)** - Click installs automatically via `uvx zotero-keeper`

---

## ✨ What is this?

**Zotero Keeper** is a [MCP Server](https://modelcontextprotocol.io/) that lets your AI assistant:

- 🔍 **Search references**: "Find papers about CRISPR from 2024"
- 📖 **View details**: "What's the abstract of this article?"
- ➕ **Add references**: "Add this DOI to my Zotero" (with auto-fetch metadata!)
- 🔄 **PubMed integration**: "Search PubMed, skip what I already have"
- 📁 **Interactive save**: Shows collection options for you to choose!

No more manually searching, copying, pasting. Just tell your AI in natural language!

---

## ✨ Features

- **🔌 MCP Native**: Built with FastMCP SDK for seamless AI integration
- **📖 MCP Resources**: Browse Zotero data via URIs (`zotero://collections`, etc.)
- **💬 MCP Elicitation**: Interactive collection selection with numbered options
- **🔒 Auto-fetch Metadata**: DOI/PMID → complete abstract + all fields automatically!
- **� Citation Metrics**: RCR, NIH Percentile → stored in Zotero extra field (v1.8.0)
- **🛡️ Collection 防呆**: Use collection_name for auto-validation (v1.8.0)
- **�📖 Read Operations**: Search, list, retrieve items from local Zotero
- **✏️ Write Operations**: Add references via Connector API
- **🧠 Smart Features**: Duplicate detection, validation, intelligent import
- **📁 Collection Support**: Nested collections (folders) with hierarchy
- **🏗️ Clean Architecture**: DDD with onion architecture
- **🔒 No Cloud Required**: All operations are local

---

## 🚀 Quick Start

### Prerequisites

- ✅ [Python 3.12+](https://www.python.org/downloads/)
- ✅ [Zotero 7 or 8](https://www.zotero.org/download/) (must be running)
- ✅ [VS Code](https://code.visualstudio.com/) + GitHub Copilot, or [Claude Desktop](https://claude.ai/)
- ✅ [uv](https://docs.astral.sh/uv/getting-started/installation/) (recommended)

### Installation

```bash
# Clone the repository
git clone https://github.com/u9401066/zotero-keeper.git
cd zotero-keeper/mcp-server

# Install with uv (required)
uv pip install -e .

# Test (make sure Zotero is running)
python -m zotero_mcp
```

### Configure VS Code Copilot

Create `.vscode/mcp.json` in your workspace:

```json
{
  "servers": {
    "zotero-keeper": {
      "type": "stdio",
      "command": "uv",
      "args": [
        "run",
        "--directory",
        "/path/to/zotero-keeper/mcp-server",
        "python", "-m", "zotero_mcp"
      ]
    }
  }
}
```

### Configure Claude Desktop

Add to `claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "zotero-keeper": {
      "command": "python",
      "args": ["-m", "zotero_mcp"],
      "cwd": "/path/to/zotero-keeper/mcp-server"
    }
  }
}
```

> 💡 Use absolute paths and ensure [uv](https://docs.astral.sh/uv/) is installed.

---

## 🔧 Available Tools (25 Total)

> 💡 **Tip**: Most read operations can also be done via [MCP Resources](#-mcp-resources-browsable-data) without calling tools.

### 📖 Core Tools (server.py - 6 tools)

| Tool | Description | Example |
|------|-------------|---------|
| `check_connection` | Test Zotero connectivity | "Is Zotero running?" |
| `search_items` | Search references | "Find papers about CRISPR" |
| `get_item` | Get item details | "Show abstract for key:ABC123" |
| `list_items` | List recent items | "Show papers in collection X" |
| `list_tags` | List all tags | "What tags have I used?" |
| `get_item_types` | Available item types | "What types can I add?" |

### 📁 Collection Tools (server.py - 5 tools)

> ⚠️ These can also be accessed via `zotero://collections/...` Resources

| Tool | Description | Equivalent Resource |
|------|-------------|--------------------|
| `list_collections` | List all folders | `zotero://collections` |
| `get_collection` | Get collection details | `zotero://collections/{key}` |
| `get_collection_items` | Items in a collection | `zotero://collections/{key}/items` |
| `get_collection_tree` | Hierarchical tree view | `zotero://collections/tree` |
| `find_collection` | Find by name | — (Tool only) |

### ✏️ Save Tools (interactive_tools.py - 2 tools)

> 📊 **Auto RCR**: When PMID is provided, automatically fetches Relative Citation Ratio from iCite and stores in Zotero's extra field

| Tool | Description | Example |
|------|-------------|--------|
| `interactive_save` ⭐ | Interactive save + auto RCR | "Save this paper to Zotero" |
| `quick_save` | Quick save + auto RCR | "Quick save to AI Research" |

### 🔍 Saved Search Tools (saved_search_tools.py - 3 tools)

| Tool | Description | Example |
|------|-------------|---------|
| `list_saved_searches` | List all saved searches | "What saved searches exist?" |
| `run_saved_search` | Execute a saved search | "Which papers have no PDF?" |
| `get_saved_search_details` | Get search conditions | "What's in 'Missing PDF' search?" |

### 🔍 Advanced Search & PubMed Integration (search_tools.py - 3 tools)

| Tool | Description | Example |
|------|-------------|---------|
| `advanced_search` ⭐ | Multi-condition search (itemType, tag, qmode) | "Find all journal articles tagged with AI" |
| `search_pubmed_exclude_owned` | Search PubMed, exclude owned | "Find CRISPR papers I don't have" |
| `check_articles_owned` | Check if PMIDs exist in Zotero | "Do I have these PMIDs?" |

### 📥 Import Tools (pubmed_tools.py - 3 tools, batch_tools.py - 1 tool)

> 📊 **RCR Default ON**: All PubMed import tools automatically fetch RCR by default

| Tool | Description | Example |
|------|-------------|--------|
| `quick_import_pmids` ⭐ | Simplest one-step import | "Import these PMIDs" |
| `import_ris_to_zotero` | Import RIS citations | "Import this RIS text" |
| `import_from_pmids` | Import by PMID + auto RCR | "Import PMID 12345678" |
| `batch_import_from_pubmed` | Batch import + validation + RCR | "Import PMIDs to 'AI Research'" |

### 📊 Analytics Tools (analytics_tools.py - 2 tools) ⭐ NEW!

| Tool | Description | Example |
|------|-------------|--------|
| `get_library_stats` | Library statistics (year/author/journal) | "Show my library statistics" |
| `find_orphan_items` | Find unorganized items | "Which papers need organizing?" |

#### batch_import_from_pubmed v1.8.0+ Features

```python
# ✅ Simple: just provide PMIDs and collection
# RCR is automatically fetched by default!
batch_import_from_pubmed(
    pmids="38353755,37864754",
    collection_name="AI Research"  # Auto-validates name
)

# Zotero extra 欄位會包含:
# PMID: 38353755
# RCR: 5.23
# NIH Percentile: 85.2
# Citations: 127
```

#### advanced_search v1.8.0 新功能

```python
# 🔍 依文獻類型搜尋
advanced_search(item_type="journalArticle")  # 只找期刊論文
advanced_search(item_type="book")  # 只找書籍
advanced_search(item_type="-attachment")  # 排除附件

# 🏷️ 依標籤搜尋
advanced_search(tag="AI")  # 具有 AI 標籤的文獻
advanced_search(tags=["AI", "Review"])  # 同時具有兩個標籤 (AND)
advanced_search(tag="AI || ML")  # 具有任一標籤 (OR)

# 📝 全文搜尋 (含 abstract)
advanced_search(q="XGBoost", qmode="everything")  # 搜尋摘要內容

# 🌟 組合條件
advanced_search(
    q="machine learning",
    item_type="journalArticle",
    tag="AI",
    sort="dateAdded",
    direction="desc"
)
```

---

## 📖 MCP Resources (Browsable Data)

No tool calls needed! AI can directly browse Zotero data:

| Resource URI | Description |
|--------------|-------------|
| `zotero://collections` | All collections |
| `zotero://collections/tree` | Collection hierarchy |
| `zotero://collections/{key}` | Specific collection |
| `zotero://collections/{key}/items` | Items in collection |
| `zotero://items` | Recent items |
| `zotero://items/{key}` | Item details |
| `zotero://tags` | All tags |
| `zotero://searches` | Saved searches |
| `zotero://searches/{key}` | Search details |
| `zotero://schema/item-types` | Available item types |

---

## 🎯 Interactive Save (Recommended!)

The `interactive_save` tool uses **MCP Elicitation** to show collection options:

```
User: "Save this DOI:10.1234/example paper to Zotero"

[MCP Elicitation pops up]
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📚 Saving: Deep Learning for Medical Imaging

⭐ Suggested:
   1. AI Research (match: 90%) - Title matches
   2. Medical Imaging (match: 75%) - Keyword matches

📂 All Collections:
   3. Biology (12 items)
   4. Chemistry (8 items)
   5. To Read (23 items)

0. Save to My Library (no collection)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Enter the number of your choice: [User enters: 1]

AI: ✅ Saved to 'AI Research' collection!
```

### 🔒 Data Integrity: Auto-fetch Metadata

When you provide a **DOI** or **PMID**, the tool automatically fetches complete metadata:

- **DOI** → CrossRef API → Full abstract, authors, journal, date
- **PMID** → PubMed API → Full abstract, MeSH terms, affiliations

No more missing abstracts! Just provide the identifier.

---

## 📁 Collection Organization

Zotero supports **nested collections**. Recommended strategies:

### By Topic (Recommended)
```
📁 My Library
├── 📁 Research Topics
│   ├── 📂 CRISPR Gene Editing
│   ├── 📂 Machine Learning in Medicine
│   └── 📂 Anesthesia Safety
├── 📁 Projects
│   ├── 📂 2024 Paper Draft
│   └── 📂 PhD Thesis
└── 📁 Reading List
    ├── 📂 To Read
    └── 📂 Important
```

> 💡 **Best Practice**: Use **collections** for primary organization, **tags** for cross-cutting attributes (e.g., "to-read", "important", "review").

---

## 🔬 PubMed Integration

Works seamlessly with [pubmed-search-mcp](https://github.com/u9401066/pubmed-search-mcp):

```
You: "Find new anesthesia AI papers from 2024 that I don't have"

AI executes:
1. search_pubmed_exclude_owned("anesthesia AI", min_year=2024)
   → Found 30, you own 5, returns 25 new ones

2. batch_import_from_pubmed(pmids="12345,67890,...")
   → Batch imports with complete abstracts, authors, DOI

You: Done! 25 new papers in Zotero
```

### Install PubMed Integration

```bash
uv pip install -e ".[pubmed]"
```

---

## 🌐 Remote Zotero Setup

If Zotero runs on another computer:

### 1. On Zotero Machine (Windows)

```powershell
# Enable Local API (in Zotero → Tools → Developer → Run JavaScript)
Zotero.Prefs.set("httpServer.localAPI.enabled", true)

# Open firewall
netsh advfirewall firewall add rule name="Zotero" dir=in action=allow protocol=TCP localport=23119

# Setup port proxy (Zotero only listens on 127.0.0.1)
netsh interface portproxy add v4tov4 listenaddress=0.0.0.0 listenport=23119 connectaddress=127.0.0.1 connectport=23119
```

### 2. Configure MCP Server

```json
{
  "env": {
    "ZOTERO_HOST": "192.168.1.100",
    "ZOTERO_PORT": "23119"
  }
}
```

---

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────┐
│           AI Agent (VS Code / Claude)           │
└──────────────────────┬──────────────────────────┘
                       │ MCP Protocol
                       │ ├── Tools (22)
                       │ ├── Resources (10 URIs)
                       │ └── Elicitation (interactive input)
                       ▼
┌─────────────────────────────────────────────────┐
│              Zotero Keeper MCP Server           │
│  ┌───────────────────────────────────────────┐  │
│  │  MCP Layer                                │  │
│  │  ├── server.py (11 tools: 6 core + 5 collection) │
│  │  ├── resources.py (10 URIs, incl. collections)   │
│  ├── interactive_tools.py (2 save tools)  │  │
│  │  ├── saved_search_tools.py (3 tools)      │  │
│  │  ├── search_tools.py (3 tools)            │  │
│  │  ├── pubmed_tools.py (2 tools)            │  │
│  │  ├── batch_tools.py (1 tool)              │  │
│  │  └── smart_tools.py (helpers only)        │  │
│  └───────────────────────────────────────────┘  │
└──────────────────────┬──────────────────────────┘
                       │ HTTP (port 23119)
                       ▼
┌─────────────────────────────────────────────────┐
│              Zotero Desktop Client              │
│  ├── Local API (/api/...) → Read               │
│  └── Connector API (/connector/...) → Write    │
└─────────────────────────────────────────────────┘
```

---

## ⚠️ Zotero API Limitations (Important!)

### � API Capability Matrix

Zotero provides **two local APIs**, but neither supports full CRUD:

| API | Endpoint | Read | Create | Update | Delete |
|-----|----------|:----:|:------:|:------:|:------:|
| **Local API** | `/api/...` | ✅ | ❌ | ❌ | ❌ |
| **Connector API** | `/connector/...` | ❌ | ✅ | ❌ | ❌ |

### 🔍 Technical Details

**Local API** (port 23119):
- Designed for reading Zotero data (items, collections, tags)
- Per [official source code](https://github.com/zotero/zotero/blob/main/chrome/content/zotcom/server/server_localAPI.js#L28-L43): **"Write access is not yet supported."**
- DELETE/PATCH/PUT methods return `501 Not Implemented`

**Connector API** (port 23119):
- Designed for browser extensions to **save new items**
- `saveItems` endpoint: **Always creates NEW items, never updates**
- Even if you import the same PMID twice → creates duplicate items
- No `updateItem` or `deleteItem` endpoints exist

### 🔴 Operations NOT Supported

| Operation | API Support | Technical Reason |
|-----------|-------------|------------------|
| ❌ **Delete items** | 501 Not Implemented | Local API is read-only |
| ❌ **Update items** | 501 Not Implemented | Local API is read-only |
| ❌ **Move items to collection** | Cannot modify | Connector API only creates, never updates |
| ❌ **Add tags to existing items** | Cannot modify | No update endpoint available |
| ❌ **Create collections** | 400 Bad Request | Connector API doesn't support it |
| ❌ **Delete collections** | 501 Not Implemented | Local API is read-only |
| ❌ **Merge duplicates** | No API | Must use Zotero GUI |

### 💡 What This Means

**"Smart Management" Limitations:**

```
❌ Cannot do:
- "Move these 10 papers to another collection"
- "Delete all duplicate references"
- "Help me organize my collections"
- "Archive old papers"

✅ Can do:
- "Add to specific collection when importing" (at creation time)
- "Search for matching references" (then handle manually)
- "List potential duplicates" (but manual deletion needed)
```

### 🛠️ Workarounds

| Need | Alternative |
|------|-------------|
| Organize collections | Drag & drop in Zotero GUI |
| Delete duplicates | Zotero → Tools → "Merge duplicates" |
| Batch operations | Use [Zotero Actions & Tags](https://github.com/windingwind/zotero-actions-tags) plugin |
| Auto-categorize | Use [Zutilo](https://github.com/wshanks/Zutilo) plugin |

### 🔮 Future Possibilities

Zotero team is working on **Local API write support**:
- [GitHub Issue #1320](https://github.com/zotero/zotero/issues/1320) - Request for write support
- Expected in future Zotero releases (8.x+)

**We'll update zotero-keeper as soon as Zotero supports it!**

---

### 🌟 Local API Exclusive: Execute Saved Searches

| API | Execute Saved Search |
|-----|---------------------|
| Web API (api.zotero.org) | ❌ Can only read search metadata |
| **Local API** | ✅ Can execute and retrieve results! |

**Recommended Saved Searches** (create once, use forever):

| Name | Condition | AI Prompt |
|------|-----------|-----------|
| Missing PDF | Attachment File Type is not PDF | "Which papers have no PDF?" |
| Missing DOI | DOI is empty | "Which items lack DOI?" |
| Recent | Date Added in last 7 days | "What did I add this week?" |
| Unread | Tag is not "read" | "What haven't I read?" |
| Duplicates | Similar titles | "Potential duplicate items?" |

---

## 🚧 Future: One-Click Installation

We understand that **most users are researchers, not developers**. Installing Python, uv, and configuring MCP can be daunting.

### 🎯 Planned Improvements

| Current (v1.x) | Future (v2.x) |
|----------------|---------------|
| Requires Python 3.12+ | Standalone executable (.exe / .app) |
| Requires `uv pip install` | One-click installer |
| Manual `mcp.json` config | Auto-configure VS Code/Claude |
| Developer-friendly | Researcher-friendly |

### 📦 Planned Distribution Methods

1. **PyPI Package**: `uv pip install zotero-keeper-mcp` (simplified)
2. **Standalone Executable**: PyInstaller bundle (no Python needed)
3. **VS Code Extension**: One-click install from Marketplace (planned)
4. **Homebrew/Chocolatey**: Package manager support

> 💡 **Want to help?** We welcome contributions to simplify installation!
> See [CONTRIBUTING.md](CONTRIBUTING.md) for how to help.

---

## 🤔 Troubleshooting

### Can't connect to Zotero?

1. Make sure Zotero is running
2. Test: `curl http://127.0.0.1:23119/connector/ping`
3. Should return: `Zotero is running`

### MCP Server not found?

1. Use absolute paths
2. Check Python environment
3. Restart VS Code / Claude Desktop

### PubMed features missing?

```bash
uv pip install -e ".[pubmed]"
```

---

## 📚 Resources

- [CHANGELOG](CHANGELOG.md) - Release notes
- [ARCHITECTURE](ARCHITECTURE.md) - Technical architecture
- [CONTRIBUTING](CONTRIBUTING.md) - How to contribute
- [ROADMAP](ROADMAP.md) - Development roadmap
- [pubmed-search-mcp](https://github.com/u9401066/pubmed-search-mcp) - PubMed search (Apache 2.0)

---

## 🤝 Contributing

Contributions welcome! See [CONTRIBUTING.md](CONTRIBUTING.md).

- 🐛 [Report Bugs](https://github.com/u9401066/zotero-keeper/issues)
- 💡 [Request Features](https://github.com/u9401066/zotero-keeper/issues)
- 🔧 [Submit PRs](https://github.com/u9401066/zotero-keeper/pulls)

---

## 📄 License

Apache 2.0 - See [LICENSE](LICENSE)

---

<p align="center">
  Made with ❤️ for researchers<br>
  Let AI manage your references, focus on your research!
</p>
