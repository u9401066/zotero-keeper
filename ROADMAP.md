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

---

## Phase 4.6: Unified Search Gateway 🔄

> 🎯 **核心理念**：單一入口 + 後端自動分流（像 Google 一樣）
> 
> 📄 **詳細設計**：
> - `docs/research/UNIFIED_SEARCH_RESEARCH.md` - 總體規格
> - `docs/research/AGENT_MCP_COLLABORATION.md` - Agent-MCP 協作設計

### Phase 1.0 - 基礎建設 (8h) ✅ **COMPLETED**

> 📅 完成時間：2026-01-11

- ✅ **UnifiedArticle 統一資料模型** ⭐
  - ✅ `models/unified_article.py` - 統一文章物件
  - ✅ 支援所有來源的標準化欄位
  - ✅ OA 連結、引用指標欄位
  - ✅ `cite_vancouver()` / `cite_apa()` 引用格式輸出

- ✅ **新增資料源 Client**
  - ✅ `sources/crossref.py` - CrossRef Client
  - ✅ `sources/unpaywall.py` - Unpaywall Client
  - ✅ Rate limiting、重試機制

### Phase 1.5 - 查詢分析與結果彙整 (10h) ✅ **COMPLETED**

> 📅 完成時間：2026-01-11

- ✅ **QueryAnalyzer** ⭐
  - ✅ `unified/query_analyzer.py` - 查詢意圖分析
  - ✅ QueryComplexity 評估 (SIMPLE/MODERATE/COMPLEX/AMBIGUOUS)
  - ✅ QueryIntent 偵測 (LOOKUP/EXPLORATION/COMPARISON/SYSTEMATIC)
  - ✅ PICO 元素自動偵測
  - ✅ 年份約束解析、識別碼擷取 (PMID/DOI/PMC)

- ✅ **ResultAggregator** ⭐
  - ✅ `unified/result_aggregator.py` - 多維度排序
  - ✅ 5 維度評分：relevance, quality, recency, impact, source_trust
  - ✅ 去重邏輯（DOI > PMID > Title normalized）
  - ✅ RankingConfig 預設（default/impact/recency/quality focused）
  - ✅ 多來源合併與 merge_from() 整合

### Phase 2.0 - MVP 統一搜尋 (6h) ✅ **COMPLETED**

- ✅ **unified_search MCP Tool** ⭐ **MVP 里程碑**
  - ✅ `mcp/tools/unified.py` - 550+ 行 MCP 工具
  - ✅ 單一入口、後端自動分流
  - ✅ DispatchStrategy 矩陣實作
  - ✅ `analyze_search_query()` 查詢分析輔助工具
  - ✅ 16 項單元測試通過

### Phase 2.1 - Agent 友善工具重構 (4h) 🔄 **IN PROGRESS**

- ✅ **InputNormalizer** ⭐ 輸入規範化
  - ✅ `normalize_pmids()` - 多格式 PMID 支援
  - ✅ `normalize_pmcid()` - PMC ID 規範化
  - ✅ `normalize_year()` - 年份格式化
  - ✅ `normalize_limit()` - 限制數量規範
  - ✅ `normalize_bool()` - 布林值規範
  - ✅ `normalize_query()` - 查詢字串規範
  - ✅ 47 項單元測試通過

- ✅ **ResponseFormatter** ⭐ 回應格式化
  - ✅ `success()` - 成功回應 (markdown/json)
  - ✅ `error()` - 友善錯誤訊息 + 建議
  - ✅ `no_results()` - 無結果建議
  - ✅ `partial_success()` - 部分成功

- ✅ **KEY_ALIASES** ⭐ 參數別名
  - ✅ `year_from` → `min_year`
  - ✅ `max_results` → `limit`
  - ✅ `format` → `output_format`

- 📋 **現有工具改造**
  - 📋 套用 InputNormalizer 到所有工具
  - 📋 套用 ResponseFormatter 到所有工具
  - 📋 Integration tests

### Phase 2.5 - Agent 協作 (4h) 📋

- 📋 **NeedsDecisionResponse**
  - 📋 Agent 決策請求格式
  - 📋 Session 狀態管理
  - 📋 Suggest/Delegate 模式

### Phase 3.0 - 測試與監控 (4h) 📋

- 📋 **測試覆蓋**
  - 📋 Unit tests for each client
  - 📋 Integration tests for unified_search

