"""
PubMed Import Tools for Zotero Keeper

Focused import tools that complement pubmed-search-mcp.
Use pubmed-search-mcp for searching, use these tools for importing to Zotero.

Recommended Workflow:
1. pubmed-search: search_literature("CRISPR") → PMIDs
2. pubmed-search: prepare_export(pmids, format="ris") → RIS text
3. zotero-keeper: import_ris_to_zotero(ris_text) → Zotero items

Alternative (requires pubmed extra):
1. pubmed-search: search_literature("CRISPR") → PMIDs
2. zotero-keeper: import_from_pmids(pmids) → Zotero items
"""

import logging
import re
from typing import Any, Optional

logger = logging.getLogger(__name__)

# Check if pubmed-search-mcp is available (for direct PMID import)
try:
    from pubmed_search import PubMedClient
    PUBMED_AVAILABLE = True
except ImportError:
    PUBMED_AVAILABLE = False
    logger.info("pubmed-search-mcp not installed. Direct PMID import disabled.")
    logger.info("Install with: pip install 'zotero-keeper[pubmed]'")


def _parse_ris_to_zotero_items(ris_text: str) -> list[dict[str, Any]]:
    """
    Parse RIS format text to Zotero item format.
    
    RIS tags reference:
    - TY: Type (JOUR = journalArticle)
    - TI/T1: Title
    - AU/A1: Author
    - PY/Y1: Year
    - JO/JF/T2: Journal
    - VL: Volume
    - IS: Issue
    - SP/EP: Start/End Page
    - DO: DOI
    - AB: Abstract
    - KW: Keywords
    - UR: URL
    """
    items = []
    current_item: dict[str, Any] = {}
    current_authors: list[dict] = []
    current_tags: list[dict] = []
    
    # RIS type to Zotero type mapping
    type_map = {
        "JOUR": "journalArticle",
        "BOOK": "book",
        "CHAP": "bookSection",
        "CONF": "conferencePaper",
        "THES": "thesis",
        "RPRT": "report",
        "ELEC": "webpage",
        "GEN": "document",
    }
    
    for line in ris_text.strip().split('\n'):
        line = line.strip()
        if not line or len(line) < 6:
            continue
        
        # Parse RIS tag format: "XX  - value"
        match = re.match(r'^([A-Z][A-Z0-9])\s+-\s+(.*)$', line)
        if not match:
            continue
            
        tag, value = match.groups()
        value = value.strip()
        
        if tag == "TY":
            # Start new record
            if current_item:
                if current_authors:
                    current_item["creators"] = current_authors
                if current_tags:
                    current_item["tags"] = current_tags
                items.append(current_item)
            current_item = {"itemType": type_map.get(value, "journalArticle")}
            current_authors = []
            current_tags = []
        elif tag == "ER":
            # End record
            if current_item:
                if current_authors:
                    current_item["creators"] = current_authors
                if current_tags:
                    current_item["tags"] = current_tags
                items.append(current_item)
            current_item = {}
            current_authors = []
            current_tags = []
        elif tag in ("TI", "T1"):
            current_item["title"] = value
        elif tag in ("AU", "A1"):
            # Author format: "LastName, FirstName" or "LastName"
            if "," in value:
                parts = value.split(",", 1)
                current_authors.append({
                    "lastName": parts[0].strip(),
                    "firstName": parts[1].strip() if len(parts) > 1 else "",
                    "creatorType": "author"
                })
            else:
                current_authors.append({
                    "lastName": value,
                    "firstName": "",
                    "creatorType": "author"
                })
        elif tag in ("PY", "Y1"):
            # Year: might be "2024" or "2024/01/15"
            current_item["date"] = value.split("/")[0]
        elif tag in ("JO", "JF", "T2"):
            current_item["publicationTitle"] = value
        elif tag == "VL":
            current_item["volume"] = value
        elif tag == "IS":
            current_item["issue"] = value
        elif tag == "SP":
            current_item["pages"] = value
        elif tag == "EP":
            if current_item.get("pages"):
                current_item["pages"] += f"-{value}"
            else:
                current_item["pages"] = value
        elif tag == "DO":
            current_item["DOI"] = value
        elif tag == "AB":
            current_item["abstractNote"] = value
        elif tag == "KW":
            current_tags.append({"tag": value})
        elif tag == "UR":
            current_item["url"] = value
        elif tag == "SN":
            current_item["ISSN"] = value
        elif tag == "N1":
            # Notes - often contains PMID
            if "PMID:" in value or value.isdigit():
                pmid = re.search(r'(\d+)', value)
                if pmid:
                    current_item["extra"] = f"PMID: {pmid.group(1)}"
            else:
                current_item["extra"] = value
    
    # Don't forget last item if no ER tag
    if current_item and current_item.get("title"):
        if current_authors:
            current_item["creators"] = current_authors
        if current_tags:
            current_item["tags"] = current_tags
        items.append(current_item)
    
    return items


