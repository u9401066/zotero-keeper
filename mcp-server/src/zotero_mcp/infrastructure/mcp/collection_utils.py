"""
Collection Utilities for Zotero

Provides:
- Collection selection formatting
- Number-to-key mapping for user choice
"""

import logging

logger = logging.getLogger(__name__)


def format_collection_options(collections: list[dict], suggestions: list[dict] | None = None) -> tuple[str, dict[str, int]]:
    """
    Format collections as numbered options for user selection.

    Returns a formatted string like:

    📁 Available Collections:
    ─────────────────────────
    ⭐ Suggested:
       1. AI Research (score: 85) - 12 items
       2. Machine Learning (score: 70) - 8 items

    📂 All Collections:
       3. Biology - 15 items
       4. Chemistry - 10 items
       ...

    0. Save to My Library (no collection)

    Args:
        collections: List of collection dicts with key, name, parentKey, itemCount
        suggestions: Optional list of suggested collections with scores

    Returns:
        Tuple of (formatted_string, key_to_num_mapping)
    """
    lines = ["", "📁 **Select a Collection:**", "─" * 30]

    option_num = 1
    key_to_num: dict[str, int] = {}

    # Add suggestions first if available
    if suggestions:
        lines.append("")
        lines.append("⭐ **Suggested (based on title/tags):**")
        for sug in suggestions[:3]:  # Top 3 suggestions
            key = sug.get("key", "")
            name = sug.get("name", "")
            score = sug.get("score", 0)
            reason = sug.get("reason", "")
            lines.append(f"   **{option_num}.** {name} (match: {score}%) - {reason}")
            key_to_num[key] = option_num
            option_num += 1

    # Add all collections (excluding already suggested)
    suggested_keys = {s.get("key") for s in (suggestions or [])}
    other_collections = [c for c in collections if c.get("key") not in suggested_keys]

    if other_collections:
        lines.append("")
        lines.append("📂 **All Collections:**")
        for col in other_collections[:15]:  # Limit to 15
            key = col.get("key", "")
            name = col.get("name", "")
            item_count = col.get("itemCount", 0)
            parent_key = col.get("parentKey")
            indent = "      " if parent_key else "   "
            lines.append(f"{indent}**{option_num}.** {name} ({item_count} items)")
            key_to_num[key] = option_num
            option_num += 1

        if len(other_collections) > 15:
            lines.append(f"   ... and {len(other_collections) - 15} more collections")

    # Always add "no collection" option
    lines.append("")
    lines.append("**0.** Save to My Library (no collection)")
    lines.append("")
    lines.append("─" * 30)

    return "\n".join(lines), key_to_num


def num_to_collection_key(num_str: str, key_to_num: dict[str, int]) -> str | None:
    """
    Convert user's number choice back to collection key.

    Args:
        num_str: User's input (e.g., "1", "2", "0")
        key_to_num: Mapping from collection key to number

    Returns:
        Collection key, or None if choice is 0 or invalid
    """
    try:
        choice_num = int(num_str.strip())
        if choice_num == 0:
            return None  # No collection

        # Reverse lookup
        for key, num in key_to_num.items():
            if num == choice_num:
                return key

        return None
    except ValueError:
        return None


async def get_formatted_collections(zotero_client, item: dict | None = None) -> tuple[list[dict], str, dict[str, int]]:
    """
    Get all collections formatted for selection.

    Args:
        zotero_client: Zotero client instance
        item: Optional item for getting suggestions

    Returns:
        Tuple of (all_collections, formatted_text, key_to_num_mapping)
    """
    from .smart_tools import _suggest_collections

    # Get all collections
    collections = await zotero_client.get_collections()
    all_collections = [
        {
            "key": c.get("key"),
            "name": c.get("data", {}).get("name", ""),
            "parentKey": c.get("data", {}).get("parentCollection"),
            "itemCount": c.get("data", {}).get("numItems", 0),
        }
        for c in collections
    ]

    # Get suggestions if item provided
    suggestions = None
    if item:
        suggestions = await _suggest_collections(item, zotero_client)

    # Format options
    options_text, key_to_num = format_collection_options(all_collections, suggestions)

    return all_collections, options_text, key_to_num
