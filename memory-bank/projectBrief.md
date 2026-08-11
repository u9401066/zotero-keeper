# Project Brief

> 📌 此檔案描述專案的高層級目標和範圍，建立後很少更改。

## 🎯 專案目的

**Zotero Keeper** - 整合 PubMed 文獻搜尋與 Zotero 書目管理的 AI 輔助研究工具組

包含：
- **pubmed-search-mcp**: PubMed / 多來源生醫文獻搜尋、全文、pipeline、
  session 與 Research Chronicle MCP Server
- **zotero-keeper**: Zotero Local API / Connector MCP Server，負責本地書庫與匯入
- **vscode-extension**: 在單一受管理 Python 環境安裝、驗證並啟動兩套 MCP 的
  VS Code 整合擴充功能

## 👥 目標用戶

- 醫學研究人員和臨床醫師
- 需要系統性文獻回顧的學者
- 使用 Zotero 管理書目的研究者
- VS Code + GitHub Copilot 使用者

## 🏆 成功指標

- [x] PubMed 搜尋 MCP Server 可正常運作
- [x] Zotero 本地 API 整合完成
- [x] VS Code Extension 發布到 Marketplace
- [x] 支援 PICO 臨床問題搜尋
- [x] PubMed / UnifiedArticle → Zotero `import_articles` 直送機制
- [x] Session PMID / article cache / summary 持久化
- [x] 本機 PDF metadata / auto-recognize 匯入
- [ ] 完成 MCP SDK v2 breaking release：Keeper `2.0.0`、PubMed `0.6.1`、
  VSIX `0.6.0`

## 🚫 範圍限制

- Keeper 不取代 Zotero 雲端同步或 Zotero Web API；主要邊界是桌面 Local API /
  Connector
- 不包含 Impact Factor 資料（版權問題）
- 外部 biomedical sources 由 PubMed Search MCP 聚合；Keeper 不重複實作搜尋
- 不把可遠端存取的 authenticated service 與 local/Connector 模式視為同一
  信任邊界
- Zotero 官方組織目前沒有發布 MCP server；Registry 收錄的社群 server 不構成
  Zotero 官方背書，也不得因相同 `zotero_mcp` namespace 與 Keeper 混裝

## 📦 相關專案

- [pubmed-search-mcp](https://pypi.org/project/pubmed-search-mcp/) - PyPI
- [vscode-zotero-mcp](https://marketplace.visualstudio.com/items?itemName=u9401066.vscode-zotero-mcp) - VS Code Marketplace

---
*Created: 2025-12-16*
*Updated: 2026-08-11*
