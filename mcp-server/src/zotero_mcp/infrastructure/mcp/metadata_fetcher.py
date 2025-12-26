"""
Metadata Fetcher - Auto-fetch article metadata from DOI/PMID

🔒 DATA INTEGRITY GUARANTEE:
   When DOI or PMID is provided, these functions fetch complete
   article metadata (including abstract) from external APIs.

Supports:
- PubMed API (via PMID) - includes iCite citation metrics (RCR)
- CrossRef API (via DOI)
"""

import logging
import re

logger = logging.getLogger(__name__)


async def fetch_metadata_from_pmid(
    pmid: str, include_citation_metrics: bool = True
) -> dict | None:
    """
    Fetch complete article metadata from PubMed using PMID.

    Returns Zotero-compatible item dict with all fields including abstract.
    Optionally includes citation metrics (RCR) from iCite.

    Args:
        pmid: PubMed ID
        include_citation_metrics: If True, fetch RCR/percentile from iCite (default: True)

    Returns:
        Zotero-compatible item dict, or None if fetch fails
    """
    try:
        from ..mappers.pubmed_mapper import pubmed_to_zotero_item
        from ..pubmed import fetch_pubmed_articles, enrich_articles_with_metrics

        articles = fetch_pubmed_articles([pmid])
        if articles:
            article = articles[0]

            # Enrich with citation metrics (RCR) if requested
            if include_citation_metrics:
                enrich_articles_with_metrics([article], [pmid])
                if article.get("relative_citation_ratio"):
                    logger.info(
                        f"✅ RCR {article['relative_citation_ratio']:.2f} for PMID {pmid}"
                    )

            zotero_item = pubmed_to_zotero_item(article)
            logger.info(f"Fetched complete metadata from PMID {pmid}")
            return zotero_item
    except Exception as e:
        logger.warning(f"Failed to fetch metadata from PMID {pmid}: {e}")
    return None


async def fetch_metadata_from_doi(doi: str) -> dict | None:
    """
    Fetch complete article metadata from CrossRef using DOI.

    Returns Zotero-compatible item dict with all fields including abstract.

    Args:
        doi: Digital Object Identifier

    Returns:
        Zotero-compatible item dict, or None if fetch fails
    """
    import httpx

    try:
        url = f"https://api.crossref.org/works/{doi}"
        async with httpx.AsyncClient(timeout=10) as client:
            response = await client.get(url)

        if response.status_code != 200:
            return None

        data = response.json().get("message", {})

        # Convert CrossRef format to Zotero format
        item = {
            "itemType": "journalArticle",
            "title": " ".join(data.get("title", [])),
            "DOI": doi,
        }

        # Abstract
        abstract = data.get("abstract", "")
        if abstract:
            # Remove HTML tags
            abstract = re.sub(r"<[^>]+>", "", abstract)
            item["abstractNote"] = abstract

        # Authors
        authors = data.get("author", [])
        if authors:
            item["creators"] = [
                {
                    "creatorType": "author",
                    "firstName": a.get("given", ""),
                    "lastName": a.get("family", ""),
                }
                for a in authors
            ]

        # Journal
        containers = data.get("container-title", [])
        if containers:
            item["publicationTitle"] = containers[0]

        # Date
        published = data.get("published", {}).get("date-parts", [[]])
        if published and published[0]:
            date_parts = published[0]
            if len(date_parts) >= 1:
                item["date"] = str(date_parts[0])  # Year
                if len(date_parts) >= 2:
                    item["date"] = f"{date_parts[0]}-{date_parts[1]:02d}"
                if len(date_parts) >= 3:
                    item["date"] = f"{date_parts[0]}-{date_parts[1]:02d}-{date_parts[2]:02d}"

        # Volume, Issue, Pages
        if data.get("volume"):
            item["volume"] = data["volume"]
        if data.get("issue"):
            item["issue"] = data["issue"]
        if data.get("page"):
            item["pages"] = data["page"]

        # URL
        if data.get("URL"):
            item["url"] = data["URL"]

        logger.info(f"Fetched complete metadata from DOI {doi}")
        return item

    except Exception as e:
        logger.warning(f"Failed to fetch metadata from DOI {doi}: {e}")
    return None


def merge_metadata(user_input: dict, fetched: dict) -> dict:
    """
    Merge user-provided data with fetched metadata.

    User-provided data takes priority, fetched data fills gaps.
    This ensures:
    1. User's explicit values are preserved
    2. Missing fields (especially abstract!) are filled from API

    Args:
        user_input: Data provided by user
        fetched: Data fetched from external API

    Returns:
        Merged dict with user data taking priority
    """
    result = fetched.copy()

    for key, value in user_input.items():
        if value is not None and value != "" and value != []:
            result[key] = value

    return result


async def auto_fetch_and_merge(
    user_input: dict,
    pmid: str | None = None,
    doi: str | None = None,
    auto_fetch: bool = True,
    include_citation_metrics: bool = True,
) -> tuple[dict, str]:
    """
    Auto-fetch metadata and merge with user input.

    Args:
        user_input: User-provided item data
        pmid: PubMed ID (optional)
        doi: DOI (optional)
        auto_fetch: Whether to fetch from external APIs
        include_citation_metrics: Whether to fetch RCR from iCite

    Returns:
        Tuple of (merged_item, metadata_source)
        metadata_source is one of: "user", "pmid", "doi", "merged (pmid)", "merged (doi)"
    """
    metadata_source = "user"
    fetched_metadata = None

    if auto_fetch:
        # Try PMID first (more reliable for academic articles)
        if pmid:
            fetched_metadata = await fetch_metadata_from_pmid(
                pmid, include_citation_metrics=include_citation_metrics
            )
            if fetched_metadata:
                metadata_source = "pmid"

        # If no PMID or fetch failed, try DOI
        if not fetched_metadata and doi:
            fetched_metadata = await fetch_metadata_from_doi(doi)
            if fetched_metadata:
                metadata_source = "doi"

    # Merge: user input takes priority, fetched fills gaps
    if fetched_metadata:
        item = merge_metadata(user_input, fetched_metadata)
        if metadata_source != "user":
            metadata_source = f"merged ({metadata_source})"
        logger.info(f"Merged metadata from {metadata_source}")
    else:
        item = user_input

    return item, metadata_source
