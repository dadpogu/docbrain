# Doc Brain

[Project structure](./docs/project_structure.md)

[Architecture](./docs/rag_architecture.md)

[Deployment Instructions](./docs/rag_deployment.md)

DocBrain is a compliance-focused hybrid RAG system. It aims to turn regulatory documents into grounded answers, risk/control analysis, and operational workflows using three complementary representations:  
- Vector store: Retrieve specific facts, clauses, and exact excerpts through dense/sparse search.  
- Semantic layer: Retrieve hierarchical RAPTOR summaries for document-wide themes and overviews.  
- Knowledge graph: Connect entities and relationships for multi-hop questions and corpus-wide patterns.  

Provenance ties the system together: summaries and graph relationships reference supporting chunks, allowing answers to trace back to source passages rather than rely solely on generated summaries.

The repository separates document preparation into assets/raw, assets/parsed, and assets/cleaned. docs/ describes the lifecycle; src/ contains models, routing, summary-tree construction/search, graph extraction, evidence fusion, and document lifecycle handling.