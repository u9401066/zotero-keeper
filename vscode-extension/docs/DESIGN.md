# VS Code Extension for Zotero + PubMed MCP Servers

> Current installer contract (v0.6.0, 2026-08-11): the VSIX uses `UvPythonManager` to download `uv`, create an isolated Python 3.12 venv in VS Code global storage, and install pinned GitHub archive sources for Zotero Keeper 2.0.0 and PubMed Search MCP 0.6.1 (`ad85dde`). Both servers require MCP SDK 2.x and its `MCPServer` API; SDK 1.x is incompatible. Older phase sketches below remain as historical design context and are not the active install contract.

## 🎯 目標

建立一個 VS Code Extension，讓使用者可以一鍵安裝並使用 Zotero Keeper + PubMed Search MCP servers。

## 📦 架構設計

```
vscode-zotero-mcp/
├── package.json          # Extension manifest
├── src/
│   ├── extension.ts      # Main entry point
│   └── pythonSetup.ts    # Python env management
├── bundled/              # Pre-bundled Python packages (wheel files)
│   ├── zotero_keeper/
│   └── pubmed_search/
├── scripts/
│   └── install.py        # Python installation script
└── README.md
```

## 🔧 核心功能

### 1. McpServerDefinitionProvider

使用 VS Code 1.99+ 的新 API 來動態註冊 MCP servers：

```typescript
import * as vscode from 'vscode';

class ZoteroMcpProvider implements vscode.McpServerDefinitionProvider<vscode.McpStdioServerDefinition> {

    provideMcpServerDefinitions(): vscode.McpStdioServerDefinition[] {
        const pythonPath = this.getPythonPath();

        return [
            // Zotero Keeper MCP Server
            new vscode.McpStdioServerDefinition(
                'Zotero Keeper',
                pythonPath,
                ['-m', 'zotero_mcp'],
                { ZOTERO_HOST: 'localhost', ZOTERO_PORT: '23119' },
                '2.0.0'
            ),
            // PubMed Search MCP Server
            new vscode.McpStdioServerDefinition(
                'PubMed Search',
                pythonPath,
                ['-m', 'pubmed_search.presentation.mcp_server'],
                { NCBI_EMAIL: 'user@example.com' },
                '0.6.1'
            ),
        ];
    }
}
```

### 2. Python 環境管理

三種策略（按優先順序）：

1. **使用者指定的 Python** - 設定中 `zoteroMcp.pythonPath`
2. **自動偵測系統 Python** - `python3` 或 `python`
3. **Extension 內建虛擬環境** - 在 extension 的 global storage 建立 venv

### 3. 自動安裝依賴

```typescript
async function ensureDependencies(): Promise<void> {
    // 1. Check if packages are installed
    const hasZotero = await checkPackage('zotero-keeper');
    const hasPubmed = await checkPackage('pubmed-search-mcp');

    if (!hasZotero || !hasPubmed) {
        // 2. Ask user permission
        const choice = await vscode.window.showInformationMessage(
            'Zotero MCP requires Python packages. Install now?',
            'Yes', 'No'
        );

        if (choice === 'Yes') {
            // 3. Install via uv into an extension-managed venv, never system site-packages
            await pythonEnv.installPackages();
        }
    }
}
```

## ⚙️ Extension Settings

```json
{
    "zoteroMcp.pythonPath": {
        "type": "string",
        "default": "",
        "description": "Path to Python interpreter. Leave empty for auto-detect."
    },
    "zoteroMcp.zoteroHost": {
        "type": "string",
        "default": "localhost",
        "description": "Zotero host address"
    },
    "zoteroMcp.zoteroPort": {
        "type": "number",
        "default": 23119,
        "description": "Zotero port number"
    },
    "zoteroMcp.ncbiEmail": {
        "type": "string",
        "default": "",
        "description": "Email for NCBI API (required for PubMed search)"
    }
}
```

## 🚀 使用者體驗

### 安裝流程

1. 使用者在 VS Code Marketplace 搜尋 "Zotero MCP"
2. 點擊安裝
3. Extension 自動偵測 Python 環境
4. 提示安裝 Python packages（一次性）
5. MCP servers 自動出現在 Copilot 的 tools 列表中

