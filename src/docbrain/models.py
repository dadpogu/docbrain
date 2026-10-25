"""
Canonical Data Models & Grounding Schema for Tri-Store Hybrid RAG.
Addresses Gap 1: Grounding & Cross-Representation Linking
Addresses Gap 5: Structured Evidence Bundle Specification
"""

import hashlib
import re
import uuid
from datetime import date, datetime
from enum import Enum, StrEnum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


class DocumentFormat(str, Enum):
    PDF = "pdf"
    DOCX = "docx"
    HTML = "html"
    MARKDOWN = "markdown"


class QueryIntent(str, Enum):
    FACTUAL_LOOKUP = "factual_lookup"           # Point facts -> Vector Store
    THEMATIC_SUMMARY = "thematic_summary"       # High-level overview -> Semantic Layer
    MULTI_HOP_RELATIONAL = "multi_hop_relational" # Relationships/entities -> Knowledge Graph
    GLOBAL_CORPUS = "global_corpus"             # Corpus-wide patterns -> KG Communities + L3 Summaries
    COMPLEX_HYBRID = "complex_hybrid"           # Broad/ambiguous -> Parallel fan-out


class ProvenanceSpan(BaseModel):
    """Pinpoints the exact source location within a document."""
    doc_id: str
    chunk_id: str
    page_numbers: List[int] = Field(default_factory=list)
    section_breadcrumb: str = Field(..., description="e.g., Section 4 > Clause 4.2")
    char_start: Optional[int] = None
    char_end: Optional[int] = None


class CanonicalChunk(BaseModel):
    """Unified chunk representation across all stores."""
    chunk_id: str = Field(..., description="Format: {doc_id}#c{index:04d}")
    doc_id: str
    chunk_index: int
    text: str
    content_hash: str
    provenance: ProvenanceSpan
    entity_ids: List[str] = Field(default_factory=list, description="IDs of entities mentioned in this chunk")
    dense_vector: Optional[List[float]] = None
    sparse_indices: Optional[List[int]] = None
    sparse_values: Optional[List[float]] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)

    @classmethod
    def create(cls, doc_id: str, index: int, text: str, breadcrumb: str, pages: List[int]) -> "CanonicalChunk":
        chunk_id = f"{doc_id}#c{index:04d}"
        content_hash = hashlib.sha256(text.encode("utf-8")).hexdigest()
        prov = ProvenanceSpan(
            doc_id=doc_id,
            chunk_id=chunk_id,
            page_numbers=pages,
            section_breadcrumb=breadcrumb
        )
        return cls(
            chunk_id=chunk_id,
            doc_id=doc_id,
            chunk_index=index,
            text=text,
            content_hash=content_hash,
            provenance=prov
        )


class SemanticTreeNode(BaseModel):
    """Node in the RAPTOR hierarchical summary tree."""
    node_id: str = Field(..., description="Format: {doc_id}#L{level}_c{cluster_id}")
    doc_id: str
    level: int = Field(..., description="0=raw chunk, 1=section, 2=document, 3=domain")
    summary_text: str
    title: str
    parent_node_id: Optional[str] = None
    children_node_ids: List[str] = Field(default_factory=list)
    leaf_chunk_ids: List[str] = Field(default_factory=list, description="All underlying raw chunks grounded by this node")
    embedding: Optional[List[float]] = None
    is_stale: bool = False


class EntityNode(BaseModel):
    """Knowledge Graph entity with provenance grounding."""
    entity_id: str = Field(..., description="Canonical ID: ent_{normalized_slug}")
    name: str
    type: str = Field(..., description="e.g. Organization, Person, Regulation, Contract")
    description: str
    aliases: List[str] = Field(default_factory=list)
    source_chunk_ids: List[str] = Field(default_factory=list)
    doc_ids: List[str] = Field(default_factory=list)


class EntityRelation(BaseModel):
    """Knowledge Graph edge with provenance grounding."""
    relation_id: str
    source_id: str
    target_id: str
    relation_type: str = Field(..., description="e.g. REGULATES, GOVERNED_BY, PARTNERS_WITH")
    description: str
    weight: float = 1.0
    source_chunk_ids: List[str] = Field(default_factory=list)


