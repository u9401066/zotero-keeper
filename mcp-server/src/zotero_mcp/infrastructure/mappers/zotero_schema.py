"""
Zotero Item Type Schema & Type-Aware Mapping Helpers

Zotero stores different bibliographic item types (journal articles, books, book
chapters, conference papers, theses, reports, web pages, preprints, software,
datasets, ...) and each type has a *different* set of valid fields.

If we send a field that is not valid for the target item type, Zotero silently
drops it and the metadata is lost. This module provides:

* ``ZOTERO_ITEM_FIELDS``    - the authoritative set of valid fields per item type
                              (sourced from the Zotero schema API).
* ``CONTAINER_FIELD``       - where the "container/venue" title goes per type
                              (journal -> publicationTitle, chapter -> bookTitle,
                              conference -> proceedingsTitle, ...).
* ``ZOTERO_PRIMARY_CREATOR``- the primary creator role per type
                              (software uses "programmer", not "author").
* ``detect_item_type()``    - robustly infer the best Zotero item type from any
                              source vocabulary (CrossRef / OpenAlex / RIS /
                              PubMed / BibTeX) plus identifier/field heuristics.
* ``finalize_item_for_schema()`` - keep only fields valid for the detected type
                              and preserve everything else in the ``extra`` field
                              so no metadata is ever lost.

Field lists verified against https://api.zotero.org/itemTypeFields?itemType=...
"""

from __future__ import annotations

from typing import Any

