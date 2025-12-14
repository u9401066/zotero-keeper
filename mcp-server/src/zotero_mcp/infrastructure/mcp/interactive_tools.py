"""
Interactive Save Tools with MCP Elicitation

Uses MCP Elicitation feature to interactively ask users to select collections
when saving references. This provides a much better UX than two-phase save.

Key Features:
- Mid-tool user input via ctx.elicit()
- Collection selection with numbered options
- Duplicate detection with confirmation
- Validation with user feedback
- **Auto-fetch complete metadata from DOI/PMID** ✨ 重要！

🔒 DATA INTEGRITY GUARANTEE:
   When DOI or PMID is provided, this tool will automatically fetch
   complete article metadata (including abstract) from external APIs.
   This ensures ALL saved references have full metadata!
"""

import logging
from typing import Any

from mcp.server.fastmcp import Context
from mcp.server.session import ServerSession
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


# =============================================================================
# Auto-fetch Metadata Functions (Data Integrity Guarantee)
# =============================================================================

async def _fetch_metadata_from_pmid(pmid: str, include_citation_metrics: bool = True) -> dict | None:
    """
    Fetch complete article metadata from PubMed using PMID.

    Returns Zotero-compatible item dict with all fields including abstract.
    Optionally includes citation metrics (RCR) from iCite.

    Args:
        pmid: PubMed ID
        include_citation_metrics: If True, fetch RCR/percentile from iCite (default: True)

    Returns:
        Zotero-compatible item dict, or None if fetch fails
    """
    try:
        from ..mappers.pubmed_mapper import pubmed_to_zotero_item
        from ..pubmed import fetch_pubmed_articles, enrich_articles_with_metrics

        articles = fetch_pubmed_articles([pmid])
        if articles:
            article = articles[0]

            # Enrich with citation metrics (RCR) if requested
            if include_citation_metrics:
                enrich_articles_with_metrics([article], [pmid])
                if article.get("relative_citation_ratio"):
                    logger.info(f"✅ RCR {article['relative_citation_ratio']:.2f} for PMID {pmid}")

            zotero_item = pubmed_to_zotero_item(article)
            logger.info(f"Fetched complete metadata from PMID {pmid}")
            return zotero_item
    except Exception as e:
        logger.warning(f"Failed to fetch metadata from PMID {pmid}: {e}")
    return None


async def _fetch_metadata_from_doi(doi: str) -> dict | None:
    """
    Fetch complete article metadata from CrossRef using DOI.

    Returns Zotero-compatible item dict with all fields including abstract.
    """
    import httpx

    try:
        url = f"https://api.crossref.org/works/{doi}"
        async with httpx.AsyncClient(timeout=10) as client:
            response = await client.get(url)

        if response.status_code != 200:
            return None

        data = response.json().get("message", {})

        # Convert CrossRef format to Zotero format
        item = {
            "itemType": "journalArticle",
            "title": " ".join(data.get("title", [])),
            "DOI": doi,
        }

        # Abstract
        abstract = data.get("abstract", "")
        if abstract:
            # Remove HTML tags
            import re
            abstract = re.sub(r'<[^>]+>', '', abstract)
            item["abstractNote"] = abstract

        # Authors
        authors = data.get("author", [])
        if authors:
            item["creators"] = [
                {
                    "creatorType": "author",
                    "firstName": a.get("given", ""),
                    "lastName": a.get("family", ""),
                }
                for a in authors
            ]

        # Journal
        containers = data.get("container-title", [])
        if containers:
            item["publicationTitle"] = containers[0]

        # Date
        published = data.get("published", {}).get("date-parts", [[]])
        if published and published[0]:
            date_parts = published[0]
            if len(date_parts) >= 1:
                item["date"] = str(date_parts[0])  # Year
                if len(date_parts) >= 2:
                    item["date"] = f"{date_parts[0]}-{date_parts[1]:02d}"
                if len(date_parts) >= 3:
                    item["date"] = f"{date_parts[0]}-{date_parts[1]:02d}-{date_parts[2]:02d}"

        # Volume, Issue, Pages
        if data.get("volume"):
            item["volume"] = data["volume"]
        if data.get("issue"):
            item["issue"] = data["issue"]
        if data.get("page"):
            item["pages"] = data["page"]

        # URL
        if data.get("URL"):
            item["url"] = data["URL"]

        logger.info(f"Fetched complete metadata from DOI {doi}")
        return item

    except Exception as e:
        logger.warning(f"Failed to fetch metadata from DOI {doi}: {e}")
    return None


