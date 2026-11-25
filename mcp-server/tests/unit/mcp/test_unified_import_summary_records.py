"""import_articles / import_pdf must not write incomplete items from summary records.

pubmed-search-mcp 0.12.0 changed ``unified_search(..., output_format="json")``:
``articles`` are summary records by default (``first_author`` + ``author_count``,
a 400-character ``abstract_snippet``; no author list, full abstract,
volume/issue/pages or MeSH terms). Complete ``UnifiedArticle.to_dict()``
records need ``options="full_records"``. Before this guard Keeper saved summary
records as Zotero items without creators and without an abstract.

The fixtures below are verbatim ``_summary_article_payload`` output of the
pubmed-search-mcp 0.12.0 release branch (a PubMed RCT and an OpenAlex-only
record), plus the rank scores and retrieval provenance a real search adds.
"""

from __future__ import annotations

from collections.abc import Awaitable, Callable
import copy
from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pytest

from zotero_mcp.infrastructure.mcp.unified_import_tools import _parse_ris_to_articles, register_unified_import_tools
from zotero_mcp.infrastructure.mcp.unified_record_detail import is_summary_record

ToolFunction = Callable[..., Awaitable[dict[str, Any]]]

SNIPPET = (
    "Extubation in the post-anesthesia care unit (PACU) is a high-risk transition, frequently accompanied by "
    "hemodynamic fluctuations and respiratory events. Extubation in the post-anesthesia care unit (PACU) is a "
    "high-risk transition, frequently accompanied by hemodynamic fluctuations and respiratory events. "
    "Extubation in the post-anesthesia care unit (PACU) is a high-risk transition, frequently…"
)

PUBMED_SUMMARY_RECORD: dict[str, Any] = {
    "rank": 1,
    "pmid": "41926003",
    "doi": "10.1007/s10877-026-00001-0",
    "pmc": "PMC12345678",
    "title": "Nociception index-monitored extubation in the post-anesthesia care unit: a randomized controlled trial.",
    "year": 2026,
    "journal": "Journal of clinical monitoring and computing",
    "first_author": "Investigator0 Surname0",
    "author_count": 3,
    "publication_types": ["Journal Article", "Randomized Controlled Trial"],
    "article_type": "randomized-controlled-trial",
    "abstract_snippet": SNIPPET,
    "abstract_truncated": True,
    "source": "pubmed",
    "sources": ["pubmed"],
    "open_access": True,
    "oa_status": "green",
    "pdf_available": False,
    "ranking_score": 0.8123,
    "rank_percentile": 1.0,
    "retrieval": {"tier": "exact", "broadened": False, "strategy": "original"},
}

OPENALEX_SUMMARY_RECORD: dict[str, Any] = {
    "rank": 2,
    "pmid": None,
    "doi": None,
    "pmc": None,
    "openalex_id": "W4400000000",
    "title": "An OpenAlex-only preprint",
    "year": None,
    "journal": None,
    "first_author": None,
    "author_count": 0,
    "publication_types": [],
    "article_type": "unknown",
    "abstract_snippet": "Short abstract.",
    "abstract_truncated": False,
    "source": "openalex",
    "sources": [],
    "open_access": False,
    "oa_status": "unknown",
    "pdf_available": False,
}

# UnifiedArticle.to_dict() shape, as returned with options="full_records".
FULL_RECORD: dict[str, Any] = {
    "title": "Processed EEG guidance and emergence delirium after general anaesthesia",
    "primary_source": "pubmed",
    "identifiers": {
        "pmid": "41000001",
        "doi": "10.1000/full-record",
        "pmc": None,
        "openalex_id": None,
        "s2_id": None,
        "core_id": None,
        "arxiv_id": None,
    },
    "authors": [{"name": "Jane Smith", "orcid": None}, {"name": "Wei Chen", "orcid": None}],
    "author_string": "Smith J, Chen W",
    "abstract": "Full abstract of the complete record.",
    "journal": "Anesthesiology",
    "journal_abbrev": "Anesthesiology",
    "volume": "144",
    "issue": "2",
    "pages": "201-210",
    "year": 2026,
    "publication_date": "2026-02-01",
    "publisher": None,
    "article_type": "randomized-controlled-trial",
    "keywords": ["processed EEG"],
    "mesh_terms": ["Emergence Delirium"],
    "open_access": {"is_oa": False, "status": "closed", "best_link": None, "links": []},
    "urls": {"pubmed": "https://pubmed.ncbi.nlm.nih.gov/41000001/", "doi": "https://doi.org/10.1000/full-record", "pmc": None},
    "sources": ["pubmed"],
}


