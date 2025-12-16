# Progress Tracking

## ✅ Completed (Done)

### Phase 1: Core MCP Server
- [x] 基礎 Zotero API 客戶端 (`client.py`)
- [x] 搜尋工具 (`search_tools.py`)
- [x] 批次工具 (`batch_tools.py`)
- [x] 智慧工具 (`smart_tools.py`)
- [x] PubMed 整合工具 (`pubmed_tools.py`)

### Phase 2: VS Code Extension
- [x] 擴充套件基礎架構
- [x] uv Python 環境管理
- [x] 發佈 v0.3.1 到 Marketplace

### Phase 3: Template Integration (2025-12-16)
- [x] 整合 memory-bank 架構
- [x] 加入 CONSTITUTION.md
- [x] 加入 bylaws (DDD, Git, Python, Memory Bank)
- [x] 加入 chatmodes

### Phase 4: P0-P1 Bug Fixes
- [x] P0: 修復 pubmed-search-mcp 搜尋計數錯誤
- [x] P1a: 實作 session tools (PMID 持久化)

---

## 🔄 In Progress (Doing)

### 專案整理 (根據 CONSTITUTION + bylaws)
- [x] 更新 systemPatterns.md
- [x] 分析檔案行數
- [ ] 重構超過 400 行的檔案
  - [ ] `interactive_tools.py` (816 行)
  - [ ] `client.py` (618 行)
  - [ ] `search_tools.py` (604 行)
  - [ ] `server.py` (586 行)
  - [ ] `batch_tools.py` (469 行)
  - [ ] `pubmed_tools.py` (433 行)
- [ ] 更新 architect.md

---

## 📋 Next (Planned)

### P1b: PubMed → Zotero RIS Direct Transfer
- [ ] 設計 RIS 匯入工具
- [ ] 實作 `import_from_pubmed` tool

### P2: Collection Flow Improvement
- [ ] 新增 collection 選擇流程
- [ ] batch add 前顯示 collection 列表

### P2: Abstract Priority from Zotero
- [ ] 修改 abstract 取得邏輯
- [ ] 優先從 Zotero cache 取得

### P3: Full-text Link Retrieval
- [ ] 自動取得 PMC/DOI 連結
- [ ] 整合到文獻詳情顯示

### P3: Impact Factor Alternative
- [ ] 整合 Scimago SJR
- [ ] 替代付費 Impact Factor

---

## 📊 Metrics

### Code Quality (bylaws/ddd-architecture.md)
| 指標 | 目標 | 現狀 |
|------|------|------|
| 檔案行數 | ≤200 (建議), ≤400 (硬限) | 6 檔案超標 |
| 模組複雜度 | <20 | 待評估 |
| 測試覆蓋率 | >80% | 待評估 |

---
*Updated: 2025-12-16*
