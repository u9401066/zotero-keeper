"""Tests for unified_import_tools.py."""

from collections.abc import Awaitable, Callable
from datetime import date
import importlib.util
import json
from pathlib import Path
import sys
from typing import Any

import httpx
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from zotero_mcp.infrastructure.mcp.unified_import_tools import (
    _parse_ris_to_articles,
    _unified_article_to_zotero,
    register_unified_import_tools,
)


ImportArticlesTool = Callable[..., Awaitable[dict[str, Any]]]


def _build_pubmed_unified_article_payload() -> dict[str, Any]:
    """Build a payload from pubmed-search-mcp's canonical UnifiedArticle contract."""
    repo_root = Path(__file__).resolve().parents[4]
    article_contract = repo_root / "external" / "pubmed-search-mcp" / "src" / "pubmed_search" / "domain" / "entities" / "article.py"
    if not article_contract.exists():
        raise FileNotFoundError(f"Missing pubmed-search-mcp article contract: {article_contract}")

    spec = importlib.util.spec_from_file_location("pubmed_article_contract", article_contract)
    if spec is None or spec.loader is None:
        raise ImportError(f"Cannot load pubmed-search-mcp article contract: {article_contract}")

    article_module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = article_module
    spec.loader.exec_module(article_module)
    ArticleType = article_module.ArticleType
    Author = article_module.Author
    CitationMetrics = article_module.CitationMetrics
    UnifiedArticle = article_module.UnifiedArticle

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


def _register_import_tools(mock_mcp, mock_client) -> dict[str, ImportArticlesTool]:
    """Register all unified import tools and capture them by function name."""
    registered: dict[str, ImportArticlesTool] = {}

    def tool_decorator():
        def wrapper(func):
            registered[func.__name__] = func
            return func

        return wrapper

    mock_mcp.tool = tool_decorator
    register_unified_import_tools(mock_mcp, mock_client)
    return registered


def _register_import_tool(mock_mcp, mock_client) -> ImportArticlesTool:
    """Register tools and return the import_articles tool function."""
    tools = _register_import_tools(mock_mcp, mock_client)
    assert "import_articles" in tools
    return tools["import_articles"]


def _register_pdf_tool(mock_mcp, mock_client) -> ImportArticlesTool:
    """Register tools and return the import_pdf tool function."""
    tools = _register_import_tools(mock_mcp, mock_client)
    assert "import_pdf" in tools
    return tools["import_pdf"]


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
        # New metadata completeness fields
        assert saved_item["accessDate"].endswith("Z")
        assert saved_item["libraryCatalog"] == "PubMed"

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
            articles=[{"title": f"Article {index}", "pmid": str(10000000 + index), "authors": [f"Author {index}"]} for index in range(60)],
            skip_duplicates=False,
        )

        assert result["success"] is False
        assert result["partial_success"] is True
        assert result["imported"] == 50
        assert mock_client.save_items.await_count == 2
        assert any(error.get("batch") == 2 for error in result["errors"])


