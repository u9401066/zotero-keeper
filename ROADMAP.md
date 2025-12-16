# Roadmap

Development roadmap for Zotero Keeper - A MCP server for local Zotero library management.

---

## Legend

- ✅ Completed
- 🔄 In Progress
- 📋 Planned
- 💡 Future Consideration

---

## Phase 1: Foundation ✅

### v1.0.0 - v1.1.0 (December 2024)

- ✅ Project structure (DDD architecture)
- ✅ FastMCP framework integration
- ✅ Zotero Local API client
- ✅ Basic connectivity (`check_connection`)
- ✅ Configuration management

---

## Phase 2: Core Functionality ✅

### v1.2.0 - v1.4.0 (December 2024)

- ✅ **Item Operations**
  - ✅ `add_reference` - Add new reference
  - ✅ `create_item` - Create with full metadata
  - ✅ `search_items` - Full-text search
  - ✅ `list_items` - Recent items
  - ✅ `get_item` - Get by key

- ✅ **Collection Operations**
  - ✅ `list_collections` - List all
  - ✅ `get_collection` - Get details
  - ✅ `get_collection_items` - Items in collection
  - ✅ `get_collection_tree` - Hierarchical view
  - ✅ `find_collection` - Search by name

- ✅ **Metadata**
  - ✅ `list_tags` - All tags
  - ✅ `get_item_types` - Available types

---

## Phase 3: Advanced Features ✅

### v1.5.0 - v1.6.0 (December 2024)

- ✅ **Dual API Architecture**
  - ✅ Local API for READ operations
  - ✅ Connector API for WRITE operations
  - ✅ Unified HTTP client

- ✅ **PubMed Integration**
  - ✅ `search_pubmed_exclude_owned` - Exclude owned items
  - ✅ `check_articles_owned` - Check ownership
  - ✅ `batch_import_from_pubmed` - Batch import

- ✅ **Saved Search Support** (Local API Exclusive!)
  - ✅ `list_saved_searches` - List searches
  - ✅ `run_saved_search` - Execute search
  - ✅ `get_saved_search_details` - Search conditions

- ✅ **Import Capabilities**
  - ✅ `import_ris_to_zotero` - RIS format
  - ✅ `import_from_pmids` - From PMIDs

### v1.7.0 (December 2024)

- ✅ **Tool Simplification** (21 tools, down from 27)
  - ✅ Consolidated smart tools into save tools
  - ✅ `smart_tools.py` now helpers only

- ✅ **MCP Resources** (10 URIs)
  - ✅ `zotero://collections` (+ tree, key, items)
  - ✅ `zotero://items` (+ key)
  - ✅ `zotero://tags`
  - ✅ `zotero://searches` (+ key)
  - ✅ `zotero://schema/item-types`

- ✅ **MCP Elicitation**
  - ✅ Interactive collection selection
  - ✅ Numbered options for user choice

- ✅ **Auto-fetch Metadata**
  - ✅ DOI → CrossRef API
  - ✅ PMID → PubMed E-utilities
  - ✅ Intelligent merge (user priority)

### v1.8.0 (December 2024)

- ✅ **Collection 防呆機制**
  - ✅ `collection_name` parameter (auto-validates!)
  - ✅ Returns available collections if not found
  - ✅ `collection_info` confirms destination
  - ✅ Warns against raw `collection_key` usage

- ✅ **Citation Metrics Support**
  - ✅ `include_citation_metrics` parameter
  - ✅ iCite API integration (RCR, Percentile)
  - ✅ Metrics stored in Zotero `extra` field

- ✅ **Documentation**
  - ✅ `docs/ZOTERO_LOCAL_API.md` created
  - ✅ API reference and limitations documented

### v1.8.1 (December 2024)

- ✅ **Advanced Search Tool** ⭐
  - ✅ `advanced_search` with multi-condition support
  - ✅ `item_type` filter (journalArticle, book, -attachment)
  - ✅ `tag` / `tags` filter (single, multiple, OR logic)
  - ✅ `qmode` for full-text search (everything = abstract)
  - ✅ `sort` / `direction` for flexible sorting

