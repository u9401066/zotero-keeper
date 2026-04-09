"""Tests for unified_import_tools.py."""

from collections.abc import Awaitable, Callable
from datetime import date
from pathlib import Path
import sys
from typing import Any

import pytest
from unittest.mock import AsyncMock, MagicMock

from zotero_mcp.infrastructure.mcp.unified_import_tools import register_unified_import_tools


ImportArticlesTool = Callable[..., Awaitable[dict[str, Any]]]


def _build_pubmed_unified_article_payload() -> dict[str, Any]:
    """Build a payload from pubmed-search-mcp's canonical UnifiedArticle contract."""
    repo_root = Path(__file__).resolve().parents[4]
    pubmed_src = repo_root / "external" / "pubmed-search-mcp" / "src"
    if not pubmed_src.exists():
        raise FileNotFoundError(f"Missing pubmed-search-mcp source tree: {pubmed_src}")

    pubmed_src_str = str(pubmed_src)
    if pubmed_src_str not in sys.path:
        sys.path.insert(0, pubmed_src_str)

    from pubmed_search.domain.entities.article import ArticleType, Author, CitationMetrics, UnifiedArticle

    article = UnifiedArticle(
        title="Machine Learning for ICU Sedation",
        primary_source="pubmed",
        pmid="12345678",
        doi="10.1000/icu-sedation",
        pmc="PMC7654321",
        authors=[
            Author(given_name="Jane", family_name="Smith"),
            Author(given_name="Wei", family_name="Chen"),
        ],
        abstract="Structured search payload used for keeper contract verification.",
        journal="Critical Care Medicine",
        volume="52",
        issue="4",
        pages="101-110",
        publication_date=date(2024, 2, 15),
        year=2024,
        article_type=ArticleType.JOURNAL_ARTICLE,
        keywords=["machine learning", "icu"],
        mesh_terms=["Conscious Sedation", "Intensive Care Units"],
        citation_metrics=CitationMetrics(
            citation_count=42,
            relative_citation_ratio=1.75,
            nih_percentile=82.5,
            apt=0.34,
        ),
    )
    return article.to_dict()


def _register_import_tool(mock_mcp, mock_client) -> ImportArticlesTool:
    """Register import_articles and return the captured tool function."""
    registered_func: ImportArticlesTool | None = None

    def tool_decorator():
        def wrapper(func):
            nonlocal registered_func
            registered_func = func
            return func

        return wrapper

    mock_mcp.tool = tool_decorator
    register_unified_import_tools(mock_mcp, mock_client)
    assert registered_func is not None
    return registered_func


