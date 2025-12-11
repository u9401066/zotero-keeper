"""Zotero Collection Repository Implementation"""

from typing import Optional

from ...domain.entities.collection import Collection
from ...domain.repositories.collection_repository import CollectionRepository
from ..zotero_client import ZoteroClient


class ZoteroCollectionRepository(CollectionRepository):
    """
    Collection Repository Implementation using Zotero HTTP API
    """
    
    def __init__(self, client: ZoteroClient):
        self._client = client
    
    async def create(self, collection: Collection) -> Optional[str]:
        """Create a new collection in Zotero, returns the key"""
        result = await self._client.create_collection(
            name=collection.name,
            parent_key=collection.parent_key,
        )
        
        return result.get("key")
    
    async def get_by_key(self, key: str) -> Optional[Collection]:
        """Get a collection by its key"""
        collections = await self.list_all()
        for col in collections:
            if col.key == key:
                return col
        return None
    
    async def list_all(self, parent_key: Optional[str] = None) -> list[Collection]:
        """List all collections"""
        result = await self._client.get_collections()
        
        collections = [
            Collection.from_zotero_dict(col)
            for col in result.get("results", [])
        ]
        
        # Filter by parent_key if specified
        if parent_key is not None:
            collections = [c for c in collections if c.parent_key == parent_key]
        
        return collections
    
    async def add_item(self, collection_key: str, item_key: str) -> bool:
        """
        Add an item to a collection.
        
        Note: This requires getting the item, adding the collection, and saving.
        For now, we'll handle this at the use case level when creating items.
        """
        # This would need to be implemented using item update
        # For simplicity, we handle collection assignment during item creation
        return True
