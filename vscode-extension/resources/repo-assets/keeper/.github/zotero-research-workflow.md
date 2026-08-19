# Research Workflow Guide for Copilot

> 這份指南幫助 Copilot 理解如何正確使用 Zotero + PubMed MCP tools

> v0.8.0 VSIX 基線：Zotero Keeper 2.2.0（MCP SDK v2，41 個預設 tools + 6 個具體 resources）與 PubMed Search MCP 0.6.3 `febf53a`（45 tools / 16 categories）。

## 🔍 文獻搜尋流程

### 步驟 1: 了解研究問題
使用 `parse_pico` 將研究問題拆解為 PICO 結構：
- **P**opulation: 研究對象
- **I**ntervention: 介入措施
- **C**omparison: 對照組
- **O**utcome: 結果指標

### 步驟 2: 生成搜尋策略
使用 `generate_search_queries` 產生專業的搜尋策略，包含：
- MeSH terms
- Boolean operators
- Field tags

### 步驟 3: 執行搜尋
使用 `unified_search` 執行搜尋，注意：
- 結果會自動快取到 Session
- 使用 `get_session_pmids` 取得已搜尋的 PMID
- **不要重複搜尋相同的關鍵字**
- `unified_search` 會自動合併去重多個來源的結果
- 需要特定範圍時可用 `options="trials"` / `"native_semantic"` /
  `"systematic"`，不要將 systematic 當成無上限擴張搜尋
- 依 `search_status` 區分合法 `empty`、需附 warning 的 `partial` 與
  真正 `failed`，不得將 partial/failed 假裝成零結果

### 步驟 4: 過濾已有文獻
使用 `check_articles_owned` 檢查搜尋結果中的 PMID 哪些已存在於 Zotero

---

## 📥 匯入 Zotero 流程

### ⚠️ 重要：先詢問 Collection！
在匯入任何文獻前，**必須先詢問用戶**要存入哪個 Collection。

Collection 路由採 fail-closed：

- `interactive_save` 只能回傳精確 collection key 或 `ROOT`；`ROOT` 還必須通過第二次確認。
- `skip_collection_prompt=True` 會中止，不會自動存入 library root。
- `quick_save`、`import_articles`、`import_pdf` 沒有 collection 時預設拒絕。只有用戶明確確認 My Library 且呼叫含 `allow_library_root=true` 才可存入 root。

### 匯入方式選擇

| 情境 | 推薦工具 | 說明 |
|------|----------|------|
| pubmed-search-mcp JSON 結果 | `import_articles` | 預設推薦，直接接 `unified_search(..., output_format="json")` |
| RIS 匯出文字 | `import_articles` | 傳入 `ris_text`，由 keeper 統一解析匯入 |
| 需要舊版 keeper 單機橋接流程 | legacy tools | 僅在啟用 `ZOTERO_KEEPER_ENABLE_LEGACY_PUBMED_TOOLS=1` 時使用 |

### 匯入前確認清單
1. ✅ 已詢問目標 Collection
2. ✅ 已確認文章或 PMID 來源（例如 `unified_search` 結果或 `get_session_pmids`）
3. ✅ 已提醒用戶文獻數量
4. ✅ 沒有以「省略 collection」當成 root；如用戶要存 My Library，已完成明確確認與 `allow_library_root=true`

---

## 🔄 Session 管理

### 為什麼需要 Session？
- PubMed 搜尋結果會快取
- 避免重複 API 呼叫
- 保持 PMID 追蹤，不依賴 Agent 記憶

### Session 工具使用時機

| 工具 | 何時使用 |
|------|----------|
| `get_session_pmids` | 需要取得之前搜尋的 PMID |
| `get_session_log` / `read_session` | 查看或重讀 session 內已持久化的搜尋與操作紀錄 |
| `get_cached_article` | 取得已快取的文章詳情（避免重複 fetch） |
| `get_session_summary` | 檢查 Session 狀態 |

