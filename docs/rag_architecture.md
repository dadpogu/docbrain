# Hybrid RAG Architecture

A unified, tri-focal retrieval architecture designed for high-precision regulatory compliance, risk analysis, and operational workflow generation.

---

## 1. System Vision & The Core Idea

Standard Retrieval-Augmented Generation (RAG) relies on uniform semantic vector search over isolated text chunks. While vector search excels at point-lookup queries, it fails in enterprise regulatory and governance contexts due to:
1. **Holistic / Thematic Blindness:** Inability to synthesize corpus-wide themes (*"What are the recurring compliance risks across all subsidiaries?"*).
2. **Multi-Hop Relational Disconnect:** Inability to traverse non-contiguous entity relationships across disparate documents (*"How does Supplier X connect to Facility Y through Outage Z?"*).
3. **Contextual & Structural Fragmentation:** Loss of document hierarchy, clause numbering, and tabular geometries during naive chunking.

The DocBrain architecture resolves these failure modes by constructing **three synchronized representations**:
- **Vector Store (Point Facts):** Fine-grained semantic chunk retrieval via dense/sparse hybrid embeddings.
- **Semantic Layer (Meso/Macro Summaries):** RAPTOR-style hierarchical tree of summaries for progressive drill-down.
- **Knowledge Graph (Structural / Topological Relationships):** GraphRAG-style entity-relation graph with community clustering and graph algorithms.

A central **Retrieval Broker** classifies query intent, routes to the appropriate representations, fuses candidate evidence via Weighted Reciprocal Rank Fusion (W-RRF), and generates a verified **Evidence Bundle** for downstream Agent synthesis.

```mermaid
graph TD
    classDef primary fill:#2563eb,stroke:#1d4ed8,color:#ffffff;
    classDef storage fill:#059669,stroke:#047857,color:#ffffff;
    classDef broker fill:#d97706,stroke:#b45309,color:#ffffff;
    classDef agent fill:#7c3aed,stroke:#6d28d9,color:#ffffff;

    SRC["Source Documents (PDF, DOCX, HTML)"]:::primary --> PARSE

    subgraph PARSE["1. Parse Stage"]
        PARSER["Document Parser"]:::primary
        PARSER --> MD["Enriched Markdown + Metadata"]:::primary
        PARSER --> JSON["Hierarchical JSON + Metadata"]:::primary
    end

    subgraph EXTRACT["2. Extract Stage"]
        ING_VEC["Chunker & Pre-processor"]
        ING_SEM["Hierarchical Summarizer (RAPTOR)"]
        ING_KG["Entity/Relation Extractor & Resolver"]
    end

    PARSE --> EXTRACT

    subgraph ENCODE["3. Encode Stage"]
        ING_VEC --> VS[("Vector Store: Dense + Sparse Hybrid")]:::storage
        ING_SEM --> SL[("Semantic Layer: Hierarchical Summaries L0-L3")]:::storage
        ING_KG --> GS[("Knowledge Graph: Entities, Relations, Communities")]:::storage
    end

    subgraph RETRIEVE["4. Retrieve Stage"]
        USER["User Query / Agent Prompt"]:::agent --> ROUTER{"Two-Tier Query Router"}:::broker

        ROUTER -->|"Point / Factual"| VS
        ROUTER -->|"Thematic / Overview"| SL
        ROUTER -->|"Relational / Multi-hop"| GS
        ROUTER -->|"Complex / Ambiguous"| ALL["Parallel Dispatch (All Stores)"]:::broker

        ALL --> VS
        ALL --> SL
        ALL --> GS

        VS --> EXP["Cross-Grounding & Expansion"]:::broker
        SL --> EXP
        GS --> EXP

        EXP --> RRF["Hybrid Rank Fusion (W-RRF) & Re-ranker"]:::broker
        RRF --> DEDUP["Context Deduplicator & Compressor"]:::broker
        DEDUP --> BUNDLE["Structured Evidence Bundle"]:::broker
    end

    BUNDLE --> AGENT["Agent / LLM Gateway"]:::agent
    AGENT --> EVAL{"Context Sufficiency Check (CRAG)"}:::agent
    EVAL -->|"Sufficient"| RESP["Final Grounded Response with Citations"]:::agent
    EVAL -->|"Insufficient / Missing"| REWRITE["Query Reformulation Loop"]:::agent
    REWRITE --> ROUTER
```

