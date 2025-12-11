"""Collection Repository Interface"""

from abc import ABC, abstractmethod
from typing import Optional

from ..entities.collection import Collection


class CollectionRepository(ABC):
    """
    Collection Repository Interface
    
    Defines the contract for collection data access.
    """
    
    @abstractmethod
    async def create(self, collection: Collection) -> Optional[str]:
        """
        Create a new collection.
        
        Args:
            collection: The collection to create
            
        Returns:
            The key of the created collection, or None on failure
        """
        pass
    
    @abstractmethod
    async def get_by_key(self, key: str) -> Optional[Collection]:
        """
        Get a collection by its key.
        
        Args:
            key: The unique key of the collection
            
        Returns:
            The collection if found, None otherwise
        """
        pass
    
    @abstractmethod
    async def list_all(self, parent_key: Optional[str] = None) -> list[Collection]:
        """
        List all collections in the library.
        
        Args:
            parent_key: Optional parent collection key to filter sub-collections
            
        Returns:
            List of collections
        """
        pass
    
    @abstractmethod
    async def add_item(self, collection_key: str, item_key: str) -> bool:
        """
        Add an item to a collection.
        
        Args:
            collection_key: The collection key
            item_key: The item key to add
            
        Returns:
            True if successful
        """
        pass
