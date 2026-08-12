# Zotero Keeper 📚

讓 AI 幫你管理文獻！連接 VS Code Copilot / Claude Desktop 與本地 Zotero 書目資料庫。

[![Python 3.12+](https://img.shields.io/badge/python-3.12+-blue.svg)](https://www.python.org/downloads/)
[![MCP SDK](https://img.shields.io/badge/MCP%20SDK-v2-green.svg)](https://github.com/modelcontextprotocol/python-sdk)
[![License](https://img.shields.io/badge/license-Apache%202.0-blue.svg)](LICENSE)
[![Zotero 7/8/9/10+](https://img.shields.io/badge/Zotero-7%20%2F%208%20%2F%209%20%2F%2010%2B-red.svg)](https://www.zotero.org/)
[![CI](https://github.com/u9401066/zotero-keeper/actions/workflows/ci.yml/badge.svg)](https://github.com/u9401066/zotero-keeper/actions/workflows/ci.yml)

> 🌐 **[English](README.md)** | **繁體中文**

---

## 🚀 建議安裝方式 (VS Code)

> **前置作業**：必須先啟動 [Zotero 7、8、9 或 10+](https://www.zotero.org/download/)；新的授權式 Local API 寫入需要 Zotero 10+

[📦 從 VS Code Marketplace 安裝 Zotero + PubMed MCP](https://marketplace.visualstudio.com/items?itemName=u9401066.vscode-zotero-mcp)

**v0.7.0 VSIX 是目前建議的發佈管道**：擴充套件會建立隔離環境，並安裝 Zotero Keeper 2.1.0 與固定版的 PubMed Search MCP 0.6.1。`uvx` / PyPI 仍可用於舊版的直接 server 安裝，但在 PyPI 更新前，不應當作 2.1 版本來使用。

> ⚠️ MCP SDK 2.0 與 1.x 不相容。擴充套件升級後，若 VS Code 仍使用舊環境，請執行 **Zotero MCP: Reinstall Python Environment**。

---

## ✨ 這是什麼？

**Zotero Keeper** 是一個 [MCP 伺服器](https://modelcontextprotocol.io/)，讓你的 AI 助手可以：

- 🔍 **搜尋文獻**：「幫我找 2024 年關於 CRISPR 的論文」
- 📖 **查看細節**：「這篇文章的摘要是什麼？」
- ➕ **新增文獻**：「把這篇 DOI 加到我的 Zotero」（自動取得完整 metadata！）
- 🤝 **協作式 PubMed 工作流**：先用 pubmed-search-mcp 搜尋，再用 keeper 檢查重複與匯入
- 📁 **互動式存檔**：列出所有收藏夾讓你選擇！
- 🗂️ **Zotero 10+ 整理能力**：建立巢狀收藏夾、更新既有項目、建立子筆記，並把檔案附加到書庫中已存在的項目
- 📚 **現代化文獻發現**：PubMed Search MCP 0.6.1 提供 16 類、45 個工具，包含兩工具組成的 Research Chronicle 工作流程

不用自己開 Zotero、手動搜尋、複製貼上。直接用自然語言告訴 AI，它會幫你完成！

---

## ✨ 特色功能

- **🔌 MCP SDK 2.0 原生整合**：使用 v2 `MCPServer` API，不再依賴不相容的 1.x `FastMCP` 介面
- **📖 MCP Resources**：透過 URI 瀏覽 Zotero 資料（`zotero://collections` 等）
- **💬 MCP Elicitation**：使用精確 collection key 做互動式選擇；`ROOT` 一定會再確認一次
- **🔒 自動取得 Metadata**：DOI/PMID → 自動取得完整摘要 + 所有欄位！
- **📖 讀取操作**：搜尋、列出、取得本地 Zotero 書目資料
- **✏️ 寫入操作**：Zotero 7–9 保留 Connector 匯入；Zotero 10+ 使用執行時授權的 Local API 寫入
- **🧠 智慧功能**：重複偵測、參考文獻驗證、智能匯入
- **📁 Collection 支援**：支援巢狀收藏夾（資料夾層級結構）
- **🏗️ DDD 架構**：乾淨的領域驅動設計，洋蔥式架構
- **🔒 Zotero 本機邊界**：Zotero 資料庫操作只走本機 loopback API；PubMed
  文獻探索則使用已設定的外部文獻 API

---

## 🚀 快速開始

### 你需要準備

- ✅ [Python 3.12+](https://www.python.org/downloads/)
- ✅ [Zotero 7、8、9 或 10+](https://www.zotero.org/download/)（要先執行；Local API 寫入需 10+）
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
- [docs/COLLABORATION_WORKFLOW.md](docs/COLLABORATION_WORKFLOW.md) — pubmed-search-mcp 與 keeper 的 collaboration-safe 工作流
- [docs/tools-reference.md](docs/tools-reference.md) — 公開工具參數與使用範例總表
- [docs/faq.md](docs/faq.md) — 安裝、疑難排解與工作流 FAQ
- [docs/ZOTERO_LOCAL_API.md](docs/ZOTERO_LOCAL_API.md) — Zotero API 能力與限制整理
- [docs/ZOTERO_MCP_LANDSCAPE.md](docs/ZOTERO_MCP_LANDSCAPE.md) — 官方與社群 MCP 的定位、能力與安全共存方式
- [ARCHITECTURE.md](ARCHITECTURE.md) — 元件與分層架構
- [CONTRIBUTING.md](CONTRIBUTING.md) — 開發與貢獻流程

---

## 🔧 可用工具 (預設公開面 32 個 + legacy opt-in 5 個)

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

### 🗂️ Zotero 10+ Local API 工具 (local_api_tools.py - 8 工具)

這組工具使用 Zotero 官方 Local API v3 寫入功能。preview 前先由 Local API
read 或 `authorize_local_writes` 取得 response-bound `server_id`，並以
`expected_server_id` 放進 proposal。key 只留在 Keeper process 內，不會經由
MCP 回傳；所有寫入僅限 loopback，並綁定已審核的 Zotero Server-ID。

| 工具 | 說明 | 安全邊界 |
|------|------|----------|
| `authorize_local_writes` | 請 Zotero 授權 Keeper；檔案上傳前使用 `require_remembered=true` | 絕不回傳或記錄 key |
| `create_collection` | 建立頂層或巢狀收藏夾 | 精確 parent key + 明確確認 |
| `add_items_to_collection` | 把最多 50 個既有項目加入收藏夾，保留原有歸屬 | 寫入前驗證全部 key，再做一次版本化 batch |
| `update_item_fields` | 更新允許的純量 metadata | 必須提供目前 local object version |
| `create_note` | 在既有項目下建立子筆記 | 驗證 parent + 明確確認 |
| `create_saved_search` | 建立 Zotero saved search | 結構化條件 + 明確確認 |
| `attach_file_to_item` | 把本機檔案附加到既有項目 | remembered authorization + 驗證 loopback upload URL |
| `set_attachment_fulltext` | 寫入 attachment 的索引文字 | response-bound library cursor + Server-ID + 明確確認 |

Zotero 7–9 無法使用這些操作，並繼續使用現有 Connector 匯入
路徑。Keeper 刻意不公開任意 raw PATCH 或通用破壞性 DELETE 工具。

每個 mutation 都要在 `confirm=false` proposal 中先放入
`expected_server_id`；有版本條件時，還要放入同一 response 綁定的 item object
version 或 full-text library cursor，才請使用者核准。若後續 authorization 回傳
不同 identity，必須丟棄 proposal、重新 read、preview 與取得核准，不能在
preview 後才補 identity。`confirm=true` 必須原樣重送已核准 proposal，且不得
自動重試 412。

### ✏️ 存檔工具 (interactive_tools.py - 2 工具)

> 📊 **RCR 自動取得**：當提供 PMID 時，預設會自動從 iCite 取得 Relative Citation Ratio 並存入 Zotero extra 欄位

| 工具 | 說明 | 範例問法 |
|------|------|----------|
| `interactive_save` ⭐ | 互動式存檔 + 自動 RCR | 「把這篇存到 Zotero」 |
| `quick_save` | 快速存檔 + 自動 RCR | 「快速存到 AI Research」 |

所有存檔路徑都採 fail-closed。`interactive_save` 要求精確 collection key（或明確的 `ROOT` sentinel）；選 `ROOT` 後還會再確認一次。`skip_collection_prompt=True` 會中止，不會靜默存入 library root。`quick_save`、`import_articles` 與 `import_pdf` 在沒有 collection 時預設拒絕；只有使用者已明確確認 root，且 caller 傳入 `allow_library_root=true` 才會執行。

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

### 📥 匯入工具 (2 個)

> 🤝 **collaboration-safe 預設**：PubMed 搜尋、探索與匯出由 pubmed-search-mcp 負責；Zotero Keeper 提供單一公開匯入入口 `import_articles`。

| 工具 | 說明 | 範例問法 |
|------|------|----------|
| `import_articles` ⭐ | 單一公開匯入入口，可接 JSON articles 或 RIS 文字 | 「把這批 PubMed 結果存到 AI Research」 |
| `import_pdf` 📎 | 透過 Zotero Connector 匯入本機 PDF，可提供 metadata 或讓 Zotero 自動辨識 | 「匯入這份 PDF 並掛到文章」 |

### 📊 分析工具 (analytics_tools.py - 2 工具)

| 工具 | 說明 | 範例問法 |
|------|------|----------|
| `get_library_stats` | 顯示年份 / 作者 / 期刊統計 | 「顯示我的文獻庫統計」 |
| `find_orphan_items` | 找出未放入收藏夾的文獻 | 「哪些文獻還沒整理？」 |

### 📎 附件工具 (attachment_tools.py - 2 工具)

> 🗂️ **PDF 存取**：Zotero 10+ 會透過官方 Local API 解析附件路徑；`ZOTERO_DATA_DIR` 只保留給舊版 Zotero 或 view URL 不可用時作為 fallback。

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
pmids = [article.get("identifiers", {}).get("pmid") for article in results["articles"]]
owned = check_articles_owned(pmids=[pmid for pmid in pmids if pmid])

# 3. 匯入到 Zotero
import_articles(
  articles=results["articles"],
  collection_name="AI Research"
)
```

### 🤝 collaboration-safe 設定摘要

- pubmed-search-mcp 負責搜尋 / 探索 / 匯出，zotero-keeper 只處理重複檢查與單一 `import_articles` 匯入。
- 確保已安裝 pubmed-search-mcp 或同步 submodule；若使用本地原始碼可設定 `PUBMED_SEARCH_PATH`。
- 除非真的需要，請不要開啟 legacy PubMed 工具（需設定 `ZOTERO_KEEPER_ENABLE_LEGACY_PUBMED_TOOLS=1`）。
- 完整檢查清單請見 `docs/COLLABORATION_WORKFLOW.md`。

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

SDK v2 server 會公告 6 個具體 resource，另有 4 個參數化 URI template，用於個別文獻、collection、collection 內容與 saved search。

### 具體 resources (6)

| Resource URI | 說明 |
|--------------|------|
| `zotero://collections` | 所有收藏夾 |
| `zotero://collections/tree` | 收藏夾樹狀結構 |
| `zotero://items` | 最近的文獻 |
| `zotero://tags` | 所有標籤 |
| `zotero://searches` | Saved Search 列表 |
| `zotero://schema/item-types` | 可用的文獻類型 |

### 參數化 resource templates (4)

| Resource template | 說明 |
|-------------------|------|
| `zotero://collections/{key}` | 特定收藏夾 |
| `zotero://collections/{key}/items` | 收藏夾內的文獻 |
| `zotero://items/{key}` | 文獻詳情 |
| `zotero://searches/{key}` | Saved Search 詳情 |

---

## 🎯 互動式存檔（推薦！）

`interactive_save` 使用 **MCP Elicitation** 技術，會列出所有收藏夾讓你選擇：

```
你：「把這篇 DOI:10.1234/example 的論文存到 Zotero」

[MCP Elicitation 彈出]
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📚 Saving: Deep Learning for Medical Imaging

⭐ 推薦:
   AI Research — key `A1B2C3D4` (匹配度: 90%)
   Medical Imaging — key `M5N6P7Q8` (匹配度: 75%)

📂 所有收藏夾:
   Biology — key `B1O2L3O4` (12 items)
   Chemistry — key `C5H6E7M8` (8 items)
   待讀 — key `T1O2R3E4` (23 items)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

輸入精確 collection key 或 `ROOT`: [用戶輸入: A1B2C3D4]

AI: ✅ 已存入 'AI Research' 收藏夾！
```

`ROOT` 不是預設快捷選項。選擇後必須通過第二次確認；拒絕或跳過 prompt 都會中止。

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

v0.7.0 VSIX 固定使用 [pubmed-search-mcp 0.6.1](https://github.com/u9401066/pubmed-search-mcp/tree/v0.6.1)（commit `ad85dde`）。它的 MCP SDK v2 server 提供 **16 類、45 個工具**；新的 `build_research_chronicle` 與 `read_research_chronicle` 取代了早期 3 個 timeline 工具。

```
你: 「幫我找 2024 年麻醉 AI 的新論文，我還沒有的」

AI 執行:
1. pubmed-search-mcp: unified_search("anesthesia AI", filters="year:2024-", output_format="json")
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

### Zotero MCP 生態定位

截至 2026-08-12，未在 Zotero 組織的 repository 或 Zotero 官方文件找到由 Zotero 發佈的官方 MCP server。[`54yyyu/zotero-mcp`](https://github.com/54yyyu/zotero-mcp) 功能完整，且已收錄於 MCP Registry，但它是**社群 server**，不是 Zotero 官方 server。OpenAI-curated Zotero connector 也是獨立的 connector 產品，不應被寫成 Zotero 官方 MCP server，也不應在沒有可驗證介面時杜撰 tool schema。

社群 server 與 Zotero Keeper 都使用 Python module/package 名 `zotero_mcp`。若要並用，必須安裝到**不同虛擬環境、以不同 MCP process 啟動**；不要把社群 package 加入擴充套件管理的共用環境。詳見 [MCP 生態比較](docs/ZOTERO_MCP_LANDSCAPE.md)。

---

## 🌐 遠端 Zotero 存取

Zotero Local API 讀取與 Connector endpoints 是本機介面；Zotero 10+ 的
Local API 寫入雖加入執行時授權，但取得的 key 沒有細粒度 scope。因此
23119 port 仍必須只綁定 loopback，請勿暴露或轉送到 LAN / Internet。

遠端書庫請使用 Zotero 有身分驗證的 HTTPS Web API，或使用具 TLS、授權與網路存取控制的專用服務。如果要使用 Local/Connector 操作，請讓 Zotero Keeper 與 Zotero Desktop 在同一台可信任主機執行。

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
                                    │ Local API read/write (10+) │
                                    │ + Connector legacy create │
                                    └────────────────────────────┘
```

預設公開面是 collaboration-safe：

- pubmed-search-mcp 負責搜尋、探索、匯出與引用指標
- keeper 負責本地書庫查詢、collection 選擇、重複檢查與匯入
- 舊版 keeper PubMed bridge 工具只在 `ZOTERO_KEEPER_ENABLE_LEGACY_PUBMED_TOOLS=1` 時才會註冊

---

## ⚠️ Zotero API 能力與安全邊界

Zotero 10+ 已大幅升級 Local API：官方平台現在支援 items、collections、
saved searches 的授權式寫入、tag deletion、full-text write 與完整檔案
upload。Keeper 2.1 公開的是經過限制的安全子集，而不是把無 scope 的 key
與任意 API path 直接交給 AI client。

| 介面 | 範圍 | 身分驗證 | Keeper 2.1 用途 |
|------|------|----------|-----------------|
| **Local API v3** `/api/...` | 同機讀取；Zotero 10+ 寫入 | 讀取無認證；寫入需執行時由使用者同意 | Zotero 7–10+ 讀取；10+ guarded writes |
| **Connector API** `/connector/...` | browser-connector save flow | 本機介面 | 向後相容的建立／匯入路徑，包含 Zotero 7–9 |
| **Web API v3** `https://api.zotero.org` | 遠端與同步書庫 | zotero.org key / OAuth | 遠端存取建議路徑；本機 Keeper tools 不使用 |

Zotero 10+ 寫入前，Keeper 會先由 discovery/read 或 runtime authorization
取得 response-bound `Zotero-Server-ID`。該 identity 必須先出現在
`confirm=false` proposal，所有 confirmed mutation 都以
`expected_server_id` 帶回。`update_item_fields` 另使用同一 exact-item response
的 object version；full-text replacement 則使用 response-bound library cursor，
透過 bulk `POST /api/users/0/fulltext` 與
`If-Unmodified-Since-Version` 寫入，不使用 attachment object version。若
authorization 指向不同 database，read、preview 與 approval 必須全部重做。
資料庫變更或 stale cursor 回傳 `412` 時絕不靜默覆寫；缺少
identity/precondition (`428`) 與無效授權 (`401`) 也會 fail closed。

Keeper 2.1 已完成過去受限的高價值流程：

- 建立頂層或巢狀 collection；
- 把既有 items 加入已確認的 collection，同時保留原本歸屬；
- 更新既有 item 的允許 metadata，並建立 child note；
- 建立 saved search；
- 透過官方三階段 upload 把檔案附加到既有 item；
- 為 attachment 提供 indexed full text；以及
- 透過官方 Local API 取得 attachment path，不再只能猜測 Zotero data directory。

本版不公開通用刪除、任意 raw PATCH、duplicate merge、annotation edit 或
group-library write。破壞性維護仍請使用 Zotero UI。完整平台能力與 Keeper
較窄的安全 contract 請見 [docs/ZOTERO_LOCAL_API.md](docs/ZOTERO_LOCAL_API.md)。

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
| 直接用 `uvx zotero-keeper` 註冊 MCP | ⚠️ 舊 PyPI 版線 | 明確要使用 2.0 之前版本的 MCP client |
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
- [docs/tools-reference.md](docs/tools-reference.md) - 完整 MCP 工具參數參考
- [docs/faq.md](docs/faq.md) - 常見問題解答
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