# --- Evidence Bundle Models ---

class EvidenceType(str, Enum):
    EXACT_EXCERPT = "exact_excerpt"
    MACRO_SUMMARY = "macro_summary"
    GRAPH_RELATION_PATH = "graph_relation_path"
    COMMUNITY_REPORT = "community_report"


class EvidenceItem(BaseModel):
    citation_id: str = Field(..., description="e.g. EV-01")
    source_store: str = Field(..., description="VectorStore | SemanticLayer | KnowledgeGraph")
    evidence_type: EvidenceType
    content: str
    relevance_score: float = Field(..., description="Calibrated cross-encoder score [0.0 - 1.0]")
    supporting_chunk_ids: List[str] = Field(default_factory=list)
    provenance: Optional[ProvenanceSpan] = None
    graph_path: Optional[List[str]] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)


class EvidenceBundle(BaseModel):
    query: str
    classified_intent: QueryIntent
    evidence_items: List[EvidenceItem]
    total_sources_consulted: int
    conflicting_facts_detected: bool = False
    conflict_notes: Optional[str] = None
    token_budget_used: int = 0
    generated_at: str = Field(default_factory=lambda: datetime.utcnow().isoformat())


# =============================================================================
# Canonical identity, scope, provenance, and legal-time contracts (DB-004).
#
# The prototype models above remain importable for the existing modules. The
# contracts below are the versioned, tenant-scoped source of truth for new code.
# =============================================================================

#: Offsets in every :class:`SourceSpan` use this convention.
TEXT_OFFSET_CONVENTION = (
    "End-exclusive Unicode code point offsets into the artifact bytes decoded as strict UTF-8, "
    "with the original line endings (LF or CRLF) retained."
)

#: Fixed namespace for deterministic vector-store point IDs. Changing it re-keys every point.
POINT_ID_NAMESPACE = uuid.UUID("2b7f6a8e-3c51-5d0a-9e47-6f1d2c8b9a30")

_ID_SEGMENT = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,127}$")


def _check_id(value: str, what: str) -> str:
    if not _ID_SEGMENT.match(value):
        raise ValueError(f"invalid {what} {value!r}: use letters, digits, '.', '_' or '-'")
    return value


