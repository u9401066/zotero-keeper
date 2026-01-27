# Active Context

> 🎯 目前工作焦點與下一步行動

## 當前狀態: VS Code Extension v0.5.9 發布完成 ✅

### 已完成 (2026-01-27)

1. ✅ 更新 pubmed-search-mcp 子模組到 v0.2.5
   - 修復 server 啟動 bug (session manager 變數名稱)

2. ✅ VS Code Extension v0.5.9 發布
   - 修復 uv venv 沒有 pip 的問題
   - pythonEnvironment.ts 自動偵測並使用 uv pip
   - 套件大小優化：601 檔案→20 檔案

3. ✅ 安全性修復
   - 修復 4 個 npm 安全漏洞
   - 新增 32-bit Windows 支援

4. ⚠️ Marketplace 驗證問題
   - v0.5.5-v0.5.8 都遇到 "Repository signing failed"
   - 這是 Microsoft 端的暫時性問題
   - v0.5.9 等待驗證中

---

## 待解決問題

### Marketplace Repository Signing Failed
- 原因：Microsoft 端暫時性問題
- 狀態：等待驗證或聯繫 VSMarketplace@microsoft.com
- 公開版本仍是 v0.5.2

### Open VSX 未發布
- 需要 Open VSX token（不是 Azure DevOps PAT）
- 取得方式：https://open-vsx.org/ → Settings → Access Tokens

---

## VSIX 手動安裝

```powershell
# 清除舊資料
Remove-Item -Recurse -Force "$env:APPDATA\Code - Insiders\User\globalStorage\u9401066.vscode-zotero-mcp"

# 安裝 VSIX
code-insiders --install-extension vscode-zotero-mcp-0.5.9.vsix
```

---

## 版本狀態

| 元件 | 版本 | 狀態 |
|------|------|------|
| pubmed-search-mcp | v0.2.5 | PyPI ✅ |
| zotero-keeper MCP | v1.11.0 | PyPI ✅ |
| VS Code Extension | v0.5.9 | Marketplace 驗證中 |
| 公開可用版本 | v0.5.2 | Marketplace ✅ |

---
*Updated: 2026-01-27*
*工作模式: Code*
