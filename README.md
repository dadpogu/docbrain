# Doc Brain

[Project structure](./docs/project_structure.md)

[Architecture](./docs/rag_architecture.md)

[Deployment Instructions](./docs/rag_deployment.md)

DocBrain is a compliance-focused hybrid RAG system. It aims to turn regulatory documents (legislation, codes, adopted standards, and guidelines) into grounded answers, risk/control analysis, and regulatory change review using three complementary representations:  
- Vector store: Retrieve specific facts, clauses, and exact excerpts through dense/sparse search.  
- Semantic layer: Retrieve hierarchical RAPTOR summaries for document-wide themes and overviews.  
- Knowledge graph: Connect entities and relationships for multi-hop questions and corpus-wide patterns.  

Provenance ties the system together: summaries and graph relationships reference supporting chunks, allowing answers to trace back to source passages rather than rely solely on generated summaries.

External callers, such as the future process application, and ad hoc users query DocBrain through its query API; DocBrain stores no site data. Process documentation (Compliance Agent, Documentation Agent, site-specific policies and procedures) is a separate future application; see [process_pipeline_future](./plans/process_pipeline_future/README.md).

The repository separates document preparation into assets/raw, assets/parsed, and assets/cleaned, each organised by dotted scope code (`GLOBAL`, `GLOBAL.AU`, `GLOBAL.AU.VIC`, `GLOBAL.AU.VIC.AUWOD`). docs/ describes the lifecycle; plans/ holds the implementation plan and coding backlog; src/docbrain/ contains models, routing, summary-tree construction/search, graph extraction, evidence fusion, and document lifecycle handling.

## Development

Install with `uv sync`. Run the offline checks with `uv run pytest`, `uv run ruff check src tests`, `uv run ruff format --check src tests`, and `uv run mypy`. No hosted services are contacted.
