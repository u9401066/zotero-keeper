"""
Smart Tools for Zotero Keeper

Intelligent features for reference management:
- Duplicate detection with fuzzy matching
- Reference validation
- Smart add with auto-check

Uses rapidfuzz for high-performance fuzzy string matching.
"""

import logging
from typing import Any, Optional

from rapidfuzz import fuzz, process

logger = logging.getLogger(__name__)

# Matching thresholds
TITLE_MATCH_THRESHOLD = 85  # Fuzzy match score (0-100)
EXACT_MATCH_FIELDS = ["DOI", "ISBN", "PMID"]  # Exact match on these identifiers


def _normalize_title(title: str) -> str:
    """Normalize title for comparison."""
    if not title:
        return ""
    # Lowercase, remove punctuation, extra spaces
    import re
    title = title.lower()
    title = re.sub(r'[^\w\s]', ' ', title)
    title = re.sub(r'\s+', ' ', title)
    return title.strip()


def _extract_identifier(item: dict, field: str) -> Optional[str]:
    """Extract identifier from item, checking multiple locations."""
    # Direct field
    if item.get(field):
        return str(item[field]).strip().lower()
    
    # Check in 'extra' field (common for PMID, PMCID)
    extra = item.get("extra", "")
    if extra and field in extra.upper():
        import re
        pattern = rf'{field}:\s*(\S+)'
        match = re.search(pattern, extra, re.IGNORECASE)
        if match:
            return match.group(1).strip().lower()
    
    return None


def _get_required_fields(item_type: str) -> list[str]:
    """Get required fields for an item type using Python 3.10+ match-case."""
    # Python 3.10+ structural pattern matching
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
        case "report" | "patent":
            return ["title"]
        case _:
            return ["title"]  # Default base required


def _validate_item(item: dict) -> dict[str, Any]:
    """
    Validate a reference item.
    
    Returns:
        {
            "valid": bool,
            "errors": list of error messages,
            "warnings": list of warning messages
        }
    """
    errors = []
    warnings = []
    
    item_type = item.get("itemType", "document")
    required_fields = _get_required_fields(item_type)
    
    # Check required fields
    for field in required_fields:
        if field == "creators":
            creators = item.get("creators", [])
            if not creators:
                errors.append(f"Missing required field: creators (at least one author)")
            else:
                # Validate creator structure
                for i, creator in enumerate(creators):
                    if not creator.get("lastName") and not creator.get("name"):
                        errors.append(f"Creator {i+1}: missing lastName or name")
        else:
            if not item.get(field):
                errors.append(f"Missing required field: {field}")
    
    # Warnings for recommended fields
    if item_type == "journalArticle":
        if not item.get("publicationTitle"):
            warnings.append("Recommended: publicationTitle (journal name)")
        if not item.get("date") and not item.get("year"):
            warnings.append("Recommended: date or year")
        if not item.get("DOI"):
            warnings.append("Recommended: DOI for journal articles")
    
    if item_type == "book":
        if not item.get("ISBN"):
            warnings.append("Recommended: ISBN for books")
        if not item.get("publisher"):
            warnings.append("Recommended: publisher")
    
    # Check for identifiers (at least one recommended)
    has_identifier = any([
        item.get("DOI"),
        item.get("ISBN"),
        _extract_identifier(item, "PMID"),
        item.get("url"),
    ])
    if not has_identifier:
        warnings.append("No unique identifier (DOI, ISBN, PMID, or URL)")
    
    return {
        "valid": len(errors) == 0,
        "errors": errors,
        "warnings": warnings,
    }


async def _find_duplicates(
    item: dict,
    zotero_client,
    limit: int = 100,
) -> list[dict]:
    """
    Find potential duplicates in Zotero library.
    
    Returns list of potential matches with similarity scores.
    """
    duplicates = []
    title = item.get("title", "")
    normalized_title = _normalize_title(title)
    
    if not normalized_title:
        return duplicates
    
    # Check exact identifier matches first
    for field in EXACT_MATCH_FIELDS:
        identifier = _extract_identifier(item, field)
        if identifier:
            # Search by identifier
            results = await zotero_client.search_items(query=identifier, limit=10)
            for existing in results:
                existing_id = _extract_identifier(existing, field)
                if existing_id and existing_id == identifier:
                    duplicates.append({
                        "key": existing.get("key"),
                        "title": existing.get("data", {}).get("title", existing.get("title", "")),
                        "match_type": f"exact_{field}",
                        "score": 100,
                        "identifier": identifier,
                    })
    
    # If exact match found, return immediately
    if duplicates:
        return duplicates
    
    # Fuzzy title matching
    # Get recent items for comparison
    existing_items = await zotero_client.get_items(limit=limit)
    
    # Extract titles for comparison
    existing_titles = []
    title_to_item = {}
    
    for existing in existing_items:
        data = existing.get("data", existing)
        existing_title = data.get("title", "")
        if existing_title:
            normalized = _normalize_title(existing_title)
            if normalized:
                existing_titles.append(normalized)
                title_to_item[normalized] = {
                    "key": existing.get("key"),
                    "title": existing_title,
                    "data": data,
                }
    
    # Find fuzzy matches
    if existing_titles:
        matches = process.extract(
            normalized_title,
            existing_titles,
            scorer=fuzz.token_sort_ratio,
            limit=5,
        )
        
        for match_title, score, _ in matches:
            if score >= TITLE_MATCH_THRESHOLD:
                matched_item = title_to_item.get(match_title, {})
                duplicates.append({
                    "key": matched_item.get("key"),
                    "title": matched_item.get("title"),
                    "match_type": "fuzzy_title",
                    "score": score,
                })
    
    return duplicates