---

## 2. Documentation Architecture & Lifecycle Stages

Detailed technical specifications, agent guidelines, schemas, and operational workflows are modularized into four dedicated lifecycle documents:

```mermaid
graph LR
    P["Stage 1: PARSE<br/>Layout parsing & normalization"] --> E["Stage 2: EXTRACT<br/>Entity & 4-tier knowledge modeling"]
    E --> C["Stage 3: ENCODE<br/>Chunking, RAPTOR & storage"]
    C --> R["Stage 4: RETRIEVE<br/>Routing, fusion & agentic CRAG"]
```

| Lifecycle Stage | Detailed Documentation Guide | Key Responsibilities | Reference Implementation |
| :--- | :--- | :--- | :--- |
| **Stage 1: Parse** | [rag_parse.md](./rag_parse.md) | Document structure parsing, dual Markdown/JSON AST, list/table unrolling, pronoun de-anonymization, sentence atomization, and RFC 2119 modality tagging. | [`models.py`](../src/models.py) |
| **Stage 2: Extract** | [rag_extract.md](./rag_extract.md) | 4-tier knowledge architecture (Document $\to$ Concept $\to$ Risk/Control $\to$ Workflow), schema-guided entity extraction, Leiden community detection, and audit-safe graph evolution. | [`graph_engine.py`](../src/graph_engine.py) |
| **Stage 3: Encode** | [rag_encode.md](./rag_encode.md) | Layout-aware semantic chunking, dual-text indexing (normalized embeddings vs. verbatim payloads), recursive RAPTOR tree construction, storage collection DDLs, and differential ingestion. | [`semantic_tree.py`](../src/semantic_tree.py), [`lifecycle.py`](../src/lifecycle.py) |
| **Stage 4: Retrieve** | [rag_retrieve.md](./rag_retrieve.md) | Two-tier adaptive routing, multi-store search execution, Graph-to-Vector Grounding Expansion, Weighted RRF, cross-encoder re-ranking, and Corrective RAG (CRAG). | [`router.py`](../src/router.py), [`broker_fusion.py`](../src/broker_fusion.py) |

---

## 3. Canonical Data Model & Unified Grounding

To unify the three stores and eliminate isolated data silos, every entity, summary node, and text chunk references a deterministic canonical identifier schema implemented in [`models.py`](../src/models.py):

```
Canonical Identifier Schema:
  Document:    doc_id    = "doc_{sha256(source_uri)[:16]}"
  Chunk:       chunk_id  = "{doc_id}#c{chunk_index:04d}"
  Tree Node:   node_id   = "{doc_id}#L{level}_c{cluster_id:02d}"
  KG Entity:   entity_id = "ent_{slug(normalized_name)}"
  KG Relation: rel_id    = "rel_{source_id}_{type}_{target_id}"
```

### 3.1 Provenance Linkage Across Stores
- **Vector Store (Chunks):** Payload stores `{doc_id, chunk_id, section_path, page_numbers, entity_ids, content_hash}`.
- **Semantic Layer (Tree Nodes):** Payload stores `{node_id, doc_id, level, parent_id, children_ids, leaf_chunk_ids}`.
- **Knowledge Graph (Nodes & Edges):** Properties store `{provenance_chunks: [chunk_id], doc_ids: [doc_id], confidence: float}`.

### 3.2 Bidirectional Resolution Flow
```mermaid
graph LR
    VS["Vector Store Chunk<br/>(entity_ids: [ent_1, ent_2])"]
    KG["Knowledge Graph Subgraph<br/>(provenance_chunks: [chunk_id])"]
    
    VS -->|"1. Traverse connected entities"| KG
    KG -->|"2. Direct point-fetch supporting text"| VS
```

1. **Vector $\to$ Graph:** Chunks store extracted `entity_ids`. When a chunk is retrieved, downstream agents can immediately inspect its local subgraph without running a separate graph search.
2. **Graph $\to$ Vector (Grounding Expansion):** When a graph traversal identifies relevant paths or community summaries, the broker reads `provenance_chunks` and fetches the underlying text chunks directly by primary key, bypassing redundant vector index lookups.

---

## 4. End-to-End Architectural Workflows

