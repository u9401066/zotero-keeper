"""
Unit tests for PubMed to Zotero mapper.

Tests all mapping functions and edge cases.
"""


class TestMapPubmedToZotero:
    """Test map_pubmed_to_zotero function."""

    def test_map_basic_article(self, mock_pubmed_article):
        """Test mapping basic article."""
        from zotero_mcp.infrastructure.mappers.pubmed_mapper import map_pubmed_to_zotero

        result = map_pubmed_to_zotero(mock_pubmed_article)

        assert result["itemType"] == "journalArticle"
        assert result["title"] == mock_pubmed_article["title"]
        assert result["abstractNote"] == mock_pubmed_article["abstract"]

    def test_map_creators(self, mock_pubmed_article):
        """Test mapping creators from authors_full."""
        from zotero_mcp.infrastructure.mappers.pubmed_mapper import map_pubmed_to_zotero

        result = map_pubmed_to_zotero(mock_pubmed_article)

        assert "creators" in result
        assert len(result["creators"]) == 3
        assert result["creators"][0]["firstName"] == "John"
        assert result["creators"][0]["lastName"] == "Smith"
        assert result["creators"][0]["creatorType"] == "author"

    def test_map_creators_fallback_to_authors(self):
        """Test mapping falls back to simple authors list."""
        from zotero_mcp.infrastructure.mappers.pubmed_mapper import map_pubmed_to_zotero

        article = {
            "title": "Test",
            "authors": ["John Smith", "Jane Doe"],
        }
        result = map_pubmed_to_zotero(article)

        assert len(result["creators"]) == 2
        assert result["creators"][0]["firstName"] == "John"
        assert result["creators"][0]["lastName"] == "Smith"

    def test_map_creators_single_name(self):
        """Test mapping author with single name."""
        from zotero_mcp.infrastructure.mappers.pubmed_mapper import map_pubmed_to_zotero

        article = {
            "title": "Test",
            "authors": ["Madonna"],
        }
        result = map_pubmed_to_zotero(article)

        assert result["creators"][0]["lastName"] == "Madonna"
        assert result["creators"][0]["firstName"] == ""

    def test_map_journal_info(self, mock_pubmed_article):
        """Test mapping journal information."""
        from zotero_mcp.infrastructure.mappers.pubmed_mapper import map_pubmed_to_zotero

        result = map_pubmed_to_zotero(mock_pubmed_article)

        assert result["publicationTitle"] == "Journal of Anesthesiology"
        assert result["journalAbbreviation"] == "J Anesth"

    def test_map_date_full(self, mock_pubmed_article):
        """Test mapping full date (year-month-day)."""
        from zotero_mcp.infrastructure.mappers.pubmed_mapper import map_pubmed_to_zotero

        result = map_pubmed_to_zotero(mock_pubmed_article)

        assert result["date"] == "2024-02-15"

    def test_map_date_year_month(self):
        """Test mapping date with year and month only."""
        from zotero_mcp.infrastructure.mappers.pubmed_mapper import map_pubmed_to_zotero

        article = {"title": "Test", "year": "2024", "month": "Mar"}
        result = map_pubmed_to_zotero(article)

        assert result["date"] == "2024-03"

    def test_map_date_year_only(self):
        """Test mapping date with year only."""
        from zotero_mcp.infrastructure.mappers.pubmed_mapper import map_pubmed_to_zotero

        article = {"title": "Test", "year": "2024"}
        result = map_pubmed_to_zotero(article)

        assert result["date"] == "2024"

    def test_map_date_numeric_month(self):
        """Test mapping date with numeric month."""
        from zotero_mcp.infrastructure.mappers.pubmed_mapper import map_pubmed_to_zotero

        article = {"title": "Test", "year": "2024", "month": "12", "day": "25"}
        result = map_pubmed_to_zotero(article)

        assert result["date"] == "2024-12-25"

    def test_map_volume_issue_pages(self, mock_pubmed_article):
        """Test mapping volume, issue, pages."""
        from zotero_mcp.infrastructure.mappers.pubmed_mapper import map_pubmed_to_zotero

        result = map_pubmed_to_zotero(mock_pubmed_article)

        assert result["volume"] == "140"
        assert result["issue"] == "2"
        assert result["pages"] == "e100-e115"

    def test_map_identifiers(self, mock_pubmed_article):
        """Test mapping DOI and ISSN."""
        from zotero_mcp.infrastructure.mappers.pubmed_mapper import map_pubmed_to_zotero

        result = map_pubmed_to_zotero(mock_pubmed_article)

        assert result["DOI"] == "10.1234/janesth.2024.001"
        assert result["ISSN"] == "1234-5678"

    def test_map_language(self, mock_pubmed_article):
        """Test mapping language."""
        from zotero_mcp.infrastructure.mappers.pubmed_mapper import map_pubmed_to_zotero

        result = map_pubmed_to_zotero(mock_pubmed_article)

        assert result["language"] == "eng"

    def test_map_extra_field(self, mock_pubmed_article):
        """Test mapping extra field with PMID, PMCID, etc."""
        from zotero_mcp.infrastructure.mappers.pubmed_mapper import map_pubmed_to_zotero

        result = map_pubmed_to_zotero(mock_pubmed_article)

        assert "PMID: 38353755" in result["extra"]
        assert "PMCID: PMC11111111" in result["extra"]
        assert "Publication Type: Systematic Review" in result["extra"]

    def test_map_extra_affiliations(self, mock_pubmed_article):
        """Test mapping affiliations to extra field."""
        from zotero_mcp.infrastructure.mappers.pubmed_mapper import map_pubmed_to_zotero

        result = map_pubmed_to_zotero(mock_pubmed_article)

        # Should include unique affiliations
        assert "Affiliations:" in result["extra"]
        assert "MIT" in result["extra"]
        assert "Stanford" in result["extra"]

    def test_map_tags_keywords(self, mock_pubmed_article):
        """Test mapping keywords to tags."""
        from zotero_mcp.infrastructure.mappers.pubmed_mapper import map_pubmed_to_zotero

        result = map_pubmed_to_zotero(mock_pubmed_article)

        tag_values = [t["tag"] for t in result["tags"]]
        assert "artificial intelligence" in tag_values
        assert "anesthesiology" in tag_values

    def test_map_tags_mesh_terms(self, mock_pubmed_article):
        """Test mapping MeSH terms to tags with prefix."""
        from zotero_mcp.infrastructure.mappers.pubmed_mapper import map_pubmed_to_zotero

        result = map_pubmed_to_zotero(mock_pubmed_article)

        tag_values = [t["tag"] for t in result["tags"]]
        assert "MeSH: Artificial Intelligence" in tag_values
        assert "MeSH: Anesthesiology" in tag_values

    def test_map_extra_tags(self, mock_pubmed_article):
        """Test adding extra tags."""
        from zotero_mcp.infrastructure.mappers.pubmed_mapper import map_pubmed_to_zotero

        result = map_pubmed_to_zotero(mock_pubmed_article, extra_tags=["custom-tag", "2024-import"])

        tag_values = [t["tag"] for t in result["tags"]]
        assert "custom-tag" in tag_values
        assert "2024-import" in tag_values

    def test_map_extra_tags_no_duplicates(self, mock_pubmed_article):
        """Test extra tags don't create duplicates."""
        from zotero_mcp.infrastructure.mappers.pubmed_mapper import map_pubmed_to_zotero

        # "artificial intelligence" already exists in keywords
        result = map_pubmed_to_zotero(mock_pubmed_article, extra_tags=["artificial intelligence", "new-tag"])

        tag_values = [t["tag"].lower() for t in result["tags"]]
        # Count occurrences of "artificial intelligence"
        count = sum(1 for t in tag_values if t == "artificial intelligence")
        assert count == 1  # Should not duplicate

    def test_map_collection_keys(self, mock_pubmed_article):
        """Test adding collection keys."""
        from zotero_mcp.infrastructure.mappers.pubmed_mapper import map_pubmed_to_zotero

        result = map_pubmed_to_zotero(
            mock_pubmed_article,
            collection_keys=["ABC123", "DEF456"],
        )

        assert "collections" in result
        assert result["collections"] == ["ABC123", "DEF456"]

    def test_map_collection_keys_single(self, mock_pubmed_article):
        """Test adding single collection key."""
        from zotero_mcp.infrastructure.mappers.pubmed_mapper import map_pubmed_to_zotero

        result = map_pubmed_to_zotero(
            mock_pubmed_article,
            collection_keys=["MHT7CZ8U"],
        )

        assert result["collections"] == ["MHT7CZ8U"]

    def test_map_no_collection_keys(self, mock_pubmed_article):
        """Test that collections field is absent when no collection_keys provided."""
        from zotero_mcp.infrastructure.mappers.pubmed_mapper import map_pubmed_to_zotero

        result = map_pubmed_to_zotero(mock_pubmed_article)

        assert "collections" not in result

    def test_map_empty_article(self):
        """Test mapping article with minimal data."""
        from zotero_mcp.infrastructure.mappers.pubmed_mapper import map_pubmed_to_zotero

        article = {"title": "Minimal Article"}
        result = map_pubmed_to_zotero(article)

        assert result["itemType"] == "journalArticle"
        assert result["title"] == "Minimal Article"
        assert result["abstractNote"] == ""

    def test_map_no_creators(self):
        """Test mapping article without any author information."""
        from zotero_mcp.infrastructure.mappers.pubmed_mapper import map_pubmed_to_zotero

        article = {"title": "No Authors"}
        result = map_pubmed_to_zotero(article)

        assert "creators" not in result


