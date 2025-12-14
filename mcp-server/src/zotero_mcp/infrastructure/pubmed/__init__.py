"""
PubMed Search Integration

Provides direct access to pubmed-search library.

Priority:
1. Git submodule (development mode) - external/pubmed-search-mcp/src
2. Installed package via pip/uv (production mode) - pubmed_search

This allows both development with submodule and production with installed package.
"""

import logging
import os
import sys
from pathlib import Path
from typing import TYPE_CHECKING

logger = logging.getLogger(__name__)

# Flag to track configuration status
_configured = False
_use_submodule = False  # True if using submodule, False if using installed package


def _find_submodule_path() -> Path | None:
    """
    Find the pubmed-search submodule path.

    Returns:
        Path to submodule src/ directory, or None if not found.
    """
    current_file = Path(__file__).resolve()

    # Walk up from current file to find project root (contains external/)
    def find_external(start_path: Path) -> Path | None:
        current = start_path
        for _ in range(10):  # Max 10 levels up
            external = current / "external" / "pubmed-search-mcp" / "src"
            if external.exists() and (external / "pubmed_search").is_dir():
                return external
            parent = current.parent
            if parent == current:
                break
            current = parent
        return None

    # Check environment variable first
    env_path = os.environ.get("PUBMED_SEARCH_PATH")
    if env_path:
        p = Path(env_path)
        if p.exists() and (p / "pubmed_search").is_dir():
            return p

    # Search from current file location
    found = find_external(current_file.parent)
    if found:
        return found

    # Search from cwd
    found = find_external(Path.cwd())
    if found:
        return found

    return None


def _configure_pubmed_search() -> bool:
    """
    Configure pubmed_search import.

    Priority:
    1. Git submodule (if available) - for development
    2. Installed package - for production

    Returns:
        True if successful, False otherwise.
    """
    global _configured, _use_submodule

    if _configured:
        return True

    # Priority 1: Try submodule first (development mode)
    submodule_path = _find_submodule_path()
    if submodule_path:
        path_str = str(submodule_path)
        if path_str not in sys.path:
            sys.path.insert(0, path_str)

        # Verify import works
        try:
            import pubmed_search
            # Reload if already imported from installed package
            if hasattr(pubmed_search, '__file__') and submodule_path not in Path(pubmed_search.__file__).parents:
                import importlib
                importlib.reload(pubmed_search)

            logger.info(f"Using pubmed-search from submodule: {submodule_path}")
            _configured = True
            _use_submodule = True
            return True
        except ImportError:
            # Remove the path if import failed
            if path_str in sys.path:
                sys.path.remove(path_str)

    # Priority 2: Try installed package (production mode)
    try:
        import pubmed_search
        logger.info(f"Using installed pubmed-search package: {pubmed_search.__file__}")
        _configured = True
        _use_submodule = False
        return True
    except ImportError:
        pass

    logger.warning(
        "pubmed-search not available. Options:\n"
        "  1. Development: git submodule update --init --recursive\n"
        "  2. Production: pip install pubmed-search-mcp"
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
    if not _configure_pubmed_search():
        raise ImportError(
            "Cannot import pubmed_search. "
            "Install via 'pip install pubmed-search-mcp' or "
            "clone submodule via 'git submodule update --init --recursive'"
        )

    from pubmed_search.client import PubMedClient

    # Get API key from environment if available
    email = os.environ.get("NCBI_EMAIL", "zotero-keeper@example.com")
    api_key = os.environ.get("NCBI_API_KEY")

    return PubMedClient(email=email, api_key=api_key)


def is_using_submodule() -> bool:
    """Check if using submodule (development) or installed package (production)."""
    _configure_pubmed_search()
    return _use_submodule


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
    from pubmed_search.client import PubMedClient, SearchResult  # noqa: F401