def _pmid_to_zotero_item(article: dict) -> dict[str, Any]:
    """Convert PubMed article dict to Zotero item format."""
    creators = []
    for author in article.get("authors", []):
        if isinstance(author, str):
            parts = author.split()
            if len(parts) >= 2:
                creators.append({
                    "firstName": parts[0],
                    "lastName": " ".join(parts[1:]),
                    "creatorType": "author",
                })
            else:
                creators.append({
                    "lastName": author,
                    "firstName": "",
                    "creatorType": "author",
                })
        elif isinstance(author, dict):
            creators.append({
                "firstName": author.get("firstName", author.get("first_name", "")),
                "lastName": author.get("lastName", author.get("last_name", "")),
                "creatorType": "author",
            })
    
    item: dict[str, Any] = {
        "itemType": "journalArticle",
        "title": article.get("title", ""),
        "creators": creators,
    }
    
    if article.get("abstract"):
        item["abstractNote"] = article["abstract"]
    if article.get("journal"):
        item["publicationTitle"] = article["journal"]
    if article.get("year"):
        item["date"] = str(article["year"])
    if article.get("volume"):
        item["volume"] = article["volume"]
    if article.get("issue"):
        item["issue"] = article["issue"]
    if article.get("pages"):
        item["pages"] = article["pages"]
    if article.get("doi"):
        item["DOI"] = article["doi"]
    
    # PMID and PMCID in extra field
    extra_parts = []
    if article.get("pmid"):
        extra_parts.append(f"PMID: {article['pmid']}")
    if article.get("pmc_id"):
        extra_parts.append(f"PMCID: {article['pmc_id']}")
    if extra_parts:
        item["extra"] = "\n".join(extra_parts)
    
    # URL
    if article.get("url"):
        item["url"] = article["url"]
    elif article.get("pmid"):
        item["url"] = f"https://pubmed.ncbi.nlm.nih.gov/{article['pmid']}/"
    
    # Tags from MeSH or keywords
    if article.get("mesh_terms"):
        item["tags"] = [{"tag": term} for term in article["mesh_terms"][:10]]
    elif article.get("keywords"):
        item["tags"] = [{"tag": kw} for kw in article["keywords"][:10]]
    
    return item


