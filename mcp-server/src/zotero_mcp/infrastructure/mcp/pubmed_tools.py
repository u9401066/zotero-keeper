"""
PubMed Import Tools for Zotero Keeper

Focused import tools that complement pubmed-search-mcp.
Use pubmed-search-mcp for searching, use these tools for importing to Zotero.

Recommended Workflow:
1. pubmed-search: search_literature("CRISPR") → PMIDs
2. pubmed-search: prepare_export(pmids, format="ris") → RIS text
3. zotero-keeper: import_ris_to_zotero(ris_text) → Zotero items

Alternative (requires pubmed extra):
1. pubmed-search: search_literature("CRISPR") → PMIDs
2. zotero-keeper: import_from_pmids(pmids) → Zotero items
"""

import logging
import re
from typing import Any

logger = logging.getLogger(__name__)

# Check if pubmed-search-mcp is available (for direct PMID import)
try:
    from pubmed_search import PubMedClient
    PUBMED_AVAILABLE = True
except ImportError:
    PUBMED_AVAILABLE = False
    logger.info("pubmed-search-mcp not installed. Direct PMID import disabled.")
    logger.info("Install with: pip install 'zotero-keeper[pubmed]'")


def _parse_ris_to_zotero_items(ris_text: str) -> list[dict[str, Any]]:
    """
    Parse RIS format text to Zotero item format.

    RIS tags reference:
    - TY: Type (JOUR = journalArticle)
    - TI/T1: Title
    - AU/A1: Author
    - PY/Y1: Year
    - JO/JF/T2: Journal
    - VL: Volume
    - IS: Issue
    - SP/EP: Start/End Page
    - DO: DOI
    - AB: Abstract
    - KW: Keywords
    - UR: URL
    """
    items = []
    current_item: dict[str, Any] = {}
    current_authors: list[dict] = []
    current_tags: list[dict] = []

    # RIS type to Zotero type mapping
    type_map = {
        "JOUR": "journalArticle",
        "BOOK": "book",
        "CHAP": "bookSection",
        "CONF": "conferencePaper",
        "THES": "thesis",
        "RPRT": "report",
        "ELEC": "webpage",
        "GEN": "document",
    }

    for line in ris_text.strip().split('\n'):
        line = line.strip()
        if not line or len(line) < 6:
            continue

        # Parse RIS tag format: "XX  - value"
        match = re.match(r'^([A-Z][A-Z0-9])\s+-\s+(.*)$', line)
        if not match:
            continue

        tag, value = match.groups()
        value = value.strip()

        if tag == "TY":
            # Start new record
            if current_item:
                if current_authors:
                    current_item["creators"] = current_authors
                if current_tags:
                    current_item["tags"] = current_tags
                items.append(current_item)
            current_item = {"itemType": type_map.get(value, "journalArticle")}
            current_authors = []
            current_tags = []
        elif tag == "ER":
            # End record
            if current_item:
                if current_authors:
                    current_item["creators"] = current_authors
                if current_tags:
                    current_item["tags"] = current_tags
                items.append(current_item)
            current_item = {}
            current_authors = []
            current_tags = []
        elif tag in ("TI", "T1"):
            current_item["title"] = value
        elif tag in ("AU", "A1"):
            # Author format: "LastName, FirstName" or "LastName"
            if "," in value:
                parts = value.split(",", 1)
                current_authors.append({
                    "lastName": parts[0].strip(),
                    "firstName": parts[1].strip() if len(parts) > 1 else "",
                    "creatorType": "author"
                })
            else:
                current_authors.append({
                    "lastName": value,
                    "firstName": "",
                    "creatorType": "author"
                })
        elif tag in ("PY", "Y1"):
            # Year: might be "2024" or "2024/01/15"
            current_item["date"] = value.split("/")[0]
        elif tag in ("JO", "JF", "T2"):
            current_item["publicationTitle"] = value
        elif tag == "VL":
            current_item["volume"] = value
        elif tag == "IS":
            current_item["issue"] = value
        elif tag == "SP":
            current_item["pages"] = value
        elif tag == "EP":
            if current_item.get("pages"):
                current_item["pages"] += f"-{value}"
            else:
                current_item["pages"] = value
        elif tag == "DO":
            current_item["DOI"] = value
        elif tag == "AB":
            current_item["abstractNote"] = value
        elif tag == "KW":
            current_tags.append({"tag": value})
        elif tag == "UR":
            current_item["url"] = value
        elif tag == "SN":
            current_item["ISSN"] = value
        elif tag == "N1":
            # Notes - often contains PMID
            if "PMID:" in value or value.isdigit():
                pmid = re.search(r'(\d+)', value)
                if pmid:
                    current_item["extra"] = f"PMID: {pmid.group(1)}"
            else:
                current_item["extra"] = value

    # Don't forget last item if no ER tag
    if current_item and current_item.get("title"):
        if current_authors:
            current_item["creators"] = current_authors
        if current_tags:
            current_item["tags"] = current_tags
        items.append(current_item)

    return items


