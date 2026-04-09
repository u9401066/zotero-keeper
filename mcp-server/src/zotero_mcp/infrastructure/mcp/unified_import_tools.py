"""
Unified Import Tools for Zotero Keeper

This module provides a SINGLE unified entry point for importing articles from ANY source.

Architecture Decision (2026-01-12):
    Instead of having multiple import tools for different sources
    (import_ris_to_zotero, import_from_pmids, quick_import_pmids, etc.),
    we now have ONE tool: `import_articles`.

    This tool accepts the standardized article format from pubmed-search-mcp,
    making it easy to import from any source that MCP supports.

Supported Sources:
    - PubMed / Europe PMC / CORE / OpenAlex (via unified_search)
    - Detailed article metadata (via fetch_article_details)
    - CrossRef (via DOI lookup)
    - OpenAlex (via openalex_id lookup)
    - Semantic Scholar (via s2_id lookup)
    - Manual entry (direct dict input)
    - RIS text (parsed to articles)

Workflow:
    1. User searches with pubmed-search-mcp → gets articles
    2. Agent passes articles to zotero-keeper's import_articles
    3. Articles are converted to Zotero format and saved

Example:
    # From pubmed-search-mcp structured search result
    articles = [...]  # extracted from unified_search(..., output_format="json")

    # Import to Zotero
    result = await import_articles(
        articles=articles["articles"],
        collection_name="CRISPR Research",
        tags=["crispr", "2024"]
    )
"""

import logging
import re
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, ValidationError, field_validator

from .collection_support import apply_collection_and_tags, attach_saved_to_info, resolve_collection_target

logger = logging.getLogger(__name__)

MAX_IMPORT_ARTICLES = 100
SAVE_BATCH_SIZE = 50


class ArticleAuthorPayload(BaseModel):
    model_config = ConfigDict(extra="allow")

    name: str | None = None
    full_name: str | None = None
    display_name: str | None = None
    family_name: str | None = None
    given_name: str | None = None
    lastName: str | None = None
    firstName: str | None = None


class ArticleIdentifierPayload(BaseModel):
    model_config = ConfigDict(extra="allow")

    doi: str | int | None = None
    pmid: str | int | None = None
    pmc: str | int | None = None
    core_id: str | int | None = None
    openalex_id: str | int | None = None
    s2_id: str | int | None = None
    arxiv_id: str | int | None = None


class ArticleImportPayload(BaseModel):
    model_config = ConfigDict(extra="allow")

    title: str
    authors: list[str | ArticleAuthorPayload] = Field(default_factory=list)
    identifiers: ArticleIdentifierPayload = Field(default_factory=ArticleIdentifierPayload)
    citation_metrics: dict[str, Any] = Field(default_factory=dict)
    urls: dict[str, str] = Field(default_factory=dict)
    keywords: list[str] = Field(default_factory=list)
    mesh_terms: list[str] = Field(default_factory=list)
    abstract: str | None = None
    abstractNote: str | None = None
    journal: str | None = None
    publicationTitle: str | None = None
    volume: str | int | None = None
    issue: str | int | None = None
    pages: str | None = None
    year: str | int | None = None
    date: str | int | None = None
    publication_date: str | None = None
    doi: str | int | None = None
    DOI: str | int | None = None
    pmid: str | int | None = None
    pmc: str | int | None = None
    pmcid: str | int | None = None
    uid: str | int | None = None
    url: str | None = None
    language: str | None = None
    primary_source: str | None = None
    source: str | None = None
    article_type: str | None = None

    @field_validator("title", mode="before")
    @classmethod
    def _normalize_title(cls, value: Any) -> str:
        if value is None:
            raise ValueError("title is required")
        title = str(value).strip()
        if not title:
            raise ValueError("title must not be empty")
        return title

    @field_validator("authors", "keywords", "mesh_terms", mode="before")
    @classmethod
    def _normalize_optional_lists(cls, value: Any) -> Any:
        return [] if value is None else value

    @field_validator("identifiers", "citation_metrics", "urls", mode="before")
    @classmethod
    def _normalize_optional_dicts(cls, value: Any) -> Any:
        return {} if value is None else value


