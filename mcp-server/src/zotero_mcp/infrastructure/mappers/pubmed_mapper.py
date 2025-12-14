"""
PubMed to Zotero Mapper

Maps SearchResult from pubmed-search library to Zotero item schema.
Ensures complete metadata preservation.
"""

from typing import Any, Optional
import logging

logger = logging.getLogger(__name__)


def map_pubmed_to_zotero(article: dict[str, Any], extra_tags: Optional[list[str]] = None) -> dict[str, Any]:
    """
    Map a PubMed article (from pubmed-search) to Zotero journalArticle schema.
    
    Args:
        article: Article dict from PubMedClient.fetch_details()
                 (SearchResult.to_dict() or raw dict)
        extra_tags: Additional tags to add (user-provided)
    
    Returns:
        Zotero item dict ready for save_items()
    
    Field Mapping:
        pubmed-search          -> Zotero
        ─────────────────────────────────────
        pmid                   -> extra (PMID: xxx)
        title                  -> title
        abstract               -> abstractNote (FULL!)
        authors_full           -> creators[]
        journal                -> publicationTitle
        journal_abbrev         -> journalAbbreviation
        year/month/day         -> date (YYYY-MM-DD)
        volume                 -> volume
        issue                  -> issue
        pages                  -> pages
        doi                    -> DOI
        pmc_id                 -> extra (PMCID: xxx)
        issn                   -> ISSN
        language               -> language
        keywords               -> tags[]
        mesh_terms             -> tags[] (prefix: MeSH:)
        publication_types      -> extra
    """
    
    # Basic fields
    item: dict[str, Any] = {
        "itemType": "journalArticle",
        "title": article.get("title", ""),
        "abstractNote": article.get("abstract", ""),  # 完整摘要！
    }
    
    # Creators (authors)
    creators = []
    authors_full = article.get("authors_full", [])
    
    if authors_full:
        for author in authors_full:
            creator = {
                "creatorType": "author",
            }
            # Handle different author formats
            if isinstance(author, dict):
                creator["firstName"] = author.get("fore_name", author.get("forename", ""))
                creator["lastName"] = author.get("last_name", author.get("lastname", ""))
            else:
                # Fallback for string format
                parts = str(author).rsplit(" ", 1)
                if len(parts) == 2:
                    creator["firstName"] = parts[0]
                    creator["lastName"] = parts[1]
                else:
                    creator["lastName"] = str(author)
                    creator["firstName"] = ""
            
            if creator.get("lastName"):  # Only add if has last name
                creators.append(creator)
    
    # Fallback to simple authors list if no authors_full
    if not creators and article.get("authors"):
        for author_name in article.get("authors", []):
            parts = str(author_name).rsplit(" ", 1)
            if len(parts) == 2:
                creators.append({
                    "creatorType": "author",
                    "firstName": parts[0],
                    "lastName": parts[1],
                })
            else:
                creators.append({
                    "creatorType": "author",
                    "lastName": author_name,
                    "firstName": "",
                })
    
    if creators:
        item["creators"] = creators
    
    # Journal info
    if article.get("journal"):
        item["publicationTitle"] = article["journal"]
    if article.get("journal_abbrev"):
        item["journalAbbreviation"] = article["journal_abbrev"]
    
    # Date - format as YYYY-MM-DD or YYYY-MM or YYYY
    date_parts = []
    year = article.get("year")
    month = article.get("month", "")
    day = article.get("day", "")
    
    if year:
        date_parts.append(str(year))
        if month:
            # Convert month name to number if needed
            month_num = _month_to_number(month)
            if month_num:
                date_parts.append(month_num)
                if day:
                    date_parts.append(str(day).zfill(2))
    
    if date_parts:
        item["date"] = "-".join(date_parts)
    
    # Volume, issue, pages
    if article.get("volume"):
        item["volume"] = article["volume"]
    if article.get("issue"):
        item["issue"] = article["issue"]
    if article.get("pages"):
        item["pages"] = article["pages"]
    
    # Identifiers
    if article.get("doi"):
        item["DOI"] = article["doi"]
    if article.get("issn"):
        item["ISSN"] = article["issn"]
    
    # Language
    if article.get("language"):
        item["language"] = article["language"]
    
    # Extra field - PMID, PMCID, publication types, affiliations
    extra_parts = []
    
    pmid = article.get("pmid")
    if pmid:
        extra_parts.append(f"PMID: {pmid}")
    
    pmc_id = article.get("pmc_id")
    if pmc_id:
        extra_parts.append(f"PMCID: {pmc_id}")
    
    pub_types = article.get("publication_types", [])
    if pub_types:
        extra_parts.append(f"Publication Type: {', '.join(pub_types)}")
    
    # Extract unique affiliations from authors
    affiliations = _extract_unique_affiliations(article.get("authors_full", []))
    if affiliations:
        extra_parts.append(f"Affiliations:\n" + "\n".join(f"  - {aff}" for aff in affiliations[:5]))
        if len(affiliations) > 5:
            extra_parts.append(f"  ... and {len(affiliations) - 5} more")
    
    if extra_parts:
        item["extra"] = "\n".join(extra_parts)
    
    # Tags - keywords + MeSH terms + user tags
    tags = []
    
    # Author keywords
    keywords = article.get("keywords", [])
    for kw in keywords:
        if kw and kw.strip():
            tags.append({"tag": kw.strip()})
    
    # MeSH terms with prefix
    mesh_terms = article.get("mesh_terms", [])
    for mesh in mesh_terms:
        if mesh and mesh.strip():
            tags.append({"tag": f"MeSH: {mesh.strip()}"})
    
    # User-provided extra tags
    if extra_tags:
        for tag in extra_tags:
            if tag and tag.strip():
                # Avoid duplicates
                tag_exists = any(t["tag"].lower() == tag.strip().lower() for t in tags)
                if not tag_exists:
                    tags.append({"tag": tag.strip()})
    
    if tags:
        item["tags"] = tags
    
    return item


