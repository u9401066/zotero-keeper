"""
Search and Filter Tools for Zotero Keeper

Integrated search that combines PubMed search with Zotero library filtering.
When both pubmed-search-mcp and zotero-keeper are available, this provides
a unified search experience that excludes already-owned articles.

Requirements:
- pubmed-search-mcp: For PubMed search functionality
- zotero-keeper: For Zotero library access

When to use:
- Use this integrated tool (search_pubmed_exclude_owned) when you want to
  find NEW articles that you don't already have in Zotero
- This replaces the basic `search_literature` from pubmed-search-mcp
- Advanced pubmed-search-mcp tools (generate_search_queries, parse_pico, etc.)
  still work normally and can be used to BUILD the query before searching
"""

import logging
import os
import re
from typing import Any

from rapidfuzz import fuzz

logger = logging.getLogger(__name__)

# Check if pubmed-search-mcp is available
try:
    from pubmed_search import PubMedClient
    PUBMED_AVAILABLE = True
except ImportError:
    PUBMED_AVAILABLE = False
    logger.info("pubmed-search-mcp not installed. Integrated search disabled.")


# Matching configuration
TITLE_MATCH_THRESHOLD = 85  # Fuzzy title matching threshold


def _normalize_title(title: str) -> str:
    """Normalize title for comparison."""
    if not title:
        return ""
    title = title.lower()
    title = re.sub(r'[^\w\s]', ' ', title)
    title = re.sub(r'\s+', ' ', title)
    return title.strip()


def _extract_pmid_from_extra(extra: str) -> str | None:
    """Extract PMID from Zotero extra field."""
    if not extra:
        return None
    match = re.search(r'PMID:\s*(\d+)', extra, re.IGNORECASE)
    return match.group(1) if match else None


async def _get_owned_identifiers(zotero_client, limit: int = 500) -> dict[str, set]:
    """
    Get identifiers of owned items in Zotero.

    Returns:
        {
            "dois": set of DOIs (lowercase),
            "pmids": set of PMIDs,
            "titles": set of normalized titles,
        }
    """
    owned = {
        "dois": set(),
        "pmids": set(),
        "titles": set(),
    }

    try:
        items = await zotero_client.get_items(limit=limit)

        for item in items:
            data = item.get("data", item)

            # DOI
            doi = data.get("DOI", "")
            if doi:
                owned["dois"].add(doi.lower().strip())

            # PMID from extra field
            extra = data.get("extra", "")
            pmid = _extract_pmid_from_extra(extra)
            if pmid:
                owned["pmids"].add(pmid)

            # Title (normalized)
            title = data.get("title", "")
            if title:
                owned["titles"].add(_normalize_title(title))

        logger.info(f"Loaded {len(owned['dois'])} DOIs, {len(owned['pmids'])} PMIDs, {len(owned['titles'])} titles from Zotero")

    except Exception as e:
        logger.error(f"Failed to load owned items: {e}")

    return owned


def _is_owned(article: dict, owned: dict[str, set]) -> tuple[bool, str]:
    """
    Check if an article is already owned.

    Returns:
        (is_owned: bool, reason: str)
    """
    # Check DOI
    doi = article.get("doi", "")
    if doi and doi.lower().strip() in owned["dois"]:
        return True, f"DOI match: {doi}"

    # Check PMID
    pmid = article.get("pmid", "")
    if pmid and pmid in owned["pmids"]:
        return True, f"PMID match: {pmid}"

    # Fuzzy title matching
    title = article.get("title", "")
    if title:
        normalized = _normalize_title(title)
        for owned_title in owned["titles"]:
            score = fuzz.token_sort_ratio(normalized, owned_title)
            if score >= TITLE_MATCH_THRESHOLD:
                return True, f"Title match ({score}%)"

    return False, ""


