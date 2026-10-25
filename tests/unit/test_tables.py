"""DB-009: table semantics, per-cell provenance, and unresolved fragments."""

from __future__ import annotations

from typing import Any

from docbrain.models import ContentClass, ParsedLegislation, ProvisionKind, Region, TableStatus
from docbrain.parsing import normalize_text, parse_legislation_markdown
from tests.conftest import EARLIER_MD, read_text


def test_section_151_keeps_all_reviewed_item_person_decision_tuples(
    earlier: ParsedLegislation, expected: dict[str, Any]
) -> None:
    (table,) = earlier.tables_for("s151")
    assert table.status is TableStatus.RESOLVED and table.evidence_eligible
    assert table.owner_key == "s151(1)"
    reviewed = expected["section_151_table"]["items"]
    assert [r.key for r in table.rows] == [t["item"] for t in reviewed]
    for tup in reviewed:
        assert table.value(tup["item"], "Column 1") == tup["person_affected"]
        assert table.value(tup["item"], "Reviewable decision") == tup["reviewable_decision"]
    item13 = table.value("13", "Person affected") or ""
    assert item13.splitlines()[0] == "The following persons:" and len(item13.splitlines()) == 3
    # Per-cell provenance points at the exact source cell.
    text = read_text(EARLIER_MD)
    cell = table.row("1").cell(table.column_index("Column 1"))
    assert cell is not None and cell.span is not None
    assert text[cell.span.char_start : cell.span.char_end] == "A person who applies for an exemption under section 25"


def test_section_106_keeps_eight_items_with_conditional_grounds(
    earlier: ParsedLegislation, expected: dict[str, Any]
) -> None:
    (table,) = earlier.tables_for("s106")
    assert len(table.rows) == expected["section_106_table"]["item_count"] == 8
    grounds = table.value("1", "Grounds for giving direction") or ""
    assert grounds.startswith("Any of the following:")
    assert [line[:3] for line in grounds.splitlines()[1:]] == ["(a)", "(b)", "(c)"]
    assert table.value("8", "Grounds") == "A ground prescribed by the rules"


def test_section_2_marks_column_3_as_non_operative(earlier: ParsedLegislation) -> None:
    (table,) = earlier.tables_for("s2")
    by_number = {c.column_number: c.classification for c in table.columns}
    assert by_number == {1: "operative", 2: "operative", 3: "non_operative_information"}
    assert table.value("1", "Column 2") == "The day after this Act receives the Royal Assent."
    assert table.value("1", "Column 3") == "16 December 2020"
    assert "is not part of this Act" in earlier.provisions["s2(2)"].text


def test_liteparse_section_151_fragments_are_visible_but_never_evidence(lite: ParsedLegislation) -> None:
    tables = lite.tables_for("s151")
    assert tables and all(t.status is TableStatus.UNRESOLVED and not t.evidence_eligible for t in tables)
    assert max(len(t.rows) for t in tables) < 28
    fragments = [f for t in tables for f in t.fragments]
    texts = [f.text for f in fragments]
    assert "2 A person who applies for an export" in texts
    assert any(t.startswith("Column 2 Reviewable decision") for t in texts)
    assert {f.span.printed_page_label for f in fragments} == {"163", "164", "165", "166"}
    assert any("absent from the table" in issue for t in tables for issue in t.issues)
    # Row 1 is structurally present, but its decision column is detached: no pairing is produced.
    first = tables[0]
    assert [c.header for c in first.columns] == ["Item", "Column 1 Person affected"]
    assert all("26(1)(b)" not in cell.text for row in first.rows for cell in row.cells)


def test_liteparse_section_2_interleaving_is_flagged_not_repaired(lite: ParsedLegislation) -> None:
    (table,) = lite.tables_for("s2")
    assert table.status is TableStatus.UNRESOLVED and table.title == "Commencement information"
    sub2 = lite.provisions["s2(2)"].text
    assert sub2 == "(2) Any information in column 3 of the table is not part of this Act."
    assert "Royal Assent" not in lite.full_text("s2") and "16 December 2020" not in lite.full_text("s2")
    assert any(f.text == "16 December 2020" for f in table.fragments)


MISORDERED = """# Synthetic Review Act 2031

## Part 1—Review

###### 5 Persons affected

(1) Column 1 of the table sets out each person affected. Column 2 of the table sets out the decision.

**Persons affected by decisions**

| Item | Column 1 Person affected |
|---|---|
| 1 | An applicant for a permit |

---

2 The holder of a permit

---

3 A former holder of a permit

###### Column 2 Decision

A decision to revoke the permit A decision to refuse the permit A decision to vary the permit

(2) The rules may prescribe other decisions.
"""


def test_detached_columns_are_not_zipped_into_rows() -> None:
    parsed = parse_legislation_markdown(MISORDERED, "synthetic")
    (table,) = parsed.tables_for("s5")
    # Naive positional pairing would give item 1 -> "revoke" (wrong: the source order is unknown).
    assert table.status is TableStatus.UNRESOLVED and not table.evidence_eligible
    assert [r.key for r in table.rows] == ["1"]
    assert all("decision" not in c.text.lower() for r in table.rows for c in r.cells)
    assert [f.text for f in table.fragments][:2] == ["2 The holder of a permit", "3 A former holder of a permit"]
    assert parsed.provisions["s5(2)"].text == "(2) The rules may prescribe other decisions."


SWAPPED = """# Synthetic Order Act 2031

## Part 1—Review

###### 7 Decisions

(1) The table sets out decisions.

<table>
<tr><td>Item</td><td>Column 2<br>Decision</td><td>Column 1<br>Person</td></tr>
<tr><td>1</td><td>A decision to refuse a permit</td><td>An applicant for a permit</td></tr>
<tr><td>2</td><td>A decision to revoke a permit</td><td>The holder of a permit</td></tr>
</table>
"""


def test_cells_are_read_by_header_not_position() -> None:
    (table,) = parse_legislation_markdown(SWAPPED, "synthetic").tables_for("s7")
    assert table.status is TableStatus.RESOLVED
    assert table.value("2", "Column 1") == "The holder of a permit"
    assert table.value("2", "Decision") == "A decision to revoke a permit"


def test_endnote_tables_are_compilation_information(earlier: ParsedLegislation) -> None:
    endnote_tables = [t for t in earlier.tables if t.region is Region.ENDNOTES]
    assert {t.content_class for t in endnote_tables} == {
        ContentClass.COMPILATION_INFORMATION,
        ContentClass.AMENDMENT_HISTORY,
    }
    assert not any(t.evidence_eligible for t in endnote_tables)
    abbreviations = endnote_tables[0]
    assert any(normalize_text(c.text) == "effect" for r in abbreviations.rows for c in r.cells)
    # Wrapped abbreviation rows never become provisions or obligations.
    assert not any("effect" == n.text for n in earlier.provisions.values())
    assert earlier.provisions["s5"].content_class is ContentClass.SIMPLIFIED_OUTLINE
    assert all(n.kind is not ProvisionKind.SECTION or n.key != "s122" for n in earlier.provisions.values())
