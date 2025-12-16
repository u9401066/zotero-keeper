# System Patterns

> 🏗️ 專案中使用的架構模式和設計模式

## DDD 分層架構 (符合憲法第 1 條)

```
zotero-keeper/mcp-server/src/zotero_mcp/
├── domain/                    # 領域層（核心）
│   └── entities/              # 實體
│       ├── reference.py       # 文獻參考實體
│       ├── collection.py      # 收藏夾實體
│       └── batch_result.py    # 批次結果實體
│
├── infrastructure/            # 基礎設施層
│   ├── zotero_client/         # Zotero API 客戶端
│   │   └── client.py          # HTTP 客戶端
│   ├── mappers/               # 資料映射器
│   │   └── pubmed_mapper.py   # PubMed → Zotero 映射
│   └── mcp/                   # MCP Server 實作
│       ├── server.py          # FastMCP server
│       ├── search_tools.py    # 搜尋工具
│       ├── smart_tools.py     # 智慧工具
│       └── batch_tools.py     # 批次工具
│
└── main.py                    # 入口點
```

## pubmed-search-mcp 架構

```
external/pubmed-search-mcp/src/pubmed_search/
├── entrez/                    # NCBI Entrez API 封裝
│   ├── search.py              # 搜尋功能
│   ├── strategy.py            # 搜尋策略生成
│   └── icite.py               # iCite 引用指標
│
├── mcp/                       # MCP Server
│   ├── server.py              # FastMCP server
│   ├── session_tools.py       # Session 管理工具
│   └── tools/                 # 工具模組
│       ├── discovery.py       # 搜尋/探索工具
│       └── strategy.py        # 策略工具
│
├── session.py                 # Session 持久化
└── exports/                   # 匯出格式
```

## 設計模式

### 1. Repository Pattern (DAL)
- `zotero_client/client.py` - 資料存取層
- 符合憲法第 2 條：DAL 獨立

### 2. Mapper Pattern
- `pubmed_mapper.py` - PubMed 到 Zotero 資料轉換
- 隔離外部 API 資料格式

### 3. Strategy Pattern
- `strategy.py` - 搜尋策略生成器
- 不同搜尋策略可互換

### 4. Session Pattern (P1a 改進)
- `session.py` - Session 狀態管理
- `session_tools.py` - Session PMID 持久化
- 解決 Agent 記憶滿載問題

## VS Code Extension 架構

```
vscode-extension/
├── src/
│   ├── extension.ts           # 入口點
│   ├── mcpProvider.ts         # MCP 連接管理
│   ├── uvPythonManager.ts     # uv 環境管理
│   ├── pythonEnvironment.ts   # Python 環境檢測
│   └── statusBar.ts           # 狀態列
│
└── resources/
    └── walkthrough/           # 引導頁面
```

## 命名慣例 (符合子法第 4 條)

| 類型 | 模式 | 範例 |
|------|------|------|
| Entity | 名詞單數 | `Reference`, `Collection` |
| Tool | 動詞_名詞 | `search_items`, `add_reference` |
| Mapper | {Source}Mapper | `PubmedMapper` |
| Config | {Module}Config | `McpConfig` |

---
*Updated: 2025-12-16*
*符合: CONSTITUTION.md, bylaws/ddd-architecture.md*
