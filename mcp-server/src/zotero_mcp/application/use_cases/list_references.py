"""List References Use Case"""

from dataclasses import dataclass
from typing import Optional

from ...domain.repositories.reference_repository import ReferenceRepository


@dataclass
class ListReferencesInput:
    """Input DTO for listing references"""
    limit: int = 20
    offset: int = 0
    collection: Optional[str] = None


@dataclass
class ListReferencesOutput:
    """Output DTO for listing references"""
    total: int
    count: int
    references: list[dict]


class ListReferencesUseCase:
    """
    Use Case: List references from Zotero library
    """
    
    def __init__(self, repository: ReferenceRepository):
        self._repository = repository
    
    async def execute(self, input_data: ListReferencesInput) -> ListReferencesOutput:
        """Execute the use case"""
        
        references, total = await self._repository.list_all(
            limit=input_data.limit,
            offset=input_data.offset,
            collection_key=input_data.collection,
        )
        
        serialized = [
            {
                "key": ref.key,
                "itemType": ref.item_type.value,
                "title": ref.title,
                "authors": ref.authors_string,
                "date": ref.date,
                "doi": ref.doi,
            }
            for ref in references
        ]
        
        return ListReferencesOutput(
            total=total,
            count=len(serialized),
            references=serialized,
        )
