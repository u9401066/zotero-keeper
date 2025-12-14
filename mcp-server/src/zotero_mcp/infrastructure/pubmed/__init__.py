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


def fetch_citation_metrics(pmids: list[str]) -> dict[str, dict]:
    """
    Fetch citation metrics (RCR, percentile) from NIH iCite.

    Args:
        pmids: List of PubMed IDs

    Returns:
        Dictionary mapping PMID to metrics:
        {
            "12345678": {
                "relative_citation_ratio": 2.5,
                "nih_percentile": 85.0,
                "citation_count": 50,
                "citations_per_year": 10.0,
                "apt": 0.7
            }
        }
    """
    if not pmids:
        return {}

    try:
        client = get_pubmed_client()
        from pubmed_search.entrez import LiteratureSearcher  # type: ignore

        searcher = LiteratureSearcher(
            email=getattr(client, 'email', 'zotero@example.com'),
            api_key=getattr(client, 'api_key', None)
        )
        metrics = searcher.get_citation_metrics(pmids)
        logger.info(f"Fetched citation metrics for {len(metrics)} articles")
        return metrics

    except ImportError as e:
        logger.warning(f"Cannot import LiteratureSearcher for citation metrics: {e}")
        return {}
    except Exception as e:
        logger.warning(f"Failed to fetch citation metrics: {e}")
        return {}


def enrich_articles_with_metrics(articles: list[dict], pmids: list[str] | None = None) -> list[dict]:
    """
    Enrich article data with citation metrics.

    Modifies articles in-place by adding RCR and other metrics.

    Args:
        articles: List of article dictionaries (will be modified)
        pmids: Optional list of PMIDs. If not provided, extracted from articles.

    Returns:
        The same articles list with metrics added
    """
    if not articles:
        return articles

    # Extract PMIDs if not provided
    if pmids is None:
        pmids = [str(a.get("pmid", "")) for a in articles if a.get("pmid")]

    if not pmids:
        return articles

    # Fetch metrics
    metrics = fetch_citation_metrics(pmids)

    if not metrics:
        return articles

    # Merge metrics into articles
    for article in articles:
        pmid = str(article.get("pmid", ""))
        if pmid in metrics:
            m = metrics[pmid]
            article["relative_citation_ratio"] = m.get("relative_citation_ratio")
            article["nih_percentile"] = m.get("nih_percentile")
            article["citation_count"] = m.get("citation_count")
            article["citations_per_year"] = m.get("citations_per_year")
            article["apt"] = m.get("apt")

    return articles


# Type checking support
if TYPE_CHECKING:
    from pubmed_search.client import PubMedClient, SearchResult  # noqa: F401
