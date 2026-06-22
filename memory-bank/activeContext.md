# Active Context

## 當前焦點
準備 VS Code extension v0.5.33 發布，將 managed `pubmed-search-mcp` 安裝來源、submodule、keeper optional dependency floor、文件與 bundled assistant assets 升級到 `pubmed-search-mcp v0.5.17`。

## 相關檔案
- `vscode-extension/src/mcpProvider.ts` - 傳入 `PUBMED_WORKSPACE_DIR` 給 PubMed MCP server
- `vscode-extension/src/pubmedSearchPackage.ts` - 集中管理 PubMed 固定安裝來源、版本與 entrypoint
- `vscode-extension/src/zoteroKeeperPackage.ts` - extension-managed keeper archive 指向當前 `v0.5.33-ext` release tag
- `vscode-extension/src/pythonEnvironment.ts` - 驗證最小 PubMed 版本並安裝修正後 snapshot
- `vscode-extension/src/uvPythonManager.ts` - 內嵌 Python 環境改安裝固定的 PubMed snapshot
- `mcp-server/pyproject.toml` - keeper optional/dev PubMed dependency floor
- `external/pubmed-search-mcp` - bundled PubMed Search MCP submodule pointer
- `vscode-extension/CHANGELOG.md` - v0.5.33 release notes
- `vscode-extension/README.md` - 更新最新版本說明
- `memory-bank/progress.md` - 任務進度追蹤

## 待解決問題
- [x] 確認 `pubmed-search-mcp v0.5.17` GitHub tag/commit 可達
- [x] 確認 PyPI resolver 可解析 `pubmed-search-mcp==0.5.17`
- [ ] 建立 release commit 並推送 `v0.5.33-ext` tag 觸發 VSIX 更新

## 上下文
- `pubmed-search-mcp v0.5.17` 修復 MCP startup 後 OpenAlex、CrossRef、Unpaywall 與 fulltext downloader fallback 掉回 placeholder source API email 的問題。
- extension 端持續用固定 upstream commit archive 安裝 PubMed Search，以保留可重現、自動刷新、跨平台的 VSIX managed install 行為。
- 發布前仍需執行 Zotero full-check、VSIX package smoke、VSIX contents check、分段 commit、push main 與推送 `v0.5.33-ext` tag。

## 更新時間
2026-06-22
