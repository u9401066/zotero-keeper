"""
Unified Import Tools for Zotero Keeper

This module provides a SINGLE unified entry point for importing articles from ANY source.

Architecture Decision (2026-01-12):
    Instead of having multiple import tools for different sources
    (import_ris_to_zotero, import_from_pmids, quick_import_pmids, etc.),
    we now have ONE tool: `import_articles`.
    
    This tool accepts the standardized article format from pubmed-search-mcp,
    making it easy to import from any source that MCP supports.

Supported Sources:
    - PubMed (via search_literature, fetch_article_details)
    - Europe PMC (via search_europe_pmc)
    - CORE (via search_core)
    - CrossRef (via DOI lookup)
    - OpenAlex (via openalex_id lookup)
    - Semantic Scholar (via s2_id lookup)
    - Manual entry (direct dict input)
    - RIS text (parsed to articles)

Workflow:
    1. User searches with pubmed-search-mcp → gets articles
    2. Agent passes articles to zotero-keeper's import_articles
    3. Articles are converted to Zotero format and saved

Example:
    # From pubmed-search-mcp search result
    articles = await search_literature("CRISPR", limit=5)
    
    # Import to Zotero
    result = await import_articles(
        articles=articles["articles"],
        collection_name="CRISPR Research",
        tags=["crispr", "2024"]
    )
"""

import logging
import re
from typing import Any

logger = logging.getLogger(__name__)


