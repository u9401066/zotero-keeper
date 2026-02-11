# Reference Repositories for Literature Search Tools

> 📚 本文檔詳細記錄 5 個重要的學術文獻搜尋開源專案，作為 pubmed-search-mcp 的學習參考。

---

## 總覽

| Repo | Stars | 語言 | 授權 | 最後更新 |
|------|-------|------|------|----------|
| [scholarly](https://github.com/scholarly-python-package/scholarly) | 1.8k | Python | Unlicense | 活躍 |
| [habanero](https://github.com/sckott/habanero) | 238 | Python | MIT | 活躍 |
| [pyalex](https://github.com/J535D165/pyalex) | 325 | Python | MIT | 活躍 |
| [metapub](https://github.com/metapub/metapub) | 140 | Python | Apache-2.0 | 活躍 |
| [bioservices](https://github.com/cokelaer/bioservices) | 325 | Python | GPL-3.0 | 活躍 |

---

## 1. scholarly (Google Scholar 爬蟲)

### 基本資訊

- **GitHub**: https://github.com/scholarly-python-package/scholarly
- **Stars**: 1,800+
- **授權**: Unlicense (公共領域)
- **安裝**: `pip install scholarly`

### 核心功能

```python
from scholarly import scholarly

# 搜尋論文
search_query = scholarly.search_pubs('deep learning')
paper = next(search_query)

# 取得完整資料（延遲載入）
paper_filled = scholarly.fill(paper)

# 搜尋作者
author = scholarly.search_author_id('EmD_lTEAAAAJ')  # Geoffrey Hinton
author_filled = scholarly.fill(author)

# 取得引用此論文的文章
citations = scholarly.citedby(paper)
```

### 關鍵架構學習

#### 1.1 ProxyGenerator - 代理池管理

```python
from scholarly import ProxyGenerator

pg = ProxyGenerator()

# 方式 1: ScraperAPI (商業服務)
pg.ScraperAPI('YOUR_API_KEY')

# 方式 2: Tor 網路
pg.Tor_Internal()

# 方式 3: 免費代理池
pg.FreeProxies()

# 設定代理
scholarly.use_proxy(pg)
```

**學習重點**：
- 抽象代理介面，支援多種代理來源
- 自動輪換和失敗重試
- 避免 Google 的 CAPTCHA 封鎖

#### 1.2 fill() 延遲載入模式

```python
# 初始搜尋返回基本資訊
paper = next(scholarly.search_pubs('attention is all you need'))
# paper.bib 只有標題、作者等基本資訊

# fill() 取得完整資訊
paper = scholarly.fill(paper)
# 現在有完整摘要、引用數、PDF 連結等
```

**學習重點**：
- 減少不必要的 API 請求
- 用戶只在需要時取得完整資料
- 可應用於我們的 `fetch_article_details`

#### 1.3 引用網路遍歷

```python
# 取得引用此論文的文章
for citing_paper in scholarly.citedby(paper):
    print(citing_paper['bib']['title'])

# 取得作者的所有文章
for pub in author['publications']:
    filled_pub = scholarly.fill(pub)
```

### 整合建議

| 功能 | 優先級 | 實作方式 |
|------|--------|----------|
| Google Scholar 引用數 | 中 | 作為 iCite 補充 |
| 作者 h-index | 低 | 新增 `get_author_metrics` |
| 代理輪換機制 | 高 | 用於高頻搜尋場景 |

---

## 2. habanero (CrossRef API)

### 基本資訊

- **GitHub**: https://github.com/sckott/habanero
- **Stars**: 238
- **授權**: MIT
- **安裝**: `pip install habanero`

### 核心功能

```python
from habanero import Crossref, counts, cn

cr = Crossref()

# 搜尋作品
result = cr.works(query="machine learning")

# 透過 DOI 取得元數據
work = cr.works(ids="10.1038/nature12373")

# 取得引用數
citation_count = counts.citation_count(doi="10.1038/nature12373")
```

### 關鍵架構學習

#### 2.1 Content Negotiation (cn 模組)

```python
from habanero import cn

doi = "10.1126/science.169.3946.635"

# 取得 BibTeX 格式
bibtex = cn.content_negotiation(ids=doi, format="bibtex")

# 取得 RIS 格式
ris = cn.content_negotiation(ids=doi, format="ris")

# 取得 Citeproc JSON
citeproc = cn.content_negotiation(ids=doi, format="citeproc-json")

# 支援的格式
# rdf-xml, turtle, citeproc-json, citeproc-json-ish
# text, ris, bibtex, crossref-xml, datacite-xml
```

**學習重點**：
- 單一 DOI 可輸出多種引用格式
- 標準 HTTP Content Negotiation
- 可增強我們的 `prepare_export` 功能

#### 2.2 Polite Pool 機制

```python
from habanero import Crossref

# 設定 email 以獲得更高速率限制
cr = Crossref(mailto="your@email.com")

# CrossRef 會將你加入 "polite pool"
# 速率限制從 50 req/s 提升到更高
```

**學習重點**：
- 簡單設定即可獲得更好的 API 體驗
- 我們的 CrossRef client 應採用同樣做法

#### 2.3 Reference 連結追蹤

```python
# 取得論文的參考文獻 DOI
work = cr.works(ids="10.1038/nature12373")
references = work['message'].get('reference', [])

for ref in references:
    if 'DOI' in ref:
        print(f"Reference DOI: {ref['DOI']}")
```

### 整合建議

| 功能 | 優先級 | 實作方式 |
|------|--------|----------|
| Content Negotiation | 高 | 增強 `prepare_export` |
| Polite Pool | 高 | 更新 `sources/crossref.py` |
| Reference DOI 提取 | 中 | 增強 `get_article_references` |

---

## 3. pyalex (OpenAlex API)

### 基本資訊

- **GitHub**: https://github.com/J535D165/pyalex
- **Stars**: 325
- **授權**: MIT
- **安裝**: `pip install pyalex`

### 核心功能

```python
import pyalex
from pyalex import Works, Authors, Sources, Institutions

# 設定 email (polite pool)
pyalex.config.email = "your@email.com"

# Pipe 操作風格搜尋
works = Works().filter(publication_year=2023).filter(open_access={"is_oa": True}).get()

# 透過 ID 取得
work = Works()["W2741809807"]
author = Authors()["A5023888391"]

# N-grams 支援
ngrams = Works()["W2023271753"].ngrams()
```

### 關鍵架構學習

#### 3.1 Pipe 操作鏈

```python
from pyalex import Works

# 鏈式 API 設計
results = (
    Works()
    .filter(publication_year=">2020")
    .filter(concepts={"id": "C41008148"})  # Computer Science
    .filter(is_oa=True)
    .sort(cited_by_count="desc")
    .get()
)

# 取得特定頁
page_3 = Works().filter(publication_year=2023).get(page=3, per_page=50)
```

**學習重點**：
- 流暢 API 設計提升開發體驗
- 可應用於我們的搜尋工具鏈

#### 3.2 Abstract 反向索引轉換

OpenAlex 使用反向索引儲存摘要：

```python
# OpenAlex 原始格式
abstract_inverted_index = {
    "This": [0],
    "is": [1, 4],
    "a": [2],
    "test": [3],
    "paper": [5]
}

# pyalex 自動轉換
from pyalex import Works

work = Works()["W2741809807"]
plain_abstract = work['abstract']  # 自動轉為純文字
```

**學習重點**：
- 資料格式轉換的封裝
- 隱藏複雜性，提供簡潔介面

#### 3.3 Cursor-based Pagination

```python
from pyalex import Works

# 使用 cursor 取得所有結果
all_works = []
for page in Works().filter(publication_year=2023).paginate(per_page=200):
    all_works.extend(page)
    if len(all_works) >= 10000:
        break
```

**學習重點**：
- 大量資料的高效分頁
- Iterator 模式處理流式資料

### 整合建議

| 功能 | 優先級 | 實作方式 |
|------|--------|----------|
| N-grams 趨勢分析 | 中 | 新增 `analyze_topic_trends` |
| Concepts 探索 | 中 | 新增 `explore_concepts` |
| 流暢 API | 低 | 重構現有客戶端 |

---

## 4. metapub (NCBI 工具包) ⭐⭐ 高度相關

### 基本資訊

- **GitHub**: https://github.com/metapub/metapub
- **Stars**: 140
- **授權**: Apache-2.0
- **安裝**: `pip install metapub`

### 核心功能

```python
from metapub import PubMedFetcher, FindIt, CrossRefFetcher

# PubMed 搜尋
fetch = PubMedFetcher()
pmids = fetch.pmids_for_query("cancer treatment 2023")
article = fetch.article_by_pmid('12345678')

# PDF 發現
url = FindIt('12345678').url  # 自動找到 PDF 連結

# CrossRef 整合
cr = CrossRefFetcher()
article = cr.article_by_doi('10.1038/nature12373')
```

### 關鍵架構學習

#### 4.1 FindIt - PDF 發現引擎 ⭐⭐

**這是 metapub 最有價值的功能**：

```python
from metapub import FindIt

# 自動發現 PDF 連結
src = FindIt('23132851')
print(src.url)  # https://www.nature.com/articles/nature12373.pdf
print(src.reason)  # 'DOI lookup' 或 'PubMed Central' 等

# 支援 68+ 出版商的 URL 規則
# - Elsevier (ScienceDirect)
# - Springer Nature
# - Wiley
# - Oxford University Press
# - Taylor & Francis
# - SAGE
# - American Chemical Society
# - 等等...
```

**學習重點**：
- 維護出版商 URL 規則資料庫
- 多策略嘗試（DOI lookup → PMC → Publisher site）
- 可顯著增強我們的全文取得能力

#### 4.2 UrlReverse - URL 識別

```python
from metapub import UrlReverse

# 從 URL 識別論文
ur = UrlReverse("https://www.nature.com/articles/nature12373")
print(ur.doi)   # 10.1038/nature12373
print(ur.pmid)  # 23132851
```

**學習重點**：
- 反向工程 URL 提取識別碼
- 可增加 "從 URL 搜尋" 功能

#### 4.3 統一 Article 介面

```python
from metapub import PubMedArticle, CrossRefArticle

# 兩種來源使用相同介面
pm_article = PubMedFetcher().article_by_pmid('12345678')
cr_article = CrossRefFetcher().article_by_doi('10.1038/xxx')

# 統一屬性
print(pm_article.title)
print(pm_article.authors)
print(pm_article.abstract)
print(pm_article.citation)  # 格式化引用
```

**學習重點**：
- 類似我們的 `UnifiedArticle` 設計
- 可參考其屬性定義

### 整合建議

| 功能 | 優先級 | 實作方式 |
|------|--------|----------|
| FindIt PDF 發現 | **極高** | Fork 或整合其邏輯 |
| UrlReverse | 中 | 新增 `identify_url` 工具 |
| MedGen/ClinVar | 低 | 與 `search_clinvar` 整合 |

### FindIt 整合計畫

```python
# 建議的整合方式
# external/pubmed-search-mcp/src/pubmed_search/fulltext/findit.py

from metapub import FindIt

class FulltextFinder:
    """整合 metapub FindIt 的全文發現器"""

    def find_pdf_url(self, pmid: str) -> dict:
        """找出論文的 PDF 連結"""
        try:
            src = FindIt(pmid)
            return {
                "pmid": pmid,
                "pdf_url": src.url,
                "source": src.reason,
                "backup_urls": src.backup_url_list,
            }
        except Exception as e:
            return {"pmid": pmid, "error": str(e)}
```

---

## 5. bioservices (多服務框架)

### 基本資訊

- **GitHub**: https://github.com/cokelaer/bioservices
- **Stars**: 325
- **授權**: GPL-3.0
- **安裝**: `pip install bioservices`

### 核心功能

```python
from bioservices import UniProt, KEGG, ChEMBL, PubChem

# UniProt 蛋白質資料庫
u = UniProt()
result = u.search("BRCA1", limit=10)

# KEGG 代謝途徑
k = KEGG()
pathway = k.get("hsa:7157")  # p53

# ChEMBL 藥物資料庫
c = ChEMBL()
compounds = c.get_molecule_by_chemblId("CHEMBL25")

# PubChem 化合物
p = PubChem()
compound = p.get_compound_by_name("aspirin")
```

### 關鍵架構學習

#### 5.1 統一服務抽象層

```python
from bioservices import REST, WSDL

class MyService(REST):
    """自訂服務的基礎類別"""

    _url = "https://api.example.com"

    def __init__(self, verbose=False):
        super().__init__(name="MyService", url=self._url, verbose=verbose)

    def search(self, query):
        return self.http_get(f"search?q={query}")
```

**學習重點**：
- REST/WSDL 基礎類別提供統一介面
- 自動處理重試、快取、錯誤
- 可參考設計我們的 `sources/base.py`

#### 5.2 命令列工具

```bash
# 內建 CLI
bioservices download-accession P12345 --db uniprot
bioservices search "BRCA1" --db uniprot --limit 10
```

**學習重點**：
- 服務層可直接暴露為 CLI
- 方便調試和獨立使用

#### 5.3 支援的服務列表

bioservices 包裝了 40+ 服務，其中與我們相關的：

| 服務 | 功能 | 相關性 |
|------|------|--------|
| EUtils | NCBI E-utilities | 高 |
| PubChem | 化合物資料庫 | 中 |
| ChEMBL | 藥物資料庫 | 中 |
| UniProt | 蛋白質資料庫 | 低 |
| KEGG | 代謝途徑 | 低 |

### 整合建議

| 功能 | 優先級 | 實作方式 |
|------|--------|----------|
| 服務抽象層設計 | 中 | 重構 `sources/` 架構 |
| CLI 工具 | 低 | 新增 `pubmed-mcp-cli` |
| PubChem 深度整合 | 中 | 增強 `get_compound_details` |

---

## 關於論文圖片 API 📷

### 問題

> PubMed 官方 API 是否提供論文內圖片連結？

### 答案

**PubMed E-utilities 是純文字 API，不直接提供圖片連結**

### 替代方案

#### 1. PMC Open Access (最可靠)

```xml
<!-- PMC 全文 XML 中的圖片元素 -->
<fig id="fig1">
  <label>Figure 1</label>
  <caption>
    <p>Experimental design...</p>
  </caption>
  <graphic xlink:href="PMC7096777_fig1.jpg"/>
</fig>
```

**取得方式**：
1. 使用 `get_fulltext_xml(pmcid)` 取得 JATS XML
2. 解析 `<fig>` 元素
3. 組合圖片 URL：
   ```
   https://www.ncbi.nlm.nih.gov/pmc/articles/{PMCID}/bin/{filename}
   ```

#### 2. Europe PMC Text-Mining API

```python
# 取得 FIGURE 類型的標註
from pubmed_search.mcp.tools.fulltext import get_text_mined_terms

# semantic_type="FIGURE" 可取得圖片相關標註
figures = get_text_mined_terms(pmid="12345678", semantic_type="FIGURE")
```

#### 3. bioRxiv/medRxiv

預印本服務器通常直接在 HTML 中暴露圖片 URL：

```
https://www.biorxiv.org/content/10.1101/2024.01.01.001.full/figure/F1.large.jpg
```

### 實作建議

```python
# 建議新增工具: get_article_figures

async def get_article_figures(pmcid: str) -> dict:
    """
    從 PMC 全文取得論文圖片列表。

    Args:
        pmcid: PMC ID (如 "PMC7096777")

    Returns:
        {
            "figures": [
                {
                    "id": "fig1",
                    "label": "Figure 1",
                    "caption": "Experimental design...",
                    "url": "https://www.ncbi.nlm.nih.gov/pmc/articles/PMC7096777/bin/fig1.jpg"
                }
            ]
        }
    """
    xml = await get_fulltext_xml(pmcid)
    # 解析 XML 提取 <fig> 元素...
```

---

## 學習行動計畫

### 立即 (v1.12.0)

1. **整合 habanero Content Negotiation**
   - 更新 `sources/crossref.py` 加入 `cn` 功能
   - 增強 `prepare_export` 支援更多格式

2. **採用 metapub FindIt 邏輯**
   - 研究 FindIt 的出版商 URL 規則
   - 新增 `find_fulltext_url` 工具

3. **實作 PMC 圖片提取**
   - 解析 JATS XML 中的 `<fig>` 元素
   - 新增 `get_article_figures` 工具

### 中期 (v1.13.0)

4. **pyalex N-grams 趨勢分析**
   - 新增 `analyze_topic_trends` 工具

5. **bioservices 框架參考**
   - 重構 `sources/` 模組
   - 建立統一服務基礎類別

### 長期

6. **scholarly Google Scholar 整合**
   - 評估法律風險和穩定性
   - 作為補充引用來源

---

## 6. Web of Science Starter API (Clarivate 官方)

### 基本資訊

- **Developer Portal**: https://developer.clarivate.com/apis/wos-starter
- **GitHub**: https://github.com/clarivate/wosstarter_python_client
- **Stars**: 29 (官方維護)
- **授權**: OpenAPI 生成
- **安裝**: `pip install git+https://github.com/clarivate/wosstarter_python_client.git`

### 核心功能

```python
import clarivate.wos_starter.client as wos

# 配置 API Key
configuration = wos.Configuration(
    host="https://api.clarivate.com/apis/wos-starter/v1"
)
configuration.api_key['ClarivateApiKeyAuth'] = 'YOUR_API_KEY'

with wos.ApiClient(configuration) as api_client:
    api = wos.DocumentsApi(api_client)

    # 搜尋文獻
    result = api.documents_get(
        q='TS=machine learning AND PY=2024',
        db='WOS',
        limit=10,
        sort_field='TC+D'  # 按引用數降序
    )

    # 取得單篇文獻
    doc = api.documents_uid_get(uid='WOS:000123456789')
```

### 關鍵特色

#### 6.1 Times Cited 數據

**這是 WoS 最有價值的數據**：

```python
# 返回的文獻包含 times_cited
for doc in result.data:
    print(f"{doc.title}: {doc.times_cited} citations")
```

**優勢**：
- 官方引用數據（比 Google Scholar 更權威）
- 包含 JCR (Journal Citation Reports) 連結
- 支援 Web of Science Core Collection 完整欄位

#### 6.2 高級搜尋語法

```python
# 支援的搜尋欄位
queries = [
    'TI=deep learning',           # 標題
    'AU=Smith, John',             # 作者
    'TS=CRISPR',                  # 主題 (標題+摘要+關鍵字)
    'DO=10.1038/nature12373',     # DOI
    'PMID=23132851',              # PubMed ID
    'PY=2020-2024',               # 年份範圍
    'OG=Harvard University',       # 機構
]
```

#### 6.3 多資料庫支援

```python
# 支援的資料庫
databases = [
    'WOS',      # Web of Science Core Collection
    'MEDLINE',  # MEDLINE
    'BIOSIS',   # BIOSIS Previews
    'DRCI',     # Data Citation Index
    'PPRN',     # Preprint Citation Index
    'WOK',      # All databases
]
```

### 方案層級

| 方案 | 請求限制 | Times Cited | 適用對象 |
|------|----------|-------------|----------|
| Free Trial | 50/day | ❌ | 評估用途 |
| Institutional Member | 5,000/day | ✅ | 訂閱機構成員 |
| Integration | 20,000/day | ✅ | 機構系統整合 |

### 整合建議

| 功能 | 優先級 | 實作方式 |
|------|--------|----------|
| Times Cited 補充 | 中 | 與 iCite 並行提供 |
| JCR 連結 | 低 | 期刊影響因子參考 |
| WoS 識別碼 | 低 | UID 交叉引用 |

**注意**：需要 API Key，且 Times Cited 需要機構訂閱。

---

## 持續學習建議

### 每季度 Review 清單

1. **檢查 Release Notes**
   - 各 repo 的 GitHub Releases
   - API 更新和新端點

2. **追蹤新功能**
   - scholarly: 新的反爬蟲策略
   - habanero: CrossRef API 更新
   - pyalex: OpenAlex 新 Concepts
   - metapub: FindIt 新出版商規則

3. **社群動態**
   - GitHub Issues 和 Discussions
   - Stack Overflow 相關問題

### 學習資源

| 資源 | 連結 |
|------|------|
| PubMed API | https://www.ncbi.nlm.nih.gov/books/NBK25501/ |
| CrossRef API | https://api.crossref.org/swagger-ui/index.html |
| OpenAlex API | https://docs.openalex.org/ |
| Europe PMC API | https://europepmc.org/RestfulWebService |
| Unpaywall API | https://unpaywall.org/products/api |
| Web of Science API | https://developer.clarivate.com/apis/wos-starter |

---

*最後更新: 2025 年 1 月*
