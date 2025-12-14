"""
Zotero HTTP Client

Handles HTTP communication with Zotero's built-in Local API and Connector API.

Zotero 7 提供兩套 API:
1. Local API (/api/...) - 讀取功能，與 Web API 兼容
2. Connector API (/connector/...) - 瀏覽器連接器使用，可寫入

網路設定:
- Zotero 只綁定 127.0.0.1:23119
- 需要透過 Windows port proxy 從外部存取
- 請求需要 Host: 127.0.0.1:23119 header
"""

import json
import os
from dataclasses import dataclass, field
from typing import Any

import httpx


class ZoteroConnectionError(Exception):
    """Raised when connection to Zotero fails"""
    pass


class ZoteroAPIError(Exception):
    """Raised when Zotero API returns an error"""
    def __init__(self, message: str, status_code: int = 0, response_text: str = ""):
        super().__init__(message)
        self.status_code = status_code
        self.response_text = response_text


@dataclass
class ZoteroConfig:
    """Zotero connection configuration"""
    host: str = field(default_factory=lambda: os.getenv("ZOTERO_HOST", "localhost"))
    port: int = field(default_factory=lambda: int(os.getenv("ZOTERO_PORT", "23119")))
    timeout: float = field(default_factory=lambda: float(os.getenv("ZOTERO_TIMEOUT", "30")))

    @property
    def base_url(self) -> str:
        return f"http://{self.host}:{self.port}"

    @property
    def host_header(self) -> str:
        """Required header for port proxy"""
        return f"127.0.0.1:{self.port}"

    @property
    def needs_host_header(self) -> bool:
        """Check if we need Host header override (remote connection via port proxy)"""
        return self.host not in ("localhost", "127.0.0.1")


