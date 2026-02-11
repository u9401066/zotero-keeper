"""
Batch Import Result Entities

Domain entities for batch import operations.
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any


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
    zotero_key: str | None = None
    reason: str | None = None
    warning: str | None = None
    error: str | None = None

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

    # Enhanced tracking
    collection_key: str | None = None
    collection_name: str | None = None
    target_library: str = "My Library"
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())
    elapsed_time: float = 0.0

    # Data source tracking
    data_source: str = "PubMed API"
    pmids_requested: list[str] = field(default_factory=list)

    def add_item(self, item: ImportedItem) -> None:
        """Add an item result and update counters."""
        self.total += 1

        # Python 3.10+ match-case for cleaner enum handling
        match item.action:
            case ImportAction.ADDED:
                self.added += 1
                self.added_items.append(item)
            case ImportAction.SKIPPED:
                self.skipped += 1
                self.skipped_items.append(item)
            case ImportAction.WARNING:
                self.warnings += 1
                self.warning_items.append(item)
            case ImportAction.FAILED:
                self.failed += 1
                self.failed_items.append(item)
                self.success = False  # Mark overall as failed if any item fails

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for MCP response."""
        result = {
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
            "elapsed_time": round(self.elapsed_time, 2),
            # Enhanced report fields
            "timestamp": self.timestamp,
            "data_source": self.data_source,
            "target": {
                "library": self.target_library,
                "collection_key": self.collection_key,
                "collection_name": self.collection_name,
            },
            "report": self._generate_report(),
        }
        return result

    def _generate_report(self) -> str:
        """Generate a detailed human-readable report for agent debugging."""
        lines = [
            "=" * 60,
            "📊 BATCH IMPORT REPORT",
            "=" * 60,
            f"⏰ Timestamp: {self.timestamp}",
            f"📡 Data Source: {self.data_source}",
            f"⏱️  Elapsed Time: {self.elapsed_time:.2f}s",
            "",
            "📍 TARGET:",
            f"   Library: {self.target_library}",
            f"   Collection: {self.collection_name or '(none)'} [{self.collection_key or 'root'}]",
            "",
            "📈 STATISTICS:",
            f"   Total Processed: {self.total}",
            f"   ✅ Added: {self.added}",
            f"   ⏭️  Skipped: {self.skipped}",
            f"   ⚠️  Warnings: {self.warnings}",
            f"   ❌ Failed: {self.failed}",
        ]

        if self.failed > 0:
            lines.append("")
            lines.append("❌ FAILED ITEMS:")
            for item in self.failed_items[:10]:  # Limit to 10
                lines.append(f"   - PMID {item.pmid}: {item.error or 'Unknown error'}")
            if len(self.failed_items) > 10:
                lines.append(f"   ... and {len(self.failed_items) - 10} more")

        if self.skipped > 0:
            lines.append("")
            lines.append("⏭️  SKIPPED ITEMS (first 5):")
            for item in self.skipped_items[:5]:
                lines.append(f"   - PMID {item.pmid}: {item.reason or 'Already exists'}")
            if len(self.skipped_items) > 5:
                lines.append(f"   ... and {len(self.skipped_items) - 5} more")

        if not self.collection_key:
            lines.append("")
            lines.append("⚠️  WARNING: No collection specified!")
            lines.append("   Items were added to 'My Library' root, not a collection.")
            lines.append("   Use collection_key parameter to specify target collection.")

        lines.append("")
        lines.append("=" * 60)

        return "\n".join(lines)

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