class TestImportArticles:
    """Tests for the unified import tool."""

    @pytest.mark.asyncio
    async def test_accepts_pubmed_unified_article_contract_without_drift(self):
        """Canonical UnifiedArticle.to_dict output should import cleanly into keeper."""
        mock_mcp = MagicMock()
        mock_client = AsyncMock()
        mock_client.save_items.return_value = {"success": True}

        import_articles = _register_import_tool(mock_mcp, mock_client)
        payload = _build_pubmed_unified_article_payload()

        result = await import_articles(articles=[payload], skip_duplicates=False)

        assert result["success"] is True
        assert result["imported"] == 1
        saved_item = mock_client.save_items.await_args.args[0][0]

        assert saved_item["title"] == "Machine Learning for ICU Sedation"
        assert saved_item["DOI"] == "10.1000/icu-sedation"
        assert saved_item["publicationTitle"] == "Critical Care Medicine"
        assert saved_item["date"] == "2024"
        assert saved_item["url"] == "https://doi.org/10.1000/icu-sedation"
        assert saved_item["creators"][0] == {
            "firstName": "Jane",
            "lastName": "Smith",
            "creatorType": "author",
        }
        assert "PMID: 12345678" in saved_item["extra"]
        assert "PMCID: PMC7654321" in saved_item["extra"]
        assert "RCR: 1.75" in saved_item["extra"]
        assert "Percentile: 82.5" in saved_item["extra"]
        assert "Citations: 42" in saved_item["extra"]
        assert {tag["tag"] for tag in saved_item["tags"]} == {
            "machine learning",
            "icu",
            "Conscious Sedation",
            "Intensive Care Units",
        }

    @pytest.mark.asyncio
    async def test_skips_duplicates_using_batch_identifier_check(self):
        """PMID and DOI duplicates should be filtered via batch_check_identifiers."""
        mock_mcp = MagicMock()
        mock_client = AsyncMock()
        mock_client.batch_check_identifiers.return_value = {
            "existing_pmids": {"11111111"},
            "existing_dois": {"10.1234/existing"},
            "pmid_to_key": {"11111111": "PMIDKEY"},
            "doi_to_key": {"10.1234/existing": "DOIKEY"},
        }
        mock_client.save_items.return_value = {"success": True}

        import_articles = _register_import_tool(mock_mcp, mock_client)

        result = await import_articles(
            articles=[
                {"title": "Duplicate PMID", "pmid": "11111111", "authors": ["Author One"]},
                {"title": "Duplicate DOI", "doi": "10.1234/existing", "authors": ["Author Two"]},
                {"title": "Fresh Article", "pmid": "33333333", "doi": "10.1234/new", "authors": ["Author Three"]},
            ]
        )

        assert result["success"] is True
        assert result["skipped"] == 2
        assert result["imported"] == 1
        mock_client.batch_check_identifiers.assert_awaited_once_with(
            pmids=["11111111", "33333333"],
            dois=["10.1234/existing", "10.1234/new"],
        )

        saved_items = mock_client.save_items.await_args.args[0]
        assert len(saved_items) == 1
        assert saved_items[0]["title"] == "Fresh Article"

    @pytest.mark.asyncio
    async def test_rejects_article_lists_larger_than_limit(self):
        """Large imports should fail fast with a batching hint."""
        mock_mcp = MagicMock()
        mock_client = AsyncMock()
        import_articles = _register_import_tool(mock_mcp, mock_client)

        result = await import_articles(
            articles=[{"title": f"Article {index}"} for index in range(101)],
            skip_duplicates=False,
        )

        assert result["success"] is False
        assert "Maximum supported per import is 100" in result["error"]
        assert "Split the import into batches" in result["hint"]
        mock_client.batch_check_identifiers.assert_not_called()
        mock_client.save_items.assert_not_called()

    @pytest.mark.asyncio
    async def test_reports_invalid_article_payloads_without_blocking_valid_items(self):
        """Schema validation should skip bad payloads while importing valid ones."""
        mock_mcp = MagicMock()
        mock_client = AsyncMock()
        mock_client.save_items.return_value = {"success": True}

        import_articles = _register_import_tool(mock_mcp, mock_client)

        result = await import_articles(
            articles=[
                {"title": "Valid Article", "pmid": "12345678", "authors": ["Author One"]},
                {"title": "Bad Authors", "authors": "Author One"},
                {"pmid": "87654321", "authors": ["Author Two"]},
            ],
            skip_duplicates=False,
        )

        assert result["success"] is True
        assert result["imported"] == 1
        assert len(result["errors"]) == 2
        assert all("Invalid article schema" in error["error"] for error in result["errors"])

        saved_items = mock_client.save_items.await_args.args[0]
        assert len(saved_items) == 1
        assert saved_items[0]["title"] == "Valid Article"

    @pytest.mark.asyncio
    async def test_reports_partial_success_when_a_save_batch_fails(self):
        """Imports should continue batch-by-batch and report partial success."""
        mock_mcp = MagicMock()
        mock_client = AsyncMock()
        mock_client.save_items.side_effect = [
            {"success": True},
            Exception("Connector API unavailable"),
        ]

        import_articles = _register_import_tool(mock_mcp, mock_client)

        result = await import_articles(
            articles=[
                {"title": f"Article {index}", "pmid": str(10000000 + index), "authors": [f"Author {index}"]}
                for index in range(60)
            ],
            skip_duplicates=False,
        )

        assert result["success"] is False
        assert result["partial_success"] is True
        assert result["imported"] == 50
        assert mock_client.save_items.await_count == 2
        assert any(error.get("batch") == 2 for error in result["errors"])