def sha256_hex(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def point_uuid(canonical_id: str) -> uuid.UUID:
    """Map a readable canonical domain ID to a deterministic UUID point ID."""
    return uuid.uuid5(POINT_ID_NAMESPACE, canonical_id)


# --- Scope and trusted request context ---------------------------------------


class SiteScopeKind(StrEnum):
    NOT_SITE_SPECIFIC = "not_site_specific"  # e.g. legislation registered for a corpus
    SITE = "site"
    SHARED = "shared"  # explicitly authorized for the listed sites only
    UNRESOLVED = "unresolved"  # site scope missing: never treated as shared


class SiteScope(BaseModel):
    model_config = ConfigDict(frozen=True)

    kind: SiteScopeKind = SiteScopeKind.NOT_SITE_SPECIFIC
    site_id: Optional[str] = None
    shared_with: frozenset[str] = frozenset()

    @model_validator(mode="after")
    def _consistent(self) -> "SiteScope":
        if self.kind is SiteScopeKind.SITE:
            if not self.site_id or self.shared_with:
                raise ValueError("a site scope names exactly one site_id")
            _check_id(self.site_id, "site_id")
        elif self.kind is SiteScopeKind.SHARED:
            if self.site_id or not self.shared_with:
                raise ValueError("a shared scope must explicitly list the authorized sites")
            for site in self.shared_with:
                _check_id(site, "site_id")
        elif self.site_id or self.shared_with:
            raise ValueError(f"{self.kind.value} scope cannot name sites")
        return self

    @classmethod
    def site(cls, site_id: str) -> "SiteScope":
        return cls(kind=SiteScopeKind.SITE, site_id=site_id)

    @classmethod
    def shared(cls, *site_ids: str) -> "SiteScope":
        return cls(kind=SiteScopeKind.SHARED, shared_with=frozenset(site_ids))

    @classmethod
    def unresolved(cls) -> "SiteScope":
        return cls(kind=SiteScopeKind.UNRESOLVED)


class ResourceScope(BaseModel):
    """Who may read a stored resource. Carried on artifacts, documents, and evidence."""

    model_config = ConfigDict(frozen=True)

    tenant_id: str
    access_partition: str = "internal"
    corpus_id: str = "default"
    site: SiteScope = SiteScope()
    process_id: Optional[str] = None

    @field_validator("tenant_id", "access_partition", "corpus_id")
    @classmethod
    def _ids(cls, value: str) -> str:
        return _check_id(value, "scope identifier")


class RequestContext(BaseModel):
    """Trusted caller identity. Built by the application from authentication, never from tool input."""

    model_config = ConfigDict(frozen=True)

    tenant_id: str
    principal_id: str
    access_partitions: frozenset[str] = frozenset({"internal"})
    site_ids: frozenset[str] = frozenset()
    roles: frozenset[str] = frozenset()
    authenticated: bool = True


def is_authorized(ctx: RequestContext, scope: ResourceScope) -> bool:
    """Deny unless tenant, partition, and site scope all permit the caller."""
    if not ctx.authenticated or ctx.tenant_id != scope.tenant_id:
        return False
    if scope.access_partition not in ctx.access_partitions:
        return False
    site = scope.site
    if site.kind is SiteScopeKind.NOT_SITE_SPECIFIC:
        return True
    if site.kind is SiteScopeKind.SITE:
        return site.site_id in ctx.site_ids
    if site.kind is SiteScopeKind.SHARED:
        return bool(site.shared_with & ctx.site_ids)
    return False  # UNRESOLVED site scope is never readable as site evidence


# --- Source roles, artifacts, and derivations ---------------------------------


class SourceRole(StrEnum):
    REGULATORY_AUTHORITY = "regulatory_authority"
    PROCESS_DESCRIPTION = "process_description"
    SITE_FACT = "site_fact"
    ORGANIZATIONAL_POLICY = "organizational_policy"
    TEMPLATE = "template"
    GENERATED_DERIVATIVE = "generated_derivative"


class AuthoritySubtype(StrEnum):
    LAW = "law"
    PERMIT_CONDITION = "permit_condition"
    STANDARD = "standard"
    GUIDANCE = "guidance"


class ArtifactRole(StrEnum):
    ORIGINAL = "original"
    METADATA_SIDECAR = "metadata_sidecar"
    PARSER_RESPONSE = "parser_response"
    IMPORTED_RENDERING = "imported_rendering"
    CANONICAL_TEXT = "canonical_text"
    PARSE_OUTPUT = "parse_output"
    CORRECTION = "correction"
    CORRECTION_DIFF = "correction_diff"


class Derivation(BaseModel):
    """How an artifact was produced. ``None`` fields are unknown, not defaults."""

    model_config = ConfigDict(frozen=True)

    method: str
    tool: Optional[str] = None
    tool_version: Optional[str] = None
    settings: Optional[Dict[str, Any]] = None
    attribution: Optional[str] = None
    author: Optional[str] = None
    reason: Optional[str] = None


class ArtifactRecord(BaseModel):
    model_config = ConfigDict(frozen=True)

    artifact_id: str
    scope: ResourceScope
    sha256: str
    size: int
    media_type: str
    role: ArtifactRole
    original_name: Optional[str] = None  # informational only; never identity
    derived_from: tuple[str, ...] = ()
    derivation: Optional[Derivation] = None
    created_at: datetime


# --- Documents, versions, and legal time ---------------------------------------


class DocumentKey(BaseModel):
    """Logical document identity: tenant + authority + identifier (+ site for site documents).

    File paths and names never participate, so moving or renaming a source keeps its identity.
    """

    model_config = ConfigDict(frozen=True)

    tenant_id: str
    authority: str
    identifier: str
    site_id: Optional[str] = None

    @field_validator("tenant_id", "authority", "identifier")
    @classmethod
    def _ids(cls, value: str) -> str:
        return _check_id(value, "document key segment")

    @property
    def doc_id(self) -> str:
        base = f"{self.tenant_id}:{self.authority}:{self.identifier}"
        return f"{base}@{self.site_id}" if self.site_id else base

    @property
    def display_id(self) -> str:
        return f"{self.authority}:{self.identifier}"


class SourceAlias(BaseModel):
    """A URI a source was obtained from. Mutable aliases (``/latest/``) never identify a version."""

    model_config = ConfigDict(frozen=True)

    uri: str
    mutable: bool

    @classmethod
    def from_uri(cls, uri: str) -> "SourceAlias":
        return cls(uri=uri, mutable=bool(re.search(r"/latest(/|$)", uri)))


class LegalTime(BaseModel):
    """Distinct legal and observation dates. Unknown values stay ``None``."""

    model_config = ConfigDict(frozen=True)

    original_enactment_date: Optional[date] = None
    compilation_date: Optional[date] = None
    version_start: Optional[date] = None
    last_amended: Optional[date] = None
    registration_date: Optional[date] = None
    effective_from: Optional[date] = None
    effective_to: Optional[date] = None
    retrieved_on: Optional[date] = None
    observed_at: Optional[datetime] = None
    provision_commencement_known: bool = False

    def as_of_limitations(self) -> List[str]:
        notes: List[str] = []
        if self.effective_from is None:
            notes.append("effective-from date is unknown")
        if self.effective_to is None:
            notes.append("effective-to date is unknown; later versions may exist")
        if not self.provision_commencement_known:
            notes.append(
                "version dates apply to the document; individual provisions may have commenced on other dates"
            )
        return notes

    def covers(self, as_of: date) -> Optional[bool]:
        """Whether this version is known to apply on ``as_of``; ``None`` when that is unknown."""
        if self.effective_from is None:
            return None
        if as_of < self.effective_from:
            return False
        if self.effective_to is None:
            return None
        return as_of < self.effective_to


class ApprovalState(BaseModel):
    """A document's self-declared label is kept apart from authenticated approval records."""

    model_config = ConfigDict(frozen=True)

    claimed_label: Optional[str] = None
    verified_decision_id: Optional[str] = None

    @property
    def is_verified(self) -> bool:
        return self.verified_decision_id is not None


class LogicalDocument(BaseModel):
    model_config = ConfigDict(frozen=True)

    key: DocumentKey
    title: Optional[str] = None
    source_role: SourceRole
    authority_subtype: Optional[AuthoritySubtype] = None
    jurisdiction: Optional[str] = None
    language: Optional[str] = None
    scope: ResourceScope
    aliases: tuple[SourceAlias, ...] = ()
    owner: Optional[str] = None
    approval: ApprovalState = ApprovalState()

    @model_validator(mode="after")
    def _scope_matches_key(self) -> "LogicalDocument":
        if self.scope.tenant_id != self.key.tenant_id:
            raise ValueError("document scope tenant must match its key")
        return self

    @property
    def doc_id(self) -> str:
        return self.key.doc_id


class OfficialVersion(BaseModel):
    """One claimed official version (e.g. a compilation). Parser renderings are derivations of it."""

    model_config = ConfigDict(frozen=True)

    doc_id: str
    official_id: str
    compilation_number: Optional[int] = None
    legal_time: LegalTime = LegalTime()

    @property
    def version_id(self) -> str:
        return f"{self.doc_id}/{self.official_id}"


# --- Source spans ---------------------------------------------------------------


class PageBasis(StrEnum):
    PDF_PHYSICAL = "pdf_physical"  # from a parser run over the PDF itself
    FOOTER_TEXT = "footer_text"  # printed label read from page-furniture text


class BoundingBox(BaseModel):
    model_config = ConfigDict(frozen=True)

    physical_page: int = Field(ge=1, description="1-based physical PDF page")
    x0: float
    y0: float
    x1: float
    y1: float
    origin: str = "top-left"
    units: str = "pt"


class SourceSpan(BaseModel):
    """Exact location in one immutable text artifact (see :data:`TEXT_OFFSET_CONVENTION`).

    ``physical_page`` is only set from an actual PDF extraction; Markdown page separators never
    establish it.
    """

    model_config = ConfigDict(frozen=True)

    artifact_id: str
    char_start: int = Field(ge=0)
    char_end: int = Field(ge=0)
    line_start: int = Field(ge=1)
    line_end: int = Field(ge=1)
    physical_page: Optional[int] = Field(default=None, ge=1)
    printed_page_label: Optional[str] = None
    page_label_basis: Optional[PageBasis] = None
    bbox: Optional[BoundingBox] = None

    @model_validator(mode="after")
    def _ordered(self) -> "SourceSpan":
        if self.char_end < self.char_start or self.line_end < self.line_start:
            raise ValueError("span end precedes its start")
        return self

    def validate_against(self, text: str) -> None:
        if self.char_end > len(text):
            raise ValueError(f"span {self.char_start}:{self.char_end} exceeds artifact length {len(text)}")

    def excerpt(self, text: str) -> str:
        self.validate_against(text)
        return text[self.char_start : self.char_end]


# --- Clause keys and readable / point identifiers --------------------------------

_SECTION_TOKEN = re.compile(r"^(\d+)([A-Za-z]{0,3})$")
_CLAUSE_QUERY = re.compile(
    r"^\s*(?:s(?:ection)?s?\.?\s*)?(\d+)([A-Za-z]{0,3})((?:\s*\([0-9A-Za-z]{1,5}\))*)\s*$", re.IGNORECASE
)


def canonical_section_number(token: str) -> str:
    """``65b`` -> ``65B``. Raises for tokens that are not section numbers."""
    match = _SECTION_TOKEN.match(token.strip())
    if not match:
        raise ValueError(f"not a section number: {token!r}")
    return f"{int(match.group(1))}{match.group(2).upper()}"


def parse_clause_query(query: str) -> Optional[str]:
    """Parse ``s 65B``, ``section 65b``, ``65B(5)`` or ``s153(2)(b)`` into a canonical clause key.

    Returns ``None`` when the query is not a clause reference. Never performs prefix matching.
    """
    match = _CLAUSE_QUERY.match(query)
    if not match:
        return None
    key = f"s{int(match.group(1))}{match.group(2).upper()}"
    for i, part in enumerate(re.findall(r"\(([0-9A-Za-z]{1,5})\)", match.group(3))):
        key += f"({part.upper()})" if i == 0 and part[0].isdigit() else f"({part})"
    return key


def provision_display_id(key: DocumentKey, official_id: str, clause_key: str) -> str:
    """Readable citation ID, e.g. ``au:C2020A00119/C2026C00317/s153(2)(b)``."""
    return f"{key.display_id}/{official_id}/{clause_key}"


def build_scoped_id(version_id: str, build_id: str, clause_key: str) -> str:
    """Canonical build-specific ID. Derive point IDs from this, not from display IDs."""
    return f"{version_id}#{build_id}#{clause_key}"


# --- Parsed structure ------------------------------------------------------------


class Region(StrEnum):
    FRONT_MATTER = "front_matter"
    COVER = "cover"
    COMPILATION_NOTES = "compilation_notes"
    CONTENTS = "contents"
    LONG_TITLE = "long_title"
    BODY = "body"
    ENDNOTES = "endnotes"


class BlockKind(StrEnum):
    HEADING = "heading"
    PARAGRAPH = "paragraph"
    HTML_TABLE = "html_table"
    PIPE_TABLE = "pipe_table"
    CODE = "code"
    IMAGE = "image"
    SEPARATOR = "separator"
    PAGE_BREAK = "page_break"
    FRONT_MATTER = "front_matter"


class FurnitureKind(StrEnum):
    RUNNING_HEADER = "running_header"
    PAGE_FOOTER = "page_footer"
    PAGE_BREAK = "page_break"
    LAYOUT_SEPARATOR = "layout_separator"


class Block(BaseModel):
    index: int
    kind: BlockKind
    region: Region
    span: SourceSpan
    level: Optional[int] = None
    furniture: Optional[FurnitureKind] = None


class ProvisionKind(StrEnum):
    CHAPTER = "chapter"
    PART = "part"
    DIVISION = "division"
    SUBDIVISION = "subdivision"
    SCHEDULE = "schedule"
    SECTION = "section"
    SUBSECTION = "subsection"
    PARAGRAPH = "paragraph"
    SUBPARAGRAPH = "subparagraph"
    SUBSUBPARAGRAPH = "subsubparagraph"
    DEFINITION = "definition"
    NOTE = "note"
    PENALTY = "penalty"


class ContentClass(StrEnum):
    BODY_PROVISION = "body_provision"
    DEFINITION = "definition"
    NOTE = "note"
    PENALTY = "penalty"
    SIMPLIFIED_OUTLINE = "simplified_outline"
    COMPILATION_INFORMATION = "compilation_information"
    AMENDMENT_HISTORY = "amendment_history"


class ProvisionNode(BaseModel):
    key: str
    kind: ProvisionKind
    number: Optional[str] = None
    title: Optional[str] = None
    label: Optional[str] = None  # unnumbered heading such as "Fault-based offence"
    content_class: ContentClass = ContentClass.BODY_PROVISION
    parent_key: Optional[str] = None
    children: List[str] = Field(default_factory=list)
    spans: List[SourceSpan] = Field(default_factory=list)
    text: str = ""  # faithful normalized text of this node only (not its children)
    list_connective: Optional[str] = None  # "and" / "or" closing a list item
    table_ids: List[str] = Field(default_factory=list)


class TableStatus(StrEnum):
    RESOLVED = "resolved"
    UNRESOLVED = "unresolved"


class TableCell(BaseModel):
    column_index: int
    text: str
    span: Optional[SourceSpan] = None
    colspan: int = 1


class TableColumn(BaseModel):
    index: int
    header: str
    column_number: Optional[int] = None
    classification: str = "operative"  # or "non_operative_information"


class TableRow(BaseModel):
    key: str
    cells: List[TableCell]

    def cell(self, column_index: int) -> Optional[TableCell]:
        return next((c for c in self.cells if c.column_index == column_index), None)


class TableFragment(BaseModel):
    """Source text that belongs to a table but whose row/column association is unproven."""

    text: str
    span: SourceSpan
    reason: str


class TableRecord(BaseModel):
    table_id: str
    region: Region
    content_class: ContentClass
    section_key: Optional[str] = None
    owner_key: Optional[str] = None
    title: Optional[str] = None
    columns: List[TableColumn] = Field(default_factory=list)
    rows: List[TableRow] = Field(default_factory=list)
    status: TableStatus = TableStatus.RESOLVED
    issues: List[str] = Field(default_factory=list)
    fragments: List[TableFragment] = Field(default_factory=list)
    span: Optional[SourceSpan] = None

    @property
    def evidence_eligible(self) -> bool:
        """Only resolved operative tables may support answers or graph assertions."""
        return self.status is TableStatus.RESOLVED and self.content_class is ContentClass.BODY_PROVISION

    def column_index(self, label: str) -> int:
        """Find a column by header text (``"Column 1"``, ``"Reviewable decision"``), never by position."""
        pattern = re.compile(rf"(?<![0-9A-Za-z]){re.escape(label)}(?![0-9A-Za-z])", re.IGNORECASE)
        matches = [c.index for c in self.columns if pattern.search(c.header)]
        if len(matches) != 1:
            raise KeyError(f"{len(matches)} columns match {label!r} in table {self.table_id}")
        return matches[0]

    def row(self, key: str) -> TableRow:
        matches = [r for r in self.rows if r.key == key]
        if len(matches) != 1:
            raise KeyError(f"{len(matches)} rows have key {key!r} in table {self.table_id}")
        return matches[0]

    def value(self, row_key: str, column_label: str) -> Optional[str]:
        cell = self.row(row_key).cell(self.column_index(column_label))
        return cell.text if cell else None


class ReferenceStatus(StrEnum):
    RESOLVED = "resolved"
    EXTERNAL_UNAVAILABLE = "external_unavailable"
    AMBIGUOUS = "ambiguous"
    EXPLICITLY_REPEALED = "explicitly_repealed"
    UNRESOLVED = "unresolved"


class ReferenceKind(StrEnum):
    SECTION = "section"
    SUBSECTION = "subsection"
    PARAGRAPH = "paragraph"
    TABLE_ITEMS = "table_items"
    EXTERNAL_ACT = "external_act"


class Reference(BaseModel):
    kind: ReferenceKind
    raw_text: str
    source_key: str
    span: Optional[SourceSpan] = None
    targets: List[str] = Field(default_factory=list)
    target_act: Optional[str] = None
    table_items: List[str] = Field(default_factory=list)
    status: ReferenceStatus = ReferenceStatus.UNRESOLVED
    note: Optional[str] = None


class DefinitionEntry(BaseModel):
    term: str
    defined_in: str
    scope_kind: str  # "act", "section", or a structural kind such as "part"
    scope_key: Optional[str] = None
    qualifier: Optional[str] = None  # e.g. "for an audit under Division 4 ..." limits where it applies
    external_act: Optional[str] = None
    text: str
    spans: List[SourceSpan] = Field(default_factory=list)


class RepealEntry(BaseModel):
    """Amendment-history evidence that a provision was repealed. Not its former wording."""

    provision: str
    how: str
    span: SourceSpan


class ParseWarning(BaseModel):
    code: str
    message: str
    span: Optional[SourceSpan] = None
    clause_key: Optional[str] = None


class FactClaim(BaseModel):
    value: Any
    span: SourceSpan


class ParsedLegislation(BaseModel):
    """Canonical structure of one rendering. Every node and cell points back to artifact spans."""

    artifact_id: str
    text_sha256: str
    front_matter: Optional[Dict[str, Any]] = None
    cover_facts: Dict[str, FactClaim] = Field(default_factory=dict)
    blocks: List[Block] = Field(default_factory=list)
    provisions: Dict[str, ProvisionNode] = Field(default_factory=dict)
    order: List[str] = Field(default_factory=list)
    tables: List[TableRecord] = Field(default_factory=list)
    references: List[Reference] = Field(default_factory=list)
    definitions: List[DefinitionEntry] = Field(default_factory=list)
    repeals: List[RepealEntry] = Field(default_factory=list)
    warnings: List[ParseWarning] = Field(default_factory=list)

    def nodes(self, kind: ProvisionKind) -> List[ProvisionNode]:
        return [self.provisions[k] for k in self.order if self.provisions[k].kind is kind]

    def section_numbers(self) -> List[str]:
        return [n.number or "" for n in self.nodes(ProvisionKind.SECTION)]

    def find(self, query: str) -> Optional[ProvisionNode]:
        """Exact clause lookup (``s 65B``, ``65B(5)``); never a prefix match."""
        key = parse_clause_query(query)
        return self.provisions.get(key) if key else None

    def section_of(self, key: str) -> Optional[ProvisionNode]:
        node = self.provisions.get(key)
        while node is not None and node.kind is not ProvisionKind.SECTION:
            node = self.provisions.get(node.parent_key) if node.parent_key else None
        return node

    def ancestry(self, key: str) -> List[ProvisionNode]:
        """Structural ancestors from the outermost level down to (excluding) ``key``."""
        chain: List[ProvisionNode] = []
        node = self.provisions.get(key)
        while node is not None and node.parent_key:
            node = self.provisions[node.parent_key]
            chain.append(node)
        return list(reversed(chain))

    def descendants(self, key: str) -> List[ProvisionNode]:
        out: List[ProvisionNode] = []
        stack = list(reversed(self.provisions[key].children))
        while stack:
            node = self.provisions[stack.pop()]
            out.append(node)
            stack.extend(reversed(node.children))
        return out

    def full_text(self, key: str) -> str:
        parts = [self.provisions[key].text] + [n.text for n in self.descendants(key)]
        return " ".join(p for p in parts if p)

    def tables_for(self, section_key: str) -> List[TableRecord]:
        return [t for t in self.tables if t.section_key == section_key]
