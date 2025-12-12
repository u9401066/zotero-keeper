"""
Batch Import Tools for Zotero Keeper

High-performance batch import with complete metadata preservation.
Uses direct Python import from pubmed-search library (submodule).

Architecture:
- zotero-keeper directly imports pubmed-search as Python library
- Data flows: pubmed-search → mapper → Zotero
- No Agent intermediary - complete metadata preserved!

Tools:
- batch_import_from_pubmed: Primary batch import (PMID → complete metadata → Zotero)
"""

import logging
import time
from typing import Any

logger = logging.getLogger(__name__)

# Import domain entities
from ...domain.entities.batch_result import (
    BatchImportResult,
    ImportedItem,
    ImportAction,
)

# Import mappers
from ..mappers.pubmed_mapper import (
    map_pubmed_to_zotero,
    extract_pmid_from_zotero_item,
    extract_doi_from_zotero_item,
)

# Import pubmed integration
from ..pubmed import fetch_pubmed_articles, get_pubmed_client

# Check if pubmed-search is available
try:
    _pubmed_client = get_pubmed_client()
    BATCH_IMPORT_AVAILABLE = True
except ImportError:
    BATCH_IMPORT_AVAILABLE = False
    logger.warning(
        "pubmed-search submodule not available. "
        "Batch import disabled. "
        "Run: git submodule update --init --recursive"
    )


def is_batch_import_available() -> bool:
    """Check if batch import is available."""
    return BATCH_IMPORT_AVAILABLE


