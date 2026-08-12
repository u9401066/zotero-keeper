# Zotero Keeper 📚

Let AI manage your references! A MCP Server connecting VS Code Copilot / Claude Desktop to your local Zotero library.

[![Python 3.12+](https://img.shields.io/badge/python-3.12+-blue.svg)](https://www.python.org/downloads/)
[![MCP SDK](https://img.shields.io/badge/MCP%20SDK-v2-green.svg)](https://github.com/modelcontextprotocol/python-sdk)
[![License](https://img.shields.io/badge/license-Apache%202.0-blue.svg)](LICENSE)
[![Zotero 7/8/9/10+](https://img.shields.io/badge/Zotero-7%20%2F%208%20%2F%209%20%2F%2010%2B-red.svg)](https://www.zotero.org/)
[![CI](https://github.com/u9401066/zotero-keeper/actions/workflows/ci.yml/badge.svg)](https://github.com/u9401066/zotero-keeper/actions/workflows/ci.yml)
[![PRs Welcome](https://img.shields.io/badge/PRs-welcome-brightgreen.svg)](CONTRIBUTING.md)

> 🌐 **English** | **[繁體中文](README.zh-TW.md)**

---

## 🚀 Recommended Install (VS Code)

> **Prerequisites**: [Zotero 7, 8, 9, or 10+](https://www.zotero.org/download/) must be running. Zotero 10+ is required for authorized Local API writes.

[📦 Install Zotero + PubMed MCP from the VS Code Marketplace](https://marketplace.visualstudio.com/items?itemName=u9401066.vscode-zotero-mcp)

The **v0.7.0 VSIX is the recommended distribution**. It creates an isolated environment and installs Zotero Keeper 2.1.0 plus the pinned PubMed Search MCP 0.6.1 snapshot. The `uvx`/PyPI path remains available for older direct-server installs, but it must not be treated as the 2.1 release until PyPI is updated.

> ⚠️ MCP SDK 2.0 is not compatible with 1.x. After upgrading the extension, run **Zotero MCP: Reinstall Python Environment** if VS Code still has an older managed environment.

---

## ✨ What is this?

**Zotero Keeper** is a [MCP Server](https://modelcontextprotocol.io/) that lets your AI assistant:

- 🔍 **Search references**: "Find papers about CRISPR from 2024"
- 📖 **View details**: "What's the abstract of this article?"
- ➕ **Add references**: "Add this DOI to my Zotero" (with auto-fetch metadata!)
- 🔄 **PubMed integration**: "Search PubMed, skip what I already have"
- 📁 **Interactive save**: Shows collection options for you to choose!
- 🗂️ **Zotero 10+ organization**: Create nested collections, update existing records, add notes, and attach files to records already in your library
- 📚 **Modern literature discovery**: PubMed Search MCP 0.6.1 exposes 45 tools in 16 categories, including the two-tool Research Chronicle workflow

No more manually searching, copying, pasting. Just tell your AI in natural language!

---

## ✨ Features

- **🔌 MCP SDK 2.0 native**: Built on the v2 `MCPServer` API (not the incompatible 1.x `FastMCP` surface)
- **📖 MCP Resources**: Browse Zotero data via URIs (`zotero://collections`, etc.)
- **💬 MCP Elicitation**: Interactive collection selection using an exact collection key; `ROOT` always requires a second confirmation
- **🔒 Auto-fetch Metadata**: DOI/PMID → complete abstract + all fields automatically!
- **📊 Citation Metrics**: RCR and NIH Percentile stored in Zotero extra fields
- **🛡️ Collection Validation**: Use `collection_name` for safer auto-validation
- **📖 Read Operations**: Search, list, and retrieve items from local Zotero
- **✏️ Write Operations**: Keep Connector imports for Zotero 7–9; use runtime-authorized Local API writes on Zotero 10+
- **🧠 Smart Features**: Duplicate detection, validation, intelligent import
- **📁 Collection Support**: Nested collections (folders) with hierarchy
- **🏗️ Clean Architecture**: DDD with onion architecture
- **🔒 Local Zotero boundary**: Zotero library operations stay on the local
  loopback API; PubMed discovery uses the configured external literature APIs

---

## 🚀 Quick Start

### Prerequisites

- ✅ [Python 3.12+](https://www.python.org/downloads/)
- ✅ [Zotero 7, 8, 9, or 10+](https://www.zotero.org/download/) (must be running; 10+ for Local API writes)
- ✅ [VS Code](https://code.visualstudio.com/) + GitHub Copilot, or [Claude Desktop](https://claude.ai/)
- ✅ [uv](https://docs.astral.sh/uv/getting-started/installation/) (recommended)

### Installation

```bash
# Clone the repository
git clone https://github.com/u9401066/zotero-keeper.git
cd zotero-keeper/mcp-server

# Install with uv (required)
uv sync --extra all

# Test (make sure Zotero is running)
uv run python -m zotero_mcp
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
      "command": "uv",
      "args": ["run", "python", "-m", "zotero_mcp"],
      "cwd": "/path/to/zotero-keeper/mcp-server"
    }
  }
}
```

> 💡 Use absolute paths and ensure [uv](https://docs.astral.sh/uv/) is installed.

### Common Environment Variables

If you run the server directly, these are the main settings you may want to provide via `.env` or your MCP launcher configuration:

```bash
ZOTERO_HOST=localhost
ZOTERO_PORT=23119
ZOTERO_TIMEOUT=30
NCBI_EMAIL=your.email@example.com
# NCBI_API_KEY=your_api_key_here
# ZOTERO_KEEPER_ENABLE_LEGACY_PUBMED_TOOLS=1
# PUBMED_SEARCH_PATH=/path/to/pubmed-search-mcp
```

- Use `NCBI_EMAIL` and optional `NCBI_API_KEY` for higher NCBI/PubMed rate limits.
- Use `ZOTERO_KEEPER_ENABLE_LEGACY_PUBMED_TOOLS=1` only if you intentionally want keeper's older PubMed bridge/import tools.
- Use `PUBMED_SEARCH_PATH` only during local development when you want keeper to import a checked-out `pubmed-search-mcp` tree instead of the installed package.

---

## 📚 Documentation Map

- [README.zh-TW.md](README.zh-TW.md) — Traditional Chinese overview
- [mcp-server/README.md](mcp-server/README.md) — focused server usage and tool reference
- [vscode-extension/README.md](vscode-extension/README.md) — VS Code extension setup and UX
- [docs/COLLABORATION_WORKFLOW.md](docs/COLLABORATION_WORKFLOW.md) — collaboration-safe flow between pubmed-search-mcp and keeper
- [docs/tools-reference.md](docs/tools-reference.md) — parameter reference and examples for public tools
- [docs/faq.md](docs/faq.md) — installation, troubleshooting, and workflow FAQ
- [docs/ZOTERO_LOCAL_API.md](docs/ZOTERO_LOCAL_API.md) — Zotero API capability notes and limitations
- [docs/ZOTERO_MCP_LANDSCAPE.md](docs/ZOTERO_MCP_LANDSCAPE.md) — what is official, what is community-maintained, and safe coexistence guidance
- [ARCHITECTURE.md](ARCHITECTURE.md) — component and layering overview
- [CONTRIBUTING.md](CONTRIBUTING.md) — development workflow and contribution guide

---

## 🔧 Available Tools (32 default public + 5 legacy opt-in)

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

### 🗂️ Zotero 10+ Local API Tools (local_api_tools.py - 8 tools)

These tools use Zotero's official Local API v3 write support. Before preview,
obtain a response-bound `server_id` from a Local API read or
`authorize_local_writes`, and include it as `expected_server_id`. The key stays
inside the Keeper process; all writes are restricted to loopback and bound to
the reviewed Zotero Server-ID.

| Tool | Description | Safety boundary |
|------|-------------|-----------------|
| `authorize_local_writes` | Ask Zotero to authorize Keeper; use `require_remembered=true` before file upload | Never returns or logs the key |
| `create_collection` | Create a top-level or nested collection | Exact parent key + explicit confirmation |
| `add_items_to_collection` | Add up to 50 existing items without removing other memberships | Validates every key before one versioned batch write |
| `update_item_fields` | Update approved scalar metadata fields | Requires the current local object version |
| `create_note` | Add a child note to an existing item | Validates the parent + explicit confirmation |
| `create_saved_search` | Create a Zotero saved search | Structured conditions + explicit confirmation |
| `attach_file_to_item` | Attach a local file to an existing item | Remembered authorization + validated loopback upload URL |
| `set_attachment_fulltext` | Write indexed text for an attachment | Response-bound library cursor + Server-ID + explicit confirmation |

These operations are unavailable on Zotero 7–9, which retain the existing
Connector import path. Keeper intentionally does not expose an unrestricted raw
PATCH or general-purpose destructive DELETE tool.

For each mutation, put `expected_server_id` (and the response-bound item object
version or full-text library cursor, when applicable) into the `confirm=false`
proposal before asking for approval. If later authorization reports a different
identity, discard that proposal, reread, preview again, and obtain new approval;
never add identity only after preview. Confirmed execution repeats the unchanged
proposal. A 412 is never retried automatically.

### ✏️ Save Tools (interactive_tools.py - 2 tools)

> 📊 **Auto RCR**: When PMID is provided, automatically fetches Relative Citation Ratio from iCite and stores in Zotero's extra field

| Tool | Description | Example |
|------|-------------|--------|
| `interactive_save` ⭐ | Interactive save + auto RCR | "Save this paper to Zotero" |
| `quick_save` | Quick save + auto RCR | "Quick save to AI Research" |

All save paths fail closed when no destination is confirmed. `interactive_save` asks for an exact collection key (or the explicit sentinel `ROOT`); choosing `ROOT` triggers a second confirmation. `skip_collection_prompt=True` aborts instead of silently saving to the library root. `quick_save`, `import_articles`, and `import_pdf` reject a missing collection unless the user has explicitly confirmed root storage and the caller passes `allow_library_root=true`.

### 🔍 Saved Search Tools (saved_search_tools.py - 3 tools)

| Tool | Description | Example |
|------|-------------|---------|
| `list_saved_searches` | List all saved searches | "What saved searches exist?" |
| `run_saved_search` | Execute a saved search | "Which papers have no PDF?" |
| `get_saved_search_details` | Get search conditions | "What's in 'Missing PDF' search?" |

### 🔍 Advanced Search & Ownership Check (search_tools.py - 2 public tools)

| Tool | Description | Example |
|------|-------------|---------|
| `advanced_search` ⭐ | Multi-condition search (itemType, tag, qmode) | "Find all journal articles tagged with AI" |
| `check_articles_owned` | Check if PMIDs exist in Zotero | "Do I have these PMIDs?" |

### 📥 Import Tools (2 tools)

> 🤝 **Collaboration-safe default**: PubMed search/discovery/export lives in pubmed-search-mcp. Zotero Keeper exposes one public import handoff: `import_articles`.

| Tool | Description | Example |
|------|-------------|--------|
| `import_articles` ⭐ | Single public import entry for JSON articles or RIS text | "Import these PubMed results to AI Research" |
| `import_pdf` 📎 | Import a local PDF through Zotero Connector endpoints, with metadata or Zotero recognition | "Import this PDF and attach it to its paper" |

#### Legacy PubMed bridge tools

`search_pubmed_exclude_owned`, `quick_import_pmids`, `import_ris_to_zotero`, `import_from_pmids`, and `batch_import_from_pubmed` are now hidden by default to avoid duplicating pubmed-search-mcp.

If you intentionally want the old standalone keeper behavior, set `ZOTERO_KEEPER_ENABLE_LEGACY_PUBMED_TOOLS=1` before starting the server.

### 📊 Analytics Tools (analytics_tools.py - 2 tools)

| Tool | Description | Example |
|------|-------------|--------|
| `get_library_stats` | Library statistics (year/author/journal) | "Show my library statistics" |
| `find_orphan_items` | Find unorganized items | "Which papers need organizing?" |

### 📎 Attachment & Fulltext Tools (attachment_tools.py - 2 tools)

> 🗂️ **PDF Access**: Zotero 10+ resolves attachment paths through the official Local API. `ZOTERO_DATA_DIR` remains an optional fallback for older Zotero versions or unavailable view URLs.

| Tool | Description | Example |
|------|-------------|--------|
| `get_item_attachments` | List PDFs/snapshots for an item | "What attachments does key:X42A7DEE have?" |
| `get_item_fulltext` | Get Zotero-indexed fulltext content | "Read the full text of key:X42A7DEE" |

#### Recommended PubMed → Zotero workflow

```python
# 1. Search with pubmed-search-mcp
results = unified_search("anesthesia AI", output_format="json")

# 2. Optional: filter against local Zotero
pmids = [
  article.get("identifiers", {}).get("pmid")
  for article in results["articles"]
]
owned = check_articles_owned(pmids=[pmid for pmid in pmids if pmid])

# 3. Import selected records into Zotero
import_articles(
  articles=results["articles"],
  collection_name="AI Research"
)
```

### 🤝 Collaboration-Safe Setup (Summary)

- pubmed-search-mcp runs search/discovery/export; zotero-keeper handles duplicate checks and the single `import_articles` handoff.
- Ensure pubmed-search-mcp is installed or the submodule is present; set `PUBMED_SEARCH_PATH` if you rely on a local checkout.
- Keep legacy PubMed bridge tools disabled unless you set `ZOTERO_KEEPER_ENABLE_LEGACY_PUBMED_TOOLS=1` intentionally.
- Full checklist: see `docs/COLLABORATION_WORKFLOW.md`.

#### advanced_search Examples

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

The SDK v2 server advertises six concrete resources. Four additional parameterized URI templates resolve individual items, collections, collection contents, and saved searches.

### Concrete resources (6)

| Resource URI | Description |
|--------------|-------------|
| `zotero://collections` | All collections |
| `zotero://collections/tree` | Collection hierarchy |
| `zotero://items` | Recent items |
| `zotero://tags` | All tags |
| `zotero://searches` | Saved searches |
| `zotero://schema/item-types` | Available item types |

### Parameterized resource templates (4)

| Resource template | Description |
|-------------------|-------------|
| `zotero://collections/{key}` | Specific collection |
| `zotero://collections/{key}/items` | Items in collection |
| `zotero://items/{key}` | Item details |
| `zotero://searches/{key}` | Saved-search details |

---

## 🎯 Interactive Save (Recommended!)

The `interactive_save` tool uses **MCP Elicitation** to show collection options:

```
User: "Save this DOI:10.1234/example paper to Zotero"

[MCP Elicitation pops up]
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📚 Saving: Deep Learning for Medical Imaging

⭐ Suggested:
   AI Research — key `A1B2C3D4` (match: 90%)
   Medical Imaging — key `M5N6P7Q8` (match: 75%)

📂 All Collections:
   Biology — key `B1O2L3O4` (12 items)
   Chemistry — key `C5H6E7M8` (8 items)
   To Read — key `T1O2R3E4` (23 items)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Enter the exact collection key, or `ROOT`: [User enters: A1B2C3D4]

AI: ✅ Saved to 'AI Research' collection!
```

`ROOT` is not a default shortcut. Selecting it starts a second confirmation before a save can proceed; declining or skipping the prompt aborts the operation.

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

The v0.7.0 VSIX pins [pubmed-search-mcp 0.6.1](https://github.com/u9401066/pubmed-search-mcp/tree/v0.6.1) at commit `ad85dde`. Its MCP SDK v2 server exposes **45 tools across 16 categories**. The new `build_research_chronicle` and `read_research_chronicle` workflow replaces the three earlier timeline tools.

```
You: "Find new anesthesia AI papers from 2024 that I don't have"

AI executes:
1. pubmed-search-mcp: unified_search("anesthesia AI", filters="year:2024-", output_format="json")
  → Found 30 candidate articles

2. zotero-keeper: check_articles_owned([...pmids...])
  → Detects which PMIDs already exist locally

3. zotero-keeper: import_articles(articles=selected_articles, collection_name="AI Research")
  → Imports the selected records into Zotero

You: Done! 25 new papers in Zotero
```

### Install PubMed Integration

```bash
cd mcp-server
uv sync --extra pubmed
```

### Zotero MCP ecosystem naming

As of 2026-08-12, no Zotero-organization repository or Zotero documentation was found that publishes an official Zotero MCP server. [`54yyyu/zotero-mcp`](https://github.com/54yyyu/zotero-mcp) is a capable **community server listed in the MCP Registry**, not an official Zotero server. An OpenAI-curated Zotero connector is likewise a separate connector product and should not be described as Zotero's official MCP server or assigned an invented tool schema.

The community server and Zotero Keeper both use the Python module/package name `zotero_mcp`. If you run both, install them in **separate virtual environments and separate MCP processes**; do not add the community package to the extension-managed environment. See [the ecosystem comparison](docs/ZOTERO_MCP_LANDSCAPE.md).

---

## 🌐 Remote Zotero Access

Zotero Local API reads and the Connector endpoints are local interfaces;
Zotero 10+ Local API writes add runtime authorization, but the resulting key is
unscoped. Port 23119 must therefore remain on loopback. Do not expose or forward
it to a LAN or the Internet.

For remote libraries, use Zotero's authenticated HTTPS Web API, or place a purpose-built authenticated service in front of Zotero and apply TLS, authorization, and network access controls. Keep Zotero Keeper and Zotero Desktop on the same trusted host when using Local/Connector operations.

---

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────┐
│           AI Agent (VS Code / Claude)           │
└──────────────────────┬──────────────────────────┘
                       │ MCP Protocol
                       │ ├── Tools (32 default)
                       │ ├── Resources (6 + 4 URI templates)
                       │ └── Elicitation (interactive input)
                       ▼
┌─────────────────────────────────────────────────┐
│              Zotero Keeper MCP Server           │
│  ┌───────────────────────────────────────────┐  │
│  │  MCP Layer                                │  │
│  │  ├── server.py + basic reads (6 tools)      │  │
│  │  ├── collection_tools.py (5 tools)         │  │
│  │  ├── local_api_tools.py (8 guarded tools)  │  │
│  │  ├── resources.py (6 resources + 4 templates) │
│  │  ├── interactive_tools.py (2 save tools)   │  │
│  │  ├── saved_search_tools.py (3 tools)      │  │
│  │  ├── search_tools.py (2 default + 1 legacy) │ │
│  │  ├── unified_import_tools.py (2 tools)    │  │
│  │  ├── analytics + attachment tools (4)     │  │
│  │  ├── pubmed/batch legacy modules (4 tools) │ │
│  │  └── smart_tools.py (helpers only)        │  │
│  └───────────────────────────────────────────┘  │
└──────────────────────┬──────────────────────────┘
                       │ HTTP (port 23119)
                       ▼
┌─────────────────────────────────────────────────┐
│              Zotero Desktop Client              │
│  ├── Local API (/api/...) → Read + authorized  │
│  │                              write (10+)    │
│  └── Connector API (/connector/...) → Legacy   │
│                                      create    │
└─────────────────────────────────────────────────┘
```

---

## ⚠️ Zotero API Capabilities and Boundaries

Zotero 10+ changed the Local API substantially. The platform now supports
authorized item, collection, and saved-search writes, tag deletion, full-text
writes, and full file uploads. Keeper 2.1 exposes a deliberately constrained
subset rather than handing an unscoped key and arbitrary API paths to an AI
client.

| Interface | Scope | Authentication | Keeper 2.1 use |
|-----------|-------|----------------|----------------|
| **Local API v3** `/api/...` | Same-machine library reads; Zotero 10+ writes | Reads are unauthenticated; writes require runtime user approval | Reads on Zotero 7–10+; guarded writes on 10+ |
| **Connector API** `/connector/...` | Browser-connector save flows | Local interface | Backward-compatible create/import path, including Zotero 7–9 |
| **Web API v3** `https://api.zotero.org` | Remote and synchronized libraries | zotero.org key/OAuth | Recommended for remote access; not used by the local Keeper tools |

For Zotero 10+ writes, Keeper first obtains a response-bound
`Zotero-Server-ID` from discovery/read or runtime authorization. That identity
must already appear in the `confirm=false` proposal and every confirmed mutation
carries it as `expected_server_id`. `update_item_fields` additionally carries
the object version from the same exact-item response. Full-text replacement uses
the response-bound library cursor and bulk `POST /api/users/0/fulltext` with
`If-Unmodified-Since-Version`, not the attachment object version. If
authorization identifies another database, the read, preview, and approval must
all be repeated. A changed database or stale cursor returns `412` and is never
silently overwritten; missing identity/preconditions (`428`) and invalid
authorization (`401`) also fail closed.

Keeper 2.1 now supports the previously blocked high-value workflows:

- create a top-level or nested collection;
- add existing items to a confirmed collection while preserving all current memberships;
- update approved metadata on an existing item and create child notes;
- create saved searches;
- attach a local file to an existing item with Zotero's three-phase upload;
- provide indexed text for an attachment; and
- obtain attachment paths through the official Local API instead of guessing the Zotero data directory.

General deletion, arbitrary raw PATCH, duplicate merging, annotation editing,
and group-library writes are not exposed as public Keeper tools in this release.
Use Zotero's UI for destructive maintenance. See
[docs/ZOTERO_LOCAL_API.md](docs/ZOTERO_LOCAL_API.md) for the complete platform
matrix and Keeper's narrower safety contract.

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

## 📦 Installation & Distribution Paths

We support both developer-oriented and researcher-friendly entry points today, while keeping room for simpler packaging later.

| Path | Status | Best for |
|------|--------|----------|
| VS Code extension | ✅ Available now | Researchers who want guided setup inside VS Code |
| Source checkout + `uv sync` | ✅ Available now | Contributors and local development |
| Direct MCP registration via `uvx zotero-keeper` | ⚠️ Older PyPI line | Existing clients that intentionally accept the pre-2.0 package |
| Standalone executable | 🚧 Planned | Users who do not want to install Python/uv |
| Homebrew / Chocolatey | 🚧 Planned | OS-level package manager workflows |

> 💡 Want to help improve installation? See [CONTRIBUTING.md](CONTRIBUTING.md).

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
cd mcp-server
uv sync --extra pubmed
```

---

## 📚 Resources

- [CHANGELOG](CHANGELOG.md) - Release notes
- [ARCHITECTURE](ARCHITECTURE.md) - Technical architecture
- [CONTRIBUTING](CONTRIBUTING.md) - How to contribute
- [ROADMAP](ROADMAP.md) - Development roadmap
- [docs/tools-reference.md](docs/tools-reference.md) - Full MCP tools parameter reference
- [docs/faq.md](docs/faq.md) - Frequently asked questions
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
