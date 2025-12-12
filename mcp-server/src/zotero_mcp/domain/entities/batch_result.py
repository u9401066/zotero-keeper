"""
Batch Import Result Entities

Domain entities for batch import operations.
"""

from dataclasses import dataclass, field
from typing import Any, Optional
from enum import Enum


class ImportAction(Enum):
    """Action taken for an imported item."""
    ADDED = "added"
    SKIPPED = "skipped"
    WARNING = "warning"
    FAILED = "failed"


@dataclass
class ImportedItem:
    """Result for a single imported item."""
    pmid: str
    title: str
    action: ImportAction
    zotero_key: Optional[str] = None
    reason: Optional[str] = None
    warning: Optional[str] = None
    error: Optional[str] = None
    
    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        result = {
            "pmid": self.pmid,
            "title": self.title,
            "action": self.action.value,
        }
        if self.zotero_key:
            result["key"] = self.zotero_key
        if self.reason:
            result["reason"] = self.reason
        if self.warning:
            result["warning"] = self.warning
        if self.error:
            result["error"] = self.error
        return result


@dataclass
class BatchImportResult:
    """
    Result from a batch import operation.
    
    Provides detailed statistics and per-item results.
    """
    success: bool = True
    total: int = 0
    added: int = 0
    skipped: int = 0
    warnings: int = 0
    failed: int = 0
    
    added_items: list[ImportedItem] = field(default_factory=list)
    skipped_items: list[ImportedItem] = field(default_factory=list)
    warning_items: list[ImportedItem] = field(default_factory=list)
    failed_items: list[ImportedItem] = field(default_factory=list)
    
    collection_key: Optional[str] = None
    elapsed_time: float = 0.0
    
    def add_item(self, item: ImportedItem) -> None:
        """Add an item result and update counters."""
        self.total += 1
        
        if item.action == ImportAction.ADDED:
            self.added += 1
            self.added_items.append(item)
        elif item.action == ImportAction.SKIPPED:
            self.skipped += 1
            self.skipped_items.append(item)
        elif item.action == ImportAction.WARNING:
            self.warnings += 1
            self.warning_items.append(item)
        elif item.action == ImportAction.FAILED:
            self.failed += 1
            self.failed_items.append(item)
            self.success = False  # Mark overall as failed if any item fails
    
    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for MCP response."""
        return {
            "success": self.success,
            "total": self.total,
            "added": self.added,
            "skipped": self.skipped,
            "warnings": self.warnings,
            "failed": self.failed,
            "added_items": [item.to_dict() for item in self.added_items],
            "skipped_items": [item.to_dict() for item in self.skipped_items],
            "warning_items": [item.to_dict() for item in self.warning_items],
            "failed_items": [item.to_dict() for item in self.failed_items],
            "collection_key": self.collection_key,
            "elapsed_time": round(self.elapsed_time, 2),
        }
    
    def summary(self) -> str:
        """Generate a human-readable summary."""
        parts = [f"Total: {self.total}"]
        if self.added:
            parts.append(f"Added: {self.added}")
        if self.skipped:
            parts.append(f"Skipped: {self.skipped}")
        if self.warnings:
            parts.append(f"Warnings: {self.warnings}")
        if self.failed:
            parts.append(f"Failed: {self.failed}")
        parts.append(f"Time: {self.elapsed_time:.1f}s")
        return " | ".join(parts)


@dataclass
class RisImportResult:
    """Result from RIS format import."""
    success: bool = True
    total: int = 0
    added: int = 0
    skipped: int = 0
    failed: int = 0
    message: str = ""
    errors: list[str] = field(default_factory=list)
    
    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "success": self.success,
            "total": self.total,
            "added": self.added,
            "skipped": self.skipped,
            "failed": self.failed,
            "message": self.message,
            "errors": self.errors,
        }
