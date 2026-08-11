"""
Interactive Save Tools with MCP Elicitation

Uses MCP SDK v2 Resolve/Elicit dependencies to ask users to select collections
while remaining compatible with both current and legacy protocol negotiation.

Key Features:
- Protocol-portable elicitation through a read-only resolver graph
- Collection selection with exact Zotero keys
- Duplicate detection with confirmation
- Separate confirmation before writing to My Library root
- Validation with user feedback
- Auto-fetch complete metadata from DOI/PMID

🔒 DATA INTEGRITY GUARANTEE:
   When DOI or PMID is provided, this tool will automatically fetch
   complete article metadata (including abstract) from external APIs.
"""

import logging
from typing import Annotated, Any

from mcp.server.mcpserver import Elicit, Resolve
from pydantic import BaseModel, Field

from .collection_support import resolve_collection_target
from .metadata_fetcher import auto_fetch_and_merge
from .validation import validate_item, find_duplicates

logger = logging.getLogger(__name__)


# =============================================================================
# Elicitation Schemas (Pydantic models for user input)
# =============================================================================


class CollectionChoiceSchema(BaseModel):
    """Schema for collection selection elicitation"""

    choice: str = Field(description="Enter an exact Zotero collection key, or ROOT for My Library")


class DuplicateConfirmSchema(BaseModel):
    """Schema for duplicate confirmation elicitation"""

    confirm: bool = Field(description="Confirm that this possible duplicate should be saved anyway")


class RootConfirmSchema(BaseModel):
    """Schema for an explicit Zotero library-root confirmation."""

    confirm_root: bool = Field(description="Confirm saving outside every Zotero collection")


class PreparedSave(BaseModel):
    """Read-only candidate built before any interactive authorization."""

    item: dict[str, Any]
    metadata_source: str
    validation: dict[str, Any]


class DuplicateSnapshot(BaseModel):
    """Stable duplicate-check result shared by the v2 resolver graph."""

    best: dict[str, Any] | None = None


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
    extra_fields: dict[str, Any] | None,
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

    user_input.update(extra_fields or {})
    return user_input


# =============================================================================
# Register Interactive Save Tools
# =============================================================================