# ---------------------------------------------------------------------------
# Valid fields per Zotero item type (verified against the Zotero schema API).
# ---------------------------------------------------------------------------
ZOTERO_ITEM_FIELDS: dict[str, frozenset[str]] = {
    "journalArticle": frozenset(
        {
            "title",
            "abstractNote",
            "publicationTitle",
            "publisher",
            "place",
            "date",
            "volume",
            "issue",
            "section",
            "partNumber",
            "partTitle",
            "pages",
            "series",
            "seriesTitle",
            "seriesText",
            "journalAbbreviation",
            "DOI",
            "citationKey",
            "url",
            "accessDate",
            "PMID",
            "PMCID",
            "ISSN",
            "archive",
            "archiveLocation",
            "shortTitle",
            "language",
            "libraryCatalog",
            "callNumber",
            "rights",
            "extra",
        }
    ),
    "book": frozenset(
        {
            "title",
            "abstractNote",
            "series",
            "seriesNumber",
            "volume",
            "numberOfVolumes",
            "edition",
            "date",
            "publisher",
            "place",
            "originalDate",
            "originalPublisher",
            "originalPlace",
            "format",
            "numPages",
            "ISBN",
            "DOI",
            "citationKey",
            "url",
            "accessDate",
            "ISSN",
            "archive",
            "archiveLocation",
            "shortTitle",
            "language",
            "libraryCatalog",
            "callNumber",
            "rights",
            "extra",
        }
    ),
    "bookSection": frozenset(
        {
            "title",
            "abstractNote",
            "bookTitle",
            "series",
            "seriesNumber",
            "volume",
            "numberOfVolumes",
            "edition",
            "date",
            "publisher",
            "place",
            "originalDate",
            "originalPublisher",
            "originalPlace",
            "format",
            "pages",
            "ISBN",
            "DOI",
            "citationKey",
            "url",
            "accessDate",
            "ISSN",
            "archive",
            "archiveLocation",
            "shortTitle",
            "language",
            "libraryCatalog",
            "callNumber",
            "rights",
            "extra",
        }
    ),
    "conferencePaper": frozenset(
        {
            "title",
            "abstractNote",
            "proceedingsTitle",
            "conferenceName",
            "publisher",
            "place",
            "date",
            "eventPlace",
            "volume",
            "issue",
            "numberOfVolumes",
            "pages",
            "series",
            "seriesNumber",
            "DOI",
            "ISBN",
            "citationKey",
            "url",
            "accessDate",
            "ISSN",
            "archive",
            "archiveLocation",
            "shortTitle",
            "language",
            "libraryCatalog",
            "callNumber",
            "rights",
            "extra",
        }
    ),
    "thesis": frozenset(
        {
            "title",
            "abstractNote",
            "thesisType",
            "university",
            "place",
            "date",
            "series",
            "seriesNumber",
            "numPages",
            "DOI",
            "ISBN",
            "citationKey",
            "url",
            "accessDate",
            "ISSN",
            "archive",
            "archiveLocation",
            "shortTitle",
            "language",
            "libraryCatalog",
            "callNumber",
            "rights",
            "extra",
        }
    ),
    "report": frozenset(
        {
            "title",
            "abstractNote",
            "reportNumber",
            "reportType",
            "institution",
            "place",
            "date",
            "seriesTitle",
            "seriesNumber",
            "pages",
            "DOI",
            "ISBN",
            "citationKey",
            "url",
            "accessDate",
            "ISSN",
            "archive",
            "archiveLocation",
            "shortTitle",
            "language",
            "libraryCatalog",
            "callNumber",
            "rights",
            "extra",
        }
    ),
    "webpage": frozenset(
        {
            "title",
            "abstractNote",
            "websiteTitle",
            "websiteType",
            "date",
            "publisher",
            "place",
            "DOI",
            "citationKey",
            "url",
            "accessDate",
            "shortTitle",
            "language",
            "rights",
            "extra",
        }
    ),
    "preprint": frozenset(
        {
            "title",
            "abstractNote",
            "genre",
            "repository",
            "archiveID",
            "place",
            "date",
            "series",
            "seriesNumber",
            "DOI",
            "citationKey",
            "url",
            "accessDate",
            "archive",
            "archiveLocation",
            "shortTitle",
            "language",
            "libraryCatalog",
            "callNumber",
            "rights",
            "extra",
        }
    ),
    "computerProgram": frozenset(
        {
            "title",
            "abstractNote",
            "seriesTitle",
            "versionNumber",
            "date",
            "system",
            "company",
            "place",
            "programmingLanguage",
            "rights",
            "citationKey",
            "url",
            "accessDate",
            "DOI",
            "ISBN",
            "archive",
            "archiveLocation",
            "libraryCatalog",
            "callNumber",
            "shortTitle",
            "extra",
        }
    ),
    "manuscript": frozenset(
        {
            "title",
            "abstractNote",
            "manuscriptType",
            "institution",
            "place",
            "date",
            "numPages",
            "number",
            "DOI",
            "citationKey",
            "url",
            "accessDate",
            "archive",
            "archiveLocation",
            "shortTitle",
            "language",
            "libraryCatalog",
            "callNumber",
            "rights",
            "extra",
        }
    ),
    "magazineArticle": frozenset(
        {
            "title",
            "abstractNote",
            "publicationTitle",
            "publisher",
            "place",
            "date",
            "volume",
            "issue",
            "pages",
            "ISSN",
            "DOI",
            "citationKey",
            "url",
            "accessDate",
            "archive",
            "archiveLocation",
            "shortTitle",
            "language",
            "libraryCatalog",
            "callNumber",
            "rights",
            "extra",
        }
    ),
    "newspaperArticle": frozenset(
        {
            "title",
            "abstractNote",
            "publicationTitle",
            "publisher",
            "place",
            "date",
            "volume",
            "issue",
            "edition",
            "section",
            "pages",
            "ISSN",
            "DOI",
            "citationKey",
            "url",
            "accessDate",
            "archive",
            "archiveLocation",
            "shortTitle",
            "language",
            "libraryCatalog",
            "callNumber",
            "rights",
            "extra",
        }
    ),
    "dataset": frozenset(
        {
            "title",
            "abstractNote",
            "identifier",
            "type",
            "versionNumber",
            "date",
            "repository",
            "repositoryLocation",
            "format",
            "DOI",
            "citationKey",
            "url",
            "accessDate",
            "archive",
            "archiveLocation",
            "shortTitle",
            "language",
            "libraryCatalog",
            "callNumber",
            "rights",
            "extra",
        }
    ),
    "document": frozenset(
        {
            "title",
            "abstractNote",
            "type",
            "date",
            "publisher",
            "place",
            "DOI",
            "citationKey",
            "url",
            "accessDate",
            "archive",
            "archiveLocation",
            "shortTitle",
            "language",
            "libraryCatalog",
            "callNumber",
            "rights",
            "extra",
        }
    ),
}

# Where the "container / venue" title is stored for each item type.
# Types not listed here have no single container field (e.g. book, thesis).
CONTAINER_FIELD: dict[str, str] = {
    "journalArticle": "publicationTitle",
    "magazineArticle": "publicationTitle",
    "newspaperArticle": "publicationTitle",
    "bookSection": "bookTitle",
    "conferencePaper": "proceedingsTitle",
}

# Primary creator role per item type. Anything not listed defaults to "author".
ZOTERO_PRIMARY_CREATOR: dict[str, str] = {
    "computerProgram": "programmer",
}

# Structural keys that are part of the Zotero save payload but are not schema
# "fields" - always preserved verbatim by ``finalize_item_for_schema``.
_STRUCTURAL_KEYS = frozenset({"itemType", "title", "creators", "tags", "collections", "relations", "notes"})

