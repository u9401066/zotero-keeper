"""
Smart Tools - Internal Helper Functions

智慧功能的內部 helper 函數（供 interactive_tools.py 使用）

NOTE: 原本的 6 個 tools 已整合進 interactive_tools.py（方案 A 精簡）
- check_duplicate → 整合進 interactive_save/quick_save
- validate_reference → 整合進 interactive_save/quick_save
- smart_add_reference → 被 quick_save 取代
- suggest_collections → 整合進 interactive_save
- smart_add_with_collection → 被 interactive_save 取代
- save_reference → 被 interactive_save/quick_save 取代

此模組只提供內部函數給 interactive_tools.py 使用：
- _suggest_collections()
- _find_duplicates()
"""

import logging
from typing import Any, Optional

from rapidfuzz import fuzz, process

logger = logging.getLogger(__name__)

# Matching thresholds
TITLE_MATCH_THRESHOLD = 85  # Fuzzy match score (0-100)
EXACT_MATCH_FIELDS = ["DOI", "ISBN", "PMID"]  # Exact match on these identifiers
COLLECTION_MATCH_THRESHOLD = 50  # Threshold for collection keyword matching


def _normalize_title(title: str) -> str:
    """Normalize title for comparison."""
    if not title:
        return ""
    import re
    title = title.lower()
    title = re.sub(r'[^\w\s]', ' ', title)
    title = re.sub(r'\s+', ' ', title)
    return title.strip()


def _extract_identifier(item: dict, field: str) -> Optional[str]:
    """Extract identifier from item, checking multiple locations."""
    if item.get(field):
        return str(item[field]).strip().lower()
    
    extra = item.get("extra", "")
    if extra and field in extra.upper():
        import re
        pattern = rf'{field}:\s*(\S+)'
        match = re.search(pattern, extra, re.IGNORECASE)
        if match:
            return match.group(1).strip().lower()
    
    return None


async def _suggest_collections(
    item: dict,
    zotero_client,
) -> list[dict]:
    """
    Suggest appropriate collections for an item based on title/keywords.
    
    Uses fuzzy matching to find relevant collections.
    
    Returns list of suggested collections with relevance scores.
    """
    suggestions = []
    
    title = item.get("title", "").lower()
    abstract = item.get("abstractNote", item.get("abstract", "")).lower()
    tags = [t.get("tag", t) if isinstance(t, dict) else str(t) for t in item.get("tags", [])]
    
    item_text = f"{title} {abstract} {' '.join(tags)}".lower()
    
    if not item_text.strip():
        return suggestions
    
    try:
        collections = await zotero_client.get_collections()
    except Exception:
        return suggestions
    
    for col in collections:
        data = col.get("data", col)
        col_name = data.get("name", "")
        col_key = col.get("key")
        
        if not col_name or not col_key:
            continue
        
        col_name_lower = col_name.lower()
        
        # Method 1: Direct keyword match in title
        if col_name_lower in title:
            suggestions.append({
                "key": col_key,
                "name": col_name,
                "score": 90,
                "reason": f"Collection name '{col_name}' found in title",
            })
            continue
        
        # Method 2: Fuzzy match collection name with title keywords
        title_words = [w for w in title.split() if len(w) > 3]
        for word in title_words:
            score = fuzz.partial_ratio(col_name_lower, word)
            if score >= COLLECTION_MATCH_THRESHOLD:
                suggestions.append({
                    "key": col_key,
                    "name": col_name,
                    "score": score,
                    "reason": f"Keyword '{word}' matches collection",
                })
                break
        
        # Method 3: Check tags match collection name
        for tag in tags:
            tag_lower = tag.lower()
            score = fuzz.ratio(col_name_lower, tag_lower)
            if score >= 70:
                suggestions.append({
                    "key": col_key,
                    "name": col_name,
                    "score": score,
                    "reason": f"Tag '{tag}' matches collection",
                })
                break
    
    # Sort by score descending and deduplicate
    seen_keys = set()
    unique_suggestions = []
    for s in sorted(suggestions, key=lambda x: x["score"], reverse=True):
        if s["key"] not in seen_keys:
            seen_keys.add(s["key"])
            unique_suggestions.append(s)
    
    return unique_suggestions[:5]


async def _find_duplicates(
    item: dict,
    zotero_client,
    limit: int = 100,
) -> list[dict]:
    """
    Find potential duplicates in Zotero library.
    
    Returns list of potential matches with similarity scores.
    """
    duplicates = []
    title = item.get("title", "")
    normalized_title = _normalize_title(title)
    
    if not normalized_title:
        return duplicates
    
    # Check exact identifier matches first
    for field in EXACT_MATCH_FIELDS:
        identifier = _extract_identifier(item, field)
        if identifier:
            results = await zotero_client.search_items(query=identifier, limit=10)
            for existing in results:
                existing_id = _extract_identifier(existing, field)
                if existing_id and existing_id == identifier:
                    duplicates.append({
                        "key": existing.get("key"),
                        "title": existing.get("data", {}).get("title", existing.get("title", "")),
                        "match_type": f"exact_{field}",
                        "score": 100,
                        "identifier": identifier,
                    })
    
    if duplicates:
        return duplicates
    
    # Fuzzy title matching
    existing_items = await zotero_client.get_items(limit=limit)
    
    existing_titles = []
    title_to_item = {}
    
    for existing in existing_items:
        data = existing.get("data", existing)
        existing_title = data.get("title", "")
        if existing_title:
            normalized = _normalize_title(existing_title)
            if normalized:
                existing_titles.append(normalized)
                title_to_item[normalized] = {
                    "key": existing.get("key"),
                    "title": existing_title,
                    "data": data,
                }
    
    if existing_titles:
        matches = process.extract(
            normalized_title,
            existing_titles,
            scorer=fuzz.token_sort_ratio,
            limit=5,
        )
        
        for match_title, score, _ in matches:
            if score >= TITLE_MATCH_THRESHOLD:
                matched_item = title_to_item.get(match_title, {})
                duplicates.append({
                    "key": matched_item.get("key"),
                    "title": matched_item.get("title"),
                    "match_type": "fuzzy_title",
                    "score": score,
                })
    
    return duplicates


def register_smart_tools(mcp, zotero_client):
    """
    Register smart tools (空函數，向後兼容).
    
    所有 tools 已移至 interactive_tools.py
    """
    logger.info("Smart tools module loaded (helpers only, no tools)")
