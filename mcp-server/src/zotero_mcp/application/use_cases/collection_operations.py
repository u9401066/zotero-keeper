"""Collection Use Cases"""

from dataclasses import dataclass
from typing import Optional

from ...domain.entities.collection import Collection
from ...domain.repositories.collection_repository import CollectionRepository


# --- List Collections ---

@dataclass
class ListCollectionsInput:
    """Input DTO for listing collections"""
    parent_key: Optional[str] = None


@dataclass
class ListCollectionsOutput:
    """Output DTO for listing collections"""
    count: int
    collections: list[dict]


class ListCollectionsUseCase:
    """Use Case: List collections"""
    
    def __init__(self, repository: CollectionRepository):
        self._repository = repository
    
    async def execute(self, input_data: ListCollectionsInput) -> ListCollectionsOutput:
        """Execute the use case"""
        
        collections = await self._repository.list_all(
            parent_key=input_data.parent_key
        )
        
        serialized = [
            {
                "key": c.key,
                "name": c.name,
                "parentKey": c.parent_key,
            }
            for c in collections
        ]
        
        return ListCollectionsOutput(
            count=len(serialized),
            collections=serialized,
        )


# --- Get Collection ---

@dataclass
class GetCollectionInput:
    """Input DTO for getting a collection"""
    key: str


@dataclass
class GetCollectionOutput:
    """Output DTO for getting a collection"""
    found: bool
    collection: Optional[dict] = None


class GetCollectionUseCase:
    """Use Case: Get collection by key"""
    
    def __init__(self, repository: CollectionRepository):
        self._repository = repository
    
    async def execute(self, input_data: GetCollectionInput) -> GetCollectionOutput:
        """Execute the use case"""
        
        collection = await self._repository.get_by_key(input_data.key)
        
        if collection is None:
            return GetCollectionOutput(found=False)
        
        return GetCollectionOutput(
            found=True,
            collection={
                "key": collection.key,
                "name": collection.name,
                "parentKey": collection.parent_key,
            }
        )


# --- Create Collection ---

@dataclass
class CreateCollectionInput:
    """Input DTO for creating a collection"""
    name: str
    parent_key: Optional[str] = None


@dataclass
class CreateCollectionOutput:
    """Output DTO for creating a collection"""
    success: bool
    key: Optional[str] = None


class CreateCollectionUseCase:
    """Use Case: Create a new collection"""
    
    def __init__(self, repository: CollectionRepository):
        self._repository = repository
    
    async def execute(self, input_data: CreateCollectionInput) -> CreateCollectionOutput:
        """Execute the use case"""
        
        collection = Collection(
            key="",  # Will be assigned by Zotero
            name=input_data.name,
            parent_key=input_data.parent_key,
        )
        
        key = await self._repository.create(collection)
        
        return CreateCollectionOutput(
            success=key is not None,
            key=key,
        )


# --- Add Reference to Collection ---

@dataclass
class AddToCollectionInput:
    """Input DTO for adding reference to collection"""
    collection_key: str
    reference_key: str


@dataclass
class AddToCollectionOutput:
    """Output DTO for add to collection result"""
    success: bool


class AddToCollectionUseCase:
    """Use Case: Add a reference to a collection"""
    
    def __init__(self, repository: CollectionRepository):
        self._repository = repository
    
    async def execute(self, input_data: AddToCollectionInput) -> AddToCollectionOutput:
        """Execute the use case"""
        
        success = await self._repository.add_item(
            collection_key=input_data.collection_key,
            item_key=input_data.reference_key,
        )
        
        return AddToCollectionOutput(success=success)
