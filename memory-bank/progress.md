# Progress Tracking

## ✅ Completed (Done)

### v1.10.1 發布 (2025-12-16)
- [x] 一鍵安裝按鈕 (`vscode:mcp/install` URL)
- [x] `get_library_stats`: 文獻庫統計分析
- [x] `find_orphan_items`: 找出孤兒文獻
- [x] `quick_import_pmids`: 簡化 PubMed 匯入流程
- [x] 程式碼重構: server.py (586→202), basic_read_tools.py, collection_tools.py

### Phase 5: 重構大檔案 (2025-12-16)
- [x] `interactive_tools.py`: 816 → 499 行
  - 拆出 `metadata_fetcher.py` (219 行)
  - 拆出 `validation.py` (185 行)
  - 拆出 `collection_utils.py` (151 行)
- [x] `client.py`: 618 → 65 行 (主檔案)
  - 拆出 `client_base.py` (147 行)
  - 拆出 `client_read.py` (224 行)
  - 拆出 `client_write.py` (208 行)
- [x] `search_tools.py`: 604 → 312 行
  - 拆出 `search_helpers.py` (195 行)

### Bug Fixes (2025-12-15)
- [x] P0: 搜尋結果數量錯誤 - 修復 `total_count` 取得時機
- [x] P1a: Session Tools - 新增 4 個工具解決記憶體問題

### Template 整合 + MCP Skills 強化 (2025-12-22)
- [x] 導入 template-is-all-you-need 的 13 個 Skills
- [x] 強化 MCP tool descriptions（方案 1）
- [x] Extension 打包 Skills（方案 3）
- [x] 新增 `zoteroMcp.installSkills` 命令
- [x] 合併上一層 memory-bank 和研究文件

---

## 🔄 In Progress (Doing)

- [x] Template 導入 + MCP Skills 強化 (2025-12-22)

---

## 📋 Next (Planned)

### P1b: PubMed → Zotero RIS Direct Transfer
### P2: Collection Flow Improvement
### P3: Full-text / Impact Factor
### v1.11.0: 更多 analytics (重複檢測, 引用分析)

---

## 📊 Metrics

### Code Quality
| 指標 | 目標 | 現狀 |
|------|------|------|
| 超過 400 行的檔案 | 0 | 3 個 |
| 超過 200 行的檔案 | ≤5 | 13 個 |

---
*Updated: 2025-12-22*
