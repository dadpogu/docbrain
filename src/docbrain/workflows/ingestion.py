"""Resumable offline ingestion of Markdown renderings and mixed knowledge sources (DB-005/006/011/031).

Stages run under a registry job lease. Each completed stage persists its output, so a restarted
worker skips completed stages and reuses their artifact IDs; a cancelled or expired worker cannot
record further stages or mark its build validated. Identity comes only from an explicit
:class:`SourceManifest` (or the rendering's own front-matter claim), never from a filename.

This module covers register → parse/import → metadata reconciliation → structural validation.
Chunking, embedding, and manifest publication are later stages (DB-011 onwards).
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from pydantic import BaseModel, ConfigDict

from ..models import (
    ApprovalState,
    ArtifactRole,
    AuthoritySubtype,
    Derivation,
    DocumentKey,
    LegalTime,
    LogicalDocument,
    OfficialVersion,
    ParsedLegislation,
    RequestContext,
    ResourceScope,
    SiteScope,
    SiteScopeKind,
    SourceRole,
    TableStatus,
    sha256_hex,
)
from ..parsing import (
    MetadataBasis,
    MetadataClaim,
    claims_from_cover,
    claims_from_metadata,
    front_matter_metadata,
    load_sidecar_json,
    parse_legislation_markdown,
    parse_operational_markdown,
    read_front_matter,
)
from ..registry import JobCancelled, JobState, LeaseLost, Registry, deterministic_id

PIPELINE_VERSION = "markdown-import/1"


class ManifestArtifact(BaseModel):
    model_config = ConfigDict(frozen=True)

    sha256: str
    role: ArtifactRole
    media_type: str
    relation: str  # e.g. "original_pdf", "metadata_sidecar", "imported_markdown_candidate"
    path: str | None = None  # where the supplied copy lives; informational only
    derivation: Derivation | None = None


class ReviewedFact(BaseModel):
    model_config = ConfigDict(frozen=True)

    field: str
    value: Any
    reviewer: str
    note: str


class SourceManifest(BaseModel):
    """Explicit association of artifacts with one logical document and claimed official version."""

    model_config = ConfigDict(frozen=True)

    authority: str
    identifier: str
    official_id: str
    title: str | None = None
    jurisdiction: str | None = None
    language: str | None = None
    source_role: SourceRole = SourceRole.REGULATORY_AUTHORITY
    authority_subtype: AuthoritySubtype | None = AuthoritySubtype.LAW
    artifacts: tuple[ManifestArtifact, ...] = ()
    reviewed_facts: tuple[ReviewedFact, ...] = ()

    def artifact(self, sha256: str) -> ManifestArtifact | None:
        return next((a for a in self.artifacts if a.sha256 == sha256), None)

    @property
    def fingerprint(self) -> str:
        return sha256_hex(self.model_dump_json().encode("utf-8"))


class IngestionResult(BaseModel):
    job_id: str
    state: JobState
    artifact_id: str | None = None
    association: str | None = None  # manifest | front_matter_claim | unresolved
    doc_id: str | None = None
    version_id: str | None = None
    build_id: str | None = None
    build_created: bool = False
    parse_artifact_id: str | None = None
    section_count: int = 0
    unresolved_tables: int = 0
    warning_count: int = 0
    metadata_conflicts: list[str] = []
    resumed_stages: list[str] = []


StageHook = Callable[[str], None]


def ingest_legislation_markdown(
    registry: Registry,
    scope: ResourceScope,
    data: bytes,
    *,
    worker_id: str,
    manifest: SourceManifest | None = None,
    sidecar: bytes | None = None,
    original_name: str | None = None,
    after_stage: StageHook | None = None,
    lease_seconds: float = 300.0,
) -> IngestionResult:
    """Import one Markdown rendering. Re-running with the same inputs resumes or returns the same job."""
    digest = sha256_hex(data)
    sidecar_digest = sha256_hex(sidecar) if sidecar is not None else "-"
    manifest_fp = manifest.fingerprint if manifest else "-"
    job_key = "|".join(("ingest", scope.model_dump_json(), digest, sidecar_digest, manifest_fp, PIPELINE_VERSION))
    job = registry.enqueue_job(scope.tenant_id, "ingest_markdown", job_key, {"sha256": digest})
    result = IngestionResult(job_id=job.job_id, state=job.state)
    if job.state in (JobState.SUCCEEDED, JobState.CANCELLED, JobState.FAILED):
        return _result_from_stages(registry, result, job.state)
    lease = registry.claim_job(job.job_id, worker_id, lease_seconds=lease_seconds)
    if lease is None:
        return _result_from_stages(registry, result, registry.get_job(job.job_id).state)

    def stage(name: str, run: Callable[[], dict[str, Any]]) -> dict[str, Any]:
        done = registry.stage_output(lease.job_id, name)
        if done is not None:
            result.resumed_stages.append(name)
            return done
        output = registry.complete_stage(lease, name, run())
        if after_stage is not None:
            after_stage(name)
        return output

    try:
        registered = stage("register", lambda: _register(registry, scope, data, manifest, sidecar, original_name))
        parsed_out = stage("parse", lambda: _parse(registry, scope, data, registered))
        stage("metadata", lambda: _metadata(registry, scope, registered, parsed_out, manifest, sidecar))
        stage("validate", lambda: _validate(registry, scope, registered, parsed_out))
        registry.finish_job(lease)
    except (JobCancelled, LeaseLost):
        raise  # this worker no longer owns the job; it must not record anything else
    except Exception as exc:
        registry.fail_attempt(lease, f"{type(exc).__name__}: {exc}")
        raise
    return _result_from_stages(registry, result, JobState.SUCCEEDED)


def _result_from_stages(registry: Registry, result: IngestionResult, state: JobState) -> IngestionResult:
    result.state = state
    reg = registry.stage_output(result.job_id, "register") or {}
    parsed = registry.stage_output(result.job_id, "parse") or {}
    meta = registry.stage_output(result.job_id, "metadata") or {}
    valid = registry.stage_output(result.job_id, "validate") or {}
    result.artifact_id = reg.get("artifact_id")
    result.association = reg.get("association")
    result.doc_id = reg.get("doc_id")
    result.version_id = reg.get("version_id")
    result.parse_artifact_id = parsed.get("parse_artifact_id")
    result.section_count = parsed.get("section_count", 0)
    result.unresolved_tables = parsed.get("unresolved_tables", 0)
    result.warning_count = parsed.get("warning_count", 0)
    result.metadata_conflicts = meta.get("conflicts", [])
    result.build_id = valid.get("build_id")
    result.build_created = valid.get("build_created", False)
    return result


def _register(
    registry: Registry,
    scope: ResourceScope,
    data: bytes,
    manifest: SourceManifest | None,
    sidecar: bytes | None,
    original_name: str | None,
) -> dict[str, Any]:
    digest = sha256_hex(data)
    entry = manifest.artifact(digest) if manifest else None
    record = registry.register_artifact(
        scope,
        data,
        media_type="text/markdown",
        role=ArtifactRole.IMPORTED_RENDERING,
        original_name=original_name,
        derivation=entry.derivation if entry else Derivation(method="imported_markdown"),
    )
    out: dict[str, Any] = {
        "artifact_id": record.artifact_id,
        "association": "unresolved",
        "doc_id": None,
        "version_id": None,
        "sidecar_artifact_id": None,
    }
    text = data.decode("utf-8", errors="strict")
    identity: tuple[str, str, str, str | None] | None = None
    if manifest is not None and entry is not None:
        identity = (manifest.authority, manifest.identifier, manifest.official_id, manifest.title)
        out["association"] = "manifest"
    elif manifest is None:
        # The rendering's own front matter is a provider claim of identity (recorded as such).
        front = read_front_matter(text)
        if front and front.get("identifier") and front.get("register_id") and front.get("jurisdiction"):
            identity = (
                str(front["jurisdiction"]),
                str(front["identifier"]),
                str(front["register_id"]),
                str(front.get("title")) if front.get("title") else None,
            )
            out["association"] = "front_matter_claim"
    if identity is None:
        return out
    authority, identifier, official_id, title = identity
    key = DocumentKey(tenant_id=scope.tenant_id, authority=authority, identifier=identifier)
    doc = registry.register_document(
        LogicalDocument(
            key=key,
            title=title,
            source_role=manifest.source_role if manifest else SourceRole.REGULATORY_AUTHORITY,
            authority_subtype=manifest.authority_subtype if manifest else AuthoritySubtype.LAW,
            jurisdiction=manifest.jurisdiction if manifest else authority,
            language=manifest.language if manifest else None,
            scope=scope,
        )
    )
    version = registry.register_version(OfficialVersion(doc_id=doc.doc_id, official_id=official_id))
    registry.link_rendering(version.version_id, record.artifact_id, entry.relation if entry else "imported_markdown")
    out.update(doc_id=doc.doc_id, version_id=version.version_id)
    if sidecar is not None:
        side_entry = manifest.artifact(sha256_hex(sidecar)) if manifest else None
        side = registry.register_artifact(
            scope, sidecar, media_type="application/json", role=ArtifactRole.METADATA_SIDECAR
        )
        registry.link_rendering(
            version.version_id, side.artifact_id, side_entry.relation if side_entry else "metadata_sidecar"
        )
        out["sidecar_artifact_id"] = side.artifact_id
    return out


def _parse(registry: Registry, scope: ResourceScope, data: bytes, registered: dict[str, Any]) -> dict[str, Any]:
    artifact_id = registered["artifact_id"]
    parsed = parse_legislation_markdown(data.decode("utf-8", errors="strict"), artifact_id)
    output = registry.register_artifact(
        scope,
        parsed.model_dump_json().encode("utf-8"),
        media_type="application/json",
        role=ArtifactRole.PARSE_OUTPUT,
        derived_from=(artifact_id,),
        derivation=Derivation(method="docbrain_markdown_parse", tool="docbrain.parsing", tool_version=PIPELINE_VERSION),
    )
    return {
        "parse_artifact_id": output.artifact_id,
        "section_count": len(parsed.section_numbers()),
        "unresolved_tables": sum(1 for t in parsed.tables if t.status is TableStatus.UNRESOLVED),
        "warning_count": len(parsed.warnings),
        "image_warnings": [w.message for w in parsed.warnings if w.code == "image_unavailable"],
    }


def _metadata(
    registry: Registry,
    scope: ResourceScope,
    registered: dict[str, Any],
    parsed_out: dict[str, Any],
    manifest: SourceManifest | None,
    sidecar: bytes | None,
) -> dict[str, Any]:
    version_id = registered.get("version_id")
    if version_id is None:
        return {"conflicts": [], "skipped": "identity unresolved"}
    system = RequestContext(
        tenant_id=scope.tenant_id,
        principal_id="system:ingestion",
        access_partitions=frozenset({scope.access_partition}),
        site_ids=scope.site.shared_with | frozenset(filter(None, [scope.site.site_id])),
    )
    parsed = ParsedLegislation.model_validate_json(registry.read_artifact(system, parsed_out["parse_artifact_id"]))
    claims: list[MetadataClaim] = claims_from_cover(parsed)
    front = front_matter_metadata(parsed)
    if front is not None:
        claims += claims_from_metadata(front, MetadataBasis.PROVIDER_FRONT_MATTER, parsed.artifact_id)
    if sidecar is not None and registered.get("sidecar_artifact_id"):
        claims += claims_from_metadata(
            load_sidecar_json(sidecar), MetadataBasis.PROVIDER_SIDECAR, registered["sidecar_artifact_id"]
        )
    if manifest is not None:
        claims.append(
            MetadataClaim(
                field="register_id",
                value=manifest.official_id,
                basis=MetadataBasis.IMPORT_MANIFEST,
                artifact_id=parsed.artifact_id,
            )
        )
        claims.append(
            MetadataClaim(
                field="principal_identifier",
                value=manifest.identifier,
                basis=MetadataBasis.IMPORT_MANIFEST,
                artifact_id=parsed.artifact_id,
            )
        )
        for fact in manifest.reviewed_facts:
            claims.append(
                MetadataClaim(
                    field=fact.field,
                    value=fact.value,
                    basis=MetadataBasis.REVIEWED_SOURCE_FACT,
                    artifact_id=parsed.artifact_id,
                )
            )
    registry.record_claims(version_id, claims)
    reconciliation = registry.reconcile_version(scope.tenant_id, version_id)
    return {"conflicts": sorted(c.field for c in reconciliation.conflicts)}


def _validate(
    registry: Registry, scope: ResourceScope, registered: dict[str, Any], parsed_out: dict[str, Any]
) -> dict[str, Any]:
    if parsed_out["section_count"] == 0:
        raise ValueError("no legislative sections were recognised; refusing to build")
    build_id, created = registry.get_or_create_build(
        scope.tenant_id, registered.get("version_id"), registered["artifact_id"], PIPELINE_VERSION
    )
    status = "validated_with_unresolved_tables" if parsed_out["unresolved_tables"] else "validated"
    registry.set_build_status(build_id, status, parsed_out["parse_artifact_id"])
    return {"build_id": build_id, "build_created": created, "status": status}


# --------------------------------------------------------------------------------------------
# Mixed knowledge sources (DB-031)
# --------------------------------------------------------------------------------------------


class SourceRegistration(BaseModel):
    """Caller-asserted registration of a non-legislation source. Folder location is never consulted."""

    model_config = ConfigDict(frozen=True)

    role: SourceRole
    site: SiteScope = SiteScope.unresolved()
    process_id: str | None = None
    access_partition: str = "internal"
    declared_id: str | None = None  # falls back to the document's own declared ID
    derived_from: tuple[str, ...] = ()  # artifact IDs, required for generated derivatives


class RegisteredSource(BaseModel):
    document: LogicalDocument
    artifact_id: str
    revision: str | None
    claimed_status: str | None
    site_scope_resolved: bool
    findings: list[str]


def register_operational_source(
    registry: Registry,
    tenant_id: str,
    data: bytes,
    registration: SourceRegistration,
    *,
    original_name: str | None = None,
    link_exists: Callable[[str], bool] | None = None,
) -> RegisteredSource:
    """Register a process, work instruction, site fact, policy, template, or generated derivative."""
    if registration.role is SourceRole.REGULATORY_AUTHORITY:
        raise ValueError("register legislation through ingest_legislation_markdown and a source manifest")
    if registration.role is SourceRole.GENERATED_DERIVATIVE and not registration.derived_from:
        raise ValueError("a generated derivative must name the artifacts it was derived from")
    scope = ResourceScope(
        tenant_id=tenant_id,
        access_partition=registration.access_partition,
        site=registration.site,
        process_id=registration.process_id,
    )
    text = data.decode("utf-8", errors="strict")
    record = registry.register_artifact(
        scope,
        data,
        media_type="text/markdown",
        role=ArtifactRole.ORIGINAL,
        original_name=original_name,
        derived_from=registration.derived_from,
        derivation=Derivation(method="generated_derivative") if registration.derived_from else None,
    )
    doc = parse_operational_markdown(text, record.artifact_id, link_exists=link_exists)
    declared = registration.declared_id or doc.declared_id or deterministic_id("doc", record.sha256)[4:20]
    site_id = registration.site.site_id if registration.site.kind is SiteScopeKind.SITE else None
    authority = {
        SiteScopeKind.SITE: "site",
        SiteScopeKind.SHARED: "shared",
        SiteScopeKind.UNRESOLVED: "unscoped",
        SiteScopeKind.NOT_SITE_SPECIFIC: "org",
    }[registration.site.kind]
    logical = registry.register_document(
        LogicalDocument(
            key=DocumentKey(tenant_id=tenant_id, authority=authority, identifier=declared, site_id=site_id),
            title=doc.title,
            source_role=registration.role,
            scope=scope,
            owner=doc.owner,
            approval=ApprovalState(claimed_label=doc.claimed_status),
            aliases=(),
        )
    )
    revision = doc.revision or record.sha256[:12]
    version = registry.register_version(
        OfficialVersion(
            doc_id=logical.doc_id, official_id=f"rev-{revision}-{record.sha256[:12]}", legal_time=LegalTime()
        )
    )
    registry.link_rendering(version.version_id, record.artifact_id, "source_document")
    return RegisteredSource(
        document=logical,
        artifact_id=record.artifact_id,
        revision=doc.revision,
        claimed_status=doc.claimed_status,
        site_scope_resolved=registration.site.kind is not SiteScopeKind.UNRESOLVED,
        findings=sorted({f.code for f in doc.findings}),
    )


__all__ = [
    "IngestionResult",
    "ManifestArtifact",
    "PIPELINE_VERSION",
    "RegisteredSource",
    "ReviewedFact",
    "SourceManifest",
    "SourceRegistration",
    "ingest_legislation_markdown",
    "register_operational_source",
]
