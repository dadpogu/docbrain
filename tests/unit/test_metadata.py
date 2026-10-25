"""DB-005: metadata import and reconciliation keep claims, verified facts, and dates distinct."""

from __future__ import annotations

import json
from datetime import date

import pytest
from pydantic import ValidationError

from docbrain.models import ParsedLegislation
from docbrain.parsing import (
    LegislationMetadata,
    MetadataBasis,
    MetadataClaim,
    claims_from_cover,
    claims_from_metadata,
    front_matter_metadata,
    legal_time_from,
    load_sidecar_json,
    parse_legislation_markdown,
    reconcile_claims,
)
from tests.conftest import SIDECAR_JSON


def all_claims(earlier: ParsedLegislation, lite: ParsedLegislation, sidecar: bytes) -> list[MetadataClaim]:
    front = front_matter_metadata(earlier)
    assert front is not None
    return [
        *claims_from_metadata(load_sidecar_json(sidecar), MetadataBasis.PROVIDER_SIDECAR, "art_json"),
        *claims_from_metadata(front, MetadataBasis.PROVIDER_FRONT_MATTER, earlier.artifact_id),
        *claims_from_cover(earlier),
        *claims_from_cover(lite),
        MetadataClaim(
            field="register_id", value="C2026C00317", basis=MetadataBasis.IMPORT_MANIFEST, artifact_id=lite.artifact_id
        ),
        MetadataClaim(
            field="registration_date",
            value=date(2026, 7, 21),
            basis=MetadataBasis.REVIEWED_SOURCE_FACT,
            artifact_id="art_pdf",
        ),
    ]


def test_sidecar_front_matter_and_cover_facts_reconcile(earlier: ParsedLegislation, lite: ParsedLegislation) -> None:
    sidecar = SIDECAR_JSON.read_bytes()  # path contains spaces
    assert load_sidecar_json(sidecar) == front_matter_metadata(earlier)
    rec = reconcile_claims(all_claims(earlier, lite, sidecar))
    assert rec.conflicts == []
    assert rec.fields["title"].status == "agreed" and rec.fields["compilation_number"].value == 3
    assert rec.fields["act_number"].value == "119/2020"
    assert {c.basis for c in rec.fields["compilation_date"].claims} == {
        MetadataBasis.COVER_TEXT,
        MetadataBasis.PAGE_FOOTER,
    }
    # Provider metadata stays separate from facts read from the legal text itself.
    assert all(
        c.basis in (MetadataBasis.PROVIDER_SIDECAR, MetadataBasis.PROVIDER_FRONT_MATTER, MetadataBasis.IMPORT_MANIFEST)
        for c in rec.provider_claims()
    )
    lt = legal_time_from(rec)
    assert (
        lt.original_enactment_date,
        lt.version_start,
        lt.compilation_date,
        lt.registration_date,
        lt.retrieved_on,
    ) == (date(2020, 12, 15), date(2026, 7, 1), date(2026, 7, 1), date(2026, 7, 21), date(2026, 10, 11))
    assert lt.effective_to is None and not lt.provision_commencement_known


@pytest.mark.parametrize(
    ("field", "mutate"),
    [
        ("register_id", lambda s, lt: (s.replace(b'"C2026C00317"', b'"C2026C00999"'), lt)),
        (
            "compilation_date",
            lambda s, lt: (s, lt.replace("Compilation date: 1 July 2026", "Compilation date: 2 July 2026")),
        ),
        (
            "title",
            lambda s, lt: (s.replace(b'"Recycling and Waste Reduction Act 2020"', b'"Recycling Act 2020"', 1), lt),
        ),
    ],
)
def test_changed_identity_facts_produce_reviewable_conflicts(
    field: str, mutate: object, earlier: ParsedLegislation, lite_text: str
) -> None:
    sidecar, text = mutate(SIDECAR_JSON.read_bytes(), lite_text)  # type: ignore[operator]
    lite = parse_legislation_markdown(text, "art_lite_changed")
    rec = reconcile_claims(all_claims(earlier, lite, sidecar))
    assert [c.field for c in rec.conflicts] == [field]
    assert rec.value(field) is None  # no silent precedence


def test_metadata_scalars_are_validated() -> None:
    good = json.loads(SIDECAR_JSON.read_bytes())
    for bad in ({"compilation_number": "3"}, {"date": "15/12/2020"}, {"title": ["a", "b"]}, {"identifier": "../x"}):
        with pytest.raises(ValidationError):
            LegislationMetadata.model_validate({**good, **bad})