def _merge_metadata(user_input: dict, fetched: dict) -> dict:
    """
    Merge user-provided data with fetched metadata.

    User-provided data takes priority, fetched data fills gaps.
    This ensures:
    1. User's explicit values are preserved
    2. Missing fields (especially abstract!) are filled from API
    """
    result = fetched.copy()

    for key, value in user_input.items():
        if value is not None and value != "" and value != []:
            result[key] = value

    return result


# =============================================================================
# Elicitation Schemas (Pydantic models for user input)
# =============================================================================

class CollectionChoiceSchema(BaseModel):
    """Schema for collection selection elicitation"""
    choice: str = Field(
        description="Enter the number of your choice (e.g., '1' for first option, '0' for no collection)"
    )


class DuplicateConfirmSchema(BaseModel):
    """Schema for duplicate confirmation elicitation"""
    confirm: str = Field(
        description="Enter 'yes' to add anyway, or 'no' to cancel"
    )


# =============================================================================
# Helper Functions
# =============================================================================

def _format_collection_options(collections: list[dict], suggestions: list[dict] = None) -> str:
    """
    Format collections as numbered options for user selection.

    Returns a formatted string like:

    📁 Available Collections:
    ─────────────────────────
    ⭐ Suggested:
       1. AI Research (score: 85) - 12 items
       2. Machine Learning (score: 70) - 8 items

    📂 All Collections:
       3. Biology - 15 items
       4. Chemistry - 10 items
       ...

    0. Save to My Library (no collection)
    """
    lines = ["", "📁 **Select a Collection:**", "─" * 30]

    option_num = 1
    key_to_num: dict[str, int] = {}

    # Add suggestions first if available
    if suggestions:
        lines.append("")
        lines.append("⭐ **Suggested (based on title/tags):**")
        for sug in suggestions[:3]:  # Top 3 suggestions
            key = sug.get("key", "")
            name = sug.get("name", "")
            score = sug.get("score", 0)
            reason = sug.get("reason", "")
            lines.append(f"   **{option_num}.** {name} (match: {score}%) - {reason}")
            key_to_num[key] = option_num
            option_num += 1

    # Add all collections (excluding already suggested)
    suggested_keys = {s.get("key") for s in (suggestions or [])}
    other_collections = [c for c in collections if c.get("key") not in suggested_keys]

    if other_collections:
        lines.append("")
        lines.append("📂 **All Collections:**")
        for col in other_collections[:15]:  # Limit to 15
            key = col.get("key", "")
            name = col.get("name", "")
            item_count = col.get("itemCount", 0)
            parent_key = col.get("parentKey")
            indent = "      " if parent_key else "   "
            lines.append(f"{indent}**{option_num}.** {name} ({item_count} items)")
            key_to_num[key] = option_num
            option_num += 1

        if len(other_collections) > 15:
            lines.append(f"   ... and {len(other_collections) - 15} more collections")

    # Always add "no collection" option
    lines.append("")
    lines.append("**0.** Save to My Library (no collection)")
    lines.append("")
    lines.append("─" * 30)

    return "\n".join(lines), key_to_num


def _num_to_collection_key(num_str: str, key_to_num: dict[str, int]) -> str | None:
    """Convert user's number choice back to collection key"""
    try:
        choice_num = int(num_str.strip())
        if choice_num == 0:
            return None  # No collection

        # Reverse lookup
        for key, num in key_to_num.items():
            if num == choice_num:
                return key

        return None
    except ValueError:
        return None


# =============================================================================
# Validation and Duplicate Detection (imported from smart_tools)
# =============================================================================

def _normalize_title(title: str) -> str:
    """Normalize title for comparison."""
    if not title:
        return ""
    import re
    title = title.lower()
    title = re.sub(r'[^\w\s]', ' ', title)
    title = re.sub(r'\s+', ' ', title)
    return title.strip()


