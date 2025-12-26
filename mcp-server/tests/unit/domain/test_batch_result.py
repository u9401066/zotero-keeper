"""
Unit tests for BatchImportResult and related entities.
"""

import pytest


class TestImportAction:
    """Test ImportAction enum."""
    
    def test_import_action_values(self):
        """Test ImportAction enum has expected values."""
        from zotero_mcp.domain.entities.batch_result import ImportAction
        
        assert ImportAction.ADDED.value == "added"
        assert ImportAction.SKIPPED.value == "skipped"
        assert ImportAction.WARNING.value == "warning"
        assert ImportAction.FAILED.value == "failed"
    
    def test_import_action_all_values(self):
        """Test all ImportAction values are accessible."""
        from zotero_mcp.domain.entities.batch_result import ImportAction
        
        actions = list(ImportAction)
        assert len(actions) == 4


class TestImportedItem:
    """Test ImportedItem dataclass."""
    
    def test_imported_item_basic(self):
        """Test basic ImportedItem creation."""
        from zotero_mcp.domain.entities.batch_result import ImportedItem, ImportAction
        
        item = ImportedItem(
            pmid="12345678",
            title="Test Article",
            action=ImportAction.ADDED,
        )
        
        assert item.pmid == "12345678"
        assert item.title == "Test Article"
        assert item.action == ImportAction.ADDED
        assert item.zotero_key is None
        assert item.reason is None
        assert item.warning is None
        assert item.error is None
    
    def test_imported_item_with_key(self):
        """Test ImportedItem with Zotero key."""
        from zotero_mcp.domain.entities.batch_result import ImportedItem, ImportAction
        
        item = ImportedItem(
            pmid="12345678",
            title="Test",
            action=ImportAction.ADDED,
            zotero_key="ABC123",
        )
        
        assert item.zotero_key == "ABC123"
    
    def test_imported_item_skipped_with_reason(self):
        """Test skipped ImportedItem with reason."""
        from zotero_mcp.domain.entities.batch_result import ImportedItem, ImportAction
        
        item = ImportedItem(
            pmid="12345678",
            title="Duplicate Article",
            action=ImportAction.SKIPPED,
            reason="PMID already exists",
        )
        
        assert item.action == ImportAction.SKIPPED
        assert item.reason == "PMID already exists"
    
    def test_imported_item_failed_with_error(self):
        """Test failed ImportedItem with error."""
        from zotero_mcp.domain.entities.batch_result import ImportedItem, ImportAction
        
        item = ImportedItem(
            pmid="12345678",
            title="Failed Article",
            action=ImportAction.FAILED,
            error="Network timeout",
        )
        
        assert item.action == ImportAction.FAILED
        assert item.error == "Network timeout"
    
    def test_imported_item_warning_with_message(self):
        """Test ImportedItem with warning."""
        from zotero_mcp.domain.entities.batch_result import ImportedItem, ImportAction
        
        item = ImportedItem(
            pmid="12345678",
            title="Partial Article",
            action=ImportAction.WARNING,
            warning="Missing abstract",
        )
        
        assert item.action == ImportAction.WARNING
        assert item.warning == "Missing abstract"
    
    def test_imported_item_to_dict_basic(self):
        """Test ImportedItem to_dict basic output."""
        from zotero_mcp.domain.entities.batch_result import ImportedItem, ImportAction
        
        item = ImportedItem(
            pmid="12345678",
            title="Test",
            action=ImportAction.ADDED,
        )
        result = item.to_dict()
        
        assert result == {
            "pmid": "12345678",
            "title": "Test",
            "action": "added",
        }
    
    def test_imported_item_to_dict_with_optional_fields(self):
        """Test ImportedItem to_dict includes optional fields when present."""
        from zotero_mcp.domain.entities.batch_result import ImportedItem, ImportAction
        
        item = ImportedItem(
            pmid="12345678",
            title="Test",
            action=ImportAction.SKIPPED,
            zotero_key="ABC123",
            reason="Duplicate",
            warning="Metadata incomplete",
            error="Minor error",
        )
        result = item.to_dict()
        
        assert result["key"] == "ABC123"
        assert result["reason"] == "Duplicate"
        assert result["warning"] == "Metadata incomplete"
        assert result["error"] == "Minor error"


