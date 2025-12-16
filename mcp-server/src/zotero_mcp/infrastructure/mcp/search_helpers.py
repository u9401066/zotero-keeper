"""
Search Helper Functions

Provides:
- Title normalization
- Identifier extraction
- Owned item checking
- Result formatting
"""

import logging
import re
from typing import Any

from rapidfuzz import fuzz

logger = logging.getLogger(__name__)

# Matching configuration
TITLE_MATCH_THRESHOLD = 85


def normalize_title(title: str) -> str:
    """Normalize title for comparison."""
    if not title:
        return ""
    title = title.lower()
    title = re.sub(r"[^\w\s]", " ", title)
    title = re.sub(r"\s+", " ", title)
    return title.strip()


def extract_pmid_from_extra(extra: str) -> str | None:
    """Extract PMID from Zotero extra field."""
    if not extra:
        return None
    match = re.search(r"PMID:\s*(\d+)", extra, re.IGNORECASE)
    return match.group(1) if match else None


async def get_owned_identifiers(zotero_client, limit: int = 500) -> dict[str, set]:
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
            pmid = extract_pmid_from_extra(extra)
            if pmid:
                owned["pmids"].add(pmid)

            # Title (normalized)
            title = data.get("title", "")
            if title:
                owned["titles"].add(normalize_title(title))

        logger.info(
            f"Loaded {len(owned['dois'])} DOIs, "
            f"{len(owned['pmids'])} PMIDs, "
            f"{len(owned['titles'])} titles from Zotero"
        )

    except Exception as e:
        logger.error(f"Failed to load owned items: {e}")

    return owned


def is_owned(article: dict, owned: dict[str, set]) -> tuple[bool, str]:
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
        normalized = normalize_title(title)
        for owned_title in owned["titles"]:
            score = fuzz.token_sort_ratio(normalized, owned_title)
            if score >= TITLE_MATCH_THRESHOLD:
                return True, f"Title match ({score}%)"

    return False, ""


def format_search_results(results: list[dict], show_owned: bool = False) -> str:
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
            author_str = (
                f"{authors[0]} et al." if len(authors) > 3 else ", ".join(authors)
            )
        else:
            author_str = "Unknown"

        # Owned indicator
        owned_mark = ""
        if show_owned:
            is_owned_flag = r.get("_is_owned", False)
            owned_mark = " 📚" if is_owned_flag else " 🆕"

        output += f"**{i}. {title}**{owned_mark}\n"
        output += f"   - PMID: {pmid}\n"
        output += f"   - Authors: {author_str}\n"
        output += f"   - Journal: {journal} ({year})\n"
        if doi:
            output += f"   - DOI: {doi}\n"
        output += "\n"

    return output


def format_zotero_item(item: dict, index: int = 1) -> str:
    """Format a single Zotero item for display."""
    data = item.get("data", item)
    title = data.get("title", "Untitled")
    item_type = data.get("itemType", "")
    date = data.get("date", "")
    creators = data.get("creators", [])

    # Format creators
    if creators:
        first_creator = creators[0]
        author = first_creator.get("lastName", first_creator.get("name", "Unknown"))
        if len(creators) > 1:
            author += " et al."
    else:
        author = "Unknown"

    # Item type emoji
    type_emoji = {
        "journalArticle": "📄",
        "book": "📕",
        "bookSection": "📖",
        "conferencePaper": "🎤",
        "thesis": "🎓",
        "report": "📋",
        "webpage": "🌐",
        "note": "📝",
        "attachment": "📎",
    }.get(item_type, "📄")

    output = f"{index}. {type_emoji} **{title}**\n"
    output += f"   - Author: {author} ({date})\n"
    output += f"   - Type: {item_type}\n"
    output += f"   - Key: `{item.get('key', '')}`\n\n"

    return output