def register_batch_tools(mcp, zotero_client):
    """
    Register batch import tools.
    
    Args:
        mcp: FastMCP server instance
        zotero_client: ZoteroClient instance
    """
    
    @mcp.tool()
    async def batch_import_from_pubmed(
        pmids: str,
        tags: list[str] | None = None,
        skip_duplicates: bool = True,
        collection_key: str | None = None,
    ) -> dict[str, Any]:
        """
        📦 Batch import PubMed articles to Zotero with complete metadata
        
        批次匯入 PubMed 文獻到 Zotero，保留完整的 metadata！
        
        Features:
        - ✅ Complete abstract (not truncated!)
        - ✅ Author keywords + MeSH terms → tags
        - ✅ PMID, PMCID, affiliations → extra field
        - ✅ Batch duplicate detection (by PMID/DOI)
        - ✅ Detailed result reporting
        
        Args:
            pmids: Comma-separated PMIDs (e.g., "38353755,37864754")
                   or "last" to use results from last search (requires session)
            tags: Additional tags to apply to all imported articles
            skip_duplicates: Skip if exact PMID or DOI match found (default: True)
            collection_key: Zotero collection key to add items to (optional)
            
        Returns:
            Detailed import result:
            {
                "success": true,
                "total": 30,
                "added": 27,
                "skipped": 2 (duplicates),
                "warnings": 1 (possible duplicates),
                "failed": 0,
                "added_items": [...],
                "skipped_items": [...],
                "elapsed_time": 12.5
            }
            
        Example:
            # After searching with pubmed-search-mcp
            batch_import_from_pubmed(
                pmids="38353755,37864754,38215710",
                tags=["Anesthesia-AI", "2024"],
                skip_duplicates=True
            )
            
        Workflow:
            1. pubmed-search: search_literature("AI anesthesia") → PMIDs
            2. pubmed-search: (optional) analyze_fulltext_access(pmids)
            3. zotero-keeper: batch_import_from_pubmed(pmids) → Zotero
        """
        if not BATCH_IMPORT_AVAILABLE:
            return {
                "success": False,
                "error": "pubmed-search submodule not available",
                "hint": "Run: git submodule update --init --recursive",
            }
        
        start_time = time.time()
        result = BatchImportResult()
        
        try:
            # 1. Parse PMIDs
            pmid_list = _parse_pmids(pmids)
            
            if not pmid_list:
                return {
                    "success": False,
                    "error": "No valid PMIDs provided",
                    "hint": "Provide comma-separated PMIDs, e.g., '38353755,37864754'",
                }
            
            logger.info(f"Batch import: {len(pmid_list)} PMIDs")
            
            # 2. Fetch complete metadata from pubmed-search library
            # This is DIRECT Python import, not MCP call!
            # Data is complete and not truncated!
            try:
                articles = fetch_pubmed_articles(pmid_list)
            except Exception as e:
                logger.error(f"Failed to fetch from PubMed: {e}")
                return {
                    "success": False,
                    "error": f"Failed to fetch article details: {e}",
                }
            
            if not articles:
                return {
                    "success": False,
                    "error": "No articles found for provided PMIDs",
                    "pmids_provided": len(pmid_list),
                }
            
            logger.info(f"Fetched {len(articles)} articles from PubMed")
            
            # 3. Check for duplicates (batch)
            existing_identifiers = {"existing_pmids": set(), "existing_dois": set()}
            pmid_to_key = {}
            doi_to_key = {}
            
            if skip_duplicates:
                # Extract DOIs from articles
                article_dois = [
                    a.get("doi", "").lower()
                    for a in articles
                    if a.get("doi")
                ]
                
                try:
                    check_result = await zotero_client.batch_check_identifiers(
                        pmids=pmid_list,
                        dois=article_dois,
                    )
                    existing_identifiers = check_result
                    pmid_to_key = check_result.get("pmid_to_key", {})
                    doi_to_key = check_result.get("doi_to_key", {})
                    
                    logger.info(
                        f"Duplicate check: {len(existing_identifiers['existing_pmids'])} PMIDs, "
                        f"{len(existing_identifiers['existing_dois'])} DOIs already exist"
                    )
                except Exception as e:
                    logger.warning(f"Duplicate check failed: {e}")
                    # Continue without duplicate checking
            
            # 4. Process each article
            items_to_save = []
            
            for article in articles:
                pmid = article.get("pmid", "")
                title = article.get("title", "Unknown")[:100]
                doi = article.get("doi", "").lower()
                
                # Check if duplicate
                if skip_duplicates:
                    if pmid in existing_identifiers.get("existing_pmids", set()):
                        result.add_item(ImportedItem(
                            pmid=pmid,
                            title=title,
                            action=ImportAction.SKIPPED,
                            reason=f"PMID already exists (key: {pmid_to_key.get(pmid, 'unknown')})",
                        ))
                        continue
                    
                    if doi and doi in existing_identifiers.get("existing_dois", set()):
                        result.add_item(ImportedItem(
                            pmid=pmid,
                            title=title,
                            action=ImportAction.SKIPPED,
                            reason=f"DOI already exists (key: {doi_to_key.get(doi, 'unknown')})",
                        ))
                        continue
                
                # Map to Zotero schema (complete metadata!)
                try:
                    zotero_item = map_pubmed_to_zotero(article, extra_tags=tags)
                    items_to_save.append((pmid, title, zotero_item))
                except Exception as e:
                    logger.error(f"Failed to map article {pmid}: {e}")
                    result.add_item(ImportedItem(
                        pmid=pmid,
                        title=title,
                        action=ImportAction.FAILED,
                        error=f"Mapping error: {e}",
                    ))
            
            # 5. Batch save to Zotero
            if items_to_save:
                try:
                    # Extract just the items for saving
                    zotero_items = [item[2] for item in items_to_save]
                    
                    save_result = await zotero_client.batch_save_items(
                        items=zotero_items,
                        uri="http://mcp-bridge.local/batch-import-from-pubmed",
                        title="PubMed Batch Import",
                    )
                    
                    # Process save results
                    # Note: Zotero Connector API doesn't return individual keys easily
                    # So we mark all as added for now
                    for pmid, title, _ in items_to_save:
                        result.add_item(ImportedItem(
                            pmid=pmid,
                            title=title,
                            action=ImportAction.ADDED,
                            zotero_key=None,  # Key not available from Connector API
                        ))
                    
                    logger.info(f"Saved {len(items_to_save)} items to Zotero")
                    
                except Exception as e:
                    logger.error(f"Failed to save to Zotero: {e}")
                    # Mark all pending items as failed
                    for pmid, title, _ in items_to_save:
                        result.add_item(ImportedItem(
                            pmid=pmid,
                            title=title,
                            action=ImportAction.FAILED,
                            error=f"Save error: {e}",
                        ))
            
            # 6. Add to collection if specified
            if collection_key and result.added > 0:
                result.collection_key = collection_key
                # Note: Adding to collection requires additional API calls
                # This would need to be implemented via Zotero Local API
                logger.info(f"Collection key specified: {collection_key} (not yet implemented)")
            
            # 7. Finalize result
            result.elapsed_time = time.time() - start_time
            
            return result.to_dict()
            
        except Exception as e:
            logger.error(f"Batch import failed: {e}")
            result.success = False
            result.elapsed_time = time.time() - start_time
            return {
                **result.to_dict(),
                "error": str(e),
            }
    
    logger.info("Batch import tools registered (batch_import_from_pubmed)")


def _parse_pmids(pmids_input: str) -> list[str]:
    """
    Parse PMID input string to list of PMIDs.
    
    Args:
        pmids_input: Comma-separated PMIDs or special values like "last"
        
    Returns:
        List of PMID strings
    """
    if not pmids_input:
        return []
    
    # Handle "last" keyword (would need session state)
    if pmids_input.strip().lower() == "last":
        # TODO: Implement session-based last search results
        logger.warning("'last' keyword not yet implemented")
        return []
    
    # Parse comma-separated PMIDs
    pmids = []
    for pmid in pmids_input.split(","):
        pmid = pmid.strip()
        if pmid and pmid.isdigit():
            pmids.append(pmid)
        elif pmid:
            logger.warning(f"Invalid PMID skipped: {pmid}")
    
    return pmids