def _pmid_to_zotero_item(article: dict) -> dict[str, Any]:
    """Convert PubMed article dict to Zotero item format."""
    creators = []
    for author in article.get("authors", []):
        if isinstance(author, str):
            parts = author.split()
            if len(parts) >= 2:
                creators.append({
                    "firstName": parts[0],
                    "lastName": " ".join(parts[1:]),
                    "creatorType": "author",
                })
            else:
                creators.append({
                    "lastName": author,
                    "firstName": "",
                    "creatorType": "author",
                })
        elif isinstance(author, dict):
            creators.append({
                "firstName": author.get("firstName", author.get("first_name", "")),
                "lastName": author.get("lastName", author.get("last_name", "")),
                "creatorType": "author",
            })

    item: dict[str, Any] = {
        "itemType": "journalArticle",
        "title": article.get("title", ""),
        "creators": creators,
    }

    if article.get("abstract"):
        item["abstractNote"] = article["abstract"]
    if article.get("journal"):
        item["publicationTitle"] = article["journal"]
    if article.get("year"):
        item["date"] = str(article["year"])
    if article.get("volume"):
        item["volume"] = article["volume"]
    if article.get("issue"):
        item["issue"] = article["issue"]
    if article.get("pages"):
        item["pages"] = article["pages"]
    if article.get("doi"):
        item["DOI"] = article["doi"]

    # PMID and PMCID in extra field
    extra_parts = []
    if article.get("pmid"):
        extra_parts.append(f"PMID: {article['pmid']}")
    if article.get("pmc_id"):
        extra_parts.append(f"PMCID: {article['pmc_id']}")
    if extra_parts:
        item["extra"] = "\n".join(extra_parts)

    # URL
    if article.get("url"):
        item["url"] = article["url"]
    elif article.get("pmid"):
        item["url"] = f"https://pubmed.ncbi.nlm.nih.gov/{article['pmid']}/"

    # Tags from MeSH or keywords
    if article.get("mesh_terms"):
        item["tags"] = [{"tag": term} for term in article["mesh_terms"][:10]]
    elif article.get("keywords"):
        item["tags"] = [{"tag": kw} for kw in article["keywords"][:10]]

    return item


