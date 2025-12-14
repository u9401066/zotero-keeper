# Zotero Keeper 📚

讓 AI 幫你管理文獻！連接 VS Code Copilot / Claude Desktop 與本地 Zotero 書目資料庫。

[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![MCP SDK](https://img.shields.io/badge/MCP-FastMCP-green.svg)](https://github.com/modelcontextprotocol/python-sdk)
[![License](https://img.shields.io/badge/license-Apache%202.0-blue.svg)](LICENSE)
[![Zotero 7](https://img.shields.io/badge/Zotero-7.0+-red.svg)](https://www.zotero.org/)
[![CI](https://github.com/u9401066/zotero-keeper/actions/workflows/ci.yml/badge.svg)](https://github.com/u9401066/zotero-keeper/actions/workflows/ci.yml)

> 🌐 **[English](README.md)** | **繁體中文**

---

## ✨ 這是什麼？

**Zotero Keeper** 是一個 [MCP 伺服器](https://modelcontextprotocol.io/)，讓你的 AI 助手可以：

- 🔍 **搜尋文獻**：「幫我找 2024 年關於 CRISPR 的論文」
- 📖 **查看細節**：「這篇文章的摘要是什麼？」
- ➕ **新增文獻**：「把這篇 DOI 加到我的 Zotero」（自動取得完整 metadata！）
- 🔄 **整合 PubMed**：「搜尋 PubMed 並排除我已有的文獻」
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

- ✅ [Python 3.11+](https://www.python.org/downloads/)
- ✅ [Zotero 7](https://www.zotero.org/download/) (要先執行)
- ✅ [VS Code](https://code.visualstudio.com/) + GitHub Copilot，或 [Claude Desktop](https://claude.ai/)
- ✅ [uv](https://docs.astral.sh/uv/getting-started/installation/) 套件管理工具 (推薦)

### 三步驟安裝

```bash
# 1. 下載專案
git clone https://github.com/u9401066/zotero-keeper.git
cd zotero-keeper/mcp-server

# 2. 安裝
pip install -e .
# 或使用 uv:
uv pip install -e .

# 3. 測試連線 (先確認 Zotero 有開著)
python -m zotero_mcp
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
      "command": "python",
      "args": ["-m", "zotero_mcp"],
      "cwd": "/你的路徑/zotero-keeper/mcp-server"
    }
  }
}
```

---

## 🔧 可用工具 (共 21 個)

### 📖 讀取工具 (server.py - 11 工具)

| 工具 | 說明 | 範例問法 |
|------|------|----------|
| `check_connection` | 測試 Zotero 連線 | 「Zotero 有在執行嗎？」 |
| `search_items` | 搜尋文獻 | 「幫我找 CRISPR 的論文」 |
| `get_item` | 取得文獻詳情 | 「這篇文章 (key:ABC123) 的摘要」 |
| `list_items` | 列出文獻 | 「列出 AI Research 收藏夾的文獻」 |
| `list_collections` | 列出所有收藏夾 | 「我有哪些收藏夾？」 |
| `get_collection` | 取得收藏夾詳情 | 「AI Research 有幾篇文獻？」 |
| `get_collection_items` | 列出收藏夾內容 | 「列出 AI Research 的所有論文」 |
| `get_collection_tree` | 取得樹狀結構 | 「顯示收藏夾的階層結構」 |
| `find_collection` | 用名稱查找 | 「找出叫做 AI 的收藏夾」 |
| `list_tags` | 列出標籤 | 「我用過哪些標籤？」 |
| `get_item_types` | 取得文獻類型 | 「可以新增什麼類型？」 |

### ✏️ 存檔工具 (interactive_tools.py - 2 工具)

| 工具 | 說明 | 範例問法 |
|------|------|----------|
| `interactive_save` ⭐ | 互動式存檔（列出選項讓你選） | 「把這篇存到 Zotero」 |
| `quick_save` | 快速存檔（不詢問） | 「快速存到 AI Research」 |

### 🔍 Saved Search 工具 (saved_search_tools.py - 3 工具)

| 工具 | 說明 | 範例問法 |
|------|------|----------|
| `list_saved_searches` | 列出所有 Saved Search | 「有哪些儲存的搜尋？」 |
| `run_saved_search` | 執行 Saved Search | 「哪些論文還沒下載 PDF？」 |
| `get_saved_search_details` | 取得搜尋條件 | 「『缺少 PDF』的條件是什麼？」 |

### 🔬 PubMed 整合 (search_tools.py - 2 工具)

| 工具 | 說明 | 範例問法 |
|------|------|----------|
| `search_pubmed_exclude_owned` | 搜尋新文獻 | 「找 CRISPR 論文，排除我已有的」 |
| `check_articles_owned` | 檢查 PMID | 「這些 PMID 我有嗎？」 |

### 📥 匯入工具 (pubmed_tools.py - 2 工具, batch_tools.py - 1 工具)

| 工具 | 說明 | 範例問法 |
|------|------|----------|
| `import_ris_to_zotero` | 匯入 RIS 格式 | 「匯入這段 RIS」 |
| `import_from_pmids` | 用 PMID 匯入 | 「匯入 PMID 12345678」 |
| `batch_import_from_pubmed` | 批次匯入（完整 metadata） | 「匯入這些 PMID: 123,456,789」 |

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
1. search_pubmed_exclude_owned("anesthesia AI", min_year=2024)
   → 找到 30 篇，你已有 5 篇，回傳 25 篇新的

2. batch_import_from_pubmed(pmids="12345,67890,...")
   → 批次匯入，完整保留 abstract、作者、DOI

你: 收到！Zotero 已經有 25 篇新論文了
```

### 安裝 PubMed 整合

```bash
pip install -e ".[pubmed]"
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
┌─────────────────────────────────────────────────┐
│           AI Agent (VS Code / Claude)           │
└──────────────────────┬──────────────────────────┘
                       │ MCP Protocol
                       │ ├── Tools (21 個)
                       │ ├── Resources (10 個 URI)
                       │ └── Elicitation (互動輸入)
                       ▼
┌─────────────────────────────────────────────────┐
│              Zotero Keeper MCP Server           │
│  ┌───────────────────────────────────────────┐  │
│  │  MCP Layer                                │  │
│  │  ├── server.py (11 核心工具)              │  │
│  │  ├── resources.py (10 Resource URIs)      │  │
│  │  ├── interactive_tools.py (2 存檔工具)    │  │
│  │  ├── saved_search_tools.py (3 工具)       │  │
│  │  ├── search_tools.py (2 工具)             │  │
│  │  ├── pubmed_tools.py (2 工具)             │  │
│  │  ├── batch_tools.py (1 工具)              │  │
│  │  └── smart_tools.py (helpers only)        │  │
│  └───────────────────────────────────────────┘  │
└──────────────────────┬──────────────────────────┘
                       │ HTTP (port 23119)
                       ▼
┌─────────────────────────────────────────────────┐
│              Zotero Desktop Client              │
│  ├── Local API (/api/...) → 讀取              │
│  └── Connector API (/connector/...) → 寫入    │
└─────────────────────────────────────────────────┘
```

---

## ⚠️ Zotero API 限制

### Collection 建立限制

根據 [Zotero 官方原始碼](https://github.com/zotero/zotero/blob/main/chrome/content/zotero/xpcom/server/server_localAPI.js#L28-L43)：

> **"Write access is not yet supported."**

**無法透過 API 建立 Collection。** 請先在 Zotero 建立，再用 AI 分類。

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
pip install -e ".[pubmed]"
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
