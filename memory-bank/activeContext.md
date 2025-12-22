# Active Context

> 🎯 目前工作焦點與下一步行動

## 當前狀態: Template 整合 + Skills 強化完成 ✅

### 已完成 (2025-12-22)
1. ✅ 導入 template-is-all-you-need 的 13 個 Skills
2. ✅ 強化 MCP tool descriptions（方案 1）
   - `search_pubmed_exclude_owned`: 加入完整 workflow
   - `quick_import_pmids`: 強調先問 Collection
   - `list_collections`: 標註匯入前必須先用
   - `get_session_pmids`: 避免重複搜尋指南
3. ✅ Extension 打包 Skills（方案 3）
   - `resources/skills/copilot-instructions.md`
   - `resources/skills/research-workflow.md`
   - 新命令 `zoteroMcp.installSkills`
4. ✅ 合併上一層 memory-bank 和研究文件
5. ✅ 更新子模組 pubmed-search-mcp (v0.1.16)
   - Session Tools
   - Multi-source Search (Semantic Scholar, OpenAlex)

---

## 下一步選項

### Option A: 繼續重構 (Nice-to-have)
拆分超過 400 行的檔案，符合 bylaws 規範

### Option B: 實作 P1b (功能導向)
實作 PubMed → Zotero RIS 直接匯入

### Option C: Extension 發布
發布 VS Code Extension v0.4.0 包含 Skills 功能

---

## 快速指令

```bash
# 查看超過 200 行的檔案
find mcp-server/src -name "*.py" -exec wc -l {} \; | awk '$1>200'

# 執行測試
cd mcp-server && uv run pytest -v

# 打包 Extension
cd vscode-extension && npm run package
```

---
*Updated: 2025-12-22*
*工作模式: Code*