def _format_search_results(results: list[dict], show_owned: bool = False) -> str:
    """Format search results as markdown."""
    if not results:
        return "No results found."

    output = ""
    for i, r in enumerate(results, 1):
        pmid = r.get("pmid", "")
        title = r.get("title", "Unknown")
        authors = r.get("authors", [])
        journal = r.get("journal", r.get("journal_abbrev", ""))
        year = r.get("year", "")
        doi = r.get("doi", "")

        # Format authors
        if authors:
            author_str = f"{authors[0]} et al." if len(authors) > 3 else ", ".join(authors)
        else:
            author_str = "Unknown"

        # Owned indicator
        owned_mark = ""
        if show_owned:
            is_owned = r.get("_is_owned", False)
            owned_mark = " 📚" if is_owned else " 🆕"

        output += f"**{i}. {title}**{owned_mark}\n"
        output += f"   - PMID: {pmid}\n"
        output += f"   - Authors: {author_str}\n"
        output += f"   - Journal: {journal} ({year})\n"
        if doi:
            output += f"   - DOI: {doi}\n"
        output += "\n"

    return output


def register_search_tools(mcp, zotero_client):
    """
    Register integrated search tools.

    These tools combine pubmed-search-mcp's search with zotero-keeper's
    library filtering to provide a seamless experience.
    """

    if not PUBMED_AVAILABLE:
        logger.info("Skipping search_tools registration (pubmed-search-mcp not available)")
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

        This integrated tool combines pubmed-search-mcp's search with
        zotero-keeper's library to show only NEW articles you don't own.

        ⚠️ Requires: Both pubmed-search-mcp and zotero-keeper[pubmed] installed

        When to use this vs basic search:
        - Use this for discovery: "Find new papers about X that I don't have"
        - Use pubmed-search-mcp's search_literature for: exploratory search,
          building search strategies, when you want to see ALL results

        Advanced workflow:
        1. Use generate_search_queries() to get MeSH terms (pubmed-search-mcp)
        2. Use parse_pico() for clinical questions (pubmed-search-mcp)
        3. Use THIS tool for final search with the optimized query

        Args:
            query: PubMed search query (can be simple or complex with MeSH/Boolean)
            limit: Maximum NEW articles to return (default: 10)
            min_year: Minimum publication year
            max_year: Maximum publication year
            date_from: Start date (YYYY/MM/DD format)
            date_to: End date (YYYY/MM/DD format)
            article_type: Filter by type (Review, Clinical Trial, Meta-Analysis, etc.)
            strategy: Search strategy (relevance, recent, most_cited, impact)
            show_owned: If True, show owned articles marked with 📚 (default: False, only show 🆕 new)
            library_limit: How many Zotero items to check (default: 500)

        Returns:
            {
                "query": str,
                "total_found": int,
                "new_count": int,
                "owned_count": int,
                "results": list of new articles,
                "owned_results": list of owned articles (if show_owned),
                "formatted": markdown formatted results
            }

        Example:
            # Simple search
            search_pubmed_exclude_owned(query="CRISPR gene therapy", limit=10)

            # With MeSH terms (from generate_search_queries)
            search_pubmed_exclude_owned(
                query='"CRISPR-Cas Systems"[MeSH] AND "Genetic Therapy"[MeSH]',
                min_year=2023,
                article_type="Review"
            )

            # See what you already have
            search_pubmed_exclude_owned(query="CRISPR", show_owned=True)
        """
        try:
            # Initialize PubMed client
            email = os.environ.get("NCBI_EMAIL", "zotero-keeper@example.com")
            api_key = os.environ.get("NCBI_API_KEY")
            pubmed = PubMedClient(email=email, api_key=api_key)

            # Search PubMed with extra buffer for filtering
            search_limit = limit * 3  # Fetch more to account for owned items

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
                    "formatted": "No results found for this query.",
                }

            # Get owned items from Zotero
            owned = await _get_owned_identifiers(zotero_client, limit=library_limit)

            # Filter results
            new_results = []
            owned_results = []

            for article in results_raw:
                is_owned, reason = _is_owned(article, owned)
                article["_is_owned"] = is_owned
                article["_owned_reason"] = reason

                if is_owned:
                    owned_results.append(article)
                else:
                    new_results.append(article)

                    # Stop when we have enough new results
                    if len(new_results) >= limit and not show_owned:
                        break

            # Format output
            if show_owned:
                # Show all with markers
                new_results[:limit] + owned_results
                formatted = "## 🔍 PubMed Search Results\n"
                formatted += f"Query: `{query}`\n\n"
                formatted += f"Found: **{len(new_results)} new** 🆕 + **{len(owned_results)} owned** 📚\n\n"
                formatted += "### New Articles 🆕\n\n"
                formatted += _format_search_results(new_results[:limit], show_owned=False)
                if owned_results:
                    formatted += "\n### Already in Zotero 📚\n\n"
                    formatted += _format_search_results(owned_results[:5], show_owned=False)
            else:
                formatted = "## 🆕 New PubMed Articles (not in Zotero)\n"
                formatted += f"Query: `{query}`\n\n"
                formatted += f"Showing **{len(new_results[:limit])}** new articles "
                formatted += f"(filtered {len(owned_results)} already owned)\n\n"
                formatted += _format_search_results(new_results[:limit], show_owned=False)

            # Build response
            response = {
                "query": query,
                "total_found": len(results_raw),
                "new_count": len(new_results),
                "owned_count": len(owned_results),
                "results": new_results[:limit],
                "formatted": formatted,
            }

            if show_owned:
                response["owned_results"] = owned_results

            # Add PMIDs for easy import
            response["new_pmids"] = [r.get("pmid") for r in new_results[:limit] if r.get("pmid")]

            return response

        except Exception as e:
            logger.error(f"Integrated search failed: {e}")
            return {
                "query": query,
                "error": str(e),
                "hint": "Make sure both pubmed-search-mcp and zotero-keeper[pubmed] are installed",
            }

    @mcp.tool()
    async def check_articles_owned(
        pmids: list[str],
    ) -> dict[str, Any]:
        """
        📚 Check which PubMed articles are already in Zotero

        檢查哪些 PubMed 文獻已存在於 Zotero

        Useful after using pubmed-search-mcp's search_literature to
        check which results you already own before importing.

        Args:
            pmids: List of PubMed IDs to check

        Returns:
            {
                "owned": list of PMIDs already in Zotero,
                "new": list of PMIDs not in Zotero,
                "details": dict with match reasons
            }

        Example:
            # After search_literature returns PMIDs
            check_articles_owned(pmids=["12345678", "87654321", "11111111"])
        """
        try:
            # Get owned identifiers
            owned_ids = await _get_owned_identifiers(zotero_client, limit=500)

            # If pubmed is available, fetch details for title matching
            owned_pmids = []
            new_pmids = []
            details = {}

            if PUBMED_AVAILABLE:
                email = os.environ.get("NCBI_EMAIL", "zotero-keeper@example.com")
                pubmed = PubMedClient(email=email)
                articles = pubmed.fetch_details(pmids)

                for article in articles:
                    pmid = article.get("pmid", "")
                    is_owned, reason = _is_owned(article, owned_ids)

                    if is_owned:
                        owned_pmids.append(pmid)
                        details[pmid] = {"owned": True, "reason": reason}
                    else:
                        new_pmids.append(pmid)
                        details[pmid] = {"owned": False}
            else:
                # Fallback: just check PMIDs
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
                "message": f"Found {len(owned_pmids)} already owned, {len(new_pmids)} new",
            }

        except Exception as e:
            logger.error(f"Check owned failed: {e}")
            return {"error": str(e)}

    logger.info("Search tools registered (search_pubmed_exclude_owned, check_articles_owned)")


def is_search_tools_available() -> bool:
    """Check if integrated search tools are available."""
    return PUBMED_AVAILABLE
