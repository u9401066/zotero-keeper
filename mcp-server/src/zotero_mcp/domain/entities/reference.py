"""Reference Entity - Core domain entity for bibliographic references"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional
from enum import Enum


class ItemType(str, Enum):
    """Zotero item types"""
    JOURNAL_ARTICLE = "journalArticle"
    BOOK = "book"
    BOOK_SECTION = "bookSection"
    CONFERENCE_PAPER = "conferencePaper"
    THESIS = "thesis"
    REPORT = "report"
    WEBPAGE = "webpage"
    PREPRINT = "preprint"
    PATENT = "patent"
    PRESENTATION = "presentation"
    DOCUMENT = "document"


@dataclass
class Creator:
    """Author/Creator value object"""
    last_name: str
    first_name: str = ""
    creator_type: str = "author"
    
    @property
    def full_name(self) -> str:
        if self.first_name:
            return f"{self.first_name} {self.last_name}"
        return self.last_name
    
    @classmethod
    def from_full_name(cls, name: str, creator_type: str = "author") -> "Creator":
        """Parse full name into first/last name"""
        parts = name.strip().split(maxsplit=1)
        if len(parts) == 1:
            return cls(last_name=parts[0], creator_type=creator_type)
        return cls(first_name=parts[0], last_name=parts[1], creator_type=creator_type)
    
    def to_dict(self) -> dict:
        return {
            "firstName": self.first_name,
            "lastName": self.last_name,
            "creatorType": self.creator_type,
        }


@dataclass
class Reference:
    """
    Reference Entity
    
    Represents a bibliographic reference in the Zotero library.
    This is the core domain entity.
    """
    title: str
    item_type: ItemType = ItemType.JOURNAL_ARTICLE
    key: Optional[str] = None
    creators: list[Creator] = field(default_factory=list)
    
    # Publication info
    date: Optional[str] = None
    doi: Optional[str] = None
    url: Optional[str] = None
    abstract: Optional[str] = None
    
    # Journal/Book info
    publication_title: Optional[str] = None
    volume: Optional[str] = None
    issue: Optional[str] = None
    pages: Optional[str] = None
    publisher: Optional[str] = None
    place: Optional[str] = None
    
    # Identifiers
    isbn: Optional[str] = None
    issn: Optional[str] = None
    
    # Metadata
    tags: list[str] = field(default_factory=list)
    collections: list[str] = field(default_factory=list)
    date_added: Optional[datetime] = None
    date_modified: Optional[datetime] = None
    
    @property
    def authors_string(self) -> str:
        """Get formatted authors string"""
        authors = [c for c in self.creators if c.creator_type == "author"]
        if not authors:
            return ""
        return ", ".join(c.full_name for c in authors)
    
    @property
    def citation_key(self) -> str:
        """Generate a citation key"""
        if not self.creators:
            first_word = self.title.split()[0] if self.title else "unknown"
            year = self.date[:4] if self.date else ""
            return f"{first_word}{year}"
        
        first_author = self.creators[0].last_name.lower()
        year = self.date[:4] if self.date else ""
        return f"{first_author}{year}"
    
    def to_zotero_dict(self) -> dict:
        """Convert to Zotero API format"""
        data: dict = {
            "itemType": self.item_type.value,
            "title": self.title,
        }
        
        if self.creators:
            data["creators"] = [c.to_dict() for c in self.creators]
        
        # Optional fields
        field_mappings = {
            "date": self.date,
            "DOI": self.doi,
            "url": self.url,
            "abstractNote": self.abstract,
            "publicationTitle": self.publication_title,
            "volume": self.volume,
            "issue": self.issue,
            "pages": self.pages,
            "publisher": self.publisher,
            "place": self.place,
            "ISBN": self.isbn,
            "ISSN": self.issn,
        }
        
        for key, value in field_mappings.items():
            if value:
                data[key] = value
        
        if self.tags:
            data["tags"] = [{"tag": t} for t in self.tags]
        
        if self.collections:
            data["collections"] = self.collections
        
        return data
    
    @classmethod
    def from_zotero_dict(cls, data: dict) -> "Reference":
        """Create Reference from Zotero API response"""
        creators = []
        for c in data.get("creators", []):
            creators.append(Creator(
                first_name=c.get("firstName", ""),
                last_name=c.get("lastName", c.get("name", "")),
                creator_type=c.get("creatorType", "author"),
            ))
        
        tags = [t["tag"] if isinstance(t, dict) else t for t in data.get("tags", [])]
        
        return cls(
            key=data.get("key"),
            title=data.get("title", ""),
            item_type=ItemType(data.get("itemType", "journalArticle")),
            creators=creators,
            date=data.get("date"),
            doi=data.get("DOI"),
            url=data.get("url"),
            abstract=data.get("abstractNote"),
            publication_title=data.get("publicationTitle"),
            volume=data.get("volume"),
            issue=data.get("issue"),
            pages=data.get("pages"),
            publisher=data.get("publisher"),
            place=data.get("place"),
            isbn=data.get("ISBN"),
            issn=data.get("ISSN"),
            tags=tags,
            collections=data.get("collections", []),
        )