class TestTypeAwareMapping:
    """The mapper should produce schema-correct items for non-journal types."""

    def test_book_maps_publisher_place_isbn(self):
        article = {
            "title": "Clinical Anesthesia",
            "article_type": "book",
            "authors": ["Paul Barash"],
            "publisher": "Wolters Kluwer",
            "place": "Philadelphia",
            "isbn": "978-1-4963-3700-9",
            "edition": "8th",
            "year": 2017,
        }
        item = _unified_article_to_zotero(article)

        assert item["itemType"] == "book"
        assert item["publisher"] == "Wolters Kluwer"
        assert item["place"] == "Philadelphia"
        assert item["ISBN"] == "978-1-4963-3700-9"
        assert item["edition"] == "8th"
        # book has no publicationTitle field
        assert "publicationTitle" not in item

    def test_book_chapter_maps_book_title(self):
        article = {
            "title": "Airway Management",
            "article_type": "book-chapter",
            "journal": "Miller's Anesthesia",
            "pages": "1373-1412",
            "isbn": "978-0-323-59604-6",
        }
        item = _unified_article_to_zotero(article)

        assert item["itemType"] == "bookSection"
        assert item["bookTitle"] == "Miller's Anesthesia"
        assert item["pages"] == "1373-1412"
        assert "publicationTitle" not in item

    def test_conference_paper_maps_proceedings_and_conference(self):
        article = {
            "title": "Deep Learning for Sedation",
            "article_type": "conference-paper",
            "journal": "Proceedings of NeurIPS 2024",
            "conference_name": "NeurIPS 2024",
            "pages": "100-110",
            "doi": "10.1000/conf.2024",
        }
        item = _unified_article_to_zotero(article)

        assert item["itemType"] == "conferencePaper"
        assert item["proceedingsTitle"] == "Proceedings of NeurIPS 2024"
        assert item["conferenceName"] == "NeurIPS 2024"
        assert item["DOI"] == "10.1000/conf.2024"

    def test_webpage_routes_invalid_fields_to_extra(self):
        article = {
            "title": "Anesthesia Guidelines",
            "article_type": "webpage",
            "website_title": "ASA Society",
            "url": "https://asahq.org/guidelines",
            "volume": "5",  # invalid for webpage -> extra
        }
        item = _unified_article_to_zotero(article)

        assert item["itemType"] == "webpage"
        assert item["websiteTitle"] == "ASA Society"
        assert item["url"] == "https://asahq.org/guidelines"
        assert "volume" not in item
        assert "Volume: 5" in item["extra"]

    def test_repository_maps_to_computer_program_with_programmer(self):
        article = {
            "title": "zotero-keeper",
            "authors": ["Jane Doe"],
            "url": "https://github.com/owner/zotero-keeper",
            "version": "2.1.0",
            "programming_language": "Python",
        }
        item = _unified_article_to_zotero(article)

        assert item["itemType"] == "computerProgram"
        assert item["versionNumber"] == "2.1.0"
        assert item["programmingLanguage"] == "Python"
        assert item["creators"][0]["creatorType"] == "programmer"

    def test_preprint_records_arxiv_repository(self):
        article = {
            "title": "A New Transformer",
            "article_type": "preprint",
            "identifiers": {"arxiv_id": "2401.12345", "doi": "10.48550/arXiv.2401.12345"},
        }
        item = _unified_article_to_zotero(article)

        assert item["itemType"] == "preprint"
        assert item["repository"] == "arXiv"
        assert item["archiveID"] == "arXiv:2401.12345"

    def test_incomplete_record_falls_back_to_document(self):
        # Old scanned item with only a title and a note -> document, nothing lost
        article = {"title": "Untitled Scanned Monograph 1897"}
        item = _unified_article_to_zotero(article)

        assert item["itemType"] == "document"
        assert item["title"] == "Untitled Scanned Monograph 1897"

    def test_journal_article_unaffected(self):
        article = {
            "title": "AI in Anesthesia",
            "article_type": "journal-article",
            "journal": "Anesthesiology",
            "volume": "140",
            "issue": "2",
            "pages": "100-110",
            "issn": "0003-3022",
            "pmid": "12345678",
        }
        item = _unified_article_to_zotero(article)

        assert item["itemType"] == "journalArticle"
        assert item["publicationTitle"] == "Anesthesiology"
        assert item["volume"] == "140"
        assert item["ISSN"] == "0003-3022"
        assert "PMID: 12345678" in item["extra"]


class TestRisTypeAwareParsing:
    """The RIS parser should capture fields for books, conferences and web pages."""

    def test_parse_book_with_publisher_place_isbn(self):
        ris = (
            "TY  - BOOK\n"
            "TI  - Clinical Anesthesia\n"
            "AU  - Barash, Paul\n"
            "ED  - Cullen, Bruce\n"
            "PB  - Wolters Kluwer\n"
            "CY  - Philadelphia\n"
            "ET  - 8th\n"
            "SN  - 978-1-4963-3700-9\n"
            "PY  - 2017\n"
            "ER  - \n"
        )
        articles = _parse_ris_to_articles(ris)
        assert len(articles) == 1
        book = articles[0]
        assert book["article_type"] == "book"
        assert book["publisher"] == "Wolters Kluwer"
        assert book["place"] == "Philadelphia"
        assert book["edition"] == "8th"
        assert book["isbn"] == "978-1-4963-3700-9"
        assert book["editors"] == ["Cullen, Bruce"]

        item = _unified_article_to_zotero(book)
        assert item["itemType"] == "book"
        assert item["ISBN"] == "978-1-4963-3700-9"
        assert any(c["creatorType"] == "editor" for c in item["creators"])

    def test_parse_conference_paper(self):
        ris = (
            "TY  - CONF\n"
            "TI  - Neural Sedation Monitoring\n"
            "AU  - Smith, John\n"
            "T2  - Proceedings of NeurIPS\n"
            "SP  - 100\n"
            "EP  - 110\n"
            "DO  - 10.1000/conf.1\n"
            "ER  - \n"
        )
        articles = _parse_ris_to_articles(ris)
        item = _unified_article_to_zotero(articles[0])
        assert item["itemType"] == "conferencePaper"
        assert item["proceedingsTitle"] == "Proceedings of NeurIPS"
        assert item["pages"] == "100-110"

    def test_parse_webpage_distinguishes_issn_isbn(self):
        ris = "TY  - JOUR\nTI  - A Journal Article\nSN  - 1234-5678\nER  - \n"
        articles = _parse_ris_to_articles(ris)
        assert articles[0]["issn"] == "1234-5678"
        assert "isbn" not in articles[0]


