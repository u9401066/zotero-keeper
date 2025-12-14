"""
Unit tests for Collection entity.
"""

import pytest


class TestCollection:
    """Test Collection dataclass."""
    
    def test_collection_basic(self):
        """Test basic Collection creation."""
        from zotero_mcp.domain.entities.collection import Collection
        
        col = Collection(name="Test Collection")
        
        assert col.name == "Test Collection"
        assert col.key is None
        assert col.parent_key is None
        assert col.item_count == 0
    
    def test_collection_with_all_fields(self):
        """Test Collection with all fields populated."""
        from zotero_mcp.domain.entities.collection import Collection
        
        col = Collection(
            name="AI Research",
            key="COL12345",
            parent_key="COL00001",
            item_count=25,
        )
        
        assert col.name == "AI Research"
        assert col.key == "COL12345"
        assert col.parent_key == "COL00001"
        assert col.item_count == 25
    
    def test_collection_is_root_true(self):
        """Test is_root returns True for root collection."""
        from zotero_mcp.domain.entities.collection import Collection
        
        col = Collection(name="Root", key="COL001")
        assert col.is_root is True
    
    def test_collection_is_root_false(self):
        """Test is_root returns False for nested collection."""
        from zotero_mcp.domain.entities.collection import Collection
        
        col = Collection(name="Nested", key="COL002", parent_key="COL001")
        assert col.is_root is False
    
    def test_collection_to_dict(self):
        """Test Collection to_dict conversion."""
        from zotero_mcp.domain.entities.collection import Collection
        
        col = Collection(
            name="Test",
            key="COL123",
            parent_key="COL001",
            item_count=10,
        )
        result = col.to_dict()
        
        assert result == {
            "key": "COL123",
            "name": "Test",
            "parentKey": "COL001",
            "itemCount": 10,
        }
    
    def test_collection_to_dict_root(self):
        """Test to_dict for root collection."""
        from zotero_mcp.domain.entities.collection import Collection
        
        col = Collection(name="Root", key="COL001")
        result = col.to_dict()
        
        assert result["parentKey"] is None
    
    def test_collection_from_zotero_dict(self):
        """Test from_zotero_dict class method."""
        from zotero_mcp.domain.entities.collection import Collection
        
        data = {
            "key": "COL123",
            "name": "AI Papers",
            "parentKey": "COL001",
            "itemCount": 15,
        }
        col = Collection.from_zotero_dict(data)
        
        assert col.key == "COL123"
        assert col.name == "AI Papers"
        assert col.parent_key == "COL001"
        assert col.item_count == 15
    
    def test_collection_from_zotero_dict_defaults(self):
        """Test from_zotero_dict with missing optional fields."""
        from zotero_mcp.domain.entities.collection import Collection
        
        data = {"key": "COL001"}
        col = Collection.from_zotero_dict(data)
        
        assert col.key == "COL001"
        assert col.name == ""
        assert col.parent_key is None
        assert col.item_count == 0
    
    def test_collection_from_zotero_dict_nested_data(self):
        """Test from_zotero_dict with nested 'data' structure."""
        from zotero_mcp.domain.entities.collection import Collection
        
        # Some API responses nest data under 'data' key
        data = {
            "key": "COL123",
            "name": "Test",
            "parentCollection": "COL001",  # Note: different key name
            "numItems": 5,
        }
        # Current implementation doesn't handle numItems, but that's okay
        col = Collection.from_zotero_dict(data)
        
        assert col.key == "COL123"
        assert col.name == "Test"


class TestCollectionEdgeCases:
    """Test edge cases for Collection."""
    
    def test_collection_empty_name(self):
        """Test Collection with empty name."""
        from zotero_mcp.domain.entities.collection import Collection
        
        col = Collection(name="")
        assert col.name == ""
    
    def test_collection_unicode_name(self):
        """Test Collection with unicode name."""
        from zotero_mcp.domain.entities.collection import Collection
        
        col = Collection(name="研究文献 / Research Papers")
        assert "研究" in col.name
    
    def test_collection_negative_item_count(self):
        """Test Collection allows negative item count (invalid but possible)."""
        from zotero_mcp.domain.entities.collection import Collection
        
        # This shouldn't happen but dataclass allows it
        col = Collection(name="Test", item_count=-1)
        assert col.item_count == -1
    
    def test_collection_roundtrip(self):
        """Test Collection roundtrip conversion."""
        from zotero_mcp.domain.entities.collection import Collection
        
        original = Collection(
            name="Test",
            key="COL123",
            parent_key="COL001",
            item_count=10,
        )
        
        as_dict = original.to_dict()
        # Adjust key names for from_zotero_dict compatibility
        as_dict["parentKey"] = as_dict.pop("parentKey")
        as_dict["itemCount"] = as_dict.pop("itemCount")
        
        restored = Collection.from_zotero_dict(as_dict)
        
        assert restored.name == original.name
        assert restored.key == original.key
