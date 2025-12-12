# Zotero Keeper 📚

A MCP Server for managing local Zotero libraries via AI Agents. Enables Copilot Agent and other AI assistants to read, search, and write bibliographic references to Zotero.

MCP 伺服器：讓 AI Agent (Copilot Agent 等) 管理本地 Zotero 書目資料庫。

[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![MCP SDK](https://img.shields.io/badge/MCP-FastMCP-green.svg)](https://github.com/modelcontextprotocol/python-sdk)
[![License](https://img.shields.io/badge/license-Apache%202.0-blue.svg)](LICENSE)
[![Zotero 7](https://img.shields.io/badge/Zotero-7.0+-red.svg)](https://www.zotero.org/)
[![CI](https://github.com/u9401066/zotero-keeper/actions/workflows/ci.yml/badge.svg)](https://github.com/u9401066/zotero-keeper/actions/workflows/ci.yml)
[![PRs Welcome](https://img.shields.io/badge/PRs-welcome-brightgreen.svg)](CONTRIBUTING.md)
[![GitHub issues](https://img.shields.io/github/issues/u9401066/zotero-keeper)](https://github.com/u9401066/zotero-keeper/issues)


> 🎉 **Contributions Welcome!** See [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines.

---

## 📖 Table of Contents | 目錄

- [Features | 特色功能](#-features--特色功能)
- [Architecture | 架構](#-architecture--架構)
- [Quick Start | 快速開始](#-quick-start--快速開始)
- [Available Tools | 可用工具](#-available-tools--可用工具)
- [Network Setup | 網路設定](#-network-setup--網路設定)
- [Development | 開發指南](#-development--開發指南)
- [Roadmap | 路線圖](#-roadmap--路線圖)
- [References | 參考資料](#-references--參考資料)

---

## 🎯 Features | 特色功能

### English

- **🔌 MCP Native Integration**: Built with FastMCP SDK for seamless AI Agent integration
- **📖 Read Operations**: Search, list, and retrieve bibliographic items from local Zotero
- **✏️ Write Operations**: Add new references to Zotero via Connector API
- **🧠 Smart Features**: Duplicate detection, reference validation, intelligent import
- **🏗️ DDD Architecture**: Clean Domain-Driven Design with onion architecture
- **🔒 No Cloud Required**: All operations are local, no Zotero account needed

### 中文

- **🔌 MCP 原生整合**：使用 FastMCP SDK，與 AI Agent 無縫整合
- **📖 讀取操作**：搜尋、列出、取得本地 Zotero 書目資料
- **✏️ 寫入操作**：透過 Connector API 將新參考文獻加入 Zotero
- **🧠 智慧功能**：重複偵測、參考文獻驗證、智能匯入
- **🏗️ DDD 架構**：乾淨的領域驅動設計，洋蔥式架構
- **🔒 無需雲端**：所有操作都在本地，無需 Zotero 帳號

---

## 🏗️ Architecture | 架構

```
┌─────────────────────────────────────────────────────────────────┐
│                      AI Agent Layer                             │
│         (VS Code Copilot / Claude Desktop / Other)              │
└──────────────────────────┬──────────────────────────────────────┘
                           │ MCP Protocol
                           ▼
┌─────────────────────────────────────────────────────────────────┐
│                    Zotero Keeper MCP Server                     │
│  ┌─────────────────────────────────────────────────────────┐    │
│  │  Infrastructure Layer (FastMCP)                          │    │
│  │  ├── MCP Tools (search, read, write)                     │    │
│  │  └── ZoteroClient (HTTP Client)                          │    │
│  └─────────────────────────────────────────────────────────┘    │
│  ┌─────────────────────────────────────────────────────────┐    │
│  │  Application Layer                                       │    │
│  │  └── Use Cases (SearchItems, AddReference, etc.)         │    │
│  └─────────────────────────────────────────────────────────┘    │
│  ┌─────────────────────────────────────────────────────────┐    │
│  │  Domain Layer                                            │    │
│  │  └── Entities (Item, Collection, Creator, Tag)           │    │
│  └─────────────────────────────────────────────────────────┘    │
└──────────────────────────┬──────────────────────────────────────┘
                           │ HTTP (port 23119)
                           ▼
┌─────────────────────────────────────────────────────────────────┐
│                    Zotero Desktop Client                        │
│  ┌─────────────────────────────────────────────────────────┐    │
│  │  Built-in HTTP Server (127.0.0.1:23119)                  │    │
│  │  ├── Local API (/api/...) - READ operations              │    │
│  │  └── Connector API (/connector/...) - WRITE operations   │    │
│  └─────────────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────────────┘
```

### Key Design Decisions | 關鍵設計決策

| Decision | Rationale | 決策理由 |
|----------|-----------|----------|
| **DDD Onion** | Domain logic isolated from infrastructure | 領域邏輯與基礎設施隔離 |
| **FastMCP** | Native Python MCP SDK, simple decorator-based API | 原生 Python MCP SDK，簡潔裝飾器 API |
| **Built-in API** | Use Zotero 7's native HTTP server, no plugin needed | 使用 Zotero 7 內建 API，無需自製插件 |
| **Dual API** | Local API for read, Connector API for write | 讀取用 Local API，寫入用 Connector API |

---

## 🚀 Quick Start | 快速開始

### Prerequisites | 前置需求

- Python 3.11+
- Zotero 7.0+ (running on local or network machine)
- pip or uv package manager

### Installation | 安裝

```bash
# Clone the repository | 複製專案
git clone https://github.com/u9401066/zotero-keeper.git
cd zotero-keeper/mcp-server

# Create virtual environment | 建立虛擬環境
python -m venv .venv
source .venv/bin/activate  # Linux/Mac
# or: .venv\Scripts\activate  # Windows

# Install dependencies | 安裝依賴
pip install -e .
# or with uv:
uv pip install -e .
```

### Run MCP Server | 執行 MCP 伺服器

```bash
# Start MCP server (stdio transport)
python -m zotero_mcp

# Or with MCP development inspector
pip install "mcp[cli]"
mcp dev src/zotero_mcp/main.py
```

### Configure with VS Code Copilot | 與 VS Code Copilot 整合

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
        "python",
        "-m",
        "zotero_mcp"
      ],
      "env": {
        "ZOTERO_HOST": "localhost",
        "ZOTERO_PORT": "23119"
      }
    },
    "pubmed-search": {
      "type": "stdio",
      "command": "uvx",
      "args": ["--with", "mcp>=1.0.0", "pubmed-search-mcp"],
      "env": {
        "NCBI_EMAIL": "your-email@example.com"
      }
    }
  }
}
```

> 📝 **Note**: Change `ZOTERO_HOST` to your Zotero machine's IP if running remotely.
> See `.env.example` for configuration reference.
> 
> 💡 **Tip**: Use absolute path for `--directory` and ensure [uv](https://docs.astral.sh/uv/) is installed.

### Configure with Claude Desktop | 與 Claude Desktop 整合

Add to `claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "zotero-keeper": {
      "command": "python",
      "args": ["-m", "zotero_mcp"],
      "cwd": "/path/to/zotero-keeper/mcp-server",
      "env": {
        "ZOTERO_HOST": "localhost",
        "ZOTERO_PORT": "23119"
      }
    }
  }
}
```

---

## 🔧 Available Tools | 可用工具

### 📖 Read Tools | 讀取工具

| Tool | Description | 說明 |
|------|-------------|------|
| `search_items(query)` | Search items by title/creator/year | 搜尋文獻（標題/作者/年份） |
| `get_item(key)` | Get item details by key | 取得文獻詳細資料 |
| `list_items(limit)` | List recent items | 列出最近文獻 |
| `list_collections()` | List all collections | 列出所有收藏夾 |
| `list_tags()` | List all tags | 列出所有標籤 |
| `get_item_types()` | Get available item types | 取得可用文獻類型 |

### ✏️ Write Tools | 寫入工具

| Tool | Description | 說明 |
|------|-------------|------|
| `add_reference(...)` | Add a new bibliographic reference | 新增書目參考文獻 |
| `create_item(type, title, ...)` | Create item with full metadata | 建立完整元資料的文獻 |

### 📥 Import Tools | 匯入工具

| Tool | Description | 說明 |
|------|-------------|------|
| `import_ris_to_zotero(ris_text)` | Import RIS format citations | 匯入 RIS 格式引用文獻 |
| `import_from_pmids(pmids)` | Import by PubMed IDs (requires pubmed extra) | 直接用 PMID 匯入 |

### 🧠 Smart Tools | 智慧工具

| Tool | Description | 說明 |
|------|-------------|------|
| `check_duplicate(title, doi)` | Check if reference already exists | 檢查是否已有重複文獻 |
| `validate_reference(...)` | Validate reference metadata | 驗證參考文獻元資料 |
| `smart_add_reference(...)` | Validate + check duplicate + add | 驗證 + 檢查重複 + 新增 |

### 🔍 Integrated Search | 整合搜尋

| Tool | Description | 說明 |
|------|-------------|------|
| `search_pubmed_exclude_owned` | Search PubMed, filter out owned articles | 搜尋 PubMed，排除已有文獻 |
| `check_articles_owned` | Check which PMIDs are already in Zotero | 檢查哪些 PMID 已存在 |

> ⚠️ **Note**: Integrated search requires both `pubmed-search-mcp` and `zotero-keeper[pubmed]` installed.

---

## 🔬 PubMed Integration | PubMed 整合

Zotero Keeper works seamlessly with [pubmed-search-mcp](https://github.com/u9401066/pubmed-search-mcp) for literature discovery and import.

### 🆕 Integrated Search (v1.6.0+) | 整合搜尋

When both MCPs are installed, use **integrated search** to find NEW papers not in your library:

```
┌────────────────────────────────────────────────────────────────┐
│                    zotero-keeper (v1.6.0+)                     │
│  search_pubmed_exclude_owned("CRISPR")                         │
│      ├── PubMed Search (via pubmed-search-mcp)                 │
│      ├── Filter against Zotero library                         │
│      └── Return only NEW articles 🆕                           │
└────────────────────────────────────────────────────────────────┘
```

**Simple Workflow (Recommended):**
```
1. [keeper] search_pubmed_exclude_owned("CRISPR", limit=10) → NEW papers only
2. [keeper] import_from_pmids(new_pmids, tags=["CRISPR"]) → Zotero
```

### Advanced Workflow | 進階工作流程

For complex searches, use pubmed-search-mcp's strategy tools first:

```
┌────────────────────────┐    ┌────────────────────────┐
│   pubmed-search-mcp    │    │     zotero-keeper      │
│   (Strategy Building)  │    │   (Search & Import)    │
│                        │    │                        │
│  • generate_search_    │    │  • search_pubmed_      │
│    queries (MeSH)      │───▶│    exclude_owned       │
│  • parse_pico          │    │  • import_from_pmids   │
│  • prepare_export      │    │  • smart_add_reference │
└────────────────────────┘    └────────────────────────┘
```

**Example:**
```
1. [pubmed] generate_search_queries("CRISPR gene therapy") → MeSH terms
2. [keeper] search_pubmed_exclude_owned(query='"CRISPR-Cas Systems"[MeSH]') → NEW only
3. [keeper] import_from_pmids(pmids, tags=["CRISPR"]) → Zotero
```

### Configuration | 設定

```json
// claude_desktop_config.json - Run both MCPs
{
  "mcpServers": {
    "pubmed-search": {
      "command": "uvx",
      "args": ["pubmed-search-mcp"]
    },
    "zotero-keeper": {
      "command": "python",
      "args": ["-m", "zotero_mcp"],
      "cwd": "/path/to/zotero-keeper/mcp-server"
    }
  }
}
```

---

## 🌐 Network Setup | 網路設定

### Scenario | 情境

```
┌──────────────┐           ┌──────────────┐
│  MCP Server  │  ──────▶  │   Zotero     │
│  (Linux VM)  │   HTTP    │  (Windows)   │
│  <MCP_HOST>  │  :23119   │ <ZOTERO_HOST>│
└──────────────┘           └──────────────┘
```

### Zotero Configuration (Windows) | Zotero 設定 (Windows)

**1. Enable Local API (Run JavaScript in Zotero):**
```javascript
Zotero.Prefs.set("httpServer.localAPI.enabled", true)
```

**2. Add Firewall Rule:**
```powershell
netsh advfirewall firewall add rule name="Zotero HTTP Server" dir=in action=allow protocol=TCP localport=23119
```

**3. Setup Port Proxy (Required - Zotero binds to 127.0.0.1 only):**
```powershell
netsh interface portproxy add v4tov4 listenaddress=0.0.0.0 listenport=23119 connectaddress=127.0.0.1 connectport=23119
```

### Connection Test | 連線測試

```bash
# Test from remote machine (requires Host header due to port proxy)
# Replace <ZOTERO_HOST> with your Zotero machine's IP
curl -s -H "Host: 127.0.0.1:23119" "http://<ZOTERO_HOST>:23119/connector/ping"
# Expected: <!DOCTYPE html><html><body>Zotero is running</body></html>

curl -s -H "Host: 127.0.0.1:23119" "http://<ZOTERO_HOST>:23119/api/users/0/items?limit=5"
# Expected: JSON array of items
```

---

## 👨‍💻 Development | 開發指南

### Project Structure | 專案結構

```
zotero-keeper/
├── README.md
├── CHANGELOG.md
├── ARCHITECTURE.md
├── ROADMAP.md
├── LICENSE
├── mcp-server/
│   ├── pyproject.toml
│   ├── src/
│   │   └── zotero_mcp/
│   │       ├── __init__.py
│   │       ├── main.py              # Entry point
│   │       ├── domain/              # Domain Layer
│   │       │   ├── entities/        # Item, Collection, Creator
│   │       │   └── repositories/    # Repository interfaces
│   │       ├── application/         # Application Layer
│   │       │   └── use_cases/       # Business logic
│   │       └── infrastructure/      # Infrastructure Layer
│   │           ├── mcp/             # MCP Server & Tools
│   │           └── zotero_client/   # HTTP Client
│   └── tests/
└── docs/
    └── memory-bank/                 # Development context
```

### Testing | 測試

```bash
# Run tests
pytest

# Run with coverage
pytest --cov=zotero_mcp

# Run specific test
pytest tests/test_client.py -v
```

### Code Quality | 程式碼品質

```bash
# Lint
ruff check src/

# Type check
mypy src/
```

---

## 🗺️ Roadmap | 路線圖

See [ROADMAP.md](ROADMAP.md) for detailed roadmap.

| Phase | Status | Description |
|-------|--------|-------------|
| **Phase 1** | ✅ Done | Network connectivity, API discovery |
| **Phase 2** | 🔄 In Progress | MCP Tools implementation (read/write) |
| **Phase 3** | 📋 Planned | Smart features (duplicate detection, validation) |
| **Phase 4** | 📋 Planned | Multi-user support, configuration |
| **Phase 5** | 📋 Planned | Enrichment (DOI lookup, metadata completion) |

---

## 📚 References | 參考資料

### APIs & Protocols

- [Zotero Web API v3](https://www.zotero.org/support/dev/web_api/v3/basics)
- [Zotero Local API Source](https://github.com/zotero/zotero/blob/main/chrome/content/zotero/xpcom/server/server_localAPI.js)
- [Model Context Protocol](https://modelcontextprotocol.io/)
- [FastMCP Python SDK](https://github.com/jlowin/fastmcp)

### Similar Projects

- [stevenyuyy/zotero-mcp](https://stevenyuyy.us/zotero-mcp/) - Official Zotero MCP documentation
- [54yyyu/zotero-mcp](https://github.com/54yyyu/zotero-mcp) - Read-only MCP server
- [kujenga/zotero-mcp](https://github.com/kujenga/zotero-mcp) - Local API based

### Design References

- [medical-calc-mcp](https://github.com/u9401066/medical-calc-mcp) - DDD architecture reference

---

## 🤝 Contributing | 貢獻

We welcome contributions! Please see our:

- [CONTRIBUTING.md](CONTRIBUTING.md) - Contribution guidelines
- [SECURITY.md](SECURITY.md) - Security policy
- [ROADMAP.md](ROADMAP.md) - Project roadmap

**Ways to contribute:**
- 🐛 Report bugs
- 💡 Suggest features
- 📖 Improve documentation
- 🔧 Submit pull requests

---

## 📄 License

Apache 2.0 - See [LICENSE](LICENSE)

---

## 🙏 Acknowledgments | 致謝

- [Zotero](https://www.zotero.org/) - The amazing open-source reference manager
- [Model Context Protocol](https://modelcontextprotocol.io/) - Anthropic's open protocol for AI-tool communication
- [FastMCP](https://github.com/jlowin/fastmcp) - Python SDK for MCP

---

<p align="center">
  Made with ❤️ for the research community
  <br>
  <a href="https://github.com/u9401066/zotero-keeper/issues">Report Bug</a>
  ·
  <a href="https://github.com/u9401066/zotero-keeper/issues">Request Feature</a>
  ·
  <a href="CONTRIBUTING.md">Contribute</a>
</p>
