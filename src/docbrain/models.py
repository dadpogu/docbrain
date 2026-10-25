"""
Canonical Data Models & Grounding Schema for Tri-Store Hybrid RAG.
Addresses Gap 1: Grounding & Cross-Representation Linking
Addresses Gap 5: Structured Evidence Bundle Specification
"""

from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field
from enum import Enum
import hashlib
from datetime import datetime


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
