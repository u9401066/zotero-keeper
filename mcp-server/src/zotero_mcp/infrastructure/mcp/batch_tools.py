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

# Import domain entities  # noqa: E402
from ...domain.entities.batch_result import (
    BatchImportResult,
    ImportAction,
    ImportedItem,
)

# Import mappers  # noqa: E402
from ..mappers.pubmed_mapper import (
    map_pubmed_to_zotero,
)

# Import pubmed integration  # noqa: E402
from ..pubmed import fetch_pubmed_articles, get_pubmed_client, is_using_submodule

# Check if pubmed-search is available
try:
    _pubmed_client = get_pubmed_client()
    BATCH_IMPORT_AVAILABLE = True
    if is_using_submodule():
        logger.info("Batch import enabled (using submodule)")
    else:
        logger.info("Batch import enabled (using installed package)")
except ImportError as e:
    BATCH_IMPORT_AVAILABLE = False
    logger.warning(
        f"pubmed-search not available: {e}\n"
        "Batch import disabled. Options:\n"
        "  1. Development: git submodule update --init --recursive\n"
        "  2. Production: uv pip install pubmed-search-mcp"
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
        collection_name: str | None = None,
        include_citation_metrics: bool = True,
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
        - ✅ Collection validation (防呆機制!)
        - ✅ Citation metrics (RCR, percentile) → extra field (default ON!)

        ⚠️ IMPORTANT - 防呆提醒:
        - 使用 collection_name 參數 (推薦!) 可自動驗證名稱是否存在
        - 如果名稱不存在，會回傳可用的 collections 清單
        - 避免使用 collection_key，除非你確定 key 是對的
        - 需要查看 collections？先呼叫 list_collections() 或 get_collection_tree()

        Args:
            pmids: Comma-separated PMIDs (e.g., "38353755,37864754")
            tags: Additional tags to apply to all imported articles
            skip_duplicates: Skip if exact PMID or DOI match found (default: True)
            collection_key: Zotero collection key (⚠️ 不建議直接使用，容易出錯)
            collection_name: Collection name (推薦! 自動驗證並解析為 key)
            include_citation_metrics: If True (default), fetch RCR/percentile from iCite
                                      and add to extra field

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
                "elapsed_time": 12.5,
                "collection_info": {"key": "ABC123", "name": "test1"}  // 確認用!
            }

        Example:
            # ✅ 推薦：使用 collection_name (會自動驗證!)
            # RCR 預設會自動取得並存入 extra 欄位
            batch_import_from_pubmed(
                pmids="38353755,37864754",
                collection_name="test1"
            )

            # 如果不需要 RCR (較快)
            batch_import_from_pubmed(
                pmids="38353755,37864754",
                collection_name="test1",
                include_citation_metrics=False
            )

        Workflow:
            1. (可選) zotero-keeper: list_collections() → 確認目標 collection 名稱
            2. pubmed-search: search_literature("AI anesthesia") → PMIDs
            3. zotero-keeper: batch_import_from_pubmed(pmids, collection_name="xxx")
        """
        if not BATCH_IMPORT_AVAILABLE:
            return {
                "success": False,
                "error": "pubmed-search submodule not available",
                "hint": "Run: git submodule update --init --recursive",
            }

        start_time = time.time()
        result = BatchImportResult()

        # === 防呆機制 1: Collection 驗證 ===
        validated_collection_key = None
        collection_info = None

        if collection_name or collection_key:
            try:
                if collection_name and not collection_key:
                    # 用名稱查找 collection
                    collections = await zotero_client.get_collections()
                    found = None
                    for col in collections:
                        col_name = col.get("data", {}).get("name", "")
                        if col_name.lower() == collection_name.lower():
                            found = col
                            break

                    if not found:
                        # 提供相似名稱建議
                        similar = [c.get("data", {}).get("name", "") for c in collections if collection_name.lower() in c.get("data", {}).get("name", "").lower()][:5]
                        return {
                            "success": False,
                            "error": f"Collection '{collection_name}' not found",
                            "hint": f"Similar collections: {similar}" if similar else "Use list_collections() to see available collections",
                            "available_collections": [{"key": c.get("key"), "name": c.get("data", {}).get("name", "")} for c in collections[:10]],
                        }

                    validated_collection_key = found.get("key")
                    collection_info = {
                        "key": validated_collection_key,
                        "name": found.get("data", {}).get("name", ""),
                        "resolved_from": "name",
                    }
                    logger.info(f"Resolved collection '{collection_name}' → key: {validated_collection_key}")

                elif collection_key:
                    # 驗證 collection_key 是否存在
                    collections = await zotero_client.get_collections()
                    found = None
                    for col in collections:
                        if col.get("key") == collection_key:
                            found = col
                            break

                    if not found:
                        return {
                            "success": False,
                            "error": f"Collection key '{collection_key}' not found",
                            "hint": "Use list_collections() to see available collections",
                            "available_collections": [{"key": c.get("key"), "name": c.get("data", {}).get("name", "")} for c in collections[:10]],
                        }

                    validated_collection_key = collection_key
                    collection_info = {
                        "key": validated_collection_key,
                        "name": found.get("data", {}).get("name", ""),
                        "resolved_from": "key",
                    }
                    logger.info(f"Validated collection key: {validated_collection_key} ({found.get('data', {}).get('name', '')})")

            except Exception as e:
                logger.warning(f"Collection validation failed: {e}")
                # 如果驗證失敗但有 key，繼續使用（向後相容）
                if collection_key:
                    validated_collection_key = collection_key
                    collection_info = {
                        "key": collection_key,
                        "name": "unknown (validation failed)",
                        "warning": str(e),
                    }

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
                articles = await fetch_pubmed_articles(pmid_list)
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

            # 2.5. Fetch citation metrics if requested
            citation_metrics = {}
            if include_citation_metrics:
                try:
                    from ..pubmed import get_pubmed_client

                    client = get_pubmed_client()
                    # Import LiteratureSearcher from pubmed_search
                    # Note: pubmed_search is configured via ../pubmed/__init__.py
                    from pubmed_search import LiteratureSearcher  # type: ignore

                    searcher = LiteratureSearcher(
                        email=getattr(client, "email", "zotero@example.com"), api_key=getattr(client, "api_key", None)
                    )
                    citation_metrics = await searcher.get_citation_metrics(pmid_list)
                    logger.info(f"Fetched citation metrics for {len(citation_metrics)} articles")
                except ImportError as e:
                    logger.warning(f"Cannot import LiteratureSearcher for citation metrics: {e}")
                except Exception as e:
                    logger.warning(f"Failed to fetch citation metrics: {e}")
                    # Continue without metrics

            # Merge citation metrics into articles
            if citation_metrics:
                for article in articles:
                    pmid = article.get("pmid", "")
                    if pmid in citation_metrics:
                        metrics = citation_metrics[pmid]
                        # Add metrics fields to article
                        article["relative_citation_ratio"] = metrics.get("relative_citation_ratio")
                        article["nih_percentile"] = metrics.get("nih_percentile")
                        article["citation_count"] = metrics.get("citation_count")
                        article["citations_per_year"] = metrics.get("citations_per_year")
                        article["apt"] = metrics.get("apt")

            # 3. Check for duplicates (batch)
            existing_identifiers = {"existing_pmids": set(), "existing_dois": set()}
            pmid_to_key = {}
            doi_to_key = {}

            if skip_duplicates:
                # Extract DOIs from articles
                article_dois = [a.get("doi", "").lower() for a in articles if a.get("doi")]

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
                        result.add_item(
                            ImportedItem(
                                pmid=pmid,
                                title=title,
                                action=ImportAction.SKIPPED,
                                reason=f"PMID already exists (key: {pmid_to_key.get(pmid, 'unknown')})",
                            )
                        )
                        continue

                    if doi and doi in existing_identifiers.get("existing_dois", set()):
                        result.add_item(
                            ImportedItem(
                                pmid=pmid,
                                title=title,
                                action=ImportAction.SKIPPED,
                                reason=f"DOI already exists (key: {doi_to_key.get(doi, 'unknown')})",
                            )
                        )
                        continue

                # Map to Zotero schema (complete metadata!)
                try:
                    # Pass validated collection_key to mapper
                    collection_keys = [validated_collection_key] if validated_collection_key else None
                    zotero_item = map_pubmed_to_zotero(
                        article,
                        extra_tags=tags,
                        collection_keys=collection_keys,
                    )
                    items_to_save.append((pmid, title, zotero_item))
                except Exception as e:
                    logger.error(f"Failed to map article {pmid}: {e}")
                    result.add_item(
                        ImportedItem(
                            pmid=pmid,
                            title=title,
                            action=ImportAction.FAILED,
                            error=f"Mapping error: {e}",
                        )
                    )

            # 5. Batch save to Zotero
            if items_to_save:
                try:
                    # Extract just the items for saving
                    zotero_items = [item[2] for item in items_to_save]

                    await zotero_client.batch_save_items(
                        items=zotero_items,
                        uri="http://mcp-bridge.local/batch-import-from-pubmed",
                        title="PubMed Batch Import",
                    )

                    # Process save results
                    # Note: Zotero Connector API doesn't return individual keys easily
                    # So we mark all as added for now
                    for pmid, title, _ in items_to_save:
                        result.add_item(
                            ImportedItem(
                                pmid=pmid,
                                title=title,
                                action=ImportAction.ADDED,
                                zotero_key=None,  # Key not available from Connector API
                            )
                        )

                    logger.info(f"Saved {len(items_to_save)} items to Zotero")

                except Exception as e:
                    logger.error(f"Failed to save to Zotero: {e}")
                    # Mark all pending items as failed
                    for pmid, title, _ in items_to_save:
                        result.add_item(
                            ImportedItem(
                                pmid=pmid,
                                title=title,
                                action=ImportAction.FAILED,
                                error=f"Save error: {e}",
                            )
                        )

            # 6. Record collection info in result
            if validated_collection_key:
                result.collection_key = validated_collection_key
                logger.info(f"Items added to collection: {validated_collection_key}")

            # 7. Finalize result
            result.elapsed_time = time.time() - start_time

            final_result = result.to_dict()

            # 加入 collection_info 讓使用者確認
            if collection_info:
                final_result["collection_info"] = collection_info
                logger.info(f"Collection info: {collection_info}")

            return final_result

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
        pmids_input: Comma-separated PMIDs

    Returns:
        List of PMID strings
    """
    if not pmids_input:
        return []

    # Fail explicitly for unsupported shortcuts instead of silently returning [].
    if pmids_input.strip().lower() == "last":
        raise ValueError("'last' is not supported by batch_import_from_pubmed yet; provide comma-separated PMIDs instead")

    # Parse comma-separated PMIDs
    pmids = []
    for pmid in pmids_input.split(","):
        pmid = pmid.strip()
        if pmid and pmid.isdigit():
            pmids.append(pmid)
        elif pmid:
            logger.warning(f"Invalid PMID skipped: {pmid}")

    return pmids