### 4.1 Ingestion & Synchronization Flow
Ingestion coordinates document parsing, parallel multi-store extraction, and differential updates across the storage layers:

```mermaid
sequenceDiagram
    autonumber
    actor Trigger as Ingestion Trigger
    participant Coord as Ingestion Coordinator
    participant Parse as Document Parser (Stage 1)
    participant Extract as Knowledge Extractor (Stage 2)
    participant VS as Vector Store & RAPTOR (Stage 3)
    participant KG as Knowledge Graph (Stage 3)

    Trigger->>Coord: Ingest Document (PDF/DOCX/HTML)
    Coord->>Parse: Parse Layout & Structure
    Parse-->>Coord: Enriched Markdown + Hierarchical JSON AST
    
    par Parallel Extraction & Storage Encoding
        Coord->>Extract: Extract Entities, Relations & Requirements
        Extract-->>Coord: Typed Tuples & Provenance Links
        Coord->>KG: Merge Nodes, Edges, Communities
    and Vector Chunking & Embeddings
        Coord->>VS: Upsert Chunks (`rag_chunks`) with Hybrid Vectors
    and RAPTOR Tree Summarization
        Coord->>VS: Build & Upsert Summary Tree (`rag_semantic_layer`)
    end
    Coord-->>Trigger: Ingestion Completed (All Stores Synchronized)
```
*Detailed breakdown in [rag_parse.md](./rag_parse.md), [rag_extract.md](./rag_extract.md), and [rag_encode.md](./rag_encode.md).*

---

### 4.2 Query Routing & Retrieval Flow
The retrieval pipeline dispatches queries based on intent, fuses multi-store results, and synthesizes answers with inline citations:

```mermaid
sequenceDiagram
    autonumber
    actor Client as User / Agent
    participant Broker as Retrieval Broker
    participant Router as Intent Classifier
    participant Stores as Vector / RAPTOR / Graph Stores
    participant Rerank as Cross-Encoder Reranker
    participant LLM as LLM Gateway

    Client->>Broker: Query Request
    Broker->>Router: Classify Intent (Heuristic / LLM)
    Router-->>Broker: Intent Target (e.g., COMPLEX_HYBRID)

    Broker->>Stores: Concurrent Multi-Store Retrieval
    Stores-->>Broker: Candidate Passages, Graph Paths & Tree Nodes

    Broker->>Broker: Graph-to-Vector Grounding Expansion
    Broker->>Broker: Weighted Reciprocal Rank Fusion (W-RRF)
    Broker->>Rerank: Batch Re-ranking (Top 25 Candidates)
    Rerank-->>Broker: Calibrated Scores & Deduplication
    Broker-->>Client: Structured Evidence Bundle (Citations [EV-01], [EV-02])

    Client->>LLM: Stream Grounded Response with Citations
    LLM-->>Client: Streaming Response
```
*Detailed breakdown in [rag_retrieve.md](./rag_retrieve.md).*

---

## 5. Quality Assurance & Continuous Evaluation

To quantitatively validate retrieval performance and prevent compliance hallucination, continuous evaluation measures five core metrics:

```mermaid
graph TD
    classDef metric fill:#1e3a8a,stroke:#3b82f6,color:#fff;

    M1["1. Context Relevance<br/>(Signal-to-noise ratio in retrieved context)"]:::metric
    M2["2. Groundedness / Faithfulness<br/>(100% of claims map to citation IDs)"]:::metric
    M3["3. Answer Relevance<br/>(Direct semantic alignment with user prompt)"]:::metric
    M4["4. Multi-Hop Path Precision<br/>(Accuracy of relational graph traversals)"]:::metric
    M5["5. RAPTOR Tree Utilization<br/>(Ratio of thematic queries resolving via macro nodes)"]:::metric
```

- **Context Relevance:** Ratio of retrieved chunks directly contributing to the answer versus irrelevant noise.
- **Groundedness / Faithfulness:** Strict verification that 100% of claims in the generated response map to valid `citation_id` entries in the Evidence Bundle.
- **Answer Relevance:** Semantic alignment between the generated response and the user's original query.
- **Multi-Hop Traversal Accuracy:** Precision of relational paths traversed in the Knowledge Graph against gold standard compliance benchmarks.
- **Hierarchical Tree Utilization:** Frequency with which macro thematic queries resolve via high-level summary nodes rather than brute-force chunk scanning.