def _format_validation_error(error: ValidationError) -> str:
    first_error = error.errors(include_url=False)[0]
    location = ".".join(str(part) for part in first_error.get("loc", ()))
    message = first_error.get("msg", "Invalid article payload")
    return f"{location}: {message}" if location else message


def _validate_article_payload(article: Any) -> dict[str, Any]:
    if not isinstance(article, dict):
        raise TypeError("article must be an object/dict")

    validated_article = ArticleImportPayload.model_validate(article)
    return validated_article.model_dump(mode="python", exclude_none=True)


def _extract_article_pmid(article: dict[str, Any]) -> str | None:
    """Extract a normalized PMID from unified or legacy article formats."""
    identifiers = article.get("identifiers", {})
    if not isinstance(identifiers, dict):
        identifiers = {}

    pmid = identifiers.get("pmid") or article.get("pmid") or article.get("uid")
    if pmid is None:
        return None

    pmid_text = str(pmid).strip()
    return pmid_text or None


def _chunk_items(items: list[dict[str, Any]], chunk_size: int) -> list[list[dict[str, Any]]]:
    """Split import payloads into stable connector-sized batches."""
    return [items[index:index + chunk_size] for index in range(0, len(items), chunk_size)]


def _unified_article_to_zotero(article: dict[str, Any]) -> dict[str, Any]:
    """
    Convert unified article format to Zotero item format.

    Accepts both:
    - UnifiedArticle.to_dict() output from pubmed-search-mcp
    - Direct search result format (legacy compatibility)

    Args:
        article: Article dict from pubmed-search-mcp or similar format

    Returns:
        Zotero item dict ready for save_items()
    """
    # Initialize Zotero item
    item_type_map = {
        "journal-article": "journalArticle",
        "book": "book",
        "book-chapter": "bookSection",
        "conference-paper": "conferencePaper",
        "thesis": "thesis",
        "report": "report",
        "webpage": "webpage",
        "document": "document",
    }
    article_type = article.get("article_type")
    if not isinstance(article_type, str):
        article_type = ""
    item: dict[str, Any] = {
        "itemType": item_type_map.get(article_type, "journalArticle"),
    }

    # Title (required)
    item["title"] = article.get("title", "Unknown Title")

    # === Authors ===
    creators = []
    authors = article.get("authors", [])

    for author in authors:
        if isinstance(author, str):
            # Simple string format: "John Smith" or "Smith J"
            if "," in author:
                family, given = author.split(",", 1)
                creators.append(
                    {
                        "lastName": family.strip(),
                        "firstName": given.strip(),
                        "creatorType": "author",
                    }
                )
            else:
                parts = author.split()
                if len(parts) >= 2:
                    # Assume "FirstName LastName" or "LastName Initials"
                    if len(parts[-1]) <= 2:  # Likely "Smith J" format
                        creators.append(
                            {
                                "lastName": " ".join(parts[:-1]),
                                "firstName": parts[-1],
                                "creatorType": "author",
                            }
                        )
                    else:  # Likely "John Smith" format
                        creators.append(
                            {
                                "firstName": parts[0],
                                "lastName": " ".join(parts[1:]),
                                "creatorType": "author",
                            }
                        )
                else:
                    creators.append(
                        {
                            "lastName": author,
                            "firstName": "",
                            "creatorType": "author",
                        }
                    )
        elif isinstance(author, dict):
            # Dict format from UnifiedArticle
            name = author.get("name") or author.get("full_name") or author.get("display_name", "")
            family = author.get("family_name") or author.get("lastName", "")
            given = author.get("given_name") or author.get("firstName", "")

            if family or given:
                creators.append(
                    {
                        "lastName": family,
                        "firstName": given,
                        "creatorType": "author",
                    }
                )
            elif name:
                # Parse full name
                parts = name.split()
                if len(parts) >= 2:
                    creators.append(
                        {
                            "firstName": parts[0],
                            "lastName": " ".join(parts[1:]),
                            "creatorType": "author",
                        }
                    )
                else:
                    creators.append(
                        {
                            "lastName": name,
                            "firstName": "",
                            "creatorType": "author",
                        }
                    )

    if creators:
        item["creators"] = creators

    # === Identifiers ===
    # Handle both nested (UnifiedArticle.to_dict) and flat (legacy) formats
    identifiers = article.get("identifiers", {})

    # DOI
    doi = identifiers.get("doi") or article.get("doi") or article.get("DOI")
    if doi:
        # Clean DOI
        doi = doi.replace("https://doi.org/", "").replace("http://doi.org/", "")
        item["DOI"] = doi

    # PMID, PMCID in extra field
    extra_parts = []
    pmid = identifiers.get("pmid") or article.get("pmid") or article.get("uid")
    pmc = identifiers.get("pmc") or article.get("pmc") or article.get("pmcid")

    if pmid:
        extra_parts.append(f"PMID: {pmid}")
    if pmc:
        pmc_clean = pmc if pmc.startswith("PMC") else f"PMC{pmc}"
        extra_parts.append(f"PMCID: {pmc_clean}")

    # Other identifiers
    core_id = identifiers.get("core_id") or article.get("core_id")
    if core_id:
        extra_parts.append(f"CORE: {core_id}")

    openalex_id = identifiers.get("openalex_id") or article.get("openalex_id")
    if openalex_id:
        extra_parts.append(f"OpenAlex: {openalex_id}")

    s2_id = identifiers.get("s2_id") or article.get("s2_id")
    if s2_id:
        extra_parts.append(f"S2: {s2_id}")

    arxiv_id = identifiers.get("arxiv_id") or article.get("arxiv_id")
    if arxiv_id:
        extra_parts.append(f"arXiv: {arxiv_id}")

    # Source tracking
    primary_source = article.get("primary_source") or article.get("source")
    if primary_source:
        extra_parts.append(f"Source: {primary_source}")

    # Citation metrics (RCR)
    metrics = article.get("citation_metrics", {})
    if isinstance(metrics, dict):
        rcr = metrics.get("rcr") or metrics.get("relative_citation_ratio")
        if rcr:
            extra_parts.append(f"RCR: {rcr}")
        percentile = metrics.get("percentile") or metrics.get("nih_percentile")
        if percentile:
            extra_parts.append(f"Percentile: {percentile}")
        apt = metrics.get("apt")
        if apt:
            extra_parts.append(f"APT: {apt}")
        citation_count = metrics.get("citation_count")
        if citation_count:
            extra_parts.append(f"Citations: {citation_count}")

    if extra_parts:
        item["extra"] = "\n".join(extra_parts)

    # === Bibliographic ===
    # Abstract
    abstract = article.get("abstract") or article.get("abstractNote")
    if abstract:
        item["abstractNote"] = abstract

    # Journal
    journal = article.get("journal") or article.get("publicationTitle")
    if journal:
        item["publicationTitle"] = journal

    # Volume, Issue, Pages
    if article.get("volume"):
        item["volume"] = str(article["volume"])
    if article.get("issue"):
        item["issue"] = str(article["issue"])
    if article.get("pages"):
        item["pages"] = article["pages"]

    # Date/Year
    year = article.get("year") or article.get("date")
    if year:
        item["date"] = str(year)
    elif article.get("publication_date"):
        # ISO date format
        item["date"] = article["publication_date"][:10] if len(article["publication_date"]) >= 10 else article["publication_date"]

    # === URL ===
    # Prefer DOI URL, then PubMed, then provided URL
    urls = article.get("urls", {})
    url = urls.get("doi") or urls.get("pubmed") or urls.get("pmc") or article.get("url")
    if not url and doi:
        url = f"https://doi.org/{doi}"
    elif not url and pmid:
        url = f"https://pubmed.ncbi.nlm.nih.gov/{pmid}/"
    if url:
        item["url"] = url

    # === Tags ===
    # Combine keywords and MeSH terms
    tags = []
    for kw in article.get("keywords", [])[:10]:
        tags.append({"tag": kw})
    for mesh in article.get("mesh_terms", [])[:10]:
        if mesh not in [t["tag"] for t in tags]:
            tags.append({"tag": mesh})
    if tags:
        item["tags"] = tags

    # === Language ===
    if article.get("language"):
        item["language"] = article["language"]

    return item