def register_pubmed_tools(mcp, zotero_client):
    """
    Register PubMed import tools.

    These tools complement pubmed-search-mcp by providing import functionality.
    """

    @mcp.tool()
    async def import_ris_to_zotero(
        ris_text: str,
        collection_name: str | None = None,
        collection_key: str | None = None,
        tags: list[str] | None = None,
    ) -> dict[str, Any]:
        """
        📥 Import RIS format citations to Zotero

        ⚠️ DEPRECATED: Use `import_articles` instead for unified import!
        This tool is kept for backward compatibility.

        將 RIS 格式的引用文獻匯入 Zotero

        🔄 NEW RECOMMENDED WORKFLOW:
        1. pubmed: search_literature("query") → articles
        2. keeper: import_articles(articles=articles, collection_name="...")

        LEGACY workflow with pubmed-search-mcp:
        1. pubmed: search_literature("query") → PMIDs
        2. pubmed: prepare_export(pmids, format="ris") → RIS text
        3. keeper: import_ris_to_zotero(ris_text, collection_name="My Collection")

        ⚠️ COLLECTION 防呆:
        - 若指定 collection_name/collection_key 但找不到，會回傳錯誤
        - 不會靜默存到 library root

        Args:
            ris_text: RIS format citation text (from prepare_export or other sources)
            collection_name: Target collection name (recommended - human readable)
            collection_key: Target collection key (alternative)
            tags: Optional tags to add to all imported items

        Returns:
            Import result with count of imported items

        Example:
            import_ris_to_zotero(
                ris_text=\"\"\"
                TY  - JOUR
                TI  - CRISPR-Cas9 Gene Editing
                AU  - Doudna, Jennifer
                PY  - 2020
                JO  - Science
                DO  - 10.1126/science.example
                ER  -
                \"\"\",
                collection_name="Gene Editing Research",
                tags=["gene-editing", "review"]
            )
        """
        try:
            # Parse RIS to Zotero items
            items = _parse_ris_to_zotero_items(ris_text)

            if not items:
                return {
                    "success": False,
                    "message": "No valid items found in RIS text",
                    "imported": 0,
                }

            # === 防呆機制: Collection 驗證 ===
            target_key = None
            target_name = None

            if collection_key:
                try:
                    col = await zotero_client.get_collection(collection_key)
                    target_key = collection_key
                    target_name = col.get("data", {}).get("name", collection_key)
                except Exception:
                    # 取得可用 collections 列表
                    collections = await zotero_client.list_collections()
                    available = [
                        {"name": c.get("data", {}).get("name", ""), "key": c.get("key", "")}
                        for c in collections[:20]
                    ]
                    return {
                        "success": False,
                        "error": f"Collection key '{collection_key}' not found",
                        "available_collections": available,
                        "hint": "Use collection_name instead for human-readable names",
                    }

            elif collection_name:
                found = await zotero_client.find_collection_by_name(collection_name)
                if found:
                    target_key = found.get("key")
                    target_name = found.get("data", {}).get("name", collection_name)
                else:
                    # 取得可用 collections 列表
                    collections = await zotero_client.list_collections()
                    available = [
                        {"name": c.get("data", {}).get("name", ""), "key": c.get("key", "")}
                        for c in collections[:20]
                    ]
                    return {
                        "success": False,
                        "error": f"Collection '{collection_name}' not found",
                        "available_collections": available,
                        "hint": "Check spelling or use list_collections to see all collections",
                    }

            # 設定 collection（如果有指定）
            if target_key:
                for item in items:
                    item["collections"] = [target_key]

            # Add custom tags
            if tags:
                for item in items:
                    existing_tags = item.get("tags", [])
                    for tag in tags:
                        existing_tags.append({"tag": tag})
                    item["tags"] = existing_tags

            # Import to Zotero
            await zotero_client.save_items(items)

            # Build response
            imported_titles = [item.get("title", "Untitled")[:50] for item in items]

            result = {
                "success": True,
                "imported": len(items),
                "items": imported_titles,
                "message": f"Successfully imported {len(items)} items to Zotero",
            }

            # 加入 collection 資訊
            if target_key:
                result["saved_to"] = {"key": target_key, "name": target_name}
            else:
                result["saved_to"] = "My Library (root)"
                result["warning"] = "No collection specified - items saved to library root. Consider specifying collection_name."

            return result

        except Exception as e:
            logger.error(f"RIS import failed: {e}")
            return {
                "success": False,
                "error": str(e),
            }

    @mcp.tool()
    async def import_from_pmids(
        pmids: list[str],
        collection_name: str | None = None,
        collection_key: str | None = None,
        tags: list[str] | None = None,
        include_citation_metrics: bool = True,
    ) -> dict[str, Any]:
        """
        📥 Import PubMed articles directly by PMID

        ⚠️ DEPRECATED: Use `import_articles` instead for unified import!
        This tool is kept for backward compatibility.

        直接透過 PMID 匯入 PubMed 文獻到 Zotero

        Requires: pip install "zotero-keeper[pubmed]"

        🔄 NEW RECOMMENDED WORKFLOW:
        1. pubmed: search_literature("query") → articles
        2. keeper: import_articles(articles=articles, collection_name="...")

        📊 CITATION METRICS (RCR):
        When include_citation_metrics=True (default), automatically fetches
        Relative Citation Ratio from iCite and stores in Zotero's extra field.

        ⚠️ COLLECTION 防呆:
        - 若指定 collection_name/collection_key 但找不到，會回傳錯誤
        - 不會靜默存到 library root

        Alternative workflow (without pubmed extra):
        1. pubmed: search_literature("query") → PMIDs
        2. keeper: import_from_pmids(pmids, collection_name="My Collection")

        Args:
            pmids: List of PubMed IDs ["12345678", "87654321"]
            collection_name: Target collection name (recommended - human readable)
            collection_key: Target collection key (alternative)
            tags: Optional tags to add to all items
            include_citation_metrics: If True (default), fetch RCR from iCite

        Returns:
            Import result

        Example:
            import_from_pmids(
                pmids=["28968381", "28324054"],
                collection_name="ML Research",
                tags=["ML", "review"]
            )
        """
        if not PUBMED_AVAILABLE:
            return {
                "success": False,
                "error": "pubmed-search-mcp not installed",
                "hint": "Install with: pip install 'zotero-keeper[pubmed]'",
                "alternative": "Use import_ris_to_zotero with RIS text from pubmed-search-mcp's prepare_export tool",
            }

        try:
            # === 防呆機制: Collection 驗證 ===
            target_key = None
            target_name = None

            if collection_key:
                try:
                    col = await zotero_client.get_collection(collection_key)
                    target_key = collection_key
                    target_name = col.get("data", {}).get("name", collection_key)
                except Exception:
                    collections = await zotero_client.list_collections()
                    available = [
                        {"name": c.get("data", {}).get("name", ""), "key": c.get("key", "")}
                        for c in collections[:20]
                    ]
                    return {
                        "success": False,
                        "error": f"Collection key '{collection_key}' not found",
                        "available_collections": available,
                        "hint": "Use collection_name instead for human-readable names",
                    }

            elif collection_name:
                found = await zotero_client.find_collection_by_name(collection_name)
                if found:
                    target_key = found.get("key")
                    target_name = found.get("data", {}).get("name", collection_name)
                else:
                    collections = await zotero_client.list_collections()
                    available = [
                        {"name": c.get("data", {}).get("name", ""), "key": c.get("key", "")}
                        for c in collections[:20]
                    ]
                    return {
                        "success": False,
                        "error": f"Collection '{collection_name}' not found",
                        "available_collections": available,
                        "hint": "Check spelling or use list_collections to see all collections",
                    }

            import os
            email = os.environ.get("NCBI_EMAIL", "zotero-keeper@example.com")
            client = PubMedClient(email=email)

            # Fetch article details (returns dicts directly)
            articles = client.fetch_details(pmids)

            if not articles:
                return {
                    "success": False,
                    "message": "No articles found for given PMIDs",
                    "imported": 0,
                }

            # Enrich with citation metrics if requested
            citation_metrics_count = 0
            if include_citation_metrics:
                try:
                    from ..pubmed import enrich_articles_with_metrics
                    enrich_articles_with_metrics(articles, pmids)
                    citation_metrics_count = sum(
                        1 for a in articles if a.get("relative_citation_ratio")
                    )
                    logger.info(f"Enriched {citation_metrics_count} articles with RCR")
                except Exception as e:
                    logger.warning(f"Failed to fetch citation metrics: {e}")

            # Convert to Zotero format
            zotero_items = []
            for article in articles:
                item = _pmid_to_zotero_item(article)
                # 設定 collection
                if target_key:
                    item["collections"] = [target_key]
                if tags:
                    existing_tags = item.get("tags", [])
                    for tag in tags:
                        existing_tags.append({"tag": tag})
                    item["tags"] = existing_tags
                zotero_items.append(item)

            # Import to Zotero
            await zotero_client.save_items(zotero_items)

            # Build response
            imported_info = [
                {"pmid": a.get("pmid"), "title": a.get("title", "")[:50]}
                for a in articles
            ]

            result = {
                "success": True,
                "imported": len(zotero_items),
                "items": imported_info,
                "message": f"Successfully imported {len(zotero_items)} articles to Zotero",
            }

            if include_citation_metrics:
                result["citation_metrics_fetched"] = citation_metrics_count

            # 加入 collection 資訊
            if target_key:
                result["saved_to"] = {"key": target_key, "name": target_name}
            else:
                result["saved_to"] = "My Library (root)"
                result["warning"] = "No collection specified - items saved to library root. Consider specifying collection_name."

            return result

        except Exception as e:
            logger.error(f"PMID import failed: {e}")
            return {
                "success": False,
                "error": str(e),
            }

    logger.info("PubMed import tools registered (import_ris_to_zotero, import_from_pmids, quick_import_pmids)")

    @mcp.tool()
    async def quick_import_pmids(
        pmids: str,
        collection_name: str | None = None,
        tags: list[str] | None = None,
    ) -> dict[str, Any]:
        """
        ⚡ Quick import PMIDs to Zotero (one-step convenience tool)

        一鍵匯入 PMIDs 到 Zotero - 最簡單的匯入方式！

        ⭐ THIS IS THE EASIEST WAY TO IMPORT FROM PUBMED:
        - Just provide PMIDs (from search results or get_session_pmids)
        - Automatically fetches complete metadata
        - Optional: specify collection and tags

        ❗ IMPORTANT WORKFLOW:
        1. BEFORE importing, ask user which Collection to save to
        2. Use list_collections to show available collections
        3. Then call this tool with collection_name parameter

        ⚠️ COLLECTION 防呆機制:
        - 如果指定 collection_name 但找不到，會回傳錯誤和可用清單
        - 避免意外存到 Library root！
        - 不指定 collection_name 則存到 root（需明確知道）

        💡 GET PMIDs FROM:
        - search_pubmed_exclude_owned → new_pmids field
        - pubmed-search-mcp's get_session_pmids tool
        - Direct user input

        Compared to other import tools:
        - `batch_import_from_pubmed`: More options, collection validation, RCR metrics
        - `import_from_pmids`: Returns detailed result with citation metrics
        - `quick_import_pmids`: Simplest, just works! ⭐

        Args:
            pmids: Comma-separated PMIDs (e.g., "38353755,37864754")
            collection_name: Optional collection name to add items to (防呆: 找不到會報錯!)
            tags: Optional tags to add to all imported items

        Returns:
            Simple result with success/failure and count

        Example:
            quick_import_pmids(pmids="38353755,37864754")
            → {"success": true, "imported": 2, "message": "..."}

            quick_import_pmids(
                pmids="38353755",
                collection_name="AI Research",
                tags=["review"]
            )
        """
        try:
            # Parse PMIDs
            pmid_list = [p.strip() for p in pmids.split(",") if p.strip().isdigit()]

            if not pmid_list:
                return {
                    "success": False,
                    "error": "No valid PMIDs provided",
                    "hint": "Provide comma-separated PMIDs, e.g., '38353755,37864754'",
                }

            # Try to use batch_import if available (better metadata)
            from .batch_tools import is_batch_import_available
            if is_batch_import_available():
                from ..pubmed import fetch_pubmed_articles
                from ..mappers.pubmed_mapper import map_pubmed_to_zotero

                # === 防呆機制: Collection 驗證 ===
                collection_key = None
                collection_info = None
                if collection_name:
                    collections = await zotero_client.list_collections()
                    found = None
                    for col in collections:
                        if col.get("name", "").lower() == collection_name.lower():
                            found = col
                            collection_key = col.get("key")
                            break

                    # 如果找不到 collection，回傳錯誤！不是靜默存到 root！
                    if not found:
                        similar = [
                            c.get("name") for c in collections
                            if collection_name.lower() in c.get("name", "").lower()
                        ][:5]
                        return {
                            "success": False,
                            "error": f"Collection '{collection_name}' not found",
                            "hint": f"Similar: {similar}" if similar else "Use list_collections() first",
                            "available_collections": [
                                {"key": c.get("key"), "name": c.get("name")}
                                for c in collections[:10]
                            ],
                        }

                    collection_info = {"key": collection_key, "name": found.get("name")}
                    logger.info(f"Resolved collection '{collection_name}' → key: {collection_key}")

                # Fetch articles
                articles = fetch_pubmed_articles(pmid_list)
                if not articles:
                    return {
                        "success": False,
                        "error": "No articles found for provided PMIDs",
                    }

                # Convert to Zotero format
                collection_keys = [collection_key] if collection_key else None
                zotero_items = [
                    map_pubmed_to_zotero(article, extra_tags=tags, collection_keys=collection_keys)
                    for article in articles
                ]

                # Save to Zotero
                await zotero_client.batch_save_items(
                    items=zotero_items,
                    uri="http://mcp-bridge.local/quick-import-pmids",
                    title="Quick PubMed Import",
                )

                result = {
                    "success": True,
                    "imported": len(zotero_items),
                    "pmids": pmid_list,
                    "message": f"Successfully imported {len(zotero_items)} articles",
                }
                # 加入 collection_info 讓使用者確認
                if collection_info:
                    result["collection_info"] = collection_info
                else:
                    result["warning"] = "No collection specified - items saved to library root"
                return result

            # Fallback to import_from_pmids if pubmed package available
            elif PUBMED_AVAILABLE:
                import os
                email = os.environ.get("NCBI_EMAIL", "zotero-keeper@example.com")
                client = PubMedClient(email=email)
                articles = client.fetch_details(pmid_list)

                if not articles:
                    return {
                        "success": False,
                        "error": "No articles found",
                    }

                zotero_items = [_pmid_to_zotero_item(a) for a in articles]
                if tags:
                    for item in zotero_items:
                        item["tags"] = item.get("tags", []) + [{"tag": t} for t in tags]

                await zotero_client.save_items(zotero_items)

                return {
                    "success": True,
                    "imported": len(zotero_items),
                    "pmids": pmid_list,
                    "message": f"Successfully imported {len(zotero_items)} articles",
                }

            else:
                return {
                    "success": False,
                    "error": "PubMed integration not available",
                    "hint": "Install with: pip install 'zotero-keeper[pubmed]'",
                    "alternative": "Use import_ris_to_zotero with RIS text",
                }

        except Exception as e:
            logger.error(f"Quick import failed: {e}")
            return {
                "success": False,
                "error": str(e),
            }


def is_pubmed_available() -> bool:
    """Check if direct PMID import is available"""
    return PUBMED_AVAILABLE
