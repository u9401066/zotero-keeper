# Batch Import Design Document

> **Version**: 1.5  
> **Date**: 2025-12-12  
> **Target Release**: v1.7.0  
> **Status**: Historical design record

## Current Status (2026-04-09)

This document is now a historical design record.

The current collaboration-safe workflow is:

`pubmed-search-mcp unified_search(..., output_format="json") -> zotero-keeper check_articles_owned(...) -> import_articles(...)`

Current production guidance:

- Use `unified_search` as the public search entry
- Use `check_articles_owned` only for local duplicate filtering
- Use `import_articles` as the single public PubMed -> Zotero handoff
- Treat `batch_import_from_pubmed`, `import_from_pmids`, and related keeper-only PubMed bridge tools as legacy compatibility tools gated by `ZOTERO_KEEPER_ENABLE_LEGACY_PUBMED_TOOLS=1`

---

## 🚀 Current Architecture Decision: Collaboration-Safe Handoff

### Key Insight: structured article handoff is the default public contract

Public MCP responsibility is intentionally split:

```python
# 1. Search with pubmed-search-mcp
results = unified_search("remimazolam ICU sedation", output_format="json")

# 2. Optionally filter against local Zotero
owned = check_articles_owned([...pmids...])

# 3. Persist selected records in Zotero
import_articles(articles=results["articles"], collection_name="ICU Sedation")
```

The older keeper-only direct library import path still exists for compatibility, but it is not the recommended public workflow.

### 為什麼現在這樣更好？

| 方式 | 資料完整性 | 效率 | 複雜度 |
|------|-----------|------|--------|
| ❌ keeper / pubmed-search 都公開自己的 PubMed bridge | ⚠️ Agent 易選錯工具 | 中 | 高 |
| ❌ 以 keeper-only batch bridge 當成預設 | ⚠️ 職責混雜 | 中 | 中 |
| ✅ **collaboration-safe handoff** | ✅ **完整** | ✅ | **低** |

---

## 🎉 Key Discovery: pubmed-search-mcp Already Has Complete Data!

**經過程式碼審查，發現 pubmed-search-mcp 的 `fetch_details()` 已經返回完整資料！**

使用 **Biopython Entrez** 模組（官方推薦方式），已經包含：

| 欄位 | 狀態 | 說明 |
|------|------|------|
| `pmid` | ✅ | |
| `title` | ✅ | |
| `authors` | ✅ | 簡短格式 |
| `authors_full` | ✅ | `{fore_name, last_name, initials}` |
| `abstract` | ✅ **完整** | Biopython 處理，不截斷！ |
| `journal` / `journal_abbrev` | ✅ | |
| `year/month/day` | ✅ | |
| `volume/issue/pages` | ✅ | |
| `doi` | ✅ | |
| `pmc_id` | ✅ | |
| `issn` | ✅ | |
| `keywords` | ✅ | 作者關鍵字 |
| `mesh_terms` | ✅ | MeSH 標準詞彙 |
| `language` | ✅ | |
| `publication_types` | ✅ | |
| `affiliations` | ❌ 缺少 | **需要在 pubmed-search 新增** |

---

## 🎯 Design Principles (設計原則)

### 1. 存就存最完整的！(Store Complete Metadata)

PubMed 提供豐富的 metadata，我們應該**全部保存**到 Zotero：

| ❌ 以前 (v1.6.0) | ✅ 現在 (v1.7.0) |
|-----------------|-----------------|
| 只存標題、作者、DOI | **完整摘要** (不截斷) |
| 缺少 MeSH 詞彙 | **Keywords + MeSH** → tags |
| 沒有機構資訊 | **作者機構** → extra field |
| 缺少 PMC ID | **PMID + PMCID** 完整保存 |

### 2. 直接 Import Library (Direct Library Import)

```
❌ 錯誤想法: 透過 Agent 傳遞資料 (可能被截斷)
❌ 錯誤想法: zotero-keeper 自己實作 NCBI API client (重複造輪子)
✅ 正確做法: zotero-keeper 直接 import pubmed-search library
```

**pubmed-search 作為 submodule，可以直接被 import！**

### 3. MCP 分工明確 (Clear Responsibility)

```
pubmed-search-mcp (library): 搜尋、取得完整資料、全文檢查、引用分析
zotero-keeper (MCP tool):    直接呼叫 pubmed-search → 重複檢測 → 寫入 Zotero
```

---

## 🎯 MCP Responsibility Split (重要!)

| Functionality | Responsible MCP | Tool/Library | Notes |
|--------------|-----------------|--------------|-------|
| **Literature Search** | pubmed-search | `unified_search` | Public MCP tool |
| **Structured Article Contract** | pubmed-search | `UnifiedArticle.to_dict()` | Public JSON payload |
| **MeSH/Synonym Expansion** | pubmed-search | `generate_search_queries` | MCP tool |
| **Article Detail Fetch** | pubmed-search | `fetch_article_details` | MCP tool |
| **Citation Metrics** | pubmed-search | `get_citation_metrics` | MCP tool |
| **Duplicate Detection** | zotero-keeper | `check_articles_owned` | Public MCP tool |
| **Batch / JSON / RIS Import** | zotero-keeper | `import_articles` | Single public import entry |
| **Collection Management** | zotero-keeper | `list_collections`, `get_collection_items` | Public MCP tools |

**Principle:**
- pubmed-search-mcp owns search, discovery, export, and citation metrics
- zotero-keeper owns local duplicate checks, collection choice, and persistence into Zotero
- keeper-only PubMed bridge tools remain legacy compatibility paths, not the default public surface

---

## 🎯 User Journey Flow (Complete Data Path)

### 典型使用情境

```
┌─────────┐     ┌─────────┐     ┌──────────────┐     ┌──────────────┐     ┌────────┐
│  User   │────▶│  Agent  │────▶│ pubmed-search│     │ zotero-keeper│────▶│ Zotero │
│         │◀────│         │◀────│    (MCP)     │     │    (MCP)     │◀────│        │
└─────────┘     └─────────┘     └──────────────┘     └──────────────┘     └────────┘
```

### Step-by-Step 資料流