def register_smart_tools(mcp, zotero_client):
    """Register smart reference management tools."""
    
    @mcp.tool()
    async def check_duplicate(
        title: str,
        doi: Optional[str] = None,
        isbn: Optional[str] = None,
        pmid: Optional[str] = None,
    ) -> dict[str, Any]:
        """
        🔍 Check if a reference already exists in Zotero
        
        檢查參考文獻是否已存在於 Zotero（支援模糊比對）
        
        Uses exact matching for identifiers (DOI, ISBN, PMID) and
        fuzzy matching for titles (85% similarity threshold).
        
        Args:
            title: Reference title to check
            doi: Optional DOI for exact matching
            isbn: Optional ISBN for exact matching
            pmid: Optional PMID for exact matching
            
        Returns:
            {
                "is_duplicate": bool,
                "confidence": "high" | "medium" | "low",
                "matches": list of potential matches with scores
            }
            
        Example:
            check_duplicate(
                title="CRISPR-Cas9 gene editing",
                doi="10.1038/nprot.2013.143"
            )
        """
        try:
            # Build item dict for checking
            item = {"title": title}
            if doi:
                item["DOI"] = doi
            if isbn:
                item["ISBN"] = isbn
            if pmid:
                item["extra"] = f"PMID: {pmid}"
            
            # Find duplicates
            matches = await _find_duplicates(item, zotero_client)
            
            if not matches:
                return {
                    "is_duplicate": False,
                    "confidence": "low",
                    "matches": [],
                    "message": "No duplicates found",
                }
            
            # Determine confidence level
            best_match = matches[0]
            if best_match["match_type"].startswith("exact_"):
                confidence = "high"
            elif best_match["score"] >= 95:
                confidence = "high"
            elif best_match["score"] >= 90:
                confidence = "medium"
            else:
                confidence = "low"
            
            return {
                "is_duplicate": True,
                "confidence": confidence,
                "matches": matches[:5],
                "message": f"Found {len(matches)} potential duplicate(s). Best match: {best_match['score']}% ({best_match['match_type']})",
            }
            
        except Exception as e:
            logger.error(f"Duplicate check failed: {e}")
            return {
                "is_duplicate": False,
                "confidence": "unknown",
                "error": str(e),
            }
    
    @mcp.tool()
    async def validate_reference(
        item_type: str,
        title: str,
        creators: Optional[list[dict]] = None,
        doi: Optional[str] = None,
        isbn: Optional[str] = None,
        publication_title: Optional[str] = None,
        date: Optional[str] = None,
        url: Optional[str] = None,
        **extra_fields,
    ) -> dict[str, Any]:
        """
        ✅ Validate a reference before adding to Zotero
        
        驗證參考文獻的必填欄位和格式
        
        Checks:
        - Required fields based on item type
        - Creator structure
        - Recommended fields (generates warnings)
        
        Args:
            item_type: Type of item (journalArticle, book, etc.)
            title: Reference title
            creators: List of author dicts [{"firstName": "John", "lastName": "Doe", "creatorType": "author"}]
            doi: Digital Object Identifier
            isbn: ISBN for books
            publication_title: Journal name or book title
            date: Publication date
            url: URL for web resources
            **extra_fields: Any additional Zotero fields
            
        Returns:
            {
                "valid": bool,
                "errors": list of error messages,
                "warnings": list of recommendations
            }
            
        Example:
            validate_reference(
                item_type="journalArticle",
                title="My Paper",
                creators=[{"firstName": "John", "lastName": "Doe", "creatorType": "author"}]
            )
        """
        try:
            # Build item dict
            item = {
                "itemType": item_type,
                "title": title,
                "creators": creators or [],
            }
            
            if doi:
                item["DOI"] = doi
            if isbn:
                item["ISBN"] = isbn
            if publication_title:
                item["publicationTitle"] = publication_title
            if date:
                item["date"] = date
            if url:
                item["url"] = url
            
            # Add extra fields
            item.update(extra_fields)
            
            # Validate
            result = _validate_item(item)
            
            if result["valid"]:
                result["message"] = "Reference is valid and ready to add"
            else:
                result["message"] = f"Validation failed: {len(result['errors'])} error(s)"
            
            return result
            
        except Exception as e:
            logger.error(f"Validation failed: {e}")
            return {
                "valid": False,
                "errors": [str(e)],
                "warnings": [],
            }
    
    @mcp.tool()
    async def smart_add_reference(
        item_type: str,
        title: str,
        creators: Optional[list[dict]] = None,
        doi: Optional[str] = None,
        isbn: Optional[str] = None,
        pmid: Optional[str] = None,
        publication_title: Optional[str] = None,
        date: Optional[str] = None,
        abstract: Optional[str] = None,
        url: Optional[str] = None,
        tags: Optional[list[str]] = None,
        skip_duplicate_check: bool = False,
        skip_validation: bool = False,
        force_add: bool = False,
        **extra_fields,
    ) -> dict[str, Any]:
        """
        🧠 Smart add: validate, check duplicates, then add to Zotero
        
        智慧新增：自動驗證、檢查重複、然後新增到 Zotero
        
        Workflow:
        1. Validate required fields (unless skip_validation=True)
        2. Check for duplicates (unless skip_duplicate_check=True)
        3. Add to Zotero if valid and no duplicates (or force_add=True)
        
        Args:
            item_type: Type of item (journalArticle, book, etc.)
            title: Reference title
            creators: List of author dicts
            doi: Digital Object Identifier
            isbn: ISBN for books
            pmid: PubMed ID
            publication_title: Journal name
            date: Publication date (YYYY or YYYY-MM-DD)
            abstract: Abstract text
            url: URL
            tags: List of tag strings
            skip_duplicate_check: Skip duplicate detection
            skip_validation: Skip validation
            force_add: Add even if duplicates found
            **extra_fields: Any additional Zotero fields
            
        Returns:
            {
                "success": bool,
                "action": "added" | "skipped" | "failed",
                "validation": validation result,
                "duplicate_check": duplicate check result,
                "item_key": key of added item (if added)
            }
            
        Example:
            smart_add_reference(
                item_type="journalArticle",
                title="CRISPR Gene Editing",
                creators=[{"firstName": "Jennifer", "lastName": "Doudna", "creatorType": "author"}],
                doi="10.1126/science.example",
                publication_title="Science",
                date="2020",
                tags=["CRISPR", "gene editing"]
            )
        """
        result = {
            "success": False,
            "action": "failed",
            "validation": None,
            "duplicate_check": None,
            "item_key": None,
        }
        
        try:
            # Build item dict
            item = {
                "itemType": item_type,
                "title": title,
                "creators": creators or [],
            }
            
            if doi:
                item["DOI"] = doi
            if isbn:
                item["ISBN"] = isbn
            if pmid:
                if item.get("extra"):
                    item["extra"] += f"\nPMID: {pmid}"
                else:
                    item["extra"] = f"PMID: {pmid}"
            if publication_title:
                item["publicationTitle"] = publication_title
            if date:
                item["date"] = date
            if abstract:
                item["abstractNote"] = abstract
            if url:
                item["url"] = url
            if tags:
                item["tags"] = [{"tag": t} for t in tags]
            
            # Add extra fields
            item.update(extra_fields)
            
            # Step 1: Validation
            if not skip_validation:
                validation_result = _validate_item(item)
                result["validation"] = validation_result
                
                if not validation_result["valid"]:
                    result["action"] = "failed"
                    result["message"] = f"Validation failed: {', '.join(validation_result['errors'])}"
                    return result
            
            # Step 2: Duplicate check
            if not skip_duplicate_check:
                duplicates = await _find_duplicates(item, zotero_client)
                
                duplicate_result = {
                    "checked": True,
                    "found": len(duplicates),
                    "matches": duplicates[:3],
                }
                result["duplicate_check"] = duplicate_result
                
                if duplicates and not force_add:
                    best = duplicates[0]
                    result["action"] = "skipped"
                    result["message"] = f"Duplicate found: '{best['title']}' ({best['score']}% match). Use force_add=True to add anyway."
                    return result
            
            # Step 3: Add to Zotero
            await zotero_client.save_items([item])
            
            result["success"] = True
            result["action"] = "added"
            result["message"] = f"Successfully added '{title}' to Zotero"
            
            # Note: save_items doesn't return the key, so we can't include it
            # A future enhancement could search for the just-added item
            
            return result
            
        except Exception as e:
            logger.error(f"Smart add failed: {e}")
            result["action"] = "failed"
            result["message"] = str(e)
            return result
    
    logger.info("Smart tools registered (check_duplicate, validate_reference, smart_add_reference)")
