"""
Unit tests for Reference, Creator, and ItemType entities.

Tests all methods and properties of the Reference domain entity.
"""

import pytest
from datetime import datetime


class TestItemType:
    """Test ItemType enum."""
    
    def test_item_type_values(self):
        """Test ItemType enum has expected values."""
        from zotero_mcp.domain.entities.reference import ItemType
        
        assert ItemType.JOURNAL_ARTICLE.value == "journalArticle"
        assert ItemType.BOOK.value == "book"
        assert ItemType.BOOK_SECTION.value == "bookSection"
        assert ItemType.CONFERENCE_PAPER.value == "conferencePaper"
        assert ItemType.THESIS.value == "thesis"
        assert ItemType.REPORT.value == "report"
        assert ItemType.WEBPAGE.value == "webpage"
        assert ItemType.PREPRINT.value == "preprint"
        assert ItemType.PATENT.value == "patent"
        assert ItemType.PRESENTATION.value == "presentation"
        assert ItemType.DOCUMENT.value == "document"
    
    def test_item_type_is_string_enum(self):
        """Test ItemType is a string enum."""
        from zotero_mcp.domain.entities.reference import ItemType
        
        assert isinstance(ItemType.JOURNAL_ARTICLE, str)
        assert ItemType.JOURNAL_ARTICLE == "journalArticle"
    
    def test_item_type_from_string(self):
        """Test creating ItemType from string."""
        from zotero_mcp.domain.entities.reference import ItemType
        
        item_type = ItemType("journalArticle")
        assert item_type == ItemType.JOURNAL_ARTICLE
    
    def test_item_type_invalid_value(self):
        """Test ItemType with invalid value raises error."""
        from zotero_mcp.domain.entities.reference import ItemType
        
        with pytest.raises(ValueError):
            ItemType("invalidType")


class TestCreator:
    """Test Creator dataclass."""
    
    def test_creator_basic(self):
        """Test basic Creator creation."""
        from zotero_mcp.domain.entities.reference import Creator
        
        creator = Creator(last_name="Smith", first_name="John")
        
        assert creator.last_name == "Smith"
        assert creator.first_name == "John"
        assert creator.creator_type == "author"
    
    def test_creator_full_name_with_first_name(self):
        """Test full_name property with first name."""
        from zotero_mcp.domain.entities.reference import Creator
        
        creator = Creator(last_name="Smith", first_name="John")
        assert creator.full_name == "John Smith"
    
    def test_creator_full_name_without_first_name(self):
        """Test full_name property without first name."""
        from zotero_mcp.domain.entities.reference import Creator
        
        creator = Creator(last_name="Smith")
        assert creator.full_name == "Smith"
    
    def test_creator_from_full_name_two_parts(self):
        """Test from_full_name with first and last name."""
        from zotero_mcp.domain.entities.reference import Creator
        
        creator = Creator.from_full_name("John Smith")
        
        assert creator.first_name == "John"
        assert creator.last_name == "Smith"
        assert creator.creator_type == "author"
    
    def test_creator_from_full_name_single_part(self):
        """Test from_full_name with single name."""
        from zotero_mcp.domain.entities.reference import Creator
        
        creator = Creator.from_full_name("Madonna")
        
        assert creator.first_name == ""
        assert creator.last_name == "Madonna"
    
    def test_creator_from_full_name_multiple_parts(self):
        """Test from_full_name with multiple parts."""
        from zotero_mcp.domain.entities.reference import Creator
        
        creator = Creator.from_full_name("John Paul Smith")
        
        assert creator.first_name == "John"
        assert creator.last_name == "Paul Smith"
    
    def test_creator_from_full_name_custom_type(self):
        """Test from_full_name with custom creator type."""
        from zotero_mcp.domain.entities.reference import Creator
        
        creator = Creator.from_full_name("Jane Doe", creator_type="editor")
        
        assert creator.creator_type == "editor"
    
    def test_creator_from_full_name_with_whitespace(self):
        """Test from_full_name handles whitespace."""
        from zotero_mcp.domain.entities.reference import Creator
        
        creator = Creator.from_full_name("  John   Smith  ")
        
        assert creator.first_name == "John"
        assert creator.last_name == "Smith"
    
    def test_creator_to_dict(self):
        """Test Creator to_dict conversion."""
        from zotero_mcp.domain.entities.reference import Creator
        
        creator = Creator(last_name="Smith", first_name="John", creator_type="editor")
        result = creator.to_dict()
        
        assert result == {
            "firstName": "John",
            "lastName": "Smith",
            "creatorType": "editor",
        }


