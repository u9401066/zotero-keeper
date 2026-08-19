# PubMed-Zotero 整合架構改進方案

> 基於 2025-12-15 使用者觀察回饋

> **歷史設計稿（已被取代）**：本頁保留當時的問題分析與舊工具名稱，
> 不代表 v0.6.0 / MCP SDK v2 現況。請以 [ARCHITECTURE.md](../ARCHITECTURE.md)、
> [協作流程](COLLABORATION_WORKFLOW.md) 與 PubMed Search MCP 0.6.3 的
> `get_session_log`、`read_session`、`build_research_chronicle`、
> `read_research_chronicle` 為準。

## 📋 問題清單與優先級

| 優先級 | 問題 | 狀態 | 影響 |
|--------|------|------|------|
| 🔴 P0 | 搜尋結果數量錯誤 | ✅ 已修復 | 可能漏掉文獻 |
| 🟠 P1a | PMID 暫存機制 | ✅ 已實作 | Agent 記憶滿載 |
| 🟠 P1b | PubMed → Zotero 直送 | 待設計 | 依賴 Agent 記憶 |
| 🟡 P2 | Collection 選擇流程 | 待設計 | 使用者體驗差 |
| 🟡 P2 | 摘要重複取回 | 待設計 | 浪費 API quota |
| 🟢 P3 | 全文連結檢索遺漏 | 待設計 | 功能不完整 |
| 🟢 P3 | IF 查詢機制 | 待評估 | 版權問題 |

---

## 🔴 P0: 搜尋結果數量錯誤 (已修復)

### 問題描述
`search_literature` 回報的總數可能不正確，導致使用者以為只有少量結果，實際上 PubMed 有更多符合條件的文獻。

### 根本原因
`discovery.py` 中的 metadata 清理邏輯有 bug：
```python
# 舊邏輯 - 有問題
if not any(k for k in results[0].keys() if not k.startswith("_")):
    results = results[1:] if len(results) > 1 else []
```

### 修復方案
```python
# 新邏輯 - 已修復
if len(results[0]) == 0 or (len(results[0]) == 1 and "error" not in results[0]):
    results = results[1:] if len(results) > 1 else []

# 並改進輸出訊息
if total_count is not None:
    if returned_count == 0:
        result = f"📊 PubMed 共有 **{total_count}** 篇符合條件，但無法取得詳細資料\n\n"
    elif total_count > returned_count:
        result = f"📊 Found **{returned_count}** results (of **{total_count}** total in PubMed)\n\n"
```

---

## 🟠 P1: PMID 暫存機制

### 問題描述
- `session.py` 有完整的 Session 和 Cache 實作
- 但 Agent (Copilot) 仍然依賴自己的上下文記憶來追蹤 PMID
- 當對話過長，記憶被壓縮/截斷時，PMID 列表遺失

### 現有機制
```
~/.pubmed-search-mcp/
├── sessions.json          # Session 索引
├── session_<id>.json      # 各 Session 資料
└── article_cache.json     # 文章快取
```

### ✅ 已實作解決方案 (2025-12-15)

#### 新增 Session 工具 (session_tools.py)

```python
# 1. get_session_pmids - 取得暫存的 PMID
get_session_pmids(search_index=-1)  # 最近一次
get_session_pmids(query_filter="BJA")  # 篩選特定搜尋

# 2. list_search_history - 列出搜尋歷史
list_search_history(limit=10)

# 3. get_cached_article - 從快取取得文章
get_cached_article(pmid="12345678")

# 4. get_session_summary - Session 狀態摘要
get_session_summary()
```

#### search_literature 輸出增強

搜尋結果現在會顯示：
```
📊 Found 25 results (of 100 total in PubMed)
...
---
💾 **Session 已暫存 25 篇 PMIDs**
🔖 後續可用: `get_session_pmids()` 或 `pmids='last'`
```

#### 使用流程

```
# 搜尋後不需記住 PMID
search_literature(query="BJA[ta] AND 2025/12[dp]", limit=25)

# 隨時取回
get_session_pmids()  # 回傳 pmids_csv 可直接用

# 或直接在其他工具使用
prepare_export(pmids="last", format="ris")
get_citation_metrics(pmids="last")
```

---

## 🟠 P1: PubMed → Zotero 直送

### 問題描述
目前流程:
```
PubMed Search → Agent 記憶 PMIDs → Agent 逐筆呼叫 → Zotero
```

應有流程:
```
PubMed Search → 標準化資料結構 → Zotero 批次匯入
```

### 改進方案

#### 方案 A: RIS 中繼檔案
`pubmed-search` 已有 `prepare_export(pmids, format="ris")` 功能，輸出到 `/tmp/pubmed_exports/`

