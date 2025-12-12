# Batch Import Design Document

> **Version**: 1.2 Draft  
> **Date**: 2025-12-12  
> **Target Release**: v1.7.0  
> **Status**: Planning

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

### 2. 直接取最原始資料 (Direct Source)

```
❌ 以前: pubmed-search.fetch_article_details() → 截斷的摘要
✅ 現在: NCBI E-utilities XML API → 完整原始資料
```

### 3. MCP 分工明確 (Clear Responsibility)

```
pubmed-search-mcp: 搜尋、全文檢查、引用分析
zotero-keeper:     批次匯入、重複檢測、PDF 附加
```

---

## 🎯 MCP Responsibility Split (重要!)

| Functionality | Responsible MCP | Tool | Notes |
|--------------|-----------------|------|-------|
| **Literature Search** | pubmed-search | `search_literature` | Keep as-is |
| **MeSH/Synonym Expansion** | pubmed-search | `generate_search_queries` | Keep as-is |
| **Fulltext Availability Check** | pubmed-search | `analyze_fulltext_access` | ⚠️ DO NOT duplicate in keeper |
| **Fulltext URLs** | pubmed-search | `get_article_fulltext_links` | ⚠️ DO NOT duplicate in keeper |
| **Citation Metrics** | pubmed-search | `get_citation_metrics` | Keep as-is |
| **Batch Import to Zotero** | zotero-keeper | `batch_import_from_pubmed` | NEW in v1.7.0 |
| **RIS Import** | zotero-keeper | `import_ris_to_zotero` | NEW in v1.7.0 |
| **Download & Attach PDFs** | zotero-keeper | `attach_pmc_pdfs` | NEW in v1.7.0 |
| **Duplicate Detection** | zotero-keeper | `check_duplicate`, `smart_add_reference` | Already exists |
| **Collection Management** | zotero-keeper | `create_collection`, `list_collections` | NEW/Existing |

**Principle: pubmed-search handles retrieval, zotero-keeper handles storage**

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

### Proposed Flow (v1.7.0)
```
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│  pubmed-search  │     │  zotero-keeper  │     │     Zotero      │
│      MCP        │     │      MCP        │     │    Desktop      │
└────────┬────────┘     └────────┬────────┘     └────────┬────────┘
         │                       │                       │
         │◀── fetch_details ────│                       │
         │    (internal call)    │                       │
         │                       │                       │
         │              batch_import_from_pubmed ──────▶│
         │                  (single batch call)          │
         │                       │                       │
         │                       │◀─── result ──────────│
         │                       │                       │
         │              Return: {added: 45,              │
         │                       skipped: 3,             │
         │                       failed: 2}              │
```

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
| `skip_exact_duplicates` | `bool` | No | `True` | Skip if exact DOI+PMID match found |
| `warn_on_similar` | `bool` | No | `True` | Add with warning if DOI matches but title differs |
| `similarity_threshold` | `float` | No | `0.85` | Title similarity threshold for duplicate detection (0-1) |
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

2. Fetch COMPLETE article metadata from PubMed E-utilities
   - Call NCBI efetch.fcgi with rettype=xml
   - Parse XML to extract ALL fields:
     ✓ Title, Authors (with affiliations)
     ✓ Abstract (FULL, not truncated!)
     ✓ Journal, Volume, Issue, Pages
     ✓ DOI, PMID, PMCID
     ✓ Keywords (author-provided)
     ✓ MeSH Terms (controlled vocabulary)
     ✓ Publication Type
     ✓ Language, Date

3. Pre-check duplicates (batch)
   - Query Zotero for existing DOIs and PMIDs
   - Build skip list

4. Map to Zotero schema (COMPLETE)
   - Apply pubmed_to_zotero_item() mapping
   - Include all metadata in appropriate fields
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

## 🔗 Metadata Source: Direct NCBI E-utilities (完整資料!)

### Why Direct NCBI API? (Not via pubmed-search-mcp)

| Approach | Pros | Cons | Decision |
|----------|------|------|----------|
| **pubmed-search's fetch_article_details** | Simple, already exists | ❌ Returns truncated abstract, missing fields | ❌ Not used |
| **Direct NCBI E-utilities XML** | ✅ Complete metadata, all fields | Need to parse XML | ✅ **Use this** |

### NCBI E-utilities API Details

```
Endpoint: https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi
Parameters:
  - db=pubmed
  - id={comma-separated PMIDs}
  - rettype=xml
  - retmode=text
```