def _parse_ris_to_articles(ris_text: str) -> list[dict[str, Any]]:
    """
    Parse RIS format text to article dicts.

    This reuses the existing RIS parser but returns unified format.
    """
    articles = []
    current_article: dict[str, Any] = {}
    current_authors: list[str] = []
    current_keywords: list[str] = []

    # RIS type to article type mapping
    type_map = {
        "JOUR": "journal-article",
        "BOOK": "book",
        "CHAP": "book-chapter",
        "CONF": "conference-paper",
        "THES": "thesis",
        "RPRT": "report",
    }

    for line in ris_text.strip().split("\n"):
        line = line.strip()
        if not line or len(line) < 6:
            continue

        match = re.match(r"^([A-Z][A-Z0-9])\s+-\s+(.*)$", line)
        if not match:
            continue

        tag, value = match.groups()
        value = value.strip()

        if tag == "TY":
            if current_article and current_article.get("title"):
                if current_authors:
                    current_article["authors"] = current_authors
                if current_keywords:
                    current_article["keywords"] = current_keywords
                articles.append(current_article)
            current_article = {
                "primary_source": "ris",
                "article_type": type_map.get(value, "journal-article"),
            }
            current_authors = []
            current_keywords = []
        elif tag == "ER":
            if current_article and current_article.get("title"):
                if current_authors:
                    current_article["authors"] = current_authors
                if current_keywords:
                    current_article["keywords"] = current_keywords
                articles.append(current_article)
            current_article = {}
            current_authors = []
            current_keywords = []
        elif tag in ("TI", "T1"):
            current_article["title"] = value
        elif tag in ("AU", "A1"):
            current_authors.append(value)
        elif tag in ("PY", "Y1"):
            current_article["year"] = value.split("/")[0]
        elif tag in ("JO", "JF", "T2"):
            current_article["journal"] = value
        elif tag == "VL":
            current_article["volume"] = value
        elif tag == "IS":
            current_article["issue"] = value
        elif tag == "SP":
            current_article["pages"] = value
        elif tag == "EP":
            if current_article.get("pages"):
                current_article["pages"] += f"-{value}"
            else:
                current_article["pages"] = value
        elif tag == "DO":
            current_article["doi"] = value
        elif tag == "AB":
            current_article["abstract"] = value
        elif tag == "KW":
            current_keywords.append(value)
        elif tag == "UR":
            current_article["url"] = value
        elif tag == "N1":
            # Notes - often contains PMID
            if "PMID:" in value or value.isdigit():
                pmid_match = re.search(r"(\d+)", value)
                if pmid_match:
                    current_article["pmid"] = pmid_match.group(1)

    # Don't forget last article
    if current_article and current_article.get("title"):
        if current_authors:
            current_article["authors"] = current_authors
        if current_keywords:
            current_article["keywords"] = current_keywords
        articles.append(current_article)

    return articles