```
Step 1: 搜尋
────────────────────────────────────────────────────────────────────────
User:   "搜尋 remimazolam 相關文獻"
Agent:  ──▶ pubmed-search.search_literature("remimazolam")
Agent:  ◀── [pmid1, pmid2, pmid3...] + 簡短摘要 (truncated for display)

📝 資料狀態: PMIDs + truncated 摘要 (只是給 User 看的，truncated 沒問題)

Step 2: 展示
────────────────────────────────────────────────────────────────────────
Agent:  展示搜尋結果給 User
        "找到 50 篇文獻：
         1. [PMID: 38353755] AI in Operating Room Management...
         2. [PMID: 37864754] Machine Learning for Anesthesia...
         ..."

Step 3: 過濾
────────────────────────────────────────────────────────────────────────
User:   "過濾 2024 年以後的 RCT"
Agent:  自己過濾 PMIDs (或再呼叫 pubmed-search)
Agent:  "篩選後剩 15 篇符合條件"

📝 資料狀態: 只需要 PMIDs，不需要完整 metadata

Step 4: 存入 Zotero ⭐ 關鍵步驟
────────────────────────────────────────────────────────────────────────
User:   "請存入 Zotero"
Agent:  ──▶ zotero-keeper.batch_import_from_pubmed(
             pmids="38353755,37864754,38215710,...",
             tags=["Anesthesia-AI"]
         )

        ┌─────────────────────────────────────────────────────┐
        │        zotero-keeper 內部 (Direct Python Import)    │
        │                                                     │
        │  # 1. Parse PMIDs                                   │
        │  pmid_list = pmids.split(",")                       │
        │                                                     │
        │  # 2. 🔥 關鍵：用 direct import 取得完整資料        │
        │  from pubmed_search.client import PubMedClient      │
        │  client = PubMedClient()                            │
        │  articles = client.fetch_details(pmid_list)         │
        │  # ↑ 這裡取得的是完整 SearchResult，不經過 Agent！  │
        │                                                     │
        │  # 3. 檢查重複                                      │
        │  existing = zotero.check_duplicates(articles)       │
        │                                                     │
        │  # 4. 存入 Zotero (完整 metadata)                   │
        │  for article in articles:                           │
        │      if article.pmid not in existing:               │
        │          zotero.save(map_to_zotero(article))        │
        └─────────────────────────────────────────────────────┘

Agent:  ◀── {added: 13, skipped: 2 (duplicates), elapsed: 8.5s}

Step 5: 確認
────────────────────────────────────────────────────────────────────────
Agent:  "已匯入 13 篇文獻到 Zotero，跳過 2 篇重複"
User:   ✅ 完成！
```

### 資料完整性保證

| 階段 | 資料來源 | 資料完整性 | 說明 |
|------|---------|-----------|------|
| Step 1-3 (搜尋/展示/過濾) | pubmed-search **MCP tool** | ⚠️ Truncated | **沒關係！** 這只是給 User 看的 |
| **Step 4 (存入)** | pubmed-search **library** | ✅ **完整** | keeper 內部重新 fetch，存完整資料 |

### 為什麼這樣設計？

| 問題 | 解決方案 |
|------|---------|
| MCP tool 輸出會 truncate 摘要 | Agent 只傳 PMIDs 給 keeper，keeper 自己 fetch 完整資料 |
| Agent 傳遞大量 metadata 慢 | PMIDs 字串很小 (`"123,456,789"`)，幾乎沒負擔 |
| 避免重複呼叫 NCBI API | 搜尋階段用快取，存入階段才 fetch 完整資料 |
| 保證資料一致性 | 單一來源 (PubMedClient)，不會有格式轉換問題 |

---

## 📋 Executive Summary

### Problem Statement | 問題陳述

Current zotero-keeper v1.6.0 has three key limitations when importing literature from PubMed:

| Issue | Current Behavior | Impact |
|-------|------------------|--------|
| **No batch import** | `smart_add_reference` processes one article at a time | 50 articles = 50 API calls, slow and inefficient |
| **Two MCPs not unified** | Agent calls `pubmed-search` directly, bypassing keeper | Lost opportunity for duplicate filtering |
| **RIS export disconnected** | `prepare_export` creates file but doesn't auto-import | Manual workflow interruption |

### Proposed Solution | 解決方案

Implement **two complementary tools**:
1. **`batch_import_from_pubmed`** (Primary) - Direct batch import via metadata
2. **`import_ris_to_zotero`** (Backup) - Import via RIS format

---

## 🏗️ Architecture Overview

### Current Flow (v1.6.0)
```
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│  pubmed-search  │     │  zotero-keeper  │     │     Zotero      │
│      MCP        │     │      MCP        │     │    Desktop      │
└────────┬────────┘     └────────┬────────┘     └────────┬────────┘
         │                       │                       │
    search_literature ──────────▶│                       │
         │                       │                       │
    prepare_export ─────────────▶│ (disconnected)       │
         │                       │                       │
         │              smart_add_reference ────────────▶│
         │              smart_add_reference ────────────▶│
         │              smart_add_reference ────────────▶│
         │                  (N times)                    │
```

### Proposed Flow (v1.7.0) - Direct Library Import
```
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│  pubmed-search  │     │  zotero-keeper  │     │     Zotero      │
│   (library)     │     │      MCP        │     │    Desktop      │
└────────┬────────┘     └────────┬────────┘     └────────┬────────┘
         │                       │                       │
         │   ┌───────────────────┘                       │
         │   │                                           │
         │   │  from pubmed_search.client import PubMedClient
         │   │                                           │
         │◀──┤  articles = PubMedClient().fetch_details(pmids)
         │   │  # 直接 Python 呼叫，資料完整不截斷！        │
         │   │                                           │
         │   │              batch_import_from_pubmed ──▶│
         │   │                  (單一 API 呼叫)           │
         │   │                                           │
         │   │                       │◀─── result ─────│
         │   │                       │                   │
         │   │              Return: {added: 45,          │
         │   │                       skipped: 3,         │
         │   │                       failed: 2}          │
         │   └───────────────────────┘                   │
```

**關鍵架構**:
- zotero-keeper **直接 import** pubmed-search 作為 Python library
- 資料不經過 Agent，完整無遺漏！
- 用戶只需呼叫 keeper 的 `batch_import_from_pubmed(pmids)`，一站式服務

---

## 🔧 Tool Specifications

### Tool A: `batch_import_from_pubmed` (Primary)

#### Signature
```python
@mcp.tool()
async def batch_import_from_pubmed(
    pmids: str,
    tags: list[str] | None = None,
    skip_duplicates: bool = True,
    batch_size: int = 10,
    collection_key: str | None = None
) -> BatchImportResult
```

#### Parameters

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `pmids` | `str` | Yes | - | Comma-separated PMIDs (e.g., "12345,67890") or "last" for last search results |
| `tags` | `list[str]` | No | `None` | Tags to apply to all imported articles |
| `skip_duplicates` | `bool` | No | `True` | Skip if exact DOI/PMID match found |
| `batch_size` | `int` | No | `10` | Number of articles to fetch per batch (NCBI rate limit) |
| `collection_key` | `str` | No | `None` | Zotero collection key to add items to directly |