class ZoteroClient:
    """
    HTTP Client for Zotero Local API

    Uses Zotero 7's built-in Local API for read operations
    and Connector API for write operations.
    """

    def __init__(self, config: ZoteroConfig | None = None):
        self.config = config or ZoteroConfig()
        self._client: httpx.AsyncClient | None = None

    async def _get_client(self) -> httpx.AsyncClient:
        """Get or create HTTP client"""
        if self._client is None:
            headers = {"Content-Type": "application/json"}

            # Add Host header override for remote connections (port proxy)
            if self.config.needs_host_header:
                headers["Host"] = self.config.host_header

            self._client = httpx.AsyncClient(
                base_url=self.config.base_url,
                timeout=self.config.timeout,
                headers=headers,
            )
        return self._client

    async def close(self) -> None:
        """Close the HTTP client"""
        if self._client:
            await self._client.aclose()
            self._client = None

    async def _request(
        self,
        method: str,
        path: str,
        json_data: dict | None = None,
        params: dict | None = None,
    ) -> Any:
        """Make HTTP request to Zotero API"""
        client = await self._get_client()

        try:
            response = await client.request(
                method=method,
                url=path,
                json=json_data,
                params=params,
            )

            # Check for error responses
            if response.status_code >= 400:
                raise ZoteroAPIError(
                    f"Zotero API error: {response.status_code}",
                    status_code=response.status_code,
                    response_text=response.text,
                )

            # Parse JSON response
            if response.text:
                try:
                    return response.json()
                except json.JSONDecodeError:
                    return response.text
            return None

        except httpx.ConnectError as e:
            raise ZoteroConnectionError(
                f"無法連接到 Zotero ({self.config.base_url})。\n"
                f"請確認:\n"
                f"1. Zotero 正在運行\n"
                f"2. Windows 防火牆已開放 port {self.config.port}\n"
                f"3. Port proxy 已設定 (netsh interface portproxy)\n"
                f"Details: {e}"
            ) from e
        except httpx.TimeoutException as e:
            raise ZoteroConnectionError(
                f"連接 Zotero 超時 ({self.config.timeout}s)"
            ) from e

    # ==================== Health Check ====================

    async def ping(self) -> bool:
        """Check if Zotero is running"""
        try:
            result = await self._request("GET", "/connector/ping")
            return "Zotero is running" in str(result)
        except Exception:
            return False

    # ==================== Local API (Read) ====================
    # Uses /api/users/0/... endpoints

    async def get_items(
        self,
        limit: int = 50,
        start: int = 0,
        sort: str = "dateModified",
        direction: str = "desc",
        item_type: str | None = None,
        q: str | None = None,
        qmode: str = "titleCreatorYear",
        tag: str | list[str] | None = None,
        include_trashed: bool = False,
    ) -> list[dict[str, Any]]:
        """
        Get items from user library with advanced filtering

        Args:
            limit: Maximum number of items to return
            start: Offset for pagination
            sort: Sort field (dateModified, dateAdded, title, creator, itemType, date, etc.)
            direction: Sort direction (asc, desc)
            item_type: Filter by item type (journalArticle, book, etc.)
                       Supports negation with "-" prefix (e.g., "-attachment")
                       Supports OR with "||" (e.g., "book || bookSection")
            q: Quick search query
            qmode: Search mode (titleCreatorYear, everything)
            tag: Filter by tag(s). Can be:
                 - Single tag: "AI"
                 - Multiple tags (AND): ["AI", "Review"]
                 - Negation: "-exclude_tag"
                 - OR within tag: "AI || ML"
            include_trashed: Include items in trash (default: False)

        Returns:
            List of items matching the criteria
        """
        params: dict[str, Any] = {
            "limit": limit,
            "start": start,
            "sort": sort,
            "direction": direction,
        }
        if item_type:
            params["itemType"] = item_type
        if q:
            params["q"] = q
            params["qmode"] = qmode
        if tag:
            # Support both single tag and list of tags
            if isinstance(tag, list):
                # Multiple tags = AND logic (each tag is a separate param)
                # httpx will handle multiple same-name params
                for t in tag:
                    if "tag" not in params:
                        params["tag"] = t
                    else:
                        # For multiple tags, we need to use a list
                        if isinstance(params["tag"], list):
                            params["tag"].append(t)
                        else:
                            params["tag"] = [params["tag"], t]
            else:
                params["tag"] = tag
        if include_trashed:
            params["includeTrashed"] = "1"

        return await self._request("GET", "/api/users/0/items", params=params)

    async def get_item(self, item_key: str) -> dict[str, Any]:
        """Get a single item by key"""
        return await self._request("GET", f"/api/users/0/items/{item_key}")

    async def get_item_children(self, item_key: str) -> list[dict[str, Any]]:
        """Get child items (attachments, notes) of an item"""
        return await self._request("GET", f"/api/users/0/items/{item_key}/children")

    async def search_items(
        self,
        query: str,
        limit: int = 25,
    ) -> list[dict[str, Any]]:
        """Search for items by title, creator, year"""
        return await self.get_items(q=query, limit=limit)

    # ==================== Collections ====================

    async def get_collections(self) -> list[dict[str, Any]]:
        """Get all collections"""
        return await self._request("GET", "/api/users/0/collections")

    async def get_collection(self, collection_key: str) -> dict[str, Any]:
        """Get a single collection"""
        return await self._request("GET", f"/api/users/0/collections/{collection_key}")

    async def get_collection_items(
        self,
        collection_key: str,
        limit: int = 50,
    ) -> list[dict[str, Any]]:
        """Get items in a collection"""
        return await self._request(
            "GET",
            f"/api/users/0/collections/{collection_key}/items",
            params={"limit": limit},
        )

    async def find_collection_by_name(
        self,
        name: str,
        parent_key: str | None = None,
    ) -> dict[str, Any] | None:
        """
        Find a collection by name (case-insensitive).

        Args:
            name: Collection name to search for
            parent_key: Optional parent collection key to narrow search

        Returns:
            Collection dict if found, None otherwise
        """
        collections = await self.get_collections()
        name_lower = name.lower().strip()

        for col in collections:
            data = col.get("data", col)
            col_name = data.get("name", "").lower().strip()
            col_parent = data.get("parentCollection")

            # If name matches and (no parent_key specified OR parent matches)
            if col_name == name_lower and (parent_key is None or col_parent == parent_key):
                return col

        return None

    async def get_collection_tree(self) -> list[dict[str, Any]]:
        """
        Get collections organized as a tree structure.

        Returns:
            List of root collections, each with 'children' array
        """
        collections = await self.get_collections()

        # Build lookup dict
        col_by_key: dict[str, dict] = {}
        for col in collections:
            key = col.get("key")
            data = col.get("data", col)
            col_by_key[key] = {
                "key": key,
                "name": data.get("name", ""),
                "parentKey": data.get("parentCollection"),
                "itemCount": data.get("numItems", 0),
                "children": [],
            }

        # Build tree
        roots = []
        for _, col in col_by_key.items():
            parent_key = col["parentKey"]
            if parent_key and parent_key in col_by_key:
                col_by_key[parent_key]["children"].append(col)
            else:
                roots.append(col)

        return roots

    # ==================== Tags ====================

    async def get_tags(self) -> list[dict[str, Any]]:
        """Get all tags"""
        return await self._request("GET", "/api/users/0/tags")

    # ==================== Saved Searches (Local API Exclusive!) ====================
    # 🌟 This is a unique Local API feature - Web API cannot execute saved searches!

    async def get_searches(self) -> list[dict[str, Any]]:
        """
        Get all saved searches.

        Local API 獨有功能！

        Returns:
            List of saved search objects with keys and conditions
        """
        return await self._request("GET", "/api/users/0/searches")

    async def get_search(self, search_key: str) -> dict[str, Any]:
        """
        Get a specific saved search by key.

        Args:
            search_key: The search key (e.g., "ABC12345")

        Returns:
            Saved search object with name and conditions
        """
        return await self._request("GET", f"/api/users/0/searches/{search_key}")

    async def execute_search(self, search_key: str, limit: int = 100) -> list[dict[str, Any]]:
        """
        Execute a saved search and return matching items.

        🌟 這是 Local API 獨有的功能！Web API 只能讀取 search 的 metadata，
        無法實際執行搜尋並取得結果。這讓 AI 可以利用使用者預設的複雜搜尋條件。

        Args:
            search_key: The search key to execute
            limit: Maximum number of items to return (default: 100)

        Returns:
            List of items matching the saved search conditions
        """
        return await self._request(
            "GET",
            f"/api/users/0/searches/{search_key}/items",
            params={"limit": limit}
        )

    async def find_search_by_name(self, name: str) -> dict[str, Any] | None:
        """
        Find a saved search by name (case-insensitive).

        Args:
            name: Search name to look for

        Returns:
            Search dict if found, None otherwise
        """
        searches = await self.get_searches()
        name_lower = name.lower().strip()

        for search in searches:
            data = search.get("data", search)
            search_name = data.get("name", "").lower().strip()
            if search_name == name_lower:
                return search

        return None

    # ==================== Schema ====================

    async def get_item_types(self) -> list[dict[str, Any]]:
        """Get available item types"""
        return await self._request("GET", "/api/itemTypes")

    async def get_item_fields(self, item_type: str) -> list[dict[str, Any]]:
        """Get fields for a specific item type"""
        return await self._request(
            "GET",
            "/api/itemTypeFields",
            params={"itemType": item_type},
        )

    async def get_creator_types(self, item_type: str) -> list[dict[str, Any]]:
        """Get creator types for a specific item type"""
        return await self._request(
            "GET",
            "/api/itemTypeCreatorTypes",
            params={"itemType": item_type},
        )

    # ==================== Connector API (Write) ====================
    # Uses /connector/... endpoints for write operations

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
            creators: List of creators [{"firstName": "", "lastName": "", "creatorType": "author"}]
            **fields: Additional fields (date, DOI, url, abstract, etc.)

        Example:
            await client.create_item(
                item_type="journalArticle",
                title="My Paper",
                creators=[{"firstName": "John", "lastName": "Doe", "creatorType": "author"}],
                date="2024",
                DOI="10.1234/example",
                publicationTitle="Nature",
            )
        """
        item: dict[str, Any] = {
            "itemType": item_type,
            "title": title,
        }

        if creators:
            item["creators"] = creators

        # Add additional fields
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

        Note: This may require the item keys to be fetched first
              and use translation API.
        """
        # Use Local API with format parameter
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
        import re

        pmids = set(pmids or [])
        dois = {d.lower() for d in (dois or [])}

        existing_pmids: set[str] = set()
        existing_dois: set[str] = set()
        pmid_to_key: dict[str, str] = {}
        doi_to_key: dict[str, str] = {}

        # Get all items (paginated if needed)
        # For now, get a reasonable batch - adjust if library is huge
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
            # Safety limit
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
                if item_doi_lower in dois:
                    existing_dois.add(item_doi_lower)
                    doi_to_key[item_doi_lower] = key

            # Check PMID in extra field
            extra = data.get("extra", "")
            if extra:
                pmid_match = re.search(r'PMID:\s*(\d+)', extra, re.IGNORECASE)
                if pmid_match:
                    item_pmid = pmid_match.group(1)
                    if item_pmid in pmids:
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

        Wrapper around save_items with batch-specific settings.

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
