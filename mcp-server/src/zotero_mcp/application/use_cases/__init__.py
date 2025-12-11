"""Application Use Cases"""

from .add_reference import AddReferenceUseCase, AddReferenceInput
from .get_reference import GetReferenceUseCase, GetReferenceInput
from .list_references import ListReferencesUseCase, ListReferencesInput, ListReferencesOutput
from .search_references import SearchReferencesUseCase, SearchReferencesInput, SearchReferencesOutput
from .export_references import ExportReferencesUseCase, ExportReferencesInput, ExportReferencesOutput, ExportFormat
from .delete_reference import DeleteReferenceUseCase, DeleteReferenceInput, DeleteReferenceOutput
from .collection_operations import (
    ListCollectionsUseCase, ListCollectionsInput, ListCollectionsOutput,
    GetCollectionUseCase, GetCollectionInput, GetCollectionOutput,
    CreateCollectionUseCase, CreateCollectionInput, CreateCollectionOutput,
    AddToCollectionUseCase, AddToCollectionInput, AddToCollectionOutput,
)

__all__ = [
    # Reference Use Cases
    "AddReferenceUseCase",
    "AddReferenceInput",
    "GetReferenceUseCase",
    "GetReferenceInput",
    "ListReferencesUseCase",
    "ListReferencesInput",
    "ListReferencesOutput",
    "SearchReferencesUseCase",
    "SearchReferencesInput",
    "SearchReferencesOutput",
    "ExportReferencesUseCase",
    "ExportReferencesInput",
    "ExportReferencesOutput",
    "ExportFormat",
    "DeleteReferenceUseCase",
    "DeleteReferenceInput",
    "DeleteReferenceOutput",
    # Collection Use Cases
    "ListCollectionsUseCase",
    "ListCollectionsInput",
    "ListCollectionsOutput",
    "GetCollectionUseCase",
    "GetCollectionInput",
    "GetCollectionOutput",
    "CreateCollectionUseCase",
    "CreateCollectionInput",
    "CreateCollectionOutput",
    "AddToCollectionUseCase",
    "AddToCollectionInput",
    "AddToCollectionOutput",
]