class TestImportPdf:
    """Tests for the import_pdf tool (Connector API attachments)."""

    @pytest.mark.asyncio
    async def test_standalone_mode_auto_recognizes(self, tmp_path):
        """With no metadata, the PDF is saved standalone and auto-recognized."""
        mock_mcp = MagicMock()
        mock_client = AsyncMock()
        mock_client.save_standalone_attachment.return_value = {
            "success": True,
            "status_code": 201,
            "message": "ok",
            "data": {"canRecognize": True},
        }
        import_pdf = _register_pdf_tool(mock_mcp, mock_client)

        pdf = tmp_path / "paper.pdf"
        pdf.write_bytes(b"%PDF-1.7 minimal")

        result = await import_pdf(file_path=str(pdf))

        assert result["success"] is True
        assert result["mode"] == "standalone"
        assert result["recognizing"] is True
        mock_client.save_standalone_attachment.assert_awaited_once()
        kwargs = mock_client.save_standalone_attachment.await_args.kwargs
        assert kwargs["content_type"] == "application/pdf"
        assert kwargs["file_bytes"] == b"%PDF-1.7 minimal"
        assert kwargs["url"].startswith("file://")
        # Standalone mode must not create a parent item
        mock_client.save_items.assert_not_called()

    @pytest.mark.asyncio
    async def test_metadata_mode_attaches_to_created_parent(self, tmp_path):
        """With an article, a parent is created and the PDF is attached to it."""
        mock_mcp = MagicMock()
        mock_client = AsyncMock()
        mock_client.save_items.return_value = {"success": True}
        mock_client.save_attachment.return_value = {
            "success": True,
            "status_code": 201,
            "message": "ok",
            "data": "",
        }
        import_pdf = _register_pdf_tool(mock_mcp, mock_client)

        pdf = tmp_path / "ai.pdf"
        pdf.write_bytes(b"%PDF-1.7 ai")

        result = await import_pdf(
            file_path=str(pdf),
            article={
                "title": "AI in Anesthesia",
                "pmid": "38353755",
                "doi": "10.1/x",
                "journal": "Anesthesiology",
            },
        )

        assert result["success"] is True
        assert result["mode"] == "metadata"

        save_items_call = mock_client.save_items.await_args
        saved_item = save_items_call.args[0][0]
        session_id = save_items_call.kwargs["session_id"]
        connector_key = saved_item["id"]
        assert connector_key  # parent carries a connector key

        # The attachment must reference the same parent and session
        att_kwargs = mock_client.save_attachment.await_args.kwargs
        assert att_kwargs["parent_item_id"] == connector_key
        assert att_kwargs["session_id"] == session_id
        assert att_kwargs["content_type"] == "application/pdf"
        assert att_kwargs["file_bytes"] == b"%PDF-1.7 ai"

    @pytest.mark.asyncio
    async def test_metadata_mode_with_title_only_creates_document(self, tmp_path):
        """A bare title produces a generic document parent with the PDF attached."""
        mock_mcp = MagicMock()
        mock_client = AsyncMock()
        mock_client.save_items.return_value = {"success": True}
        mock_client.save_attachment.return_value = {"success": True, "data": ""}
        import_pdf = _register_pdf_tool(mock_mcp, mock_client)

        pdf = tmp_path / "scan.pdf"
        pdf.write_bytes(b"%PDF-1.7")

        result = await import_pdf(file_path=str(pdf), title="Old Scanned Report")

        assert result["success"] is True
        saved_item = mock_client.save_items.await_args.args[0][0]
        assert saved_item["title"] == "Old Scanned Report"
        assert saved_item["itemType"] == "document"

    @pytest.mark.asyncio
    async def test_missing_file_returns_error(self):
        """A non-existent path returns an error without any network calls."""
        mock_mcp = MagicMock()
        mock_client = AsyncMock()
        import_pdf = _register_pdf_tool(mock_mcp, mock_client)

        result = await import_pdf(file_path="/no/such/file.pdf")

        assert result["success"] is False
        assert "not found" in result["error"].lower()
        mock_client.save_items.assert_not_called()
        mock_client.save_standalone_attachment.assert_not_called()

    @pytest.mark.asyncio
    async def test_attachment_failure_is_surfaced(self, tmp_path):
        """If the parent saves but the attachment fails, the error is reported."""
        mock_mcp = MagicMock()
        mock_client = AsyncMock()
        mock_client.save_items.return_value = {"success": True}
        mock_client.save_attachment.return_value = {
            "success": False,
            "status_code": 200,
            "message": "Library files are not editable.",
            "data": "",
        }
        import_pdf = _register_pdf_tool(mock_mcp, mock_client)

        pdf = tmp_path / "x.pdf"
        pdf.write_bytes(b"%PDF-1.7")

        result = await import_pdf(file_path=str(pdf), title="Paper")

        assert result["success"] is False
        assert "attaching the pdf failed" in result["error"].lower()

    @pytest.mark.asyncio
    async def test_metadata_mode_end_to_end_wire(self, tmp_path):
        """Full flow through the REAL client + fake Zotero: saveItems then saveAttachment, linked."""
        from zotero_mcp.infrastructure.zotero_client.client import ZoteroClient, ZoteroConfig

        requests: list = []

        def handler(request: httpx.Request) -> httpx.Response:
            path = request.url.path
            if path == "/connector/saveItems":
                requests.append(("saveItems", dict(request.headers), json.loads(request.content)))
                return httpx.Response(201, json={"items": []})
            if path == "/connector/saveAttachment":
                requests.append(("saveAttachment", dict(request.headers), request.content))
                return httpx.Response(201, text="")
            return httpx.Response(404, text="unexpected path")

        client = ZoteroClient(config=ZoteroConfig(host="localhost", port=23119))
        client._client = httpx.AsyncClient(
            base_url=client.config.base_url,
            headers={"Content-Type": "application/json"},
            transport=httpx.MockTransport(handler),
        )
        import_pdf = _register_pdf_tool(MagicMock(), client)

        pdf = tmp_path / "ai.pdf"
        pdf.write_bytes(b"%PDF-1.7 ai")

        try:
            result = await import_pdf(
                file_path=str(pdf),
                article={
                    "title": "AI in Anesthesia",
                    "pmid": "38353755",
                    "doi": "10.1/x",
                    "journal": "Anesthesiology",
                },
            )
        finally:
            await client.close()

        assert result["success"] is True
        # Exactly two requests, in the correct order
        assert [r[0] for r in requests] == ["saveItems", "saveAttachment"]

        # saveItems carried a session ID and the parent's connector id
        save_items_body = requests[0][2]
        session_id = save_items_body["sessionID"]
        item_id = save_items_body["items"][0]["id"]
        assert item_id and session_id

        # The attachment references the SAME parent + session, with the real PDF body
        att_headers = requests[1][1]
        att_meta = json.loads(att_headers["x-metadata"])
        assert att_meta["parentItemID"] == item_id
        assert att_meta["sessionID"] == session_id
        assert att_headers["content-type"] == "application/pdf"
        assert requests[1][2] == b"%PDF-1.7 ai"

    @pytest.mark.asyncio
    async def test_standalone_mode_end_to_end_wire(self, tmp_path):
        """Full standalone flow through the REAL client + fake Zotero."""
        from zotero_mcp.infrastructure.zotero_client.client import ZoteroClient, ZoteroConfig

        seen: dict = {}

        def handler(request: httpx.Request) -> httpx.Response:
            seen["path"] = request.url.path
            seen["x_metadata"] = request.headers.get("x-metadata")
            seen["content_type"] = request.headers.get("content-type")
            seen["body"] = request.content
            return httpx.Response(201, json={"canRecognize": True})

        client = ZoteroClient(config=ZoteroConfig(host="localhost", port=23119))
        client._client = httpx.AsyncClient(
            base_url=client.config.base_url,
            headers={"Content-Type": "application/json"},
            transport=httpx.MockTransport(handler),
        )
        import_pdf = _register_pdf_tool(MagicMock(), client)

        pdf = tmp_path / "scan.pdf"
        pdf.write_bytes(b"%PDF scan")

        try:
            result = await import_pdf(file_path=str(pdf))
        finally:
            await client.close()

        assert result["success"] is True
        assert result["recognizing"] is True
        assert seen["path"] == "/connector/saveStandaloneAttachment"
        assert seen["content_type"] == "application/pdf"
        assert seen["body"] == b"%PDF scan"
        meta = json.loads(seen["x_metadata"])
        assert "parentItemID" not in meta  # standalone has no parent
        assert meta["title"] == "scan"  # defaults to the filename stem

    @pytest.mark.asyncio
    async def test_empty_file_returns_error(self, tmp_path):
        """An empty file is rejected before any network call."""
        mock_client = AsyncMock()
        import_pdf = _register_pdf_tool(MagicMock(), mock_client)

        pdf = tmp_path / "empty.pdf"
        pdf.write_bytes(b"")

        result = await import_pdf(file_path=str(pdf))

        assert result["success"] is False
        assert "empty" in result["error"].lower()
        mock_client.save_standalone_attachment.assert_not_called()

    @pytest.mark.asyncio
    async def test_invalid_article_returns_error(self, tmp_path):
        """An article payload missing a title is rejected without saving."""
        mock_client = AsyncMock()
        import_pdf = _register_pdf_tool(MagicMock(), mock_client)

        pdf = tmp_path / "x.pdf"
        pdf.write_bytes(b"%PDF")

        result = await import_pdf(file_path=str(pdf), article={"pmid": "123"})

        assert result["success"] is False
        assert "invalid article" in result["error"].lower()
        mock_client.save_items.assert_not_called()

    @pytest.mark.asyncio
    async def test_collection_not_found_returns_error(self, tmp_path):
        """A missing target collection short-circuits before saving."""
        mock_client = AsyncMock()
        mock_client.find_collection_by_name.return_value = None
        mock_client.get_collections.return_value = []
        import_pdf = _register_pdf_tool(MagicMock(), mock_client)

        pdf = tmp_path / "x.pdf"
        pdf.write_bytes(b"%PDF")

        result = await import_pdf(file_path=str(pdf), title="Paper", collection_name="Nonexistent")

        assert result["success"] is False
        assert "not found" in result["error"].lower()
        mock_client.save_items.assert_not_called()

    @pytest.mark.asyncio
    async def test_standalone_failure_is_surfaced(self, tmp_path):
        """A failed standalone save (e.g. read-only library) is reported."""
        mock_client = AsyncMock()
        mock_client.save_standalone_attachment.return_value = {
            "success": False,
            "message": "Library files are not editable.",
            "data": "",
        }
        import_pdf = _register_pdf_tool(MagicMock(), mock_client)

        pdf = tmp_path / "x.pdf"
        pdf.write_bytes(b"%PDF")

        result = await import_pdf(file_path=str(pdf))

        assert result["success"] is False
        assert "editable" in result["error"].lower()

    @pytest.mark.asyncio
    async def test_unexpected_client_error_is_caught(self, tmp_path):
        """Unexpected client exceptions are caught and returned as an error."""
        mock_client = AsyncMock()
        mock_client.save_standalone_attachment.side_effect = RuntimeError("boom")
        import_pdf = _register_pdf_tool(MagicMock(), mock_client)

        pdf = tmp_path / "x.pdf"
        pdf.write_bytes(b"%PDF")

        result = await import_pdf(file_path=str(pdf))

        assert result["success"] is False
        assert "boom" in result["error"]

    @pytest.mark.asyncio
    async def test_unreadable_file_returns_error(self, tmp_path):
        """A file that exists but cannot be read is reported (not crashed on)."""
        mock_client = AsyncMock()
        import_pdf = _register_pdf_tool(MagicMock(), mock_client)

        pdf = tmp_path / "x.pdf"
        pdf.write_bytes(b"%PDF")

        with patch("pathlib.Path.read_bytes", side_effect=OSError("permission denied")):
            result = await import_pdf(file_path=str(pdf))

        assert result["success"] is False
        assert "could not read" in result["error"].lower()
        mock_client.save_standalone_attachment.assert_not_called()

    @pytest.mark.asyncio
    async def test_tools_register_with_real_fastmcp(self):
        """Both tools register on a real FastMCP (validates MCP schema generation)."""
        from mcp.server.fastmcp import FastMCP

        mcp = FastMCP("test-keeper")
        register_unified_import_tools(mcp, AsyncMock())

        tools = await mcp.list_tools()
        names = {tool.name for tool in tools}
        assert "import_articles" in names
        assert "import_pdf" in names
