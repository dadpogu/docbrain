"""DB-004: identity, scope, legal time, and span contracts."""

from __future__ import annotations

from datetime import date

import pytest
from pydantic import ValidationError

from docbrain.models import (
    DocumentKey,
    LegalTime,
    OfficialVersion,
    ResourceScope,
    SiteScope,
    SourceAlias,
    SourceSpan,
    build_scoped_id,
    is_authorized,
    parse_clause_query,
    point_uuid,
    provision_display_id,
)
from tests.conftest import context


def test_document_identity_ignores_paths_and_is_tenant_scoped() -> None:
    a = DocumentKey(tenant_id="t1", authority="au", identifier="C2020A00119")
    b = DocumentKey(tenant_id="t2", authority="au", identifier="C2020A00119")
    assert a.doc_id == "t1:au:C2020A00119"
    assert a.display_id == b.display_id == "au:C2020A00119"
    assert provision_display_id(a, "C2026C00317", "s153(2)(b)") == "au:C2020A00119/C2026C00317/s153(2)(b)"
    v1 = OfficialVersion(doc_id=a.doc_id, official_id="C2026C00317").version_id
    v2 = OfficialVersion(doc_id=b.doc_id, official_id="C2026C00317").version_id
    ids = {
        point_uuid(build_scoped_id(v1, "bld1", "s153")),
        point_uuid(build_scoped_id(v2, "bld1", "s153")),
        point_uuid(build_scoped_id(v1, "bld1", "s65A")),
        point_uuid(build_scoped_id(v1, "bld1", "s65B")),
        point_uuid(build_scoped_id(v1, "bld2", "s153")),
    }
    assert len(ids) == 5
    assert point_uuid(build_scoped_id(v1, "bld1", "s153")) == point_uuid(build_scoped_id(v1, "bld1", "s153"))


def test_document_key_rejects_path_like_segments() -> None:
    with pytest.raises(ValidationError):
        DocumentKey(tenant_id="t1", authority="au", identifier="../C2020A00119")


@pytest.mark.parametrize(
    ("query", "key"),
    [
        ("s 65B", "s65B"),
        ("section 65b", "s65B"),
        ("65B(5)", "s65B(5)"),
        ("s153(2)(b)", "s153(2)(b)"),
        ("s 1", "s1"),
        ("Section 20(1)(a)", "s20(1)(a)"),
        ("what is section 20", None),
    ],
)
def test_clause_queries_parse_to_exact_keys(query: str, key: str | None) -> None:
    assert parse_clause_query(query) == key


def test_site_scopes_require_explicit_sharing_and_deny_unresolved() -> None:
    with pytest.raises(ValidationError):
        SiteScope(kind="shared")  # type: ignore[arg-type]
    site_a = ResourceScope(tenant_id="t1", site=SiteScope.site("site-a"))
    shared_a = ResourceScope(tenant_id="t1", site=SiteScope.shared("site-a"))
    unresolved = ResourceScope(tenant_id="t1", site=SiteScope.unresolved())
    corpus = ResourceScope(tenant_id="t1")
    a, b = context(sites=("site-a",)), context(sites=("site-b",))
    assert is_authorized(a, site_a) and not is_authorized(b, site_a)
    assert is_authorized(a, shared_a) and not is_authorized(b, shared_a)
    assert not is_authorized(a, unresolved) and not is_authorized(b, unresolved)
    assert is_authorized(b, corpus)
    assert not is_authorized(context("t2", sites=("site-a",)), site_a)
    assert not is_authorized(context(partitions=("public",)), corpus)


def test_mutable_source_alias_is_not_a_version_identity() -> None:
    alias = SourceAlias.from_uri("https://www.legislation.gov.au/C2020A00119/latest/text")
    assert alias.mutable
    assert not SourceAlias.from_uri("https://www.legislation.gov.au/C2026C00317/asmade/text").mutable


def test_legal_time_keeps_unknown_boundaries_unknown() -> None:
    lt = LegalTime(original_enactment_date=date(2020, 12, 15), effective_from=date(2026, 7, 1))
    assert lt.covers(date(2026, 6, 30)) is False  # E16: this compilation did not apply yet
    assert lt.covers(date(2026, 8, 1)) is None  # end unknown: not asserted current
    assert any("individual provisions" in note for note in lt.as_of_limitations())
    assert LegalTime().covers(date(2026, 8, 1)) is None


def test_source_span_validates_against_its_artifact() -> None:
    with pytest.raises(ValidationError):
        SourceSpan(artifact_id="a", char_start=5, char_end=4, line_start=1, line_end=1)
    span = SourceSpan(artifact_id="a", char_start=2, char_end=9, line_start=1, line_end=1)
    assert span.excerpt("0123456789") == "2345678"
    with pytest.raises(ValueError):
        span.excerpt("short")
