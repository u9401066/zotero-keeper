# Self-Contained Extension 設計方案

## 🎯 目標

讓非技術使用者（醫師、研究人員）只需：
1. 下載 .vsix
2. 安裝
3. 開始使用

**不需要**：Python、pip、git、終端機操作

---

## 📦 方案比較

### 方案 A: 內嵌 Python (✅ 推薦)

將 portable Python + packages 打包進 extension：

```
vscode-zotero-mcp-standalone.vsix (~80MB)
├── extension/
│   ├── out/              # Extension code
│   ├── python/           # Embedded Python
│   │   ├── python.exe    # Windows
│   │   ├── python3       # Linux/macOS
│   │   └── Lib/site-packages/
│   │       ├── zotero_mcp/
│   │       ├── pubmed_search/
│   │       ├── httpx/
│   │       └── ...
│   └── resources/
```

**優點**：
- 真正一鍵安裝
- 不依賴系統環境
- 保證版本相容

**缺點**：
- 檔案大 (~80-100MB)
- 需要為每個平台打包

### 方案 B: 首次啟動自動下載 Python

Extension 啟動時自動下載 portable Python：

```
首次啟動流程：
1. 檢查 extension storage 是否有 Python
2. 若無，從 GitHub Release 下載 python-embed.zip
3. 解壓縮到 extension storage
4. 安裝 pip packages
5. 就緒
```

**優點**：
- 初始 .vsix 很小 (~30KB)
- 可以更新 Python 版本

**缺點**：
- 首次啟動需要下載
- 需要網路連線

### 方案 C: 使用 PyInstaller 打包成執行檔

將 MCP servers 打包成獨立執行檔：

```
zotero-mcp-server.exe (Windows)
zotero-mcp-server (Linux/macOS)
```

**優點**：
- 單一執行檔
- 不需要 Python

**缺點**：
- 每次更新都要重新打包
- 需要為每個平台打包

---

## 🚀 推薦方案：A + B 混合

### 階段 1: 先用方案 B (自動下載)
- 快速上線
- .vsix 保持小巧
- 首次啟動自動下載 embedded Python

### 階段 2: 提供 standalone 版本
- 為需要離線安裝的使用者提供 
- 包含完整 Python 環境

---

## 📋 實作細節 (方案 B)

### 1. Python Embeddable Package

使用官方 Python embeddable 版本：
- Windows: `python-3.11.x-embed-amd64.zip` (~15MB)
- Linux: 使用 `python-build-standalone` (~25MB)
- macOS: 使用 `python-build-standalone` (~25MB)

下載來源：
- https://www.python.org/ftp/python/ (Windows)
- https://github.com/indygreg/python-build-standalone (Linux/macOS)

### 2. 預先打包的 Wheels

將需要的 packages 打包成 wheel 檔：

```
bundled/
├── wheels/
│   ├── zotero_keeper-1.8.2-py3-none-any.whl
│   ├── pubmed_search_mcp-0.1.14-py3-none-any.whl
│   ├── httpx-0.27.0-py3-none-any.whl
│   ├── mcp-1.0.0-py3-none-any.whl
│   └── ... (所有依賴)
└── requirements.txt
```

### 3. 啟動流程

```typescript
async function ensureEnvironment() {
    const envPath = context.globalStorageUri.fsPath;
    const pythonPath = path.join(envPath, 'python', getPythonBinary());
    
    if (!fs.existsSync(pythonPath)) {
        // Show progress
        await vscode.window.withProgress({
            location: vscode.ProgressLocation.Notification,
            title: "Setting up Zotero MCP (first time only)",
            cancellable: false
        }, async (progress) => {
            // Download Python
            progress.report({ message: "Downloading Python..." });
            await downloadPython(envPath);
            
            // Install packages
            progress.report({ message: "Installing packages..." });
            await installPackages(pythonPath);
            
            progress.report({ message: "Ready!" });
        });
    }
    
    return pythonPath;
}
```

---

## 📁 下載位置

Extension 的 Python 環境存放在 VS Code global storage：

```
Windows: %APPDATA%\Code\User\globalStorage\u9401066.vscode-zotero-mcp\
Linux:   ~/.config/Code/User/globalStorage/u9401066.vscode-zotero-mcp/
macOS:   ~/Library/Application Support/Code/User/globalStorage/u9401066.vscode-zotero-mcp/
```

這樣：
- 不會污染使用者系統
- 卸載 extension 後可以清理
- 多個 VS Code 視窗共用

---

## 🔧 需要準備的資源

1. **Python embeddable packages**
   - Windows amd64
   - Linux x86_64
   - macOS arm64 (Apple Silicon)
   - macOS x86_64 (Intel)

2. **Pre-built wheels**
   - 所有 Python 依賴的 wheel 檔

3. **GitHub Release hosting**
   - 存放下載資源

---

## 📊 檔案大小估算

| 組件 | 大小 |
|------|------|
| Python embeddable | ~15-25 MB |
| pip + packages | ~30-40 MB |
| **總計 (下載)** | **~50-60 MB** |
| .vsix (extension 本身) | ~30 KB |

首次啟動需要下載約 50-60 MB，之後就不需要了。