### Implementation: `pubmed_client.py`

```python
import httpx
import xml.etree.ElementTree as ET
from dataclasses import dataclass

@dataclass
class PubMedArticle:
    """Complete PubMed article metadata"""
    pmid: str
    title: str
    abstract: str  # FULL abstract!
    authors: list[dict]  # [{firstName, lastName, affiliation}]
    journal: str
    date: str
    volume: str | None
    issue: str | None
    pages: str | None
    doi: str | None
    pmc_id: str | None
    issn: str | None
    language: str
    keywords: list[str]
    mesh_terms: list[str]
    pub_types: list[str]
    affiliations: list[str]


class PubMedClient:
    """Direct NCBI E-utilities client for complete metadata"""
    
    BASE_URL = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils"
    
    async def fetch_articles(self, pmids: list[str]) -> list[PubMedArticle]:
        """Fetch complete metadata for multiple PMIDs"""
        
        url = f"{self.BASE_URL}/efetch.fcgi"
        params = {
            "db": "pubmed",
            "id": ",".join(pmids),
            "rettype": "xml",
            "retmode": "text"
        }
        
        async with httpx.AsyncClient() as client:
            response = await client.get(url, params=params, timeout=30.0)
            response.raise_for_status()
        
        return self._parse_pubmed_xml(response.text)
    
    def _parse_pubmed_xml(self, xml_text: str) -> list[PubMedArticle]:
        """Parse PubMed XML to extract complete metadata"""
        
        root = ET.fromstring(xml_text)
        articles = []
        
        for article_elem in root.findall(".//PubmedArticle"):
            articles.append(self._parse_article(article_elem))
        
        return articles
    
    def _parse_article(self, elem) -> PubMedArticle:
        """Parse single article element"""
        
        # PMID
        pmid = elem.findtext(".//PMID", "")
        
        # Title
        title = elem.findtext(".//ArticleTitle", "")
        
        # Abstract (FULL!)
        abstract_parts = elem.findall(".//Abstract/AbstractText")
        if abstract_parts:
            abstract = " ".join(
                (part.get("Label", "") + ": " if part.get("Label") else "") + 
                (part.text or "")
                for part in abstract_parts
            )
        else:
            abstract = ""
        
        # Authors with affiliations
        authors = []
        for author_elem in elem.findall(".//Author"):
            author = {
                "lastName": author_elem.findtext("LastName", ""),
                "firstName": author_elem.findtext("ForeName", ""),
                "affiliation": author_elem.findtext(".//Affiliation", "")
            }
            if author["lastName"]:  # Skip empty authors
                authors.append(author)
        
        # Journal info
        journal = elem.findtext(".//Journal/Title", "")
        volume = elem.findtext(".//Volume")
        issue = elem.findtext(".//Issue")
        pages = elem.findtext(".//MedlinePgn")
        issn = elem.findtext(".//ISSN")
        
        # Date (prefer ArticleDate, fallback to PubDate)
        article_date = elem.find(".//ArticleDate")
        pub_date = elem.find(".//PubDate")
        if article_date is not None:
            year = article_date.findtext("Year", "")
            month = article_date.findtext("Month", "")
            day = article_date.findtext("Day", "")
            date = f"{year}-{month.zfill(2)}-{day.zfill(2)}" if month and day else year
        elif pub_date is not None:
            date = pub_date.findtext("Year", "")
        else:
            date = ""
        
        # DOI
        doi = None
        for eloc in elem.findall(".//ELocationID"):
            if eloc.get("EIdType") == "doi":
                doi = eloc.text
                break
        
        # PMC ID
        pmc_id = None
        for article_id in elem.findall(".//ArticleId"):
            if article_id.get("IdType") == "pmc":
                pmc_id = article_id.text
                break
        
        # Language
        language = elem.findtext(".//Language", "eng")
        
        # Keywords
        keywords = [kw.text for kw in elem.findall(".//Keyword") if kw.text]
        
        # MeSH terms
        mesh_terms = [
            mesh.findtext("DescriptorName", "")
            for mesh in elem.findall(".//MeshHeading")
        ]
        mesh_terms = [m for m in mesh_terms if m]
        
        # Publication types
        pub_types = [pt.text for pt in elem.findall(".//PublicationType") if pt.text]
        
        # Unique affiliations
        affiliations = list(set(a["affiliation"] for a in authors if a["affiliation"]))
        
        return PubMedArticle(
            pmid=pmid,
            title=title,
            abstract=abstract,
            authors=authors,
            journal=journal,
            date=date,
            volume=volume,
            issue=issue,
            pages=pages,
            doi=doi,
            pmc_id=pmc_id,
            issn=issn,
            language=language,
            keywords=keywords,
            mesh_terms=mesh_terms,
            pub_types=pub_types,
            affiliations=affiliations
        )
```

