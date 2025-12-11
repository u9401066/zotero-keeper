"""Zotero Reference Repository Implementation"""

from typing import Optional

from ...domain.entities.reference import Reference
from ...domain.repositories.reference_repository import ReferenceRepository
from ..zotero_client import ZoteroClient


class ZoteroReferenceRepository(ReferenceRepository):
    """
    Reference Repository Implementation using Zotero HTTP API
    
    Implements the ReferenceRepository interface by communicating
    with the local Zotero instance through the MCP Bridge plugin.
    """
    
    def __init__(self, client: ZoteroClient):
        self._client = client
    
    async def add(self, reference: Reference) -> Reference:
        """Add a new reference to Zotero"""
        data = reference.to_zotero_dict()
        result = await self._client.create_item(data)
        
        # Update reference with generated key
        reference.key = result.get("key")
        return reference
    
    async def get_by_key(self, key: str) -> Optional[Reference]:
        """Get a reference by its key"""
        try:
            data = await self._client.get_item(key)
            return Reference.from_zotero_dict(data)
        except Exception:
            return None
    
    async def delete(self, key: str) -> bool:
        """Delete a reference"""
        try:
            result = await self._client.delete_item(key)
            return result.get("success", False)
        except Exception:
            return False
    
    async def list_all(
        self,
        limit: int = 50,
        offset: int = 0,
        collection_key: Optional[str] = None,
    ) -> tuple[list[Reference], int]:
        """List references from Zotero"""
        result = await self._client.get_items(
            limit=limit,
            offset=offset,
            collection=collection_key,
        )
        
        references = [
            Reference.from_zotero_dict(item)
            for item in result.get("results", [])
        ]
        total = result.get("total", len(references))
        
        return references, total
    
    async def search(
        self,
        query: str,
        limit: int = 20,
    ) -> list[Reference]:
        """Search for references"""
        result = await self._client.search_items(query, limit)
        
        return [
            Reference.from_zotero_dict(item)
            for item in result.get("results", [])
        ]
    
    async def export(
        self,
        keys: list[str],
        format_type: str = "bibtex",
    ) -> str:
        """Export references in bibliographic format"""
        result = await self._client.export_items(keys, format_type)
        return result.get("data", "")
