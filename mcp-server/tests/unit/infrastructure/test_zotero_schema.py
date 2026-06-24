"""
Unit tests for the Zotero item-type schema & type-aware mapping helpers.
"""

from zotero_mcp.infrastructure.mappers.zotero_schema import (
    CONTAINER_FIELD,
    ZOTERO_ITEM_FIELDS,
    ZOTERO_PRIMARY_CREATOR,
    detect_item_type,
    finalize_item_for_schema,
    is_known_item_type,
)


class TestDetectItemType:
    """Tests for detect_item_type."""

    def test_explicit_valid_item_type(self):
        assert detect_item_type({"itemType": "book"}) == "book"
        assert detect_item_type({"item_type": "conferencePaper"}) == "conferencePaper"

    def test_journal_article_aliases(self):
        assert detect_item_type({"article_type": "journal-article"}) == "journalArticle"
        assert detect_item_type({"article_type": "research-article"}) == "journalArticle"

    def test_pubmed_publication_types_are_journal_articles(self):
        # PubMed publication types are still journal articles in Zotero
        for pub_type in ("review", "meta-analysis", "clinical-trial", "case-report", "editorial"):
            assert detect_item_type({"article_type": pub_type}) == "journalArticle"

    def test_conference_aliases(self):
        assert detect_item_type({"article_type": "conference-paper"}) == "conferencePaper"
        assert detect_item_type({"article_type": "proceedings-article"}) == "conferencePaper"
        assert detect_item_type({"type": "inproceedings"}) == "conferencePaper"

    def test_book_and_chapter(self):
        assert detect_item_type({"article_type": "book"}) == "book"
        assert detect_item_type({"article_type": "book-chapter"}) == "bookSection"
        assert detect_item_type({"type": "incollection"}) == "bookSection"

    def test_thesis_report_webpage(self):
        assert detect_item_type({"article_type": "thesis"}) == "thesis"
        assert detect_item_type({"article_type": "dissertation"}) == "thesis"
        assert detect_item_type({"article_type": "report"}) == "report"
        assert detect_item_type({"article_type": "webpage"}) == "webpage"

    def test_software_and_dataset(self):
        assert detect_item_type({"article_type": "software"}) == "computerProgram"
        assert detect_item_type({"type": "computer-program"}) == "computerProgram"
        assert detect_item_type({"article_type": "dataset"}) == "dataset"

    def test_case_and_separator_insensitive(self):
        assert detect_item_type({"article_type": "Conference Paper"}) == "conferencePaper"
        assert detect_item_type({"article_type": "BOOK_CHAPTER"}) == "bookSection"

    def test_arxiv_identifier_detects_preprint(self):
        assert detect_item_type({"identifiers": {"arxiv_id": "2401.12345"}}) == "preprint"
        assert detect_item_type({"arxiv_id": "2401.12345"}) == "preprint"

    def test_repository_url_detects_software(self):
        assert detect_item_type({"url": "https://github.com/owner/repo"}) == "computerProgram"
        assert detect_item_type({"url": "https://gitlab.com/group/project"}) == "computerProgram"

    def test_conference_fields_detect_conference(self):
        assert detect_item_type({"conference_name": "NeurIPS 2024"}) == "conferencePaper"
        assert detect_item_type({"proceedings_title": "Proc. of X"}) == "conferencePaper"

    def test_isbn_without_journal_is_book(self):
        assert detect_item_type({"isbn": "978-0-13-468599-1"}) == "book"

    def test_isbn_with_book_title_is_chapter(self):
        result = detect_item_type({"isbn": "978-0-13-468599-1", "book_title": "Handbook of X"})
        assert result == "bookSection"

    def test_website_fields_detect_webpage(self):
        assert detect_item_type({"website_title": "Some Blog"}) == "webpage"

    def test_default_journal_when_journal_present(self):
        assert detect_item_type({"journal": "Nature"}) == "journalArticle"

    def test_default_journal_when_pmid_present(self):
        assert detect_item_type({"identifiers": {"pmid": "12345678"}}) == "journalArticle"

    def test_bare_url_is_webpage(self):
        assert detect_item_type({"url": "https://example.com/page"}) == "webpage"

    def test_empty_article_is_document(self):
        assert detect_item_type({}) == "document"


class TestFinalizeItemForSchema:
    """Tests for finalize_item_for_schema."""

    def test_keeps_valid_fields(self):
        item = {
            "itemType": "journalArticle",
            "title": "T",
            "publicationTitle": "Nature",
            "volume": "10",
        }
        result = finalize_item_for_schema(item)
        assert result["publicationTitle"] == "Nature"
        assert result["volume"] == "10"

    def test_moves_invalid_fields_to_extra(self):
        # webpage has no volume/issue/ISSN fields
        item = {
            "itemType": "webpage",
            "title": "Page",
            "volume": "10",
            "ISSN": "1234-5678",
        }
        result = finalize_item_for_schema(item)
        assert "volume" not in result
        assert "ISSN" not in result
        assert "Volume: 10" in result["extra"]
        assert "ISSN: 1234-5678" in result["extra"]

    def test_preserves_existing_extra(self):
        item = {
            "itemType": "webpage",
            "title": "Page",
            "extra": "PMID: 999",
            "volume": "10",
        }
        result = finalize_item_for_schema(item)
        assert "PMID: 999" in result["extra"]
        assert "Volume: 10" in result["extra"]

    def test_drops_empty_values(self):
        item = {
            "itemType": "journalArticle",
            "title": "T",
            "volume": "",
            "issue": None,
            "pages": [],
        }
        result = finalize_item_for_schema(item)
        assert "volume" not in result
        assert "issue" not in result
        assert "pages" not in result

    def test_preserves_structural_keys(self):
        item = {
            "itemType": "journalArticle",
            "title": "T",
            "creators": [{"lastName": "Smith", "firstName": "J", "creatorType": "author"}],
            "tags": [{"tag": "x"}],
            "collections": ["ABC123"],
        }
        result = finalize_item_for_schema(item)
        assert result["creators"] == item["creators"]
        assert result["tags"] == item["tags"]
        assert result["collections"] == ["ABC123"]

    def test_unknown_item_type_returned_as_is(self):
        item = {"itemType": "madeUpType", "title": "T", "foo": "bar"}
        result = finalize_item_for_schema(item)
        assert result == item


class TestSchemaRegistry:
    """Sanity checks on the schema registry."""

    def test_known_types(self):
        assert is_known_item_type("journalArticle")
        assert is_known_item_type("computerProgram")
        assert not is_known_item_type("madeUpType")

    def test_all_types_have_title_and_extra(self):
        for fields in ZOTERO_ITEM_FIELDS.values():
            assert "title" in fields
            assert "extra" in fields

    def test_container_fields_are_valid(self):
        for item_type, field in CONTAINER_FIELD.items():
            assert field in ZOTERO_ITEM_FIELDS[item_type]

    def test_primary_creator_software(self):
        assert ZOTERO_PRIMARY_CREATOR["computerProgram"] == "programmer"
