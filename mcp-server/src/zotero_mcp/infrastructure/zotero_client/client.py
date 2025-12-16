"""
Zotero HTTP Client

Handles HTTP communication with Zotero's built-in Local API and Connector API.

Zotero 7 提供兩套 API:
1. Local API (/api/...) - 讀取功能，與 Web API 兼容
2. Connector API (/connector/...) - 瀏覽器連接器使用，可寫入

This module composes the client from mixins:
- ZoteroClientBase: HTTP handling
- ZoteroReadMixin: Read operations (items, collections, tags, searches)
- ZoteroWriteMixin: Write operations (save, create, export, batch)
"""

from .client_base import (
    ZoteroConfig,
    ZoteroConnectionError,
    ZoteroAPIError,
    ZoteroClientBase,
)
from .client_read import ZoteroReadMixin
from .client_write import ZoteroWriteMixin


class ZoteroClient(ZoteroClientBase, ZoteroReadMixin, ZoteroWriteMixin):
    """
    HTTP Client for Zotero Local API

    Uses Zotero 7's built-in Local API for read operations
    and Connector API for write operations.

    Composed from:
    - ZoteroClientBase: HTTP communication and config
    - ZoteroReadMixin: Items, Collections, Tags, Searches, Schema
    - ZoteroWriteMixin: Save, Create, Export, Batch operations

    Example:
        config = ZoteroConfig(host="192.168.1.100")
        client = ZoteroClient(config)

        # Read
        items = await client.get_items(limit=10)
        collections = await client.get_collections()

        # Write
        await client.create_item(
            item_type="journalArticle",
            title="My Paper",
            DOI="10.1234/example"
        )

        await client.close()
    """

    pass


# Re-export for backwards compatibility
__all__ = [
    "ZoteroClient",
    "ZoteroConfig",
    "ZoteroConnectionError",
    "ZoteroAPIError",
]
