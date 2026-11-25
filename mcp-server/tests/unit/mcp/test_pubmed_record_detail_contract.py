"""Contract: Keeper's summary-record guard matches the pinned PubMed Search MCP builders.

The pinned ``external/pubmed-search-mcp`` submodule (0.12.0+) renders the same
articles through its real request normalizer and JSON formatter: the default
``unified_search`` options (summary records) and ``options="full_records"``
(complete ``UnifiedArticle.to_dict()`` records). ``is_summary_record`` must
classify every rendered record correctly, and ``import_articles`` must refuse
the summary batch and import the complete one. A drift in the upstream summary
keys fails here instead of silently writing incomplete Zotero items.

The renderer runs in a subprocess with the submodule's ``src`` first on
``PYTHONPATH`` so it never collides with the ``pubmed_search`` package installed
in Keeper's environment.
"""

from __future__ import annotations

import json
import os
from pathlib import Path
import subprocess
import sys
from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pytest

from zotero_mcp.infrastructure.mcp.unified_import_tools import register_unified_import_tools
from zotero_mcp.infrastructure.mcp.unified_record_detail import SUMMARY_RECORD_KEYS, is_summary_record

PUBMED_SRC = Path(__file__).resolve().parents[4] / "external" / "pubmed-search-mcp" / "src"

RENDER_SCRIPT = r"""
import json

from pubmed_search.application.search.query_analyzer import AnalyzedQuery, QueryComplexity, QueryIntent
from pubmed_search.application.search.result_aggregator import AggregationStats
from pubmed_search.application.unified.request import normalize_unified_search_request
from pubmed_search.domain.entities.article import UnifiedArticle
from pubmed_search.domain.services.article_mapper import article_from_pubmed
from pubmed_search.presentation.mcp_server.tools.unified_formatting import _format_as_json

QUERY = "processed EEG AND post-anesthesia care unit"
pubmed_item = {
    "pmid": "41926003",
    "title": "Nociception index-monitored extubation in the post-anesthesia care unit: a randomized trial.",
    "authors": ["Investigator0 Surname0", "Investigator1 Surname1", "Investigator2 Surname2"],
    "abstract": "Extubation in the post-anesthesia care unit is a high-risk transition. " * 12,
    "journal": "Journal of clinical monitoring and computing",
    "year": "2026",
    "volume": "40",
    "issue": "4",
    "pages": "833-844",
    "doi": "10.1007/s10877-026-00001-0",
    "pmc_id": "PMC12345678",
    "keywords": ["Extubation", "PACU"],
    "mesh_terms": ["Humans", "Anesthesia Recovery Period"],
    "publication_types": ["Journal Article", "Randomized Controlled Trial"],
    "language": "eng",
}
no_pmc_item = dict(pubmed_item, pmid="41926004", doi=None, pmc_id=None, title="A PubMed record without a PMC copy.")
no_pmc_item["authors"] = []
articles = [
    article_from_pubmed(pubmed_item),
    article_from_pubmed(no_pmc_item),
    UnifiedArticle(
        title="An OpenAlex-only preprint",
        primary_source="openalex",
        openalex_id="W4400000000",
        abstract="Short abstract.",
    ),
]
analysis = AnalyzedQuery(
    original_query=QUERY,
    normalized_query=QUERY,
    complexity=QueryComplexity.MODERATE,
    intent=QueryIntent.COMPARISON,
)
stats = AggregationStats(total_input=len(articles), unique_articles=len(articles))
rendered = {}
for label, options in (("default", None), ("full_records", "full_records")):
    request = normalize_unified_search_request(query=QUERY, output_format="json", options=options)
    payload = json.loads(_format_as_json(articles, analysis, stats, record_detail=request.record_detail))
    rendered[label] = {
        "record_detail": request.record_detail,
        "record_detail_block": payload.get("record_detail"),
        "articles": payload["articles"],
    }
print(json.dumps(rendered))
"""