class TestMonthToNumber:
    """Test _month_to_number helper function."""

    def test_month_abbreviations(self):
        """Test month abbreviation conversion."""
        from zotero_mcp.infrastructure.mappers.pubmed_mapper import _month_to_number

        assert _month_to_number("jan") == "01"
        assert _month_to_number("Feb") == "02"
        assert _month_to_number("MAR") == "03"
        assert _month_to_number("apr") == "04"
        assert _month_to_number("may") == "05"
        assert _month_to_number("jun") == "06"
        assert _month_to_number("jul") == "07"
        assert _month_to_number("aug") == "08"
        assert _month_to_number("sep") == "09"
        assert _month_to_number("oct") == "10"
        assert _month_to_number("nov") == "11"
        assert _month_to_number("dec") == "12"

    def test_month_full_names(self):
        """Test full month name conversion."""
        from zotero_mcp.infrastructure.mappers.pubmed_mapper import _month_to_number

        assert _month_to_number("January") == "01"
        assert _month_to_number("february") == "02"
        assert _month_to_number("DECEMBER") == "12"

    def test_month_numeric(self):
        """Test numeric month string."""
        from zotero_mcp.infrastructure.mappers.pubmed_mapper import _month_to_number

        assert _month_to_number("1") == "01"
        assert _month_to_number("12") == "12"
        assert _month_to_number("03") == "03"

    def test_month_empty(self):
        """Test empty month."""
        from zotero_mcp.infrastructure.mappers.pubmed_mapper import _month_to_number

        assert _month_to_number("") is None
        assert _month_to_number(None) is None

    def test_month_invalid(self):
        """Test invalid month string."""
        from zotero_mcp.infrastructure.mappers.pubmed_mapper import _month_to_number

        assert _month_to_number("invalid") is None
        assert _month_to_number("xyz") is None

    def test_month_with_whitespace(self):
        """Test month with whitespace."""
        from zotero_mcp.infrastructure.mappers.pubmed_mapper import _month_to_number

        assert _month_to_number("  jan  ") == "01"
        assert _month_to_number(" december ") == "12"