#### Return Value
```python
class BatchImportResult(TypedDict):
    success: bool
    total: int
    added: int
    skipped: int              # Exact duplicates skipped
    warnings: int             # Added but with warnings (e.g., possible duplicate)
    failed: int
    added_items: list[dict]        # [{pmid, title, key}, ...]
    warning_items: list[dict]      # [{pmid, title, key, warning}, ...]  # NEW
    skipped_items: list[dict]      # [{pmid, title, reason}, ...]
    failed_items: list[dict]       # [{pmid, title, error}, ...]
    collection_key: str | None     # Collection items were added to  # NEW
    elapsed_time: float            # seconds
```

#### Algorithm
```
1. Parse PMIDs (comma-separated string → list)

2. 【直接 Python Import】從 pubmed-search library 取得完整 metadata

   from pubmed_search.client import PubMedClient

   client = PubMedClient()
   articles = client.fetch_details(pmids)

   # SearchResult 包含所有欄位，不截斷：
   # ✓ title, abstract (FULL!)
   # ✓ authors, authors_full (with affiliations)
   # ✓ journal, volume, issue, pages
   # ✓ doi, pmid, pmcid
   # ✓ keywords (author-provided)
   # ✓ mesh_terms (controlled vocabulary)
   # ✓ publication_types, language, pub_date

3. Pre-check duplicates (batch)
   - Query Zotero for existing DOIs and PMIDs
   - Build skip list

4. Map to Zotero schema (COMPLETE)
   - Apply pubmed_to_zotero_item() mapping
   - SearchResult → Zotero item
   - Keywords + MeSH → tags
   - PMID/PMCID/Affiliations → extra field

5. Import non-duplicates
   - For each article not in skip list:
     - Call Connector API saveItems
     - Apply user-provided tags

6. Return summary with full statistics
```

#### Example Usage
```
User: "Import all 30 anesthesia AI papers to Zotero with tag 'AI-Review'"

Agent:
batch_import_from_pubmed(
    pmids="38353755,37864754,38215710,...",
    tags=["Anesthesia-AI", "AI-Review"]
)

Result:
{
    "success": true,
    "total": 30,
    "added": 27,
    "skipped": 2,
    "failed": 1,
    "added_items": [...],
    "skipped_items": [
        {"pmid": "38353755", "title": "...", "reason": "duplicate (DOI match)"}
    ],
    "failed_items": [
        {"pmid": "99999999", "title": "Unknown", "error": "PMID not found"}
    ],
    "elapsed_time": 12.5
}
```

---

### Tool B: `import_ris_to_zotero` (Backup)

#### Signature
```python
@mcp.tool()
async def import_ris_to_zotero(
    ris_content: str,
    tags: list[str] | None = None,
    skip_duplicates: bool = True
) -> RisImportResult
```

#### Parameters

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `ris_content` | `str` | Yes | - | RIS format text content |
| `tags` | `list[str]` | No | `None` | Tags to apply to imported items |
| `skip_duplicates` | `bool` | No | `True` | Check duplicates before import |

#### Return Value
```python
class RisImportResult(TypedDict):
    success: bool
    total: int
    added: int
    skipped: int
    failed: int
    message: str
```

#### Algorithm
```
1. Parse RIS content
   - Extract individual records (separated by "ER  -")
   - Parse fields: TY, TI, AU, JO, PY, DO, AN (PMID), AB
2. Convert to Zotero format
   - Map RIS fields to Zotero item schema
3. Check duplicates (if enabled)
   - By DOI, PMID, or fuzzy title match
4. Import via Connector API
   - POST /connector/saveItems
5. Return summary
```

#### Example Usage
```
User: "Import this RIS file to Zotero"

Agent:
import_ris_to_zotero(
    ris_content="TY  - JOUR\nTI  - ...\nER  -\n...",
    tags=["Imported"]
)
```

---

## 🔗 Metadata Source: pubmed-search-mcp (已有完整資料!)

### Discovery: Biopython Entrez Already Provides Everything

經過程式碼審查，發現 **pubmed-search-mcp 使用 Biopython 的 Entrez 模組**，
已經返回完整的文章 metadata！

**位置**: `external/pubmed-search-mcp/src/pubmed_search/entrez/search.py`

```python
# pubmed-search 已有的 fetch_details() 方法
def fetch_details(self, id_list: List[str]) -> List[Dict[str, Any]]:
    """
    Fetch complete details for a list of PMIDs.

    Returns:
        List of dictionaries containing article details including:
        - pmid, title, authors, authors_full
        - journal, journal_abbrev, year, month, day
        - volume, issue, pages, doi, pmc_id
        - abstract, keywords, mesh_terms  ← 完整資料!
        - language, publication_types, issn
    """
```

### pubmed-search 返回的資料結構

```python
# fetch_article_details() 返回的 dict 結構
{
    "pmid": "38353755",
    "title": "Artificial Intelligence in Operating Room Management",
    "authors": ["Bellini Valentina", "Russo Michele", ...],
    "authors_full": [
        {"last_name": "Bellini", "fore_name": "Valentina", "initials": "V"},
        {"last_name": "Russo", "fore_name": "Michele", "initials": "M"},
        ...
    ],
    "abstract": "This systematic review examines...",  # 完整摘要!
    "journal": "Journal of medical systems",
    "journal_abbrev": "J Med Syst",
    "year": "2024",
    "month": "Feb",
    "day": "14",
    "volume": "48",
    "issue": "1",
    "pages": "19",
    "doi": "10.1007/s10916-024-02038-2",
    "pmc_id": "PMC10867065",
    "issn": "1573-689X",
    "keywords": ["Artificial intelligence", "Machine learning", ...],
    "mesh_terms": ["Operating Rooms", "Machine Learning", ...],
    "language": "eng",
    "publication_types": ["Journal Article", "Systematic Review"]
}
```

### ❌ 不需要自己實作 PubMedClient

```
原本計劃: zotero-keeper 自己實作 NCBI E-utilities XML parser
現在:     直接用 pubmed-search 的資料，不重複造輪子！
```

### ⚠️ 唯一需要在 pubmed-search 新增的欄位

| 欄位 | 狀態 | 來源 |
|------|------|------|
| `affiliations` | ❌ 缺少 | `Author/AffiliationInfo/Affiliation` |

**需要在 pubmed-search v0.1.10 新增 `affiliations` 欄位提取。**

---

## 📊 Data Flow Diagram - Direct Library Import

