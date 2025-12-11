"""
Zotero MCP Server - FastMCP Implementation

This is the main entry point for the MCP server.
It exposes Zotero operations as MCP tools.
"""

from typing import Optional
from fastmcp import FastMCP

from ..infrastructure.zotero_client.client import ZoteroClient
from ..infrastructure.repositories.zotero_reference_repository import ZoteroReferenceRepository
from ..infrastructure.repositories.zotero_collection_repository import ZoteroCollectionRepository
from ..application.use_cases import (
    AddReferenceUseCase, AddReferenceInput,
    GetReferenceUseCase, GetReferenceInput,
    ListReferencesUseCase, ListReferencesInput,
    SearchReferencesUseCase, SearchReferencesInput,
    ExportReferencesUseCase, ExportReferencesInput, ExportFormat,
    DeleteReferenceUseCase, DeleteReferenceInput,
    ListCollectionsUseCase, ListCollectionsInput,
    GetCollectionUseCase, GetCollectionInput,
    CreateCollectionUseCase, CreateCollectionInput,
    AddToCollectionUseCase, AddToCollectionInput,
)
from ..domain.entities.reference import ItemType


# Create FastMCP server instance
mcp = FastMCP(
    "zotero-mcp",
    description="MCP server for interacting with local Zotero library via plugin bridge",
)

# Default configuration
DEFAULT_ZOTERO_URL = "http://localhost:23120"


def _get_dependencies(zotero_url: Optional[str] = None):
    """Create dependencies for use cases"""
    url = zotero_url or DEFAULT_ZOTERO_URL
    client = ZoteroClient(base_url=url)
    ref_repo = ZoteroReferenceRepository(client)
    col_repo = ZoteroCollectionRepository(client)
    return client, ref_repo, col_repo


# =============================================================================
# MCP Tools - Reference Operations
# =============================================================================

@mcp.tool()
async def check_connection() -> dict:
    """
    Check if Zotero client is running and plugin is accessible.
    
    Returns connection status and Zotero version info.
    """
    client, _, _ = _get_dependencies()
    try:
        is_healthy = await client.health_check()
        return {
            "connected": is_healthy,
            "message": "Zotero is running and accessible" if is_healthy else "Cannot connect to Zotero",
            "endpoint": client.base_url,
        }
    except Exception as e:
        return {
            "connected": False,
            "message": f"Connection error: {str(e)}",
            "endpoint": client.base_url,
        }


@mcp.tool()
async def add_reference(
    title: str,
    item_type: str = "journalArticle",
    authors: Optional[list[str]] = None,
    date: Optional[str] = None,
    doi: Optional[str] = None,
    url: Optional[str] = None,
    abstract: Optional[str] = None,
    journal: Optional[str] = None,
    volume: Optional[str] = None,
    issue: Optional[str] = None,
    pages: Optional[str] = None,
    publisher: Optional[str] = None,
    isbn: Optional[str] = None,
    collection_key: Optional[str] = None,
) -> dict:
    """
    Add a new reference to Zotero library.
    
    Args:
        title: Title of the reference (required)
        item_type: Type of item - journalArticle, book, bookSection, conferencePaper, thesis, report, webpage, etc.
        authors: List of author names in "First Last" format
        date: Publication date (e.g., "2024", "2024-01", "2024-01-15")
        doi: Digital Object Identifier
        url: URL of the reference
        abstract: Abstract text
        journal: Journal/publication name (for articles)
        volume: Volume number
        issue: Issue number
        pages: Page range (e.g., "1-10")
        publisher: Publisher name (for books)
        isbn: ISBN (for books)
        collection_key: Optional collection key to add the reference to
        
    Returns:
        Dictionary with success status and created reference key
    """
    _, ref_repo, _ = _get_dependencies()
    
    try:
        # Parse item type
        try:
            parsed_item_type = ItemType(item_type)
        except ValueError:
            parsed_item_type = ItemType.JOURNAL_ARTICLE
        
        use_case = AddReferenceUseCase(ref_repo)
        input_data = AddReferenceInput(
            title=title,
            item_type=parsed_item_type,
            authors=authors or [],
            date=date,
            doi=doi,
            url=url,
            abstract=abstract,
            journal=journal,
            volume=volume,
            issue=issue,
            pages=pages,
            publisher=publisher,
            isbn=isbn,
            collection_key=collection_key,
        )
        
        output = await use_case.execute(input_data)
        
        return {
            "success": output.success,
            "key": output.key,
            "message": f"Reference '{title}' added successfully" if output.success else "Failed to add reference",
        }
    except Exception as e:
        return {
            "success": False,
            "key": None,
            "message": f"Error adding reference: {str(e)}",
        }