新增 `zotero-keeper` 工具:
```python
@mcp.tool()
def import_from_ris(ris_file: str, collection_key: str = None) -> str:
    """
    從 RIS 檔案批次匯入 Zotero

    Args:
        ris_file: RIS 檔案路徑 (或 "last" 使用最近匯出)
        collection_key: 目標 collection
    """
```

#### 方案 B: 直接 API 串接
在 `pubmed-search` 中新增:
```python
@mcp.tool()
def export_to_zotero(
    pmids: str,
    zotero_endpoint: str = "http://localhost:23119",
    collection_key: str = None
) -> str:
    """直接將 PubMed 結果送到 Zotero"""
```

#### 方案 C: MCP Orchestrator 模式
```python
# Agent prompt 中定義標準流程
"""
當使用者要求存入 Zotero:
1. 詢問目標 Collection
2. 呼叫 pubmed-search::prepare_export(pmids, format="ris")
3. 呼叫 zotero-keeper::import_from_ris(ris_file, collection_key)
"""
```

### 推薦: 方案 A (最少改動，最可靠)

---

## 🟡 P2: Collection 選擇流程

### 問題描述
Agent 不知道要存入哪個 Collection，也沒有詢問使用者

### 改進方案

#### Agent System Prompt 更新
```
## 存入 Zotero 標準流程

當使用者要求將文獻存入 Zotero:

1. **詢問 Collection**:
   - 先呼叫 `list_collections()` 取得可用 collections
   - 詢問使用者: "請問要存入哪個 collection？"
   - 列出選項讓使用者選擇

2. **選擇存入方式**:
   - 少於 5 篇: 使用 `smart_add_reference()` 逐筆存入 (含重複檢查)
   - 5-20 篇: 使用批次 RIS 匯入
   - 超過 20 篇: 分批處理，每批 20 篇

3. **確認結果**:
   - 回報成功/失敗數量
   - 提醒使用者手動將文章拖入 collection (API 限制)
```

---

## 🟡 P2: 摘要重複取回

### 問題描述
整理 markdown 摘要時，Agent 從 PubMed 網頁重新抓取，但 Zotero 中已有完整資料

### 改進方案

#### 優先順序
1. 檢查 Zotero 是否已有該 PMID (`search_items(pmid)`)
2. 若有，從 Zotero 讀取 (`get_item(key)`)
3. 若無，才從 PubMed 取得

#### Agent Prompt 更新
```
## 取得文獻摘要流程

當需要文獻摘要時:

1. 先檢查 Zotero: `search_items(query=pmid)`
2. 若找到: `get_item(key)` → 使用 abstractNote 欄位
3. 若未找到: `fetch_article_details(pmid)` 從 PubMed 取得
```

---

## 🟢 P3: 全文連結檢索

### 問題描述
存入 Zotero 時沒有檢查是否有 PMC 全文連結

### 改進方案

在 `smart_add_reference` 流程中加入:
```python
# 檢查全文可用性
fulltext_info = get_article_fulltext_links(pmid)
if fulltext_info.get("pmc_url"):
    # 加入 URL 欄位
    extra_fields["url"] = fulltext_info["pmc_url"]
```

---

## 🟢 P3: IF 查詢機制

### 問題描述
研究者想知道期刊 Impact Factor，但沒有官方免費 API

### 選項評估

| 選項 | 優點 | 缺點 |
|------|------|------|
| 內建 IF 資料庫 | 快速查詢 | 版權問題、需定期更新 |
| Scimago API | 免費 | 數據是 SJR 非 IF |
| 使用者自訂清單 | 無版權問題 | 需使用者維護 |
| 提示使用者查詢 | 最安全 | 使用者體驗差 |

### 建議方案
1. 預設不提供 IF (避免版權問題)
2. 提供 Scimago SJR 作為替代指標 (免費公開)
3. 允許使用者自訂 IF 對照表

---

## 📊 實施順序

```
Week 1:
├─ ✅ P0: 修復搜尋數量回報 (已完成)
├─ P1a: 增強 session PMID 輸出
└─ P2a: 更新 Agent prompt (Collection 流程)

Week 2:
├─ P1b: 實作 RIS → Zotero 匯入工具
├─ P2b: 更新 Agent prompt (摘要優先順序)
└─ P3a: 全文連結自動檢索

Week 3:
├─ P3b: Scimago SJR 整合 (可選)
└─ 整合測試
```

---

## 📝 相關檔案

- `/home/eric/workspace251211/zotero-keeper/external/pubmed-search-mcp/src/pubmed_search/mcp/tools/discovery.py` - 已修復
- `/home/eric/workspace251211/zotero-keeper/external/pubmed-search-mcp/src/pubmed_search/session.py` - Session 管理
- `/home/eric/workspace251211/zotero-keeper/src/zotero_keeper/mcp/tools/` - Zotero 工具

---

*最後更新: 2025-12-15*
