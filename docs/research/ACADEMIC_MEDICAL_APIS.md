# Academic & Medical APIs Research

> 研究用途：整合 PubMed 文獻搜尋工具的 API 候選清單
> 
> 更新日期：2026-01-11

## 📊 API 總覽表

| API | 免費層級 | 認證方式 | Rate Limit | 整合優先級 |
|-----|---------|---------|------------|-----------|
| CrossRef | ✅ 完全免費 | Email (polite pool) | 10 req/s (polite) | ⭐⭐⭐ 高 |
| Unpaywall | ✅ 免費 | Email 參數 | 100,000/天 | ⭐⭐⭐ 高 |
| OpenAlex | ✅ 完全免費 | 無需認證 | 100,000/天 | ⭐⭐⭐ 高 |
| Semantic Scholar | ✅ 免費 | API Key (建議) | 1 RPS (認證) | ⭐⭐⭐ 高 |
| bioRxiv/medRxiv | ✅ 完全免費 | 無需認證 | 無明確限制 | ⭐⭐ 中 |
| ClinicalTrials.gov | ✅ 完全免費 | 無需認證 | 無明確限制 | ⭐⭐ 中 |
| ORCID | ✅ 免費公開 API | OAuth/API Key | 視級別而定 | ⭐⭐ 中 |
| DOAJ | ✅ 免費 | API Key | 無明確限制 | ⭐⭐ 中 |
| PMC (NCBI) | ✅ 免費 | 無需認證 | 遵循 E-utilities | ⭐⭐ 中 |
| Dimensions | ⚠️ 有限免費 | 需申請 | 需聯繫 | ⭐ 低 |
| UpToDate | ❌ 企業方案 | 企業合約 | N/A | ❌ 不適用 |
| Cochrane | ❌ 無公開 API | N/A | N/A | ❌ 不適用 |

---

## 1. UpToDate API

### 狀態：❌ 不適用於個人開發者

| 項目 | 說明 |
|------|------|
| 官方網站 | https://www.wolterskluwer.com/en/solutions/uptodate |
| API 類型 | 企業級 API，需透過 Wolters Kluwer 商業合約 |
| 認證方式 | 企業授權合約 |
| 開發者存取 | **無公開 API**，僅提供給機構客戶 |
| 定價模式 | 企業訂閱制，需聯繫銷售團隊 |

### 備註
- UpToDate 是 Wolters Kluwer 的付費臨床決策支援系統
- API 僅開放給已有 UpToDate 訂閱的醫療機構
- 無法作為獨立開發者整合
- 替代方案：可考慮使用 PubMed Clinical Queries 或 Cochrane 替代臨床證據需求

---

## 2. Cochrane Library API

### 狀態：❌ 無公開 API

| 項目 | 說明 |
|------|------|
| 官方網站 | https://www.cochranelibrary.com/ |
| API 狀態 | **無公開可用的 REST API** |
| 資料存取 | 僅透過 Wiley 出版平台的付費訂閱 |

### 替代方案
1. **PubMed 搜尋 Cochrane Reviews**：
   ```
   "Cochrane Database Syst Rev"[Journal] AND your_search_term
   ```
2. **Europe PMC**：索引部分 Cochrane 內容
3. **CrossRef**：可取得 Cochrane DOI 元資料

---

## 3. CrossRef API ⭐⭐⭐

### 狀態：✅ 強烈推薦整合

| 項目 | 說明 |
|------|------|
| 官方文件 | https://www.crossref.org/documentation/retrieve-metadata/rest-api/ |
| Base URL | `https://api.crossref.org/` |
| 認證方式 | 無需認證（建議使用 `mailto` 參數加入 polite pool） |
| 免費層級 | ✅ 完全免費 |

### Rate Limits

| 存取類型 | Rate Limit | 並發限制 |
|----------|-----------|---------|
| Public | 5 req/s | 1 |
| Polite (加 mailto) | 10 req/s | 3 |
| Metadata Plus (付費) | 150 req/s | 無限制 |

### 關鍵 Endpoints

```bash
# 取得單篇 DOI 元資料
GET /works/{doi}

# 搜尋文獻
GET /works?query=machine+learning

# 期刊資訊
GET /journals/{issn}

# 作者所屬機構的出版品
GET /members/{id}/works

# 資助機構的出版品
GET /funders/{id}/works
```

### 整合價值
- DOI 解析與驗證
- 取得完整書目元資料
- 引用連結追蹤
- 開放授權資訊

