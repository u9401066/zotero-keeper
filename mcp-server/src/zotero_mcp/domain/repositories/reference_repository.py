"""Reference Repository Interface"""

from abc import ABC, abstractmethod
from typing import Optional

from ..entities.reference import Reference


class ReferenceRepository(ABC):
    """
    Reference Repository Interface
    
    Defines the contract for reference data access.
    Implementation will be in the infrastructure layer.
    """
    
    @abstractmethod
    async def add(self, reference: Reference) -> Reference:
        """
        Add a new reference to the library.
        
        Args:
            reference: The reference to add
            
        Returns:
            The added reference with generated key
        """
        pass
    
    @abstractmethod
    async def get_by_key(self, key: str) -> Optional[Reference]:
        """
        Get a reference by its key.
        
        Args:
            key: The unique key of the reference
            
        Returns:
            The reference if found, None otherwise
        """
        pass
    
    @abstractmethod
    async def delete(self, key: str) -> bool:
        """
        Delete a reference by its key.
        
        Args:
            key: The unique key of the reference
            
        Returns:
            True if deleted, False if not found
        """
        pass
    
    @abstractmethod
    async def list_all(
        self,
        limit: int = 50,
        offset: int = 0,
        collection_key: Optional[str] = None,
    ) -> tuple[list[Reference], int]:
        """
        List references in the library.
        
        Args:
            limit: Maximum number of references to return
            offset: Number of references to skip
            collection_key: Filter by collection (optional)
            
        Returns:
            Tuple of (list of references, total count)
        """
        pass
    
    @abstractmethod
    async def search(
        self,
        query: str,
        limit: int = 20,
    ) -> list[Reference]:
        """
        Search references by query string.
        
        Args:
            query: Search query (searches title, authors, abstract, etc.)
            limit: Maximum number of results
            
        Returns:
            List of matching references
        """
        pass
    
    @abstractmethod
    async def export(
        self,
        keys: list[str],
        format_type: str = "bibtex",
    ) -> str:
        """
        Export references in a bibliographic format.
        
        Args:
            keys: List of reference keys to export
            format_type: Export format (bibtex, ris, etc.)
            
        Returns:
            Exported data as string
        """
        pass