class TestExtractUniqueAffiliations:
    """Test _extract_unique_affiliations helper function."""

    def test_extract_affiliations(self):
        """Test extracting unique affiliations."""
        from zotero_mcp.infrastructure.mappers.pubmed_mapper import _extract_unique_affiliations

        authors = [
            {"last_name": "Smith", "affiliations": ["MIT", "Harvard"]},
            {"last_name": "Doe", "affiliations": ["Stanford"]},
            {"last_name": "Johnson", "affiliations": ["MIT"]},  # Duplicate
        ]

        result = _extract_unique_affiliations(authors)

        assert len(result) == 3  # MIT, Harvard, Stanford (MIT not duplicated)
        assert "MIT" in result
        assert "Harvard" in result
        assert "Stanford" in result

    def test_extract_affiliations_empty(self):
        """Test with no affiliations."""
        from zotero_mcp.infrastructure.mappers.pubmed_mapper import _extract_unique_affiliations

        authors = [
            {"last_name": "Smith"},
            {"last_name": "Doe", "affiliations": []},
        ]

        result = _extract_unique_affiliations(authors)
        assert result == []

    def test_extract_affiliations_non_dict(self):
        """Test with non-dict authors."""
        from zotero_mcp.infrastructure.mappers.pubmed_mapper import _extract_unique_affiliations

        authors = ["John Smith", "Jane Doe"]

        result = _extract_unique_affiliations(authors)
        assert result == []


