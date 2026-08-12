# Architecture Document

> 🏗️ 系統架構設計文件

## 架構總覽

```
┌─────────────────────────────────────────────────────────────────┐
│                        VS Code Extension                         │
│               (vscode-zotero-mcp v0.7.0 release)               │
│       one managed venv / one MCP SDK v2 package set             │
└──────────────────────────────┬──────────────────────────────────┘
                               │ MCP Protocol (stdio)
           ┌───────────────────┴───────────────────┐
           ▼                                       ▼
┌──────────────────────┐              ┌──────────────────────┐
│ zotero-keeper 2.1.0  │              │ pubmed-search 0.6.1 │
│ 32 tools/6 resources │◄────────────►│       45 tools       │
│ SDK v2 MCPServer     │ UnifiedArticle│ SDK v2 MCPServer     │
└──────────┬───────────┘   handoff     └──────────┬───────────┘
           │                                      │
           ▼                                      ▼
┌──────────────────────┐              ┌──────────────────────┐
│ Zotero Local API +   │              │ NCBI + biomedical   │
│ Connector :23119     │              │ literature sources  │
└──────────────────────┘              └──────────────────────┘
```

兩個 MCP servers 的預設協作發生在 agent/tool contract 層，並非互相控制對方：
PubMed Search 產生 citation-ready / `UnifiedArticle` 資料；Keeper 先檢查本地擁有
狀態與 collection，再執行持久化。

## DDD 分層架構 (符合憲法第 1 條)

### 1. Domain Layer (核心層)

```
domain/
└── entities/
    ├── reference.py      # 文獻參考實體
    ├── collection.py     # 收藏夾實體
    └── batch_result.py   # 批次結果實體
```

**責任**:
- 定義核心業務實體
- 實作業務邏輯和驗證規則
- 不依賴任何外部套件

### 2. Infrastructure Layer (基礎設施層)

```
infrastructure/
├── zotero_client/
│   ├── client.py         # read/write facade
│   ├── client_base.py    # transport/configuration
│   ├── client_read.py    # Local API reads
│   ├── client_write.py   # Zotero 7–9 compatible Connector writes
│   └── client_local.py   # Zotero 10+ authorized Local API writes
├── mappers/
│   ├── pubmed_mapper.py  # PubMed → Zotero 映射
│   └── zotero_schema.py  # type-aware Zotero schema guard
├── pubmed/
│   └── __init__.py       # PubMed v0.6.1 PubMedSearchClient adapter
└── mcp/
    ├── server.py         # MCP SDK v2 MCPServer assembly
    ├── basic_read_tools.py / search_tools.py
    ├── collection_tools.py / saved_search_tools.py
    ├── attachment_tools.py / analytics_tools.py
    ├── local_api_tools.py # 8 guarded Local API tools
    ├── unified_import_tools.py # handoff + import_pdf
    ├── interactive_tools.py / batch_tools.py
    └── resources.py      # 6 MCP resources
```

## 待重構清單 (違反 bylaws/ddd-architecture.md 第 3 條)

| 檔案 | 行數 | 優先級 | 拆分建議 |
|------|------|--------|----------|
| `unified_import_tools.py` | 1067 | P1 | → import orchestration + PDF + RIS modules |
| `pubmed_tools.py` | 526 | P2 | legacy-only bridge 可再拆分或移除 |
| `interactive_tools.py` | 489 | P2 | → validation + duplicate/save workflow |
| `batch_tools.py` | 401 | P3 | → add + validate modules |

`client.py`、`server.py` 與 `search_tools.py` 的早期拆分工作已完成；上表保留目前
仍超過 400 行的實際 hotspots，不回寫舊行數。

## 架構決策

### ADR-001: 使用 FastMCP 框架（歷史，已由 ADR-005 取代）
- **原決策**: 使用 SDK v1 FastMCP 而非手動實作 MCP
- **原理由**: 簡化 tool 定義，自動處理協定
- **狀態**: SDK v1 與 v2 不相容；Keeper `2.0.0` 起不再使用此 API 名稱