def register_pubmed_tools(mcp, zotero_client):
    """
    Register PubMed import tools.
    
    These tools complement pubmed-search-mcp by providing import functionality.
    """
    
    @mcp.tool()
    async def import_ris_to_zotero(
        ris_text: str,
        tags: Optional[list[str]] = None,
    ) -> dict[str, Any]:
        """
        📥 Import RIS format citations to Zotero
        
        將 RIS 格式的引用文獻匯入 Zotero
        
        Recommended workflow with pubmed-search-mcp:
        1. pubmed: search_literature("query") → PMIDs
        2. pubmed: prepare_export(pmids, format="ris") → RIS text
        3. keeper: import_ris_to_zotero(ris_text) → Zotero
        
        Args:
            ris_text: RIS format citation text (from prepare_export or other sources)
            tags: Optional tags to add to all imported items
            
        Returns:
            Import result with count of imported items
            
        Example:
            import_ris_to_zotero(
                ris_text=\"\"\"
                TY  - JOUR
                TI  - CRISPR-Cas9 Gene Editing
                AU  - Doudna, Jennifer
                PY  - 2020
                JO  - Science
                DO  - 10.1126/science.example
                ER  -
                \"\"\",
                tags=["gene-editing", "review"]
            )
        """
        try:
            # Parse RIS to Zotero items
            items = _parse_ris_to_zotero_items(ris_text)
            
            if not items:
                return {
                    "success": False,
                    "message": "No valid items found in RIS text",
                    "imported": 0,
                }
            
            # Add custom tags
            if tags:
                for item in items:
                    existing_tags = item.get("tags", [])
                    for tag in tags:
                        existing_tags.append({"tag": tag})
                    item["tags"] = existing_tags
            
            # Import to Zotero
            await zotero_client.save_items(items)
            
            # Build response
            imported_titles = [item.get("title", "Untitled")[:50] for item in items]
            
            return {
                "success": True,
                "imported": len(items),
                "items": imported_titles,
                "message": f"Successfully imported {len(items)} items to Zotero",
            }
            
        except Exception as e:
            logger.error(f"RIS import failed: {e}")
            return {
                "success": False,
                "error": str(e),
            }
    
    @mcp.tool()
    async def import_from_pmids(
        pmids: list[str],
        tags: Optional[list[str]] = None,
    ) -> dict[str, Any]:
        """
        📥 Import PubMed articles directly by PMID
        
        直接透過 PMID 匯入 PubMed 文獻到 Zotero
        
        Requires: pip install "zotero-keeper[pubmed]"
        
        Alternative workflow (without pubmed extra):
        1. pubmed: search_literature("query") → PMIDs
        2. keeper: import_from_pmids(pmids) → Zotero
        
        Args:
            pmids: List of PubMed IDs ["12345678", "87654321"]
            tags: Optional tags to add to all items
            
        Returns:
            Import result
            
        Example:
            import_from_pmids(
                pmids=["28968381", "28324054"],
                tags=["ML", "review"]
            )
        """
        if not PUBMED_AVAILABLE:
            return {
                "success": False,
                "error": "pubmed-search-mcp not installed",
                "hint": "Install with: pip install 'zotero-keeper[pubmed]'",
                "alternative": "Use import_ris_to_zotero with RIS text from pubmed-search-mcp's prepare_export tool",
            }
        
        try:
            import os
            email = os.environ.get("NCBI_EMAIL", "zotero-keeper@example.com")
            client = PubMedClient(email=email)
            
            # Fetch article details (returns SearchResult objects)
            results = client.fetch_by_pmids(pmids)
            
            if not results:
                return {
                    "success": False,
                    "message": "No articles found for given PMIDs",
                    "imported": 0,
                }
            
            # Convert SearchResult objects to dicts, then to Zotero format
            zotero_items = []
            articles_info = []
            for result in results:
                # Convert SearchResult to dict
                article = result.to_dict() if hasattr(result, 'to_dict') else result
                articles_info.append(article)
                
                item = _pmid_to_zotero_item(article)
                if tags:
                    existing_tags = item.get("tags", [])
                    for tag in tags:
                        existing_tags.append({"tag": tag})
                    item["tags"] = existing_tags
                zotero_items.append(item)
            
            # Import to Zotero
            await zotero_client.save_items(zotero_items)
            
            # Build response
            imported_info = [
                {"pmid": a.get("pmid"), "title": a.get("title", "")[:50]}
                for a in articles_info
            ]
            
            return {
                "success": True,
                "imported": len(zotero_items),
                "items": imported_info,
                "message": f"Successfully imported {len(zotero_items)} articles to Zotero",
            }
            
        except Exception as e:
            logger.error(f"PMID import failed: {e}")
            return {
                "success": False,
                "error": str(e),
            }
    
    logger.info("PubMed import tools registered (import_ris_to_zotero, import_from_pmids)")


def is_pubmed_available() -> bool:
    """Check if direct PMID import is available"""
    return PUBMED_AVAILABLE
