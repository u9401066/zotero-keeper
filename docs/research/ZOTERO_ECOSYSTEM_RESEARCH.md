# Zotero 生態系研究報告

> 研究日期：2025-01-12
> 目的：分析 11 個相關 GitHub repositories，提取可用於改進 zotero-keeper 的功能和技術

---

## 📊 研究概覽

| # | Repository | ⭐ Stars | 類型 | 主要學習點 |
|---|------------|---------|------|-----------|
| 1 | zotero-chinese/zotero-plugins | 595 | 插件目錄 | 插件發現機制 |
| 2 | 54yyyu/zotero-mcp | 914 | MCP Server | 語義搜尋、Web API |
| 3 | zotero/zotero-android | 627 | 官方 App | 架構參考 |
| 4 | papersgpt/papersgpt-for-zotero | 2k | AI 插件 | AutoPilot、MCP SSE |
| 5 | zotero/dataserver | 320 | 官方後端 | API 實作參考 |
| 6 | eschnett/zotero-citationcounts | 900 | 引用插件 | 引用來源整合 |
| 7 | wshanks/Zutilo | 1.8k | 工具插件 | 批次操作、快捷鍵 |
| 8 | urschrei/pyzotero | 1.2k | Python Client | 完整 API 封裝 |
| 9 | redleafnew/zotero-javascripts | 279 | JS 腳本集 | 批次處理範例 |
| 10 | jbaiter/zotero-cli | 295 | CLI 工具 | 命令列介面 |
| 11 | frangoud/ZoteroDuplicatesMerger | 391 | 重複處理 | 智能合併 |

---

## 1️⃣ zotero-chinese/zotero-plugins (595 ⭐)

### 專案簡介
中文 Zotero 插件合集網站，提供集中式的插件發現和下載服務。

### 技術架構
- TypeScript + Vue 前端
- GitHub Actions 自動抓取插件資訊
- 從 GitHub Releases 提取 XPI 檔案
- 輸出 `dist/plugins.json` 供其他應用使用

### 🎯 可借鑒改進

| 改進項目 | 說明 | 優先度 |
|----------|------|:------:|
| **插件推薦功能** | 在 MCP 中提供「推薦 Zotero 插件」工具 | 🟡 中 |
| **plugins.json 整合** | 直接使用他們的 JSON 作為插件資料來源 | 🟢 低 |
| **自動更新檢查** | 參考其 CI/CD 設計檢查插件更新 | 🟢 低 |

### 程式碼參考
```typescript
// 他們的 plugins.ts 結構
interface PluginInfo {
  repo: string;  // "northword/zotero-format-metadata"
  releases: Array<{
    targetZoteroVersion: string;  // "7" or "6"
    tagName: 'latest' | 'pre' | string;
  }>;
}
```

---

## 2️⃣ 54yyyu/zotero-mcp (914 ⭐) ⚠️ 競品分析

### 專案簡介
另一個 Zotero MCP Server，功能比我們更完整！

### 🔥 核心功能對比

| 功能 | 54yyyu/zotero-mcp | zotero-keeper | 差距 |
|------|:----------------:|:-------------:|:----:|
| 基本搜尋 | ✅ | ✅ | = |
| 語義搜尋 (Embeddings) | ✅ | ❌ | 🔴 |
| PDF 標註提取 | ✅ | ❌ | 🔴 |
| 筆記創建 | ✅ | ❌ | 🔴 |
| Web API 模式 | ✅ | ❌ (規劃中) | 🟡 |
| PubMed 整合 | ❌ | ✅ | 🟢 |
| 引用指標 (RCR) | ❌ | ✅ | 🟢 |
| 批次匯入 | ❌ | ✅ | 🟢 |

### 🎯 必須借鑒的功能

#### 1. 語義搜尋 (Semantic Search)
```python
# 他們的實現
- 使用 ChromaDB 向量資料庫
- 支援 3 種 embedding 模型:
  - all-MiniLM-L6-v2 (免費本地)
  - OpenAI text-embedding-3-small
  - Gemini models/text-embedding-004
- 命令: zotero-mcp update-db --fulltext
```

**改進方案:**
```python
# 我們可以新增
def semantic_search_library(query: str, model: str = "default"):
    """在 Zotero 庫中進行語義搜尋"""
    # 使用 sentence-transformers 或 OpenAI
    embeddings = generate_embeddings(query)
    results = chromadb_client.query(embeddings)
    return results
```

