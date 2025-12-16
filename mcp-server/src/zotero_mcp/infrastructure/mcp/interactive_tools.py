"""
Interactive Save Tools with MCP Elicitation

Uses MCP Elicitation feature to interactively ask users to select collections
when saving references. This provides a much better UX than two-phase save.

Key Features:
- Mid-tool user input via ctx.elicit()
- Collection selection with numbered options
- Duplicate detection with confirmation
- Validation with user feedback
- Auto-fetch complete metadata from DOI/PMID

🔒 DATA INTEGRITY GUARANTEE:
   When DOI or PMID is provided, this tool will automatically fetch
   complete article metadata (including abstract) from external APIs.
"""

import logging
from typing import Any

from mcp.server.fastmcp import Context
from mcp.server.session import ServerSession
from pydantic import BaseModel, Field

from .metadata_fetcher import auto_fetch_and_merge
from .validation import validate_item, find_duplicates
from .collection_utils import (
    format_collection_options,
    num_to_collection_key,
)

logger = logging.getLogger(__name__)


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

    confirm: str = Field(description="Enter 'yes' to add anyway, or 'no' to cancel")


# =============================================================================
# Helper Functions
# =============================================================================


def _build_user_input(
    item_type: str,
    title: str,
    creators: list[dict] | None,
    doi: str | None,
    isbn: str | None,
    pmid: str | None,
    publication_title: str | None,
    date: str | None,
    abstract: str | None,
    url: str | None,
    tags: list[str] | None,
    extra_fields: dict,
) -> dict:
    """Build user input dict from parameters."""
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
    return user_input


async def _handle_duplicate_check(
    item: dict, zotero_client, ctx: Context | None, result: dict
) -> bool:
    """
    Handle duplicate check with optional elicitation.

    Returns True if should proceed, False if cancelled.
    """
    from .smart_tools import _find_duplicates

    duplicates = await _find_duplicates(item, zotero_client)

    if not duplicates:
        return True

    best = duplicates[0]

    if ctx:
        try:
            dup_msg = (
                f"⚠️ **Potential Duplicate Found:**\n\n"
                f"Existing: **{best['title']}**\n"
                f"Match: {best['score']}% ({best['match_type']})\n\n"
                f"Do you want to add anyway?"
            )

            dup_result = await ctx.elicit(
                message=dup_msg,
                schema=DuplicateConfirmSchema,
            )

            if dup_result.action == "accept" and dup_result.data:
                if dup_result.data.confirm.lower() not in ("yes", "y", "是", "確定"):
                    result["message"] = "❌ Cancelled - duplicate exists"
                    result["duplicate"] = best
                    return False
            elif dup_result.action in ("decline", "cancel"):
                result["message"] = "❌ Cancelled by user"
                return False
        except Exception as e:
            logger.warning(f"Elicitation failed (duplicate check): {e}")
            result["duplicate_warning"] = (
                f"Duplicate found: {best['title']} ({best['score']}%)"
            )

    return True


async def _handle_collection_selection(
    item: dict, zotero_client, ctx: Context | None, skip_prompt: bool
) -> tuple[str | None, str | None]:
    """
    Handle collection selection with optional elicitation.

    Returns (collection_key, collection_name).
    """
    if skip_prompt or not ctx:
        return None, None

    try:
        from .smart_tools import _suggest_collections

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
        options_text, key_to_num = format_collection_options(
            all_collections, suggestions
        )

        # Build elicitation message
        title = item.get("title", "Unknown")
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
            target_key = num_to_collection_key(choice, key_to_num)

            if target_key:
                # Find the name
                for c in all_collections:
                    if c["key"] == target_key:
                        return target_key, c["name"]

        elif choice_result.action in ("decline", "cancel"):
            return "CANCELLED", None

    except Exception as e:
        logger.warning(f"Elicitation failed (collection selection): {e}")

    return None, None


# =============================================================================
# Register Interactive Save Tools
# =============================================================================