def _summary() -> dict[str, Any]:
    return copy.deepcopy(PUBMED_SUMMARY_RECORD)


def _register(mock_client: AsyncMock) -> dict[str, ToolFunction]:
    registered: dict[str, ToolFunction] = {}
    mock_mcp = MagicMock()

    def tool_decorator():
        def wrapper(func):
            registered[func.__name__] = func
            return func

        return wrapper

    mock_mcp.tool = tool_decorator
    register_unified_import_tools(mock_mcp, mock_client)
    return registered


def _client_with_collection() -> AsyncMock:
    mock_client = AsyncMock()
    mock_client.find_collection_by_name.return_value = {"key": "PACU0001", "data": {"name": "PACU"}}
    mock_client.batch_check_identifiers.return_value = {"existing_pmids": set(), "existing_dois": set()}
    mock_client.save_items.return_value = {"success": True}
    return mock_client


class TestSummaryRecordDiscriminator:
    """Summary keys without both full-record fields mark a summary record."""

    @pytest.mark.parametrize(
        ("record", "expected"),
        [
            (PUBMED_SUMMARY_RECORD, True),
            (OPENALEX_SUMMARY_RECORD, True),
            ({"title": "Only a snippet", "abstract_snippet": None}, True),
            ({"title": "Only a count", "author_count": 4}, True),
            ({"title": "Only the flag", "abstract_truncated": False}, True),
            ({**PUBMED_SUMMARY_RECORD, "authors": [], "abstract": None}, False),
            ({**PUBMED_SUMMARY_RECORD, "authors": ["A B"], "abstractNote": "Full."}, False),
            (FULL_RECORD, False),
            ({"title": "Citation node", "first_author": "Kim Lee", "authors": ["Kim Lee"]}, False),
            ({"title": "Bare manual entry"}, False),
            ("not a record", False),
            (None, False),
        ],
        ids=[
            "pubmed-summary",
            "openalex-summary",
            "snippet-key",
            "author-count-key",
            "truncated-flag-key",
            "summary-keys-with-both-full-fields",
            "summary-keys-with-abstractNote",
            "full-record",
            "first-author-only",
            "manual-entry",
            "string",
            "none",
        ],
    )
    def test_is_summary_record(self, record, expected):
        assert is_summary_record(record) is expected

    def test_ris_records_are_never_summary_records(self):
        ris = "TY  - JOUR\nTI  - A RIS record\nAU  - Smith, Jane\nER  - \n"
        assert [is_summary_record(article) for article in _parse_ris_to_articles(ris)] == [False]


