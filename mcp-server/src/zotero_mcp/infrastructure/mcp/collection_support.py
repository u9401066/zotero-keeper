"""Shared helpers for validating and formatting Zotero collection targets."""

from __future__ import annotations

from typing import Any


async def resolve_collection_target(
    zotero_client: Any,
    *,
    collection_name: str | None = None,
    collection_key: str | None = None,
    available_limit: int = 20,
    include_similar: bool = False,
    fallback_to_unvalidated_key: bool = False,
) -> dict[str, Any]:
    """Resolve a target collection and return either normalized info or an error payload."""
    if not collection_name and not collection_key:
        return {
            "success": True,
            "target_key": None,
            "target_name": None,
            "collection_info": None,
        }

    if collection_key:
        try:
            col = await zotero_client.get_collection(collection_key)
            name = col.get("data", {}).get("name", collection_key)
            return {
                "success": True,
                "target_key": collection_key,
                "target_name": name,
                "collection_info": {"key": collection_key, "name": name, "resolved_from": "key"},
            }
        except Exception as exc:
            if fallback_to_unvalidated_key:
                return {
                    "success": True,
                    "target_key": collection_key,
                    "target_name": "unknown (validation failed)",
                    "collection_info": {
                        "key": collection_key,
                        "name": "unknown (validation failed)",
                        "warning": str(exc),
                    },
                }

            collections = await zotero_client.get_collections()
            available = [
                {"name": c.get("data", {}).get("name", ""), "key": c.get("key", "")}
                for c in collections[:available_limit]
            ]
            return {
                "success": False,
                "error": f"Collection key '{collection_key}' not found",
                "available_collections": available,
                "hint": "Use collection_name instead for human-readable names",
            }

    found = await zotero_client.find_collection_by_name(collection_name)
    if found:
        key = found.get("key")
        name = found.get("data", {}).get("name", collection_name)
        return {
            "success": True,
            "target_key": key,
            "target_name": name,
            "collection_info": {"key": key, "name": name, "resolved_from": "name"},
        }

    collections = await zotero_client.get_collections()
    available = [
        {"name": c.get("data", {}).get("name", ""), "key": c.get("key", "")}
        for c in collections[:available_limit]
    ]
    result: dict[str, Any] = {
        "success": False,
        "error": f"Collection '{collection_name}' not found",
        "available_collections": available,
        "hint": "Check spelling or use list_collections to see all collections",
    }

    if include_similar and collection_name:
        similar = [
            c.get("data", {}).get("name", "")
            for c in collections
            if collection_name.lower() in c.get("data", {}).get("name", "").lower()
        ][:5]
        if similar:
            result["hint"] = f"Similar collections: {similar}"

    return result


def apply_collection_and_tags(item: dict[str, Any], *, collection_key: str | None = None, tags: list[str] | None = None) -> dict[str, Any]:
    """Mutate a Zotero item with optional collection and tags, then return it."""
    if collection_key:
        item["collections"] = [collection_key]

    if tags:
        existing_tags = item.get("tags", [])
        existing_tags.extend({"tag": tag} for tag in tags)
        item["tags"] = existing_tags

    return item