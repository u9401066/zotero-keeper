"""
Zotero HTTP Client

Handles HTTP communication with Zotero's built-in Local API and Connector API.

Zotero exposes Local API reads and a Connector compatibility write path.
Zotero 10+ additionally supports runtime-authorized Local API writes.

This module composes the client from mixins:
- ZoteroClientBase: HTTP handling
- ZoteroReadMixin: Read operations (items, collections, tags, searches)
- ZoteroLocalMixin: Authorized Zotero 10+ Local API writes
- ZoteroWriteMixin: Write operations (save, create, export, batch)
"""

from .client_base import (
    ZoteroConfig,
    ZoteroConnectionError,
    ZoteroAPIError,
    ZoteroClientBase,
)
from .client_local import ZoteroLocalMixin
from .client_read import ZoteroReadMixin
from .client_write import ZoteroWriteMixin


class ZoteroClient(ZoteroClientBase, ZoteroReadMixin, ZoteroLocalMixin, ZoteroWriteMixin):
    """
    HTTP Client for Zotero Local API

    Uses Zotero's built-in Local API for reads, preserves the Connector API
    compatibility path, and exposes explicitly prefixed Zotero 10+ Local API
    write methods.

    Composed from:
    - ZoteroClientBase: HTTP communication and config
    - ZoteroReadMixin: Items, Collections, Tags, Searches, Schema
    - ZoteroLocalMixin: Authorized Local API CRUD, full text, and file upload
    - ZoteroWriteMixin: Connector Save, Create, Export, Batch operations

    Example:
        # Keep Zotero's Local API on loopback. Never port-forward it.
        config = ZoteroConfig(host="localhost")
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
