# System Patterns

> 🏗️ 專案中使用的架構模式和設計模式

## DDD 分層架構 (符合憲法第 1 條)

```
zotero-keeper/mcp-server/src/zotero_mcp/
├── domain/
│   └── entities/                  # Reference, Collection, BatchResult
├── infrastructure/
│   ├── zotero_client/             # Local API + Connector DAL
│   │   ├── client_base.py
│   │   ├── client_read.py
│   │   └── client_write.py
│   ├── mappers/
│   │   ├── pubmed_mapper.py       # PubMed/UnifiedArticle → Zotero
│   │   └── zotero_schema.py       # item-type-aware field guard
│   ├── pubmed/__init__.py         # v0.6.1 public client adapter
│   └── mcp/
│       ├── server.py              # SDK v2 MCPServer assembly
│       ├── *_tools.py             # 24 default tools
│       └── resources.py           # 6 resources
└── main.py                        # transport entrypoint
```

## pubmed-search-mcp v0.6.1 架構

```
external/pubmed-search-mcp/src/pubmed_search/
├── domain/                        # article/chronicle/pipeline entities
├── application/
│   ├── search/                    # query, rank, aggregate, reproducibility
│   ├── session/                   # durable tenant-scoped artifacts
│   ├── fulltext/                  # source registry and extraction
│   ├── pipeline/                  # reusable research pipelines
│   └── chronicle/                 # build/read Research Chronicle
├── infrastructure/
│   ├── ncbi/                      # PubMed, iCite, citation export
│   ├── sources/                   # Europe PMC/OpenAlex/etc.
│   ├── auth/                      # service credentials
│   └── scheduling/                # background pipeline scheduler
└── presentation/mcp_server/
    ├── server.py                  # SDK v2 MCPServer; local/service modes
    ├── tool_registry.py           # 45-tool public registry
    ├── tenancy.py / auth.py       # caller identity boundaries
    └── tools/                     # search, discovery, export, chronicle, ...
```

Submodule 與 VSIX installer 都固定到 v0.6.1 commit
`ad85dde08269dbb59eff69d2e92f4d3c5b5bf21d`。Research Chronicle 的兩個
公開 tools 取代舊 timeline tool surface；內部 timeline domain/application 元件仍可
作為 chronicle 的分析實作，不代表舊工具仍應暴露給 agent。

## 設計模式

### 1. Repository / DAL Pattern
- `zotero_client/client_read.py` 封裝 Local API 讀取
- `zotero_client/client_write.py` 封裝 Connector 寫入與附件上傳
- Local/Connector 以 Zotero Desktop loopback 為信任邊界，不需要 Web API key

### 2. Mapper + Schema Guard Pattern
- `pubmed_mapper.py` 隔離 PubMed / `UnifiedArticle` 格式
- `zotero_schema.py` 依 Zotero item type 過濾欄位，無法原生容納的 metadata
  保存到 `Extra`，避免 Connector 靜默遺失

### 3. Collaboration-safe Handoff Pattern
- PubMed Search 擁有 discovery、enrichment、full text、pipeline、session 與 export
- Keeper 擁有 local inspection、duplicate check、collection selection 與 persistence
- 標準流程：`unified_search` → `check_articles_owned` → `import_articles`
- 不重新公開重疊的 legacy PubMed bridge tools，除非顯式啟用 compatibility mode

### 4. Durable Session + Chronicle Pattern
- Session 保存 PMIDs、cached articles、summary 與可稽核 artifacts，避免 agent
  context 壓縮造成狀態遺失
- Research Chronicle 從持久化研究 artifacts 建立可重讀的演進紀錄，而不是要求
  agent 重跑查詢或依賴對話記憶

### 5. Atomic Managed Package-set Pattern
- MCP SDK v1/v2 不相容；Keeper `2.0.0` 和 PubMed `0.6.1` 共同約束
  `mcp>=2,<3`
- VSIX `0.6.0` 將兩個 fixed-source distributions 交給同一 resolver install，完成
  後一起檢查 version、`direct_url.json`、install state 及 server tool listing
- 升級前停止 managed venv 中的舊 MCP processes；任何一步失敗都不得把半升級
  環境標記 ready

### 6. Security-boundary Pattern
- **local/Connector**：stdio + loopback Zotero Desktop，collection/import 行為仍遵守
  user confirmation guardrails
- **authenticated service**：遠端 HTTP 必須顯式設定 token、tenant identity、bind
  host、Host/Origin 驗證與 tenant-specific data directory
- 截至 2026-08-11，Zotero 官方組織未發布 MCP server；Registry 收錄的
  `54yyyu/zotero-mcp` 是社群 implementation。因其與 Keeper 共用 `zotero_mcp`
  Python namespace，只能用另一個 venv，不能作為 managed package set 的第三套件

## VS Code Extension 架構

```
vscode-extension/
├── src/
│   ├── extension.ts               # activation
│   ├── mcpProvider.ts             # two MCP definitions
│   ├── uvPythonManager.ts         # bundled uv + managed venv
│   ├── pythonEnvironment.ts       # custom/system Python → managed venv
│   ├── zoteroKeeperPackage.ts     # Keeper 2.0.0 pin
│   ├── pubmedSearchPackage.ts     # PubMed 0.6.1 commit pin
│   └── statusBar.ts
└── resources/
    ├── repo-assets/               # synchronized assistant harness
    └── walkthrough/
```

## 命名慣例 (符合子法第 4 條)

| 類型 | 模式 | 範例 |
|------|------|------|
| Entity | 名詞單數 | `Reference`, `Collection` |
| Tool | 動詞_名詞 | `search_items`, `import_articles` |
| Mapper | {Source}Mapper | `PubmedMapper` |
| Config | {Module}Config | `McpServerConfig` |
| Server | SDK v2 concrete type | `MCPServer` |

---
*Updated: 2026-08-11*
*符合: CONSTITUTION.md, bylaws/ddd-architecture.md*