class TestSummaryRecordImport:
    @pytest.mark.asyncio
    async def test_pure_summary_batch_is_refused_without_any_zotero_call(self):
        mock_client = _client_with_collection()
        import_articles = _register(mock_client)["import_articles"]

        result = await import_articles(
            articles=[_summary(), copy.deepcopy(OPENALEX_SUMMARY_RECORD)],
            collection_name="PACU",
        )

        assert result["success"] is False
        assert result["imported"] == 0
        assert result["error_code"] == "summary_records"
        assert 'options="full_records"' in result["hint"]
        guidance = result["summary_records"]
        assert guidance["count"] == 2
        assert guidance["articles"] == [1, 2]
        assert guidance["pmids"] == ["41926003"]
        assert guidance["without_pmid"] == [2]
        assert guidance["next_commands"] == [
            'unified_search(..., output_format="json", options="full_records")',
            'fetch_article_details(pmids="41926003", output_format="json")',
        ]
        assert [(error["article"], error["code"]) for error in result["errors"]] == [
            (1, "summary_record"),
            (2, "summary_record"),
        ]
        assert result["errors"][0]["pmid"] == "41926003"
        assert result["errors"][0]["doi"] == "10.1007/s10877-026-00001-0"
        assert "pmid" not in result["errors"][1]
        mock_client.find_collection_by_name.assert_not_awaited()
        mock_client.batch_check_identifiers.assert_not_awaited()
        mock_client.save_items.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_pure_summary_batch_without_collection_is_refused_and_never_reaches_root(self):
        mock_client = _client_with_collection()
        import_articles = _register(mock_client)["import_articles"]

        result = await import_articles(articles=[_summary()], allow_library_root=True, skip_duplicates=False)

        assert result["success"] is False
        assert result["error_code"] == "summary_records"
        assert "saved_to" not in result
        mock_client.save_items.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_mixed_batch_imports_complete_records_and_reports_each_summary_record(self):
        mock_client = _client_with_collection()
        mock_client.batch_check_identifiers.return_value = {
            "existing_pmids": {"41000001"},
            "existing_dois": set(),
        }
        import_articles = _register(mock_client)["import_articles"]
        legacy = {"title": "Legacy flat record", "pmid": "39999999", "authors": ["Ana Lopez"], "abstract": "Legacy abstract."}

        result = await import_articles(
            articles=[copy.deepcopy(FULL_RECORD), _summary(), legacy],
            collection_name="PACU",
        )

        assert result["success"] is True
        assert result["imported"] == 1
        assert result["skipped"] == 1  # duplicate safety still applies to complete records
        assert result["items"] == ["Legacy flat record"]
        assert result["saved_to"] == {"key": "PACU0001", "name": "PACU"}
        assert result["errors"] == [
            {
                "article": 2,
                "title": PUBMED_SUMMARY_RECORD["title"][:50],
                "code": "summary_record",
                "error": "Summary record (no author list or full abstract); not imported",
                "pmid": "41926003",
                "doi": "10.1007/s10877-026-00001-0",
            }
        ]
        assert result["summary_records"]["articles"] == [2]
        assert "1 summary record(s) not imported" in result["message"]
        assert "error_code" not in result

        # Only complete records reach the duplicate check and Zotero.
        mock_client.batch_check_identifiers.assert_awaited_once_with(
            pmids=["41000001", "39999999"],
            dois=["10.1000/full-record"],
        )
        saved = mock_client.save_items.await_args.args[0]
        assert [item["title"] for item in saved] == ["Legacy flat record"]
        assert saved[0]["collections"] == ["PACU0001"]
        assert saved[0]["creators"] == [{"firstName": "Ana", "lastName": "Lopez", "creatorType": "author"}]

    @pytest.mark.asyncio
    async def test_complete_records_import_exactly_as_before(self):
        mock_client = _client_with_collection()
        import_articles = _register(mock_client)["import_articles"]
        # A full record without authors or abstract (e.g. conference proceedings) is still complete.
        no_authors = copy.deepcopy(FULL_RECORD)
        no_authors["title"] = "Proceedings record without authors"
        no_authors["identifiers"]["pmid"] = "41000002"
        no_authors["identifiers"]["doi"] = None
        no_authors["authors"] = []
        no_authors["abstract"] = None

        result = await import_articles(
            articles=[copy.deepcopy(FULL_RECORD), no_authors],
            collection_name="PACU",
            skip_duplicates=False,
        )

        assert result["success"] is True
        assert result["imported"] == 2
        assert result["errors"] == []
        assert "summary_records" not in result
        full_item, proceedings_item = mock_client.save_items.await_args.args[0]
        assert full_item["creators"] == [
            {"firstName": "Jane", "lastName": "Smith", "creatorType": "author"},
            {"firstName": "Wei", "lastName": "Chen", "creatorType": "author"},
        ]
        assert full_item["abstractNote"] == "Full abstract of the complete record."
        assert full_item["volume"] == "144"
        assert full_item["pages"] == "201-210"
        assert "creators" not in proceedings_item

    @pytest.mark.asyncio
    async def test_ris_import_is_unchanged(self):
        mock_client = _client_with_collection()
        import_articles = _register(mock_client)["import_articles"]
        ris = (
            "TY  - JOUR\n"
            "TI  - Bispectral index monitoring in the PACU\n"
            "AU  - Smith, Jane\n"
            "AB  - Complete RIS abstract.\n"
            "PY  - 2025\n"
            "JO  - Anesthesia & Analgesia\n"
            "N1  - PMID: 40000001\n"
            "ER  - \n"
        )

        result = await import_articles(ris_text=ris, collection_name="PACU", skip_duplicates=False)

        assert result["success"] is True
        assert result["imported"] == 1
        assert "summary_records" not in result
        saved = mock_client.save_items.await_args.args[0][0]
        assert saved["creators"] == [{"lastName": "Smith", "firstName": "Jane", "creatorType": "author"}]
        assert saved["abstractNote"] == "Complete RIS abstract."
        assert "PMID: 40000001" in saved["extra"]

    @pytest.mark.asyncio
    async def test_summary_record_completed_with_author_list_and_abstract_is_imported(self):
        mock_client = _client_with_collection()
        import_articles = _register(mock_client)["import_articles"]
        completed = _summary()
        completed["authors"] = ["Investigator0 Surname0", "Investigator1 Surname1", "Investigator2 Surname2"]
        completed["abstract"] = "Complete abstract restored by the agent."

        result = await import_articles(articles=[completed], collection_name="PACU", skip_duplicates=False)

        assert result["success"] is True
        assert result["imported"] == 1
        saved = mock_client.save_items.await_args.args[0][0]
        assert len(saved["creators"]) == 3
        assert saved["abstractNote"] == "Complete abstract restored by the agent."

    @pytest.mark.asyncio
    @pytest.mark.parametrize(
        "restored",
        [
            {"authors": ["Investigator0 Surname0"]},
            {"abstract": SNIPPET},
        ],
        ids=["author-list-only", "abstract-only"],
    )
    async def test_summary_record_with_only_one_full_field_is_still_refused(self, restored):
        mock_client = _client_with_collection()
        import_articles = _register(mock_client)["import_articles"]
        partial = _summary()
        partial.update(restored)

        result = await import_articles(articles=[partial], collection_name="PACU")

        assert result["success"] is False
        assert result["error_code"] == "summary_records"
        mock_client.save_items.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_records_with_first_author_but_no_summary_keys_keep_todays_behaviour(self):
        """Citation-network nodes carry first_author too; they are not summary records."""
        mock_client = _client_with_collection()
        import_articles = _register(mock_client)["import_articles"]
        citation_node = {
            "pmid": "38000001",
            "title": "Seed paper from a citation tree",
            "year": 2024,
            "journal": "Anaesthesia",
            "authors": ["Kim Lee", "Ola Berg", "Raj Patel"],
            "first_author": "Kim Lee",
            "doi": "10.1000/seed",
        }

        result = await import_articles(articles=[citation_node], collection_name="PACU", skip_duplicates=False)

        assert result["success"] is True
        assert result["imported"] == 1
        assert "summary_records" not in result


class TestSummaryRecordPdfImport:
    @pytest.mark.asyncio
    async def test_import_pdf_refuses_a_summary_record_as_parent_metadata(self, tmp_path):
        mock_client = _client_with_collection()
        import_pdf = _register(mock_client)["import_pdf"]
        pdf = tmp_path / "paper.pdf"
        pdf.write_bytes(b"%PDF-1.7 minimal")

        result = await import_pdf(file_path=str(pdf), article=_summary(), collection_name="PACU")

        assert result["success"] is False
        assert result["error_code"] == "summary_records"
        assert 'fetch_article_details(pmids="41926003", output_format="json")' in result["summary_records"]["next_commands"]
        mock_client.find_collection_by_name.assert_not_awaited()
        mock_client.save_items.assert_not_awaited()
        mock_client.save_attachment.assert_not_awaited()
