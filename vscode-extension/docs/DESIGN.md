# VS Code Extension for Zotero + PubMed MCP Servers

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
                '1.8.2'
            ),
            // PubMed Search MCP Server
            new vscode.McpStdioServerDefinition(
                'PubMed Search',
                pythonPath,
                ['-m', 'pubmed_search.mcp'],
                { NCBI_EMAIL: 'user@example.com' },
                '0.1.14'
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
            // 3. Install via pip
            await runTerminal(`pip install zotero-keeper[all] pubmed-search-mcp[mcp]`);
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
│  ✓ Python 3.11 detected                             │
│  ⏳ Installing packages...                          │
│    - zotero-keeper 1.8.2                            │
│    - pubmed-search-mcp 0.1.14                       │
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
2. **Package 來源** - 只從 PyPI 安裝官方 packages
3. **環境隔離** - 建議使用虛擬環境避免污染系統

## 📊 相依性

### VS Code
- 最低版本: 1.99.0 (for `McpServerDefinitionProvider` API)

### Python
- 最低版本: 3.11
- Required packages:
  - `zotero-keeper[all]>=1.7.0`
  - `pubmed-search-mcp[mcp]>=0.1.8`

### External
- Zotero 7 (running locally with API enabled)

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