# Human-friendly labels used when an unsupported field is preserved in ``extra``.
_EXTRA_FIELD_LABELS: dict[str, str] = {
    "publicationTitle": "Publication",
    "journalAbbreviation": "Journal Abbreviation",
    "ISSN": "ISSN",
    "ISBN": "ISBN",
    "conferenceName": "Conference Name",
    "proceedingsTitle": "Proceedings Title",
    "bookTitle": "Book Title",
    "volume": "Volume",
    "issue": "Issue",
    "pages": "Pages",
    "publisher": "Publisher",
    "place": "Place",
    "series": "Series",
    "seriesNumber": "Series Number",
    "edition": "Edition",
    "numPages": "Number of Pages",
    "language": "Language",
    "libraryCatalog": "Library Catalog",
    "institution": "Institution",
    "university": "University",
    "repository": "Repository",
    "versionNumber": "Version",
    "programmingLanguage": "Programming Language",
    "websiteTitle": "Website Title",
    "websiteType": "Website Type",
    "system": "System",
    "company": "Company",
    "reportNumber": "Report Number",
    "reportType": "Report Type",
    "thesisType": "Thesis Type",
}

# Map of source-vocabulary type tokens -> Zotero item type.
# Tokens are normalized (lowercase, spaces/underscores -> hyphens) before lookup.
# NOTE: PubMed publication types such as review / meta-analysis / clinical-trial
# are still *journal articles* in Zotero, so they map to journalArticle.
_TYPE_ALIASES: dict[str, str] = {
    # --- Journal article (+ PubMed publication types) ---
    "journal-article": "journalArticle",
    "journal": "journalArticle",
    "journalarticle": "journalArticle",
    "article": "journalArticle",
    "article-journal": "journalArticle",
    "research-article": "journalArticle",
    "review": "journalArticle",
    "meta-analysis": "journalArticle",
    "systematic-review": "journalArticle",
    "clinical-trial": "journalArticle",
    "randomized-controlled-trial": "journalArticle",
    "case-report": "journalArticle",
    "case-reports": "journalArticle",
    "letter": "journalArticle",
    "editorial": "journalArticle",
    "comment": "journalArticle",
    "jour": "journalArticle",
    # --- Conference paper ---
    "conference-paper": "conferencePaper",
    "proceedings-article": "conferencePaper",
    "paper-conference": "conferencePaper",
    "conference": "conferencePaper",
    "inproceedings": "conferencePaper",
    "proceedings": "conferencePaper",
    "conf": "conferencePaper",
    "cpaper": "conferencePaper",
    # --- Book ---
    "book": "book",
    "monograph": "book",
    "reference-book": "book",
    "edited-book": "book",
    "book-whole": "book",
    # --- Book section / chapter ---
    "book-chapter": "bookSection",
    "book-section": "bookSection",
    "book-part": "bookSection",
    "chapter": "bookSection",
    "incollection": "bookSection",
    "inbook": "bookSection",
    "chap": "bookSection",
    # --- Thesis ---
    "thesis": "thesis",
    "dissertation": "thesis",
    "phdthesis": "thesis",
    "mastersthesis": "thesis",
    # --- Report ---
    "report": "report",
    "report-component": "report",
    "tech-report": "report",
    "techreport": "report",
    "working-paper": "report",
    "rprt": "report",
    # --- Web page ---
    "webpage": "webpage",
    "web-page": "webpage",
    "website": "webpage",
    "online": "webpage",
    "blog-post": "webpage",
    "post-weblog": "webpage",
    "elec": "webpage",
    # --- Preprint ---
    "preprint": "preprint",
    "posted-content": "preprint",
    # --- Software / repository ---
    "computer-program": "computerProgram",
    "computerprogram": "computerProgram",
    "software": "computerProgram",
    "program": "computerProgram",
    "code": "computerProgram",
    # --- Dataset ---
    "dataset": "dataset",
    "data": "dataset",
    "database": "dataset",
    # --- Magazine / newspaper ---
    "magazine-article": "magazineArticle",
    "magazine": "magazineArticle",
    "article-magazine": "magazineArticle",
    "newspaper-article": "newspaperArticle",
    "newspaper": "newspaperArticle",
    "article-newspaper": "newspaperArticle",
    # --- Manuscript (often old / scanned / unpublished works) ---
    "manuscript": "manuscript",
    "unpublished": "manuscript",
    # --- Generic document ---
    "document": "document",
    "misc": "document",
}

# Hosts that indicate a code repository (-> computerProgram).
_REPOSITORY_HOSTS = (
    "github.com",
    "gitlab.com",
    "bitbucket.org",
    "sourceforge.net",
    "codeberg.org",
    "gitee.com",
)


def is_known_item_type(item_type: str) -> bool:
    """Return True if ``item_type`` is a Zotero type known to this module."""
    return item_type in ZOTERO_ITEM_FIELDS


