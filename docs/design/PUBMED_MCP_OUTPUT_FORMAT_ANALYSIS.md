# PubMed Search MCP 輸出格式分析報告

> 本文件分析 `pubmed-search-mcp` 套件各工具的回傳格式，為設計標準化文章交換格式 (StandardArticle) 提供依據。

---

## 目錄

1. [search_literature - PubMed 搜尋結果](#1-search_literature---pubmed-搜尋結果)
2. [search_europe_pmc - Europe PMC 搜尋結果](#2-search_europe_pmc---europe-pmc-搜尋結果)
3. [search_core - CORE 搜尋結果](#3-search_core---core-搜尋結果)
4. [fetch_article_details - 文章詳情](#4-fetch_article_details---文章詳情)
5. [prepare_export - RIS 匯出格式](#5-prepare_export---ris-匯出格式)
6. [標準化文章交換格式設計 (StandardArticle)](#6-標準化文章交換格式設計-standardarticle)

---

## 1. search_literature - PubMed 搜尋結果

### 來源位置
- Tool: `src/pubmed_search/mcp/tools/discovery.py::search_literature()`
- Parser: `src/pubmed_search/entrez/search.py::SearchMixin._parse_pubmed_article()`

### 回傳的主要欄位

| 欄位名稱 | 類型 | 說明 | 範例 |
|---------|------|------|------|
| `pmid` | str | PubMed 唯一識別碼 | `"38123456"` |
| `title` | str | 文章標題 | `"Machine Learning in Anesthesiology"` |
| `authors` | List[str] | 作者列表（簡化格式） | `["Smith John", "Wang Li"]` |
| `authors_full` | List[Dict] | 作者詳細資料 | 見下方結構 |
| `abstract` | str | 摘要全文 | `"Background: ..."` |
| `journal` | str | 期刊全名 | `"British Journal of Anaesthesia"` |
| `journal_abbrev` | str | 期刊縮寫 | `"Br J Anaesth"` |
| `issn` | str | 期刊 ISSN | `"1471-6771"` |
| `year` | str | 出版年份 | `"2024"` |
| `month` | str | 出版月份 | `"Mar"` |
| `day` | str | 出版日期 | `"15"` |
| `pub_date` | str | 完整出版日期 | `"2024/Mar/15"` |
| `volume` | str | 卷號 | `"132"` |
| `issue` | str | 期號 | `"3"` |
| `pages` | str | 頁碼 | `"425-437"` |
| `doi` | str | DOI 識別碼 | `"10.1016/j.bja.2024.01.015"` |
| `pmc_id` | str | PubMed Central ID | `"PMC10987654"` |
| `keywords` | List[str] | 作者關鍵詞 | `["machine learning", "anesthesia"]` |
| `mesh_terms` | List[str] | MeSH 標準詞彙 | `["Anesthesiology", "Machine Learning"]` |
| `language` | str | 文章語言 | `"eng"` |
| `publication_types` | List[str] | 出版類型 | `["Journal Article", "Review"]` |

### 作者詳細結構 (authors_full)

```python
{
    "last_name": "Smith",
    "fore_name": "John William",
    "initials": "JW",
    "affiliations": [
        "Department of Anesthesiology, Harvard Medical School, Boston, MA, USA"
    ]
}
# 或集體作者
{
    "collective_name": "ENIGMA Trial Investigators"
}
```

### 完整範例

```python
{
    "pmid": "38123456",
    "title": "Machine Learning Applications in Perioperative Medicine: A Systematic Review",
    "authors": ["Smith John", "Wang Li", "Johnson Mary"],
    "authors_full": [
        {
            "last_name": "Smith",
            "fore_name": "John",
            "initials": "J",
            "affiliations": ["Harvard Medical School"]
        }
    ],
    "abstract": "Background: Machine learning has emerged as a powerful tool...",
    "journal": "British Journal of Anaesthesia",
    "journal_abbrev": "Br J Anaesth",
    "issn": "1471-6771",
    "year": "2024",
    "month": "Mar",
    "day": "15",
    "pub_date": "2024/Mar/15",
    "volume": "132",
    "issue": "3",
    "pages": "425-437",
    "doi": "10.1016/j.bja.2024.01.015",
    "pmc_id": "PMC10987654",
    "keywords": ["machine learning", "anesthesia", "prediction"],
    "mesh_terms": ["Machine Learning", "Anesthesiology", "Perioperative Care"],
    "language": "eng",
    "publication_types": ["Journal Article", "Systematic Review"]
}
```

---

## 2. search_europe_pmc - Europe PMC 搜尋結果

### 來源位置
- Tool: `src/pubmed_search/mcp/tools/europe_pmc.py::search_europe_pmc()`
- Normalizer: `src/pubmed_search/sources/europe_pmc.py::EuropePMCClient._normalize_article()`

### 回傳的主要欄位

| 欄位名稱 | 類型 | 說明 | PubMed 對應 |
|---------|------|------|------------|
| `pmid` | str | PubMed ID | ✓ 相同 |
| `pmc_id` | str | PMC ID | ✓ 相同 |
| `doi` | str | DOI | ✓ 相同 |
| `title` | str | 標題 | ✓ 相同 |
| `abstract` | str | 摘要 (來自 abstractText) | ✓ 相同 |
| `authors` | List[str] | 作者列表 | ✓ 相同 |
| `authors_full` | List[Dict] | 作者詳情 | ✓ 相同結構 |
| `journal` | str | 期刊名稱 | ✓ 相同 |
| `journal_abbrev` | str | 期刊縮寫 | ✓ 相同 |
| `year` | str | 年份 | ✓ 相同 |
| `month` | str | 月份 | ✓ 相同 |
| `day` | str | 日期 | ✓ 相同 |
| `volume` | str | 卷號 | ✓ 相同 |
| `issue` | str | 期號 | ✓ 相同 |
| `pages` | str | 頁碼 | ✓ 相同 |
| `keywords` | List[str] | 關鍵詞 | ✓ 相同 |
| `mesh_terms` | List[str] | MeSH 詞彙 | ✓ 相同 |
| `citation_count` | int | 被引用次數 | ⭐ 額外欄位 |
| `is_open_access` | bool | 是否開放取用 | ⭐ 額外欄位 |
| `has_fulltext` | bool | 是否有全文 | ⭐ 額外欄位 |
| `has_pdf` | bool | 是否有 PDF | ⭐ 額外欄位 |
| `source` | str | 資料來源 (MED/PMC) | ⭐ 額外欄位 |
| `pub_type` | str | 出版類型 | ⭐ 額外欄位 |
| `_source` | str | 來源標記 | `"europe_pmc"` |
| `_epmc_id` | str | Europe PMC 內部 ID | ⭐ 額外欄位 |

### 完整範例

```python
{
    "pmid": "38123456",
    "pmc_id": "PMC10987654",
    "doi": "10.1016/j.bja.2024.01.015",
    "title": "Machine Learning Applications in Perioperative Medicine",
    "abstract": "Background: Machine learning has emerged...",
    "authors": ["Smith John", "Wang Li"],
    "authors_full": [
        {"fore_name": "John", "last_name": "Smith", "initials": "J"}
    ],
    "journal": "British Journal of Anaesthesia",
    "journal_abbrev": "Br J Anaesth",
    "year": "2024",
    "month": "03",
    "day": "15",
    "volume": "132",
    "issue": "3",
    "pages": "425-437",
    "keywords": ["machine learning"],
    "mesh_terms": ["Machine Learning", "Anesthesiology"],
    
    # Europe PMC 特有欄位
    "citation_count": 15,
    "is_open_access": True,
    "has_fulltext": True,
    "has_pdf": True,
    "source": "MED",
    "pub_type": "research-article",
    "_source": "europe_pmc",
    "_epmc_id": "38123456"
}
```

---

## 3. search_core - CORE 搜尋結果

### 來源位置
- Tool: `src/pubmed_search/mcp/tools/core.py::search_core()`
- Normalizer: `src/pubmed_search/sources/core.py::COREClient._normalize_work()`

### 回傳的主要欄位

| 欄位名稱 | 類型 | 說明 | PubMed 對應 |
|---------|------|------|------------|
| `core_id` | int/str | CORE 內部 ID | ⭐ 額外欄位 |
| `title` | str | 標題 | ✓ 相同 |
| `authors` | List[str] | 作者列表 | ✓ 相同 |
| `author_string` | str | 格式化作者字串 | ⭐ 額外欄位 |
| `abstract` | str | 摘要 | ✓ 相同 |
| `year` | int | 出版年份 (整數) | ⚠ 類型不同 |
| `journal` | str | 期刊名稱 | ✓ 相同 |
| `publisher` | str | 出版商 | ⭐ 額外欄位 |
| `doi` | str | DOI | ✓ 相同 |
| `pmid` | str | PubMed ID (如有) | ✓ 相同 |
| `arxiv_id` | str | arXiv ID (如有) | ⭐ 額外欄位 |
| `language` | str | 語言名稱 | ⚠ 格式不同 |
| `document_type` | List[str] | 文件類型 | ⭐ 額外欄位 |
| `has_fulltext` | bool | 是否有全文 | ⭐ 額外欄位 |
| `fulltext_available` | bool | 全文是否可取得 | ⭐ 額外欄位 |
| `download_url` | str | 下載連結 | ⭐ 額外欄位 |
| `pdf_url` | str | PDF 連結 | ⭐ 額外欄位 |
| `reader_url` | str | 閱讀器連結 | ⭐ 額外欄位 |
| `citation_count` | int | 引用數 | ⭐ 額外欄位 |
| `data_providers` | List[str] | 資料提供者 | ⭐ 額外欄位 |
| `_source` | str | 來源標記 | `"core"` |

### 完整範例

```python
{
    "core_id": 152480964,
    "title": "Deep Learning for Medical Image Analysis",
    "authors": ["Chen Wei", "Liu Xin"],
    "author_string": "Chen Wei, Liu Xin",
    "abstract": "This paper presents a comprehensive review...",
    "year": 2024,  # 注意：整數類型
    "journal": "Nature Medicine",
    "publisher": "Nature Publishing Group",
    "doi": "10.1038/s41591-024-12345-x",
    "pmid": "38234567",
    "arxiv_id": None,
    "language": "English",  # 完整語言名稱
    "document_type": ["article"],
    "has_fulltext": True,
    "fulltext_available": True,
    "download_url": "https://core.ac.uk/download/pdf/152480964.pdf",
    "pdf_url": "https://core.ac.uk/download/pdf/152480964.pdf",
    "reader_url": "https://core.ac.uk/reader/152480964",
    "citation_count": 42,
    "data_providers": ["PubMed Central", "Europe PMC"],
    "_source": "core"
}
```

### CORE Output 額外欄位 (get_core_fulltext)

```python
{
    # 繼承 work 的所有欄位，加上：
    "output_id": 789012345,
    "full_text": "Introduction\n\nMachine learning has revolutionized...",  # 完整全文
    "fulltext_status": "available",
    "repository": "Harvard University Repository",
    "repository_url": "https://dash.harvard.edu"
}
```

---

## 4. fetch_article_details - 文章詳情

### 來源位置
- Tool: `src/pubmed_search/mcp/tools/discovery.py::fetch_article_details()`
- 實際上調用 `SearchMixin.fetch_details()`

### 說明

`fetch_article_details` 返回與 `search_literature` 完全相同的欄位結構，因為它們使用相同的解析器 (`_parse_pubmed_article`)。

### 與搜尋結果的差異
- 搜尋結果可能被限制數量
- `fetch_article_details` 會返回所有請求的文章完整詳情
- 適合用於：
  - 取得特定 PMID 的完整資料
  - 驗證文章存在
  - 匯出前取得最新資料

---

## 5. prepare_export - RIS 匯出格式

### 來源位置
- Tool: `src/pubmed_search/mcp/tools/export.py::prepare_export()`
- Formatter: `src/pubmed_search/exports/formats.py::export_ris()`

### RIS 格式欄位對應

```
TY  - JOUR                    (固定值：期刊文章)
T1  - {title}                 (標題)
TI  - {title}                 (標題 - 備用)
AU  - {Last, First}           (作者，每人一行)
A1  - {Last, First}           (作者 - 備用)
JO  - {journal}               (期刊全名)
JF  - {journal}               (期刊全名 - 備用)
T2  - {journal}               (期刊 - 二級標題)
JA  - {journal_abbrev}        (期刊縮寫)
J2  - {journal_abbrev}        (期刊縮寫 - 備用)
SN  - {issn}                  (ISSN)
PY  - {year}                  (年份)
Y1  - {year}                  (年份 - 備用)
DA  - {pub_date}              (完整日期)
VL  - {volume}                (卷號)
IS  - {issue}                 (期號)
SP  - {pages}                 (起始頁碼)
EP  - {end_page}              (結束頁碼，自動分割)
AN  - {pmid}                  (登錄號)
C1  - PMID: {pmid}            (自訂欄位1)
ID  - {pmid}                  (識別碼)
DO  - {doi}                   (DOI)
C2  - {pmc_id}                (自訂欄位2：PMC ID)
LA  - {language}              (語言)
M3  - {publication_type}      (出版類型，每類一行)
AB  - {abstract}              (摘要)
N2  - {abstract}              (摘要 - 備用)
KW  - {keyword}               (關鍵詞，每詞一行)
KW  - {mesh_term}             (MeSH 詞彙，每詞一行)
UR  - {pubmed_url}            (PubMed 連結)
L2  - {doi_url}               (DOI 連結)
L1  - {pmc_pdf_url}           (PMC PDF 連結)
DB  - PubMed                  (資料庫名稱)
ER  -                         (記錄結束)
```

### RIS 範例輸出

```ris
TY  - JOUR
T1  - Machine Learning Applications in Perioperative Medicine
TI  - Machine Learning Applications in Perioperative Medicine
AU  - Smith, John William
A1  - Smith, John William
AU  - Wang, Li
A1  - Wang, Li
JO  - British Journal of Anaesthesia
JF  - British Journal of Anaesthesia
T2  - British Journal of Anaesthesia
JA  - Br J Anaesth
J2  - Br J Anaesth
SN  - 1471-6771
PY  - 2024
Y1  - 2024
DA  - 2024/Mar/15
VL  - 132
IS  - 3
SP  - 425-437
EP  - 437
AN  - 38123456
C1  - PMID: 38123456
ID  - 38123456
DO  - 10.1016/j.bja.2024.01.015
C2  - PMC10987654
LA  - eng
M3  - Journal Article
M3  - Systematic Review
AB  - Background: Machine learning has emerged as a powerful tool...
N2  - Background: Machine learning has emerged as a powerful tool...
KW  - machine learning
KW  - anesthesia
KW  - Machine Learning
KW  - Anesthesiology
UR  - https://pubmed.ncbi.nlm.nih.gov/38123456/
L2  - https://doi.org/10.1016/j.bja.2024.01.015
L1  - https://www.ncbi.nlm.nih.gov/pmc/articles/PMC10987654/pdf/
DB  - PubMed
ER  - 
```

### prepare_export JSON 回傳結構

```python
# 小型匯出 (≤20 篇)
{
    "status": "success",
    "article_count": 5,
    "format": "ris",
    "export_text": "TY  - JOUR\n...",  # 完整 RIS 文字
    "instructions": "Copy the export_text content and save as .ris"
}

# 大型匯出 (>20 篇)
{
    "status": "success",
    "article_count": 50,
    "format": "ris",
    "message": "Large export saved to file",
    "file_path": "/tmp/pubmed_exports/pubmed_export_50_20240115_143022.ris",
    "instructions": "Use 'cat' or open the file to view contents"
}
```

---

## 6. 標準化文章交換格式設計 (StandardArticle)

### 設計原則

1. **最大公約數**：包含所有來源共有的核心欄位
2. **擴展支援**：允許來源特定的額外欄位
3. **類型一致**：統一欄位類型（如 year 統一為 str）
4. **Zotero 導向**：對應 Zotero 的 Item 欄位

### StandardArticle Schema

```python
from dataclasses import dataclass, field
from typing import Optional, List, Dict, Any
from datetime import date

@dataclass
class StandardAuthor:
    """標準化作者結構"""
    last_name: str
    first_name: str = ""
    initials: str = ""
    affiliations: List[str] = field(default_factory=list)
    orcid: Optional[str] = None
    
    # 集體作者
    collective_name: Optional[str] = None
    
    def to_display_name(self) -> str:
        """返回顯示用名稱"""
        if self.collective_name:
            return self.collective_name
        return f"{self.last_name} {self.first_name}".strip()
    
    def to_ris_format(self) -> str:
        """返回 RIS 格式 (Last, First)"""
        if self.collective_name:
            return self.collective_name
        if self.first_name:
            return f"{self.last_name}, {self.first_name}"
        return self.last_name


@dataclass
class StandardArticle:
    """
    標準化文章交換格式
    
    統一來自 PubMed、Europe PMC、CORE 等來源的文章資料
    """
    
    # === 必填欄位 ===
    title: str
    
    # === 識別碼 (至少需要一個) ===
    pmid: Optional[str] = None
    doi: Optional[str] = None
    pmc_id: Optional[str] = None
    core_id: Optional[str] = None      # CORE 專用
    arxiv_id: Optional[str] = None     # arXiv 專用
    
    # === 作者 ===
    authors: List[StandardAuthor] = field(default_factory=list)
    
    # === 摘要與內容 ===
    abstract: str = ""
    keywords: List[str] = field(default_factory=list)
    mesh_terms: List[str] = field(default_factory=list)
    
    # === 期刊資訊 ===
    journal: str = ""
    journal_abbrev: str = ""
    issn: str = ""
    volume: str = ""
    issue: str = ""
    pages: str = ""
    
    # === 出版資訊 ===
    year: str = ""                     # 統一為字串
    month: str = ""
    day: str = ""
    pub_date: Optional[date] = None    # 解析後的日期物件
    language: str = "eng"              # ISO 639-2 代碼
    publisher: str = ""
    
    # === 類型與分類 ===
    publication_types: List[str] = field(default_factory=list)
    document_type: str = "journalArticle"  # Zotero item type
    
    # === 開放取用與全文 ===
    is_open_access: bool = False
    has_fulltext: bool = False
    has_pdf: bool = False
    fulltext_url: Optional[str] = None
    pdf_url: Optional[str] = None
    
    # === 指標 ===
    citation_count: Optional[int] = None
    
    # === 來源追蹤 ===
    source: str = ""                   # 主要資料來源: pubmed, europe_pmc, core
    data_providers: List[str] = field(default_factory=list)
    
    # === 擴展欄位 (來源特定) ===
    extra: Dict[str, Any] = field(default_factory=dict)
    
    # === URL 生成 ===
    @property
    def pubmed_url(self) -> Optional[str]:
        if self.pmid:
            return f"https://pubmed.ncbi.nlm.nih.gov/{self.pmid}/"
        return None
    
    @property
    def doi_url(self) -> Optional[str]:
        if self.doi:
            return f"https://doi.org/{self.doi}"
        return None
    
    @property
    def pmc_url(self) -> Optional[str]:
        if self.pmc_id:
            return f"https://www.ncbi.nlm.nih.gov/pmc/articles/{self.pmc_id}/"
        return None
    
    @property
    def pmc_pdf_url(self) -> Optional[str]:
        if self.pmc_id:
            return f"https://www.ncbi.nlm.nih.gov/pmc/articles/{self.pmc_id}/pdf/"
        return None
    
    # === 作者便利方法 ===
    @property
    def author_names(self) -> List[str]:
        """返回作者顯示名稱列表"""
        return [a.to_display_name() for a in self.authors]
    
    @property
    def first_author(self) -> Optional[str]:
        """返回第一作者姓氏"""
        if self.authors:
            return self.authors[0].last_name
        return None
    
    # === 轉換方法 ===
    def to_dict(self) -> Dict[str, Any]:
        """轉換為字典格式"""
        from dataclasses import asdict
        return asdict(self)
    
    def to_zotero_item(self) -> Dict[str, Any]:
        """轉換為 Zotero API 格式"""
        creators = []
        for author in self.authors:
            if author.collective_name:
                creators.append({
                    "creatorType": "author",
                    "name": author.collective_name
                })
            else:
                creators.append({
                    "creatorType": "author",
                    "firstName": author.first_name,
                    "lastName": author.last_name
                })
        
        return {
            "itemType": self.document_type,
            "title": self.title,
            "creators": creators,
            "abstractNote": self.abstract,
            "publicationTitle": self.journal,
            "journalAbbreviation": self.journal_abbrev,
            "volume": self.volume,
            "issue": self.issue,
            "pages": self.pages,
            "date": self.year,
            "DOI": self.doi,
            "ISSN": self.issn,
            "language": self.language,
            "extra": f"PMID: {self.pmid}" if self.pmid else "",
            "tags": [{"tag": kw} for kw in self.keywords + self.mesh_terms],
        }


# === 轉換器 ===

class ArticleConverter:
    """文章格式轉換器"""
    
    @staticmethod
    def from_pubmed(data: Dict[str, Any]) -> StandardArticle:
        """從 PubMed 格式轉換"""
        authors = []
        for af in data.get("authors_full", []):
            if af.get("collective_name"):
                authors.append(StandardAuthor(
                    last_name="",
                    collective_name=af["collective_name"]
                ))
            else:
                authors.append(StandardAuthor(
                    last_name=af.get("last_name", ""),
                    first_name=af.get("fore_name", ""),
                    initials=af.get("initials", ""),
                    affiliations=af.get("affiliations", [])
                ))
        
        # 如果沒有 authors_full，使用 authors
        if not authors and data.get("authors"):
            for name in data["authors"]:
                parts = name.split()
                if len(parts) >= 2:
                    authors.append(StandardAuthor(
                        last_name=parts[0],
                        first_name=" ".join(parts[1:])
                    ))
                else:
                    authors.append(StandardAuthor(last_name=name))
        
        return StandardArticle(
            title=data.get("title", ""),
            pmid=data.get("pmid"),
            doi=data.get("doi"),
            pmc_id=data.get("pmc_id"),
            authors=authors,
            abstract=data.get("abstract", ""),
            keywords=data.get("keywords", []),
            mesh_terms=data.get("mesh_terms", []),
            journal=data.get("journal", ""),
            journal_abbrev=data.get("journal_abbrev", ""),
            issn=data.get("issn", ""),
            volume=data.get("volume", ""),
            issue=data.get("issue", ""),
            pages=data.get("pages", ""),
            year=str(data.get("year", "")),
            month=data.get("month", ""),
            day=data.get("day", ""),
            language=data.get("language", "eng"),
            publication_types=data.get("publication_types", []),
            source="pubmed"
        )
    
    @staticmethod
    def from_europe_pmc(data: Dict[str, Any]) -> StandardArticle:
        """從 Europe PMC 格式轉換"""
        article = ArticleConverter.from_pubmed(data)  # 基本結構相同
        
        # 覆蓋來源
        article.source = "europe_pmc"
        
        # 添加 Europe PMC 特有欄位
        article.citation_count = data.get("citation_count")
        article.is_open_access = data.get("is_open_access", False)
        article.has_fulltext = data.get("has_fulltext", False)
        article.has_pdf = data.get("has_pdf", False)
        
        # 保存額外資料
        article.extra = {
            "epmc_source": data.get("source"),
            "pub_type": data.get("pub_type"),
            "epmc_id": data.get("_epmc_id")
        }
        
        return article
    
    @staticmethod
    def from_core(data: Dict[str, Any]) -> StandardArticle:
        """從 CORE 格式轉換"""
        authors = []
        for name in data.get("authors", []):
            if isinstance(name, str):
                parts = name.split()
                if len(parts) >= 2:
                    authors.append(StandardAuthor(
                        last_name=parts[0],
                        first_name=" ".join(parts[1:])
                    ))
                else:
                    authors.append(StandardAuthor(last_name=name))
        
        return StandardArticle(
            title=data.get("title", ""),
            pmid=data.get("pmid"),
            doi=data.get("doi"),
            core_id=str(data.get("core_id", "")),
            arxiv_id=data.get("arxiv_id"),
            authors=authors,
            abstract=data.get("abstract", ""),
            journal=data.get("journal", ""),
            publisher=data.get("publisher", ""),
            year=str(data.get("year", "")),
            language=data.get("language", ""),
            has_fulltext=data.get("has_fulltext", False),
            pdf_url=data.get("pdf_url"),
            fulltext_url=data.get("download_url"),
            citation_count=data.get("citation_count"),
            source="core",
            data_providers=data.get("data_providers", []),
            extra={
                "document_type": data.get("document_type", []),
                "reader_url": data.get("reader_url")
            }
        )
```

### 欄位對照表

| StandardArticle | PubMed | Europe PMC | CORE | Zotero |
|-----------------|--------|------------|------|--------|
| `title` | title | title | title | title |
| `pmid` | pmid | pmid | pmid | extra (PMID) |
| `doi` | doi | doi | doi | DOI |
| `pmc_id` | pmc_id | pmc_id | - | - |
| `authors` | authors_full | authors_full | authors | creators |
| `abstract` | abstract | abstract | abstract | abstractNote |
| `journal` | journal | journal | journal | publicationTitle |
| `journal_abbrev` | journal_abbrev | journal_abbrev | - | journalAbbreviation |
| `issn` | issn | - | - | ISSN |
| `year` | year | year | year | date |
| `volume` | volume | volume | - | volume |
| `issue` | issue | issue | - | issue |
| `pages` | pages | pages | - | pages |
| `keywords` | keywords | keywords | - | tags |
| `mesh_terms` | mesh_terms | mesh_terms | - | tags |
| `language` | language | - | language | language |
| `publication_types` | publication_types | - | document_type | - |
| `citation_count` | - | citation_count | citation_count | - |
| `is_open_access` | - | is_open_access | - | - |
| `has_fulltext` | (pmc_id exists) | has_fulltext | has_fulltext | - |

---

## 使用範例

### 從 PubMed 搜尋結果轉換

```python
from zotero_keeper.models import StandardArticle, ArticleConverter

# 假設這是 search_literature 的結果
pubmed_result = {
    "pmid": "38123456",
    "title": "Machine Learning in Anesthesiology",
    "authors": ["Smith John", "Wang Li"],
    "authors_full": [
        {"last_name": "Smith", "fore_name": "John", "initials": "J"}
    ],
    "journal": "British Journal of Anaesthesia",
    "year": "2024",
    "doi": "10.1016/j.bja.2024.01.015"
}

# 轉換為標準格式
article = ArticleConverter.from_pubmed(pubmed_result)

# 轉換為 Zotero 格式
zotero_item = article.to_zotero_item()
```

### 批次匯入到 Zotero

```python
async def batch_import_to_zotero(articles: List[StandardArticle]):
    """批次匯入文章到 Zotero"""
    zotero_items = [a.to_zotero_item() for a in articles]
    
    # 調用 Zotero API
    response = await zotero_api.create_items(zotero_items)
    return response
```

---

## 總結

### 各來源比較

| 特性 | PubMed | Europe PMC | CORE |
|-----|--------|------------|------|
| 覆蓋範圍 | 生醫文獻 | 生醫 + 歐洲 | 全領域開放取用 |
| 識別碼 | PMID | PMID, PMC | CORE ID, DOI |
| 作者詳情 | ✓ 完整 | ✓ 完整 | ⚠ 僅名稱 |
| MeSH 詞彙 | ✓ 完整 | ✓ 完整 | ✗ 無 |
| 引用數 | ✗ 需 iCite | ✓ 內建 | ✓ 內建 |
| 全文取用 | 需 PMC | ✓ 直接 | ✓ 直接 |
| 期刊縮寫 | ✓ 有 | ✓ 有 | ✗ 無 |
| ISSN | ✓ 有 | ⚠ 部分 | ✗ 無 |

### 建議匯入優先順序

1. **PubMed 來源** → 最完整的書目資料
2. **Europe PMC 來源** → 補充開放取用狀態
3. **CORE 來源** → 補充全文連結

### 下一步

1. 實作 `ArticleConverter` 類別
2. 建立 `StandardArticle` 到 Zotero API 的映射
3. 處理重複檢測（PMID/DOI 對比）
4. 實作批次匯入功能
