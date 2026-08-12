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
│   │   ├── client_write.py       # Zotero 7–9 compatible Connector writes
│   │   └── client_local.py       # Zotero 10+ authorized Local API writes
│   ├── mappers/
│   │   ├── pubmed_mapper.py       # PubMed/UnifiedArticle → Zotero
│   │   └── zotero_schema.py       # item-type-aware field guard
│   ├── pubmed/__init__.py         # v0.6.1 public client adapter
│   └── mcp/
│       ├── server.py              # SDK v2 MCPServer assembly
│       ├── local_api_tools.py     # 8 guarded Local API tools
│       ├── *_tools.py             # 32 default tools in total
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
- `zotero_client/client_local.py` 封裝 Zotero 10+ discovery、runtime authorization、
  Server-ID、local-version writes 與三階段 file upload
- Zotero 7–9 使用 Connector compatibility path；Zotero 10+ 才啟用 authorized
  Local API write capability

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
- MCP SDK v1/v2 不相容；Keeper `2.1.0` 和 PubMed `0.6.1` 共同約束
  `mcp>=2,<3`
- `v0.6.0-ext` / Keeper `2.0.0` 已於 2026-08-11 發布；VSIX `0.7.0`
  候選版仍將兩個 fixed-source distributions 交給同一 resolver install，完成
  後一起檢查 version、`direct_url.json`、install state 及 server tool listing
- 升級前停止 managed venv 中的舊 MCP processes；任何一步失敗都不得把半升級
  環境標記 ready

### 6. Security-boundary Pattern
- **local/Connector**：stdio + loopback Zotero Desktop；`localhost:23119` 不得
  bind、proxy 或 forward 給其他主機，collection/import 行為仍遵守 user
  confirmation guardrails
- **runtime local authorization**：key 僅存 process memory；discovery 取得的
  Server-ID 必須出現在 authorize 與每個 write request，不可把 desktop key 當作
  長期 Web API credential
- **authenticated service**：遠端 HTTP 必須顯式設定 token、tenant identity、bind
  host、Host/Origin 驗證與 tenant-specific data directory
- 截至 2026-08-11，Zotero 官方組織未發布 MCP server；Registry 收錄的
  `54yyyu/zotero-mcp` 是社群 implementation。因其與 Keeper 共用 `zotero_mcp`
  Python namespace，只能用另一個 venv，不能作為 managed package set 的第三套件

### 7. Guarded Local Mutation Pattern
- 對 agent 公開的 8 個 Local API tools 是 closed-world surface；不公開任意 delete，
  且 `confirm=false` 必須在任何 discovery/authorization/network I/O 之前 fail closed
- preview 的 `expected_server_id` 必須先來自 response-bound read/authorize；七個
  confirmed mutations 全部要求該 reviewed identity。authorization identity 若
  改變，就重新 read、preview 與取得核准，不能 preview 後補 identity
- item metadata update 使用 exact-item response-bound object version；full-text
  replacement 使用 response-bound library cursor 與 bulk
  `POST /api/users/0/fulltext`，不得替換成 attachment object version。Zotero Local API
  的 array PATCH 是完整 replacement，不可暗示 merge
- attachment upload 固定為 create attachment item → upload bytes with prefix/suffix →
  register `uploadKey` 三階段；後段失敗必須保留 attachment key 供人工恢復

### 8. Single Release-artifact Pattern
- release 流程先通過 version、managed install、tag-archive 與 Local API smoke；
  tag job 再 package VSIX 一次並對該具名檔執行 content inspection
- Marketplace publish 與 GitHub Release 都使用該同一檔案；publish 階段不得
  重新 package，避免已檢查內容與實際發布 artifact 漂移

## VS Code Extension 架構

```
vscode-extension/
├── src/
│   ├── extension.ts               # activation
│   ├── mcpProvider.ts             # two MCP definitions
│   ├── uvPythonManager.ts         # bundled uv + managed venv
│   ├── pythonEnvironment.ts       # custom/system Python → managed venv
│   ├── zoteroKeeperPackage.ts     # Keeper 2.1.0 pin
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
*Updated: 2026-08-12*
*符合: CONSTITUTION.md, bylaws/ddd-architecture.md*
