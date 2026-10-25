"""DB-006: immutable artifacts, scoped reads, corrections with lineage, exact excerpts."""

from __future__ import annotations

from pathlib import Path

import pytest

from docbrain.adapters.artifacts import InvalidArtifactReference, LocalBlobStore
from docbrain.models import ArtifactRole, ResourceScope, SiteScope
from docbrain.parsing import parse_legislation_markdown
from docbrain.registry import NotFound, Registry, SchemaMissing
from tests.conftest import LITEPARSE_MD, context

DATA = b"(1) A person must keep records.\n(2) Penalty: 60 penalty units.\n"


def test_duplicate_bytes_share_storage_without_merging_permissions(registry: Registry, tmp_path: Path) -> None:
    t1 = registry.register_artifact(
        ResourceScope(tenant_id="t1"), DATA, media_type="text/markdown", role=ArtifactRole.IMPORTED_RENDERING
    )
    again = registry.register_artifact(
        ResourceScope(tenant_id="t1"),
        DATA,
        media_type="text/markdown",
        role=ArtifactRole.IMPORTED_RENDERING,
        original_name="moved/elsewhere.md",
    )
    t2 = registry.register_artifact(
        ResourceScope(tenant_id="t2"), DATA, media_type="text/markdown", role=ArtifactRole.IMPORTED_RENDERING
    )
    assert again.artifact_id == t1.artifact_id
    assert t2.artifact_id != t1.artifact_id and t2.sha256 == t1.sha256
    assert len(list((tmp_path / "blobs").rglob("*"))) == 3  # sha256/, one shard dir, one blob
    assert registry.read_artifact(context("t1"), t1.artifact_id) == DATA
    with pytest.raises(NotFound):
        registry.read_artifact(context("t2"), t1.artifact_id)
    site_scoped = registry.register_artifact(
        ResourceScope(tenant_id="t1", site=SiteScope.site("site-a")),
        DATA,
        media_type="text/markdown",
        role=ArtifactRole.ORIGINAL,
    )
    with pytest.raises(NotFound):
        registry.read_artifact(context("t1", sites=("site-b",)), site_scoped.artifact_id)


def test_path_traversal_fails_before_content(registry: Registry, tmp_path: Path) -> None:
    for bad in ("../../etc/passwd", "art_../x", "/etc/passwd"):
        with pytest.raises(NotFound):
            registry.read_artifact(context("t1"), bad)
    store = LocalBlobStore(tmp_path / "blobs")
    with pytest.raises(InvalidArtifactReference):
        store.get("../" + "a" * 61)


def test_correction_retains_original_and_diff(registry: Registry) -> None:
    ctx = context("t1")
    original = registry.register_artifact(
        ResourceScope(tenant_id="t1"), DATA, media_type="text/markdown", role=ArtifactRole.IMPORTED_RENDERING
    )
    fixed = DATA.replace(b"keep records.", b"make and keep records.")
    correction, diff = registry.record_correction(
        ctx, original.artifact_id, fixed, author="reviewer-1", reason="restore omitted words from PDF"
    )
    assert registry.read_artifact(ctx, original.artifact_id) == DATA
    assert correction.derived_from == (original.artifact_id,)
    assert correction.derivation is not None and correction.derivation.author == "reviewer-1"
    assert diff.derived_from == (original.artifact_id, correction.artifact_id)
    diff_text = registry.read_text(ctx, diff.artifact_id)
    assert "-(1) A person must keep records." in diff_text and "+(1) A person must make and keep records." in diff_text


def test_excerpts_match_immutable_spans(registry: Registry) -> None:
    ctx = context("t1")
    data = LITEPARSE_MD.read_bytes()
    record = registry.register_artifact(
        ResourceScope(tenant_id="t1"), data, media_type="text/markdown", role=ArtifactRole.IMPORTED_RENDERING
    )
    parsed = parse_legislation_markdown(data.decode("utf-8"), record.artifact_id)
    span = parsed.provisions["s142(2)(c)"].spans[0]
    assert registry.excerpt(ctx, span) == "(c) the period for which records must be retained;"
    # Code point offsets: the excerpt's UTF-8 bytes occur at the byte offset of the preceding text.
    prefix = data.decode("utf-8")[: span.char_start].encode("utf-8")
    assert (
        data[len(prefix) : len(prefix) + len(registry.excerpt(ctx, span).encode())]
        == registry.excerpt(ctx, span).encode()
    )
    with pytest.raises(NotFound):
        registry.excerpt(context("t2"), span)


def test_registry_requires_explicit_migration(tmp_path: Path) -> None:
    with pytest.raises(SchemaMissing):
        Registry.open(tmp_path / "fresh.sqlite3", LocalBlobStore(tmp_path / "b"))
