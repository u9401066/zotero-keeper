# 統一學術搜尋研究報告

> **版本**: 1.3.0
> **日期**: 2026-01-12
> **狀態**: 研究完成，待實作

---

## 📋 目錄

1. [執行摘要](#-執行摘要)
2. [核心設計理念](#-核心設計理念)
3. [競爭者分析](#-競爭者分析)
4. [可用 API 資源](#-可用-api-資源)
5. [統一搜尋架構設計](#-統一搜尋架構設計)
6. [實作路線圖](#-實作路線圖)
7. [技術規格](#-技術規格)
8. [Agent-MCP 協作模式](./AGENT_MCP_COLLABORATION.md) ← 🆕 **獨立文件**
9. [開源專案分析](#-開源專案分析)

---

## 📌 執行摘要

### 問題陳述

現有的 `pubmed-search-mcp` 提供 35+ 個 MCP 工具，每個工具對應一個資料源或功能。這種設計的問題：

```
❌ 當前設計（分散式）
┌─────────────────────────────────────────────────────────────┐
│  Agent 需要自己決定：                                        │
│  - search_literature (PubMed)                               │
│  - search_europe_pmc (Europe PMC)                           │
│  - search_core (CORE)                                       │
│  - search_clinvar (ClinVar)                                 │
│  - search_gene (NCBI Gene)                                  │
│  - ... 還有更多                                              │
│                                                             │
│  問題：Agent 需要知道何時用哪個工具，增加複雜度               │
└─────────────────────────────────────────────────────────────┘
```

### 解決方案

**統一入口 + 後端自動分流** —— 像 Google 一樣，用戶只需要一個搜尋入口：

```
✅ 目標設計（統一式）
┌─────────────────────────────────────────────────────────────┐
│                    unified_search()                          │
│                          ↓                                   │
│              ┌──────────────────────┐                        │
│              │   Query Analyzer     │ ← 分析查詢意圖          │
│              └──────────┬───────────┘                        │
│                         ↓                                    │
│         ┌───────────────┼───────────────┐                    │
│         ↓               ↓               ↓                    │
│    ┌─────────┐    ┌─────────┐    ┌─────────┐                │
│    │ PubMed  │    │ CrossRef│    │ CORE    │                │
│    └────┬────┘    └────┬────┘    └────┬────┘                │
│         └───────────────┼───────────────┘                    │
│                         ↓                                    │
│              ┌──────────────────────┐                        │
│              │   Result Aggregator  │ ← 合併、去重、排序      │
│              └──────────────────────┘                        │
│                         ↓                                    │
│                  統一格式結果                                 │
└─────────────────────────────────────────────────────────────┘
```

### 關鍵決策

| 決策 | 選擇 | 理由 |
|------|------|------|
| 搜尋入口 | 單一 `unified_search` | 降低 Agent 認知負擔 |
| 資料源選擇 | 後端自動分流 | 像 Google，不需用戶懂技術 |
| 結果格式 | 統一 Article 物件 | 跨來源一致性 |
| OA 連結 | 自動附加 | 每篇文章自動查 Unpaywall |

---

## 🎯 核心設計理念

### 1. 單一入口原則

> **「你不會希望 Google 教你自己一個一個網站去搜尋」**

用戶（或 Agent）只需要：

```python
# 簡單搜尋
results = unified_search("remimazolam ICU sedation")

# 進階搜尋
results = unified_search(
    query="remimazolam ICU sedation",
    filters={
        "year_from": 2020,
        "article_types": ["RCT", "Meta-Analysis"],
        "open_access_only": True
    }
)
```

### 2. 智能分流

後端根據查詢特徵自動決定搜尋哪些來源：

| 查詢特徵 | 自動選擇的來源 |
|---------|---------------|
| 一般醫學查詢 | PubMed (主) + CrossRef (補) |
| 含 DOI | CrossRef (直接解析) |
| 臨床試驗相關 | PubMed + ClinicalTrials.gov |
| 基因/藥物名稱 | PubMed + NCBI Gene/PubChem |
| 預印本需求 | bioRxiv + medRxiv |
| OA 需求 | CORE + Europe PMC |

### 3. 結果增強

每個搜尋結果自動增強：

```python
@dataclass
class UnifiedArticle:
    # 核心識別
    pmid: Optional[str]
    doi: Optional[str]

    # 基本資訊
    title: str
    authors: List[str]
    journal: str
    year: int
    abstract: str

    # 自動增強
    oa_url: Optional[str]        # ← Unpaywall 自動查詢
    pdf_url: Optional[str]       # ← PMC/CORE 自動查詢
    citation_count: Optional[int] # ← CrossRef/iCite
    mesh_terms: List[str]        # ← PubMed

    # 來源追蹤
    sources: List[str]           # 來自哪些 API
    relevance_score: float       # 綜合相關性分數
```

---

## 🥊 競爭者分析

### 商用工具概覽

| 競爭者 | 定位 | 資料規模 | 年費 | 核心優勢 |
|--------|------|---------|------|---------|
| **OpenEvidence** | 醫療專業 | NEJM/JAMA/NCCN | 免費(美國HCP) | 專有內容授權 |
| **Elicit** | 研究輔助 | 138M+ 論文 | $120-240 | 自動化系統回顧 |
| **SciSpace** | 全方位 | 多源整合 | $120 | Agent + 寫作 |
| **Consensus** | 證據搜尋 | 學術論文 | $96 | 問答式搜尋 |

### 商用工具優勢（我們無法複製）

1. **專有內容授權** - NEJM、JAMA 獨家（商業壁壘）
2. **大規模基礎設施** - 138M+ 論文索引（需要資金）
3. **精煉的 UX** - 專業設計團隊（需要時間）
4. **專門訓練模型** - 99.4% 萃取準確率（需要資料）

### 我們的差異化定位

| 維度 | 商用工具 | Zotero-Keeper |
|------|---------|---------------|
| **目標用戶** | 一般研究者 | Zotero 重度用戶、醫學研究者 |
| **資料控制** | 雲端託管 | 100% 本地執行 |
| **整合性** | 獨立封閉 | 深度整合 Zotero |
| **客製化** | 有限 | 無限（開源 MCP） |
| **專業度** | 通用 | 醫學文獻專精 |
| **成本** | $96-240/年 | **免費** |
| **隱私** | 資料上傳 | HIPAA/GDPR 友善 |

### 定位聲明

> **Zotero-Keeper + PubMed-Search-MCP** 是為 **Zotero 用戶** 和 **醫學研究者** 設計的 **本地化、可客製化、專業級** 文獻搜尋與管理 AI 助手。
>
> 我們不追求成為「最大」的平台，而是成為「最適合特定工作流」的工具。

---

## 🔌 可用 API 資源

### API 總覽

| API | 免費 | Rate Limit | 資料規模 | 整合狀態 |
|-----|------|-----------|---------|---------|
| **PubMed** | ✅ | 10/s (API Key) | 36M+ | ✅ 已整合 |
| **Europe PMC** | ✅ | 無限制 | 33M+ | ✅ 已整合 |
| **CORE** | ✅ | 10,000/天 | 200M+ | ✅ 已整合 |
| **OpenAlex** | ✅ | 100,000/天 | 250M+ | ✅ **已整合** |
| **Semantic Scholar** | ✅ | 100/s (API Key) | 214M+ | ✅ **已整合** |
| **NCBI Gene** | ✅ | 10/s | 基因資料 | ✅ 已整合 |
| **PubChem** | ✅ | 無限制 | 化合物 | ✅ 已整合 |
| **ClinVar** | ✅ | 10/s | 臨床變異 | ✅ 已整合 |
| **CrossRef** | ✅ | 10/s (polite) | 118M+ | 🔲 待整合 |
| **Unpaywall** | ✅ | 100,000/天 | 30M+ OA | 🔲 待整合 |
| **ClinicalTrials.gov** | ✅ | 無限制 | 500K+ 試驗 | 🔲 待整合 |
| **bioRxiv/medRxiv** | ✅ | 無限制 | 預印本 | 🔲 待整合 |
| **ORCID** | ✅ | 視級別 | 作者資料 | ⚪ 可選 |
| **DOAJ** | ✅ | 無限制 | OA 期刊 | ⚪ 可選 |

> **💡 Note**: OpenAlex 和 Semantic Scholar 已於 v0.1.x 整合完成，在 `sources/` 目錄下有完整客戶端。

### 不可用 API

| API | 原因 | 替代方案 |
|-----|------|---------|
| **UpToDate** | 企業授權制 | PubMed Clinical Queries |
| **Cochrane** | 無公開 API | PubMed 搜尋 Cochrane Reviews |
| **Scopus/WoS** | 付費訂閱 | OpenAlex (免費替代) |

### 核心 API 詳情

#### CrossRef（🔲 待整合 - 高優先）

```python
# 功能：DOI 元數據、引用連結、期刊資訊
# 完全免費，建議使用 Polite Pool (加入 email 提高 rate limit)
# 文件：https://api.crossref.org/swagger-ui/index.html

# Rate Limits:
# - 無認證: 50 req/sec
# - Polite Pool (加 email): 更高限制
# - 過載時返回 429/403

import urllib.request
import urllib.parse
import json

def search_crossref(query: str, email: str, rows: int = 20) -> list:
    """搜尋 CrossRef works"""
    base_url = "https://api.crossref.org/works"
    params = {
        "query": query,
        "rows": rows,
        "mailto": email,  # Polite Pool
        "select": "DOI,title,author,container-title,published,is-referenced-by-count"
    }
    url = f"{base_url}?{urllib.parse.urlencode(params)}"

    request = urllib.request.Request(url)
    request.add_header("User-Agent", f"pubmed-search-mcp/1.0 (mailto:{email})")

    with urllib.request.urlopen(request) as response:
        data = json.loads(response.read())
        return data["message"]["items"]

def get_crossref_by_doi(doi: str, email: str) -> dict:
    """用 DOI 取得元數據"""
    encoded_doi = urllib.parse.quote(doi, safe="")
    url = f"https://api.crossref.org/works/{encoded_doi}?mailto={email}"
    # ...

# 主要端點：
# GET /works/{doi}           - 取得單篇
# GET /works?query=...       - 搜尋
# GET /works?filter=from-pub-date:2023-01-01  - 過濾
# GET /journals/{issn}/works - 期刊內搜尋

# 可用過濾器：
# - from-pub-date, until-pub-date
# - type (journal-article, book-chapter, etc.)
# - has-abstract, has-references
# - is-update (排除更正版)
```

#### Unpaywall（🔲 待整合 - 高優先）

```python
# 功能：查找 OA 版本、PDF 連結
# 完全免費，只需 email
# 文件：https://unpaywall.org/products/api

# Rate Limits:
# - 100,000 次/天
# - 超量建議下載完整快照

import urllib.request
import urllib.parse
import json

def get_oa_link(doi: str, email: str) -> dict | None:
    """查詢 DOI 的 OA 狀態和連結"""
    encoded_doi = urllib.parse.quote(doi, safe="")
    url = f"https://api.unpaywall.org/v2/{encoded_doi}?email={email}"

    try:
        with urllib.request.urlopen(url) as response:
            return json.loads(response.read())
    except:
        return None

# 返回結構 (DOI Object):
# {
#   "doi": "10.1038/nature12373",
#   "is_oa": true,
#   "best_oa_location": {
#     "url_for_pdf": "https://...",
#     "url_for_landing_page": "https://...",
#     "license": "cc-by",
#     "host_type": "publisher"  # publisher/repository
#   },
#   "oa_locations": [...],  # 所有 OA 版本
#   "oa_status": "gold"     # gold/green/bronze/hybrid/closed
# }

def search_unpaywall(query: str, email: str, is_oa: bool = True) -> list:
    """搜尋 Unpaywall (標題搜尋)"""
    params = {
        "query": query,
        "is_oa": "true" if is_oa else "false",
        "email": email
    }
    url = f"https://api.unpaywall.org/v2/search?{urllib.parse.urlencode(params)}"

    with urllib.request.urlopen(url) as response:
        data = json.loads(response.read())
        return [item["response"] for item in data["results"]]

# 搜尋語法：
# - 空格分隔詞彙會 AND
# - "quoted text" 精確片語
# - OR 替換預設 AND
# - -term 排除
```

#### OpenAlex（✅ 已整合）

```python
# 位置: src/pubmed_search/sources/openalex.py
# 完整實作已存在，以下是使用範例：

from pubmed_search.sources import get_openalex_client

client = get_openalex_client(email="your@email.com")

# 搜尋
results = client.search(
    query="remimazolam sedation",
    limit=20,
    min_year=2020,
    open_access_only=True,
    is_doaj=False,  # DOAJ 期刊過濾
    sort="cited_by_count:desc"  # 按引用數排序
)

# 取得單篇 (支援 DOI, PMID, OpenAlex ID)
paper = client.get_work("doi:10.1093/bja/aez321")
paper = client.get_work("pmid:31234567")

# 取得引用
citations = client.get_citations("doi:10.1093/bja/aez321", limit=10)

# 返回格式已正規化，與 PubMed 相容：
# {
#   "pmid": "31234567",
#   "doi": "10.1093/bja/aez321",
#   "title": "...",
#   "abstract": "...",  # 從 inverted index 重建
#   "authors": ["Name1", "Name2"],
#   "journal": "...",
#   "year": "2023",
#   "citation_count": 42,
#   "is_open_access": true,
#   "pdf_url": "https://...",
#   "_source": "openalex",
#   "_openalex_id": "W12345678"
# }
```

#### Semantic Scholar（✅ 已整合）

```python
# 位置: src/pubmed_search/sources/semantic_scholar.py
# 完整實作已存在，以下是使用範例：

from pubmed_search.sources import get_semantic_scholar_client

client = get_semantic_scholar_client(api_key=None)  # API Key 可選

# 搜尋
results = client.search(
    query="deep learning medical imaging",
    limit=20,
    min_year=2020,
    max_year=2024,
    open_access_only=True
)

# 取得單篇 (支援 S2 ID, DOI, PMID)
paper = client.get_paper("DOI:10.1093/bja/aez321")
paper = client.get_paper("PMID:31234567")

# 取得引用 / 參考文獻
citations = client.get_citations("DOI:10.1093/bja/aez321", limit=10)
references = client.get_references("DOI:10.1093/bja/aez321", limit=10)

# 返回格式已正規化：
# {
#   "pmid": "31234567",
#   "doi": "10.1093/bja/aez321",
#   "arxiv_id": "2301.12345",  # 額外欄位
#   "citation_count": 42,
#   "influential_citations": 5,  # S2 特有指標
#   "is_open_access": true,
#   "pdf_url": "https://...",
#   "_source": "semantic_scholar",
#   "_s2_id": "abc123..."
# }
```

#### 跨來源搜尋（✅ 已整合）

```python
# 位置: src/pubmed_search/sources/__init__.py
# 已有 cross_search() 多來源聚合功能：

from pubmed_search.sources import cross_search

# 跨多來源搜尋
result = cross_search(
    query="remimazolam sedation",
    sources=["semantic_scholar", "openalex", "europe_pmc", "core"],
    limit_per_source=5,
    min_year=2020,
    open_access_only=True,
    deduplicate=True  # 自動去重
)

# 返回結構：
# {
#   "results": [...],  # 已去重的合併結果
#   "by_source": {
#     "semantic_scholar": [...],
#     "openalex": [...],
#     "europe_pmc": [...],
#     "core": [...]
#   },
#   "stats": {
#     "total": 15,
#     "sources_searched": ["semantic_scholar", "openalex", ...],
#     "per_source": {"semantic_scholar": 5, "openalex": 4, ...}
#   }
# }
```

#### ClinicalTrials.gov（中優先）

```python
# 功能：臨床試驗搜尋
# 套件：pip install pytrials

from pytrials.client import ClinicalTrials
ct = ClinicalTrials()

studies = ct.get_study_fields(
    search_expr="remimazolam AND sedation",
    fields=["NCT Number", "Study Title", "Phase", "Status"],
    max_studies=100
)
```

---

## 🏗 統一搜尋架構設計

### 架構圖

```
┌─────────────────────────────────────────────────────────────────────────┐
│                         UNIFIED SEARCH GATEWAY                          │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│   MCP Tool: unified_search(query, options)                              │
│                         │                                               │
│                         ▼                                               │
│   ┌─────────────────────────────────────────────────────────────────┐   │
│   │                    QUERY ANALYZER                                │   │
│   │  - 檢測查詢類型（一般/DOI/臨床試驗/基因/藥物）                    │   │
│   │  - 決定搜尋策略（哪些來源、優先順序）                            │   │
│   │  - MeSH 擴展（已有）                                             │   │
│   └─────────────────────────────────────────────────────────────────┘   │
│                         │                                               │
│          ┌──────────────┼──────────────┐                                │
│          ▼              ▼              ▼                                │
│   ┌───────────┐  ┌───────────┐  ┌───────────┐                          │
│   │  PubMed   │  │  CrossRef │  │  OpenAlex │  ... more backends       │
│   │  Client   │  │  Client   │  │  Client   │                          │
│   └─────┬─────┘  └─────┬─────┘  └─────┬─────┘                          │
│         │              │              │                                 │
│         └──────────────┼──────────────┘                                 │
│                        ▼                                                │
│   ┌─────────────────────────────────────────────────────────────────┐   │
│   │                   RESULT AGGREGATOR                              │   │
│   │  - 格式正規化（統一 Article 物件）                               │   │
│   │  - 去重（DOI/PMID 為主鍵）                                       │   │
│   │  - 合併增強（OA 連結、引用數）                                   │   │
│   │  - 相關性排序                                                    │   │
│   └─────────────────────────────────────────────────────────────────┘   │
│                         │                                               │
│                         ▼                                               │
│   ┌─────────────────────────────────────────────────────────────────┐   │
│   │                   ENRICHMENT LAYER                               │   │
│   │  - Unpaywall: 自動附加 OA 連結                                   │   │
│   │  - iCite: 自動附加引用指標                                       │   │
│   │  - PMC: 自動附加全文連結                                         │   │
│   └─────────────────────────────────────────────────────────────────┘   │
│                         │                                               │
│                         ▼                                               │
│                 List[UnifiedArticle]                                    │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘
```

### MCP 工具設計

#### 主要工具（對外）

```python
# 統一搜尋 - 唯一需要的搜尋入口
unified_search(
    query: str,                    # 搜尋詞
    limit: int = 20,               # 結果數量
    sources: List[str] = "auto",   # auto = 自動選擇
    filters: SearchFilters = None, # 過濾條件
    enrich: bool = True            # 自動增強（OA、引用）
) -> SearchResult

# 過濾條件
@dataclass
class SearchFilters:
    year_from: Optional[int]
    year_to: Optional[int]
    article_types: Optional[List[str]]  # RCT, Review, Meta-Analysis
    open_access_only: bool = False
    languages: Optional[List[str]]
    journals: Optional[List[str]]
```

#### 保留的專業工具

```python
# 這些工具仍然有價值，但不是搜尋入口

# 深入探索（找到重要文章後）
find_related_articles(pmid)      # 相似文章
find_citing_articles(pmid)       # 誰引用了這篇
get_article_references(pmid)     # 這篇引用了誰
build_citation_tree(pmid)        # 引用網路

# PICO 臨床問題（專業需求）
parse_pico(question)             # 解析臨床問題

# 匯出
prepare_export(pmids, format)    # RIS/BibTeX/CSV
```

#### 移除/合併的工具

```python
# 這些工具應該合併到 unified_search 的後端

# 移除（合併到統一搜尋）
- search_literature()      → unified_search(sources=["pubmed"])
- search_europe_pmc()      → unified_search(sources=["europe_pmc"])  
- search_core()            → unified_search(sources=["core"])
- search_gene()            → unified_search(query="BRCA1", auto_detect=gene)
- search_compound()        → unified_search(query="propofol", auto_detect=drug)
- search_clinvar()         → unified_search(query="...", sources=["clinvar"])

# 保留但變成內部使用
- generate_search_queries() → 內部使用，不暴露給 Agent
- merge_search_results()    → 內部使用
```

### 查詢分析器設計

```python
class QueryAnalyzer:
    """分析查詢意圖，決定搜尋策略"""

    def analyze(self, query: str) -> SearchStrategy:
        # 1. DOI 檢測
        if self._is_doi(query):
            return SearchStrategy(
                primary="crossref",
                secondary=["pubmed"],
                query_type="doi_lookup"
            )

        # 2. 臨床試驗檢測
        if self._is_clinical_trial(query):
            return SearchStrategy(
                primary="pubmed",
                secondary=["clinicaltrials"],
                query_type="clinical_trial"
            )

        # 3. 基因名稱檢測
        if self._is_gene(query):
            return SearchStrategy(
                primary="pubmed",
                secondary=["ncbi_gene"],
                enrich_with=["gene_info"]
            )

        # 4. 藥物名稱檢測
        if self._is_drug(query):
            return SearchStrategy(
                primary="pubmed",
                secondary=["pubchem"],
                enrich_with=["drug_info"]
            )

        # 5. 預設：醫學文獻搜尋
        return SearchStrategy(
            primary="pubmed",
            secondary=["crossref", "openalex"],
            parallel=True,
            enrich_with=["unpaywall", "icite"]
        )
```

---

## 📅 實作路線圖

### Phase 1: 核心整合（2026 Q1）

**目標**: 建立統一搜尋框架 + 整合剩餘高優先級 API

| 任務 | 工作量 | 狀態 | 備註 |
|------|--------|------|------|
| 設計 UnifiedArticle 資料模型 | 2h | 📋 | 參考現有 `_normalize_*()` |
| 實作 CrossRef Client | 4h | 📋 | 新增 |
| 實作 Unpaywall Client | 2h | 📋 | 新增，整合到 enricher |
| ~~實作 OpenAlex Client~~ | ~~4h~~ | ✅ | 已完成 (`sources/openalex.py`) |
| ~~實作 Semantic Scholar Client~~ | ~~4h~~ | ✅ | 已完成 (`sources/semantic_scholar.py`) |
| 重構 QueryAnalyzer | 3h | 📋 | 從 `strategy.py` 擴展 |
| 重構 ResultAggregator | 2h | 📋 | 基於現有 `cross_search()` |
| 實作 unified_search MCP tool | 4h | 📋 | 新 MCP 工具 |
| 測試與文檔 | 3h | 📋 | |
| **總計** | **~20h** | | ~~28h~~ → 20h (節省 8h) |

**已有基礎** (可直接利用):

- ✅ `OpenAlexClient` - 完整搜尋、取得單篇、引用功能
- ✅ `SemanticScholarClient` - 完整搜尋、引用、參考功能
- ✅ `cross_search()` - 多來源並行搜尋框架
- ✅ `_deduplicate_results()` - DOI/PMID/標題去重
- ✅ `_normalize_paper()` / `_normalize_work()` - 統一格式化

**交付物**:

- `unified_search()` MCP 工具
- CrossRef + Unpaywall 整合
- 自動 OA 連結附加

### Phase 2: 專業擴展（2026 Q2）

**目標**: 整合臨床試驗 + 預印本

| 任務 | 工作量 | 狀態 |
|------|--------|------|
| 整合 ClinicalTrials.gov | 4h | 📋 |
| 整合 bioRxiv/medRxiv | 4h | 📋 |
| QueryAnalyzer 增強 | 2h | 📋 |
| **總計** | **~10h** | |

### Phase 3: 智能增強（2026 Q3）

**目標**: AI 增強功能

| 任務 | 工作量 | 狀態 |
|------|--------|------|
| 自動摘要生成 | 8h | 💡 |
| 研究差距識別 | 8h | 💡 |
| 引用網路視覺化增強 | 4h | 💡 |

### VSX 設定擴展

```json
{
  "zoteroMcp.search.defaultSources": {
    "type": "array",
    "default": ["pubmed", "crossref", "openalex"],
    "description": "Default search sources for unified search"
  },
  "zoteroMcp.search.autoEnrich": {
    "type": "boolean",
    "default": true,
    "description": "Automatically enrich results with OA links and citations"
  },
  "zoteroMcp.unpaywall.email": {
    "type": "string",
    "description": "Email for Unpaywall API (required for OA lookup)"
  },
  "zoteroMcp.crossref.email": {
    "type": "string",
    "description": "Email for CrossRef Polite Pool (recommended)"
  }
}
```

---

## 🔧 技術規格

### 依賴套件

```toml
# pyproject.toml - 注意：專案使用 urllib 標準庫，不需額外 HTTP 客戶端

[project.dependencies]
# 核心依賴 (已有)
fastmcp = ">=0.3.0"       # MCP 框架

# 新增依賴 (Phase 1)
# 無！CrossRef 和 Unpaywall 使用 urllib 即可

[project.optional-dependencies]
# 臨床試驗整合 (Phase 2)
trials = [
    "pytrials>=1.0.0",    # ClinicalTrials.gov 客戶端
]

# NLP 增強 (Phase 3，可選)
nlp = [
    "scispacy>=0.5.0",    # 生物醫學 NLP
]
```

> **💡 設計原則**: 遵循專案現有風格，使用 Python 標準庫 `urllib` 而非 `requests`，
> 減少依賴、提高可移植性。OpenAlex 和 Semantic Scholar 客戶端已使用此模式。

### 環境變數

```bash
# 必須
NCBI_EMAIL=your@email.com          # PubMed API

# 建議
UNPAYWALL_EMAIL=your@email.com     # Unpaywall API
CROSSREF_EMAIL=your@email.com      # CrossRef Polite Pool
NCBI_API_KEY=your_key              # PubMed 高速率

# 可選
SEMANTIC_SCHOLAR_API_KEY=your_key  # Semantic Scholar
CORE_API_KEY=your_key              # CORE API
```

### 程式碼結構

```
src/pubmed_search/
├── mcp/
│   └── tools/
│       ├── unified_search.py    # 🆕 統一搜尋入口 (待實作)
│       ├── discovery.py         # 保留（深入探索）
│       ├── pico.py              # 保留（臨床問題）
│       └── export.py            # 保留（匯出）
├── sources/                      # 資料源客戶端
│   ├── __init__.py              # ✅ 已有 cross_search() 聚合邏輯
│   ├── europe_pmc.py            # ✅ 已整合
│   ├── core.py                  # ✅ 已整合
│   ├── ncbi_extended.py         # ✅ Gene/PubChem/ClinVar
│   ├── openalex.py              # ✅ 已整合 (OpenAlexClient)
│   ├── semantic_scholar.py      # ✅ 已整合 (SemanticScholarClient)
│   ├── crossref.py              # 🆕 待實作
│   ├── unpaywall.py             # 🆕 待實作
│   ├── clinicaltrials.py        # 🆕 待實作
│   └── biorxiv.py               # 🆕 待實作
├── aggregator/                   # 🆕 結果聚合 (待建立)
│   ├── __init__.py
│   ├── query_analyzer.py        # 查詢分析
│   ├── result_merger.py         # 結果合併 (部分邏輯已在 sources/__init__.py)
│   └── enricher.py              # 結果增強
└── models/
    └── unified_article.py       # 🆕 統一文章模型
```

> **💡 已有基礎**:
> - `sources/__init__.py` 已實作 `cross_search()` 函數，支援多來源並行搜尋
> - `sources/__init__.py` 已實作 `_deduplicate_results()` 去重邏輯
> - `OpenAlexClient` 和 `SemanticScholarClient` 已有 `_normalize_*()` 方法統一格式

---

## 🤖 Agent-MCP 協作模式

> **核心洞察**: Search MCP 本質是 **Search Aggregation Middle Layer**
> - Query Enhancement（查詢增強） 需要「理解」
> - Multi-source Dispatch（轉包分發） 需要「策略」
> - Result Aggregation（結果彙整） 需要「判斷」

### 設計哲學：MCP 是工具，Agent 是大腦

```

                        ITERATIVE PROTOCOL  

   Agent                          MCP  
      unified_search() ▶  

                              簡單查詢？  

              Yes  No  

              直接處理                     返回建議  
     ◀ 結果 ◀ needs_decision
      unified_search(decision=chosen) ▶  
     ◀ 最終結果  

```

### 三種協作模式

| 模式 | 適用場景 | MCP 行為 | Agent 負擔 |
|------|---------|---------|-----------|
| **Auto** | 簡單查詢 | 完全自主處理 | 無 |
| **Suggest** | 模糊查詢 | 返回建議選項 | 選擇 |
| **Delegate** | 複雜分析 | 返回原始資料 | 分析+決策 |

### Spec 完整性自評

| 面向 | 狀態 | 說明 |
|------|------|------|
| 執行摘要 | ✅ | 問題、解決方案、關鍵決策 |
| 設計理念 | ✅ | 單一入口、智能分流、結果增強 |
| 競爭者分析 | ✅ | 商用工具、差異化定位 |
| API 資源 | ✅ | 已整合、待整合、不可用 |
| 架構設計 | ✅ | MCP 工具、查詢分析器 |
| 實作路線圖 | ✅ | Phase 1-3、工時估算 |
| 技術規格 | ✅ | 依賴、環境變數、程式碼結構 |
| 開源專案分析 | ✅ | 5 個專案、可借鑑模式 |
| **Agent-MCP 協作** | ✅ | **本章節新增** |
| 錯誤處理/Fallback | 🔲 | 待補充詳細實作 |
| 測試策略 | 🔲 | 待補充 |
| 監控/可觀察性 | 🔲 | 待補充 |

---

## � 開源專案分析

> 分析 5 個相關 GitHub 專案，提取可借鏡的設計模式和功能。

### 專案價值總覽

| 專案 | 技術棧 | 核心功能 | 借鏡價值 | 優先級 |
|------|--------|---------|---------|--------|
| **[DW2-Cochrane-Chatbot](https://github.com/Iriide/DW2-Cochrane-Chatbot)** | Python, PyTorch, Transformers | RAG + 品質/信任評分 | ⭐⭐⭐⭐⭐ | 高 |
| **[cochrane-audit-engine](https://github.com/buildwithwhy/cochrane-audit-engine)** | Python, Streamlit, GPT-4o | PICO 提取、引文挖掘 | ⭐⭐⭐⭐⭐ | 高 |
| **[heycochrane](https://github.com/henryaj/heycochrane)** | Ruby, Python, Claude | CrossRef 日期、摘要生成 | ⭐⭐⭐ | 中 |
| **[scientific_research_tool](https://github.com/iCodator/scientific_research_tool)** | Python | Boolean 查詢編譯、多 DB | ⭐⭐⭐ | 中 |
| **[MedicalResearchSearchIndex](https://github.com/saivenkat98/MedicalResearchSearchIndex)** | Java, React | Cochrane 爬蟲 | ⭐ | 低 |

### 高價值模式詳解

#### 1. 品質與信任評分（DW2-Cochrane-Chatbot）

此專案使用 RAG 架構，關鍵創新在於 **多維度品質評估**：

```python
# 品質評分 - 可應用於 ResultAggregator
def score_answer(answer: str, question: str, valid_titles: list,
                 confidence: float, top_score: float) -> float:
    """
    多維度評分:
    - 關鍵詞匹配 (問題詞彙出現在答案中)
    - 答案長度 (足夠詳細但不冗長)
    - 不確定詞懲罰 (含 "不確定/可能" 等詞彙扣分)
    - 來源相關性 (是否引用有效來源)
    """
    question_keywords = set(question.lower().split()) - stop_words
    answer_words = set(answer.lower().split())
    keyword_matches = len(question_keywords & answer_words)

    uncertain_words = ["不確定", "可能", "也許", "uncertain", "maybe", "perhaps"]
    uncertain_count = sum(1 for w in uncertain_words if w in answer.lower())

    score = (
        keyword_matches * 2 +           # 關鍵詞匹配獎勵
        min(len(answer.split()), 30) -  # 長度分 (上限30)
        uncertain_count * 2             # 不確定詞懲罰
    )
    return max(0, score) / 100  # 正規化到 0-1

# 信任度評分 - 可應用於跨來源驗證
def compute_trust_score(answer: str, sources: list[str],
                        embed_fn: callable) -> float:
    """
    雙維度信任評估:
    - 文字重疊率 (答案內容是否來自來源)
    - 語義相似度 (嵌入向量相似性)
    """
    # 1. 文字重疊
    overlap_pct = compute_overlap_percentage(answer, sources)

    # 2. 語義相似度 (使用 embedding)
    answer_emb = embed_fn(answer)
    source_embs = [embed_fn(s) for s in sources]
    similarity = max(cosine_similarity(answer_emb, s) for s in source_embs)

    return (overlap_pct + similarity) / 2

# Delta Cutoff - 檢測相似度驟降
def detect_similarity_drop(scores: list[float], delta_cutoff: float = 0.1) -> int:
    """
    找出相似度分數的「斷崖」位置
    用於過濾低相關結果
    """
    for i in range(1, len(scores)):
        if scores[i-1] - scores[i] > delta_cutoff:
            return i  # 返回 cutoff 位置
    return len(scores)
```

**應用建議**:
- `score_answer()` → 整合到 `ResultAggregator` 的排序邏輯
- `compute_trust_score()` → 跨來源結果驗證
- Delta Cutoff → 自動過濾低相關結果

#### 2. PICO 提取與篩選（cochrane-audit-engine）

此專案實作完整的系統回顧篩選流程，關鍵設計：

```python
from pydantic import BaseModel
from enum import Enum

# PICO 結構化模型 - 可增強現有 parse_pico()
class ProtocolStructure(BaseModel):
    """系統回顧 Protocol 的 PICO 結構"""
    Population: str          # 研究族群
    Intervention: str        # 介入措施
    Comparator: str          # 對照組
    Outcome: str             # 結果指標
    StudyDesign: str         # 研究設計 (RCT, Cohort...)
    Exclusion: str           # 排除條件

class ScreeningDecision(str, Enum):
    """篩選決策"""
    INCLUDE = "include"
    EXCLUDE = "exclude"
    UNCERTAIN = "uncertain"

class ReasoningLog(BaseModel):
    """結構化推理日誌"""
    criteria_analysis: dict[str, str]  # 每個 PICO 元素的分析
    confidence: float                   # 信心分數 (0-1)
    decision: ScreeningDecision
    explanation: str

# 引文挖掘 - 雙流程提取
def mine_citations(text_content: str, pico_criteria: ProtocolStructure) -> list:
    """
    從 PDF 全文中挖掘引用:
    1. 找出 "Included Studies" 章節中的研究
    2. 提取完整參考文獻列表
    3. 交叉比對，標記符合 PICO 的研究
    """
    # Step 1: 找符合條件的研究
    included = extract_included_studies(text_content, pico_criteria)

    # Step 2: 提取所有參考文獻
    all_refs = extract_bibliography(text_content)

    # Step 3: 交叉比對
    return [ref for ref in all_refs if matches_pico(ref, pico_criteria)]

# 二階篩選流程
class TwoLevelScreening:
    """
    Level 1: Abstract 篩選 (快速)
    Level 2: Full-text 篩選 (精確)

    信心度 < 85% 自動標記為 UNCERTAIN，需人工審核
    """
    CONFIDENCE_THRESHOLD = 0.85

    async def screen_abstract(self, abstract: str, pico: ProtocolStructure) -> ReasoningLog:
        # 快速篩選，低成本
        pass

    async def screen_fulltext(self, pdf_path: str, pico: ProtocolStructure) -> ReasoningLog:
        # 精確篩選，高成本
        pass
```

**應用建議**:
- `ProtocolStructure` → 增強 `parse_pico()` 的輸出結構
- `ReasoningLog` → 記錄篩選決策過程
- 二階篩選 → Phase 3 系統回顧自動化
- 信心度閾值 → 自動標記需人工審核的結果

#### 3. CrossRef 日期查詢（heycochrane）

簡潔但實用的 CrossRef 日期取得模式：

```python
import urllib.request
import urllib.parse
import json

def get_date_from_crossref(doi: str) -> str | None:
    """
    從 CrossRef 取得出版日期
    優先順序: published-print → published-online → issued → created
    """
    encoded_doi = urllib.parse.quote(doi, safe="")
    url = f"https://api.crossref.org/works/{encoded_doi}"

    try:
        with urllib.request.urlopen(url, timeout=10) as response:
            data = json.loads(response.read())
            message = data.get("message", {})

            # 日期欄位優先順序
            date_fields = [
                "published-print",
                "published-online",
                "issued",
                "created"
            ]

            for field in date_fields:
                if field in message:
                    date_parts = message[field].get("date-parts", [[]])
                    if date_parts and date_parts[0]:
                        parts = date_parts[0]
                        year = parts[0]
                        month = parts[1] if len(parts) > 1 else 1
                        day = parts[2] if len(parts) > 2 else 1
                        return f"{year}-{month:02d}-{day:02d}"

            return None
    except Exception:
        return None
```

**應用建議**:
- 整合到 `CrossRefClient.get_work()` 方法
- 用於結果增強，補充 PubMed 缺失的精確日期

#### 4. 多資料庫查詢編譯（scientific_research_tool）

此專案提供 Boolean 查詢語法轉換，支援 PubMed → Europe PMC → Cochrane：

```python
# Cochrane 透過 Europe PMC 搜尋的巧妙方法
def search_cochrane_via_europepmc(query: str) -> list:
    """
    Cochrane Library 沒有公開 API，但可透過 Europe PMC 搜尋
    過濾條件: SRC:MED AND 標題含 "Cochrane"
    """
    adapted_query = f'({query}) AND (TITLE:"Cochrane Database")'

    # 或使用來源過濾
    # adapted_query = f'({query}) AND (SRC:CTX)'  # Cochrane Trials

    return search_europe_pmc(adapted_query)

# Boolean 查詢驗證器
class QueryValidator:
    """驗證並修正 Boolean 語法"""

    def validate(self, query: str) -> tuple[bool, str]:
        """
        檢查:
        - 括號配對
        - 運算子正確性 (AND/OR/NOT)
        - 欄位語法 ([Title], [Author], etc.)
        """
        errors = []

        # 括號配對
        if query.count("(") != query.count(")"):
            errors.append("括號不配對")

        # ... 其他驗證

        return len(errors) == 0, "; ".join(errors)

    def adapt_for_database(self, query: str, target: str) -> str:
        """
        轉換查詢語法:
        PubMed:     [Title] → Europe PMC: TITLE:
        PubMed:     [Author] → Europe PMC: AUTH:
        """
        if target == "europe_pmc":
            query = query.replace("[Title]", "TITLE:")
            query = query.replace("[Author]", "AUTH:")
            query = query.replace("[MeSH]", "")  # Europe PMC 不支援 MeSH 語法
        return query
```

**應用建議**:
- Cochrane via Europe PMC 模式 → 加入支援的資料源清單
- `QueryValidator` → 整合到 `QueryAnalyzer` 做輸入驗證
- 語法轉換 → 多來源搜尋時自動適配

### 不建議採用的模式

#### MedicalResearchSearchIndex

- **問題**: 使用網頁爬蟲 (Jsoup) 抓取 Cochrane，而非 API
- **風險**: 違反 Terms of Service、不穩定、維護成本高
- **結論**: ❌ 不採用

### 整合路線圖

| Phase | 整合項目 | 來源 | 預估工時 |
|-------|---------|------|---------|
| 1.5 | 品質評分 (`score_answer`) | DW2-Cochrane-Chatbot | 2h |
| 1.5 | 信任評分 (`compute_trust_score`) | DW2-Cochrane-Chatbot | 2h |
| 1.5 | CrossRef 日期查詢 | heycochrane | 1h |
| 2.0 | PICO 結構增強 | cochrane-audit-engine | 3h |
| 2.0 | Cochrane via Europe PMC | scientific_research_tool | 1h |
| 3.0 | 二階篩選流程 | cochrane-audit-engine | 8h |
| 3.0 | 引文挖掘 | cochrane-audit-engine | 4h |

---

## 📚 參考資源

### API 文檔

- [CrossRef REST API](https://api.crossref.org/swagger-ui/index.html)
- [Unpaywall API](https://unpaywall.org/products/api)
- [OpenAlex Documentation](https://docs.openalex.org/)
- [ClinicalTrials.gov API](https://clinicaltrials.gov/data-api/api)
- [Semantic Scholar API](https://api.semanticscholar.org/api-docs/)

### 競爭者

- [OpenEvidence](https://www.openevidence.com/) - Mayo Clinic 背景，專有內容授權
- [Elicit](https://elicit.com/) - 138M+ 論文，系統回顧自動化
- [SciSpace](https://scispace.com/) - Agent 模式，PRISMA 支援
- [Consensus](https://consensus.app/) - 問答式證據搜尋

### 開源專案參考

- [DW2-Cochrane-Chatbot](https://github.com/Iriide/DW2-Cochrane-Chatbot) - RAG 品質評分
- [cochrane-audit-engine](https://github.com/buildwithwhy/cochrane-audit-engine) - PICO 提取、系統回顧篩選
- [heycochrane](https://github.com/henryaj/heycochrane) - CrossRef 日期、摘要生成
- [scientific_research_tool](https://github.com/iCodator/scientific_research_tool) - 多資料庫查詢編譯

---

## 📝 變更日誌

| 日期       | 版本  | 變更                                                      |
|------------|-------|-----------------------------------------------------------|
| 2026-01-12 | 1.3.0 | 新增：Agent-MCP 協作模式獨立文件；Spec 完整性評估         |
| 2026-01-12 | 1.2.0 | 新增：開源專案分析章節（5 個 GitHub 專案）；整合路線圖    |
| 2026-01-11 | 1.1.0 | 修正：OpenAlex/Semantic Scholar 已整合；更新程式碼結構    |
| 2026-01-11 | 1.0.0 | 初始版本：整合所有研究文件                                |

---

> 本文件整合自原始分散文件: ACADEMIC_MEDICAL_APIS.md, API_INTEGRATION_CANDIDATES.md, COMPETITIVE_ANALYSIS.md
