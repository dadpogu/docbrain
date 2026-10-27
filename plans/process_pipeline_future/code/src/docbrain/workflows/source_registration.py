"""Moved from src/docbrain/workflows/ingestion.py (process application). Relies on ingestion.py imports."""

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