def _unified_article_to_zotero(article: dict[str, Any]) -> dict[str, Any]:
    """
    Convert unified article format to Zotero item format.
    
    Accepts both:
    - UnifiedArticle.to_dict() output from pubmed-search-mcp
    - Direct search result format (legacy compatibility)
    
    Args:
        article: Article dict from pubmed-search-mcp or similar format
        
    Returns:
        Zotero item dict ready for save_items()
    """
    # Initialize Zotero item
    item: dict[str, Any] = {
        "itemType": "journalArticle",
    }
    
    # Title (required)
    item["title"] = article.get("title", "Unknown Title")
    
    # === Authors ===
    creators = []
    authors = article.get("authors", [])
    
    for author in authors:
        if isinstance(author, str):
            # Simple string format: "John Smith" or "Smith J"
            parts = author.split()
            if len(parts) >= 2:
                # Assume "FirstName LastName" or "LastName Initials"
                if len(parts[-1]) <= 2:  # Likely "Smith J" format
                    creators.append({
                        "lastName": " ".join(parts[:-1]),
                        "firstName": parts[-1],
                        "creatorType": "author",
                    })
                else:  # Likely "John Smith" format
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
            # Dict format from UnifiedArticle
            name = author.get("name") or author.get("full_name") or author.get("display_name", "")
            family = author.get("family_name") or author.get("lastName", "")
            given = author.get("given_name") or author.get("firstName", "")
            
            if family or given:
                creators.append({
                    "lastName": family,
                    "firstName": given,
                    "creatorType": "author",
                })
            elif name:
                # Parse full name
                parts = name.split()
                if len(parts) >= 2:
                    creators.append({
                        "firstName": parts[0],
                        "lastName": " ".join(parts[1:]),
                        "creatorType": "author",
                    })
                else:
                    creators.append({
                        "lastName": name,
                        "firstName": "",
                        "creatorType": "author",
                    })
    
    if creators:
        item["creators"] = creators
    
    # === Identifiers ===
    # Handle both nested (UnifiedArticle.to_dict) and flat (legacy) formats
    identifiers = article.get("identifiers", {})
    
    # DOI
    doi = identifiers.get("doi") or article.get("doi") or article.get("DOI")
    if doi:
        # Clean DOI
        doi = doi.replace("https://doi.org/", "").replace("http://doi.org/", "")
        item["DOI"] = doi
    
    # PMID, PMCID in extra field
    extra_parts = []
    pmid = identifiers.get("pmid") or article.get("pmid") or article.get("uid")
    pmc = identifiers.get("pmc") or article.get("pmc") or article.get("pmcid")
    
    if pmid:
        extra_parts.append(f"PMID: {pmid}")
    if pmc:
        pmc_clean = pmc if pmc.startswith("PMC") else f"PMC{pmc}"
        extra_parts.append(f"PMCID: {pmc_clean}")
    
    # Other identifiers
    core_id = identifiers.get("core_id") or article.get("core_id")
    if core_id:
        extra_parts.append(f"CORE: {core_id}")
    
    openalex_id = identifiers.get("openalex_id") or article.get("openalex_id")
    if openalex_id:
        extra_parts.append(f"OpenAlex: {openalex_id}")
    
    s2_id = identifiers.get("s2_id") or article.get("s2_id")
    if s2_id:
        extra_parts.append(f"S2: {s2_id}")
    
    arxiv_id = identifiers.get("arxiv_id") or article.get("arxiv_id")
    if arxiv_id:
        extra_parts.append(f"arXiv: {arxiv_id}")
    
    # Source tracking
    primary_source = article.get("primary_source") or article.get("source")
    if primary_source:
        extra_parts.append(f"Source: {primary_source}")
    
    # Citation metrics (RCR)
    metrics = article.get("citation_metrics", {})
    if isinstance(metrics, dict):
        rcr = metrics.get("rcr") or metrics.get("relative_citation_ratio")
        if rcr:
            extra_parts.append(f"RCR: {rcr}")
        percentile = metrics.get("percentile") or metrics.get("nih_percentile")
        if percentile:
            extra_parts.append(f"Percentile: {percentile}")
        apt = metrics.get("apt")
        if apt:
            extra_parts.append(f"APT: {apt}")
        citation_count = metrics.get("citation_count")
        if citation_count:
            extra_parts.append(f"Citations: {citation_count}")
    
    if extra_parts:
        item["extra"] = "\n".join(extra_parts)
    
    # === Bibliographic ===
    # Abstract
    abstract = article.get("abstract") or article.get("abstractNote")
    if abstract:
        item["abstractNote"] = abstract
    
    # Journal
    journal = article.get("journal") or article.get("publicationTitle")
    if journal:
        item["publicationTitle"] = journal
    
    # Volume, Issue, Pages
    if article.get("volume"):
        item["volume"] = str(article["volume"])
    if article.get("issue"):
        item["issue"] = str(article["issue"])
    if article.get("pages"):
        item["pages"] = article["pages"]
    
    # Date/Year
    year = article.get("year") or article.get("date")
    if year:
        item["date"] = str(year)
    elif article.get("publication_date"):
        # ISO date format
        item["date"] = article["publication_date"][:10] if len(article["publication_date"]) >= 10 else article["publication_date"]
    
    # === URL ===
    # Prefer DOI URL, then PubMed, then provided URL
    urls = article.get("urls", {})
    url = (
        urls.get("doi") or 
        urls.get("pubmed") or 
        urls.get("pmc") or
        article.get("url")
    )
    if not url and doi:
        url = f"https://doi.org/{doi}"
    elif not url and pmid:
        url = f"https://pubmed.ncbi.nlm.nih.gov/{pmid}/"
    if url:
        item["url"] = url
    
    # === Tags ===
    # Combine keywords and MeSH terms
    tags = []
    for kw in article.get("keywords", [])[:10]:
        tags.append({"tag": kw})
    for mesh in article.get("mesh_terms", [])[:10]:
        if mesh not in [t["tag"] for t in tags]:
            tags.append({"tag": mesh})
    if tags:
        item["tags"] = tags
    
    # === Language ===
    if article.get("language"):
        item["language"] = article["language"]
    
    return item