class TestBatchImportResult:
    """Test BatchImportResult dataclass."""
    
    def test_batch_import_result_default(self):
        """Test BatchImportResult default values."""
        from zotero_mcp.domain.entities.batch_result import BatchImportResult
        
        result = BatchImportResult()
        
        assert result.success is True
        assert result.total == 0
        assert result.added == 0
        assert result.skipped == 0
        assert result.warnings == 0
        assert result.failed == 0
        assert result.added_items == []
        assert result.skipped_items == []
        assert result.warning_items == []
        assert result.failed_items == []
        assert result.collection_key is None
        assert result.elapsed_time == 0.0
    
    def test_batch_import_result_add_item_added(self):
        """Test add_item with ADDED action."""
        from zotero_mcp.domain.entities.batch_result import (
            BatchImportResult, ImportedItem, ImportAction
        )
        
        result = BatchImportResult()
        item = ImportedItem(
            pmid="12345678",
            title="Test",
            action=ImportAction.ADDED,
        )
        
        result.add_item(item)
        
        assert result.total == 1
        assert result.added == 1
        assert len(result.added_items) == 1
        assert result.success is True
    
    def test_batch_import_result_add_item_skipped(self):
        """Test add_item with SKIPPED action."""
        from zotero_mcp.domain.entities.batch_result import (
            BatchImportResult, ImportedItem, ImportAction
        )
        
        result = BatchImportResult()
        item = ImportedItem(
            pmid="12345678",
            title="Duplicate",
            action=ImportAction.SKIPPED,
            reason="Already exists",
        )
        
        result.add_item(item)
        
        assert result.total == 1
        assert result.skipped == 1
        assert len(result.skipped_items) == 1
        assert result.success is True  # Skipped doesn't fail
    
    def test_batch_import_result_add_item_warning(self):
        """Test add_item with WARNING action."""
        from zotero_mcp.domain.entities.batch_result import (
            BatchImportResult, ImportedItem, ImportAction
        )
        
        result = BatchImportResult()
        item = ImportedItem(
            pmid="12345678",
            title="Partial",
            action=ImportAction.WARNING,
            warning="Missing data",
        )
        
        result.add_item(item)
        
        assert result.total == 1
        assert result.warnings == 1
        assert len(result.warning_items) == 1
        assert result.success is True  # Warning doesn't fail
    
    def test_batch_import_result_add_item_failed(self):
        """Test add_item with FAILED action sets success to False."""
        from zotero_mcp.domain.entities.batch_result import (
            BatchImportResult, ImportedItem, ImportAction
        )
        
        result = BatchImportResult()
        item = ImportedItem(
            pmid="12345678",
            title="Failed",
            action=ImportAction.FAILED,
            error="Network error",
        )
        
        result.add_item(item)
        
        assert result.total == 1
        assert result.failed == 1
        assert len(result.failed_items) == 1
        assert result.success is False  # Failed sets success to False
    
    def test_batch_import_result_multiple_items(self):
        """Test add_item with multiple items."""
        from zotero_mcp.domain.entities.batch_result import (
            BatchImportResult, ImportedItem, ImportAction
        )
        
        result = BatchImportResult()
        
        # Add various items
        result.add_item(ImportedItem("1", "Added 1", ImportAction.ADDED))
        result.add_item(ImportedItem("2", "Added 2", ImportAction.ADDED))
        result.add_item(ImportedItem("3", "Skipped", ImportAction.SKIPPED, reason="Dup"))
        result.add_item(ImportedItem("4", "Warning", ImportAction.WARNING))
        result.add_item(ImportedItem("5", "Failed", ImportAction.FAILED, error="Err"))
        
        assert result.total == 5
        assert result.added == 2
        assert result.skipped == 1
        assert result.warnings == 1
        assert result.failed == 1
        assert result.success is False
    
    def test_batch_import_result_to_dict(self):
        """Test BatchImportResult to_dict output."""
        from zotero_mcp.domain.entities.batch_result import (
            BatchImportResult, ImportedItem, ImportAction
        )
        
        result = BatchImportResult()
        result.add_item(ImportedItem("1", "Test", ImportAction.ADDED))
        result.collection_key = "COL001"
        result.elapsed_time = 5.678
        
        output = result.to_dict()
        
        assert output["success"] is True
        assert output["total"] == 1
        assert output["added"] == 1
        assert output["skipped"] == 0
        assert output["warnings"] == 0
        assert output["failed"] == 0
        assert len(output["added_items"]) == 1
        assert output["target"]["collection_key"] == "COL001"
        assert output["elapsed_time"] == 5.68  # Rounded to 2 decimals
    
    def test_batch_import_result_summary_basic(self):
        """Test summary method basic output."""
        from zotero_mcp.domain.entities.batch_result import BatchImportResult
        
        result = BatchImportResult()
        result.elapsed_time = 1.5
        
        summary = result.summary()
        assert "Total: 0" in summary
        assert "Time: 1.5s" in summary
    
    def test_batch_import_result_summary_with_all_counts(self):
        """Test summary method with all counts."""
        from zotero_mcp.domain.entities.batch_result import (
            BatchImportResult, ImportedItem, ImportAction
        )
        
        result = BatchImportResult()
        result.add_item(ImportedItem("1", "A1", ImportAction.ADDED))
        result.add_item(ImportedItem("2", "A2", ImportAction.ADDED))
        result.add_item(ImportedItem("3", "S1", ImportAction.SKIPPED, reason="Dup"))
        result.add_item(ImportedItem("4", "W1", ImportAction.WARNING))
        result.add_item(ImportedItem("5", "F1", ImportAction.FAILED, error="Err"))
        result.elapsed_time = 12.345
        
        summary = result.summary()
        
        assert "Total: 5" in summary
        assert "Added: 2" in summary
        assert "Skipped: 1" in summary
        assert "Warnings: 1" in summary
        assert "Failed: 1" in summary
        assert "Time: 12.3s" in summary
    
    def test_batch_import_result_summary_omits_zero_counts(self):
        """Test summary method omits zero counts."""
        from zotero_mcp.domain.entities.batch_result import (
            BatchImportResult, ImportedItem, ImportAction
        )
        
        result = BatchImportResult()
        result.add_item(ImportedItem("1", "Test", ImportAction.ADDED))
        result.elapsed_time = 1.0
        
        summary = result.summary()
        
        assert "Added: 1" in summary
        assert "Skipped" not in summary
        assert "Warnings" not in summary
        assert "Failed" not in summary


