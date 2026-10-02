"""Behavior tests for the batch-import aggregate (counters, failure propagation, bounded reports)."""

import pytest

from zotero_mcp.domain.entities.batch_result import BatchImportResult, ImportAction, ImportedItem, RisImportResult


def _item(action: ImportAction, pmid: str = "1", **extra) -> ImportedItem:
    return ImportedItem(pmid=pmid, title=f"Title {pmid}", action=action, **extra)


def test_counters_and_buckets_track_every_action_and_only_failure_clears_success():
    result = BatchImportResult()
    for action in (ImportAction.ADDED, ImportAction.SKIPPED, ImportAction.WARNING):
        result.add_item(_item(action))
    assert result.success is True
    assert (result.total, result.added, result.skipped, result.warnings, result.failed) == (3, 1, 1, 1, 0)

    result.add_item(_item(ImportAction.FAILED, error="boom"))
    assert result.success is False
    assert (len(result.added_items), len(result.skipped_items), len(result.warning_items), len(result.failed_items)) == (1, 1, 1, 1)


def test_to_dict_serializes_optional_item_fields_only_when_present_and_rounds_time():
    result = BatchImportResult(collection_key="ABCD2345", collection_name="AI", elapsed_time=1.23456)
    result.add_item(_item(ImportAction.ADDED, zotero_key="KEY12345"))
    result.add_item(_item(ImportAction.SKIPPED, pmid="2", reason="duplicate"))

    payload = result.to_dict()

    assert payload["added_items"][0] == {"pmid": "1", "title": "Title 1", "action": "added", "key": "KEY12345"}
    assert payload["skipped_items"][0]["reason"] == "duplicate"
    assert payload["elapsed_time"] == 1.23
    assert payload["target"] == {"library": "My Library", "collection_key": "ABCD2345", "collection_name": "AI"}


@pytest.mark.parametrize(("collection_key", "warns"), [(None, True), ("ABCD2345", False)])
def test_report_warns_about_library_root_only_when_no_collection(collection_key, warns):
    report = BatchImportResult(collection_key=collection_key).to_dict()["report"]
    assert ("No collection specified" in report) is warns


def test_report_truncates_long_failure_and_skip_lists_but_counts_stay_exact():
    result = BatchImportResult(collection_key="ABCD2345")
    for index in range(13):
        result.add_item(_item(ImportAction.FAILED, pmid=f"f{index}", error="bad"))
    for index in range(8):
        result.add_item(_item(ImportAction.SKIPPED, pmid=f"s{index}"))

    report = result.to_dict()["report"]

    assert "PMID f9" in report and "PMID f10" not in report  # first 10 failures
    assert "PMID s4" in report and "PMID s5" not in report  # first 5 skips
    assert report.count("... and 3 more") == 2
    assert result.failed == 13 and result.skipped == 8


def test_summary_omits_zero_counts_and_unicode_titles_survive_serialization():
    result = BatchImportResult()
    result.add_item(ImportedItem(pmid="", title="腦科學 — ünïcode", action=ImportAction.ADDED))

    assert result.summary().startswith("Total: 1 | Added: 1 | Time:")
    assert "Skipped" not in result.summary() and "Failed" not in result.summary()
    assert result.to_dict()["added_items"][0]["title"] == "腦科學 — ünïcode"


def test_ris_result_round_trips_all_fields():
    result = RisImportResult(success=False, total=3, added=1, skipped=1, failed=1, message="partial", errors=["x"])
    assert result.to_dict() == {
        "success": False,
        "total": 3,
        "added": 1,
        "skipped": 1,
        "failed": 1,
        "message": "partial",
        "errors": ["x"],
    }
