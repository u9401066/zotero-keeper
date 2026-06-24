"""
Data Mappers for Zotero Keeper

Provides mapping between different data formats and Zotero schema.
"""

from .pubmed_mapper import (
    extract_doi_from_zotero_item,
    extract_pmid_from_zotero_item,
    map_pubmed_list_to_zotero,
    map_pubmed_to_zotero,
)
from .zotero_schema import (
    CONTAINER_FIELD,
    ZOTERO_ITEM_FIELDS,
    ZOTERO_PRIMARY_CREATOR,
    detect_item_type,
    finalize_item_for_schema,
    is_known_item_type,
)

__all__ = [
    "map_pubmed_to_zotero",
    "map_pubmed_list_to_zotero",
    "extract_pmid_from_zotero_item",
    "extract_doi_from_zotero_item",
    "ZOTERO_ITEM_FIELDS",
    "CONTAINER_FIELD",
    "ZOTERO_PRIMARY_CREATOR",
    "detect_item_type",
    "finalize_item_for_schema",
    "is_known_item_type",
]
