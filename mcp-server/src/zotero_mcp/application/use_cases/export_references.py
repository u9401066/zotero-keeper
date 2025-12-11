"""Export References Use Case"""

from dataclasses import dataclass
from enum import Enum


from ...domain.repositories.reference_repository import ReferenceRepository


class ExportFormat(str, Enum):
    """Supported export formats"""
    BIBTEX = "bibtex"
    RIS = "ris"
    CSL_JSON = "csljson"
    BIBLIOGRAPHY = "bibliography"


@dataclass
class ExportReferencesInput:
    """Input DTO for exporting references"""
    keys: list[str]
    format: ExportFormat = ExportFormat.BIBTEX


@dataclass
class ExportReferencesOutput:
    """Output DTO for export results"""
    format: str
    content: str
    count: int


class ExportReferencesUseCase:
    """
    Use Case: Export references in various citation formats
    """
    
    def __init__(self, repository: ReferenceRepository):
        self._repository = repository
    
    async def execute(self, input_data: ExportReferencesInput) -> ExportReferencesOutput:
        """Execute the use case"""
        
        content = await self._repository.export(
            keys=input_data.keys,
            format_type=input_data.format.value,
        )
        
        return ExportReferencesOutput(
            format=input_data.format.value,
            content=content,
            count=len(input_data.keys),
        )
