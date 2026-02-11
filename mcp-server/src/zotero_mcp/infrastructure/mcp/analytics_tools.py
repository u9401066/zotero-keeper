"""
Library Analytics Tools for Zotero Keeper

Provides insights and analysis tools for Zotero library:
- get_library_stats: Statistics (year/author/journal distribution)
- find_orphan_items: Items without collection or tags
"""

import logging
from collections import Counter
from typing import TYPE_CHECKING, Any

from mcp.server.fastmcp import FastMCP

if TYPE_CHECKING:
    from ..zotero_client.client import ZoteroClient

from ..zotero_client.client import ZoteroAPIError, ZoteroConnectionError

logger = logging.getLogger(__name__)


def register_analytics_tools(mcp: FastMCP, zotero: "ZoteroClient") -> None:
    """Register library analytics tools with the MCP server"""

    @mcp.tool()
    async def get_library_stats() -> dict[str, Any]:
        """
        📊 Get library statistics and insights

        取得文獻庫統計分析：年份、作者、期刊分布

        Returns:
            Statistics including:
            - total_items: Total number of items
            - by_type: Count by item type (journalArticle, book, etc.)
            - by_year: Distribution by publication year
            - top_authors: Most frequent authors
            - top_journals: Most frequent journals
            - tag_stats: Tag usage statistics
            - collection_stats: Collection statistics

        Example:
            get_library_stats()
            → {
                "total_items": 150,
                "by_type": {"journalArticle": 120, "book": 20, "thesis": 10},
                "by_year": {"2024": 30, "2023": 45, "2022": 25, ...},
                "top_authors": [["Smith J", 15], ["Lee K", 12], ...],
                "top_journals": [["Nature", 10], ["Science", 8], ...],
                ...
            }
        """
        try:
            # Fetch all items (limit high to get full library)
            items = await zotero.get_items(limit=5000)

            if not items:
                return {
                    "total_items": 0,
                    "message": "Library is empty",
                }

            # Initialize counters
            type_counter: Counter = Counter()
            year_counter: Counter = Counter()
            author_counter: Counter = Counter()
            journal_counter: Counter = Counter()
            items_without_collection = 0
            items_without_tags = 0

            for item in items:
                data = item.get("data", item)
                item_type = data.get("itemType", "unknown")

                # Skip attachments and notes
                if item_type in ("attachment", "note"):
                    continue

                type_counter[item_type] += 1

                # Year distribution
                date = data.get("date", "")
                if date:
                    # Extract year from various formats
                    year = date[:4] if len(date) >= 4 else "unknown"
                    if year.isdigit():
                        year_counter[year] += 1

                # Authors
                creators = data.get("creators", [])
                for creator in creators:
                    if creator.get("creatorType") == "author":
                        last_name = creator.get("lastName", "")
                        first_name = creator.get("firstName", "")
                        if last_name:
                            name = f"{last_name} {first_name[0]}" if first_name else last_name
                            author_counter[name] += 1

                # Journals
                journal = data.get("publicationTitle", "")
                if journal:
                    journal_counter[journal] += 1

                # Orphan tracking
                collections = data.get("collections", [])
                tags = data.get("tags", [])
                if not collections:
                    items_without_collection += 1
                if not tags:
                    items_without_tags += 1

            # Get collection stats
            try:
                collections = await zotero.get_collections()
                collection_count = len(collections)
            except Exception:
                collection_count = 0

            # Get tag stats
            try:
                tags = await zotero.get_tags()
                tag_count = len(tags)
            except Exception:
                tag_count = 0

            total_items = sum(type_counter.values())

            return {
                "total_items": total_items,
                "by_type": dict(type_counter.most_common()),
                "by_year": dict(year_counter.most_common(15)),  # Last 15 years
                "top_authors": author_counter.most_common(10),
                "top_journals": journal_counter.most_common(10),
                "collection_stats": {
                    "total_collections": collection_count,
                    "items_without_collection": items_without_collection,
                    "orphan_percentage": round(items_without_collection / total_items * 100, 1) if total_items else 0,
                },
                "tag_stats": {
                    "total_tags": tag_count,
                    "items_without_tags": items_without_tags,
                    "untagged_percentage": round(items_without_tags / total_items * 100, 1) if total_items else 0,
                },
            }

        except (ZoteroConnectionError, ZoteroAPIError) as e:
            return {"error": str(e)}

    @mcp.tool()
    async def find_orphan_items(
        limit: int = 50,
        include_no_collection: bool = True,
        include_no_tags: bool = True,
    ) -> dict[str, Any]:
        """
        🔍 Find orphan items (no collection or no tags)

        找出「孤兒」文獻：無 Collection 或無標籤的項目

        Helps you organize your library by identifying items that may need attention.

        Args:
            limit: Maximum items to return per category (default: 50)
            include_no_collection: Include items without any collection (default: True)
            include_no_tags: Include items without any tags (default: True)

        Returns:
            Lists of orphan items:
            - no_collection: Items not in any collection
            - no_tags: Items without any tags
            - completely_orphan: Items with neither collection nor tags

        Example:
            find_orphan_items()
            → {
                "no_collection": [{"key": "ABC123", "title": "Paper 1", ...}, ...],
                "no_tags": [...],
                "completely_orphan": [...],
                "summary": {"no_collection": 25, "no_tags": 40, "completely_orphan": 15}
            }
        """
        try:
            # Fetch all items
            items = await zotero.get_items(limit=5000)

            if not items:
                return {
                    "no_collection": [],
                    "no_tags": [],
                    "completely_orphan": [],
                    "summary": {"no_collection": 0, "no_tags": 0, "completely_orphan": 0},
                    "message": "Library is empty",
                }

            no_collection = []
            no_tags = []
            completely_orphan = []

            for item in items:
                data = item.get("data", item)
                item_type = data.get("itemType", "unknown")

                # Skip attachments and notes
                if item_type in ("attachment", "note"):
                    continue

                collections = data.get("collections", [])
                tags = data.get("tags", [])

                item_info = {
                    "key": item.get("key"),
                    "title": data.get("title", "Untitled")[:80],
                    "itemType": item_type,
                    "date": data.get("date", ""),
                    "dateAdded": data.get("dateAdded", "")[:10],  # Just date part
                }

                has_collection = bool(collections)
                has_tags = bool(tags)

                if not has_collection and not has_tags:
                    if len(completely_orphan) < limit:
                        completely_orphan.append(item_info)
                elif not has_collection and include_no_collection:
                    if len(no_collection) < limit:
                        no_collection.append(item_info)
                elif not has_tags and include_no_tags:
                    if len(no_tags) < limit:
                        no_tags.append(item_info)

            # Count totals (might be more than limit)
            total_no_collection = sum(
                1
                for item in items
                if item.get("data", item).get("itemType") not in ("attachment", "note") and not item.get("data", item).get("collections")
            )
            total_no_tags = sum(
                1
                for item in items
                if item.get("data", item).get("itemType") not in ("attachment", "note") and not item.get("data", item).get("tags")
            )
            total_completely_orphan = sum(
                1
                for item in items
                if item.get("data", item).get("itemType") not in ("attachment", "note")
                and not item.get("data", item).get("collections")
                and not item.get("data", item).get("tags")
            )

            result = {
                "summary": {
                    "no_collection": total_no_collection,
                    "no_tags": total_no_tags,
                    "completely_orphan": total_completely_orphan,
                },
            }

            if include_no_collection:
                result["no_collection"] = no_collection
            if include_no_tags:
                result["no_tags"] = no_tags
            result["completely_orphan"] = completely_orphan

            # Add suggestions
            if total_completely_orphan > 0:
                result["suggestion"] = (
                    f"Found {total_completely_orphan} items with no collection AND no tags. " "Consider organizing these items first."
                )

            return result

        except (ZoteroConnectionError, ZoteroAPIError) as e:
            return {"error": str(e)}

    logger.info("Analytics tools registered (get_library_stats, find_orphan_items)")
