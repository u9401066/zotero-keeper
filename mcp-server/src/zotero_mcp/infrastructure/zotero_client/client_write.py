"""
Zotero Client - Write Operations Mixin

Provides write operations using Connector API:
- Save items
- Create items
- Export
- Batch operations
"""

import json
import re
from typing import Any


class ZoteroWriteMixin:
    """Mixin providing write operations for ZoteroClient"""

    # ==================== Connector API (Write) ====================

    async def save_items(
        self,
        items: list[dict[str, Any]],
        uri: str = "http://mcp-bridge.local",
        title: str = "MCP Bridge Import",
    ) -> dict[str, Any]:
        """
        Save items using Connector API

        This is the main method for WRITING to Zotero.
        Uses the same API that browser connectors use.

        Args:
            items: List of items in Zotero API format
            uri: Source URI (for tracking)
            title: Page title (for tracking)

        Returns:
            Response from Zotero including saved item keys
        """
        payload = {
            "items": items,
            "uri": uri,
            "title": title,
        }
        return await self._request("POST", "/connector/saveItems", json_data=payload)

    async def create_item(
        self,
        item_type: str,
        title: str,
        creators: list[dict[str, str]] | None = None,
        **fields,
    ) -> dict[str, Any]:
        """
        Create a single item

        Convenience method that wraps save_items().

        Args:
            item_type: Type of item (journalArticle, book, etc.)
            title: Item title
            creators: List of creators
            **fields: Additional fields (date, DOI, url, abstract, etc.)

        Example:
            await client.create_item(
                item_type="journalArticle",
                title="My Paper",
                creators=[{"firstName": "John", "lastName": "Doe", "creatorType": "author"}],
                date="2024",
                DOI="10.1234/example",
            )
        """
        item: dict[str, Any] = {
            "itemType": item_type,
            "title": title,
        }

        if creators:
            item["creators"] = creators

        for key, value in fields.items():
            if value is not None:
                item[key] = value

        return await self.save_items([item])

    # ==================== Export ====================

    async def export_items(
        self,
        item_keys: list[str],
        format: str = "bibtex",
    ) -> str:
        """
        Export items in bibliographic format

        Args:
            item_keys: List of item keys to export
            format: Export format (bibtex, ris, csljson, etc.)
        """
        params = {
            "itemKey": ",".join(item_keys),
            "format": format,
        }
        result = await self._request("GET", "/api/users/0/items", params=params)
        return result if isinstance(result, str) else json.dumps(result)

    # ==================== Batch Operations ====================

    async def batch_check_identifiers(
        self,
        pmids: list[str] | None = None,
        dois: list[str] | None = None,
    ) -> dict[str, set[str]]:
        """
        Check which PMIDs and DOIs already exist in Zotero.

        Efficiently checks for duplicates by scanning the library once.

        Args:
            pmids: List of PMIDs to check
            dois: List of DOIs to check

        Returns:
            {
                "existing_pmids": set of PMIDs that exist,
                "existing_dois": set of DOIs that exist,
                "pmid_to_key": dict mapping PMID to Zotero item key,
                "doi_to_key": dict mapping DOI to Zotero item key,
            }
        """
        pmids_set = set(pmids or [])
        dois_set = {d.lower() for d in (dois or [])}

        existing_pmids: set[str] = set()
        existing_dois: set[str] = set()
        pmid_to_key: dict[str, str] = {}
        doi_to_key: dict[str, str] = {}

        # Get all items (paginated)
        all_items: list[dict] = []
        start = 0
        batch_size = 100

        while True:
            items = await self.get_items(limit=batch_size, start=start)
            if not items:
                break
            all_items.extend(items)
            if len(items) < batch_size:
                break
            start += batch_size
            if start > 5000:
                break

        # Scan items for PMIDs and DOIs
        for item in all_items:
            data = item.get("data", item)
            key = item.get("key", "")

            # Check DOI
            item_doi = data.get("DOI", "")
            if item_doi:
                item_doi_lower = item_doi.lower()
                if item_doi_lower in dois_set:
                    existing_dois.add(item_doi_lower)
                    doi_to_key[item_doi_lower] = key

            # Check PMID in extra field
            extra = data.get("extra", "")
            if extra:
                pmid_match = re.search(r"PMID:\s*(\d+)", extra, re.IGNORECASE)
                if pmid_match:
                    item_pmid = pmid_match.group(1)
                    if item_pmid in pmids_set:
                        existing_pmids.add(item_pmid)
                        pmid_to_key[item_pmid] = key

        return {
            "existing_pmids": existing_pmids,
            "existing_dois": existing_dois,
            "pmid_to_key": pmid_to_key,
            "doi_to_key": doi_to_key,
        }

    async def batch_save_items(
        self,
        items: list[dict[str, Any]],
        uri: str = "http://mcp-bridge.local/batch-import",
        title: str = "MCP Batch Import",
    ) -> dict[str, Any]:
        """
        Save multiple items in a single request.

        Args:
            items: List of items in Zotero API format
            uri: Source URI for tracking
            title: Source title for tracking

        Returns:
            Response from Zotero API
        """
        if not items:
            return {"success": True, "items": []}

        return await self.save_items(items, uri=uri, title=title)