@mcp.tool()
async def get_reference(key: str) -> dict:
    """
    Get a specific reference from Zotero by its key.
    
    Args:
        key: The Zotero item key (e.g., "ABC12345")
        
    Returns:
        Full reference details or not found message
    """
    _, ref_repo, _ = _get_dependencies()
    
    try:
        use_case = GetReferenceUseCase(ref_repo)
        input_data = GetReferenceInput(key=key)
        output = await use_case.execute(input_data)
        
        if not output.found:
            return {"found": False, "message": f"Reference with key '{key}' not found"}
        
        return {
            "found": True,
            "reference": output.reference,
        }
    except Exception as e:
        return {"found": False, "message": f"Error: {str(e)}"}


@mcp.tool()
async def list_references(
    limit: int = 20,
    offset: int = 0,
    collection: Optional[str] = None,
) -> dict:
    """
    List references from Zotero library.
    
    Args:
        limit: Maximum number of references to return (default: 20)
        offset: Number of references to skip for pagination (default: 0)
        collection: Optional collection key to filter by
        
    Returns:
        List of references with basic metadata
    """
    _, ref_repo, _ = _get_dependencies()
    
    try:
        use_case = ListReferencesUseCase(ref_repo)
        input_data = ListReferencesInput(
            limit=limit,
            offset=offset,
            collection=collection,
        )
        output = await use_case.execute(input_data)
        
        return {
            "total": output.total,
            "count": output.count,
            "references": output.references,
        }
    except Exception as e:
        return {"total": 0, "count": 0, "references": [], "error": str(e)}


@mcp.tool()
async def search_references(query: str, limit: int = 20) -> dict:
    """
    Search for references in Zotero library.
    
    Args:
        query: Search query string (searches title, authors, abstract, etc.)
        limit: Maximum number of results (default: 20)
        
    Returns:
        List of matching references
    """
    _, ref_repo, _ = _get_dependencies()
    
    try:
        use_case = SearchReferencesUseCase(ref_repo)
        input_data = SearchReferencesInput(query=query, limit=limit)
        output = await use_case.execute(input_data)
        
        return {
            "count": output.count,
            "references": output.references,
        }
    except Exception as e:
        return {"count": 0, "references": [], "error": str(e)}


@mcp.tool()
async def export_references(
    keys: list[str],
    format: str = "bibtex",
) -> dict:
    """
    Export references in a citation format.
    
    Args:
        keys: List of Zotero item keys to export
        format: Export format - bibtex, ris, csljson, bibliography (default: bibtex)
        
    Returns:
        Formatted citation text
    """
    _, ref_repo, _ = _get_dependencies()
    
    try:
        # Parse format
        try:
            parsed_format = ExportFormat(format.lower())
        except ValueError:
            parsed_format = ExportFormat.BIBTEX
        
        use_case = ExportReferencesUseCase(ref_repo)
        input_data = ExportReferencesInput(keys=keys, format=parsed_format)
        output = await use_case.execute(input_data)
        
        return {
            "format": output.format,
            "count": output.count,
            "content": output.content,
        }
    except Exception as e:
        return {"format": format, "count": 0, "content": "", "error": str(e)}