def _parse_ris_to_articles(ris_text: str) -> list[dict[str, Any]]:
    """
    Parse RIS format text to article dicts.
    
    This reuses the existing RIS parser but returns unified format.
    """
    articles = []
    current_article: dict[str, Any] = {}
    current_authors: list[str] = []
    current_keywords: list[str] = []
    
    # RIS type to article type mapping
    type_map = {
        "JOUR": "journal-article",
        "BOOK": "book",
        "CHAP": "book-chapter",
        "CONF": "conference-paper",
        "THES": "thesis",
        "RPRT": "report",
    }
    
    for line in ris_text.strip().split('\n'):
        line = line.strip()
        if not line or len(line) < 6:
            continue
        
        match = re.match(r'^([A-Z][A-Z0-9])\s+-\s+(.*)$', line)
        if not match:
            continue
        
        tag, value = match.groups()
        value = value.strip()
        
        if tag == "TY":
            if current_article and current_article.get("title"):
                if current_authors:
                    current_article["authors"] = current_authors
                if current_keywords:
                    current_article["keywords"] = current_keywords
                articles.append(current_article)
            current_article = {
                "primary_source": "ris",
                "article_type": type_map.get(value, "journal-article"),
            }
            current_authors = []
            current_keywords = []
        elif tag == "ER":
            if current_article and current_article.get("title"):
                if current_authors:
                    current_article["authors"] = current_authors
                if current_keywords:
                    current_article["keywords"] = current_keywords
                articles.append(current_article)
            current_article = {}
            current_authors = []
            current_keywords = []
        elif tag in ("TI", "T1"):
            current_article["title"] = value
        elif tag in ("AU", "A1"):
            current_authors.append(value)
        elif tag in ("PY", "Y1"):
            current_article["year"] = value.split("/")[0]
        elif tag in ("JO", "JF", "T2"):
            current_article["journal"] = value
        elif tag == "VL":
            current_article["volume"] = value
        elif tag == "IS":
            current_article["issue"] = value
        elif tag == "SP":
            current_article["pages"] = value
        elif tag == "EP":
            if current_article.get("pages"):
                current_article["pages"] += f"-{value}"
            else:
                current_article["pages"] = value
        elif tag == "DO":
            current_article["doi"] = value
        elif tag == "AB":
            current_article["abstract"] = value
        elif tag == "KW":
            current_keywords.append(value)
        elif tag == "UR":
            current_article["url"] = value
        elif tag == "N1":
            # Notes - often contains PMID
            if "PMID:" in value or value.isdigit():
                pmid_match = re.search(r'(\d+)', value)
                if pmid_match:
                    current_article["pmid"] = pmid_match.group(1)
    
    # Don't forget last article
    if current_article and current_article.get("title"):
        if current_authors:
            current_article["authors"] = current_authors
        if current_keywords:
            current_article["keywords"] = current_keywords
        articles.append(current_article)
    
    return articles


