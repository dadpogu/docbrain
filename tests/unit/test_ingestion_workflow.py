"""DB-005/011 (offline subset) and E01: resumable, idempotent Markdown ingestion."""

from __future__ import annotations

import pytest

from docbrain.models import ResourceScope
from docbrain.registry import JobCancelled, JobState, LeaseLost, Registry
from docbrain.workflows.ingestion import SourceManifest, ingest_legislation_markdown
from tests.conftest import EARLIER_MD, LITEPARSE_MD, SIDECAR_JSON, FakeClock, load_fixture

SCOPE = ResourceScope(tenant_id="t1")


class SimulatedCrash(BaseException):
    """A process death: bypasses normal error handling, so the lease is simply left to expire."""


@pytest.fixture(scope="module")
def manifest() -> SourceManifest:
    return SourceManifest.model_validate(load_fixture("recycling_act", "manifest.json"))


def test_candidates_share_one_document_and_version_but_not_builds(registry: Registry, manifest: SourceManifest) -> None:
    md = ingest_legislation_markdown(
        registry, SCOPE, EARLIER_MD.read_bytes(), worker_id="w1", manifest=manifest, sidecar=SIDECAR_JSON.read_bytes()
    )
    lite = ingest_legislation_markdown(registry, SCOPE, LITEPARSE_MD.read_bytes(), worker_id="w1", manifest=manifest)
    assert md.state is lite.state is JobState.SUCCEEDED
    assert md.association == lite.association == "manifest"
    assert md.doc_id == lite.doc_id == "t1:au:C2020A00119"
    assert md.version_id == lite.version_id == "t1:au:C2020A00119/C2026C00317"
    assert md.artifact_id != lite.artifact_id and md.build_id != lite.build_id
    assert md.metadata_conflicts == lite.metadata_conflicts == []
    assert md.section_count == 188 and lite.section_count == 187 and lite.unresolved_tables > 0
    assert len(registry.versions(md.doc_id)) == 1
    relations = set(registry.renderings(md.version_id).values())  # type: ignore[arg-type]
    assert {"liteparse_markdown_candidate", "metadata_sidecar"} <= relations
    # Identical re-import: same job, same build, nothing new.
    again = ingest_legislation_markdown(registry, SCOPE, LITEPARSE_MD.read_bytes(), worker_id="w2", manifest=manifest)
    assert (again.job_id, again.build_id, again.build_created) == (lite.job_id, lite.build_id, True)
    assert len(registry.builds("t1")) == 2


def test_metadata_less_import_without_manifest_stays_unresolved(registry: Registry) -> None:
    result = ingest_legislation_markdown(
        registry, SCOPE, LITEPARSE_MD.read_bytes(), worker_id="w1", original_name="C2026C00317.md"
    )
    assert result.state is JobState.SUCCEEDED
    assert result.association == "unresolved" and result.doc_id is None and result.version_id is None
    assert registry.documents("t1") == []


def test_interrupted_job_resumes_without_rebuilding(
    registry: Registry, clock: FakeClock, manifest: SourceManifest
) -> None:
    data = LITEPARSE_MD.read_bytes()

    def crash_after_parse(stage: str) -> None:
        if stage == "parse":
            raise SimulatedCrash

    with pytest.raises(SimulatedCrash):
        ingest_legislation_markdown(
            registry, SCOPE, data, worker_id="w1", manifest=manifest, after_stage=crash_after_parse, lease_seconds=60
        )
    assert registry.builds("t1") == []
    # Another worker cannot steal a live lease...
    blocked = ingest_legislation_markdown(registry, SCOPE, data, worker_id="w2", manifest=manifest)
    assert blocked.state is JobState.RUNNING and blocked.build_id is None
    # ...but resumes once it expires, reusing persisted stage outputs.
    clock.advance(61)
    resumed = ingest_legislation_markdown(registry, SCOPE, data, worker_id="w2", manifest=manifest)
    assert resumed.state is JobState.SUCCEEDED
    assert resumed.resumed_stages == ["register", "parse"]
    assert resumed.parse_artifact_id == blocked.parse_artifact_id
    assert len(registry.builds("t1")) == 1


def test_cancelled_job_never_builds(registry: Registry, manifest: SourceManifest) -> None:
    data = EARLIER_MD.read_bytes()

    def cancel_during_run(stage: str) -> None:
        if stage == "register":
            (job,) = registry.jobs("t1")
            registry.request_cancel(job.job_id)

    with pytest.raises(JobCancelled):
        ingest_legislation_markdown(
            registry, SCOPE, data, worker_id="w1", manifest=manifest, after_stage=cancel_during_run
        )
    (job,) = registry.jobs("t1")
    assert job.state is JobState.CANCELLED
    assert registry.builds("t1") == []
    rerun = ingest_legislation_markdown(registry, SCOPE, data, worker_id="w2", manifest=manifest)
    assert rerun.state is JobState.CANCELLED and rerun.build_id is None


def test_expired_worker_cannot_record_stages(registry: Registry, clock: FakeClock) -> None:
    job = registry.enqueue_job("t1", "ingest_markdown", "k1", {})
    lease_a = registry.claim_job(job.job_id, "a", lease_seconds=10)
    assert lease_a is not None
    clock.advance(11)
    lease_b = registry.claim_job(job.job_id, "b", lease_seconds=10)
    assert lease_b is not None and lease_b.attempt == 2
    with pytest.raises(LeaseLost):
        registry.complete_stage(lease_a, "parse", {"x": 1})
    assert registry.complete_stage(lease_b, "parse", {"x": 2}) == {"x": 2}


def test_attempt_budget_is_enforced(registry: Registry, manifest: SourceManifest) -> None:
    bad = b"\xff\xfe not utf-8"
    for _ in range(3):
        with pytest.raises(UnicodeDecodeError):
            ingest_legislation_markdown(registry, SCOPE, bad, worker_id="w1", manifest=manifest)
    result = ingest_legislation_markdown(registry, SCOPE, bad, worker_id="w1", manifest=manifest)
    assert result.state is JobState.FAILED
    assert "UnicodeDecodeError" in (registry.get_job(result.job_id).error or "")