### ADR-002: DDD 分層但不過度
- **決策**: 簡化 DDD，省略 Application Service 層
- **理由**: 專案規模不大，避免過度工程化

### ADR-003: PubMed Mapper 置於 Infrastructure
- **決策**: `pubmed_mapper.py` 放在 infrastructure/mappers
- **理由**: 負責外部 API 資料格式轉換，非核心業務邏輯

### ADR-004: 優先使用 uv
- **決策**: 使用 uv 管理 Python 環境 (符合 bylaws/python-environment.md)
- **理由**: 更快的套件安裝速度，更好的鎖定機制

### ADR-005: MCP SDK v2 `MCPServer`
- **決策**: Keeper `2.0.0` 與 PubMed Search `0.6.1` 統一使用
  `mcp.server.MCPServer` 與 `mcp>=2,<3`
- **理由**: 共用 managed venv 無法安全混用 SDK v1/v2；server assembly、context
  與 tool registration 必須使用同一 major contract

### ADR-006: Extension-managed venv 是原子 package-set 邊界
- **決策**: VSIX `0.6.0` 將 Keeper 與 PubMed 的 pinned direct sources 放在同一
  resolver install 中，安裝後共同驗證版本、source 與 tool listing
- **理由**: 避免其中一套已升級、另一套仍依賴 SDK v1 的半升級環境

### ADR-007: Zotero MCP implementation 與安全模式隔離
- **決策**: Keeper local/Connector 與 authenticated HTTP service 使用不同安全
  假設；第三方 `54yyyu/zotero-mcp` 因同名 Python namespace 只能使用獨立環境
- **理由**: Registry 收錄不代表 Zotero 官方產品；loopback 無 Web API key 的
  desktop flow 也不能直接延伸到遠端 service

### ADR-008: Zotero 10+ Local API 寫入採 runtime authorization 與封閉工具面
- **決策**: Keeper `2.1.0` 先 discovery `/api/` 取得 Server-ID，再透過
  `/api/local/authorize` 取得只存於記憶體的 runtime key；所有 authorize/write
  requests 必須攜帶 Server-ID。對 agent 只公開 1 個 authorize tool 與 7 個需要
  `confirm=true` 的 collection/item/note/saved-search/file/full-text mutations，不公開
  任意 delete surface。
- **理由**: Zotero 10+ 現已支援本地寫入，但 desktop 授權不是長期 Web API
  credential；明確工具、local optimistic concurrency 與確認閘能在擴大功能時維持
  使用者選擇與資料安全。
- **相容性**: Zotero 7–9 繼續使用既有 Connector 匯入流程；新寫入 capability
  只在 Zotero 10+ discovery/authorization 成功後啟用。
- **安全限制**: `localhost:23119` 不得被 bind、proxy 或 forward 至其他主機；
  preview 前先取得 response-bound Server-ID，所有 confirmed mutation 都要求 proposal
  中已核准的 `expected_server_id`。item metadata 使用 response-bound object version；
  full-text 使用 library cursor 與 bulk `/fulltext` POST，不使用 attachment object
  version。若 authorization identity 不同，必須重新 read、preview 與取得核准。

`v0.6.0-ext` / Keeper `2.0.0` 已於 2026-08-11 完成 MCP v2 migration；
ADR-008 對應的 `v0.7.0-ext` / Keeper `2.1.0` 已於 2026-08-12 發布。

## 下一步架構改進

1. **監看 v0.7 release**: 追蹤 Zotero 10+ authorization、Server-ID 與 attachment
   upload 的實際相容性回饋
2. **拆分大檔案**: 依據上表拆分仍超過 400 行的檔案
3. **增加 Application Layer**: 如果匯入 orchestration 持續變複雜，考慮加入 services/
4. **Repository Pattern**: 在 Domain 和 Infrastructure 之間加入抽象

---
*Updated: 2026-08-12*
*符合: CONSTITUTION.md 第 1, 2 條*