### 使用範例
```python
import requests

def get_crossref_metadata(doi: str, email: str) -> dict:
    url = f"https://api.crossref.org/works/{doi}"
    params = {"mailto": email}
    response = requests.get(url, params=params)
    return response.json()
```

---

## 4. ORCID API ⭐⭐

### 狀態：✅ 可整合（公開資料免費）

| 項目 | 說明 |
|------|------|
| 官方文件 | https://info.orcid.org/documentation/api-tutorials/ |
| API 測試 | https://postman.orcid.org/ |
| Base URL | `https://pub.orcid.org/v3.0/` |
| 認證方式 | 公開 API 無需認證；會員 API 需 OAuth |

### API 類型

| API 類型 | 存取範圍 | 認證 |
|---------|---------|------|
| Public API | 公開資料讀取 | 無需認證 |
| Member API | 讀寫已授權記錄 | OAuth 2.0 |

### 關鍵功能
- 取得研究者 ORCID iD
- 讀取公開的發表記錄
- 驗證作者身份
- 連結作者與著作

### 使用範例
```python
import requests

def get_orcid_record(orcid_id: str) -> dict:
    url = f"https://pub.orcid.org/v3.0/{orcid_id}/record"
    headers = {"Accept": "application/json"}
    response = requests.get(url, headers=headers)
    return response.json()
```

---

## 5. Unpaywall API ⭐⭐⭐

### 狀態：✅ 強烈推薦整合

| 項目 | 說明 |
|------|------|
| 官方文件 | https://unpaywall.org/products/api |
| Base URL | `https://api.unpaywall.org/v2/` |
| 認證方式 | Email 參數 (必須) |
| 免費層級 | ✅ 完全免費 |
| Rate Limit | 100,000 requests/天 |

### 關鍵 Endpoints

```bash
# 以 DOI 查詢 OA 狀態
GET /v2/{doi}?email=your@email.com

# 搜尋文章
GET /v2/search?query=your_query&email=your@email.com
```

### 回傳資料
- `is_oa`: 是否為開放取用
- `best_oa_location`: 最佳 OA 來源 URL
- `oa_status`: gold, green, hybrid, bronze, closed
- `published_version`: 出版版本連結
- `author_version`: 作者版本連結

### 整合價值
- 🔓 查找付費文獻的免費版本
- 自動連結到 PMC、機構庫、預印本
- 與 PubMed 搜尋結果整合，提供 OA 連結

### 使用範例
```python
import requests

def find_open_access(doi: str, email: str) -> dict:
    url = f"https://api.unpaywall.org/v2/{doi}"
    params = {"email": email}
    response = requests.get(url, params=params)
    return response.json()
```

---

## 6. Dimensions API ⭐

### 狀態：⚠️ 有限免費存取

| 項目 | 說明 |
|------|------|
| 官方網站 | https://www.dimensions.ai/ |
| 免費版 | https://app.dimensions.ai/ (Web 介面) |
| API 存取 | 需申請，主要為付費服務 |
| 資料規模 | 140M+ 出版品, 29M+ 資料集 |

### 免費層級限制
- Web 介面免費供個人非商業用途
- API 存取需透過學術計畫或付費訂閱
- 可申請 Scientometric Access (學術研究用途)

### 特色功能
- 引用分析與指標
- 資助連結
- 臨床試驗連結
- Altmetric 分數整合

### 建議
- 對於個人開發者，建議使用 OpenAlex 作為替代（免費且功能相似）

---

## 7. DOAJ API ⭐⭐

### 狀態：✅ 可整合

| 項目 | 說明 |
|------|------|
| 官方文件 | https://doaj.org/api/ |
| Base URL | `https://doaj.org/api/` |
| 認證方式 | API Key (透過帳戶設定取得) |
| 免費層級 | ✅ 免費 |

### 關鍵 Endpoints

```bash
# 搜尋期刊
GET /api/search/journals/{search_query}

# 搜尋文章
GET /api/search/articles/{search_query}

# 取得期刊詳情
GET /api/journals/{journal_id}

# 取得文章詳情
GET /api/articles/{article_id}
```

### 整合價值
- 驗證期刊是否為合法 OA
- 取得 OA 期刊的授權資訊
- 識別掠奪性期刊（DOAJ 有嚴格收錄標準）

---

## 8. bioRxiv / medRxiv API ⭐⭐

### 狀態：✅ 可整合

| 項目 | 說明 |
|------|------|
| 官方文件 | https://api.biorxiv.org/ |
| Base URL | `https://api.biorxiv.org/` |
| 認證方式 | 無需認證 |
| 免費層級 | ✅ 完全免費 |
| 格式 | JSON, XML (OAI-PMH), HTML |

