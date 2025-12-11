"""Add Reference Use Case"""

from dataclasses import dataclass
from typing import Optional

from ...domain.entities.reference import Reference, Creator, ItemType
from ...domain.repositories.reference_repository import ReferenceRepository


@dataclass
class AddReferenceInput:
    """Input DTO for adding a reference"""
    title: str
    item_type: ItemType = ItemType.JOURNAL_ARTICLE
    authors: Optional[list[str]] = None
    date: Optional[str] = None
    doi: Optional[str] = None
    url: Optional[str] = None
    abstract: Optional[str] = None
    journal: Optional[str] = None  # publication_title for journals
    volume: Optional[str] = None
    issue: Optional[str] = None
    pages: Optional[str] = None
    publisher: Optional[str] = None
    isbn: Optional[str] = None
    tags: Optional[list[str]] = None
    collection_key: Optional[str] = None


@dataclass
class AddReferenceOutput:
    """Output DTO for adding a reference"""
    success: bool
    key: Optional[str]
    title: str
    message: str


class AddReferenceUseCase:
    """
    Use Case: Add a new reference to Zotero library
    
    This use case handles the business logic for adding a new
    bibliographic reference to the user's Zotero library.
    """
    
    def __init__(self, repository: ReferenceRepository):
        self._repository = repository
    
    async def execute(self, input_data: AddReferenceInput) -> AddReferenceOutput:
        """Execute the use case"""
        
        # Parse authors
        creators = []
        if input_data.authors:
            for author_name in input_data.authors:
                creators.append(Creator.from_full_name(author_name))
        
        # Create reference entity
        reference = Reference(
            title=input_data.title,
            item_type=input_data.item_type,
            creators=creators,
            date=input_data.date,
            doi=input_data.doi,
            url=input_data.url,
            abstract=input_data.abstract,
            publication_title=input_data.journal,
            volume=input_data.volume,
            issue=input_data.issue,
            pages=input_data.pages,
            publisher=input_data.publisher,
            isbn=input_data.isbn,
            tags=input_data.tags or [],
            collections=[input_data.collection_key] if input_data.collection_key else [],
        )
        
        # Add to repository
        try:
            saved_reference = await self._repository.add(reference)
            return AddReferenceOutput(
                success=True,
                key=saved_reference.key,
                title=saved_reference.title,
                message=f"Reference '{saved_reference.title}' added successfully",
            )
        except Exception as e:
            return AddReferenceOutput(
                success=False,
                key=None,
                title=input_data.title,
                message=f"Failed to add reference: {str(e)}",
            )