def _get_required_fields(item_type: str) -> list[str]:
    """Get required fields for an item type."""
    match item_type:
        case "journalArticle" | "book":
            return ["title", "creators"]
        case "bookSection":
            return ["title", "creators", "bookTitle"]
        case "conferencePaper":
            return ["title", "creators"]
        case "thesis":
            return ["title", "creators", "university"]
        case "webpage":
            return ["title", "url"]
        case _:
            return ["title"]


def _validate_item(item: dict) -> dict[str, Any]:
    """Validate a reference item."""
    errors = []
    warnings = []

    item_type = item.get("itemType", "document")
    required_fields = _get_required_fields(item_type)

    for field in required_fields:
        if field == "creators":
            creators = item.get("creators", [])
            if not creators:
                errors.append("Missing required: creators (at least one author)")
        else:
            if not item.get(field):
                errors.append(f"Missing required: {field}")

    # Warnings for journal articles
    if item_type == "journalArticle":
        if not item.get("publicationTitle"):
            warnings.append("Recommended: publicationTitle (journal name)")
        if not item.get("DOI"):
            warnings.append("Recommended: DOI")

    return {
        "valid": len(errors) == 0,
        "errors": errors,
        "warnings": warnings,
    }


# =============================================================================
# Register Interactive Save Tool
# =============================================================================