def register_interactive_save_tools(mcp, zotero_client):
    """Register the interactive save tool with elicitation support."""

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

        Args:
            item_type: Type (journalArticle, book, etc.)
            title: Reference title (required)
            creators: List of author dicts
            doi: Digital Object Identifier → 自動從 CrossRef 取得完整資料
            pmid: PubMed ID → 自動從 PubMed 取得完整資料 + RCR
            skip_collection_prompt: If True, save without asking

        Returns:
            Success/failure with details
        """
        result = {
            "success": False,
            "message": "",
            "saved_to": None,
            "metadata_source": "user",
        }

        try:
            # Step 0: Build user input and auto-fetch metadata
            user_input = _build_user_input(
                item_type,
                title,
                creators,
                doi,
                isbn,
                pmid,
                publication_title,
                date,
                abstract,
                url,
                tags,
                extra_fields,
            )

            item, metadata_source = await auto_fetch_and_merge(
                user_input,
                pmid=pmid,
                doi=doi,
                auto_fetch=auto_fetch_metadata,
                include_citation_metrics=include_citation_metrics,
            )
            result["metadata_source"] = metadata_source

            # Log abstract status
            if item.get("abstractNote"):
                logger.info(f"✅ Abstract included ({len(item['abstractNote'])} chars)")
            else:
                logger.warning("⚠️ No abstract in final item")
                result["warning"] = "No abstract. Provide DOI or PMID for complete metadata."

            # Step 1: Validation
            validation = validate_item(item)
            if not validation["valid"]:
                result["message"] = f"❌ Validation failed: {', '.join(validation['errors'])}"
                result["validation"] = validation
                return result

            # Step 2: Duplicate Check
            if not await _handle_duplicate_check(item, zotero_client, ctx, result):
                return result

            # Step 3: Collection Selection
            target_key, target_name = await _handle_collection_selection(
                item, zotero_client, ctx, skip_collection_prompt
            )

            if target_key == "CANCELLED":
                result["message"] = "❌ Cancelled by user"
                return result

            # Step 4: Save
            if target_key:
                item["collections"] = [target_key]

            await zotero_client.save_items([item])

            result["success"] = True
            if target_key:
                result["saved_to"] = {"key": target_key, "name": target_name}
                result["message"] = f"✅ Saved '{title}' to collection '{target_name}'"
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

        Args:
            item_type: Type (journalArticle, book, etc.)
            title: Reference title (required)
            collection_key: Collection key to save to
            collection_name: OR collection name (will be looked up)
            doi: Digital Object Identifier → 自動從 CrossRef 取得完整資料
            pmid: PubMed ID → 自動從 PubMed 取得完整資料 + RCR
            force_add: Add even if duplicate found

        Returns:
            Success/failure with details
        """
        result = {
            "success": False,
            "message": "",
            "saved_to": None,
            "metadata_source": "user",
        }

        try:
            # Step 0: Build user input and auto-fetch metadata
            user_input = _build_user_input(
                item_type,
                title,
                creators,
                doi,
                isbn,
                pmid,
                publication_title,
                date,
                abstract,
                url,
                tags,
                extra_fields,
            )

            item, metadata_source = await auto_fetch_and_merge(
                user_input,
                pmid=pmid,
                doi=doi,
                auto_fetch=auto_fetch_metadata,
                include_citation_metrics=include_citation_metrics,
            )
            result["metadata_source"] = metadata_source

            # Log abstract status
            if item.get("abstractNote"):
                logger.info(f"✅ Abstract included ({len(item['abstractNote'])} chars)")
            else:
                result["warning"] = "No abstract. Provide DOI or PMID for complete metadata."

            # Validation
            validation = validate_item(item)
            if not validation["valid"]:
                result["message"] = f"❌ Validation failed: {', '.join(validation['errors'])}"
                return result

            # Duplicate check
            if not force_add:
                duplicates = await find_duplicates(item, zotero_client)
                if duplicates:
                    best = duplicates[0]
                    result["message"] = (
                        f"⚠️ Duplicate found: '{best['title']}' ({best['score']}% match). "
                        f"Use force_add=True to add anyway."
                    )
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