### 關鍵 Endpoints

```bash
# 取得預印本詳情 (日期範圍)
GET /details/biorxiv/{start_date}/{end_date}/{cursor}
GET /details/medrxiv/{start_date}/{end_date}/{cursor}

# 以 DOI 取得單篇
GET /details/biorxiv/{doi}/na

# 已發表文章資訊
GET /pubs/biorxiv/{start_date}/{end_date}/{cursor}

# 統計資料
GET /sum/m  # 月統計
GET /usage/m  # 使用統計
```

### 回傳資料
- doi, title, authors
- abstract
- category (主題分類)
- date, version
- license
- published (是否已正式發表)

### 整合價值
- 追蹤最新預印本
- 追蹤預印本的正式發表狀態
- 醫學研究的早期發現

---

## 9. ClinicalTrials.gov API ⭐⭐

### 狀態：✅ 可整合

| 項目 | 說明 |
|------|------|
| 官方文件 | https://clinicaltrials.gov/data-api/api |
| API 規格 | https://clinicaltrials.gov/api/oas/v2 (OpenAPI 3.0) |
| Base URL | `https://clinicaltrials.gov/api/v2/` |
| 認證方式 | 無需認證 |
| 免費層級 | ✅ 完全免費 |
| 資料更新 | 每日 (週一至週五, 美東 9:00 AM) |

### 關鍵 Endpoints

```bash
# 搜尋臨床試驗
GET /studies?query.term=diabetes

# 取得單一試驗
GET /studies/{nctId}

# 取得欄位枚舉值
GET /studies/enums

# 統計資料
GET /stats/size
GET /stats/field/values

# 版本資訊
GET /version
```

### 整合價值
- 連結文獻與相關臨床試驗
- 追蹤藥物/治療的試驗狀態
- 支援 PICO 搜尋（病人、介入、比較、結果）

---

## 10. Semantic Scholar API ⭐⭐⭐

### 狀態：✅ 強烈推薦整合

| 項目 | 說明 |
|------|------|
| 官方文件 | https://api.semanticscholar.org/api-docs/ |
| 教學 | https://www.semanticscholar.org/product/api/tutorial |
| Base URL | `https://api.semanticscholar.org/` |
| 認證方式 | API Key (建議但非必須) |
| 免費層級 | ✅ 免費 |
| 資料規模 | 214M+ 論文, 2.49B+ 引用, 79M+ 作者 |

### Rate Limits

| 類型 | Rate Limit |
|------|-----------|
| 未認證 | 1000 req/s (共享) |
| API Key | 1 RPS (入門) |
| 進階 | 需申請提升 |

### 服務類型
1. **Academic Graph API**: 論文、作者、引用、機構
2. **Recommendations API**: 相關論文推薦
3. **Datasets API**: 大量資料下載

### 關鍵 Endpoints

```bash
# 論文搜尋
GET /graph/v1/paper/search?query=machine+learning

# 論文詳情 (by ID)
GET /graph/v1/paper/{paper_id}

# 論文詳情 (by DOI)
GET /graph/v1/paper/DOI:{doi}

# 作者資訊
GET /graph/v1/author/{author_id}

# 論文引用
GET /graph/v1/paper/{paper_id}/citations

# 論文參考文獻
GET /graph/v1/paper/{paper_id}/references

# 推薦論文
GET /recommendations/v1/papers/forpaper/{paper_id}
```

### 特色功能
- SPECTER2 embeddings (語意向量)
- TLDR 摘要
- 影響力分數
- 開放取用狀態

### 整合價值
- 強大的語意搜尋
- 引用網路分析
- AI 生成的摘要
- 相關論文推薦

---

## 11. OpenAlex API ⭐⭐⭐

### 狀態：✅ 強烈推薦整合

| 項目 | 說明 |
|------|------|
| 官方文件 | https://docs.openalex.org/ |
| Base URL | `https://api.openalex.org/` |
| 認證方式 | 無需認證 (建議加 mailto) |
| 免費層級 | ✅ 完全免費 (CC0 授權) |
| Rate Limit | 100,000 requests/天 |
| 資料規模 | 比 Scopus/WoS 多約 2 倍覆蓋率 |

### 實體類型
- Works (著作)
- Authors (作者)
- Sources (來源/期刊)
- Institutions (機構)
- Topics (主題)
- Publishers (出版商)
- Funders (資助機構)

