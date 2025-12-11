"""Get Reference Use Case"""

from dataclasses import dataclass
from typing import Optional

from ...domain.entities.reference import Reference
from ...domain.repositories.reference_repository import ReferenceRepository


@dataclass
class GetReferenceOutput:
    """Output DTO for getting a reference"""
    found: bool
    reference: Optional[dict]
    message: str


class GetReferenceUseCase:
    """
    Use Case: Get a reference by its key
    """
    
    def __init__(self, repository: ReferenceRepository):
        self._repository = repository
    
    async def execute(self, key: str) -> GetReferenceOutput:
        """Execute the use case"""
        
        reference = await self._repository.get_by_key(key)
        
        if reference is None:
            return GetReferenceOutput(
                found=False,
                reference=None,
                message=f"找不到 key 為「{key}」的文獻",
            )
        
        return GetReferenceOutput(
            found=True,
            reference=self._serialize_reference(reference),
            message="成功取得文獻資訊",
        )
    
    def _serialize_reference(self, ref: Reference) -> dict:
        """Serialize reference for output"""
        return {
            "key": ref.key,
            "itemType": ref.item_type.value,
            "title": ref.title,
            "authors": ref.authors_string,
            "date": ref.date,
            "doi": ref.doi,
            "url": ref.url,
            "abstract": ref.abstract,
            "publicationTitle": ref.publication_title,
            "volume": ref.volume,
            "issue": ref.issue,
            "pages": ref.pages,
            "tags": ref.tags,
            "collections": ref.collections,
        }