- 📋 **監控指標**
  - 📋 Source response times
  - 📋 Fallback trigger rates

---

### v1.11.0 (2026 Q1) - Unified Search Framework

> ✅ Phase 1.0 + 1.5 + 2.0 = **MVP Complete!**

- ✅ **統一搜尋入口** ⭐ 最高優先
  - ✅ `unified_search()` - 取代分散的多個搜尋工具
  - ✅ QueryAnalyzer - 自動分析查詢意圖
  - ✅ ResultAggregator - 合併、去重、排序

- ✅ **新增資料源整合**
  - ✅ CrossRef Client - DOI 元數據、引用連結
  - ✅ Unpaywall Client - 自動 OA 連結附加

- ✅ **結果自動增強**
  - ✅ 每篇文章自動附加 OA 連結
  - ✅ 自動附加引用指標（iCite）
  - ✅ 統一 Article 物件格式

### v1.12.0 (2026 Q2) - Extended Sources

- 📋 **臨床試驗整合**
  - 📋 ClinicalTrials.gov Client
  - 📋 自動關聯文獻與試驗

- 📋 **預印本整合**
  - 📋 bioRxiv/medRxiv Client
  - 📋 追蹤預印本正式發表狀態

### 設計原則

```
❌ 舊設計（分散式）- Agent 需要自己選擇工具
   search_literature() / search_europe_pmc() / search_core() / ...

✅ 新設計（統一式）- 單一入口，後端自動分流
   unified_search(query, options)
   └── 自動選擇 PubMed/CrossRef/OpenAlex/CORE/...
   └── 自動合併去重
   └── 自動附加 OA 連結
```

### 競爭定位

| 維度 | 商用工具 (Elicit/SciSpace) | Zotero-Keeper |
|------|---------------------------|---------------|
| 目標用戶 | 一般研究者 | Zotero 用戶、醫學研究者 |
| 資料控制 | 雲端託管 | 100% 本地 |
| 成本 | $96-240/年 | **免費開源** |
| 整合性 | 獨立封閉 | 深度整合 Zotero |

---

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

## Phase 8: Reference Repositories & Learning Plan 📚

> 🎯 **核心價值**：從優秀開源專案學習，提升工具品質和功能完整度

### 重要參考 Repos

以下是 5 個重要的學術文獻搜尋相關開源專案，我們應該研究學習其設計模式和功能：