```
┌────────────────────────────────────────────────────────────────────┐
│                        batch_import_from_pubmed                    │
│                        (zotero-keeper tool)                        │
└────────────────────────────────────────────────────────────────────┘
                                  │
                                  │ Input: pmids="38353755,37864754,..."
                                  ▼
        ┌──────────────────────────────────────────────────────────┐
        │ 1. Parse PMIDs                                           │
        │    "38353755,37864754" → ["38353755", "37864754"]        │
        └──────────────────────────────────────────────────────────┘
                                  │
                                  ▼
        ┌──────────────────────────────────────────────────────────┐
        │ 2. 【Direct Python Import】取得完整 metadata             │
        │                                                          │
        │    from pubmed_search.client import PubMedClient         │
        │                                                          │
        │    client = PubMedClient()                               │
        │    articles: list[SearchResult] = client.fetch_details( │
        │        pmids=["38353755", "37864754"]                    │
        │    )                                                     │
        │                                                          │
        │    # SearchResult 包含完整資料：                          │
        │    # - abstract: 完整不截斷！                             │
        │    # - keywords, mesh_terms: 全部標籤                    │
        │    # - authors_full: 完整作者資訊                        │
        └──────────────────────────────────────────────────────────┘
                                  │
                                  ▼
        ┌──────────────────────────────────────────────────────────┐
        │ 3. Duplicate Check (batch)                               │
        │    - Query Zotero for existing DOIs and PMIDs            │
        │    - Build skip list                                      │
        └──────────────────────────────────────────────────────────┘
                                  │
                                  ▼
        ┌──────────────────────────────────────────────────────────┐
        │ 4. Map to Zotero Schema                                  │
        │    - SearchResult → Zotero journalArticle               │
        │    - keywords + mesh_terms → tags                        │
        │    - pmid + pmc_id → extra                               │
        └──────────────────────────────────────────────────────────┘
                                  │
                                  ▼
        ┌──────────────────────────────────────────────────────────┐
        │ 5. Batch Import via Connector API                        │
        │    POST /connector/saveItems                             │
        └──────────────────────────────────────────────────────────┘
                                  │
                                  ▼
        ┌──────────────────────────────────────────────────────────┐
        │ 6. Return Summary                                        │
        │    BatchImportResult                                     │
        └──────────────────────────────────────────────────────────┘
```

**架構優勢**:
- ✅ **無 Agent 中繼**: 直接 Python import，資料不經過 Agent 傳遞
- ✅ **完整不截斷**: 直接存取 SearchResult 物件，不受 MCP tool 輸出限制
- ✅ **程式碼重用**: 利用 pubmed-search 已有的 Biopython Entrez 實現
- ✅ **單一 API 呼叫**: 用戶只需呼叫 `batch_import_from_pubmed(pmids)`

---

## 📦 Metadata Mapping: pubmed-search → Zotero

### pubmed-search 欄位 → Zotero Schema

| pubmed-search 欄位 | Zotero Field | 說明 |
|-------------------|--------------|------|
| `pmid` | `extra` (PMID: xxx) | |
| `title` | `title` | |
| `abstract` | `abstractNote` | ✅ 完整! |
| `authors_full[].fore_name` | `creators[].firstName` | |
| `authors_full[].last_name` | `creators[].lastName` | |
| `journal` | `publicationTitle` | |
| `year` + `month` + `day` | `date` | 格式化為 YYYY-MM-DD |
| `volume` | `volume` | |
| `issue` | `issue` | |
| `pages` | `pages` | |
| `doi` | `DOI` | |
| `pmc_id` | `extra` (PMCID: xxx) | |
| `issn` | `ISSN` | |
| `language` | `language` | |
| `keywords` | `tags[]` | |
| `mesh_terms` | `tags[]` (prefix: MeSH:) | |
| `publication_types` | `extra` | |
| `affiliations` | `extra` | ⚠️ pubmed-search 目前未提取 |

### SearchResult 欄位定義 (from pubmed_search.client)

```python
@dataclass
class SearchResult:
    pmid: str
    title: str
    abstract: str          # ✅ FULL text, not truncated!
    authors: list[str]     # ["Bellini V", "Bignami E"]
    authors_full: list[AuthorInfo]  # With fore_name, last_name
    journal: str
    year: int
    month: str | None
    day: str | None
    volume: str | None
    issue: str | None
    pages: str | None
    doi: str | None
    pmc_id: str | None
    issn: str | None
    language: str | None
    keywords: list[str]    # Author-provided keywords
    mesh_terms: list[str]  # Controlled vocabulary
    publication_types: list[str]
    # affiliations: 目前未提取
```

---

## 📦 Complete Metadata Mapping (存就存最完整的!)

### PubMed E-utilities XML → Zotero Schema

| PubMed XML Path | Zotero Field | Example | Priority |
|-----------------|--------------|---------|----------|
| `PMID` | `extra` (PMID: xxx) | 38353755 | ⭐ P0 |
| `ArticleTitle` | `title` | Artificial Intelligence in... | ⭐ P0 |
| `Abstract/AbstractText` | `abstractNote` | **完整摘要** (不截斷!) | ⭐ P0 |
| `Author/LastName` + `ForeName` | `creators[]` | Bellini Valentina | ⭐ P0 |
| `Journal/Title` | `publicationTitle` | Journal of medical systems | ⭐ P0 |
| `PubDate/Year` | `date` | 2024 | ⭐ P0 |
| `ELocationID[@EIdType="doi"]` | `DOI` | 10.1007/s10916-024-02038-2 | ⭐ P0 |
| `ArticleId[@IdType="pmc"]` | `extra` (PMCID: xxx) | PMC10867065 | ⭐ P0 |
| `Volume` | `volume` | 48 | P1 |
| `Issue` | `issue` | 1 | P1 |
| `MedlinePgn` / `StartPage` | `pages` | 19 | P1 |
| `ISSN` | `ISSN` | 1573-689X | P1 |
| `AffiliationInfo/Affiliation` | `extra` (多行) | University of Parma... | P1 |
| `KeywordList/Keyword` | `tags[]` | ["AI", "Machine learning"...] | P1 |
| `MeshHeading/DescriptorName` | `tags[]` (prefix: MeSH:) | ["MeSH: Operating Rooms"...] | P2 |
| `PublicationType` | `extra` | Systematic Review | P2 |
| `Language` | `language` | eng | P2 |
| `ArticleDate` | `date` (precise) | 2024-02-14 | P2 |
| `CoiStatement` | `extra` | Conflict of interest... | P3 |
| `ReferenceList` | (future: linked items) | - | P3 |

### Zotero Item Schema (Complete)