---

## 📊 Data Flow Diagram

```
┌────────────────────────────────────────────────────────────────────┐
│                        batch_import_from_pubmed                    │
└────────────────────────────────────────────────────────────────────┘
                                  │
                    ┌─────────────┴─────────────┐
                    ▼                           ▼
        ┌──────────────────┐         ┌──────────────────┐
        │ 1. Parse PMIDs   │         │ 2. Fetch Metadata│
        │    (internal)    │         │    from PubMed   │
        └────────┬─────────┘         └────────┬─────────┘
                 │                            │
                 │         ┌──────────────────┘
                 │         ▼
                 │  ┌──────────────────┐
                 │  │ NCBI E-utilities │
                 │  │ efetch.fcgi      │
                 │  │ (XML format)     │
                 │  └────────┬─────────┘
                 │           │
                 ▼           ▼
        ┌──────────────────────────────┐
        │ 3. Parse COMPLETE Metadata   │
        │    - Title, Authors          │
        │    - Abstract (FULL!)        │
        │    - Keywords, MeSH          │
        │    - Affiliations            │
        │    - References              │
        └────────────────┬─────────────┘
                         │
            ┌────────────┴────────────┐
            ▼                         ▼
   ┌─────────────────┐       ┌─────────────────┐
   │ 4. Duplicate    │       │ 5. Map to       │
   │    Check        │       │    Zotero Schema│
   └────────┬────────┘       └────────┬────────┘
            │                         │
            └────────────┬────────────┘
                         ▼
              ┌──────────────────────┐
              │ 6. Batch Import      │
              │    Connector API     │
              │    /saveItems        │
              └────────────┬─────────┘
                           │
                           ▼
              ┌──────────────────────┐
              │ 7. Return Summary    │
              │    BatchImportResult │
              └──────────────────────┘
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
│   ├── pubmed/                    # NEW: PubMed integration ⭐
│   │   ├── __init__.py
│   │   ├── pubmed_client.py      # NCBI E-utilities XML API client
│   │   ├── xml_parser.py         # PubMed XML → PubMedArticle
│   │   └── zotero_mapper.py      # PubMedArticle → Zotero schema
│   │
│   └── zotero_client/
│       └── client.py             # Add batch operations
│
├── domain/
│   └── entities/
│       ├── pubmed_article.py     # NEW: Complete PubMed metadata ⭐
│       └── batch_result.py       # NEW: BatchImportResult ⭐
│
└── application/
    └── use_cases/
        └── batch_import.py       # NEW: BatchImportUseCase ⭐
```

### New Dependencies

```toml
# pyproject.toml additions
dependencies = [
    # ... existing ...
    "defusedxml>=0.7.1",  # Safe XML parsing (security)
]
```

---

## 🚀 Implementation Plan

### Phase 1: Core Infrastructure (Day 1)
- [ ] Create `pubmed_client.py` with NCBI E-utilities integration
- [ ] Create `batch_result.py` domain entity
- [ ] Add batch duplicate checking to `zotero_client.py`

### Phase 2: Primary Tool (Day 2)
- [ ] Implement `batch_import_from_pubmed` in `batch_tools.py`
- [ ] Unit tests for batch import
- [ ] Integration test with real Zotero

### Phase 3: Backup Tool (Day 3)
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
| NCBI API rate limiting | Implement exponential backoff, respect 3 req/sec |
| Large batch size | Limit to 100 PMIDs per call |
| Malicious RIS content | Sanitize input, validate format |
| Network timeouts | Set reasonable timeouts (30s), retry logic |

---

## 📈 Success Metrics

| Metric | Target |
|--------|--------|
| Batch import speed | 50 articles in < 30 seconds |
| Success rate | > 95% for valid PMIDs |
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
│ │ 1. NCBI E-utilities efetch.fcgi (XML format)                │ │
│ │    → Fetch COMPLETE metadata for all PMIDs                  │ │
│ │                                                             │ │
│ │ 2. Parse XML to extract:                                    │ │
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
