# Active Context

## 當前焦點
完成 VS Code extension 的 PubMed 啟動回歸修復釋出準備，將 `pubmed-search-mcp` 安裝來源切到已修正的 upstream snapshot，並同步 Marketplace release notes。

## 相關檔案
- `vscode-extension/src/mcpProvider.ts` - 傳入 `PUBMED_WORKSPACE_DIR` 給 PubMed MCP server
- `vscode-extension/src/pubmedSearchPackage.ts` - 集中管理 PubMed 固定安裝來源、版本與 entrypoint
- `vscode-extension/src/pythonEnvironment.ts` - 驗證最小 PubMed 版本並安裝修正後 snapshot
- `vscode-extension/src/uvPythonManager.ts` - 內嵌 Python 環境改安裝固定的 PubMed snapshot
- `vscode-extension/CHANGELOG.md` - v0.5.23 release notes
- `vscode-extension/README.md` - 更新最新版本說明
- `memory-bank/progress.md` - 任務進度追蹤

## 待解決問題
- [x] 修正 VS Code 內 PubMed Search 0.5.4 啟動回歸
- [x] 將內嵌安裝來源切換到已修正的 upstream snapshot
- [ ] 建立 release commit 並推送 `v0.5.23-ext` tag

## 上下文
- `pubmed-search-mcp 0.5.4` 的 PyPI 發行版缺少啟動所需 import，會在 VS Code 內啟動 MCP server 時失敗。
- extension 端以 `PUBMED_WORKSPACE_DIR` 與固定 upstream commit snapshot 避開壞版發行物，同時保留 MCP metadata 為 `0.5.4`。
- 發布前檢查已完成 lint、compile、focused mocha tests 與 VSIX package，結果皆可用。

## 更新時間
2026-04-20