- ✅ **Enhanced Documentation**
  - ✅ API Capability Matrix (Local API vs Connector API)
  - ✅ Detailed technical limitations explanation
  - ✅ One-click installation roadmap section

### v1.10.1 (December 2024) - Current ⭐

- ✅ **One-Click Installation**
  - ✅ `vscode:mcp/install` URL button in README
  - ✅ One-click install for VS Code and VS Code Insiders

- ✅ **Library Analytics** ⭐
  - ✅ `get_library_stats`: Year/author/journal distribution
  - ✅ `find_orphan_items`: Find unorganized items

- ✅ **Quick Import**
  - ✅ `quick_import_pmids`: Simplest PubMed import method

- ✅ **Code Refactoring**
  - ✅ Split `server.py` (586 → 202 lines)
  - ✅ New `basic_read_tools.py` and `collection_tools.py`

### v1.10.0 (December 2024)

- ✅ **PyPI Publication**
  - ✅ `zotero-keeper` available on PyPI
  - ✅ `pip install zotero-keeper` works out of the box
  - ✅ All dependencies properly declared

- ✅ **VS Code Extension v0.3.1** ⭐
  - ✅ Replaced embedded Python with [uv](https://github.com/astral-sh/uv)
  - ✅ 10-100x faster package installation
  - ✅ Automatic Python 3.11 management
  - ✅ Fixed Windows installation errors
  - ✅ Smaller extension size (~30KB)

---

## Phase 4: Enhanced User Experience 📋

### v1.9.0 (Planned) - Library Analytics & Insights

> 🎯 **核心價值**：幫助用戶了解自己的文獻庫，發現問題並提供改善建議

- 📋 **文獻庫分析** ⭐ 高價值
  - 📋 `get_library_stats` - 統計分析（年份/作者/期刊分布）
  - 📋 `find_orphan_items` - 找出無 Collection、無標籤的「孤兒」文獻
  - 📋 `find_potential_duplicates` - 模糊比對找可能重複的文獻
  - 📋 `analyze_reading_progress` - 分析「待讀」vs「已讀」比例

- 📋 **Note & Annotation Support**
  - 📋 `get_item_notes` - 讀取文獻筆記
  - 📋 `get_item_attachments` - 列出附件
  - 📋 `get_pdf_annotations` - 讀取 PDF 標註 (if possible)

- 📋 **Better Error Handling**
  - 📋 Detailed error messages
  - 📋 Retry logic for transient failures
  - 📋 Connection recovery

### v2.0.0 (Planned) - One-Click Installation + Citation Analysis 🎯

> ⚠️ **目標用戶**：研究人員，不是開發者。需要簡化安裝流程。

- 📋 **安裝簡化**
  - 📋 PyPI Package: `pip install zotero-keeper-mcp`
  - 📋 Standalone Executable (PyInstaller)
  - 📋 Auto-configure MCP settings

- 📋 **VS Code Extension** ⭐ (詳見下方 Phase 4.5)
  - 📋 從 Marketplace 一鍵安裝
  - 📋 內嵌 MCP Server
  - 📋 自動配置

- 📋 **引用關係分析** ⭐ 結合 PubMed
  - 📋 `find_missing_citations` - 找出「我有 A 但沒有 A 引用的 B」
  - 📋 `suggest_related_papers` - 基於現有文獻推薦相關論文
  - 📋 `build_citation_map` - 視覺化文獻引用關係 (Mermaid)

- 📋 **智能標籤建議** (AI-Assisted)
  - 📋 `suggest_tags` - 根據標題/摘要建議標籤
  - 📋 `suggest_collection` - 建議應該放入哪個 Collection
  - 📋 `detect_topic_clusters` - 自動發現主題群組

- 📋 **Better Duplicate Detection**
  - 📋 Fuzzy title matching improvements
  - 📋 Author name normalization
  - 📋 ISBN validation

### v2.1.0 (Planned) - Report Generation

> 📝 **核心價值**：讓 AI Agent 幫助產生文獻報告

- 📋 **報告生成** ⭐
  - 📋 `generate_bibliography` - 產生特定格式引用列表 (APA/MLA/Chicago)
  - 📋 `summarize_collection` - 總結一個 Collection 的主題和內容
  - 📋 `create_reading_list` - 根據主題產生推薦閱讀順序
  - 📋 `export_collection_report` - 匯出 Collection 報告 (Markdown)

- 📋 **Caching Layer**
  - 📋 Cache frequently accessed collections
  - 📋 TTL-based invalidation
  - 📋 Memory-efficient storage

---

## Phase 4.5: VS Code Extension & Marketplace 📋

> 💡 **研究結果**：VS Code 支援三種 MCP 安裝方式

### 安裝方式比較

| 方式 | 簡易度 | 發布管道 | 適合用戶 |
|------|--------|----------|----------|
| **MCP Install URL** | ⭐⭐⭐⭐⭐ | 網站連結 | 所有用戶 |
| **VS Code Extension** | ⭐⭐⭐⭐⭐ | Marketplace | 所有用戶 |
| **mcp.json 配置** | ⭐⭐ | 手動 | 開發者 |

### 方案 A: MCP Install URL (最簡單) 🎯

VS Code 支援 `vscode:mcp/install?{json-config}` URL scheme：

```typescript
// 生成安裝連結
const config = {
  "name": "zotero-keeper",
  "command": "uvx",
  "args": ["zotero-keeper-mcp"]
};
const link = `vscode:mcp/install?${encodeURIComponent(JSON.stringify(config))}`;
// 結果: vscode:mcp/install?%7B%22name%22%3A%22zotero-keeper%22...
```

**優點**:
- 用戶點擊連結即可安裝
- 不需要發布到 Marketplace
- 可放在 GitHub README 或網站

**實作步驟**:
1. 📋 發布到 PyPI: `zotero-keeper-mcp`
2. 📋 在 README 加入一鍵安裝按鈕
3. 📋 建立 Landing Page 頁面

### 🚀 立即行動項目 (Next Actions)

> 📅 **目標**: v2.0.0 發布前完成以下項目

#### Step 1: 發布 PyPI 套件

```bash
# 1. 更新 pyproject.toml
[project]
name = "zotero-keeper-mcp"
version = "2.0.0"

# 2. 建構並發布
cd mcp-server
uv build
uv publish  # 或 twine upload dist/*
```

#### Step 2: 產生一鍵安裝連結

```python
import json
from urllib.parse import quote

config = {
    "name": "zotero-keeper",
    "command": "uvx", 
    "args": ["zotero-keeper-mcp"]
}

# VS Code 安裝連結
vscode_link = f"vscode:mcp/install?{quote(json.dumps(config))}"
# vscode:mcp/install?%7B%22name%22%3A%22zotero-keeper%22%2C%22command%22%3A%22uvx%22%2C%22args%22%3A%5B%22zotero-keeper-mcp%22%5D%7D

# VS Code Insiders 安裝連結  
insiders_link = f"vscode-insiders:mcp/install?{quote(json.dumps(config))}"
```

#### Step 3: 更新 GitHub README

```markdown
## 🚀 一鍵安裝

[![Install in VS Code](https://img.shields.io/badge/VS%20Code-Install%20MCP-007ACC?logo=visualstudiocode)](vscode:mcp/install?%7B%22name%22%3A%22zotero-keeper%22%2C%22command%22%3A%22uvx%22%2C%22args%22%3A%5B%22zotero-keeper-mcp%22%5D%7D)

[![Install in VS Code Insiders](https://img.shields.io/badge/VS%20Code%20Insiders-Install%20MCP-24bfa5?logo=visualstudiocode)](vscode-insiders:mcp/install?%7B%22name%22%3A%22zotero-keeper%22%2C%22command%22%3A%22uvx%22%2C%22args%22%3A%5B%22zotero-keeper-mcp%22%5D%7D)

**或手動安裝:**
\`\`\`bash
pip install zotero-keeper-mcp
\`\`\`
```

#### Step 4: Git 提交與標籤

```bash
# 提交變更
git add .
git commit -m "feat: v2.0.0 - One-click installation support"

# 建立標籤
git tag -a v2.0.0 -m "Release v2.0.0 - One-click MCP installation"
git push origin main --tags

# 建立 GitHub Release
gh release create v2.0.0 --title "v2.0.0 - One-Click Installation" --notes "..."
```

### 方案 B: VS Code Extension (完整整合)

使用 `vscode.lm.registerMcpServerDefinitionProvider` API：

```json
// package.json
{
  "contributes": {
    "mcpServerDefinitionProviders": [{
      "id": "zoteroKeeper",
      "label": "Zotero Keeper MCP Server"
    }]
  }
}
```

```typescript
// extension.ts
import * as vscode from 'vscode';

export function activate(context: vscode.ExtensionContext) {
  context.subscriptions.push(
    vscode.lm.registerMcpServerDefinitionProvider('zoteroKeeper', {
      provideMcpServerDefinitions: () => [{
        name: 'zotero-keeper',
        command: 'uvx',
        args: ['zotero-keeper-mcp']
      }]
    })
  );
}
```

**優點**:
- Marketplace 一鍵安裝 + 自動更新
- 可加入 UI (狀態列、設定頁面)
- 與 VS Code 深度整合

**實作步驟**:
1. 📋 建立 VS Code Extension 專案
2. 📋 實作 `registerMcpServerDefinitionProvider`
3. 📋 申請 Publisher ID
4. 📋 發布到 Marketplace

### 方案 C: Chat Participant (進階)

超越 MCP，直接實作 Chat Participant：

```json
// package.json
{
  "contributes": {
    "chatParticipants": [{
      "id": "zotero-keeper.zotero",
      "name": "zotero",
      "fullName": "Zotero Keeper",
      "description": "Manage your Zotero library"
    }]
  }
}
```

**優點**:
- `@zotero` 呼叫方式
- 完全控制 prompt 和回應
- 可加入 slash commands (`/search`, `/import`)

**註**: 需要更多開發工作，但提供最佳用戶體驗

### 推薦路徑

```
v2.0: PyPI + MCP Install URL (簡單快速)
       ↓
v2.5: VS Code Extension (完整整合)
       ↓
v3.0: Chat Participant (最佳體驗)
```

---

## Phase 5: Write Operations via Plugin Integration 🔄

> ⚠️ **Zotero Local API 限制**: DELETE/PATCH/PUT 回傳 501 Not Implemented
> 
> 解決方案：整合 Zotero 外掛，透過外掛的內部 API 實現寫入操作

### v2.0.0 - Plugin Bridge (Planned)

- 📋 **Actions & Tags 整合** ⭐ 推薦
  - 📋 研究 Actions & Tags 的 customScript API
  - 📋 設計 MCP → Plugin 的通訊機制
  - 📋 實作常用操作腳本模板
  - 📋 文檔化腳本安裝步驟

- 📋 **可能的寫入操作** (需 Plugin)
  - 📋 `delete_items` - 刪除文獻 (`item.eraseTx()`)
  - 📋 `move_to_collection` - 移動文獻 (`item.addToCollection()`)
  - 📋 `remove_from_collection` - 從 Collection 移除
  - 📋 `update_item_field` - 更新欄位 (`item.setField()`)
  - 📋 `batch_add_tags` - 批次加標籤
  - 📋 `batch_remove_tags` - 批次移除標籤

- 📋 **實作方式探索**
  - 💡 方案 A: MCP 輸出腳本 → 使用者貼到 Actions & Tags
  - 💡 方案 B: 透過 Zotero 的 `Run JavaScript` 功能
  - 💡 方案 C: 等待 Zotero 官方開放 Local API 寫入

### 相關外掛資源

| 外掛 | Stars | 功能 | 連結 |
|------|-------|------|------|
| **Actions & Tags** | 2.5k | 自訂腳本、事件觸發 | [GitHub](https://github.com/windingwind/zotero-actions-tags) |
| **Zutilo** | 1.7k | 批次操作、快捷鍵 | [GitHub](https://github.com/wshanks/Zutilo) |
| **Better BibTeX** | - | 引用鍵管理 | [GitHub](https://github.com/retorquere/zotero-better-bibtex) |

### 常用腳本範例 (Actions & Tags)

```javascript
// 刪除選中文獻
if (items?.length > 0) {
    for (const item of items) {
        await item.eraseTx();
    }
}

// 移動到指定 Collection
const targetKey = "MHT7CZ8U";
if (items?.length > 0) {
    for (const item of items) {
        item.addToCollection(targetKey);
        await item.saveTx();
    }
}
```

---

## Phase 6: Multi-Library & Collaboration 💡

### v2.x.0 (Future Consideration)

- 💡 **Group Library Support**
  - 💡 List available libraries
  - 💡 Switch library context
  - 💡 Permission-aware operations

- 💡 **Sync Status**
  - 💡 Check sync status
  - 💡 Show sync conflicts
  - 💡 Trigger sync (if possible)

- 💡 **Collection Management** (等待 Zotero API 支援)
  - 💡 Create collections
  - 💡 Move items between collections
  - 💡 Rename collections

---

## Phase 7: Advanced Integration 💡

### Future Releases

- 💡 **Citation Export**
  - 💡 Generate citations in multiple styles
  - 💡 Integration with document editors

- 💡 **AI-Powered Features**
  - 💡 Automatic tagging based on content
  - 💡 Smart collection assignment
  - 💡 Related paper suggestions

- 💡 **Real-time Updates**
  - 💡 WebSocket support (if Zotero supports)
  - 💡 Push notifications for library changes

- 💡 **等待 Zotero 官方支援**
  - 💡 Local API Write Support ([Issue #1320](https://github.com/zotero/zotero/issues/1320))
  - 💡 當支援後，直接實作原生寫入操作

---

## Tool Count Evolution

| Version | Total Tools | Notes |
|---------|-------------|-------|
| v1.1.0  | 1 | `check_connection` only |
| v1.2.0  | 5 | + CRUD basics |
| v1.3.0  | 8 | + Search |
| v1.4.0  | 13 | + Collections |
| v1.5.0  | 19 | + Smart tools |
| v1.6.0  | 27 | + PubMed + Saved Search |
| v1.7.0 | 21 | Simplification |
| v1.8.0 | 21 | Collection 防呆 + RCR |
| v1.10.0 | 22 | PyPI + VS Code Extension v0.3.1 |
| **v1.10.1** | **25** | **One-click install + Analytics tools (current)** |
| v1.11.0  | ~28 | + More Analytics (duplicates, citations) |
| v2.0.0  | ~32 | + Citation Analysis + Smart Suggestions |
| v2.1.0  | ~36 | + Report Generation |

---

## MCP Features Evolution

| Feature | Version | Status |
|---------|---------|--------|
| Tools | v1.1.0 | ✅ |
| Resources | v1.7.0 | ✅ |
| Elicitation | v1.7.0 | ✅ |
| Prompts | - | 💡 Future |
| Sampling | - | 💡 Future |

---

## Contributing

Have ideas for new features? Open an issue on GitHub!

Priority considerations:
1. Does it improve the literature management workflow?
2. Is it possible with Zotero's Local/Connector API?
3. Does it reduce complexity (not add more tools)?

---

*Last updated: December 16, 2024 (v1.10.1)*