class TestReference:
    """Test Reference dataclass."""
    
    def test_reference_basic(self):
        """Test basic Reference creation."""
        from zotero_mcp.domain.entities.reference import Reference, ItemType
        
        ref = Reference(title="Test Article")
        
        assert ref.title == "Test Article"
        assert ref.item_type == ItemType.JOURNAL_ARTICLE
        assert ref.key is None
        assert ref.creators == []
        assert ref.tags == []
    
    def test_reference_with_all_fields(self):
        """Test Reference with all fields populated."""
        from zotero_mcp.domain.entities.reference import Reference, ItemType, Creator
        
        ref = Reference(
            title="Complete Test",
            item_type=ItemType.BOOK,
            key="ABC123",
            creators=[Creator(last_name="Author", first_name="Test")],
            date="2024-01-15",
            doi="10.1234/test",
            url="https://example.com",
            abstract="Test abstract",
            publication_title="Test Publisher",
            volume="1",
            issue="2",
            pages="10-20",
            publisher="Publisher Inc",
            place="New York",
            isbn="978-1234567890",
            issn="1234-5678",
            tags=["tag1", "tag2"],
            collections=["COL001"],
        )
        
        assert ref.key == "ABC123"
        assert ref.item_type == ItemType.BOOK
        assert len(ref.creators) == 1
        assert ref.volume == "1"
    
    def test_reference_authors_string_empty(self):
        """Test authors_string with no creators."""
        from zotero_mcp.domain.entities.reference import Reference
        
        ref = Reference(title="Test")
        assert ref.authors_string == ""
    
    def test_reference_authors_string_single(self):
        """Test authors_string with single author."""
        from zotero_mcp.domain.entities.reference import Reference, Creator
        
        ref = Reference(
            title="Test",
            creators=[Creator(last_name="Smith", first_name="John")]
        )
        assert ref.authors_string == "John Smith"
    
    def test_reference_authors_string_multiple(self):
        """Test authors_string with multiple authors."""
        from zotero_mcp.domain.entities.reference import Reference, Creator
        
        ref = Reference(
            title="Test",
            creators=[
                Creator(last_name="Smith", first_name="John"),
                Creator(last_name="Doe", first_name="Jane"),
            ]
        )
        assert ref.authors_string == "John Smith, Jane Doe"
    
    def test_reference_authors_string_filters_by_type(self):
        """Test authors_string only includes authors, not editors."""
        from zotero_mcp.domain.entities.reference import Reference, Creator
        
        ref = Reference(
            title="Test",
            creators=[
                Creator(last_name="Author", first_name="Main", creator_type="author"),
                Creator(last_name="Editor", first_name="Book", creator_type="editor"),
            ]
        )
        assert ref.authors_string == "Main Author"
    
    def test_reference_citation_key_no_creators(self):
        """Test citation_key without creators uses title."""
        from zotero_mcp.domain.entities.reference import Reference
        
        ref = Reference(title="Machine Learning Study", date="2024")
        assert ref.citation_key == "Machine2024"
    
    def test_reference_citation_key_no_creators_no_date(self):
        """Test citation_key without creators or date."""
        from zotero_mcp.domain.entities.reference import Reference
        
        ref = Reference(title="Test Article")
        assert ref.citation_key == "Test"
    
    def test_reference_citation_key_with_creator(self):
        """Test citation_key with creator."""
        from zotero_mcp.domain.entities.reference import Reference, Creator
        
        ref = Reference(
            title="Test",
            creators=[Creator(last_name="Smith")],
            date="2024-01-15",
        )
        assert ref.citation_key == "smith2024"
    
    def test_reference_citation_key_empty_title(self):
        """Test citation_key with empty title."""
        from zotero_mcp.domain.entities.reference import Reference
        
        ref = Reference(title="")
        assert ref.citation_key == "unknown"
    
    def test_reference_to_zotero_dict_basic(self):
        """Test to_zotero_dict basic conversion."""
        from zotero_mcp.domain.entities.reference import Reference, ItemType
        
        ref = Reference(title="Test Article")
        result = ref.to_zotero_dict()
        
        assert result["itemType"] == "journalArticle"
        assert result["title"] == "Test Article"
        assert "creators" not in result
    
    def test_reference_to_zotero_dict_with_creators(self):
        """Test to_zotero_dict with creators."""
        from zotero_mcp.domain.entities.reference import Reference, Creator
        
        ref = Reference(
            title="Test",
            creators=[Creator(last_name="Smith", first_name="John")],
        )
        result = ref.to_zotero_dict()
        
        assert "creators" in result
        assert len(result["creators"]) == 1
        assert result["creators"][0]["lastName"] == "Smith"
    
    def test_reference_to_zotero_dict_with_optional_fields(self):
        """Test to_zotero_dict includes only non-None fields."""
        from zotero_mcp.domain.entities.reference import Reference
        
        ref = Reference(
            title="Test",
            doi="10.1234/test",
            volume="1",
        )
        result = ref.to_zotero_dict()
        
        assert result["DOI"] == "10.1234/test"
        assert result["volume"] == "1"
        assert "issue" not in result
        assert "pages" not in result
    
    def test_reference_to_zotero_dict_with_tags(self):
        """Test to_zotero_dict with tags."""
        from zotero_mcp.domain.entities.reference import Reference
        
        ref = Reference(title="Test", tags=["tag1", "tag2"])
        result = ref.to_zotero_dict()
        
        assert result["tags"] == [{"tag": "tag1"}, {"tag": "tag2"}]
    
    def test_reference_to_zotero_dict_with_collections(self):
        """Test to_zotero_dict with collections."""
        from zotero_mcp.domain.entities.reference import Reference
        
        ref = Reference(title="Test", collections=["COL001", "COL002"])
        result = ref.to_zotero_dict()
        
        assert result["collections"] == ["COL001", "COL002"]
    
    def test_reference_from_zotero_dict_basic(self):
        """Test from_zotero_dict basic conversion."""
        from zotero_mcp.domain.entities.reference import Reference, ItemType
        
        data = {
            "key": "ABC123",
            "title": "Test Article",
            "itemType": "journalArticle",
        }
        ref = Reference.from_zotero_dict(data)
        
        assert ref.key == "ABC123"
        assert ref.title == "Test Article"
        assert ref.item_type == ItemType.JOURNAL_ARTICLE
    
    def test_reference_from_zotero_dict_with_creators(self):
        """Test from_zotero_dict with creators."""
        from zotero_mcp.domain.entities.reference import Reference
        
        data = {
            "title": "Test",
            "itemType": "journalArticle",
            "creators": [
                {"firstName": "John", "lastName": "Smith", "creatorType": "author"},
            ],
        }
        ref = Reference.from_zotero_dict(data)
        
        assert len(ref.creators) == 1
        assert ref.creators[0].first_name == "John"
        assert ref.creators[0].last_name == "Smith"
    
    def test_reference_from_zotero_dict_creator_with_name(self):
        """Test from_zotero_dict with creator using 'name' field."""
        from zotero_mcp.domain.entities.reference import Reference
        
        data = {
            "title": "Test",
            "itemType": "journalArticle",
            "creators": [
                {"name": "Organization Name", "creatorType": "author"},
            ],
        }
        ref = Reference.from_zotero_dict(data)
        
        assert ref.creators[0].last_name == "Organization Name"
    
    def test_reference_from_zotero_dict_with_tags_dict(self):
        """Test from_zotero_dict with tags as dict objects."""
        from zotero_mcp.domain.entities.reference import Reference
        
        data = {
            "title": "Test",
            "itemType": "journalArticle",
            "tags": [{"tag": "tag1"}, {"tag": "tag2"}],
        }
        ref = Reference.from_zotero_dict(data)
        
        assert ref.tags == ["tag1", "tag2"]
    
    def test_reference_from_zotero_dict_with_tags_strings(self):
        """Test from_zotero_dict with tags as plain strings."""
        from zotero_mcp.domain.entities.reference import Reference
        
        data = {
            "title": "Test",
            "itemType": "journalArticle",
            "tags": ["tag1", "tag2"],
        }
        ref = Reference.from_zotero_dict(data)
        
        assert ref.tags == ["tag1", "tag2"]
    
    def test_reference_from_zotero_dict_with_all_fields(self):
        """Test from_zotero_dict with all optional fields."""
        from zotero_mcp.domain.entities.reference import Reference
        
        data = {
            "key": "ABC123",
            "title": "Complete Test",
            "itemType": "book",
            "date": "2024",
            "DOI": "10.1234/test",
            "url": "https://example.com",
            "abstractNote": "Test abstract",
            "publicationTitle": "Test Journal",
            "volume": "1",
            "issue": "2",
            "pages": "10-20",
            "publisher": "Publisher",
            "place": "City",
            "ISBN": "1234567890",
            "ISSN": "1234-5678",
            "collections": ["COL001"],
        }
        ref = Reference.from_zotero_dict(data)
        
        assert ref.doi == "10.1234/test"
        assert ref.abstract == "Test abstract"
        assert ref.publication_title == "Test Journal"
        assert ref.isbn == "1234567890"