```python
def pubmed_to_zotero_item(pubmed_data: dict) -> dict:
    """Convert PubMed metadata to Zotero journalArticle schema"""

    return {
        "itemType": "journalArticle",

        # === P0: Core Fields (必填) ===
        "title": pubmed_data["title"],
        "creators": [
            {
                "creatorType": "author",
                "firstName": author["forename"],
                "lastName": author["lastname"]
            }
            for author in pubmed_data["authors"]
        ],
        "abstractNote": pubmed_data["abstract"],  # 完整摘要!
        "publicationTitle": pubmed_data["journal"],
        "date": pubmed_data["date"],  # YYYY-MM-DD or YYYY
        "DOI": pubmed_data.get("doi"),

        # === P1: Publication Details ===
        "volume": pubmed_data.get("volume"),
        "issue": pubmed_data.get("issue"),
        "pages": pubmed_data.get("pages"),
        "ISSN": pubmed_data.get("issn"),
        "language": pubmed_data.get("language", "eng"),

        # === P1: Identifiers & URLs ===
        "url": f"https://pubmed.ncbi.nlm.nih.gov/{pubmed_data['pmid']}/",

        # === P1-P2: Tags (Keywords + MeSH) ===
        "tags": [
            # User keywords
            *[{"tag": kw} for kw in pubmed_data.get("keywords", [])],
            # MeSH terms with prefix
            *[{"tag": f"MeSH: {mesh}"} for mesh in pubmed_data.get("mesh_terms", [])]
        ],

        # === P2: Extra Field (structured) ===
        "extra": _build_extra_field(pubmed_data),

        # === Attachments (handled separately) ===
        # PDF attachment added via attach_pmc_pdfs tool
    }


def _build_extra_field(pubmed_data: dict) -> str:
    """Build structured Extra field for additional metadata"""

    lines = []

    # Identifiers
    lines.append(f"PMID: {pubmed_data['pmid']}")
    if pubmed_data.get("pmc_id"):
        lines.append(f"PMCID: {pubmed_data['pmc_id']}")

    # Publication type
    if pubmed_data.get("pub_types"):
        lines.append(f"Publication Type: {', '.join(pubmed_data['pub_types'])}")

    # Affiliations (first 3, truncate if too long)
    if pubmed_data.get("affiliations"):
        lines.append("Affiliations:")
        for i, aff in enumerate(pubmed_data["affiliations"][:3]):
            lines.append(f"  {i+1}. {aff[:200]}")  # Truncate long affiliations

    # Grant info (if available)
    if pubmed_data.get("grants"):
        lines.append(f"Grants: {', '.join(pubmed_data['grants'][:3])}")

    return "\n".join(lines)
```

### Example: Complete Zotero Item

```json
{
    "itemType": "journalArticle",
    "title": "Artificial Intelligence in Operating Room Management",
    "creators": [
        {"creatorType": "author", "firstName": "Valentina", "lastName": "Bellini"},
        {"creatorType": "author", "firstName": "Michele", "lastName": "Russo"},
        {"creatorType": "author", "firstName": "Tania", "lastName": "Domenichetti"},
        {"creatorType": "author", "firstName": "Matteo", "lastName": "Panizzi"},
        {"creatorType": "author", "firstName": "Simone", "lastName": "Allai"},
        {"creatorType": "author", "firstName": "Elena Giovanna", "lastName": "Bignami"}
    ],
    "abstractNote": "This systematic review examines the recent use of artificial intelligence, particularly machine learning, in the management of operating rooms. A total of 22 selected studies from February 2019 to September 2023 are analyzed. The review emphasizes the significant impact of AI on predicting surgical case durations, optimizing post-anesthesia care unit resource allocation, and detecting surgical case cancellations. Machine learning algorithms such as XGBoost, random forest, and neural networks have demonstrated their effectiveness in improving prediction accuracy and resource utilization. However, challenges such as data access and privacy concerns are acknowledged. The review highlights the evolving nature of artificial intelligence in perioperative medicine research and the need for continued innovation to harness artificial intelligence's transformative potential for healthcare administrators, practitioners, and patients. Ultimately, artificial intelligence integration in operative room management promises to enhance healthcare efficiency and patient outcomes.",
    "publicationTitle": "Journal of medical systems",
    "date": "2024-02-14",
    "DOI": "10.1007/s10916-024-02038-2",
    "volume": "48",
    "issue": "1",
    "pages": "19",
    "ISSN": "1573-689X",
    "language": "eng",
    "url": "https://pubmed.ncbi.nlm.nih.gov/38353755/",
    "tags": [
        {"tag": "Artificial intelligence"},
        {"tag": "Machine learning"},
        {"tag": "Management"},
        {"tag": "Operating room"},
        {"tag": "Perioperative"},
        {"tag": "MeSH: Operating Rooms"},
        {"tag": "MeSH: Machine Learning"},
        {"tag": "MeSH: Efficiency, Organizational"}
    ],
    "extra": "PMID: 38353755\nPMCID: PMC10867065\nPublication Type: Journal Article, Systematic Review\nAffiliations:\n  1. Anesthesiology, Intensive Care and Pain Medicine Division, Department of Medicine and Surgery, University of Parma, Parma, 43126, Italy."
}
```

---

## 🧪 Test Cases

### Unit Tests

| Test Case | Input | Expected Output |
|-----------|-------|-----------------|
| Single PMID | `pmids="38353755"` | 1 article imported |
| Multiple PMIDs | `pmids="38353755,37864754"` | 2 articles imported |
| Invalid PMID | `pmids="99999999"` | failed=1, error message |
| Duplicate check | Import same PMID twice | Second import: skipped=1 |
| With tags | `tags=["AI", "2024"]` | Articles have tags |
| Empty input | `pmids=""` | Error: no PMIDs provided |
| Malformed input | `pmids="abc,def"` | Error: invalid PMID format |

### Integration Tests

| Test Case | Description |
|-----------|-------------|
| Full workflow | Search → Import → Verify in Zotero |
| Large batch | Import 50 articles at once |
| Network failure | Handle PubMed API timeout |
| Zotero offline | Handle Zotero not running |

---

## 📁 File Structure Changes

```
mcp-server/src/zotero_mcp/
├── infrastructure/
│   ├── mcp/
│   │   ├── tools.py              # Existing read tools
│   │   ├── write_tools.py        # Existing write tools
│   │   ├── smart_tools.py        # Existing smart tools
│   │   ├── search_tools.py       # Existing integrated search
│   │   └── batch_tools.py        # NEW: batch import tools ⭐
│   │                              #   - batch_import_from_pubmed
│   │                              #   - import_ris_to_zotero
│   │                              #   - attach_pmc_pdfs
│   │
│   ├── mappers/                   # NEW: Data mapping ⭐
│   │   ├── __init__.py
│   │   └── pubmed_mapper.py      # SearchResult → Zotero schema
│   │
│   └── zotero_client/
│       └── client.py             # Add batch operations
│
├── domain/
│   └── entities/
│       └── batch_result.py       # NEW: BatchImportResult ⭐
│
└── application/
    └── use_cases/
        └── batch_import.py       # NEW: BatchImportUseCase ⭐

# pubmed-search library integration (submodule)
external/
└── pubmed-search-mcp/            # Git submodule (already exists!)
    └── src/
        └── pubmed_search/
            ├── client.py         # PubMedClient, SearchResult
            └── ...
```

