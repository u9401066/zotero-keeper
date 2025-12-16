# Copilot 自定義指令 - Zotero Keeper

## 專案概述
這是一個整合 PubMed 文獻搜尋與 Zotero 書目管理的 AI 輔助研究工具組。

## 開發哲學 💡
> **「想要寫文件的時候，就更新 Memory Bank 吧！」**
> 
> **「想要零散測試的時候，就寫測試檔案進 tests/ 資料夾吧！」**

## 法規遵循
你必須遵守以下法規層級：
1. **憲法**：`CONSTITUTION.md` - 最高原則
2. **子法**：`.github/bylaws/*.md` - 細則規範

## 架構原則
- 採用 DDD (Domain-Driven Design)
- DAL (Data Access Layer) 必須獨立
- 參見子法：`.github/bylaws/ddd-architecture.md`

## Python 環境（uv 優先）
- 新專案必須使用 uv 管理套件
- 必須建立虛擬環境（禁止全域安裝）
- 參見子法：`.github/bylaws/python-environment.md`

## Memory Bank 同步
每次重要操作必須更新 Memory Bank：
- 參見子法：`.github/bylaws/memory-bank.md`
- 目錄：`memory-bank/`

## Git 工作流
提交前必須執行檢查清單：
- 參見子法：`.github/bylaws/git-workflow.md`

## MCP Server 開發
- pubmed-search-mcp: `external/pubmed-search-mcp/`
- zotero-keeper: `mcp-server/`
- 使用 FastMCP 框架

## VS Code Extension 開發
- 位置: `vscode-extension/`
- 使用 TypeScript
- 發布到 VS Code Marketplace

## 回應風格
- 使用繁體中文
- 提供清晰的步驟說明
- 引用相關法規條文
