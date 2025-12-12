"""
PubMed Search Integration

Provides direct access to pubmed-search library as a Python import.
This module handles the path configuration to import from the submodule.
"""

import sys
import os
import logging
from pathlib import Path
from typing import TYPE_CHECKING

logger = logging.getLogger(__name__)

# Flag to track if we've already configured the path
_path_configured = False


def _configure_pubmed_search_path() -> bool:
    """
    Configure sys.path to allow importing pubmed_search from submodule.
    
    Returns:
        True if successful, False otherwise.
    """
    global _path_configured
    
    if _path_configured:
        return True
    
    # Find the external/pubmed-search-mcp/src directory
    # We need to search upward from the current file location
    current_file = Path(__file__).resolve()
    
    # Try different possible locations
    possible_paths = [
        # From mcp-server/src/zotero_mcp/infrastructure/pubmed/ (current location)
        current_file.parent.parent.parent.parent.parent.parent / "external" / "pubmed-search-mcp" / "src",
        # From workspace root
        Path.cwd() / "external" / "pubmed-search-mcp" / "src",
        # Alternative: environment variable
    ]
    
    # Check PUBMED_SEARCH_PATH environment variable
    env_path = os.environ.get("PUBMED_SEARCH_PATH")
    if env_path:
        possible_paths.insert(0, Path(env_path))
    
    for path in possible_paths:
        if path.exists() and (path / "pubmed_search").is_dir():
            path_str = str(path)
            if path_str not in sys.path:
                sys.path.insert(0, path_str)
                logger.info(f"Added pubmed-search path: {path_str}")
            _path_configured = True
            return True
    
    logger.warning(
        "Could not find pubmed-search-mcp submodule. "
        "Please ensure the submodule is cloned: "
        "git submodule update --init --recursive"
    )
    return False


def get_pubmed_client():
    """
    Get a PubMedClient instance.
    
    Lazily configures the import path and creates a client.
    
    Returns:
        PubMedClient instance
        
    Raises:
        ImportError: If pubmed-search cannot be imported
    """
    if not _configure_pubmed_search_path():
        raise ImportError(
            "Cannot import pubmed_search. "
            "Please ensure external/pubmed-search-mcp submodule is available."
        )
    
    from pubmed_search.client import PubMedClient
    
    # Get API key from environment if available
    email = os.environ.get("NCBI_EMAIL", "zotero-keeper@example.com")
    api_key = os.environ.get("NCBI_API_KEY")
    
    return PubMedClient(email=email, api_key=api_key)


def fetch_pubmed_articles(pmids: list[str]) -> list[dict]:
    """
    Fetch complete article details from PubMed.
    
    This is the main entry point for fetching article metadata.
    Uses the pubmed-search library's PubMedClient.
    
    Args:
        pmids: List of PubMed IDs
        
    Returns:
        List of article dictionaries with complete metadata
        
    Raises:
        ImportError: If pubmed-search cannot be imported
        Exception: If fetch fails
    """
    client = get_pubmed_client()
    return client.fetch_details(pmids)


# Type checking support
if TYPE_CHECKING:
    from pubmed_search.client import PubMedClient, SearchResult