#### 2. PDF 標註提取
```python
# 他們的功能
zotero_get_annotations(item_key)  # 包括直接 PDF 提取
zotero_search_notes(query)        # 搜尋筆記和標註
```

#### 3. 筆記創建 (Beta)
```python
zotero_create_note(item_key, content)
```

### 技術細節
- Python 3.10+
- 支援 Local API 和 Web API
- 自動更新機制 (`zotero-mcp update`)
- 配置持久化

### 🚀 建議行動
1. **P0**: 研究其語義搜尋實作，評估整合可行性
2. **P1**: 新增 PDF 標註讀取功能
3. **P2**: 考慮合作或功能互補

---

## 3️⃣ zotero/zotero-android (627 ⭐)

### 專案簡介
官方 Android App，使用 Kotlin 開發。

### 技術架構
- Kotlin + Jetpack Compose (Material Design 3)
- 使用 Zotero Sync API
- 引用 zotero-schema、translators、locales submodules

### 🎯 可借鑒改進

| 改進項目 | 說明 | 優先度 |
|----------|------|:------:|
| **Schema 使用** | 參考他們如何使用 zotero-schema | 🟡 中 |
| **Translators 整合** | 學習如何嵌入 translators | 🟢 低 |

### 重要發現
- 使用官方 `zotero-schema` 進行 item type 驗證
- Citation 功能使用 `citeproc-js`

---

## 4️⃣ papersgpt/papersgpt-for-zotero (2k ⭐) 🔥

### 專案簡介
最受歡迎的 Zotero AI 插件，支援多種 LLM。

### 🔥 核心功能

#### AutoPilot (AI Agent)
- 自動閱讀 100+ 篇論文
- AI 生成的洞見自動存入 Zotero Notes
- 自訂 prompt 支援

#### MCP Server (SSE)
```text
URL: http://localhost:9080/sse
- C++ 實作，極快速
- 支援 BM25 全文搜尋
- 搜尋範圍: 標題、作者、標籤、摘要、筆記、標註
```

#### 多 LLM 支援
- GPT-5.1, Claude Sonnet 4.5, Gemini 3
- DeepSeek, Qwen3, Kimi K2
- 本地 LLM (Ollama 支援)

### 🎯 可借鑒改進

| 改進項目 | 說明 | 優先度 |
|----------|------|:------:|
| **SSE Transport** | 目前我們用 stdio，可考慮加 SSE | 🟡 中 |
| **BM25 搜尋** | 本地全文搜尋優化 | 🟡 中 |
| **AutoPilot 概念** | 批次 AI 處理文獻 | 🔴 高 |

### AutoPilot 整合構想
```python
# 新增 MCP 工具
async def batch_analyze_papers(
    collection_key: str,
    prompt: str,  # e.g., "Extract methodology from each paper"
    save_to_notes: bool = True
):
    """批次 AI 分析論文，結果存入 Zotero Notes"""
    items = get_collection_items(collection_key)
    for item in items:
        fulltext = get_item_fulltext(item.key)
        analysis = await llm.analyze(fulltext, prompt)
        if save_to_notes:
            create_note(item.key, analysis)
    return results
```

---

## 5️⃣ zotero/dataserver (320 ⭐)

### 專案簡介
官方 Zotero Data Server，PHP 實作。

### 技術架構
- PHP 8.x
- MySQL + Redis
- 實作 Zotero Web API v3

### 🎯 可借鑒改進

| 改進項目 | 說明 | 優先度 |
|----------|------|:------:|
| **API 實作參考** | 理解官方 API 的邊界情況 | 🟢 低 |
| **Schema 更新** | 追蹤 schema 變化 | 🟢 低 |

### 重要發現
- 使用 `zotero-schema` submodule
- Version 衝突處理邏輯可參考

---

## 6️⃣ eschnett/zotero-citationcounts (900 ⭐)

### 專案簡介
自動從多個來源抓取引用次數。

### 支援的引用來源
1. **Crossref** - DOI 查詢
2. **Inspire HEP** - 高能物理
3. **Semantic Scholar** - 學術搜尋引擎

### 技術實作
- 引用存在 `Extra` 欄位
- 格式: `Citations: 127 [2024-01-15]`

### 🎯 可借鑒改進