**關鍵**: 透過 `sys.path.insert(0, "external/pubmed-search-mcp/src")`
直接 import `pubmed_search.client`，不需要複製程式碼！

---

## 🚀 Implementation Plan

### Phase 0: Setup Integration (Day 1)
- [ ] 確認 submodule `external/pubmed-search-mcp` 已 clone
- [ ] 新增 setup code 在 `batch_tools.py` import pubmed_search
- [ ] 或者在 `pyproject.toml` 設定 editable install

### Phase 1: Core Infrastructure (Day 1-2)
- [ ] Create `pubmed_mapper.py` (SearchResult → Zotero schema)
- [ ] Create `batch_result.py` domain entity
- [ ] Add batch duplicate checking to `zotero_client.py`

### Phase 2: Primary Tool (Day 2-3)
- [ ] Implement `batch_import_from_pubmed` in `batch_tools.py`:
  ```python
  from pubmed_search.client import PubMedClient

  client = PubMedClient()
  articles = client.fetch_details(pmids)
  # Direct access to SearchResult objects!
  ```
- [ ] Unit tests for batch import
- [ ] Integration test with real Zotero

### Phase 3: Backup Tool (Day 3-4)
- [ ] Implement RIS parser
- [ ] Implement `import_ris_to_zotero`
- [ ] Unit tests for RIS import

### Phase 4: Documentation & Release (Day 4)
- [ ] Update README with new tools
- [ ] Update CHANGELOG
- [ ] Tag v1.7.0 release

---

## 🔒 Security Considerations

| Concern | Mitigation |
|---------|------------|
| Large batch size | Limit to 100 articles per call |
| Malicious RIS content | Sanitize input, validate format |
| Network timeouts | Set reasonable timeouts (30s), retry logic |

---

## 📈 Success Metrics

| Metric | Target |
|--------|--------|
| Batch import speed | 50 articles in < 30 seconds |
| Success rate | > 95% for valid articles |
| Duplicate detection accuracy | > 99% |
| User workflow reduction | 50 calls → 1 call |

---

## ✅ Design Decisions (Confirmed 2025-12-12)

| Question | Decision | Rationale |
|----------|----------|----------|
| **Collection support** | ✅ Add `collection_key` parameter | Allow direct organization during import |
| **Progress reporting** | ✅ Wait for completion, return summary | Keep implementation simple, avoid complexity |
| **Conflict resolution** | ✅ Add with warning flag | Don't lose data, let user decide later |

### Decision Details

#### 1. Collection Support
```python
batch_import_from_pubmed(
    pmids="...",
    collection_key="EXSL84KZ"  # Optional: add to specific collection
)
```
- If `collection_key` provided → add items to that collection after import
- If not provided → add to "My Library" (default behavior)
- Implementation: Use Zotero Local API to add item to collection after creation

#### 2. Progress Reporting
```python
# Return complete summary at end
return {
    "success": True,
    "total": 50,
    "added": 47,
    "skipped": 2,
    "failed": 1,
    "warnings": 3,  # NEW: count of warning items
    "elapsed_time": 15.2
}
```
- Simple synchronous operation
- No intermediate progress updates
- Suitable for batches up to ~100 items