### 首次啟動

```
┌──────────────────────────────────────────────────────┐
│  🔬 Zotero MCP Extension                             │
│                                                      │
│  Setting up your research assistant...               │
│                                                      │
│  ✓ Python 3.12 environment ready                    │
│  ⏳ Installing packages...                          │
│    - zotero-keeper 2.0.0                            │
│    - pubmed-search-mcp 0.6.1 @ ad85dde              │
│  ✓ MCP servers registered                           │
│                                                      │
│  Ready! Try asking Copilot:                          │
│  "Search PubMed for remimazolam sedation"           │
└──────────────────────────────────────────────────────┘
```

## 📋 package.json 重點

```json
{
    "name": "vscode-zotero-mcp",
    "displayName": "Zotero + PubMed MCP",
    "description": "AI-powered research assistant for Zotero and PubMed",
    "version": "0.1.0",
    "engines": {
        "vscode": "^1.99.0"
    },
    "categories": ["AI", "Chat"],
    "activationEvents": [],
    "main": "./out/extension.js",
    "contributes": {
        "mcpServerDefinitionProviders": [
            {
                "id": "zotero-mcp.servers",
                "label": "Zotero + PubMed Research Tools"
            }
        ],
        "configuration": {
            "title": "Zotero MCP",
            "properties": {
                "zoteroMcp.pythonPath": {...},
                "zoteroMcp.zoteroHost": {...},
                "zoteroMcp.zoteroPort": {...},
                "zoteroMcp.ncbiEmail": {...}
            }
        },
        "commands": [
            {
                "command": "zoteroMcp.checkConnection",
                "title": "Check Zotero Connection"
            },
            {
                "command": "zoteroMcp.reinstallPackages",
                "title": "Reinstall Python Packages"
            }
        ]
    }
}
```

## 🔒 安全考量

1. **Python 路徑驗證** - 只允許執行已知的 Python interpreter
2. **Package 來源** - 擴充套件安裝固定的 GitHub archive commit/tag，不漂移追蹤 branch tip
3. **環境隔離** - 一律使用 extension-managed venv，避免污染系統 Python
4. **Zotero loopback 邊界** - 未認證的 Local/Connector API 只能在 loopback 使用，不得直接對外暴露
5. **Package namespace** - 不在共用 venv 安裝其他名為 `zotero_mcp` 的社群 server；如需並用，必須拆分環境與 process
6. **Collection fail-closed** - `interactive_save` 只接受精確 collection key 或明確的 `ROOT`，且 `ROOT` 會再確認一次；`skip_collection_prompt=True` 會中止。`quick_save` / `import_articles` / `import_pdf` 無 collection 時拒絕，除非使用者已確認且 caller 傳入 `allow_library_root=true`

## 📊 相依性

### VS Code
- 最低版本: 1.99.0 (for `McpServerDefinitionProvider` API)

### Python
- 最低版本: 3.12
- Required packages:
    - Extension-managed Zotero Keeper `2.0.0`
    - Extension-managed PubMed Search MCP `0.6.1` at commit `ad85dde`
    - `mcp>=2.0,<3`

The managed PubMed server exposes 45 tools in 16 categories. Its Research Chronicle surface consists of `build_research_chronicle` and `read_research_chronicle`, replacing the earlier three timeline tools. Zotero Keeper exposes 24 default tools and six concrete resources.

### External
- Zotero 7, 8, or 9 (running locally with API enabled)

## 🗓️ 開發計劃

### Phase 1: MVP (v0.1.0)
- [x] Design document
- [ ] Basic extension structure
- [ ] McpServerDefinitionProvider implementation
- [ ] Python detection and package installation
- [ ] Basic settings

### Phase 2: Polish (v0.2.0)
- [ ] Connection status indicator
- [ ] Better error messages
- [ ] Walkthrough / Getting started guide
- [ ] Pre-bundled wheel files (offline install)

### Phase 3: Advanced (v0.3.0)
- [ ] Collection browser webview
- [ ] Quick pick for recent references
- [ ] Inline citation insertion