| 改進項目 | 說明 | 優先度 |
|----------|------|:------:|
| **Semantic Scholar API** | 新增 S2 作為引用來源 | 🟡 中 |
| **引用格式標準化** | 參考其 Extra 欄位格式 | 🟢 低 |

### 與我們的對比
```
他們: Crossref, Inspire, Semantic Scholar
我們: iCite (RCR, NIH Percentile)

可以互補！
```

### 整合方案
```python
# 新增 Semantic Scholar 支援
async def get_semantic_scholar_citations(doi: str):
    """從 Semantic Scholar 取得引用數"""
    url = f"https://api.semanticscholar.org/v1/paper/{doi}"
    response = await httpx.get(url)
    return response.json().get("citationCount")
```

---

## 7️⃣ wshanks/Zutilo (1.8k ⭐)

### 專案簡介
功能強大的 Zotero 工具插件。

### 核心功能
- **標籤操作**: 複製、貼上、移除標籤
- **關聯操作**: 批次建立文獻關聯
- **複製功能**: 多種格式複製到剪貼簿
- **快捷鍵**: 所有功能可綁定快捷鍵

### 🎯 可借鑒改進

| 改進項目 | 說明 | 優先度 |
|----------|------|:------:|
| **批次標籤操作** | 新增 `copy_tags`, `paste_tags` 工具 | 🟡 中 |
| **批次關聯** | 新增 `relate_items` 工具 | 🟡 中 |
| **複製格式** | 支援更多匯出格式 | 🟢 低 |

### MCP 工具構想
```python
# 新增工具
def copy_tags_between_items(source_key: str, target_keys: list[str]):
    """從來源項目複製標籤到目標項目"""
    
def relate_items(item_keys: list[str]):
    """建立多個項目之間的關聯"""
    
def copy_item_as(item_key: str, format: str):
    """以指定格式複製項目 (citation, bibtex, ris, etc.)"""
```

---

## 8️⃣ urschrei/pyzotero (1.2k ⭐)

### 專案簡介
Python Zotero API 封裝，已在 ZOTERO_LOCAL_API.md 詳細記錄。

### 🎯 整合狀態
- ✅ 已記錄在文檔中
- ⏳ 計畫整合為 Web API 模式

### 關鍵功能
```python
zot.addto_collection(collection_key, item)  # 核心需求！
zot.update_item(item)
zot.create_items([items])
zot.attachment_simple([files], parent_key)
```

---

## 9️⃣ redleafnew/zotero-javascripts (279 ⭐)

### 專案簡介
30+ 個 Zotero JavaScript 腳本，用於批次處理。

### 實用腳本列表

| 腳本 | 功能 | MCP 可實現？ |
|------|------|:----------:|
| 01-set-language-to-en | 空語言欄位設為 en | ✅ |
| 02-title-to-sentence-case | 標題轉 Sentence case | ✅ |
| 03-empty-extra-field | 清空 Extra 欄位 | ✅ |
| 06-authors-to-title-case | 作者名轉 Title case | ✅ |
| 07-batch-merge-duplicates | 批次合併重複 | ⚠️ |
| 15-swap-author-names | 交換姓名順序 | ✅ |
| 26-change-item-type | 更改項目類型 | ✅ |
| 27-remove-extra-space | 移除摘要多餘空格 | ✅ |

### 🎯 可借鑒改進

| 改進項目 | 說明 | 優先度 |
|----------|------|:------:|
| **批次清理工具** | 新增 `clean_metadata` 工具 | 🟡 中 |
| **格式標準化** | 新增 `normalize_titles` 工具 | 🟡 中 |
| **作者處理** | 新增 `fix_author_names` 工具 | 🟢 低 |

### MCP 工具構想
```python
def clean_item_metadata(
    item_keys: list[str],
    operations: list[str]  # ["fix_title_case", "remove_extra_spaces", "set_language"]
):
    """批次清理項目 metadata"""
    
def normalize_journal_names(item_keys: list[str]):
    """標準化期刊名稱"""
```

---

## 🔟 jbaiter/zotero-cli (295 ⭐)

### 專案簡介
Zotero 命令列工具，9 年前的專案。

### 核心功能
```bash
zotcli query "deep learning"     # 搜尋
zotcli read "deep learning"      # 開啟 PDF
zotcli add-note "deep learning"  # 新增筆記
zotcli edit-note F5R83K6P        # 編輯筆記
```