### Research Chronicle

需要建立可持續更新的研究演進紀錄時，先用
`build_research_chronicle`，再用 `read_research_chronicle` 閱讀 map 或
Mermaid timeline。這兩個工具已取代舊的 3 個 timeline 工具。
0.6.3 續建既有 chronicle 時，要明確重送原 topic/PMIDs/year/max-events
scope。SearchRun 恢復則用 `read_session` 的 `search_runs` /
`search_run` / `replay_search` action，不要盲目重搜。

---

## 📚 Zotero 書庫管理

### 查詢現有文獻
1. `list_collections` - 先看有哪些 Collections
2. `get_collection_items` - 取得特定 Collection 的文獻
3. `search_items` - 在書庫中搜尋

### 避免重複匯入
使用 `check_articles_owned` 檢查 PMID 是否已存在

### 書庫分析
- `get_library_stats` - 統計分析
- `find_orphan_items` - 找出孤兒文獻（未分類）

### Zotero 10+ 整理與更新

只有使用者要求 mutation 時才呼叫 `authorize_local_writes`。Zotero 會顯示
自己的授權視窗；Local API key 不會出現在 tool result。preview 前先從 exact
Local API read 或 authorization 取得 response-bound `server_id`，並在第一次
`confirm=false` 呼叫時就以 `expected_server_id` 放進 proposal。向使用者確認
identity、版本 cursor、精確對象與內容後，才以 `confirm=true` 原樣重送。

- `create_collection`：建立頂層／巢狀 collection
- `update_collection` / `delete_collection`：使用 exact collection object version 更新、移動或刪除
- `add_items_to_collection` / `remove_items_from_collection`：只變更目標 membership，保留其他歸屬
- `update_item_fields` / `delete_item`：使用 exact-item object version 更新安全欄位或刪除精確 item
- `create_note`：在 exact parent 下建立 child note
- `create_saved_search` / `update_saved_search` / `delete_saved_search`：使用結構化條件與 object version 管理 saved search
- `delete_tags`：使用 response-bound library cursor 批次刪除精確 tag 名稱
- `attach_file_to_item` / `replace_attachment_file`：先呼叫 `authorize_local_writes(require_remembered=true)` 並在 Zotero 選 Always Allow；replace 還要核對 exact attachment version 與原 MD5
- `set_attachment_fulltext` / `set_attachment_fulltexts`：使用 response-bound library cursor，batch 最多十筆；不得使用 attachment object version

十六個 confirmed mutation 全部必須帶已核准 proposal 中的
`expected_server_id`。若 authorization 回傳不同 identity，丟棄原 proposal，
重新 read、preview 與取得核准；不能在 preview 後才補 identity。收到 412
version/identity conflict 時不得自動重試。

---

## ⚠️ 常見錯誤避免

### ❌ 錯誤做法
1. 搜尋後直接匯入，沒問 Collection
2. 重複搜尋相同關鍵字
3. 匯入時沒確認 PMID 列表
4. 從 PubMed 重新取摘要（Zotero 已有）

### ✅ 正確做法
1. 搜尋 → 確認結果 → 詢問 Collection → 匯入
2. 用 `get_session_pmids` 取得已有的 PMID
3. 用 `get_item` 從 Zotero 讀取已存文獻的詳情
4. 匯入前用 `check_articles_owned` 檢查重複，再用 `import_articles` 存入 Zotero

---

## 🎯 典型對話流程範例

```
用戶: 幫我找最近的 AI 麻醉研究

Copilot 動作:
1. parse_pico: 分析研究問題
2. generate_search_queries: 產生搜尋策略
3. unified_search: 執行搜尋
4. [回報結果，詢問是否要存入 Zotero]
5. list_collections: 取得 Collection 列表
6. [詢問用戶要存入哪個 Collection]
7. import_articles: 匯入到指定 Collection
8. [確認完成]
```
