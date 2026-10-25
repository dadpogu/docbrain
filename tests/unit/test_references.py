"""DB-010: clause references and scoped definitions."""

from __future__ import annotations

import pytest

from docbrain.models import ParsedLegislation, ReferenceKind, ReferenceStatus
from docbrain.parsing import parse_legislation_markdown
from docbrain.references import resolve_term


def refs(parsed: ParsedLegislation, source_key: str) -> list:
    return [r for r in parsed.references if r.source_key == source_key]


@pytest.mark.parametrize("candidate", ["earlier", "lite"])
def test_section_25_note_links_to_application_provisions(candidate: str, request: pytest.FixtureRequest) -> None:
    parsed: ParsedLegislation = request.getfixturevalue(candidate)
    (ref,) = refs(parsed, "s25/note1")
    assert ref.targets == ["s172", "s173", "s174"] and ref.status is ReferenceStatus.RESOLVED


def test_section_153_table_item_ranges(earlier: ParsedLegislation, lite: ParsedLegislation) -> None:
    (minister,) = refs(earlier, "s153(1)(a)")
    (ceo,) = refs(earlier, "s153(1)(b)")
    assert minister.kind is ReferenceKind.TABLE_ITEMS and minister.table_items == ["1", "11", "12", "13"]
    assert ceo.table_items == [str(n) for n in [*range(2, 11), *range(14, 29)]]
    assert minister.status is ceo.status is ReferenceStatus.RESOLVED
    # The LiteParse table cannot support these items: the reference says so instead of guessing.
    (lite_ref,) = refs(lite, "s153(1)(a)")
    assert lite_ref.status is ReferenceStatus.AMBIGUOUS


@pytest.mark.parametrize("candidate", ["earlier", "lite"])
def test_local_and_external_references(candidate: str, request: pytest.FixtureRequest) -> None:
    parsed: ParsedLegislation = request.getfixturevalue(candidate)
    by_kind = {r.kind: r for r in refs(parsed, "s20(3)")}
    assert by_kind[ReferenceKind.PARAGRAPH].targets == ["s20(1)(b)", "s20(1)(c)"]
    assert by_kind[ReferenceKind.SUBSECTION].targets == ["s20(2)"]
    (tribunal,) = refs(parsed, "s154(3)")
    assert tribunal.kind is ReferenceKind.EXTERNAL_ACT
    assert tribunal.target_act == "Administrative Review Tribunal Act 2024"
    assert tribunal.status is ReferenceStatus.EXTERNAL_UNAVAILABLE


def test_scoped_definitions(earlier: ParsedLegislation) -> None:
    local = resolve_term(earlier, "relevant person", "s172(1)(a)")
    assert local.status == "resolved" and local.definition is not None
    assert local.definition.defined_in == "s172(5)/def:relevant person"
    # The Dictionary's audit-only meaning never applies elsewhere.
    elsewhere = resolve_term(earlier, "relevant person", "s20(1)")
    assert elsewhere.status == "qualified_only" and elsewhere.definition is None
    ceo = resolve_term(earlier, "CEO", "s153(1)")
    assert ceo.status == "external_unavailable"
    assert (
        ceo.definition is not None
        and ceo.definition.external_act == "National Environmental Protection Agency Act 2025"
    )
    assert ceo.notes == ["Note: This is a reference to the CEO of NEPA."]
    assert resolve_term(earlier, "reviewer", "s153(3)").definition.scope_key == "s153"  # type: ignore[union-attr]


REPEALED = """# Synthetic Repeal Act 2031

## Part 1—Main

###### 1 Duty

(1) A person must comply with sections 2 and 3.

(2) See also subsection (7).

###### 3 Other duty

A person must keep records.

## Endnotes

### Endnote 4—Amendment history

| Provision affected | How affected |
|---|---|
| s 2 | rep No 9, 2030 |
"""


def test_repealed_and_inconsistent_references_are_reported_not_corrected() -> None:
    parsed = parse_legislation_markdown(REPEALED, "synthetic")
    (sections,) = [r for r in refs(parsed, "s1(1)") if r.kind is ReferenceKind.SECTION]
    assert sections.targets == ["s2", "s3"]
    assert sections.status is ReferenceStatus.EXPLICITLY_REPEALED and "s2 rep No 9, 2030" in (sections.note or "")
    (missing,) = refs(parsed, "s1(2)")
    assert missing.targets == ["s1(7)"] and missing.status is ReferenceStatus.UNRESOLVED
    assert any(w.code == "unresolved_reference" and w.clause_key == "s1(2)" for w in parsed.warnings)
