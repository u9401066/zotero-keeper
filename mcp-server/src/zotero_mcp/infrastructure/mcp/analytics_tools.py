"""
Library Analytics Tools for Zotero Keeper

Provides insights and analysis tools for Zotero library:
- get_library_stats: Statistics (year/author/journal distribution)
- find_orphan_items: Items without collection or tags
"""

import logging
from collections import Counter
from typing import TYPE_CHECKING, Any

from mcp.server import MCPServer

if TYPE_CHECKING:
    from ..zotero_client.client import ZoteroClient

from ..zotero_client.client import ZoteroAPIError, ZoteroConnectionError
from .read_contracts import same_server_snapshot

logger = logging.getLogger(__name__)


def register_analytics_tools(mcp: MCPServer, zotero: "ZoteroClient") -> None:
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
            # Bounded scan: expose coverage rather than claiming a complete library.
            items, server_id = await zotero.get_items_snapshot(limit=5000)

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

                # Skip attachments, notes, and annotations
                if item_type in ("attachment", "note", "annotation"):
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

            # Missing supplemental reads are unknown, never a fabricated zero.
            warnings = []
            collection_count = None
            try:
                collections, collection_id = await zotero.get_collections_snapshot()
                same_server_snapshot(server_id, collection_id)
                collection_count = len(collections)
            except (ZoteroAPIError, ZoteroConnectionError) as exc:
                if isinstance(exc, ZoteroAPIError) and exc.status_code == 412:
                    raise
                warnings.append({"section": "collections", "error": str(exc)})

            # Get tag stats
            tag_count = None
            try:
                tags, _, tag_id = await zotero.get_tags_snapshot()
                same_server_snapshot(server_id, tag_id)
                tag_count = len(tags)
            except (ZoteroAPIError, ZoteroConnectionError) as exc:
                if isinstance(exc, ZoteroAPIError) and exc.status_code == 412:
                    raise
                warnings.append({"section": "tags", "error": str(exc)})

            total_items = sum(type_counter.values())

            return {
                "total_items": total_items,
                "server_id": server_id,
                "warnings": warnings,
                "scanned_count": len(items),
                "scan_limit": 5000,
                "possibly_truncated": len(items) == 5000,
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
        if type(limit) is not int or not 1 <= limit <= 1000:
            return {"error": "limit must be between 1 and 1000"}
        try:
            # Bounded scan; callers must inspect coverage metadata.
            items, server_id = await zotero.get_items_snapshot(limit=5000)

            no_collection = []
            no_tags = []
            completely_orphan = []
            total_no_collection = total_no_tags = total_completely_orphan = 0

            for item in items:
                data = item.get("data", item)
                item_type = data.get("itemType", "unknown")

                # Skip attachments, notes, and annotations
                if item_type in ("attachment", "note", "annotation"):
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
                    total_completely_orphan += 1
                    if len(completely_orphan) < limit:
                        completely_orphan.append(item_info)
                if not has_collection:
                    total_no_collection += 1
                    if include_no_collection and len(no_collection) < limit:
                        no_collection.append(item_info)
                if not has_tags:
                    total_no_tags += 1
                    if include_no_tags and len(no_tags) < limit:
                        no_tags.append(item_info)

            result: dict[str, Any] = {
                "server_id": server_id,
                "scanned_count": len(items),
                "scan_limit": 5000,
                "possibly_truncated": len(items) == 5000,
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
                    f"Found {total_completely_orphan} items with no collection AND no tags. Consider organizing these items first."
                )

            return result

        except (ZoteroConnectionError, ZoteroAPIError) as e:
            return {"error": str(e)}

    logger.info("Analytics tools registered (get_library_stats, find_orphan_items)")