def register_interactive_save_tools(mcp, zotero_client):
    """Register the interactive save tool with elicitation support."""

    # Import suggestion function from smart_tools
    from .smart_tools import _find_duplicates, _suggest_collections

    @mcp.tool()
    async def interactive_save(
        item_type: str,
        title: str,
        creators: list[dict] | None = None,
        doi: str | None = None,
        isbn: str | None = None,
        pmid: str | None = None,
        publication_title: str | None = None,
        date: str | None = None,
        abstract: str | None = None,
        url: str | None = None,
        tags: list[str] | None = None,
        skip_collection_prompt: bool = False,
        auto_fetch_metadata: bool = True,
        include_citation_metrics: bool = True,
        ctx: Context[ServerSession, None] = None,
        **extra_fields,
    ) -> dict[str, Any]:
        """
        💾 Interactive save with collection selection

        互動式儲存 - 會列出所有收藏夾讓你選擇

        🎯 This tool uses MCP Elicitation to:
        1. Show all available collections as numbered options
        2. Highlight suggested collections based on title/tags
        3. Let you choose by entering a number
        4. Confirm if duplicates are found

        🔒 DATA INTEGRITY:
        When DOI or PMID is provided, this tool will **automatically fetch**
        complete article metadata from external APIs (CrossRef/PubMed).
        This ensures the saved reference includes abstract and all fields!

        📊 CITATION METRICS (RCR):
        When PMID is provided and include_citation_metrics=True (default),
        automatically fetches Relative Citation Ratio from iCite and stores
        in Zotero's extra field.

        Args:
            item_type: Type (journalArticle, book, etc.)
            title: Reference title (required)
            creators: List of author dicts
            doi: Digital Object Identifier → 自動從 CrossRef 取得完整資料
            isbn: ISBN for books
            pmid: PubMed ID → 自動從 PubMed 取得完整資料 + RCR
            publication_title: Journal name
            date: Publication date
            abstract: Abstract text
            url: URL
            tags: List of tags
            skip_collection_prompt: If True, save without asking (to My Library)
            auto_fetch_metadata: If True (default), auto-fetch from DOI/PMID
            include_citation_metrics: If True (default), fetch RCR from iCite when PMID provided
            **extra_fields: Additional Zotero fields

        Returns:
            {
                "success": bool,
                "message": str,
                "saved_to": collection info or "My Library",
                "metadata_source": "user" | "pmid" | "doi" | "merged"
            }

        Example:
            interactive_save(
                item_type="journalArticle",
                title="Deep Learning for Medical Imaging",
                doi="10.1234/example",  # ← Will auto-fetch abstract!
                tags=["AI", "medical"]
            )

            → Fetches complete metadata from CrossRef
            → Shows numbered collection list
            → User enters "2" to select second option
            → Saves to that collection with FULL data (including abstract)
        """
        result = {
            "success": False,
            "message": "",
            "saved_to": None,
            "metadata_source": "user",
        }

        try:
            # ========== Step 0: Auto-fetch metadata if DOI/PMID provided ==========
            user_input = {
                "itemType": item_type,
                "title": title,
                "creators": creators or [],
            }

            if doi:
                user_input["DOI"] = doi
            if isbn:
                user_input["ISBN"] = isbn
            if pmid:
                user_input["extra"] = f"PMID: {pmid}"
            if publication_title:
                user_input["publicationTitle"] = publication_title
            if date:
                user_input["date"] = date
            if abstract:
                user_input["abstractNote"] = abstract
            if url:
                user_input["url"] = url
            if tags:
                user_input["tags"] = [{"tag": t} for t in tags]

            user_input.update(extra_fields)

            # Auto-fetch if enabled and we have identifiers
            fetched_metadata = None

            if auto_fetch_metadata:
                # Try PMID first (more reliable for academic articles)
                if pmid:
                    fetched_metadata = await _fetch_metadata_from_pmid(
                        pmid, include_citation_metrics=include_citation_metrics
                    )
                    if fetched_metadata:
                        result["metadata_source"] = "pmid"
                        if include_citation_metrics:
                            result["citation_metrics_fetched"] = True

                # If no PMID or fetch failed, try DOI
                if not fetched_metadata and doi:
                    fetched_metadata = await _fetch_metadata_from_doi(doi)
                    if fetched_metadata:
                        result["metadata_source"] = "doi"

            # Merge: user input takes priority, fetched fills gaps
            if fetched_metadata:
                item = _merge_metadata(user_input, fetched_metadata)
                if result["metadata_source"] != "user":
                    result["metadata_source"] = f"merged ({result['metadata_source']})"
                logger.info(f"Merged metadata from {result['metadata_source']}")
            else:
                item = user_input

            # Log if abstract is present
            if item.get("abstractNote"):
                logger.info(f"✅ Abstract included ({len(item['abstractNote'])} chars)")
            else:
                logger.warning("⚠️ No abstract in final item - consider providing DOI/PMID")
                result["warning"] = "No abstract available. Provide DOI or PMID for complete metadata."

            # ========== Step 1: Validation ==========
            validation = _validate_item(item)
            if not validation["valid"]:
                result["message"] = f"❌ Validation failed: {', '.join(validation['errors'])}"
                result["validation"] = validation
                return result

            # ========== Step 2: Duplicate Check ==========
            duplicates = await _find_duplicates(item, zotero_client)

            if duplicates and ctx:
                # Ask user to confirm
                best = duplicates[0]
                dup_msg = (
                    f"⚠️ **Potential Duplicate Found:**\n\n"
                    f"Existing: **{best['title']}**\n"
                    f"Match: {best['score']}% ({best['match_type']})\n\n"
                    f"Do you want to add anyway?"
                )

                try:
                    dup_result = await ctx.elicit(
                        message=dup_msg,
                        schema=DuplicateConfirmSchema,
                    )

                    if dup_result.action == "accept" and dup_result.data:
                        if dup_result.data.confirm.lower() not in ("yes", "y", "是", "確定"):
                            result["message"] = "❌ Cancelled - duplicate exists"
                            result["duplicate"] = best
                            return result
                    elif dup_result.action in ("decline", "cancel"):
                        result["message"] = "❌ Cancelled by user"
                        return result
                except Exception as e:
                    # Elicitation not supported, proceed with warning
                    logger.warning(f"Elicitation failed (duplicate check): {e}")
                    result["duplicate_warning"] = f"Duplicate found: {best['title']} ({best['score']}%)"

            # ========== Step 3: Collection Selection ==========
            target_collection_key = None
            target_collection_name = None

            if not skip_collection_prompt and ctx:
                try:
                    # Get all collections
                    collections = await zotero_client.get_collections()
                    all_collections = [
                        {
                            "key": c.get("key"),
                            "name": c.get("data", {}).get("name", ""),
                            "parentKey": c.get("data", {}).get("parentCollection"),
                            "itemCount": c.get("data", {}).get("numItems", 0),
                        }
                        for c in collections
                    ]

                    # Get suggestions
                    suggestions = await _suggest_collections(item, zotero_client)

                    # Format options
                    options_text, key_to_num = _format_collection_options(all_collections, suggestions)

                    # Build elicitation message
                    elicit_msg = (
                        f"📚 **Saving:** {title}\n"
                        f"{options_text}\n"
                        f"Enter the number of your choice:"
                    )

                    # Ask user
                    choice_result = await ctx.elicit(
                        message=elicit_msg,
                        schema=CollectionChoiceSchema,
                    )

                    if choice_result.action == "accept" and choice_result.data:
                        choice = choice_result.data.choice.strip()
                        target_collection_key = _num_to_collection_key(choice, key_to_num)

                        if target_collection_key:
                            # Find the name
                            for c in all_collections:
                                if c["key"] == target_collection_key:
                                    target_collection_name = c["name"]
                                    break
                    elif choice_result.action in ("decline", "cancel"):
                        result["message"] = "❌ Cancelled by user"
                        return result

                except Exception as e:
                    # Elicitation not supported, save without collection
                    logger.warning(f"Elicitation failed (collection selection): {e}")
                    result["note"] = "Collection selection skipped (elicitation not supported)"

            # ========== Step 4: Save ==========
            if target_collection_key:
                item["collections"] = [target_collection_key]

            await zotero_client.save_items([item])

            result["success"] = True
            if target_collection_key:
                result["saved_to"] = {
                    "key": target_collection_key,
                    "name": target_collection_name,
                }
                result["message"] = f"✅ Saved '{title}' to collection '{target_collection_name}'"
            else:
                result["saved_to"] = "My Library (no collection)"
                result["message"] = f"✅ Saved '{title}' to My Library"

            if validation.get("warnings"):
                result["warnings"] = validation["warnings"]

            return result

        except Exception as e:
            logger.error(f"Interactive save failed: {e}")
            result["message"] = f"❌ Save failed: {str(e)}"
            return result


    @mcp.tool()
    async def quick_save(
        item_type: str,
        title: str,
        collection_key: str | None = None,
        collection_name: str | None = None,
        creators: list[dict] | None = None,
        doi: str | None = None,
        isbn: str | None = None,
        pmid: str | None = None,
        publication_title: str | None = None,
        date: str | None = None,
        abstract: str | None = None,
        url: str | None = None,
        tags: list[str] | None = None,
        force_add: bool = False,
        auto_fetch_metadata: bool = True,
        include_citation_metrics: bool = True,
        **extra_fields,
    ) -> dict[str, Any]:
        """
        ⚡ Quick save without interactive prompts

        快速儲存（不詢問，直接存）

        Use this when you already know the collection, or want to save
        without interaction. For interactive collection selection,
        use `interactive_save` instead.

        🔒 DATA INTEGRITY:
        When DOI or PMID is provided, this tool will **automatically fetch**
        complete article metadata from external APIs (CrossRef/PubMed).
        This ensures the saved reference includes abstract and all fields!

        📊 CITATION METRICS (RCR):
        When PMID is provided and include_citation_metrics=True (default),
        automatically fetches Relative Citation Ratio from iCite and stores
        in Zotero's extra field.

        Args:
            item_type: Type (journalArticle, book, etc.)
            title: Reference title (required)
            collection_key: Collection key to save to
            collection_name: OR collection name (will be looked up)
            creators: List of author dicts
            doi: Digital Object Identifier → 自動從 CrossRef 取得完整資料
            isbn: ISBN for books
            pmid: PubMed ID → 自動從 PubMed 取得完整資料 + RCR
            publication_title: Journal name
            date: Publication date
            abstract: Abstract text
            url: URL
            tags: List of tags
            force_add: Add even if duplicate found
            auto_fetch_metadata: If True (default), auto-fetch from DOI/PMID
            include_citation_metrics: If True (default), fetch RCR from iCite when PMID provided
            **extra_fields: Additional Zotero fields

        Returns:
            Success/failure with details

        Example:
            quick_save(
                item_type="journalArticle",
                title="My Paper",
                pmid="12345678",  # ← Will auto-fetch abstract + RCR!
                collection_name="AI Research"
            )
        """
        result = {
            "success": False,
            "message": "",
            "saved_to": None,
            "metadata_source": "user",
        }

        try:
            # ========== Step 0: Auto-fetch metadata if DOI/PMID provided ==========
            user_input = {
                "itemType": item_type,
                "title": title,
                "creators": creators or [],
            }

            if doi:
                user_input["DOI"] = doi
            if isbn:
                user_input["ISBN"] = isbn
            if pmid:
                user_input["extra"] = f"PMID: {pmid}"
            if publication_title:
                user_input["publicationTitle"] = publication_title
            if date:
                user_input["date"] = date
            if abstract:
                user_input["abstractNote"] = abstract
            if url:
                user_input["url"] = url
            if tags:
                user_input["tags"] = [{"tag": t} for t in tags]

            user_input.update(extra_fields)

            # Auto-fetch if enabled and we have identifiers
            fetched_metadata = None

            if auto_fetch_metadata:
                # Try PMID first (more reliable for academic articles)
                if pmid:
                    fetched_metadata = await _fetch_metadata_from_pmid(
                        pmid, include_citation_metrics=include_citation_metrics
                    )
                    if fetched_metadata:
                        result["metadata_source"] = "pmid"
                        if include_citation_metrics:
                            result["citation_metrics_fetched"] = True

                # If no PMID or fetch failed, try DOI
                if not fetched_metadata and doi:
                    fetched_metadata = await _fetch_metadata_from_doi(doi)
                    if fetched_metadata:
                        result["metadata_source"] = "doi"

            # Merge: user input takes priority, fetched fills gaps
            if fetched_metadata:
                item = _merge_metadata(user_input, fetched_metadata)
                if result["metadata_source"] != "user":
                    result["metadata_source"] = f"merged ({result['metadata_source']})"
                logger.info(f"Merged metadata from {result['metadata_source']}")
            else:
                item = user_input

            # Log if abstract is present
            if item.get("abstractNote"):
                logger.info(f"✅ Abstract included ({len(item['abstractNote'])} chars)")
            else:
                logger.warning("⚠️ No abstract in final item")
                result["warning"] = "No abstract available. Provide DOI or PMID for complete metadata."

            # Validation
            validation = _validate_item(item)
            if not validation["valid"]:
                result["message"] = f"❌ Validation failed: {', '.join(validation['errors'])}"
                return result

            # Duplicate check
            if not force_add:
                duplicates = await _find_duplicates(item, zotero_client)
                if duplicates:
                    best = duplicates[0]
                    result["message"] = f"⚠️ Duplicate found: '{best['title']}' ({best['score']}% match). Use force_add=True to add anyway."
                    result["duplicate"] = best
                    return result

            # Resolve collection
            target_key = None
            target_name = None

            if collection_key:
                try:
                    col = await zotero_client.get_collection(collection_key)
                    target_key = collection_key
                    target_name = col.get("data", {}).get("name", collection_key)
                except Exception:
                    result["message"] = f"❌ Collection key '{collection_key}' not found"
                    return result

            elif collection_name:
                found = await zotero_client.find_collection_by_name(collection_name)
                if found:
                    target_key = found.get("key")
                    target_name = found.get("data", {}).get("name", collection_name)
                else:
                    result["message"] = f"❌ Collection '{collection_name}' not found"
                    return result

            # Save
            if target_key:
                item["collections"] = [target_key]

            await zotero_client.save_items([item])

            result["success"] = True
            if target_key:
                result["saved_to"] = {"key": target_key, "name": target_name}
                result["message"] = f"✅ Saved '{title}' to '{target_name}'"
            else:
                result["saved_to"] = "My Library"
                result["message"] = f"✅ Saved '{title}' to My Library"

            return result

        except Exception as e:
            logger.error(f"Quick save failed: {e}")
            result["message"] = f"❌ Save failed: {str(e)}"
            return result


    logger.info("Interactive save tools registered (interactive_save, quick_save)")