class TestRisImportResult:
    """Test RisImportResult dataclass."""
    
    def test_ris_import_result_default(self):
        """Test RisImportResult default values."""
        from zotero_mcp.domain.entities.batch_result import RisImportResult
        
        result = RisImportResult()
        
        assert result.success is True
        assert result.total == 0
        assert result.added == 0
        assert result.skipped == 0
        assert result.failed == 0
        assert result.message == ""
        assert result.errors == []
    
    def test_ris_import_result_with_values(self):
        """Test RisImportResult with values."""
        from zotero_mcp.domain.entities.batch_result import RisImportResult
        
        result = RisImportResult(
            success=True,
            total=10,
            added=8,
            skipped=1,
            failed=1,
            message="Import completed",
            errors=["Line 50: Invalid format"],
        )
        
        assert result.total == 10
        assert result.added == 8
        assert len(result.errors) == 1
    
    def test_ris_import_result_to_dict(self):
        """Test RisImportResult to_dict output."""
        from zotero_mcp.domain.entities.batch_result import RisImportResult
        
        result = RisImportResult(
            success=False,
            total=5,
            added=3,
            skipped=1,
            failed=1,
            message="Partial success",
            errors=["Error 1", "Error 2"],
        )
        output = result.to_dict()
        
        assert output == {
            "success": False,
            "total": 5,
            "added": 3,
            "skipped": 1,
            "failed": 1,
            "message": "Partial success",
            "errors": ["Error 1", "Error 2"],
        }


class TestBatchImportEdgeCases:
    """Test edge cases for batch import entities."""
    
    def test_imported_item_empty_pmid(self):
        """Test ImportedItem with empty PMID."""
        from zotero_mcp.domain.entities.batch_result import ImportedItem, ImportAction
        
        item = ImportedItem(pmid="", title="No PMID", action=ImportAction.ADDED)
        assert item.pmid == ""
    
    def test_imported_item_long_title(self):
        """Test ImportedItem with very long title."""
        from zotero_mcp.domain.entities.batch_result import ImportedItem, ImportAction
        
        long_title = "A" * 1000
        item = ImportedItem(pmid="123", title=long_title, action=ImportAction.ADDED)
        assert len(item.title) == 1000
    
    def test_batch_import_result_no_items_summary(self):
        """Test summary with no items added."""
        from zotero_mcp.domain.entities.batch_result import BatchImportResult
        
        result = BatchImportResult()
        result.elapsed_time = 0.1
        
        summary = result.summary()
        assert "Total: 0" in summary
    
    def test_imported_item_unicode(self):
        """Test ImportedItem with unicode characters."""
        from zotero_mcp.domain.entities.batch_result import ImportedItem, ImportAction
        
        item = ImportedItem(
            pmid="12345",
            title="日本語論文タイトル",
            action=ImportAction.ADDED,
        )
        result = item.to_dict()
        assert "日本語" in result["title"]
