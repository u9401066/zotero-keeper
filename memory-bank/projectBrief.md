# Project Brief

> 📌 此檔案描述專案的高層級目標和範圍，建立後很少更改。

## 🎯 專案目的

**Zotero Keeper** - 整合 PubMed 文獻搜尋與 Zotero 書目管理的 AI 輔助研究工具組

包含：
- **pubmed-search-mcp**: PubMed 文獻搜尋 MCP Server
- **zotero-keeper**: Zotero 本地 API MCP Server
- **vscode-extension**: VS Code 整合擴充功能

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
- [ ] PubMed → Zotero 直送機制
- [ ] Session PMID 持久化完善

## 🚫 範圍限制

- 不提供 Zotero 雲端同步功能（僅本地 API）
- 不包含 Impact Factor 資料（版權問題）
- 不支援非 PubMed 資料庫搜尋

## 📦 相關專案

- [pubmed-search-mcp](https://pypi.org/project/pubmed-search-mcp/) - PyPI
- [vscode-zotero-mcp](https://marketplace.visualstudio.com/items?itemName=u9401066.vscode-zotero-mcp) - VS Code Marketplace

---
*Created: 2025-12-16*