### 關鍵 Endpoints

```bash
# 搜尋著作
GET /works?search=machine+learning

# 以 DOI 取得著作
GET /works/doi:10.1234/example

# 過濾搜尋
GET /works?filter=open_access.is_oa:true

# 作者資訊
GET /authors/{id}

# 機構資訊
GET /institutions/{id}
```

### 特色功能
- 完全開放 (CC0 授權)
- 優秀的非英語文獻覆蓋
- 全球南方研究覆蓋更佳
- 可下載完整資料集

### 整合價值
- Scopus/Web of Science 的免費替代
- 機構與資助連結
- 開放取用分析
- 引用分析

---

## 12. PMC APIs (NCBI) ⭐⭐

### 狀態：✅ 可整合（已部分整合於 pubmed-search-mcp）

| 項目 | 說明 |
|------|------|
| 官方文件 | https://pmc.ncbi.nlm.nih.gov/tools/developers/ |
| 認證方式 | 無需認證 (建議遵循 E-utilities 政策) |
| 免費層級 | ✅ 完全免費 |

### 可用 APIs

| API | 用途 | Base URL |
|-----|------|----------|
| OA API | OA 子集文章資訊 | `ncbi.nlm.nih.gov/pmc/utils/oa/oa.fcgi` |
| OAI-PMH | 元資料收割 | `pmc.ncbi.nlm.nih.gov/api/oai/v1/mh/` |
| BioC API | 全文 (XML/JSON) | `ncbi.nlm.nih.gov/research/bionlp/RESTful/pmcoa.cgi` |
| ID Converter | ID 轉換 | `pmc.ncbi.nlm.nih.gov/tools/idconv/api/v1/articles/` |
| Citation Exporter | 引用匯出 | `pmc.ncbi.nlm.nih.gov/api/ctxp/` |

### 雲端服務
- AWS S3/HTTPS 存取 OA 子集
- 無需登入
- 快速大量下載

---

## 🎯 整合優先順序建議

### 第一階段：核心功能增強
1. **Unpaywall** - 為搜尋結果加入 OA 連結
2. **CrossRef** - DOI 驗證與元資料補充
3. **OpenAlex** - 替代/補充資料來源

### 第二階段：深化分析
4. **Semantic Scholar** - AI 功能（TLDR、推薦）
5. **ClinicalTrials.gov** - 臨床研究連結
6. **bioRxiv/medRxiv** - 預印本追蹤

### 第三階段：擴展功能
7. **ORCID** - 作者識別與驗證
8. **DOAJ** - OA 期刊驗證

---

## 📝 整合代碼範例

### 統一 API 包裝器設計

```python
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Optional, List

@dataclass
class Article:
    doi: Optional[str]
    pmid: Optional[str]
    title: str
    authors: List[str]
    abstract: Optional[str]
    publication_date: Optional[str]
    journal: Optional[str]
    is_open_access: bool = False
    oa_url: Optional[str] = None

class AcademicAPIClient(ABC):
    @abstractmethod
    async def search(self, query: str, limit: int = 10) -> List[Article]:
        pass
    
    @abstractmethod
    async def get_by_doi(self, doi: str) -> Optional[Article]:
        pass

class UnpaywallClient(AcademicAPIClient):
    def __init__(self, email: str):
        self.email = email
        self.base_url = "https://api.unpaywall.org/v2"
    
    async def get_oa_link(self, doi: str) -> Optional[str]:
        # 實作 OA 連結查詢
        pass

class CrossRefClient(AcademicAPIClient):
    def __init__(self, email: str):
        self.email = email
        self.base_url = "https://api.crossref.org"
    
    async def get_by_doi(self, doi: str) -> Optional[Article]:
        # 實作 DOI 查詢
        pass

class OpenAlexClient(AcademicAPIClient):
    def __init__(self, email: Optional[str] = None):
        self.email = email
        self.base_url = "https://api.openalex.org"
    
    async def search(self, query: str, limit: int = 10) -> List[Article]:
        # 實作搜尋
        pass
```

---

## 📚 參考資源

- [CrossRef API Learning Hub](https://www.crossref.org/learning/)
- [OpenAlex Documentation](https://docs.openalex.org/)
- [Semantic Scholar API Tutorial](https://www.semanticscholar.org/product/api/tutorial)
- [NCBI E-utilities Guidelines](https://www.ncbi.nlm.nih.gov/books/NBK25497/)
- [ClinicalTrials.gov API Migration Guide](https://clinicaltrials.gov/data-api/about-api/api-migration)
