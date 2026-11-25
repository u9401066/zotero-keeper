"""Recognize pubmed-search-mcp summary records before they reach Zotero.

pubmed-search-mcp 0.12.0 changed ``unified_search(..., output_format="json")``:
each entry of ``articles`` is an agent-sized *summary record* by default
(``first_author`` plus ``author_count``, a 400-character ``abstract_snippet``
with ``abstract_truncated``; no author list, full abstract, volume/issue/pages,
MeSH terms or keywords). Complete ``UnifiedArticle.to_dict()`` records need the
explicit ``options="full_records"``. Importing a summary record would create a
Zotero item without its authors and with a truncated or missing abstract, so
the import tools refuse such records and name the calls that return complete
ones.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any

SUMMARY_RECORD_KEYS: tuple[str, ...] = ("abstract_snippet", "abstract_truncated", "author_count")
"""Keys that only pubmed-search-mcp's summary projection emits for article records.

``_summary_article_payload`` always writes all three; ``UnifiedArticle.to_dict()``
never writes any of them. ``first_author`` is deliberately not a marker:
citation-network nodes, timeline milestones and reference-verification matches
carry it too, and their import behaviour is unchanged.
"""

FULL_RECORD_AUTHORS_KEY = "authors"
FULL_RECORD_ABSTRACT_KEYS: tuple[str, ...] = ("abstract", "abstractNote")

SUMMARY_RECORD_CODE = "summary_record"
SUMMARY_RECORDS_ERROR_CODE = "summary_records"
SUMMARY_RECORDS_ERROR = "Summary records cannot be imported: they lack the author list and full abstract"

FULL_RECORDS_SEARCH_CALL = 'unified_search(..., output_format="json", options="full_records")'
FETCH_DETAILS_CALL = 'fetch_article_details(pmids="...", output_format="json")'

SUMMARY_RECORD_HINT = (
    "These are pubmed-search-mcp unified_search summary records (first_author/author_count and a "
    "400-character abstract_snippet; no author list, full abstract, volume/issue/pages or MeSH terms). "
    "Importing them would create incomplete Zotero items, so nothing was written for them. "
    f"Repeat the search with {FULL_RECORDS_SEARCH_CALL} and pass those articles, or fetch the "
    f"selected PMIDs with {FETCH_DETAILS_CALL} and pass its articles."
)


def is_summary_record(article: Any) -> bool:
    """Return whether ``article`` is a summary record that lacks the complete fields.

    A record is summary-shaped when it carries any of :data:`SUMMARY_RECORD_KEYS`
    and does not also carry both the full ``authors`` list and a full abstract
    (``abstract`` or ``abstractNote``), the fields ``UnifiedArticle.to_dict()``
    always emits (possibly empty). Complete records, RIS-parsed records and
    hand-built dicts without summary keys are therefore never affected.
    """
    if not isinstance(article, Mapping):
        return False
    if not any(key in article for key in SUMMARY_RECORD_KEYS):
        return False
    has_author_list = FULL_RECORD_AUTHORS_KEY in article
    has_full_abstract = any(key in article for key in FULL_RECORD_ABSTRACT_KEYS)
    return not (has_author_list and has_full_abstract)


def _identifier(article: Mapping[str, Any], key: str) -> str | None:
    identifiers = article.get("identifiers")
    value = (identifiers.get(key) if isinstance(identifiers, Mapping) else None) or article.get(key)
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _title(article: Mapping[str, Any]) -> str:
    title = article.get("title")
    return str(title)[:50] if title else "Unknown"


def summary_record_error(article_index: int, article: Mapping[str, Any]) -> dict[str, Any]:
    """Build the per-record error for one refused summary record (1-based index)."""
    error: dict[str, Any] = {
        "article": article_index,
        "title": _title(article),
        "code": SUMMARY_RECORD_CODE,
        "error": "Summary record (no author list or full abstract); not imported",
    }
    for key in ("pmid", "doi"):
        value = _identifier(article, key)
        if value:
            error[key] = value
    return error


def summary_record_guidance(records: Sequence[tuple[int, Mapping[str, Any]]]) -> dict[str, Any]:
    """Summarize refused summary records and the calls that return complete ones.

    ``records`` holds ``(1-based article index, article)`` pairs. Records with a
    PMID can be completed with ``fetch_article_details``; records without one
    (for example OpenAlex-only results) need the ``full_records`` search.
    """
    pmids: list[str] = []
    without_pmid: list[int] = []
    for article_index, article in records:
        pmid = _identifier(article, "pmid")
        if pmid is None:
            without_pmid.append(article_index)
        elif pmid not in pmids:
            pmids.append(pmid)

    next_commands = [FULL_RECORDS_SEARCH_CALL]
    if pmids:
        next_commands.append(f'fetch_article_details(pmids="{",".join(pmids)}", output_format="json")')

    return {
        "count": len(records),
        "articles": [article_index for article_index, _ in records],
        "pmids": pmids,
        "without_pmid": without_pmid,
        "hint": SUMMARY_RECORD_HINT,
        "next_commands": next_commands,
    }


def summary_records_refusal(records: Sequence[tuple[int, Mapping[str, Any]]]) -> dict[str, Any]:
    """Return the typed fields of a refusal when every supplied record is a summary record."""
    return {
        "error": SUMMARY_RECORDS_ERROR,
        "error_code": SUMMARY_RECORDS_ERROR_CODE,
        "hint": SUMMARY_RECORD_HINT,
        "summary_records": summary_record_guidance(records),
    }