def register_unified_import_tools(mcp, zotero_client):
    """
    Register the unified import tool.

    This is the SINGLE entry point for all imports to Zotero.
    """

    @mcp.tool()
    async def import_articles(
        articles: list[dict[str, Any]] | None = None,
        ris_text: str | None = None,
        collection_name: str | None = None,
        collection_key: str | None = None,
        tags: list[str] | None = None,
        skip_duplicates: bool = True,
    ) -> dict[str, Any]:
        """
        📥 Unified Import Tool - Import articles from ANY source to Zotero

        統一匯入工具 - 從任何來源匯入文章到 Zotero

        ⭐ THIS IS THE SINGLE TOOL FOR ALL IMPORTS:
        - Accepts articles from pubmed-search-mcp (any search tool)
        - Accepts RIS text (from prepare_export or external sources)
        - Automatically handles format conversion
        - Supports collection targeting with validation

        🔗 INTEGRATION WITH pubmed-search-mcp:
        Articles from these tools can be directly imported:
        - unified_search(..., output_format="json") → articles
        - fetch_article_details() → article
        - prepare_export(format="ris") → ris_text

        ⚠️ COLLECTION 防呆:
        - If collection_name/collection_key is specified but not found → ERROR
        - Returns available collections list for user to choose
        - If no collection specified → saves to library root (with warning)

        Args:
            articles: List of article dicts from pubmed-search-mcp
                     Format: UnifiedArticle.to_dict() or search result format
            ris_text: Alternative - RIS format text to parse and import
            collection_name: Target collection name (human-readable, recommended)
            collection_key: Target collection key (alternative)
            tags: Additional tags to add to all imported items
            skip_duplicates: If True (default), skip articles already in Zotero

        Returns:
            Import result with:
            - success: bool
            - imported: number of items imported
            - skipped: number of duplicates skipped
            - items: list of imported titles
            - saved_to: collection info or "My Library (root)"
            - errors: any errors encountered

        Example - From PubMed search:
            # Step 1: Search with pubmed-search-mcp
            results = await unified_search("machine learning anesthesia", output_format="json")

            # Step 2: Import to Zotero
            await import_articles(
                articles=results["articles"],
                collection_name="ML Anesthesia",
                tags=["ML", "review-2024"]
            )

        Example - From multi-source search:
            results = await unified_search("CRISPR", output_format="json")
            await import_articles(articles=results["articles"], collection_name="CRISPR OA")

        Example - From RIS text:
            ris = await prepare_export(pmids="12345678,87654321", format="ris")
            await import_articles(ris_text=ris["content"], collection_name="My Collection")
        """
        result: dict[str, Any] = {
            "success": False,
            "imported": 0,
            "skipped": 0,
            "items": [],
            "errors": [],
        }

        try:
            # === Step 1: Validate input ===
            if not articles and not ris_text:
                result["error"] = "Must provide either 'articles' or 'ris_text'"
                result["hint"] = "Use unified_search(..., output_format=\"json\") or fetch_article_details() to get articles, then pass them here"
                return result

            # === Step 2: Parse RIS if provided ===
            if ris_text and not articles:
                articles = _parse_ris_to_articles(ris_text)
                if not articles:
                    result["error"] = "No valid articles found in RIS text"
                    return result
                logger.info(f"Parsed {len(articles)} articles from RIS text")

            articles = articles or []

            if len(articles) > MAX_IMPORT_ARTICLES:
                result["error"] = f"Too many articles provided ({len(articles)}). Maximum supported per import is {MAX_IMPORT_ARTICLES}."
                result["hint"] = f"Split the import into batches of {MAX_IMPORT_ARTICLES} articles or fewer."
                return result

            resolution = await resolve_collection_target(
                zotero_client,
                collection_name=collection_name,
                collection_key=collection_key,
            )
            if not resolution["success"]:
                result.update(resolution)
                return result

            target_key = resolution["target_key"]
            target_name = resolution["target_name"]

            # === Step 4: Convert articles to Zotero format ===
            converted_items: list[tuple[dict[str, Any], dict[str, Any]]] = []
            for article_index, article in enumerate(articles, start=1):
                try:
                    validated_article = _validate_article_payload(article)
                    zotero_item = _unified_article_to_zotero(validated_article)

                    converted_items.append(
                        (
                            validated_article,
                            apply_collection_and_tags(zotero_item, collection_key=target_key, tags=tags),
                        )
                    )
                except ValidationError as e:
                    article_title = article.get("title", "Unknown")[:50] if isinstance(article, dict) else "Unknown"
                    result["errors"].append(
                        {
                            "article": article_index,
                            "title": article_title,
                            "error": f"Invalid article schema: {_format_validation_error(e)}",
                        }
                    )
                except TypeError as e:
                    result["errors"].append(
                        {
                            "article": article_index,
                            "title": "Unknown",
                            "error": f"Invalid article schema: {e}",
                        }
                    )
                except Exception as e:
                    result["errors"].append(
                        {
                            "article": article_index,
                            "title": article.get("title", "Unknown")[:50] if isinstance(article, dict) else "Unknown",
                            "error": str(e),
                        }
                    )

            if not converted_items:
                result["error"] = "No valid articles to import"
                return result

            # === Step 5: Duplicate check (optional) ===
            items_to_import = [item for _, item in converted_items]
            skipped_count = 0

            if skip_duplicates:
                try:
                    pmids_to_check = [pmid for article, _ in converted_items if (pmid := _extract_article_pmid(article))]
                    dois_to_check = [
                        doi.lower().strip()
                        for _, item in converted_items
                        if (doi := item.get("DOI"))
                    ]

                    duplicate_check = await zotero_client.batch_check_identifiers(
                        pmids=pmids_to_check,
                        dois=dois_to_check,
                    )
                    existing_pmids = set(duplicate_check.get("existing_pmids", set()))
                    existing_dois = set(duplicate_check.get("existing_dois", set()))

                    filtered_items = []
                    for article, item in converted_items:
                        pmid = _extract_article_pmid(article)
                        doi = item.get("DOI", "").lower().strip()

                        if (pmid and pmid in existing_pmids) or (doi and doi in existing_dois):
                            skipped_count += 1
                            continue
                        filtered_items.append(item)

                    items_to_import = filtered_items
                except Exception as e:
                    logger.warning(f"Duplicate check failed, importing all: {e}")

            # === Step 6: Save to Zotero ===
            saved_items: list[dict[str, Any]] = []
            batch_failures = 0
            if items_to_import:
                for batch_index, batch in enumerate(_chunk_items(items_to_import, SAVE_BATCH_SIZE), start=1):
                    try:
                        await zotero_client.save_items(batch)
                        saved_items.extend(batch)
                    except Exception as e:
                        batch_failures += 1
                        logger.error(f"Import batch {batch_index} failed: {e}")
                        result["errors"].append(
                            {
                                "batch": batch_index,
                                "count": len(batch),
                                "items": [item.get("title", "Untitled")[:50] for item in batch],
                                "error": str(e),
                            }
                        )

            # === Step 7: Build response ===
            result["imported"] = len(saved_items)
            result["skipped"] = skipped_count
            result["items"] = [item.get("title", "Untitled")[:50] for item in saved_items]

            if batch_failures:
                result["success"] = False
                if saved_items:
                    result["partial_success"] = True
                    result["error"] = f"Imported {len(saved_items)} articles, but {batch_failures} batch(es) failed"
                    result["message"] = result["error"]
                else:
                    result["error"] = "Failed to import articles to Zotero"
                    result["message"] = result["error"]
                    return result
            else:
                result["success"] = True
                result["message"] = f"Successfully imported {len(saved_items)} articles to Zotero"

            if skipped_count > 0:
                result["message"] += f" ({skipped_count} duplicates skipped)"

            # Collection info
            return attach_saved_to_info(result, target_key=target_key, target_name=target_name)

        except Exception as e:
            logger.error(f"Import failed: {e}")
            result["error"] = str(e)
            return result

    logger.info("Unified import tool registered (import_articles)")