#### 3. Conflict Resolution
```python
# When DOI exists but title differs significantly
{
    "pmid": "12345678",
    "title": "New Title Here",
    "action": "added_with_warning",
    "warning": "DOI match found but title differs (similarity: 65%)",
    "existing_key": "ABC12345"  # Reference to existing item
}
```
- Add the item anyway (don't lose data)
- Flag with warning in result
- Include reference to potentially duplicate item
- User can manually review and merge later

---

## 🆕 Advanced Design: Agent Collaboration (v1.7.0)

### Collection Workflow: No Collection? Ask User!

When user wants to import but no collection exists, the MCP should guide the agent to ask:

```
┌─────────────────────────────────────────────────────────────────┐
│  User: "Import anesthesia AI papers to Zotero"                  │
│                                                                 │
│  Agent checks: list_collections() → []  (empty)                 │
│                                                                 │
│  MCP returns:                                                   │
│  {                                                              │
│    "status": "no_collection",                                   │
│    "prompt_user": true,                                         │
│    "message": "No collections found. Would you like to:",       │
│    "options": [                                                 │
│      "1. Create a new collection (name suggestion: '麻醉AI')",  │
│      "2. Import to My Library (organize later)",                │
│      "3. Let me suggest a collection name based on search"      │
│    ]                                                            │
│  }                                                              │
│                                                                 │
│  Agent asks user which option they prefer                       │
└─────────────────────────────────────────────────────────────────┘
```

#### New Tool: `suggest_collection_name`
```python
@mcp.tool()
async def suggest_collection_name(
    pmids: str | None = None,
    search_query: str | None = None
) -> dict:
    """
    Suggest a collection name based on article topics.

    Returns:
    {
        "suggestions": [
            "Anesthesia-AI (2024-2025)",
            "Machine Learning in Anesthesiology",
            "AI Clinical Applications"
        ],
        "common_keywords": ["artificial intelligence", "anesthesia", "machine learning"],
        "date_range": "2024-2025"
    }
    """
```

#### New Tool: `create_collection` (if Zotero API supports)
```python
@mcp.tool()
async def create_collection(
    name: str,
    parent_key: str | None = None
) -> dict:
    """
    Create a new Zotero collection.

    Note: Requires Zotero Connector API or manual creation.
    Returns instructions if API not available.
    """
```

---

### Conflict Resolution: Return JSON for Agent Discussion

When conflicts are found, return structured data for agent to discuss with user:

```python
class BatchImportResult(TypedDict):
    # ... existing fields ...

    # NEW: Structured conflict data for agent
    conflicts: list[ConflictItem]
    conflict_summary: str  # Human-readable summary for agent to relay

class ConflictItem(TypedDict):
    pmid: str
    new_title: str
    new_doi: str | None
    existing_item: dict  # {key, title, doi, date}
    similarity_score: float
    conflict_type: str  # "doi_match_title_differs", "title_similar_no_doi", etc.
    suggested_action: str  # "merge", "keep_both", "skip"
```

#### Example Response with Conflicts
```json
{
    "success": true,
    "total": 30,
    "added": 25,
    "skipped": 2,
    "warnings": 3,
    "conflicts": [
        {
            "pmid": "38353755",
            "new_title": "AI in Operating Room Management (Updated)",
            "new_doi": "10.1007/s10916-024-02038-2",
            "existing_item": {
                "key": "BIZDPR9V",
                "title": "Artificial Intelligence in Operating Room Management",
                "doi": "10.1007/s10916-024-02038-2",
                "date": "2024"
            },
            "similarity_score": 0.78,
            "conflict_type": "doi_match_title_differs",
            "suggested_action": "skip"
        }
    ],
    "conflict_summary": "Found 3 potential conflicts:\n- 2 articles have matching DOI but different titles\n- 1 article has similar title (78% match)\n\nWould you like to review these individually?"
}
```

Agent can then ask user:
> "I found 3 potential conflicts. For example, PMID 38353755 has the same DOI as an existing article but the title is slightly different. Would you like to: (1) Skip these, (2) Add anyway, (3) Review each one?"

---

### Fulltext/Abstract Check: Use pubmed-search-mcp (Already Exists!)

**pubmed-search-mcp already provides:**
- `analyze_fulltext_access(pmids)` - Check PMC availability for multiple articles
- `get_article_fulltext_links(pmid)` - Get fulltext URLs for single article

#### Example Response from pubmed-search
```json
{
  "summary": {
    "total": 30,
    "open_access": 12,
    "subscription": 15,
    "abstract_only": 3,
    "pmc_available": [
      {"pmid": "38353755", "pmc_pdf_url": "https://..."}
    ],
    "pmc_percentage": 40.0
  }
}
```

#### zotero-keeper Collaboration: Download & Attach PDFs

**NEW Tool in zotero-keeper: `attach_pmc_pdfs`**
```python
@mcp.tool()
async def attach_pmc_pdfs(
    pmids: str,
    item_keys: str | None = None  # Optional: map PMIDs to Zotero item keys
) -> dict:
    """
    Download PMC PDFs and attach to Zotero items.

    Workflow:
    1. Call pubmed-search's get_article_fulltext_links for each PMID
    2. Download PDFs from PMC
    3. Attach to corresponding Zotero items

    Returns:
    {
        "total": 12,
        "attached": 10,
        "failed": 2,
        "failed_items": [{"pmid": "...", "error": "..."}]
    }
    """
```

#### Workflow Integration
```
┌─────────────────────────────────────────────────────────────────┐
│  After batch_import_from_pubmed:                                │
│                                                                 │
│  Agent: "Import complete! 30 articles added."                   │
│                                                                 │
│  [pubmed] analyze_fulltext_access(pmids)                        │
│  → "12 articles have free PMC fulltext (40%)"                   │
│                                                                 │
│  Agent: "12 of your imported articles have free PDFs.           │
│          Would you like me to download and attach them?"        │
│                                                                 │
│  User: "Yes"                                                    │
│                                                                 │
│  [keeper] attach_pmc_pdfs(pmids="38353755,37864754,...")        │
│  → Downloads and attaches PDFs to Zotero items                  │
└─────────────────────────────────────────────────────────────────┘
```

#### Responsibility Split

| Task | MCP | Tool |
|------|-----|------|
| Check fulltext availability | pubmed-search | `analyze_fulltext_access` |
| Get fulltext URLs | pubmed-search | `get_article_fulltext_links` |
| Download & attach PDFs | zotero-keeper | `attach_pmc_pdfs` (NEW) |

---

## 🔗 MCP Integration Strategy

### Problem: How to unify pubmed-search + zotero-keeper?

Three approaches, from least to most invasive:

### Approach 1: System Prompt Instructions (Recommended) ✅

Add instructions to `.vscode/mcp.json` or agent system prompt:

```json
{
  "servers": {
    "zotero-keeper": {
      "type": "stdio",
      "command": "...",
      "instructions": "When user asks to search PubMed for literature to add to Zotero, prefer using zotero-keeper's integrated tools (search_and_import, batch_import_from_pubmed) over direct pubmed-search calls. This ensures duplicate checking and proper organization."
    }
  }
}
```

**Pros**: No code changes, flexible  
**Cons**: Agent may not always follow

### Approach 2: Tool Shadowing / Wrapping

zotero-keeper provides wrapper tools that internally call pubmed-search:

```python
# In zotero-keeper
@mcp.tool()
async def search_pubmed(
    query: str,
    limit: int = 20,
    min_year: int | None = None
) -> dict:
    """
    Search PubMed for articles (wrapper with Zotero integration).

    This is the PREFERRED way to search when working with Zotero.
    Automatically checks which articles you already own.

    For raw PubMed search without Zotero integration,
    use pubmed-search MCP directly.
    """
    # 1. Call pubmed-search's search_literature
    # 2. Check against Zotero library
    # 3. Return annotated results with "owned" flag
```

**Pros**: Seamless integration  
**Cons**: Tool name collision possible

### Approach 3: Resource-based Integration

Use MCP Resources to share state:

```python
# zotero-keeper exposes a resource
@mcp.resource("zotero://owned-pmids")
async def get_owned_pmids() -> str:
    """List of PMIDs already in Zotero library"""
    items = await zotero_client.search_items("")
    pmids = [item.get("pmid") for item in items if item.get("pmid")]
    return json.dumps(pmids)

# pubmed-search can read this resource to filter results
# (requires pubmed-search to support this)
```

**Pros**: Clean separation, shared state  
**Cons**: Requires both MCPs to coordinate

### Recommended Strategy: Hybrid

```
┌─────────────────────────────────────────────────────────────────┐
│                    RECOMMENDED APPROACH                          │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  1. System Prompt (immediate):                                  │
│     "For literature management, use zotero-keeper's             │
│      integrated tools instead of raw pubmed-search"             │
│                                                                 │
│  2. Tool Shadowing (v1.7.0):                                    │
│     zotero-keeper provides `search_pubmed_for_import`           │
│     that wraps pubmed-search with Zotero integration            │
│                                                                 │
│  3. Future (v2.0):                                              │
│     Consider merging into single MCP or using Resources         │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

---

## 📝 Updated Tool List (v1.7.0)

### New Tools

| Tool | Purpose | Priority |
|------|---------|----------|
| `batch_import_from_pubmed` | Batch import PMIDs | P0 (Core) |
| `import_ris_to_zotero` | Import RIS format | P1 |
| `attach_pmc_pdfs` | Download & attach PMC PDFs | P2 |
| `suggest_collection_name` | AI-assisted naming | P2 |
| `create_collection` | Create new collection | P2 |
| `search_pubmed_for_import` | Integrated search wrapper | P1 |

### Delegated to pubmed-search-mcp (DO NOT DUPLICATE)

| Tool | Purpose | Notes |
|------|---------|-------|
| `analyze_fulltext_access` | Check PMC/OA status | Already exists in pubmed-search |
| `get_article_fulltext_links` | Get fulltext URLs | Already exists in pubmed-search |

### Modified Tools

| Tool | Change |
|------|--------|
| `smart_add_reference` | Add `collection_key` parameter |
| `list_collections` | Add `prompt_for_creation` hint in response |

---

## 🔄 Updated Workflow (完整 Metadata 版本)

```
┌─────────────────────────────────────────────────────────────────┐
│  Complete Literature Import Workflow (v1.7.0)                   │
│  🎯 設計原則: 存就存最完整的!                                     │
└─────────────────────────────────────────────────────────────────┘

User: "Find and import 2024-2025 anesthesia AI papers to Zotero"

┌─────────────────────────────────────────────────────────────────┐
│ Step 1: Search via pubmed-search                                 │
├─────────────────────────────────────────────────────────────────┤
│ [pubmed] search_literature(                                     │
│     query="anesthesia artificial intelligence",                 │
│     min_year=2024, limit=50                                     │
│ )                                                               │
│ → Returns PMIDs + basic info (titles, authors)                  │
│ → "Found 50 articles matching your query"                       │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│ Step 2: Check Fulltext Availability                              │
├─────────────────────────────────────────────────────────────────┤
│ [pubmed] analyze_fulltext_access(pmids="...")                   │
│ → "25 have PMC fulltext (free PDF), 25 subscription only"       │
│ → Agent asks: "Import all 50, or only those with free fulltext?"│
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│ Step 3: Batch Import with COMPLETE Metadata                      │
├─────────────────────────────────────────────────────────────────┤
│ [keeper] batch_import_from_pubmed(                              │
│     pmids="38353755,37864754,...",                              │
│     tags=["Anesthesia-AI"],                                     │
│     collection_key="EXSL84KZ"                                   │
│ )                                                               │
│                                                                 │
│ 🔄 Internal Process:                                            │
│ ┌─────────────────────────────────────────────────────────────┐ │
│ │ 1. Direct Python Import from pubmed-search library          │ │
│ │    from pubmed_search.client import PubMedClient            │ │
│ │    articles = PubMedClient().fetch_details(pmids)           │ │
│ │                                                             │ │
│ │ 2. SearchResult 已包含完整資料:                                    │ │
│ │    ✓ Title, Authors (with affiliations!)                    │ │
│ │    ✓ Abstract (FULL - not truncated!)                       │ │
│ │    ✓ Journal, Volume, Issue, Pages                          │ │
│ │    ✓ DOI, PMID, PMCID                                       │ │
│ │    ✓ Keywords (author-provided)                             │ │
│ │    ✓ MeSH Terms (controlled vocabulary)                     │ │
│ │    ✓ Publication Type, Language                             │ │
│ │                                                             │ │
│ │ 3. Duplicate check against Zotero                           │ │
│ │    → Match by DOI/PMID/Title                                │ │
│ │                                                             │ │
│ │ 4. Map to Zotero schema:                                    │ │
│ │    - title → title                                          │ │
│ │    - authors → creators[]                                   │ │
│ │    - abstract → abstractNote (完整!)                        │ │
│ │    - keywords + MeSH → tags[]                               │ │
│ │    - PMID/PMCID/affiliations → extra                        │ │
│ │                                                             │ │
│ │ 5. Batch write to Zotero via Connector API                  │ │
│ └─────────────────────────────────────────────────────────────┘ │
│                                                                 │
│ → Result: added=47, skipped=2 (duplicates), warnings=1          │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│ Step 4: Download PDFs (Optional)                                 │
├─────────────────────────────────────────────────────────────────┤
│ Agent: "47 articles imported! 25 have free PMC fulltext.        │
│         Would you like me to download and attach the PDFs?"     │
│                                                                 │
│ User: "Yes, download them"                                      │
│                                                                 │
│ [keeper] attach_pmc_pdfs(pmids="38353755,37864754,...")         │
│ → Downloads PDFs from PMC                                       │
│ → Attaches to corresponding Zotero items                        │
│ → Result: attached=23, failed=2 (PDF not available)             │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│ Final Result in Zotero:                                          │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│ Collection: 麻醉AI (2024-2025)                                  │
│ ├── 📄 Artificial Intelligence in Operating Room Management     │
│ │   ├── Authors: Bellini V, Russo M, Domenichetti T, et al.    │
│ │   ├── Abstract: This systematic review examines... (完整!)   │
│ │   ├── Tags: AI, Machine learning, MeSH: Operating Rooms...   │
│ │   ├── PMID: 38353755 | PMCID: PMC10867065                    │
│ │   └── 📎 PDF (attached from PMC)                              │
│ │                                                               │
│ ├── 📄 Machine Learning for Anesthesia...                       │
│ │   └── ...                                                     │
│ └── ... (47 total articles)                                     │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

### Before vs After

| Aspect | v1.6.0 (Before) | v1.7.0 (After) |
|--------|-----------------|----------------|
| **Import Method** | One by one (N API calls) | Batch (1 call) |
| **Abstract** | Manual entry | ✅ FULL, automatic |
| **Keywords** | Manual | ✅ Author keywords + MeSH |
| **Affiliations** | None | ✅ In extra field |
| **PDF Attachment** | Manual | ✅ Automatic from PMC |
| **Duplicate Check** | Per-item | ✅ Batch |
| **Time for 50 articles** | ~10 minutes | ~30 seconds |

---

## 📝 Appendix

### A. NCBI E-utilities Reference
- Base URL: `https://eutils.ncbi.nlm.nih.gov/entrez/eutils/`
- efetch: `efetch.fcgi?db=pubmed&id=PMID&rettype=xml`
- Rate limit: 3 requests/second without API key, 10 with key

### B. Zotero Connector API Reference
- saveItems: `POST /connector/saveItems`
- Payload: `{ "items": [...], "uri": "..." }`

### C. RIS Format Reference
```
TY  - JOUR          (Type)
TI  - Title         (Title)
AU  - Author        (Author, repeatable)
JO  - Journal       (Journal)
PY  - 2024          (Year)
VL  - 1             (Volume)
IS  - 2             (Issue)
SP  - 100           (Start Page)
EP  - 110           (End Page)
DO  - 10.1000/xyz   (DOI)
AN  - 12345678      (PMID in PubMed exports)
AB  - Abstract...   (Abstract)
KW  - keyword       (Keywords, repeatable)
ER  -               (End of Record)
```
