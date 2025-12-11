"""Search References Use Case"""

from dataclasses import dataclass
from typing import Optional

from ...domain.repositories.reference_repository import ReferenceRepository


@dataclass
class SearchReferencesInput:
    """Input DTO for searching references"""
    query: str
    limit: int = 20


@dataclass
class SearchReferencesOutput:
    """Output DTO for search results"""
    count: int
    references: list[dict]


class SearchReferencesUseCase:
    """
    Use Case: Search references in Zotero library
    """
    
    def __init__(self, repository: ReferenceRepository):
        self._repository = repository
    
    async def execute(self, input_data: SearchReferencesInput) -> SearchReferencesOutput:
        """Execute the use case"""
        
        references = await self._repository.search(
            query=input_data.query,
            limit=input_data.limit,
        )
        
        serialized = [
            {
                "key": ref.key,
                "itemType": ref.item_type.value,
                "title": ref.title,
                "authors": ref.authors_string,
                "date": ref.date,
                "doi": ref.doi,
                "abstract": ref.abstract[:200] + "..." if ref.abstract and len(ref.abstract) > 200 else ref.abstract,
            }
            for ref in references
        ]
        
        return SearchReferencesOutput(
            count=len(serialized),
            references=serialized,
        )