def _normalize_type_token(value: Any) -> str:
    """Normalize a source type token for alias lookup."""
    if not isinstance(value, str):
        return ""
    return value.strip().lower().replace("_", "-").replace(" ", "-")


def _first_url(article: dict[str, Any]) -> str | None:
    """Return the most representative URL for the article, if any."""
    url = article.get("url")
    if isinstance(url, str) and url.strip():
        return url
    urls = article.get("urls")
    if isinstance(urls, dict):
        for value in urls.values():
            if isinstance(value, str) and value.strip():
                return value
    return None


def _looks_like_repository(url: str) -> bool:
    """Return True if the URL points at a known code-repository host."""
    lowered = url.lower()
    return any(host in lowered for host in _REPOSITORY_HOSTS)


def detect_item_type(article: dict[str, Any]) -> str:
    """
    Infer the most appropriate Zotero item type for an article.

    Resolution order:
        1. Explicit, already-valid Zotero ``itemType`` / ``item_type``.
        2. Known source-vocabulary type token (CrossRef / OpenAlex / RIS /
           PubMed / BibTeX) via ``_TYPE_ALIASES``.
        3. Identifier / characteristic-field heuristics (arXiv -> preprint,
           repo URL -> computerProgram, conference fields -> conferencePaper,
           ISBN without journal -> book/bookSection, website fields -> webpage).
        4. Sensible defaults (journalArticle when journal/PMID present,
           webpage for bare URLs, otherwise document).
    """
    # 1) Explicit, already-valid Zotero item type
    explicit = article.get("itemType") or article.get("item_type")
    if isinstance(explicit, str) and explicit in ZOTERO_ITEM_FIELDS:
        return explicit

    # 2) Known type vocabularies
    raw_type = article.get("article_type") or article.get("type") or article.get("genre")
    mapped = _TYPE_ALIASES.get(_normalize_type_token(raw_type))
    if mapped:
        return mapped

    identifiers = article.get("identifiers")
    if not isinstance(identifiers, dict):
        identifiers = {}

    # 3) Heuristics
    if identifiers.get("arxiv_id") or article.get("arxiv_id"):
        return "preprint"

    url = _first_url(article)
    if url and _looks_like_repository(url):
        return "computerProgram"

    if (
        article.get("conference_name")
        or article.get("conferenceName")
        or article.get("proceedings_title")
        or article.get("proceedingsTitle")
    ):
        return "conferencePaper"

    if article.get("website_title") or article.get("websiteTitle"):
        return "webpage"

    has_journal = bool(article.get("journal") or article.get("publicationTitle") or article.get("container_title") or article.get("venue"))
    has_isbn = bool(article.get("isbn") or article.get("ISBN"))
    if has_isbn and not has_journal:
        if article.get("book_title") or article.get("bookTitle") or article.get("chapter"):
            return "bookSection"
        return "book"

    has_doi = bool(identifiers.get("doi") or article.get("doi") or article.get("DOI"))
    has_pmid = bool(identifiers.get("pmid") or article.get("pmid") or article.get("uid"))

    # 4) Defaults
    if has_journal or has_pmid:
        return "journalArticle"
    if url and not has_doi:
        return "webpage"
    if has_doi:
        return "journalArticle"
    return "document"


def finalize_item_for_schema(item: dict[str, Any]) -> dict[str, Any]:
    """
    Drop fields that are invalid for the item's type, preserving them in ``extra``.

    This guarantees the Zotero Connector API never silently discards metadata:
    any field not valid for the detected item type is appended to the ``extra``
    field as a ``Label: value`` line instead of being lost.

    Empty values ("" / None / [] / {}) are removed entirely.
    """
    item_type = item.get("itemType", "document")
    valid_fields = ZOTERO_ITEM_FIELDS.get(item_type)
    if valid_fields is None:
        # Unknown type - return as-is rather than risk corrupting the payload.
        return item

    cleaned: dict[str, Any] = {"itemType": item_type}
    extra_lines: list[str] = []
    existing_extra = ""

    for key, value in item.items():
        if key == "itemType":
            continue
        if key in _STRUCTURAL_KEYS:
            cleaned[key] = value
            continue
        if key == "extra":
            existing_extra = value or ""
            continue
        if value in (None, "", [], {}):
            continue
        if key in valid_fields:
            cleaned[key] = value
        else:
            label = _EXTRA_FIELD_LABELS.get(key, key)
            extra_lines.append(f"{label}: {value}")

    combined_extra = existing_extra
    if extra_lines:
        addition = "\n".join(extra_lines)
        combined_extra = f"{existing_extra}\n{addition}".strip() if existing_extra else addition
    if combined_extra:
        cleaned["extra"] = combined_extra

    return cleaned
