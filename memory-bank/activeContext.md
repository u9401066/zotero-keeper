# Active Context

> 🎯 目前工作焦點與下一步行動

## 當前狀態: 專案整理完成 ✅

已根據 CONSTITUTION.md 和 bylaws 完成以下工作：

### 已完成 (2025-12-16)
1. ✅ 更新 `systemPatterns.md` - 記錄 DDD 分層架構
2. ✅ 更新 `architect.md` - 記錄架構狀態和待重構清單
3. ✅ 更新 `progress.md` - 追蹤完成和待辦事項
4. ✅ 更新 `decisionLog.md` - 記錄重要決策
5. ✅ 分析程式碼行數 - 識別 6 個超過 400 行的檔案

### 識別的問題
| 檔案 | 行數 | 違反 |
|------|------|------|
| `interactive_tools.py` | 816 | bylaws/ddd-architecture.md 第 3 條 |
| `client.py` | 618 | bylaws/ddd-architecture.md 第 3 條 |
| `search_tools.py` | 604 | bylaws/ddd-architecture.md 第 3 條 |
| `server.py` | 586 | bylaws/ddd-architecture.md 第 3 條 |
| `batch_tools.py` | 469 | bylaws/ddd-architecture.md 第 3 條 |
| `pubmed_tools.py` | 433 | bylaws/ddd-architecture.md 第 3 條 |

---

## 下一步選項

### Option A: 繼續重構 (Nice-to-have)
拆分超過 400 行的檔案，符合 bylaws 規範

### Option B: 實作 P1b (功能導向)
實作 PubMed → Zotero RIS 直接匯入

### Option C: 實作 P2 (使用者體驗)
改進 Collection 選擇流程

---

## 待確認
- [ ] 是否立即開始拆分大檔案？
- [ ] 還是先處理功能需求 (P1b/P2)？

---

## 快速指令

```bash
# 查看超過 200 行的檔案
find mcp-server/src -name "*.py" -exec wc -l {} \; | awk '$1>200'

# 執行測試
cd mcp-server && uv run pytest -v

# 啟動 MCP Server
cd mcp-server && uv run zotero-mcp
```

---
*Updated: 2025-12-16*
*工作模式: Architect*