def register_interactive_save_tools(mcp, zotero_client):
    """Register save tools with protocol-portable MCP v2 elicitation."""

    async def prepare_candidate(
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
        auto_fetch_metadata: bool = True,
        include_citation_metrics: bool = True,
        extra_fields: dict[str, Any] | None = None,
    ) -> PreparedSave:
        """Build and validate a save candidate without changing Zotero."""
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
        return PreparedSave(
            item=item,
            metadata_source=metadata_source,
            validation=validate_item(item),
        )

    candidate_dependency = Resolve(prepare_candidate)

    async def inspect_duplicates(
        candidate: Annotated[PreparedSave, candidate_dependency],
    ) -> DuplicateSnapshot:
        """Take a duplicate snapshot; invalid candidates never reach Zotero reads."""
        if not candidate.validation.get("valid"):
            return DuplicateSnapshot()

        from .smart_tools import _find_duplicates

        duplicates = await _find_duplicates(candidate.item, zotero_client)
        return DuplicateSnapshot(best=duplicates[0] if duplicates else None)

    duplicate_dependency = Resolve(inspect_duplicates)

    async def authorize_duplicate(
        duplicate: Annotated[DuplicateSnapshot, duplicate_dependency],
    ) -> DuplicateConfirmSchema | Elicit[DuplicateConfirmSchema]:
        """Ask only when a duplicate exists; refusal aborts dependency resolution."""
        if duplicate.best is None:
            return DuplicateConfirmSchema(confirm=True)

        best = duplicate.best
        message = (
            "⚠️ **Potential Duplicate Found**\n\n"
            f"Existing: **{best.get('title', 'Untitled')}**\n"
            f"Match: {best.get('score', '?')}% ({best.get('match_type', 'similar metadata')})\n\n"
            "Save another copy anyway?"
        )
        return Elicit(message, DuplicateConfirmSchema)

    duplicate_authorization = Resolve(authorize_duplicate)

    async def choose_collection(
        candidate: Annotated[PreparedSave, candidate_dependency],
        duplicate: Annotated[DuplicateSnapshot, duplicate_dependency],
        duplicate_confirmation: Annotated[DuplicateConfirmSchema, duplicate_authorization],
        skip_collection_prompt: bool = False,
    ) -> CollectionChoiceSchema | Elicit[CollectionChoiceSchema]:
        """Choose a destination only after validation and duplicate authorization."""
        if not candidate.validation.get("valid") or (duplicate.best and not duplicate_confirmation.confirm):
            return CollectionChoiceSchema(choice="BLOCKED")
        if skip_collection_prompt:
            return CollectionChoiceSchema(choice="SKIPPED")

        from .smart_tools import _suggest_collections

        collections = await zotero_client.get_collections()
        catalog = sorted(
            (
                {
                    "key": str(collection.get("key") or "").strip(),
                    "name": str(collection.get("data", {}).get("name") or "Untitled"),
                }
                for collection in collections
                if collection.get("key")
            ),
            key=lambda collection: (collection["name"].casefold(), collection["key"]),
        )
        suggestions = await _suggest_collections(candidate.item, zotero_client)
        suggested_keys = {
            str(suggestion.get("key"))
            for suggestion in sorted(
                suggestions,
                key=lambda suggestion: (
                    -float(suggestion.get("score", 0)),
                    str(suggestion.get("name", "")).casefold(),
                    str(suggestion.get("key", "")),
                ),
            )[:3]
            if suggestion.get("key")
        }

        lines = [f"📚 **Saving:** {candidate.item.get('title', 'Untitled')}", "", "Choose a collection key:"]
        for collection in catalog:
            marker = "⭐ " if collection["key"] in suggested_keys else ""
            lines.append(f"- {marker}{collection['name']}: `{collection['key']}`")
        lines.extend(
            [
                "",
                "Enter `ROOT` only if you intend to save outside every collection; a second confirmation is required.",
            ]
        )
        return Elicit("\n".join(lines), CollectionChoiceSchema)

    collection_dependency = Resolve(choose_collection)

    async def confirm_library_root(
        collection_choice: Annotated[CollectionChoiceSchema, collection_dependency],
    ) -> RootConfirmSchema | Elicit[RootConfirmSchema]:
        """Require a separate human confirmation before writing to library root."""
        if collection_choice.choice.strip().upper() != "ROOT":
            return RootConfirmSchema(confirm_root=False)
        return Elicit(
            "Save this item to My Library without assigning it to any collection?",
            RootConfirmSchema,
        )

    root_authorization = Resolve(confirm_library_root)

    @mcp.tool()
    async def interactive_save(
        item_type: str,
        title: str,
        candidate: Annotated[PreparedSave, candidate_dependency],
        duplicate: Annotated[DuplicateSnapshot, duplicate_dependency],
        duplicate_confirmation: Annotated[DuplicateConfirmSchema, duplicate_authorization],
        collection_choice: Annotated[CollectionChoiceSchema, collection_dependency],
        root_confirmation: Annotated[RootConfirmSchema, root_authorization],
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
        extra_fields: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """
        💾 Interactive save with collection selection

        互動式儲存 - 會列出所有收藏夾讓你選擇

        🎯 This tool uses MCP Elicitation to:
        1. Show available collections and their exact keys
        2. Highlight suggested collections based on title/tags
        3. Let you choose an exact collection key
        4. Confirm if duplicates are found
        5. Require a second confirmation if you choose ROOT

        🔒 DATA INTEGRITY:
        When DOI or PMID is provided, this tool will **automatically fetch**
        complete article metadata from external APIs (CrossRef/PubMed).

        🤝 MCP COLLABORATION NOTE:
        This auto-fetch path is intended for manual DOI/PMID entry.
        If metadata already comes from pubmed-search-mcp, prefer `import_articles()`
        to avoid refetching the same PubMed record.

        Args:
            item_type: Type (journalArticle, book, etc.)
            title: Reference title (required)
            creators: List of author dicts
            doi: Digital Object Identifier → 自動從 CrossRef 取得完整資料
            pmid: PubMed ID → 自動從 PubMed 取得完整資料 + RCR
            skip_collection_prompt: Deprecated. If True, aborts without writing;
                use quick_save with a validated collection or explicitly approved
                allow_library_root instead.

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
            # Resolvers are read-only. This final body is the sole write boundary.
            item = dict(candidate.item)
            validation = candidate.validation
            result["metadata_source"] = candidate.metadata_source

            # Log abstract status
            if item.get("abstractNote"):
                logger.info(f"✅ Abstract included ({len(item['abstractNote'])} chars)")
            else:
                logger.warning("⚠️ No abstract in final item")
                result["warning"] = "No abstract. Provide DOI or PMID for complete metadata."

            if not validation["valid"]:
                result["message"] = f"❌ Validation failed: {', '.join(validation['errors'])}"
                result["validation"] = validation
                return result

            if duplicate.best and not duplicate_confirmation.confirm:
                result["message"] = "❌ Cancelled - duplicate exists"
                result["duplicate"] = duplicate.best
                return result

            choice = collection_choice.choice.strip()
            if choice == "BLOCKED":
                result["message"] = "❌ Save authorization was not completed"
                return result
            if choice == "SKIPPED":
                result["message"] = (
                    "❌ skip_collection_prompt no longer writes to My Library. "
                    "Use quick_save with a validated collection key, or choose ROOT and confirm it interactively."
                )
                return result

            target_key: str | None = None
            target_name: str | None = None
            if choice.upper() == "ROOT":
                if not root_confirmation.confirm_root:
                    result["message"] = "❌ My Library root was not confirmed"
                    return result
            else:
                try:
                    collection = await zotero_client.get_collection(choice)
                except Exception:
                    result["message"] = f"❌ Collection key '{choice}' is no longer available"
                    return result

                collection_data = collection.get("data", {}) if isinstance(collection, dict) else {}
                target_key = choice
                target_name = collection_data.get("name") or choice

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
        allow_library_root: bool = False,
        auto_fetch_metadata: bool = True,
        include_citation_metrics: bool = True,
        extra_fields: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """
        ⚡ Quick save without interactive prompts

        快速儲存（不詢問，直接存）

        Use this when you already know the collection. A destination is required
        unless the user has explicitly approved a root-library write and the
        caller carries that approval as `allow_library_root=True`. For interactive
        collection selection, use `interactive_save` instead.

        🔒 DATA INTEGRITY:
        When DOI or PMID is provided, this tool will **automatically fetch**
        complete article metadata from external APIs (CrossRef/PubMed).

        🤝 MCP COLLABORATION NOTE:
        This auto-fetch path is intended for manual DOI/PMID entry.
        If metadata already comes from pubmed-search-mcp, prefer `import_articles()`
        to avoid refetching the same PubMed record.

        Args:
            item_type: Type (journalArticle, book, etc.)
            title: Reference title (required)
            collection_key: Collection key to save to
            collection_name: OR collection name (will be looked up)
            doi: Digital Object Identifier → 自動從 CrossRef 取得完整資料
            pmid: PubMed ID → 自動從 PubMed 取得完整資料 + RCR
            force_add: Add even if duplicate found
            allow_library_root: Explicitly allow saving outside every collection

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
                    result["message"] = f"⚠️ Duplicate found: '{best['title']}' ({best['score']}% match). Use force_add=True to add anyway."
                    result["duplicate"] = best
                    return result

            # Resolve collection through the shared fail-closed path. A truthy
            # but malformed name lookup must never degrade into a root write.
            resolution = await resolve_collection_target(
                zotero_client,
                collection_name=collection_name,
                collection_key=collection_key,
                allow_library_root=allow_library_root,
            )
            if not resolution["success"]:
                result["message"] = f"❌ {resolution['error']}"
                if resolution.get("hint"):
                    result["hint"] = resolution["hint"]
                if resolution.get("available_collections") is not None:
                    result["available_collections"] = resolution["available_collections"]
                return result

            target_key = resolution["target_key"]
            target_name = resolution["target_name"]

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