| Repo | Stars | 核心功能 | 學習重點 |
|------|-------|----------|----------|
| **[scholarly](https://github.com/scholarly-python-package/scholarly)** | 1.8k | Google Scholar 爬蟲 | 代理輪換、反爬蟲策略 |
| **[habanero](https://github.com/sckott/habanero)** | 238 | CrossRef API 客戶端 | Content negotiation 引用格式 |
| **[pyalex](https://github.com/J535D165/pyalex)** | 325 | OpenAlex API 封裝 | Pipe 操作、N-grams 支援 |
| **[metapub](https://github.com/metapub/metapub)** | 140 | NCBI/PubMed 工具包 | FindIt PDF 發現、UrlReverse |
| **[bioservices](https://github.com/cokelaer/bioservices)** | 325 | 40+ 生物服務整合 | 多服務框架設計 |
| **[wos-starter](https://github.com/clarivate/wosstarter_python_client)** | 29 | Web of Science API | Times Cited、JCR 連結 |

### 各 Repo 詳細學習計畫

#### 1. scholarly (Google Scholar 爬蟲) ⭐

**主要功能**：
- 論文搜尋與引用網路
- 作者資料和 h-index
- 代理輪換避免封鎖

**學習重點**：
- `ProxyGenerator` - 代理池管理 (ScraperAPI, Tor, Free Proxies)
- `fill()` 方法 - 延遲載入完整元數據
- `scholarly.citedby()` - 引用網路遍歷

**整合可能**：
- 📋 作為 unified_search 的補充來源
- 📋 取得 Google Scholar 引用數 (比 iCite 更全面)
- 📋 h-index 和作者影響力分析

#### 2. habanero (CrossRef API) ⭐

**主要功能**：
- DOI 解析和元數據
- 引用連結追蹤
- Content negotiation (多格式引用)

**學習重點**：
- `cn.content_negotiation()` - 一個 DOI 輸出多種格式 (RDF, BibTeX, Citeproc)
- `polite pool` - 使用 email 識別獲得更高速率限制
- 引用連結解析

**整合可能**：
- ✅ 已整合: `sources/crossref.py`
- 📋 強化 content negotiation 功能
- 📋 加入引用連結追蹤

#### 3. pyalex (OpenAlex API) ⭐

**主要功能**：
- 搜尋論文、作者、機構、來源
- N-grams 支援 (概念分析)
- 反向索引摘要轉純文字

**學習重點**：
- Pipe 操作鏈: `Works().filter().sort().get()`
- `abstract_inverted_index` → 純文字轉換
- Cursor-based pagination

**整合可能**：
- ✅ 部分整合: `sources/openalex.py`
- 📋 N-grams 主題趨勢分析
- 📋 Concepts API 主題探索

#### 4. metapub (NCBI 工具包) ⭐⭐ 高度相關

**主要功能**：
- PubMed 文獻搜尋
- **FindIt** - PDF 發現 (68+ 出版商)
- UrlReverse - URL → DOI/PMID

**學習重點**：
- `FindIt` 架構 - 15,000+ 期刊的 PDF URL 規則
- `CrossRef` 和 `PubMedArticle` 統一介面
- `MedGen`, `ClinVar` 整合

**整合可能**：
- 📋 **採用 FindIt 邏輯增強全文取得**
- 📋 UrlReverse 功能 (用戶給 URL，辨識論文)
- 📋 參考其 `PubMedArticle` 資料模型

#### 5. bioservices (多服務框架) ⭐

**主要功能**：
- 40+ 生物資訊服務的統一 Python 接口
- UniProt, KEGG, ChEMBL, PubChem...
- WSDL/SOAP + REST 支援

**學習重點**：
- 多服務統一框架設計
- 錯誤處理和重試機制
- 命令列工具設計

**整合可能**：
- 📋 學習其服務抽象層設計
- 📋 參考 CLI 設計模式
- 📋 整合 PubChem 化合物查詢

### 關於論文圖片 API 📷

> 🔍 **問題**：PubMed 官方 API 是否提供論文圖片連結？

**答案**：**PubMed E-utilities 是純文字 API，不提供圖片連結**

**替代方案**：

| 來源 | 圖片支援 | 說明 |
|------|----------|------|
| **PMC Open Access** | ✅ | 解析 JATS XML 中的 `<fig>` 元素 |
| **Europe PMC** | ✅ | text-mining API 有 FIGURE 類型標註 |
| **bioRxiv/medRxiv** | ✅ | 預印本直接提供圖片 URL |
| **OpenAlex** | ❌ | 無圖片連結 |
| **CrossRef** | ❌ | 無圖片連結 |

**技術實作建議**：
1. 取得 PMC 全文 XML (`get_fulltext_xml`)
2. 解析 `<fig>` 元素取得圖片路徑
3. 組合 PMC 圖片基礎 URL

**範例 PMC 圖片 URL 格式**：
```
https://www.ncbi.nlm.nih.gov/pmc/articles/PMC7096777/bin/figure1.jpg
```

### 學習優先順序

```
立即學習 (v1.12.0):
├── metapub.FindIt        → PDF 全文發現
├── habanero.cn          → 引用格式轉換
└── pyalex.pipe          → 流暢 API 設計

中期學習 (v1.13.0):
├── scholarly.proxy      → Google Scholar 整合
├── bioservices.框架     → 多服務抽象
└── PMC XML 圖片解析     → 論文圖片取得

長期考慮:
└── metapub 完整整合或 fork
```

### 長期持續學習

這些 repos 都是長期多人維護的成熟專案，值得持續追蹤：

| Repo | 維護狀態 | 持續學習重點 |
|------|----------|-------------|
| scholarly | 活躍 | 反爬蟲技術演進、新功能 |
| habanero | 活躍 | CrossRef API 更新 |
| pyalex | 活躍 | OpenAlex 新端點、N-grams |
| metapub | 活躍 | FindIt 出版商規則更新 |
| bioservices | 活躍 | 新服務整合 |
| wos-starter | 官方 | Web of Science API v2 特性 |

**建議**：每季度 Review 一次這些 repos 的 Release Notes 和新功能。

### 詳細文檔

📄 完整學習筆記請參考：`docs/research/REFERENCE_REPOSITORIES.md`

---

*Last updated: January 2025 (v1.10.4)*
