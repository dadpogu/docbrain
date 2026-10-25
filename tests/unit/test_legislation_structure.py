"""DB-007: canonical structure of both supplied Recycling Act renderings."""

from __future__ import annotations

from typing import Any

import pytest

from docbrain.models import ParsedLegislation, ProvisionKind, Region
from docbrain.parsing import compare_section_inventory, lookup_key, parse_legislation_markdown
from tests.conftest import EARLIER_MD, read_text, to_crlf, to_lf


@pytest.mark.parametrize("line_endings", [to_lf, to_crlf], ids=["lf", "crlf"])
def test_earlier_markdown_matches_reviewed_section_inventory(line_endings: Any, expected: dict[str, Any]) -> None:
    text = line_endings(read_text(EARLIER_MD))
    parsed = parse_legislation_markdown(text, "art_md")
    comparison = compare_section_inventory(parsed, expected["section_numbers"])
    assert comparison.matches, comparison
    assert len(parsed.section_numbers()) == 188
    assert [(c.number, c.title) for c in parsed.nodes(ProvisionKind.CHAPTER)] == [
        (c["number"], c["title"]) for c in expected["chapters"]
    ]
    numbers = parsed.section_numbers()
    assert numbers[numbers.index("65") : numbers.index("66") + 1] == ["65", "65A", "65B", "66"]
    assert "122" not in numbers and "187" not in numbers
    # Spans index the exact artifact text regardless of line endings.
    node = parsed.provisions["s153(2)(a)"]
    assert text[node.spans[0].char_start : node.spans[0].char_end] == (
        "(a) 30 days after the day on which the decision first came to the notice of the applicant; or"
    )


def test_line_endings_do_not_change_structure() -> None:
    lf = parse_legislation_markdown(to_lf(read_text(EARLIER_MD)), "a")
    crlf = parse_legislation_markdown(to_crlf(read_text(EARLIER_MD)), "a")
    assert lf.order == crlf.order
    assert [lf.provisions[k].text for k in lf.order] == [crlf.provisions[k].text for k in crlf.order]
    assert [s.line_start for s in lf.provisions["s151"].spans] == [s.line_start for s in crlf.provisions["s151"].spans]


def test_liteparse_inventory_reports_omission_without_inventing_a_section(
    lite: ParsedLegislation, expected: dict[str, Any]
) -> None:
    comparison = compare_section_inventory(lite, expected["section_numbers"])
    assert comparison.missing == ["120"]
    assert comparison.duplicates == [] and comparison.unexpected == [] and comparison.out_of_order == []
    hint = [w for w in lite.warnings if w.code == "possible_unmarked_section_heading"]
    assert len(hint) == 1 and "section 120" in hint[0].message
    assert "s120" not in lite.provisions
    assert len(lite.nodes(ProvisionKind.CHAPTER)) == 5


@pytest.mark.parametrize("candidate", ["earlier", "lite"])
def test_ancestry_uses_available_levels_only(candidate: str, request: pytest.FixtureRequest) -> None:
    parsed: ParsedLegislation = request.getfixturevalue(candidate)
    s76 = [(n.kind.value, n.number) for n in parsed.ancestry("s76")]
    assert s76 == [("chapter", "3"), ("part", "4"), ("division", "1"), ("subdivision", "A")]
    assert [(n.kind.value, n.number) for n in parsed.ancestry("s171")] == [("chapter", "5")]


@pytest.mark.parametrize("candidate", ["earlier", "lite"])
def test_numbering_comes_from_legal_markers_not_line_starts(candidate: str, request: pytest.FixtureRequest) -> None:
    parsed: ParsedLegislation = request.getfixturevalue(candidate)
    p = parsed.provisions
    # LiteParse places 142(2) and 153(2) inline after the previous paragraph.
    assert p["s142(2)"].text.startswith("(2) Without limiting subsection (1)")
    assert p["s142(1)(j)"].text == "(j) any other person prescribed by the rules."
    assert p["s153(2)"].text == "(2) An application for internal review must be made within:"
    assert p["s153(1)(b)"].text.endswith("subsection 151(1)-the CEO.")
    # References such as "subsection (1)" never become clauses.
    for section in ("s20", "s22", "s142", "s153"):
        keys = [n.key for n in parsed.descendants(section)]
        assert not any("#dup" in k for k in keys), keys
    assert [n.number for n in parsed.descendants("s142") if n.kind is ProvisionKind.SUBSECTION] == list("12345")
    # Near-identical clauses in different sections stay distinct.
    assert p["s20(1)(a)"].text == "(a) the person exports waste material; and"
    assert p["s21(1)(a)"].text == "(a) waste material is entered for export by the person; and"
    assert p["s20(1)(a)"].list_connective == "and"


@pytest.mark.parametrize("candidate", ["earlier", "lite"])
def test_labels_and_penalties_inherit_their_provision(candidate: str, request: pytest.FixtureRequest) -> None:
    parsed: ParsedLegislation = request.getfixturevalue(candidate)
    p = parsed.provisions
    assert p["s20(2)"].label == "Fault-based offence"
    assert p["s20(2)/penalty1"].text == "Penalty: Imprisonment for 5 years or 300 penalty units, or both."
    assert p["s20(2)/penalty1"].parent_key == "s20(2)"
    assert p["s20(4)"].label == "Civil penalty provision"
    assert p["s20(4)/penalty1"].text == "Civil penalty: 600 penalty units."
    assert p["s22(4)/penalty1"].text == "Civil penalty: 360 penalty units."
    assert p["s22(5)"].label == "Exception"
    assert p["s142(4)"].label == "Strict liability offence"
    assert p["s142(4)/penalty1"].text == "Penalty: 60 penalty units."
    assert p["s142(5)/penalty1"].text == "Civil penalty: 250 penalty units."