@pytest.fixture(scope="module")
def rendered() -> dict[str, Any]:
    builder = PUBMED_SRC / "pubmed_search" / "presentation" / "mcp_server" / "tools" / "unified_formatting.py"
    if not builder.exists():
        raise FileNotFoundError(f"Missing pubmed-search-mcp formatter: {builder} (git submodule update --init)")
    if "_summary_article_payload" not in builder.read_text(encoding="utf-8"):
        raise AssertionError("Pinned pubmed-search-mcp has no summary-record builder; the pin must be 0.12.0 or later")

    env = {**os.environ, "PYTHONPATH": str(PUBMED_SRC), "PYTHONDONTWRITEBYTECODE": "1"}
    completed = subprocess.run(
        [sys.executable, "-B", "-c", RENDER_SCRIPT],
        capture_output=True,
        check=False,
        env=env,
        text=True,
        encoding="utf-8",
        timeout=120,
    )
    assert completed.returncode == 0, completed.stderr[-4000:]
    return json.loads(completed.stdout.strip().splitlines()[-1])


def _register_import_articles(mock_client: AsyncMock):
    registered = {}
    mock_mcp = MagicMock()

    def tool_decorator():
        def wrapper(func):
            registered[func.__name__] = func
            return func

        return wrapper

    mock_mcp.tool = tool_decorator
    register_unified_import_tools(mock_mcp, mock_client)
    return registered["import_articles"]


def test_default_records_are_upstream_summary_records(rendered):
    default = rendered["default"]

    assert default["record_detail"] == "summary"
    assert default["record_detail_block"]["level"] == "summary"
    assert 'options="full_records"' in default["record_detail_block"]["full_records"]
    for record in default["articles"]:
        assert set(SUMMARY_RECORD_KEYS) <= set(record), "upstream summary keys drifted"
        assert not {"authors", "abstract"} & set(record)
        assert is_summary_record(record) is True


def test_full_records_option_yields_complete_records(rendered):
    full = rendered["full_records"]

    assert full["record_detail"] == "full"
    assert full["record_detail_block"] is None
    for record in full["articles"]:
        assert {"authors", "abstract", "identifiers"} <= set(record)
        assert not set(SUMMARY_RECORD_KEYS) & set(record)
        assert is_summary_record(record) is False


@pytest.mark.asyncio
async def test_import_articles_refuses_upstream_summaries_and_imports_full_records(rendered):
    mock_client = AsyncMock()
    mock_client.find_collection_by_name.return_value = {"key": "PACU0001", "data": {"name": "PACU"}}
    mock_client.save_items.return_value = {"success": True}
    import_articles = _register_import_articles(mock_client)

    refused = await import_articles(articles=rendered["default"]["articles"], collection_name="PACU", skip_duplicates=False)

    assert refused["success"] is False
    assert refused["error_code"] == "summary_records"
    assert refused["summary_records"]["pmids"] == ["41926003", "41926004"]
    assert refused["summary_records"]["without_pmid"] == [3]
    mock_client.save_items.assert_not_awaited()

    imported = await import_articles(articles=rendered["full_records"]["articles"], collection_name="PACU", skip_duplicates=False)

    assert imported["success"] is True, imported["errors"]
    assert imported["imported"] == 3
    saved = {item["title"]: item for item in mock_client.save_items.await_args.args[0]}
    lead = saved["Nociception index-monitored extubation in the post-anesthesia care unit: a randomized trial."]
    assert len(lead["creators"]) == 3
    assert lead["abstractNote"].startswith("Extubation in the post-anesthesia care unit")
    assert (lead["volume"], lead["issue"], lead["pages"]) == ("40", "4", "833-844")
    assert "PMCID: PMC12345678" in lead["extra"]
    # Records without a PMC copy, DOI or PMID carry null urls entries and still import.
    assert "creators" not in saved["A PubMed record without a PMC copy."]
    assert "OpenAlex: W4400000000" in saved["An OpenAlex-only preprint"]["extra"]