class TestReferenceEdgeCases:
    """Test edge cases and boundary conditions."""
    
    def test_reference_empty_title(self):
        """Test Reference with empty title."""
        from zotero_mcp.domain.entities.reference import Reference
        
        ref = Reference(title="")
        assert ref.title == ""
    
    def test_reference_unicode_title(self):
        """Test Reference with unicode characters."""
        from zotero_mcp.domain.entities.reference import Reference
        
        ref = Reference(title="日本語タイトル: 機械学習の研究")
        assert "日本語" in ref.title
    
    def test_creator_unicode_name(self):
        """Test Creator with unicode names."""
        from zotero_mcp.domain.entities.reference import Creator
        
        creator = Creator(last_name="田中", first_name="太郎")
        assert creator.full_name == "太郎 田中"
    
    def test_reference_from_zotero_dict_missing_item_type(self):
        """Test from_zotero_dict with missing itemType defaults to journalArticle."""
        from zotero_mcp.domain.entities.reference import Reference, ItemType
        
        data = {"title": "Test"}
        ref = Reference.from_zotero_dict(data)
        
        assert ref.item_type == ItemType.JOURNAL_ARTICLE
    
    def test_reference_from_zotero_dict_empty_creators(self):
        """Test from_zotero_dict with empty creators list."""
        from zotero_mcp.domain.entities.reference import Reference
        
        data = {"title": "Test", "itemType": "journalArticle", "creators": []}
        ref = Reference.from_zotero_dict(data)
        
        assert ref.creators == []
    
    def test_reference_roundtrip_conversion(self):
        """Test Reference survives to_zotero_dict -> from_zotero_dict roundtrip."""
        from zotero_mcp.domain.entities.reference import Reference, Creator, ItemType
        
        original = Reference(
            title="Roundtrip Test",
            item_type=ItemType.BOOK,
            creators=[Creator(last_name="Author", first_name="Test")],
            date="2024",
            doi="10.1234/test",
            tags=["test"],
        )
        
        as_dict = original.to_zotero_dict()
        restored = Reference.from_zotero_dict(as_dict)
        
        assert restored.title == original.title
        assert restored.item_type == original.item_type
        assert len(restored.creators) == len(original.creators)
        assert restored.date == original.date
        assert restored.doi == original.doi
        assert restored.tags == original.tags
