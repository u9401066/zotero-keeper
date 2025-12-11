"""Delete Reference Use Case"""

from dataclasses import dataclass

from ...domain.repositories.reference_repository import ReferenceRepository


@dataclass
class DeleteReferenceInput:
    """Input DTO for deleting a reference"""
    key: str


@dataclass
class DeleteReferenceOutput:
    """Output DTO for delete result"""
    success: bool
    deleted_key: str


class DeleteReferenceUseCase:
    """
    Use Case: Delete a reference from Zotero library
    """
    
    def __init__(self, repository: ReferenceRepository):
        self._repository = repository
    
    async def execute(self, input_data: DeleteReferenceInput) -> DeleteReferenceOutput:
        """Execute the use case"""
        
        success = await self._repository.delete(input_data.key)
        
        return DeleteReferenceOutput(
            success=success,
            deleted_key=input_data.key,
        )