def _month_to_number(month: str) -> Optional[str]:
    """Convert month name or abbreviation to two-digit number."""
    if not month:
        return None
    
    # Already a number
    if month.isdigit():
        return str(int(month)).zfill(2)
    
    month_map = {
        "jan": "01", "january": "01",
        "feb": "02", "february": "02",
        "mar": "03", "march": "03",
        "apr": "04", "april": "04",
        "may": "05",
        "jun": "06", "june": "06",
        "jul": "07", "july": "07",
        "aug": "08", "august": "08",
        "sep": "09", "september": "09",
        "oct": "10", "october": "10",
        "nov": "11", "november": "11",
        "dec": "12", "december": "12",
    }
    
    return month_map.get(month.lower().strip())


def _extract_unique_affiliations(authors_full: list[dict]) -> list[str]:
    """
    Extract unique affiliations from authors_full list.
    
    Returns deduplicated list of affiliations.
    """
    seen = set()
    affiliations = []
    
    for author in authors_full:
        if isinstance(author, dict) and "affiliations" in author:
            for aff in author["affiliations"]:
                if aff and aff not in seen:
                    seen.add(aff)
                    affiliations.append(aff)
    
    return affiliations


def map_pubmed_list_to_zotero(
    articles: list[dict[str, Any]],
    extra_tags: Optional[list[str]] = None,
) -> list[dict[str, Any]]:
    """
    Map a list of PubMed articles to Zotero items.
    
    Args:
        articles: List of article dicts from PubMedClient
        extra_tags: Tags to add to all items
    
    Returns:
        List of Zotero items
    """
    return [map_pubmed_to_zotero(article, extra_tags) for article in articles]


def extract_pmid_from_zotero_item(item: dict[str, Any]) -> Optional[str]:
    """
    Extract PMID from a Zotero item.
    
    Checks the 'extra' field for PMID: xxx pattern.
    """
    import re
    
    data = item.get("data", item)
    extra = data.get("extra", "")
    
    if not extra:
        return None
    
    match = re.search(r'PMID:\s*(\d+)', extra, re.IGNORECASE)
    if match:
        return match.group(1)
    
    return None


def extract_doi_from_zotero_item(item: dict[str, Any]) -> Optional[str]:
    """Extract DOI from a Zotero item."""
    data = item.get("data", item)
    return data.get("DOI") or data.get("doi")


# Alias for backward compatibility
pubmed_to_zotero_item = map_pubmed_to_zotero
