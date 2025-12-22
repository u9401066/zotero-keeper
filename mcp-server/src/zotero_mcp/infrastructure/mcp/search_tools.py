"""
Search and Filter Tools for Zotero Keeper

Integrated search that combines PubMed search with Zotero library filtering.
When both pubmed-search-mcp and zotero-keeper are available, this provides
a unified search experience that excludes already-owned articles.
"""

import logging
import os
from typing import Any

from .search_helpers import (
    get_owned_identifiers,
    is_owned,
    format_search_results,
    format_zotero_item,
)

logger = logging.getLogger(__name__)

# Check if pubmed-search-mcp is available
try:
    from pubmed_search import PubMedClient

    PUBMED_AVAILABLE = True
except ImportError:
    PUBMED_AVAILABLE = False
    logger.info("pubmed-search-mcp not installed. Integrated search disabled.")


def register_search_tools(mcp, zotero_client):
    """Register integrated search tools."""

    @mcp.tool()
    async def advanced_search(
        q: str | None = None,
        item_type: str | None = None,
        tag: str | None = None,
        tags: list[str] | None = None,
        sort: str = "dateModified",
        direction: str = "desc",
        qmode: str = "titleCreatorYear",
        limit: int = 50,
        include_trashed: bool = False,
    ) -> dict[str, Any]:
        """
        🔍 Advanced search with multiple conditions in Zotero library

        使用多重條件搜尋 Zotero 書庫

        Args:
            q: Quick search query (title, creator, year)
            item_type: Filter by type (journalArticle, book, -attachment, etc.)
            tag: Single tag filter
            tags: Multiple tags (AND logic)
            sort: Sort field (dateModified, dateAdded, title, etc.)
            direction: Sort direction (desc, asc)
            qmode: Search mode (titleCreatorYear, everything)
            limit: Maximum results
            include_trashed: Include trash items

        Returns:
            Search results with formatted output
        """
        try:
            tag_param = tags if tags else tag

            items = await zotero_client.get_items(
                q=q,
                item_type=item_type,
                tag=tag_param,
                sort=sort,
                direction=direction,
                qmode=qmode,
                limit=limit,
                include_trashed=include_trashed,
            )

            # Format results
            formatted = "## 🔍 Advanced Search Results\n\n"
            formatted += f"Found **{len(items)}** items\n\n"

            params_used = []
            if q:
                params_used.append(f'q="{q}" (mode: {qmode})')
            if item_type:
                params_used.append(f"itemType={item_type}")
            if tag:
                params_used.append(f"tag={tag}")
            if tags:
                params_used.append(f"tags={tags} (AND)")
            params_used.append(f"sort={sort} {direction}")

            formatted += f"Parameters: {', '.join(params_used)}\n\n"

            for i, item in enumerate(items[:20], 1):
                formatted += format_zotero_item(item, i)

            if len(items) > 20:
                formatted += f"\n*... and {len(items) - 20} more items*\n"

            return {
                "count": len(items),
                "items": items,
                "search_params": {
                    "q": q,
                    "item_type": item_type,
                    "tag": tag,
                    "tags": tags,
                    "sort": sort,
                    "direction": direction,
                    "qmode": qmode,
                    "limit": limit,
                },
                "formatted": formatted,
            }

        except Exception as e:
            logger.error(f"Advanced search failed: {e}")
            return {
                "error": str(e),
                "hint": "Make sure Zotero is running",
            }

    logger.info("Advanced search tool registered")

    # ==================== PubMed Integration ====================

    if not PUBMED_AVAILABLE:
        logger.info("Skipping PubMed search tools")
        return

    @mcp.tool()
    async def search_pubmed_exclude_owned(
        query: str,
        limit: int = 10,
        min_year: int | None = None,
        max_year: int | None = None,
        date_from: str | None = None,
        date_to: str | None = None,
        article_type: str | None = None,
        strategy: str = "relevance",
        show_owned: bool = False,
        library_limit: int = 500,
    ) -> dict[str, Any]:
        """
        🔍📚 Search PubMed and filter out articles already in Zotero

        搜尋 PubMed 並排除已存在於 Zotero 的文獻

        ⭐ RECOMMENDED WORKFLOW:
        1. Use this tool to find NEW articles
        2. Review results with user
        3. ❗ ASK user which Collection to save to (use list_collections first)
        4. Use quick_import_pmids or batch_import_from_pubmed to import

        💡 TIP: Use get_session_pmids from pubmed-search-mcp to retrieve
        previously searched PMIDs instead of searching again!

        Args:
            query: PubMed search query (supports MeSH, Boolean)
            limit: Maximum NEW articles to return
            min_year/max_year: Publication year range
            date_from/date_to: Date range (YYYY/MM/DD)
            article_type: Filter (Review, Clinical Trial, etc.)
            strategy: Search strategy (relevance, recent, most_cited)
            show_owned: Show owned articles with 📚 marker
            library_limit: Zotero items to check

        Returns:
            New articles not in Zotero with PMIDs for easy import
            - new_pmids: Ready for import with quick_import_pmids
        """
        try:
            email = os.environ.get("NCBI_EMAIL", "zotero-keeper@example.com")
            api_key = os.environ.get("NCBI_API_KEY")
            pubmed = PubMedClient(email=email, api_key=api_key)

            search_limit = limit * 3
            results_raw = pubmed.search_raw(
                query=query,
                limit=search_limit,
                min_year=min_year,
                max_year=max_year,
                date_from=date_from,
                date_to=date_to,
                article_type=article_type,
                strategy=strategy,
            )

            if not results_raw:
                return {
                    "query": query,
                    "total_found": 0,
                    "new_count": 0,
                    "owned_count": 0,
                    "results": [],
                    "formatted": "No results found.",
                }

            owned = await get_owned_identifiers(zotero_client, limit=library_limit)

            new_results = []
            owned_results = []

            for article in results_raw:
                is_owned_flag, reason = is_owned(article, owned)
                article["_is_owned"] = is_owned_flag
                article["_owned_reason"] = reason

                if is_owned_flag:
                    owned_results.append(article)
                else:
                    new_results.append(article)
                    if len(new_results) >= limit and not show_owned:
                        break

            # Format output
            if show_owned:
                formatted = "## 🔍 PubMed Search Results\n"
                formatted += f"Query: `{query}`\n\n"
                formatted += f"Found: **{len(new_results)} new** 🆕 + **{len(owned_results)} owned** 📚\n\n"
                formatted += "### New Articles 🆕\n\n"
                formatted += format_search_results(new_results[:limit])
                if owned_results:
                    formatted += "\n### Already in Zotero 📚\n\n"
                    formatted += format_search_results(owned_results[:5])
            else:
                formatted = "## 🆕 New PubMed Articles\n"
                formatted += f"Query: `{query}`\n\n"
                formatted += f"Showing **{len(new_results[:limit])}** new "
                formatted += f"(filtered {len(owned_results)} owned)\n\n"
                formatted += format_search_results(new_results[:limit])

            response = {
                "query": query,
                "total_found": len(results_raw),
                "new_count": len(new_results),
                "owned_count": len(owned_results),
                "results": new_results[:limit],
                "formatted": formatted,
                "new_pmids": [
                    r.get("pmid") for r in new_results[:limit] if r.get("pmid")
                ],
            }

            if show_owned:
                response["owned_results"] = owned_results

            return response

        except Exception as e:
            logger.error(f"Integrated search failed: {e}")
            return {"query": query, "error": str(e)}

    @mcp.tool()
    async def check_articles_owned(
        pmids: list[str],
    ) -> dict[str, Any]:
        """
        📚 Check which PubMed articles are already in Zotero

        檢查哪些 PubMed 文獻已存在於 Zotero

        Args:
            pmids: List of PubMed IDs to check

        Returns:
            Lists of owned and new PMIDs
        """
        try:
            owned_ids = await get_owned_identifiers(zotero_client, limit=500)

            owned_pmids = []
            new_pmids = []
            details = {}

            if PUBMED_AVAILABLE:
                email = os.environ.get("NCBI_EMAIL", "zotero-keeper@example.com")
                pubmed = PubMedClient(email=email)
                articles = pubmed.fetch_details(pmids)

                for article in articles:
                    pmid = article.get("pmid", "")
                    is_owned_flag, reason = is_owned(article, owned_ids)

                    if is_owned_flag:
                        owned_pmids.append(pmid)
                        details[pmid] = {"owned": True, "reason": reason}
                    else:
                        new_pmids.append(pmid)
                        details[pmid] = {"owned": False}
            else:
                for pmid in pmids:
                    if pmid in owned_ids["pmids"]:
                        owned_pmids.append(pmid)
                        details[pmid] = {"owned": True, "reason": "PMID match"}
                    else:
                        new_pmids.append(pmid)
                        details[pmid] = {"owned": False}

            return {
                "total": len(pmids),
                "owned": owned_pmids,
                "owned_count": len(owned_pmids),
                "new": new_pmids,
                "new_count": len(new_pmids),
                "details": details,
                "message": f"{len(owned_pmids)} owned, {len(new_pmids)} new",
            }

        except Exception as e:
            logger.error(f"Check owned failed: {e}")
            return {"error": str(e)}

    logger.info("PubMed search tools registered")


def is_search_tools_available() -> bool:
    """Check if integrated search tools are available."""
    return PUBMED_AVAILABLE
