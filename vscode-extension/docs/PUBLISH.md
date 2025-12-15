# VS Code Extension 發布指南

## 📋 發布到 Marketplace 的步驟

### 1️⃣ 建立 Azure DevOps 帳號和 PAT

1. 前往 https://dev.azure.com/
2. 登入或建立帳號
3. 建立組織 (Organization)
4. 建立 Personal Access Token (PAT):
   - User Settings → Personal Access Tokens → New Token
   - **Scopes**: 選擇 "Marketplace" → 勾選 "Manage"
   - 複製並保存 token (只顯示一次!)

### 2️⃣ 建立 Publisher

```bash
# 安裝 vsce (VS Code Extension 管理工具)
npm install -g @vscode/vsce

# 建立 publisher (首次)
vsce create-publisher <publisher-name>
# 例如: vsce create-publisher u9401066

# 或登入現有 publisher
vsce login <publisher-name>
# 輸入你的 PAT
```

### 3️⃣ 準備發布

確認 `package.json` 包含必要欄位:
```json
{
    "name": "vscode-zotero-mcp",
    "displayName": "Zotero + PubMed MCP",
    "publisher": "u9401066",  // ← 你的 publisher ID
    "version": "0.1.0",
    "engines": { "vscode": "^1.99.0" },
    "icon": "resources/icon.png",  // ← 需要 128x128 PNG
    "repository": { ... },
    "license": "Apache-2.0"
}
```

### 4️⃣ 打包和發布

```bash
cd vscode-extension

# 打包成 .vsix 檔 (本地測試用)
vsce package
# 產生: vscode-zotero-mcp-0.1.0.vsix

# 發布到 Marketplace
vsce publish
# 或指定版本
vsce publish minor  # 0.1.0 → 0.2.0
vsce publish patch  # 0.1.0 → 0.1.1
```

---

## 🧪 測試安裝的方法

### 方法 1: 從 .vsix 檔安裝 (本地測試)

```bash
# 打包
vsce package

# 在 VS Code 中安裝
code --install-extension vscode-zotero-mcp-0.1.0.vsix

# 或在 VS Code UI:
# Extensions → ⋯ → Install from VSIX...
```

### 方法 2: 從 Marketplace 安裝 (發布後)

```bash
# 命令列安裝
code --install-extension u9401066.vscode-zotero-mcp

# 或在 VS Code 中搜尋 "Zotero MCP"
```

### 方法 3: 開發模式測試

```bash
cd vscode-extension

# 啟動 Extension Development Host
# 按 F5 或執行 "Run Extension" 任務
```

---

## ✅ 驗證安裝成功

### 檢查 Extension 已載入

1. 開啟 VS Code
2. `Ctrl+Shift+P` → "Extensions: Show Installed Extensions"
3. 搜尋 "Zotero"
4. 應該看到 "Zotero + PubMed MCP" 已安裝

### 檢查 MCP Servers 已註冊

1. `Ctrl+Shift+P` → "GitHub Copilot: Manage Tools"
2. 應該看到:
   - ✅ Zotero Keeper
   - ✅ PubMed Search

### 檢查狀態列

- 右下角應該顯示 `🔬 Zotero MCP: Ready`

### 測試功能

在 Copilot Chat 中嘗試:
```
@workspace Search PubMed for remimazolam sedation
```

---

## 🔧 發布前檢查清單

- [ ] `package.json` 版本號正確
- [ ] `README.md` 完整
- [ ] `CHANGELOG.md` 已更新
- [ ] 有 icon.png (128x128 或更大)
- [ ] 所有 TypeScript 編譯成功 (`npm run compile`)
- [ ] 已在本地測試 `.vsix` 檔

---

## 📊 Marketplace 統計

發布後可在以下位置查看:
- https://marketplace.visualstudio.com/items?itemName=u9401066.vscode-zotero-mcp
- 下載數、評分、安裝趨勢

---

## ⚠️ 常見問題

### "Missing publisher"
確保 `package.json` 有 `"publisher": "your-id"`

### "Invalid icon"
Icon 必須是 PNG，建議 128x128 或 256x256

### "vsce login 失敗"
確認 PAT 有 Marketplace Manage 權限

### Extension 載入但 MCP servers 沒出現
- 檢查 Python 是否正確安裝
- 檢查 Output panel → "Zotero MCP" 的錯誤訊息