@mcp.tool()
async def delete_reference(key: str) -> dict:
    """
    Delete a reference from Zotero library.
    
    Args:
        key: The Zotero item key to delete
        
    Returns:
        Success status
    """
    _, ref_repo, _ = _get_dependencies()
    
    try:
        use_case = DeleteReferenceUseCase(ref_repo)
        input_data = DeleteReferenceInput(key=key)
        output = await use_case.execute(input_data)
        
        return {
            "success": output.success,
            "deleted_key": output.deleted_key,
            "message": f"Reference '{key}' deleted" if output.success else f"Failed to delete '{key}'",
        }
    except Exception as e:
        return {"success": False, "deleted_key": key, "message": f"Error: {str(e)}"}


# =============================================================================
# MCP Tools - Collection Operations
# =============================================================================

@mcp.tool()
async def list_collections(parent_key: Optional[str] = None) -> dict:
    """
    List collections from Zotero library.
    
    Args:
        parent_key: Optional parent collection key to list sub-collections
        
    Returns:
        List of collections
    """
    _, _, col_repo = _get_dependencies()
    
    try:
        use_case = ListCollectionsUseCase(col_repo)
        input_data = ListCollectionsInput(parent_key=parent_key)
        output = await use_case.execute(input_data)
        
        return {
            "count": output.count,
            "collections": output.collections,
        }
    except Exception as e:
        return {"count": 0, "collections": [], "error": str(e)}


@mcp.tool()
async def get_collection(key: str) -> dict:
    """
    Get a specific collection by its key.
    
    Args:
        key: The Zotero collection key
        
    Returns:
        Collection details or not found message
    """
    _, _, col_repo = _get_dependencies()
    
    try:
        use_case = GetCollectionUseCase(col_repo)
        input_data = GetCollectionInput(key=key)
        output = await use_case.execute(input_data)
        
        if not output.found:
            return {"found": False, "message": f"Collection '{key}' not found"}
        
        return {
            "found": True,
            "collection": output.collection,
        }
    except Exception as e:
        return {"found": False, "message": f"Error: {str(e)}"}


@mcp.tool()
async def create_collection(
    name: str,
    parent_key: Optional[str] = None,
) -> dict:
    """
    Create a new collection in Zotero.
    
    Args:
        name: Name of the collection
        parent_key: Optional parent collection key for nested collection
        
    Returns:
        Success status and created collection key
    """
    _, _, col_repo = _get_dependencies()
    
    try:
        use_case = CreateCollectionUseCase(col_repo)
        input_data = CreateCollectionInput(name=name, parent_key=parent_key)
        output = await use_case.execute(input_data)
        
        return {
            "success": output.success,
            "key": output.key,
            "message": f"Collection '{name}' created" if output.success else "Failed to create collection",
        }
    except Exception as e:
        return {"success": False, "key": None, "message": f"Error: {str(e)}"}


@mcp.tool()
async def add_to_collection(collection_key: str, reference_key: str) -> dict:
    """
    Add a reference to a collection.
    
    Args:
        collection_key: The collection key to add to
        reference_key: The reference key to add
        
    Returns:
        Success status
    """
    _, _, col_repo = _get_dependencies()
    
    try:
        use_case = AddToCollectionUseCase(col_repo)
        input_data = AddToCollectionInput(
            collection_key=collection_key,
            reference_key=reference_key,
        )
        output = await use_case.execute(input_data)
        
        return {
            "success": output.success,
            "message": "Reference added to collection" if output.success else "Failed to add to collection",
        }
    except Exception as e:
        return {"success": False, "message": f"Error: {str(e)}"}


# =============================================================================
# Server Factory
# =============================================================================

def create_mcp_server(zotero_url: Optional[str] = None) -> FastMCP:
    """
    Create and configure the MCP server.
    
    Args:
        zotero_url: Optional URL for Zotero plugin (default: http://localhost:23120)
        
    Returns:
        Configured FastMCP server instance
    """
    global DEFAULT_ZOTERO_URL
    if zotero_url:
        DEFAULT_ZOTERO_URL = zotero_url
    
    return mcp