class TestMapPubmedListToZotero:
    """Test map_pubmed_list_to_zotero function."""

    def test_map_list(self, mock_pubmed_articles):
        """Test mapping list of articles."""
        from zotero_mcp.infrastructure.mappers.pubmed_mapper import map_pubmed_list_to_zotero

        result = map_pubmed_list_to_zotero(mock_pubmed_articles)

        assert len(result) == 3
        assert all(item["itemType"] == "journalArticle" for item in result)

    def test_map_list_with_tags(self, mock_pubmed_articles):
        """Test mapping list with extra tags."""
        from zotero_mcp.infrastructure.mappers.pubmed_mapper import map_pubmed_list_to_zotero

        result = map_pubmed_list_to_zotero(mock_pubmed_articles, extra_tags=["batch-import"])

        for item in result:
            tag_values = [t["tag"] for t in item["tags"]]
            assert "batch-import" in tag_values

    def test_map_empty_list(self):
        """Test mapping empty list."""
        from zotero_mcp.infrastructure.mappers.pubmed_mapper import map_pubmed_list_to_zotero

        result = map_pubmed_list_to_zotero([])
        assert result == []


class TestExtractPmidFromZoteroItem:
    """Test extract_pmid_from_zotero_item function."""

    def test_extract_pmid_basic(self):
        """Test extracting PMID from extra field."""
        from zotero_mcp.infrastructure.mappers.pubmed_mapper import extract_pmid_from_zotero_item

        item = {"data": {"extra": "PMID: 12345678"}}

        assert extract_pmid_from_zotero_item(item) == "12345678"

    def test_extract_pmid_with_other_content(self):
        """Test extracting PMID when extra has other content."""
        from zotero_mcp.infrastructure.mappers.pubmed_mapper import extract_pmid_from_zotero_item

        item = {"data": {"extra": "PMID: 12345678\nPMCID: PMC9876543\nOther info"}}

        assert extract_pmid_from_zotero_item(item) == "12345678"

    def test_extract_pmid_lowercase(self):
        """Test extracting PMID with lowercase pmid."""
        from zotero_mcp.infrastructure.mappers.pubmed_mapper import extract_pmid_from_zotero_item

        item = {"data": {"extra": "pmid: 12345678"}}

        assert extract_pmid_from_zotero_item(item) == "12345678"

    def test_extract_pmid_no_extra(self):
        """Test when extra field is missing."""
        from zotero_mcp.infrastructure.mappers.pubmed_mapper import extract_pmid_from_zotero_item

        item = {"data": {}}

        assert extract_pmid_from_zotero_item(item) is None

    def test_extract_pmid_no_pmid(self):
        """Test when extra doesn't contain PMID."""
        from zotero_mcp.infrastructure.mappers.pubmed_mapper import extract_pmid_from_zotero_item

        item = {"data": {"extra": "Some other content"}}

        assert extract_pmid_from_zotero_item(item) is None

    def test_extract_pmid_flat_dict(self):
        """Test with flat dict (no 'data' wrapper)."""
        from zotero_mcp.infrastructure.mappers.pubmed_mapper import extract_pmid_from_zotero_item

        item = {"extra": "PMID: 12345678"}

        assert extract_pmid_from_zotero_item(item) == "12345678"


class TestExtractDoiFromZoteroItem:
    """Test extract_doi_from_zotero_item function."""

    def test_extract_doi_uppercase(self):
        """Test extracting DOI field."""
        from zotero_mcp.infrastructure.mappers.pubmed_mapper import extract_doi_from_zotero_item

        item = {"data": {"DOI": "10.1234/test"}}

        assert extract_doi_from_zotero_item(item) == "10.1234/test"

    def test_extract_doi_lowercase(self):
        """Test extracting doi field (lowercase)."""
        from zotero_mcp.infrastructure.mappers.pubmed_mapper import extract_doi_from_zotero_item

        item = {"data": {"doi": "10.1234/test"}}

        assert extract_doi_from_zotero_item(item) == "10.1234/test"

    def test_extract_doi_missing(self):
        """Test when DOI is missing."""
        from zotero_mcp.infrastructure.mappers.pubmed_mapper import extract_doi_from_zotero_item

        item = {"data": {}}

        assert extract_doi_from_zotero_item(item) is None


class TestAliasCompatibility:
    """Test alias for backward compatibility."""

    def test_pubmed_to_zotero_item_alias(self, mock_pubmed_article):
        """Test pubmed_to_zotero_item is an alias for map_pubmed_to_zotero."""
        from zotero_mcp.infrastructure.mappers.pubmed_mapper import (
            map_pubmed_to_zotero,
            pubmed_to_zotero_item,
        )

        result1 = map_pubmed_to_zotero(mock_pubmed_article)
        result2 = pubmed_to_zotero_item(mock_pubmed_article)

        assert result1 == result2
