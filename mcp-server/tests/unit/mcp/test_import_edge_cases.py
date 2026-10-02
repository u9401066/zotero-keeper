"""Edge cases for the import application logic: RIS parsing, creator coercion, partial input."""

from unittest.mock import AsyncMock, MagicMock

import pytest

from zotero_mcp.infrastructure.mcp.unified_import_tools import (
    _chunk_items,
    _coerce_creator,
    _parse_ris,
    _parse_ris_to_articles,
    _unified_article_to_zotero,
    register_unified_import_tools,
)


def _import_articles(client):
    tools = {}
    server = MagicMock()
    server.tool = lambda **_kw: lambda fn: tools.setdefault(fn.__name__, fn)
    register_unified_import_tools(server, client)
    return tools["import_articles"]


@pytest.mark.parametrize("text", ["", "   \n\n", "not ris at all", "TY  -\nER  -", "XX  - nothing recognised"])
def test_ris_without_usable_records_yields_nothing_and_never_raises(text):
    assert _parse_ris(text)[0] == []


def test_ris_tolerates_crlf_missing_er_and_records_without_terminators():
    ris = "TY  - JOUR\r\nTI  - First\r\nAU  - Smith, J\r\nTY  - BOOK\r\nT1  - Second\r\nPY  - 2020/05/01/\r\nSN  - 978-3-16-148410-0\r\n"

    first, second = _parse_ris_to_articles(ris)

    assert (first["title"], first["authors"], first["article_type"]) == ("First", ["Smith, J"], "journal-article")
    assert (second["title"], second["year"], second["isbn"]) == ("Second", "2020", "978-3-16-148410-0")


@pytest.mark.parametrize(
    ("lines", "pages"),
    [
        (["SP  - 10", "EP  - 20"], "10-20"),
        (["EP  - 20", "SP  - 10"], "10-20"),  # exporters differ in tag order
        (["SP  - e1234"], "e1234"),
        (["EP  - 99"], "99"),
    ],
)
def test_ris_page_range_is_order_independent(lines, pages):
    ris = "\n".join(["TY  - JOUR", "TI  - T", *lines, "ER  -"])
    assert _parse_ris_to_articles(ris)[0]["pages"] == pages


def test_ris_pages_do_not_leak_between_records():
    ris = "TY  - JOUR\nTI  - A\nSP  - 1\nEP  - 2\nER  -\nTY  - JOUR\nTI  - B\nER  -"
    first, second = _parse_ris_to_articles(ris)
    assert first["pages"] == "1-2" and "pages" not in second


def test_untitled_records_are_counted_not_silently_lost():
    ris = "TY  - JOUR\nTI  - Kept\nER  -\nTY  - JOUR\nAU  - Nobody\nER  -\nTY  - JOUR\nER  -"
    articles, untitled = _parse_ris(ris)
    assert [a["title"] for a in articles] == ["Kept"]
    assert untitled == 2  # a typed record without a title still counts as a lost record


def test_ris_pmid_comes_only_from_notes_that_declare_one():
    ris = "TY  - JOUR\nTI  - A\nN1  - PMID: 123; PMCID: PMC9\nER  -\nTY  - JOUR\nTI  - B\nN1  - Supported by grant 555\nER  -"
    first, second = _parse_ris_to_articles(ris)
    assert first["pmid"] == "123" and "pmid" not in second


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        ("Smith J", ("Smith", "J")),
        ("Smith, John", ("Smith", "John")),
        ("van der Berg, Anna", ("van der Berg", "Anna")),
        ("John Ronald Tolkien", ("Ronald Tolkien", "John")),  # documented heuristic: first token is the given name
        ("Prince", ("Prince", "")),
        ({"name": "Prince"}, ("Prince", "")),
        ({"family_name": "Doe", "given_name": "A"}, ("Doe", "A")),
        ({"last_name": "Doe"}, ("Doe", "")),
    ],
)
def test_creator_coercion_accepts_common_author_shapes(value, expected):
    creator = _coerce_creator(value)
    assert (creator["lastName"], creator["firstName"]) == expected and creator["creatorType"] == "author"


@pytest.mark.parametrize(
    "value", [None, 5, "", "   ", {}, {"family_name": "", "given_name": ""}, {"name": 5}, {"name": "  "}, [], ["Smith"]]
)
def test_creator_coercion_rejects_unusable_values(value):
    assert _coerce_creator(value) is None


def test_blank_and_malformed_authors_never_become_empty_zotero_creators():
    item = _unified_article_to_zotero({"title": "T", "authors": ["Smith J", "", None, 5, {}, {"name": "  "}, {"family_name": "Doe"}]})
    assert [(c["lastName"], c["firstName"]) for c in item["creators"]] == [("Smith", "J"), ("Doe", "")]


@pytest.mark.parametrize("authors", [None, []])
def test_missing_authors_produce_no_creators_field(authors):
    assert "creators" not in _unified_article_to_zotero({"title": "T", "authors": authors})


def test_untitled_article_gets_a_visible_placeholder_title():
    assert _unified_article_to_zotero({})["title"] == "Unknown Title"


def test_chunking_is_stable_for_empty_exact_and_remainder_sizes():
    assert _chunk_items([], 5) == []
    assert [len(c) for c in _chunk_items([{}] * 10, 5)] == [5, 5]
    assert [len(c) for c in _chunk_items([{}] * 11, 5)] == [5, 5, 1]


@pytest.mark.asyncio
async def test_ris_import_reports_untitled_records_as_a_warning():
    client = AsyncMock()
    client.save_items.return_value = {"success": True}
    ris = "TY  - JOUR\nTI  - Kept\nER  -\nTY  - JOUR\nAU  - Nobody\nER  -\n"

    result = await _import_articles(client)(ris_text=ris, allow_library_root=True, skip_duplicates=False)

    assert result["success"] is True and result["imported"] == 1
    assert result["warnings"] == ["1 RIS record(s) had no title and were not imported"]
    assert "no title" in result["message"]


@pytest.mark.asyncio
@pytest.mark.parametrize("ris", ["TY  - JOUR\nAU  - Nobody\nER  -", "garbage"])
async def test_ris_import_with_no_importable_record_fails_without_touching_zotero(ris):
    client = AsyncMock()

    result = await _import_articles(client)(ris_text=ris, allow_library_root=True)

    assert result["success"] is False and result["error"] == "No valid articles found in RIS text"
    client.save_items.assert_not_awaited()
