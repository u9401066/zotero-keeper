"""Collection Entity - Represents a Zotero collection (folder)"""

from dataclasses import dataclass


@dataclass
class Collection:
    """
    Collection Entity

    Represents a collection (folder) in the Zotero library.
    Collections can be nested (have parent collections).
    """
    name: str
    key: str | None = None
    parent_key: str | None = None
    item_count: int = 0

    @property
    def is_root(self) -> bool:
        """Check if this is a root-level collection"""
        return self.parent_key is None

    def to_dict(self) -> dict:
        """Convert to dictionary"""
        return {
            "key": self.key,
            "name": self.name,
            "parentKey": self.parent_key,
            "itemCount": self.item_count,
        }

    @classmethod
    def from_zotero_dict(cls, data: dict) -> "Collection":
        """Create Collection from Zotero API response"""
        return cls(
            key=data.get("key"),
            name=data.get("name", ""),
            parent_key=data.get("parentKey"),
            item_count=data.get("itemCount", 0),
        )