def register_unified_import_tools(mcp, zotero_client):
    """
    Register the unified import tool.
    
    This is the SINGLE entry point for all imports to Zotero.
    """
    
    @mcp.tool()
    async def import_articles(
        articles: list[dict[str, Any]] | None = None,
        ris_text: str | None = None,
        collection_name: str | None = None,
        collection_key: str | None = None,
        tags: list[str] | None = None,
        skip_duplicates: bool = True,
    ) -> dict[str, Any]:
        """
        📥 Unified Import Tool - Import articles from ANY source to Zotero

        統一匯入工具 - 從任何來源匯入文章到 Zotero

        ⭐ THIS IS THE SINGLE TOOL FOR ALL IMPORTS:
        - Accepts articles from pubmed-search-mcp (any search tool)
        - Accepts RIS text (from prepare_export or external sources)
        - Automatically handles format conversion
        - Supports collection targeting with validation

        🔗 INTEGRATION WITH pubmed-search-mcp:
        Articles from these tools can be directly imported:
        - search_literature() → articles
        - search_europe_pmc() → articles
        - search_core() → articles  
        - fetch_article_details() → article
        - prepare_export(format="ris") → ris_text

        ⚠️ COLLECTION 防呆:
        - If collection_name/collection_key is specified but not found → ERROR
        - Returns available collections list for user to choose
        - If no collection specified → saves to library root (with warning)

        Args:
            articles: List of article dicts from pubmed-search-mcp
                     Format: UnifiedArticle.to_dict() or search result format
            ris_text: Alternative - RIS format text to parse and import
            collection_name: Target collection name (human-readable, recommended)
            collection_key: Target collection key (alternative)
            tags: Additional tags to add to all imported items
            skip_duplicates: If True (default), skip articles already in Zotero

        Returns:
            Import result with:
            - success: bool
            - imported: number of items imported
            - skipped: number of duplicates skipped
            - items: list of imported titles
            - saved_to: collection info or "My Library (root)"
            - errors: any errors encountered

        Example - From PubMed search:
            # Step 1: Search with pubmed-search-mcp
            results = await search_literature("machine learning anesthesia", limit=10)
            
            # Step 2: Import to Zotero
            await import_articles(
                articles=results["articles"],
                collection_name="ML Anesthesia",
                tags=["ML", "review-2024"]
            )

        Example - From Europe PMC:
            results = await search_europe_pmc("CRISPR", open_access_only=True)
            await import_articles(articles=results["articles"], collection_name="CRISPR OA")

        Example - From RIS text:
            ris = await prepare_export(pmids="12345678,87654321", format="ris")
            await import_articles(ris_text=ris["content"], collection_name="My Collection")
        """
        result: dict[str, Any] = {
            "success": False,
            "imported": 0,
            "skipped": 0,
            "items": [],
            "errors": [],
        }
        
        try:
            # === Step 1: Validate input ===
            if not articles and not ris_text:
                result["error"] = "Must provide either 'articles' or 'ris_text'"
                result["hint"] = "Use search_literature, search_europe_pmc, etc. to get articles, then pass them here"
                return result
            
            # === Step 2: Parse RIS if provided ===
            if ris_text and not articles:
                articles = _parse_ris_to_articles(ris_text)
                if not articles:
                    result["error"] = "No valid articles found in RIS text"
                    return result
                logger.info(f"Parsed {len(articles)} articles from RIS text")
            
            # === Step 3: Collection validation (防呆) ===
            target_key = None
            target_name = None
            
            if collection_key:
                try:
                    col = await zotero_client.get_collection(collection_key)
                    target_key = collection_key
                    target_name = col.get("data", {}).get("name", collection_key)
                except Exception:
                    collections = await zotero_client.list_collections()
                    available = [
                        {"name": c.get("data", {}).get("name", ""), "key": c.get("key", "")}
                        for c in collections[:20]
                    ]
                    result["error"] = f"Collection key '{collection_key}' not found"
                    result["available_collections"] = available
                    result["hint"] = "Use collection_name instead for human-readable names"
                    return result
            
            elif collection_name:
                found = await zotero_client.find_collection_by_name(collection_name)
                if found:
                    target_key = found.get("key")
                    target_name = found.get("data", {}).get("name", collection_name)
                else:
                    collections = await zotero_client.list_collections()
                    available = [
                        {"name": c.get("data", {}).get("name", ""), "key": c.get("key", "")}
                        for c in collections[:20]
                    ]
                    result["error"] = f"Collection '{collection_name}' not found"
                    result["available_collections"] = available
                    result["hint"] = "Check spelling or use list_collections to see all collections"
                    return result
            
            # === Step 4: Convert articles to Zotero format ===
            zotero_items = []
            for article in articles:
                try:
                    zotero_item = _unified_article_to_zotero(article)
                    
                    # Set collection
                    if target_key:
                        zotero_item["collections"] = [target_key]
                    
                    # Add extra tags
                    if tags:
                        existing_tags = zotero_item.get("tags", [])
                        for tag in tags:
                            existing_tags.append({"tag": tag})
                        zotero_item["tags"] = existing_tags
                    
                    zotero_items.append(zotero_item)
                except Exception as e:
                    result["errors"].append({
                        "title": article.get("title", "Unknown")[:50],
                        "error": str(e),
                    })
            
            if not zotero_items:
                result["error"] = "No valid articles to import"
                return result
            
            # === Step 5: Duplicate check (optional) ===
            items_to_import = zotero_items
            skipped_count = 0
            
            if skip_duplicates:
                # Get existing items to check for duplicates
                # This is a simplified check - just compare titles
                try:
                    # We'll use DOI and PMID for duplicate detection if available
                    existing_dois = set()
                    existing_pmids = set()
                    
                    # Search for potential duplicates
                    for item in zotero_items[:10]:  # Limit initial check
                        if item.get("DOI"):
                            search_results = await zotero_client.search_items(
                                query=item["DOI"],
                                limit=5
                            )
                            for r in search_results:
                                if r.get("data", {}).get("DOI"):
                                    existing_dois.add(r["data"]["DOI"].lower())
                    
                    # Filter out duplicates
                    filtered_items = []
                    for item in zotero_items:
                        doi = item.get("DOI", "").lower()
                        if doi and doi in existing_dois:
                            skipped_count += 1
                            continue
                        filtered_items.append(item)
                    
                    items_to_import = filtered_items
                except Exception as e:
                    logger.warning(f"Duplicate check failed, importing all: {e}")
            
            # === Step 6: Save to Zotero ===
            if items_to_import:
                await zotero_client.save_items(items_to_import)
            
            # === Step 7: Build response ===
            result["success"] = True
            result["imported"] = len(items_to_import)
            result["skipped"] = skipped_count
            result["items"] = [item.get("title", "Untitled")[:50] for item in items_to_import]
            result["message"] = f"Successfully imported {len(items_to_import)} articles to Zotero"
            
            if skipped_count > 0:
                result["message"] += f" ({skipped_count} duplicates skipped)"
            
            # Collection info
            if target_key:
                result["saved_to"] = {"key": target_key, "name": target_name}
            else:
                result["saved_to"] = "My Library (root)"
                result["warning"] = "No collection specified - items saved to library root. Consider specifying collection_name."
            
            return result
            
        except Exception as e:
            logger.error(f"Import failed: {e}")
            result["error"] = str(e)
            return result
    
    logger.info("Unified import tool registered (import_articles)")