def test_page_furniture_is_metadata_and_contents_do_not_duplicate_sections(
    lite: ParsedLegislation, lite_text: str
) -> None:
    assert [n.key for n in lite.nodes(ProvisionKind.SECTION)].count("s20") == 1
    body_start = min(b.span.char_start for b in lite.blocks if b.region is Region.BODY)
    assert all(s.char_start >= body_start for s in lite.provisions["s20"].spans)
    for key in lite.order:
        text = lite.provisions[key].text
        assert "Compilation date: 01/07/2026" not in text, key
    # Page-spanning section 22 carries both printed labels; physical pages are never inferred.
    labels = {s.printed_page_label for n in [lite.provisions["s22"], *lite.descendants("s22")] for s in n.spans}
    assert labels == {"21", "22"}
    assert all(s.physical_page is None for n in lite.provisions.values() for s in n.spans)
    assert {s.printed_page_label for s in lite.provisions["s153(1)"].spans} == {"167"}


def test_earlier_markdown_locators_and_unknown_page_labels(earlier: ParsedLegislation) -> None:
    assert earlier.provisions["s2"].spans[0].line_start == 73
    assert earlier.provisions["s151"].spans[0].line_start == 4565
    assert earlier.provisions["s153"].spans[0].line_start == 4738
    assert all(s.printed_page_label is None for n in earlier.provisions.values() for s in n.spans)


@pytest.mark.parametrize("candidate", ["earlier", "lite"])
def test_endnotes_are_history_not_provisions(candidate: str, request: pytest.FixtureRequest) -> None:
    parsed: ParsedLegislation = request.getfixturevalue(candidate)
    endnotes_start = min(b.span.char_start for b in parsed.blocks if b.region is Region.ENDNOTES)
    assert all(s.char_start < endnotes_start for n in parsed.provisions.values() for s in n.spans)
    repeals = {r.provision: r.how for r in parsed.repeals}
    assert repeals == {"s122": "rep No 68, 2025", "s187": "rep No 68, 2025"}


def test_missing_image_is_warned_not_fetched(lite: ParsedLegislation) -> None:
    images = [w for w in lite.warnings if w.code == "image_unavailable"]
    assert len(images) == 1 and "img_p1_1.png" in images[0].message
    supplied = parse_legislation_markdown(
        "![](img_p1_1.png)\n\n# Some Act 2020\n", "a", available_assets={"img_p1_1.png"}
    )
    assert not [w for w in supplied.warnings if w.code == "image_unavailable"]


def test_non_breaking_hyphens_do_not_break_lookup(earlier: ParsedLegislation, lite: ParsedLegislation) -> None:
    raw_title = read_text(EARLIER_MD).splitlines()[607]
    assert "\u2011" in raw_title  # the earlier Markdown uses U+2011 in "non‑compliance"
    assert lookup_key(earlier.provisions["s20"].title or "") == lookup_key(lite.provisions["s20"].title or "")
    assert earlier.find("Section 20") is earlier.provisions["s20"]
    assert earlier.find("s 65B").title == "Quarterly reports by CEO"  # type: ignore[union-attr]
    assert earlier.find("s 1").key == "s1"  # type: ignore[union-attr]


SYNTHETIC_ACT = """# Widget Control Act 2031

Contents

## Part 1—Preliminary

###### 1 Short title

This Act is the *Widget Control Act 2031*.

###### 2 Definitions

In this Act:

***widget*** means a small device.

## Part 2—Controls

### Division 1—Licences

###### 3 Licence required

(1) A person must not sell a widget without a licence.

Penalty: 10 penalty units.

(2) Subsection (1) does not apply to a person mentioned in paragraph (3)(a).

(3) The following persons are exempt:

(a) a person selling fewer than 5 widgets; and

(b) a person prescribed by the rules.

###### 3A Display of licence

A licence holder must display the licence.

###### 4 Repealed matter heading

Text.
"""


def test_a_different_synthetic_act_parses_with_its_own_counts() -> None:
    parsed = parse_legislation_markdown(SYNTHETIC_ACT, "synthetic")
    assert parsed.section_numbers() == ["1", "2", "3", "3A", "4"]
    assert [n.number for n in parsed.nodes(ProvisionKind.PART)] == ["1", "2"]
    assert [n.kind.value for n in parsed.ancestry("s3")] == ["part", "division"]
    assert [n.kind.value for n in parsed.ancestry("s1")] == ["part"]
    assert parsed.provisions["s3(1)/penalty1"].text == "Penalty: 10 penalty units."
    assert [c for c in parsed.provisions["s3(3)"].children] == ["s3(3)(a)", "s3(3)(b)"]
    assert parsed.provisions["s2/def:widget"].text == "widget means a small device."


@pytest.mark.parametrize("path", sorted(EARLIER_MD.parent.glob("*.md")), ids=lambda p: p.stem[:12])
def test_every_supplied_act_parses_into_sections(path) -> None:  # type: ignore[no-untyped-def]
    text = read_text(path)
    parsed = parse_legislation_markdown(text, "corpus")
    assert parsed.section_numbers(), path.name
    for node in parsed.nodes(ProvisionKind.SECTION):
        heading = node.spans[0].excerpt(text)
        assert heading.lstrip("#").strip().startswith(node.number or ""), heading