### 技術特點
- 使用 SQLite FTS 進行本地搜尋
- 支援 pandoc 格式轉換
- 使用 Web API

### 🎯 可借鑒改進

| 改進項目 | 說明 | 優先度 |
|----------|------|:------:|
| **CLI 包裝** | 考慮提供 CLI 介面 | 🟢 低 |
| **FTS 搜尋** | 本地全文搜尋優化 | 🟡 中 |

### 已過時警告
- 9 年未更新
- 可能無法與 Zotero 7 相容

---

## 1️⃣1️⃣ frangoud/ZoteroDuplicatesMerger (391 ⭐)

### 專案簡介
自動合併重複項目的插件。

### 核心功能
1. **Smart Merge**: 選擇項目後智能合併
2. **Bulk Merge**: 自動處理所有重複項

### 合併選項
- 選擇 master (最新/最舊)
- 類型衝突處理 (跳過/強制)
- 跳過預覽

### 🎯 可借鑒改進

| 改進項目 | 說明 | 優先度 |
|----------|------|:------:|
| **重複檢測增強** | 改進我們的重複檢測邏輯 | 🟡 中 |
| **合併建議** | MCP 提供合併建議 | 🟢 低 |

### 與我們的對比
```
我們: 匯入時檢測重複 (by PMID/DOI)
他們: 合併已存在的重複

可以互補！
```

### MCP 工具構想
```python
def find_duplicates(collection_key: str = None):
    """找出庫中的重複項目"""
    
def suggest_merge(item_key1: str, item_key2: str):
    """比較兩個項目，建議合併策略"""
```

---

## 🎯 改進優先級總結

### P0 - 高優先 (應立即實施)

| 項目 | 來源 | 說明 |
|------|------|------|
| 語義搜尋 | 54yyyu/zotero-mcp | 向量搜尋，概念匹配 |
| Web API 模式 | pyzotero | 完整讀寫能力 |
| AutoPilot 概念 | papersgpt | 批次 AI 處理 |

### P1 - 中優先 (近期實施)

| 項目 | 來源 | 說明 |
|------|------|------|
| PDF 標註讀取 | 54yyyu/zotero-mcp | 讀取 PDF 標註 |
| Semantic Scholar API | zotero-citationcounts | 新增引用來源 |
| 批次標籤操作 | Zutilo | copy/paste tags |
| 批次 metadata 清理 | zotero-javascripts | 標準化處理 |
| SSE Transport | papersgpt | 除了 stdio 外支援 SSE |

### P2 - 低優先 (未來考慮)

| 項目 | 來源 | 說明 |
|------|------|------|
| 插件推薦 | zotero-plugins | 推薦合適插件 |
| CLI 介面 | zotero-cli | 命令列工具 |
| 重複合併建議 | ZoteroDuplicatesMerger | 智能合併 |

---

## 📋 行動計畫

### Phase 1: Web API 整合 (2 週)
1. 整合 pyzotero
2. 支援 API Key 模式
3. 實現 `add_to_collection` 功能

### Phase 2: 語義搜尋 (3 週)
1. 研究 54yyyu/zotero-mcp 實作
2. 整合 ChromaDB 或替代方案
3. 支援本地 + OpenAI embeddings

### Phase 3: 增強功能 (持續)
1. PDF 標註讀取
2. 批次操作工具
3. Semantic Scholar 整合

---

## 📚 參考連結

- [zotero-chinese/zotero-plugins](https://github.com/zotero-chinese/zotero-plugins)
- [54yyyu/zotero-mcp](https://github.com/54yyyu/zotero-mcp)
- [zotero/zotero-android](https://github.com/zotero/zotero-android)
- [papersgpt/papersgpt-for-zotero](https://github.com/papersgpt/papersgpt-for-zotero)
- [zotero/dataserver](https://github.com/zotero/dataserver)
- [eschnett/zotero-citationcounts](https://github.com/eschnett/zotero-citationcounts)
- [wshanks/Zutilo](https://github.com/wshanks/Zutilo)
- [urschrei/pyzotero](https://github.com/urschrei/pyzotero)
- [redleafnew/zotero-javascripts](https://github.com/redleafnew/zotero-javascripts)
- [jbaiter/zotero-cli](https://github.com/jbaiter/zotero-cli)
- [frangoud/ZoteroDuplicatesMerger](https://github.com/frangoud/ZoteroDuplicatesMerger)
