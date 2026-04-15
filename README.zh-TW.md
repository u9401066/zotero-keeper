# Zotero Keeper 📚

讓 AI 幫你管理文獻！連接 VS Code Copilot / Claude Desktop 與本地 Zotero 書目資料庫。

[![Python 3.12+](https://img.shields.io/badge/python-3.12+-blue.svg)](https://www.python.org/downloads/)
[![MCP SDK](https://img.shields.io/badge/MCP-FastMCP-green.svg)](https://github.com/modelcontextprotocol/python-sdk)
[![License](https://img.shields.io/badge/license-Apache%202.0-blue.svg)](LICENSE)
[![Zotero 7/8](https://img.shields.io/badge/Zotero-7%20%2F%208-red.svg)](https://www.zotero.org/)
[![CI](https://github.com/u9401066/zotero-keeper/actions/workflows/ci.yml/badge.svg)](https://github.com/u9401066/zotero-keeper/actions/workflows/ci.yml)

> 🌐 **[English](README.md)** | **繁體中文**

---

## ✨ 這是什麼？

**Zotero Keeper** 是一個 [MCP 伺服器](https://modelcontextprotocol.io/)，讓你的 AI 助手可以：

- 🔍 **搜尋文獻**：「幫我找 2024 年關於 CRISPR 的論文」
- 📖 **查看細節**：「這篇文章的摘要是什麼？」
- ➕ **新增文獻**：「把這篇 DOI 加到我的 Zotero」（自動取得完整 metadata！）
- 🤝 **協作式 PubMed 工作流**：先用 pubmed-search-mcp 搜尋，再用 keeper 檢查重複與匯入
- 📁 **互動式存檔**：列出所有收藏夾讓你選擇！

不用自己開 Zotero、手動搜尋、複製貼上。直接用自然語言告訴 AI，它會幫你完成！

---

## ✨ 特色功能

- **🔌 MCP 原生整合**：使用 FastMCP SDK，與 AI Agent 無縫整合
- **📖 MCP Resources**：透過 URI 瀏覽 Zotero 資料（`zotero://collections` 等）
- **💬 MCP Elicitation**：互動式收藏夾選擇，提供數字選項
- **🔒 自動取得 Metadata**：DOI/PMID → 自動取得完整摘要 + 所有欄位！
- **📖 讀取操作**：搜尋、列出、取得本地 Zotero 書目資料
- **✏️ 寫入操作**：透過 Connector API 將新參考文獻加入 Zotero
- **🧠 智慧功能**：重複偵測、參考文獻驗證、智能匯入
- **📁 Collection 支援**：支援巢狀收藏夾（資料夾層級結構）
- **🏗️ DDD 架構**：乾淨的領域驅動設計，洋蔥式架構
- **🔒 無需雲端**：所有操作都在本地，無需 Zotero 帳號

---

## 🚀 快速開始

### 你需要準備

- ✅ [Python 3.12+](https://www.python.org/downloads/)
- ✅ [Zotero 7 or 8](https://www.zotero.org/download/) (要先執行)
- ✅ [VS Code](https://code.visualstudio.com/) + GitHub Copilot，或 [Claude Desktop](https://claude.ai/)
- ✅ [uv](https://docs.astral.sh/uv/getting-started/installation/) 套件管理工具 (推薦)

### 三步驟安裝

```bash
# 1. 下載專案
git clone https://github.com/u9401066/zotero-keeper.git
cd zotero-keeper/mcp-server

# 2. 安裝（使用 uv）
uv sync --extra all

# 3. 測試連線 (先確認 Zotero 有開著)
uv run python -m zotero_mcp
```

### 設定 VS Code Copilot

在你的專案資料夾建立 `.vscode/mcp.json`：

```json
{
  "servers": {
    "zotero-keeper": {
      "type": "stdio",
      "command": "uv",
      "args": [
        "run",
        "--directory",
        "/你的路徑/zotero-keeper/mcp-server",
        "python", "-m", "zotero_mcp"
      ]
    }
  }
}
```

### 設定 Claude Desktop

編輯 `claude_desktop_config.json`：

```json
{
  "mcpServers": {
    "zotero-keeper": {
      "command": "uv",
      "args": ["run", "python", "-m", "zotero_mcp"],
      "cwd": "/你的路徑/zotero-keeper/mcp-server"
    }
  }
}
```

### 常用環境變數

如果你是直接啟動 server，建議透過 `.env` 或 MCP 啟動設定提供以下變數：

```bash
ZOTERO_HOST=localhost
ZOTERO_PORT=23119
ZOTERO_TIMEOUT=30
NCBI_EMAIL=your.email@example.com
# NCBI_API_KEY=your_api_key_here
# ZOTERO_KEEPER_ENABLE_LEGACY_PUBMED_TOOLS=1
# PUBMED_SEARCH_PATH=/path/to/pubmed-search-mcp
```

- `NCBI_EMAIL` 與可選的 `NCBI_API_KEY` 可提高 NCBI / PubMed API 的請求額度。
- `ZOTERO_KEEPER_ENABLE_LEGACY_PUBMED_TOOLS=1` 只應在你刻意要啟用 keeper 舊版 PubMed bridge / import 工具時設定。
- `PUBMED_SEARCH_PATH` 只用於本地開發，讓 keeper 載入你 checkout 下來的 `pubmed-search-mcp` 原始碼，而不是已安裝套件。

---

## 📚 文件導覽

- [README.md](README.md) — 英文總覽
- [mcp-server/README.md](mcp-server/README.md) — server 使用方式與工具說明
- [vscode-extension/README.md](vscode-extension/README.md) — VS Code 擴充功能安裝與使用體驗
- [docs/ZOTERO_LOCAL_API.md](docs/ZOTERO_LOCAL_API.md) — Zotero API 能力與限制整理
- [ARCHITECTURE.md](ARCHITECTURE.md) — 元件與分層架構
- [CONTRIBUTING.md](CONTRIBUTING.md) — 開發與貢獻流程

---

## 🔧 可用工具 (預設公開面 23 個 + legacy opt-in 5 個)

> 💡 **提示**：大部分讀取操作也可透過 [MCP Resources](#-mcp-resources-可瀏覽的資料) 完成，不需呼叫 Tool。

### 📖 核心工具 (server.py - 6 工具)

| 工具 | 說明 | 範例問法 |
|------|------|----------|
| `check_connection` | 測試 Zotero 連線 | 「Zotero 有在執行嗎？」 |
| `search_items` | 搜尋文獻 | 「幫我找 CRISPR 的論文」 |
| `get_item` | 取得文獻詳情 | 「這篇文章 (key:ABC123) 的摘要」 |
| `list_items` | 列出文獻 | 「列出 AI Research 收藏夾的文獻」 |
| `list_tags` | 列出標籤 | 「我用過哪些標籤？」 |
| `get_item_types` | 取得文獻類型 | 「可以新增什麼類型？」 |

### 📁 Collection 工具 (server.py - 5 工具)

> ⚠️ 這些工具也可透過 `zotero://collections/...` Resources 存取

| 工具 | 說明 | 對應 Resource |
|------|------|----------------|
| `list_collections` | 列出所有收藏夾 | `zotero://collections` |
| `get_collection` | 取得收藏夾詳情 | `zotero://collections/{key}` |
| `get_collection_items` | 列出收藏夾內容 | `zotero://collections/{key}/items` |
| `get_collection_tree` | 取得樹狀結構 | `zotero://collections/tree` |
| `find_collection` | 用名稱查找 | — (僅 Tool 支援) |

### ✏️ 存檔工具 (interactive_tools.py - 2 工具)

> 📊 **RCR 自動取得**：當提供 PMID 時，預設會自動從 iCite 取得 Relative Citation Ratio 並存入 Zotero extra 欄位

| 工具 | 說明 | 範例問法 |
|------|------|----------|
| `interactive_save` ⭐ | 互動式存檔 + 自動 RCR | 「把這篇存到 Zotero」 |
| `quick_save` | 快速存檔 + 自動 RCR | 「快速存到 AI Research」 |

### 🔍 Saved Search 工具 (saved_search_tools.py - 3 工具)

| 工具 | 說明 | 範例問法 |
|------|------|----------|
| `list_saved_searches` | 列出所有 Saved Search | 「有哪些儲存的搜尋？」 |
| `run_saved_search` | 執行 Saved Search | 「哪些論文還沒下載 PDF？」 |
| `get_saved_search_details` | 取得搜尋條件 | 「『缺少 PDF』的條件是什麼？」 |

### 🔍 進階搜尋與擁有狀態檢查 (search_tools.py - 2 個公開工具)

| 工具 | 說明 | 範例問法 |
|------|------|----------|
| `advanced_search` ⭐ | 多條件搜尋 (itemType, tag, qmode) | 「找出所有標記為 AI 的期刊論文」 |
| `check_articles_owned` | 檢查 PMID 是否已有 | 「這些 PMID 我有嗎？」 |

### 📥 匯入工具 (單一公開 handoff)

> 🤝 **collaboration-safe 預設**：PubMed 搜尋、探索與匯出由 pubmed-search-mcp 負責；Zotero Keeper 提供單一公開匯入入口 `import_articles`。

| 工具 | 說明 | 範例問法 |
|------|------|----------|
| `import_articles` ⭐ | 單一公開匯入入口，可接 JSON articles 或 RIS 文字 | 「把這批 PubMed 結果存到 AI Research」 |

### 📊 分析工具 (analytics_tools.py - 2 工具)

| 工具 | 說明 | 範例問法 |
|------|------|----------|
| `get_library_stats` | 顯示年份 / 作者 / 期刊統計 | 「顯示我的文獻庫統計」 |
| `find_orphan_items` | 找出未放入收藏夾的文獻 | 「哪些文獻還沒整理？」 |

### 📎 附件工具 (attachment_tools.py - 2 工具)

| 工具 | 說明 | 範例問法 |
|------|------|----------|
| `get_item_attachments` | 列出附件資訊與檔案路徑 | 「列出 key:ABC123 的附件」 |
| `get_item_fulltext` | 讀取 Zotero 已索引的 PDF/EPUB 全文 | 「打開 key:ABC123 的全文」 |

#### Legacy PubMed bridge 工具

舊版 keeper PubMed bridge / import 工具現在都預設隱藏，避免和 pubmed-search-mcp 重複暴露同一類 PubMed 工作流。

只有在你刻意要使用舊版 keeper 單機橋接模式時，才設定 `ZOTERO_KEEPER_ENABLE_LEGACY_PUBMED_TOOLS=1`。

#### 推薦的 PubMed → Zotero 工作流

```python
# 1. 用 pubmed-search-mcp 搜尋
results = unified_search("anesthesia AI", output_format="json")

# 需要納入預印本時
results = unified_search("anesthesia AI", output_format="json", options="preprints")

# 需要保留非同行審查內容時
results = unified_search("anesthesia AI", output_format="json", options="all_types")

# 2. 可選：先對本地 Zotero 做重複檢查
owned = check_articles_owned([article["identifiers"]["pmid"] for article in results["articles"] if article.get("identifiers", {}).get("pmid")])

# 3. 匯入到 Zotero
import_articles(
  articles=results["articles"],
  collection_name="AI Research"
)
```

#### advanced_search 使用範例

```python
# 🔍 依文獻類型搜尋
advanced_search(item_type="journalArticle")  # 只找期刊論文
advanced_search(item_type="book")  # 只找書籍
advanced_search(item_type="-attachment")  # 排除附件

# 🏷️ 依標籤搜尋
advanced_search(tag="AI")  # 具有 AI 標籤的文獻
advanced_search(tags=["AI", "Review"])  # 同時具有兩個標籤 (AND)
advanced_search(tag="AI || ML")  # 具有任一標籤 (OR)

# 📝 全文搜尋 (含 abstract)
advanced_search(q="XGBoost", qmode="everything")  # 搜尋摘要內容

# 🌟 組合條件
advanced_search(
    q="machine learning",
    item_type="journalArticle",
    tag="AI",
    sort="dateAdded",
    direction="desc"
)
```

---

## 📖 MCP Resources (可瀏覽的資料)

不需要呼叫 Tool！AI 可以直接瀏覽 Zotero 資料：

| Resource URI | 說明 |
|--------------|------|
| `zotero://collections` | 所有收藏夾 |
| `zotero://collections/tree` | 收藏夾樹狀結構 |
| `zotero://collections/{key}` | 特定收藏夾 |
| `zotero://collections/{key}/items` | 收藏夾內的文獻 |
| `zotero://items` | 最近的文獻 |
| `zotero://items/{key}` | 文獻詳情 |
| `zotero://tags` | 所有標籤 |
| `zotero://searches` | Saved Search 列表 |
| `zotero://searches/{key}` | 搜尋詳情 |
| `zotero://schema/item-types` | 可用的文獻類型 |

---

## 🎯 互動式存檔（推薦！）

`interactive_save` 使用 **MCP Elicitation** 技術，會列出所有收藏夾讓你選擇：

```
你：「把這篇 DOI:10.1234/example 的論文存到 Zotero」

[MCP Elicitation 彈出]
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📚 Saving: Deep Learning for Medical Imaging

⭐ 推薦:
   1. AI Research (匹配度: 90%) - 標題匹配
   2. Medical Imaging (匹配度: 75%) - 關鍵字匹配

📂 所有收藏夾:
   3. Biology (12 items)
   4. Chemistry (8 items)
   5. 待讀 (23 items)

0. 存到 My Library (不選收藏夾)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

輸入數字選擇: [用戶輸入: 1]

AI: ✅ 已存入 'AI Research' 收藏夾！
```

### 🔒 資料完整性：自動取得 Metadata

當你提供 **DOI** 或 **PMID** 時，工具會自動取得完整 metadata：

- **DOI** → CrossRef API → 完整摘要、作者、期刊、日期
- **PMID** → PubMed API → 完整摘要、MeSH 詞彙、機構

再也不會遺失摘要！只要提供識別碼即可。

---

## 📁 Collection 組織策略

Zotero 支援**巢狀收藏夾**。建議的組織方式：

### 依主題分類（推薦）
```
📁 我的文獻庫
├── 📁 研究主題
│   ├── 📂 CRISPR 基因編輯
│   ├── 📂 醫療 AI
│   └── 📂 麻醉安全
├── 📁 專案
│   ├── 📂 2024 論文草稿
│   └── 📂 博士論文
└── 📁 閱讀清單
    ├── 📂 待讀
    └── 📂 重要文獻
```

> 💡 **最佳實踐**：用**收藏夾**做主要分類，用**標籤**標記屬性（如「待讀」、「重要」、「review」）。

---

## 🔬 搭配 PubMed 使用

最強大的工作流程是搭配 [pubmed-search-mcp](https://github.com/u9401066/pubmed-search-mcp)：

```
你: 「幫我找 2024 年麻醉 AI 的新論文，我還沒有的」

AI 執行:
1. pubmed-search-mcp: unified_search("anesthesia AI", min_year=2024, output_format="json")
  → 找到 30 篇候選文獻

2. zotero-keeper: check_articles_owned([...pmids...])
  → 找出哪些 PMID 已經在本地 Zotero

3. zotero-keeper: import_articles(articles=selected_articles, collection_name="AI Research")
  → 匯入選定文獻，保留 abstract、作者、DOI 與引用指標

你: 收到！Zotero 已經有 25 篇新論文了
```

### 安裝可選的 keeper 本地 PubMed bridge

預設的 collaboration-safe 模式，是讓 keeper 與獨立的 pubmed-search-mcp server 協作。只有當你真的需要 keeper 內建的舊版本地 PubMed bridge 時，才安裝這個 extra：

```bash
cd mcp-server
uv sync --extra pubmed
```

---

## 🌐 遠端 Zotero 設定

如果 Zotero 在另一台電腦：

### 1. 在 Zotero 電腦執行 (Windows)

```powershell
# 開啟 Local API (在 Zotero → 工具 → 開發者 → Run JavaScript)
Zotero.Prefs.set("httpServer.localAPI.enabled", true)

# 開啟防火牆
netsh advfirewall firewall add rule name="Zotero" dir=in action=allow protocol=TCP localport=23119

# 設定 Port Proxy (Zotero 只聽 127.0.0.1)
netsh interface portproxy add v4tov4 listenaddress=0.0.0.0 listenport=23119 connectaddress=127.0.0.1 connectport=23119
```

### 2. 設定 MCP Server

```json
{
  "env": {
    "ZOTERO_HOST": "192.168.1.100",
    "ZOTERO_PORT": "23119"
  }
}
```

---

## 🏗️ 架構圖

```
┌────────────────────────────┐    ┌────────────────────────────┐
│     pubmed-search-mcp      │    │       zotero-keeper       │
│   (搜尋 / 探索 / 匯出)      │    │  (本地 Zotero 管理 / 匯入) │
│                            │    │                            │
│  • unified_search          │───▶│  • check_articles_owned    │
│  • fetch_article_details   │    │  • list_collections        │
│  • prepare_export          │    │  • import_articles         │
│  • parse_pico              │    │  • interactive_save        │
│  • get_citation_metrics    │    │  • quick_save              │
└────────────────────────────┘    └──────────────┬─────────────┘
                                                 │
                                                 ▼
                                    ┌────────────────────────────┐
                                    │    Zotero Desktop Client   │
                                    │  Local API + Connector API │
                                    └────────────────────────────┘
```

預設公開面是 collaboration-safe：

- pubmed-search-mcp 負責搜尋、探索、匯出與引用指標
- keeper 負責本地書庫查詢、collection 選擇、重複檢查與匯入
- 舊版 keeper PubMed bridge 工具只在 `ZOTERO_KEEPER_ENABLE_LEGACY_PUBMED_TOOLS=1` 時才會註冊

---

## ⚠️ Zotero API 限制（重要！）

### API 能力矩陣

Zotero 提供**兩個本地 API**，但都不支援完整的 CRUD：

| API | 端點 | 讀取 | 新增 | 更新 | 刪除 |
|-----|------|:----:|:----:|:----:|:----:|
| **Local API** | `/api/...` | ✅ | ❌ | ❌ | ❌ |
| **Connector API** | `/connector/...` | ❌ | ✅ | ❌ | ❌ |

### 🔍 技術細節

**Local API** (port 23119):
- 設計用於讀取 Zotero 資料（文獻、收藏夾、標籤）
- 根據[官方原始碼](https://github.com/zotero/zotero/blob/main/chrome/content/zotero/xpcom/server/server_localAPI.js#L28-L43)：**"Write access is not yet supported."**
- DELETE/PATCH/PUT 方法回傳 `501 Not Implemented`

**Connector API** (port 23119):
- 設計用於瀏覽器擴充功能**儲存新項目**
- `saveItems` 端點：**永遠建立新項目，不會更新既有項目**
- 即使匯入相同 PMID 兩次 → 會建立重複項目
- 沒有 `updateItem` 或 `deleteItem` 端點

### 🔴 無法執行的操作

| 操作 | API 支援 | 技術原因 |
|------|---------|----------|
| ❌ **刪除文獻** | 501 Not Implemented | Local API 唯讀 |
| ❌ **更新文獻** | 501 Not Implemented | Local API 唯讀 |
| ❌ **移動文獻到收藏夾** | 無法操作 | Connector API 只能新增，不能更新 |
| ❌ **為既有文獻加標籤** | 無法操作 | 沒有更新端點 |
| ❌ **建立 Collection** | 400 Bad Request | Connector API 不支援 |
| ❌ **刪除 Collection** | 501 Not Implemented | Local API 唯讀 |
| ❌ **合併重複** | 無 API | 必須使用 Zotero GUI |

### 💡 這意味著什麼？

**「智慧管理」的限制**：

```
❌ 無法做到：
- 「把這 10 篇文獻移到另一個收藏夾」
- 「刪除所有重複的文獻」  
- 「幫我整理收藏夾」
- 「把舊文獻移到 Archive」

✅ 可以做到：
- 「新增文獻時指定收藏夾」（新增時指定）
- 「搜尋符合條件的文獻」（然後手動處理）
- 「列出可能重複的文獻」（但需手動刪除）
```

### 🛠️ 替代方案

| 需求 | 替代做法 |
|------|----------|
| 整理收藏夾 | 使用 Zotero GUI 拖拉文獻 |
| 刪除重複 | Zotero → 工具 → 「合併重複項目」 |
| 批次操作 | 使用 [Zotero Actions & Tags](https://github.com/windingwind/zotero-actions-tags) 外掛 |
| 自動分類 | 使用 [Zutilo](https://github.com/wshanks/Zutilo) 外掛 |

### 🔮 未來可能性

Zotero 團隊正在開發 **Local API 寫入功能**：
- [GitHub Issue #1320](https://github.com/zotero/zotero/issues/1320) - 請求寫入支援
- 預計在 Zotero 後續版本加入 (8.x+)

**當 Zotero 支援後，我們會立即更新 zotero-keeper！**

---

### 🌟 Local API 獨家功能：執行 Saved Search

| API | 執行 Saved Search |
|-----|------------------|
| Web API (api.zotero.org) | ❌ 只能讀取條件 |
| **Local API** | ✅ 可以執行並取得結果！ |

**推薦的 Saved Search**（建立一次，永久使用）：

| 名稱 | 條件 | AI 問法 |
|------|------|--------|
| Missing PDF | Attachment File Type is not PDF | 「哪些論文沒 PDF？」 |
| Missing DOI | DOI is empty | 「哪些缺 DOI？」 |
| Recent | Date Added in last 7 days | 「這週新增了什麼？」 |
| Unread | Tag is not "read" | 「還沒讀的有哪些？」 |
| Duplicates | 標題相似 | 「可能重複的文獻？」 |

---

## 📦 安裝與發佈路徑

目前已同時提供開發者導向與研究者導向的入口，後續再逐步補齊更簡化的封裝方式。

| 路徑 | 狀態 | 適合對象 |
|------|------|----------|
| VS Code 擴充功能 | ✅ 已提供 | 想在 VS Code 內走引導式安裝的研究者 |
| 原始碼 checkout + `uv sync` | ✅ 已提供 | 貢獻者與本地開發 |
| 直接用 `uvx zotero-keeper` 註冊 MCP | ✅ 已提供 | 已有 MCP client 的使用者 |
| 獨立執行檔 | 🚧 規劃中 | 不想自行安裝 Python / uv 的使用者 |
| Homebrew / Chocolatey | 🚧 規劃中 | 偏好 OS 套件管理器的使用者 |

> 💡 想幫忙改善安裝體驗？請參考 [CONTRIBUTING.md](CONTRIBUTING.md)。

---

## 🤔 常見問題

### ❓ 連不上 Zotero？

1. 確認 Zotero 有執行
2. 測試連線：`curl http://127.0.0.1:23119/connector/ping`
3. 應該要回傳：`Zotero is running`

### ❓ 找不到 MCP Server？

1. 確認路徑正確 (用絕對路徑)
2. 確認 Python 環境正確
3. 重啟 VS Code / Claude Desktop

### ❓ PubMed 功能沒出現？

```bash
cd mcp-server
uv sync --extra pubmed
```

---

## 📚 相關資源

- [CHANGELOG](CHANGELOG.md) - 版本更新記錄
- [ARCHITECTURE](ARCHITECTURE.md) - 技術架構
- [CONTRIBUTING](CONTRIBUTING.md) - 貢獻指南
- [ROADMAP](ROADMAP.md) - 開發路線圖
- [pubmed-search-mcp](https://github.com/u9401066/pubmed-search-mcp) - PubMed 搜尋 (Apache 2.0)

---

## 🤝 貢獻

歡迎貢獻！請閱讀 [CONTRIBUTING.md](CONTRIBUTING.md)。

- 🐛 [回報 Bug](https://github.com/u9401066/zotero-keeper/issues)
- 💡 [功能建議](https://github.com/u9401066/zotero-keeper/issues)
- 🔧 [發送 PR](https://github.com/u9401066/zotero-keeper/pulls)

---

## 📄 授權

Apache 2.0 - 詳見 [LICENSE](LICENSE)

---

<p align="center">
  Made with ❤️ for researchers<br>
  讓 AI 幫你管理文獻，專注在研究上！
</p>
