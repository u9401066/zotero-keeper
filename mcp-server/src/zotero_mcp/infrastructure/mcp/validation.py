"""
Validation and Duplicate Detection for Zotero References

Provides:
- Item validation based on item type
- Duplicate detection with fuzzy matching
- Title normalization for comparison
"""

import logging
import re
from typing import Any

logger = logging.getLogger(__name__)


def normalize_title(title: str) -> str:
    """
    Normalize title for comparison.

    Removes punctuation, converts to lowercase, collapses whitespace.

    Args:
        title: Original title string

    Returns:
        Normalized title for comparison
    """
    if not title:
        return ""
    title = title.lower()
    title = re.sub(r"[^\w\s]", " ", title)
    title = re.sub(r"\s+", " ", title)
    return title.strip()


def get_required_fields(item_type: str) -> list[str]:
    """
    Get required fields for an item type.

    Args:
        item_type: Zotero item type

    Returns:
        List of required field names
    """
    match item_type:
        case "journalArticle" | "book":
            return ["title", "creators"]
        case "bookSection":
            return ["title", "creators", "bookTitle"]
        case "conferencePaper":
            return ["title", "creators"]
        case "thesis":
            return ["title", "creators", "university"]
        case "webpage":
            return ["title", "url"]
        case _:
            return ["title"]


def validate_item(item: dict) -> dict[str, Any]:
    """
    Validate a reference item.

    Checks required fields based on item type and provides warnings
    for recommended fields.

    Args:
        item: Zotero item dict

    Returns:
        {
            "valid": bool,
            "errors": list of error messages,
            "warnings": list of recommendations
        }
    """
    errors = []
    warnings = []

    item_type = item.get("itemType", "document")
    required_fields = get_required_fields(item_type)

    for field in required_fields:
        if field == "creators":
            creators = item.get("creators", [])
            if not creators:
                errors.append("Missing required: creators (at least one author)")
        else:
            if not item.get(field):
                errors.append(f"Missing required: {field}")

    # Warnings for journal articles
    if item_type == "journalArticle":
        if not item.get("publicationTitle"):
            warnings.append("Recommended: publicationTitle (journal name)")
        if not item.get("DOI"):
            warnings.append("Recommended: DOI")

    return {
        "valid": len(errors) == 0,
        "errors": errors,
        "warnings": warnings,
    }


async def find_duplicates(item: dict, zotero_client, threshold: float = 0.85) -> list[dict]:
    """
    Find potential duplicates for an item.

    Uses title similarity and exact identifier matching.

    Args:
        item: Item to check
        zotero_client: Zotero client instance
        threshold: Similarity threshold (0.0-1.0)

    Returns:
        List of potential duplicates with scores
    """
    try:
        from rapidfuzz import fuzz
    except ImportError:
        logger.warning("rapidfuzz not installed, skipping duplicate detection")
        return []

    duplicates = []
    title = item.get("title", "")
    doi = item.get("DOI", "")
    isbn = item.get("ISBN", "")

    if not title:
        return []

    normalized_title = normalize_title(title)

    try:
        # Search by title
        existing_items = await zotero_client.search_items(title[:50], limit=20)

        for existing in existing_items:
            data = existing.get("data", {})
            existing_title = data.get("title", "")

            if not existing_title:
                continue

            match_type = None
            score = 0

            # Check exact identifier match first
            if doi and data.get("DOI") == doi:
                match_type = "DOI"
                score = 100
            elif isbn and data.get("ISBN") == isbn:
                match_type = "ISBN"
                score = 100
            else:
                # Fuzzy title match
                existing_normalized = normalize_title(existing_title)
                score = fuzz.ratio(normalized_title, existing_normalized)

                if score >= threshold * 100:
                    match_type = "title"

            if match_type:
                duplicates.append(
                    {
                        "key": existing.get("key"),
                        "title": existing_title,
                        "score": score,
                        "match_type": match_type,
                    }
                )

        # Sort by score descending
        duplicates.sort(key=lambda x: x["score"], reverse=True)

    except Exception as e:
        logger.warning(f"Duplicate check failed: {e}")

    return duplicates
