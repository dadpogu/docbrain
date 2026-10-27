# DocBrain implementation plan

Status: proposed implementation baseline, 2026-10-25. No production deployment or service provisioning is implied by this document.

**Coding backlog:** [source-driven tasks](./coding_tasks.md) break these phases into dependency-ordered increments using the supplied *Recycling and Waste Reduction Act 2020*. They include twenty legal Q&A scenarios, target modules, and completion gates. Task checkboxes record implementation progress; this plan remains the architectural baseline.

Process application material (Compliance Agent, Documentation Agent, site/process/template sources, document packages) moved to [process_pipeline_future](./process_pipeline_future/README.md).

## 1. Deliver grounded answers before autonomous actions

Build a Python application that ingests regulatory documents (legislation, codes, adopted standards, and guidelines), answers questions with inspectable source evidence, and explains changes. External callers, such as the future process application, and ad hoc users query DocBrain through its query API; DocBrain stores no site data. The agents, prompts, tools, and workflows live in this repository; hosted providers supply parsing, models, vector storage, and graph storage.

The first usable release is **version-aware, cited document Q&A**. Graph extraction and hierarchical summaries extend that baseline only when evaluation shows a benefit. A generated control is a proposal, not a legal determination or an instruction to change a production system.

This plan governs implementation order, contracts, and technology choices. The stage documents describe domain intent and contain earlier illustrative designs; where they differ, this plan takes precedence. Update each stage specification alongside its implementation. Existing `src/` modules are prototypes, not proven production components.

### Working assumptions

- “Dockling” means **Docling**; “Lanchain” means **LangChain**. Use **LangGraph** for explicit, checkpointed workflows within the LangChain ecosystem.
- LiteLLM, a parser service, Qdrant, and Memgraph endpoints are supplied externally. DocBrain owns clients and compatibility checks, not those services' deployment.
- English-language Australian legislation in `assets/parsed/GLOBAL.AU` is the initial corpus. Other jurisdictions and languages are later evaluation tracks, not assumptions about current accuracy. Standards are included only when the organisation has adopted them (for example ISO 9001, ISO 14001, ISO 45001).
- Assets live under `assets/{raw,parsed,cleaned}/<scope>/` with dotted scope codes such as `GLOBAL`, `GLOBAL.AU`, `GLOBAL.AU.VIC`, and `GLOBAL.AU.VIC.AUWOD` (Wodonga). A location scope inherits every ancestor scope by dotted segment. Scope is a necessary filter, not proof of applicability; the regulatory pipeline defines applicability conditions.
- Begin with a single organization, but carry tenant, corpus, and access-scope identifiers from the first release. Do not expose a shared deployment until authorization tests pass.
- Propose **PostgreSQL** for document/version manifests, durable jobs, approvals, audit records, and LangGraph checkpoints. This is an additional dependency requiring an available endpoint before shared deployment. SQLite plus local files is acceptable for a single-process development mode, not a production failover.
- Preserve originals and derived artifacts in an existing object store, or a local artifact directory during development. Do not put entire PDFs or parser output into workflow checkpoints.
- No frontend, autonomous external actions, general web crawling, or self-hosted database platform is required for the first release. Provide a CLI and API first.

## 2. Technology choices and replacement boundaries

| Responsibility | Initial choice | Contract and replacement rule |
| --- | --- | --- |
| Models | Hosted LiteLLM gateway | Role aliases for routing, extraction, summarization, answering, embeddings, and optional reranking. Record resolved model/version and usage. Provider credentials remain at the gateway. |
| Agent components | LangChain | Typed tools, structured model output, prompt composition, model integration. Keep domain objects independent of LangChain `Document` and message types. |
| Workflow execution | LangGraph in this repository | Explicit states, bounded loops, checkpoints, cancellation, human interrupts. No hosted LangGraph platform requirement. |
| Parser | Supplied LiteParse export as first comparison candidate; Docling challenger | Both adapters target DocBrain's `ParsedDocument`, preserving native output separately. Select a production parser from PDF-reviewed measurements; no winner yet. |
| Vector retrieval | Hosted Qdrant | Dense plus sparse retrieval, payload filters, ID fetch, batch writes, pagination. Keep SDK result objects inside the adapter. |
| Graph retrieval | Hosted Memgraph | Parameterized, bounded Cypher templates and provenance-aware writes. Bolt compatibility does not imply Neo4j APOC/GDS compatibility. |
| Durable application state | PostgreSQL | Transactions govern job claims, manifest publication, approvals, and audit events. LangGraph uses its supported Postgres checkpointer in a separate namespace. |
| Artifact storage | Existing object storage; local development fallback | Immutable bytes, checksums, versioned keys, retention policy, authorized source access. |
| Application interfaces | FastAPI and a small CLI | Shared application functions, asynchronous ingestion jobs, typed errors, request IDs. |
| Engineering baseline | `pyproject.toml`, `uv`, Pydantic, pytest, Ruff, type checking | Pin a tested Python/dependency combination and lockfile in Phase 0; avoid hard-coded historical provider model names. |
| Telemetry | Structured logs and OpenTelemetry | Optional Langfuse or LangSmith export after data-retention review; neither is a runtime requirement. |

Implement small Python protocols only at actual external boundaries: parser, model gateway, vector index, graph store, and artifact storage. Do not build a generic database framework or implement multiple production adapters before one works. Switching a store requires a data migration/reindex and contract-test run, not merely changing an environment variable.

### Model integration

Use a maintained LangChain LiteLLM integration, or the gateway's standard OpenAI-compatible API through `langchain-openai` when only standard fields are required. Phase 0 must test the exact hosted endpoint with structured output, tool calls, streaming, embeddings, and usage reporting. Do not assume provider-specific reasoning fields survive an OpenAI-compatible wrapper. Reranking is an optional separately probed capability, not a property of every model gateway.

Do not silently change embedding models on an existing index. Dense model identity, dimensions, normalization, sparse tokenizer/model, and metric form a versioned embedding profile. A changed profile requires a parallel collection and an evaluated cutover. Generation-model fallback is permitted only to models that satisfy the same output and data-handling contract.

Start sparse retrieval with a pinned BM25 implementation, using FastEmbed/Qdrant support if the compatibility probe confirms it. Generate document and query weights under the same profile, configure corpus IDF handling explicitly, and test that IDF is not applied twice. Keep exact legislation/clause keys in indexed payload fields so punctuation-sensitive identifiers do not depend entirely on tokenization. SPLADE or other learned sparse models are later benchmark candidates, not extra MVP dependencies.

### Parser decision experiment

Start offline with the supplied [LiteParse Markdown export](../assets/parsed/Sample/C2020A00119_Liteparse.md), the [earlier structured Markdown](../assets/parsed/Sample/C2020A00119_LawCodex.md) (byte-identical to `assets/parsed/GLOBAL.AU/C2020A00119-recycling-and-waste-reduction-act-2020.md`), and reviewed spans of their raw Recycling Act PDF. These are two candidate renderings of compilation `C2026C00317`, not two legal versions. Record the user's LiteParse attribution, but leave its engine version, options, timing, and native-coordinate availability unknown: the export does not establish them. Neither Markdown is ground truth.

The supplied LiteParse export retains page furniture and contents, has no YAML metadata, uses different heading depths, and places some subsection boundaries inline. Section 151's four-page table has detached person/decision columns and incomplete pipe-table rows; section 2 also interleaves table columns with surrounding prose. Preserve these defects as regression inputs, not hand-repaired originals. Recover structure only from traceable source evidence; ambiguous table relationships must remain flagged and unavailable for factual synthesis until re-extraction or review resolves them. The earlier Markdown's structured tables are comparison candidates, not permission to silently transplant cells.

Then benchmark reproducible runs of available LiteParse and Docling services against the same source hashes and reviewed expectations. Measure clause/reading-order preservation, table cell associations, source-span fidelity, OCR errors in numbers and negations, latency, and cost per page. Record engine/wrapper versions, settings, and native responses separately from Markdown export steps. An offline artifact comparison cannot supply runtime or cost measurements. Add native-text PDFs, scanned pages, nested clauses, multi-page tables, footnotes, and DOCX/HTML samples as fixtures become available.

Docling's document model makes it a useful hierarchy/table/provenance challenger, not an already measured improvement. LiteParse is not LlamaParse. Capability depends on the installed version and service wrapper; do not assume identical schemas, OCR engines, or supported formats. Implement the winning adapter first; add fallback routing only for a measured failure class. Correct legal qualifiers and table associations are hard gates: throughput cannot compensate for a wrong person/decision pairing. The human approval step between parsed and cleaned Markdown is paused: the owner will supply outputs from several parsers, and if one is good enough the manual correction step is removed.

The Markdown corpus can bootstrap Q&A without waiting for raw-file parsing. Mark provenance as imported Markdown, cite immutable text spans and sections, and never invent PDF coordinates from separator counts or a global page offset. Associate metadata-less imports through explicit source manifests and reconciliation, not filenames alone. Preserve missing image references as warnings; do not fetch arbitrary assets. Additional fixtures are still needed for scanned and non-PDF formats. Detailed observed failures and acceptance checks live in the [coding backlog](./coding_tasks.md).

## 3. Runtime ownership

```diagram
┌──────────────────────┐       ┌──────────────────────────┐
│ CLI / authenticated  │──────▶│ DocBrain API             │
│ API caller           │       │ Query + ingestion jobs   │
└──────────────────────┘       └────────────┬─────────────┘
                                           │
                 ┌─────────────────────────┼──────────────────┐
                 ▼                         ▼                  ▼
       ┌──────────────────┐     ┌──────────────────┐  ┌──────────────┐
       │ LangGraph query  │     │ Durable worker   │  │ PostgreSQL   │
       │ and review flows │     │ ingestion flow   │  │ + artifacts  │
       └────────┬─────────┘     └────────┬─────────┘  └──────────────┘
                │                        │
                └───────────┬────────────┘
                            ▼
       ┌──────────────────────────────────────────────────────┐
       │ External adapters: LiteLLM / Parser / Qdrant / Graph │
       └──────────────────────────────────────────────────────┘
```

The API and worker share one package and domain contracts. CPU-heavy local parsing runs outside the API event loop. Initially use a Postgres-backed job table with leases, heartbeats, retries, and bounded worker concurrency; do not introduce Redis/Celery merely to start a background function. LangGraph checkpoints preserve workflow state but do not replace job dispatch, scheduling, or idempotency.

## 4. Contracts that must precede indexing

### Identity, provenance, and legal time

| Object | Required identity and metadata |
| --- | --- |
| Document | Stable tenant-scoped `doc_id`, authority/source key, source URI aliases, title, jurisdiction, language, license/access scope. Prefer an official legislation identifier over a mutable download URL. |
| Source version | Immutable `version_id`, source checksum, official revision/compilation identifier where known, effective-from/to, observed-at, and source artifact reference. Unknown effective dates remain unknown. |
| Parse artifact | Version ID, parser/profile version, raw parser output reference, normalized block tree, parse warnings, and provenance quality. |
| Chunk | Immutable `chunk_id` within a versioned build, source block/span references, clause key, section path, verbatim text, optional normalized retrieval text, content hash, scope. |
| Index build | `build_id`, source version, parser/chunker/prompt/schema/embedding fingerprints, stage status, expected artifact counts, and dependency IDs. |
| Entity/requirement | Tenant-scoped typed identity; versioned assertions with supporting chunks, extraction method, review state, conditions, exceptions, units, and effective dates. Names/slugs are aliases, not uniqueness guarantees. |
| Summary/community | Scope, build/snapshot dependencies, source chunk IDs, level/type, content, and generation profile. Cross-document summaries have corpus identity, not a fabricated document ID. |
| Evidence bundle | Query, authorized scope, selected manifest revision, as-of policy, intent, evidence items, supporting source spans, retrieval diagnostics, partial-result reasons, and token usage. |
| Answer | Text, claim-to-evidence references, unsupported/missing facets, warnings, status (`answered`, `partial`, `insufficient_evidence`), and run ID. |

Use deterministic UUIDs derived from canonical domain IDs for Qdrant point IDs; Qdrant accepts UUIDs or unsigned integers, not arbitrary strings such as `doc_x#c0001`. Keep the readable domain ID in payloads. Versioned IDs prevent an updated passage from changing the meaning of an old citation.

Define span coordinates explicitly: page index convention, bounding-box origin/units, and character offsets into a named immutable text artifact. “Verbatim” means extracted source text, not guaranteed perfect OCR; OCR/cleanup provenance remains visible. Manual cleanup creates a derived revision with author, reason, original reference, and diff; it never overwrites original evidence.

Separate legal effective time from system observation/publication time. Default to the latest approved available version and disclose its date; an as-of question selects an explicit effective date. Missing or conflicting dates must produce a warning rather than an assertion that the corpus represents current law.

Classify each regulatory source as law, permit conditions, standards, or guidance. Record tenant and location scope, source approval state, document owner, revision, and dependency provenance on chunks, assertions, summaries, and evidence bundles. A federal Act matching the topic does not establish that a particular site or activity is subject to it; applicable state law, permits, rules, and exemptions may be missing.

### Extraction is not policy invention

Keep source statements, normalized interpretations, inferred risks, and proposed controls as distinct objects. Do not add a `MUST`, numeric threshold, actor, exception, or technology requirement that the source does not state. Preserve uncertainty and unresolved references. RFC 2119 labels are useful normalization tags, not a substitute for legal interpretation.

Retain the four-tier model: **Clause → Concept/Requirement → Risk/Control → Workflow/TaskStep**. Procedures depend on approved requirements/controls rather than raw clause numbering, but may retain read-only source provenance for audit. Reject unsupported node/relationship types instead of converting them into unrelated defaults. Human review resolves ambiguous entity merges and material regulatory interpretations.

### Visibility without a distributed transaction

1. Register immutable source/version and acquire an idempotent job lease. Job key includes tenant, source version, and pipeline fingerprint.
2. Parse, chunk, and write a new staging build. Persist stage outputs before moving on. Retried writes use the same IDs.
3. Build the representations required by the release profile: chunks for MVP; chunks, graph, and summaries for the full profile. Optional unavailable enrichments are explicitly marked absent, never presented as complete.
4. Validate counts, provenance resolution, scope, and required-stage completion. Keep the previous published manifest available on failure.
5. Publish a new immutable corpus manifest in one Postgres transaction using compare-and-swap against its parent revision. The manifest selects document versions/builds and compatible derived artifacts. Concurrent publishers reconcile and retry, rather than overwrite each other.
6. Each query pins one authorized manifest revision. Every search, graph hop, ID fetch, and summary expansion filters to the selected builds and scope. Staging writes cannot be discovered through a side channel. Small-corpus build-ID filters are the initial implementation; benchmark their scaling before adding generation-specific indexes.
7. Reconcile interrupted builds and clean unreferenced staging artifacts after a retention interval. Deletion first tombstones the document in the registry, invalidates affected derived artifacts, and schedules physical cleanup. Enforce revocation again at source fetch/answer delivery; a pinned historical snapshot never overrides current authorization or deletion policy.

This provides application-level publication consistency, not atomic commits across Qdrant and Memgraph. Persist enough immutable evidence to reproduce retained answers, subject to retention and erasure requirements. Ordinary supersession retains history; authorized erasure follows an explicit policy covering artifacts, indexes, checkpoints, caches, and audit metadata.

## 5. Workflows to implement in this repository

### Ingestion graph

`register → parse/import → validate structure → chunk → embed/index → enrich → validate build → publish`

After chunk IDs exist, graph extraction and document summaries may run concurrently. Uncertain extraction creates review items; it must not block access to valid source text unless the source itself is quarantined. Every node records attempts, input fingerprint, output references, duration, and cost. Retried/continued execution must not duplicate relationships, approvals, or external effects.

### Question-answering graph

`authorize/pin snapshot → interpret query → retrieve → ground/fuse/rerank → assess coverage → synthesize → verify → return`

- Begin with vector retrieval and an exact clause/identifier path. Later route factual, thematic, relational, global, or mixed requests to the appropriate stores. Multiple intents must not be hidden by first-match regex precedence.
- Retrieve dense and sparse candidates with the same filters. Fuse by canonical evidence identity; normalize provider results before cross-store fusion. RRF scores are rankings, not probabilities.
- Use parameterized graph templates with bounded depth, fan-out, result count, and timeout. No unrestricted text-to-Cypher tool. Resolve edge evidence as well as node evidence back to raw chunks.
- Summary and graph results expand to supporting passages before legal claims are generated. Preserve source diversity and exceptions during deduplication; count tokens with the selected model's tokenizer or a conservative documented fallback.
- Allow at most two corrective retrieval rounds and one answer-repair round initially, within a total deadline/token/cost budget. Stop on no new evidence. Return a partial answer or abstention when the budget is exhausted.
- Verify citation existence, version/scope, quote spans, and numeric/modality consistency deterministically where possible. Separately assess whether the cited material actually supports each claim. An LLM judge and a valid citation ID are not proof of legal correctness.
- Stream progress events first. Do not stream unchecked answer text as a verified final answer; release the validated answer after verification in the first release.
- No automatic web-search fallback. A later opt-in authority-only connector must ingest external evidence with its own provenance, trust label, and legal time metadata.

### Regulatory change and control workflow

`compare versions → classify delta → trace dependencies → propose impact assessment → human review → record approved revision`

Editorial changes, renumbering, and semantic changes are separate classes. A numeric change from 30 to 15 days, a new exception, or `SHOULD` becoming `MUST` must trigger review. Generate an evidence-backed change dossier showing both source spans and affected controls/procedures. Conflicting obligations are surfaced, not silently reconciled by model preference.

LangGraph interrupts pause approval steps; durable checkpoints permit resumption. The approval API authenticates reviewer role, verifies the proposal version/hash, records the decision, and rejects stale or repeated decisions. Side effects before an interrupt must be idempotent because a node may restart on resume. Approval changes DocBrain's records only; execution in external business systems is a later, separately authorized integration.

Tools exposed to agents are narrow: `search_evidence`, `fetch_source_span`, `trace_requirement`, `compare_versions`, and `propose_control`. Approval is an authenticated application operation, not a model tool. Tool inputs do not grant access: tenant and permissions come from trusted request context. Database credentials, unrestricted query tools, and arbitrary filesystem writes are never given to the model.

## 6. Delivery phases and acceptance gates

Implement in this order. Each phase produces a usable, testable increment; do not start advanced retrieval merely because a prototype file exists.

### Phase 0 — Reproducible foundation and service compatibility

**Build:** package configuration, lockfile, settings validation, CLI skeleton, test/lint/type-check commands, and narrow service interfaces. Preserve current module names initially; characterize reusable algorithms before changing them. Fix import/type errors such as the missing `Any` import in `router.py` as part of implementation, not this documentation change.

Add an explicit `doctor` command to report endpoint/version/capability compatibility. It performs read-only checks by default; write probes require a disposable test namespace. Check LiteLLM structured output/embedding profiles, parser schema, Qdrant named dense/sparse vectors and filters, Memgraph transaction/constraint syntax and installed procedures, and Postgres/checkpointer compatibility. Never run collection creation or graph DDL automatically on application startup.

**Gate:** package imports and offline checks pass; a recorded compatibility matrix names exact client/service versions and unsupported capabilities; contract probes pass against disposable real services. Missing hosted access is reported, not replaced with fake production success.

### Phase 1 — Source registry, provenance, and durable ingestion

**Build:** canonical contracts, SQL migrations, artifact storage, Markdown import, first parser adapter, clause-aware chunking, durable job claims/recovery, and source-inspection CLI. Start the parser comparison with the supplied raw Recycling Act and add fixtures for missing format/OCR cases; verify redistribution rights before committing samples.

Use the seven supplied Markdown files in `assets/parsed/GLOBAL.AU`, one per Act, for the first ingestion dataset; evaluate the Recycling Act's two candidate renderings in `assets/parsed/Sample` in isolated builds, not as duplicate corroborating evidence. Reconcile its supplied JSON with the earlier Markdown front matter, LiteParse cover text, explicit artifact associations, and PDF identity; do not invent sidecars for the others. Capture title, authority identifiers, jurisdiction, provenance quality, and unknown metadata. Preserve cross-references and definitions; split oversized tables with repeated headers and source-cell links. In particular, preserve section 151's 28 reviewable-decision items and section 153's review qualifications together in retrievable evidence. A candidate with unresolved table associations cannot pass the full-document quality gate; a deliberately partial build must disclose and exclude the affected evidence.

**Gate:** the same artifacts/version/profile ingested twice yield one logical build; changed bytes create a new artifact/derivation, not automatically a new official legal version; malformed/encrypted/oversized documents produce actionable errors; worker interruption resumes safely. Table conditions, negation, clause numbers, and available source coordinates survive normalization.

### Phase 2 — Cited Q&A MVP

**Build:** Qdrant adapter, embedding batches/cache, dense+sparse search, exact clause lookup, manifest publication, evidence fusion, optional reranker, LangGraph Q&A, and API/CLI access to answers and source spans. Make retention, tombstoning, pagination, and tenant/scope checks work before adding other stores.

**Gate:** ingest the corpus and answer held-out factual/exception questions with resolvable citations; abstain on absent facts; handle ambiguous versions explicitly; restart jobs without duplicate visible data. One hundred percent of emitted citation references resolve to authorized source versions. Simulated Qdrant/gateway failures yield documented errors or partial results, not fabricated answers.

**Deliverable:** the first usable release. Record baseline quality, latency, token usage, and cost before optimizing.

### Phase 3 — Memgraph-backed regulatory relationships

**Build:** typed extraction and resolution, evidence-backed requirements/relations, Memgraph migrations and adapter, bounded retrieval templates, graph-to-chunk grounding, review queue, and graph participation in manifest validation. Replace Neo4j-specific APOC/GDS assumptions; the `neo4j` Python driver may still be used over Bolt after compatibility tests.

**Gate:** a curated multi-hop case finds a dependency across documents with supporting evidence on every asserted edge; similar entity names are not merged solely by slug; retries do not inflate relationship weights. Unauthorized or unpublished edge evidence cannot bridge an otherwise permitted path. Vector-only availability is disclosed if graph functionality is disabled.

### Phase 4 — Hierarchical and corpus-wide retrieval

**Build:** document section summaries first, then evaluated RAPTOR clustering, then cross-document summaries and community reports. Store child and parent links consistently; ground every summary to immutable leaves. Add explicit empty/single-chunk behavior and do not assume every document has three levels.

Run Memgraph MAGE Leiden only if the installed service exposes the required scoped procedure. Otherwise export an authorized, size-bounded snapshot to an offline `igraph`/`leidenalg` job, or defer community retrieval. Persist membership and algorithm/profile identity; do not treat nondeterministic community labels as stable business IDs. No Neo4j GDS dependency.

Build global summaries separately for compatible access scopes; a private document must not influence a public summary. Document updates invalidate every dependent summary/community report before publication, even when unchanged chunk embeddings can be reused.

**Gate:** ablation evaluation compares vector-only, vector+graph, and full retrieval on held-out questions. Added paths improve their target query classes without degrading citation/authorization guarantees or exceeding agreed budgets. Ship optional advanced paths disabled if they fail this gate.

### Phase 5 — Regulatory change impact and review

**Build:** version diffing, obligation comparison, dependency impact traversal, approval/rejection/resume endpoints, and append-only decision history. Add reviewer-readable evidence exports; no UI framework is needed until an actual review workflow requires it.

**Gate:** a changed law identifies the correct downstream requirements and controls; editorial changes do not silently alter approved procedures. Reviewed proposals resume after process restart. Unauthorized, stale, and replayed approval requests are rejected. Generated suggestions remain visibly distinct from extracted law.

### Phase 6 — Shared-service release hardening

**Build:** authenticated identity integration, permission-change/erasure propagation, load/backpressure controls, backups and restore drills, cancellation, bounded retries, dead-job recovery, telemetry dashboards, migration/cutover runbooks, and container images for the application only.

**Gate:** fault injection between each ingestion stage cannot expose a mixed build; restore reproduces manifests and citation resolution; permission revocation blocks new delivery; production-shaped concurrency stays within measured budgets. A human approves shared schema migrations and the deployment after staging checks.

Phases 3 and 4 can be implemented independently after Phase 2 if their schema/manifest contracts are frozen. Phase 5 depends on Phase 3; Phase 6 hardening begins early but gates shared release. Estimate calendar effort after Phase 0 establishes service access, parser quality, and corpus volume.

## 7. Proposed API and operator surface

These are planned contracts, not existing routes or executable commands.

| Surface | Behavior |
| --- | --- |
| `POST /v1/ingestions` | Accept an approved artifact/source reference and idempotency key; return `202` with job ID. Upload limits and content validation apply before parsing. |
| `GET /v1/jobs/{id}` | Authorized stage/status, warnings, attempts, and progress; no credentials or unrestricted artifact paths. |
| `POST /v1/jobs/{id}/cancel` | Cooperative cancellation; never publish a cancelled staging build. |
| `POST /v1/retrieval/query` | Return typed evidence without answer generation; useful to applications and evaluation. |
| `POST /v1/answers` | Return a verified/partial/insufficient answer with evidence, warnings, and run ID. Optional progress stream. |
| `GET /v1/sources/{chunk_id}` | Authorize and resolve the exact source version/span; return an excerpt or short-lived artifact access. |
| `POST /v1/change-assessments` | Queue comparison of two authorized versions and create a reviewable impact proposal. |
| `POST /v1/reviews/{id}/decision` | Authorized approve/reject decision, expected proposal revision, audit event, workflow resume. |
| `DELETE /v1/documents/{id}` | Privileged tombstone/retention workflow; explicit erasure scope, async physical cleanup, auditable status. |
| `/health/live`, `/health/ready` | Process liveness versus required dependency readiness. Missing optional graph/reranker capability is reported separately. |

Query requests specify corpus, optional version/as-of date, and bounded output budget; tenant identity comes from authentication. Server policy caps caller-supplied limits. Error responses distinguish invalid input, forbidden scope, unsupported capability, insufficient evidence, transient dependency failure, and exhausted budget. Logs use request/run/job IDs consistently.

Planned CLI verbs: `doctor`, `ingest`, `job`, `query`, `source`, `evaluate`, `review`, and explicit admin-only `migrate`/`reconcile`. Share implementation with API handlers; avoid a second retrieval pipeline.

## 8. Evaluation and release criteria

Create a small, human-reviewed corpus benchmark before tuning prompts. Start with about 60 questions split across exact clauses, exceptions/negations, numeric thresholds, cross-references, thematic coverage, multi-hop relationships, version changes, and unanswerable requests. Tag which phases can answer each class; keep development and held-out subsets separate. Gold answers specify source spans, not model-generated answer strings.

Track retrieval recall at k, ranking quality, claim support, citation resolution, abstention accuracy, extraction precision/recall, legal-time correctness, p50/p95 latency, and cost per document/query. A valid citation alone is not faithfulness. Human reviewers adjudicate a sample of model-judge results, especially numbers, exceptions, and conflicting legislation.

Provisional MVP targets for the supported factual subset: recall@10 at least 90%, human-reviewed claim support at least 95%, and correct abstention on at least 90% of explicitly unanswerable fixtures. These are release hypotheses to ratify with the benchmark, not current measured performance or promises about legal correctness. Hard gates are zero unauthorized disclosures in the security suite, zero dangling emitted citations, and no unsupported numeric/modality change in the critical regression fixtures.

Start latency budgets at p95 under 3 seconds for evidence-only retrieval and under 20 seconds for a normal verified answer, measured at a declared corpus size, concurrency, region, and model profile. Corrective multi-round requests get a separate bounded budget. Replace these provisional budgets with Phase 2 measurements and owner-approved SLOs; do not promise a 160 ms broker containing remote model calls. Set cost ceilings from measured tokens/pages and actual hosted pricing rather than invented dollar estimates.

Required checks include:

- Unit/property tests for identity determinism, span mapping, fusion, budgets, and legal-version selection; use asymmetric ranks and boundary dates.
- Adapter contract tests against disposable real services for filters, transactions, paging beyond one page, and actual SDK response shapes.
- End-to-end ingest → publish → query → cite → supersede → query-as-of → tombstone tests.
- Adversarial cases: prompt injection in source text, fabricated citations, same name across tenants/types, forbidden intermediate graph nodes, mixed-access summaries, SSRF paths, and revoked source access.
- Crash/retry scenarios at write and publication boundaries, duplicate jobs, competing updates, parser timeout, model 429/5xx, dimension mismatch, graph outage, and empty evidence.
- Retrieval ablations and prompt/model-version evaluations before promotion. Keep CI deterministic by default; opt-in hosted model evaluations are budgeted and separately reported.

## 9. Security, cost, and operational requirements

- Authenticate at the API; carry trusted authorization through all adapters, checkpoints, caches, summaries, and source downloads. Revalidate reviewer permissions on resume. Start with explicit supported access partitions rather than pretending arbitrary document ACL combinations can safely share summaries.
- Treat documents and model output as untrusted data. Use schema validation and tool allowlists; source text cannot issue instructions, choose credentials, disable filters, or approve actions.
- Restrict source fetching to approved schemes/domains; block loopback/private metadata endpoints and unsafe redirects. Enforce file/page/decompression/time limits; disable parser callbacks to arbitrary URLs. Sandbox local parsers.
- Use TLS verification, least-privilege service accounts, secret references, and environment-specific namespaces. Runtime accounts do not need schema-administration privileges. Do not use the LiteLLM master key in the application.
- Minimize logged document text and prompts. Decide residency, retention, provider-training policy, and licensed-document handling before enabling external model calls/tracing.
- Batch embeddings/extraction with per-tenant concurrency and rate limits. Cache by content plus model/prompt/schema/profile, scope, and manifest where relevant. Do not use semantic answer caching until invalidation and ACL behavior are proven.
- Maintain an extraction/summary dependency ledger so changes rebuild only affected work. Reuse identical content computations without reusing obsolete version-specific provenance.
- Keep graphs and vector indexes rebuildable from retained artifacts and registry state. Recovery includes Postgres/checkpoints and artifact backups, not just provider database snapshots.

## 10. Decisions to validate, not blockers to writing code

Phase 0 must establish hosted endpoint versions/authentication, Memgraph MAGE availability, parser job protocol, gateway aliases/limits, approved storage and Postgres availability, and the service region/data policy. Phase 1 has one raw PDF/JSON example; it still needs a reviewer for the benchmark and representative scanned/non-PDF inputs. Actual earlier compilations and delegated rules are also needed before claiming historical-law or rule-specific coverage. Before shared release, confirm identity provider, tenant/access model, expected document/page volume, concurrency, retention/legal hold, and operational owners.

Until those facts are known, proceed with the stated single-organization defaults, local disposable development services, explicit capability reports, and no production writes. Keep parser selection and retrieval thresholds reversible. Defer multi-agent “teams,” arbitrary Cypher generation, fine-tuning, multimodal retrieval, automatic legal conflict resolution, and external control execution until a measured use case justifies them.

## 11. Official references

Reviewed for this plan; exact deployed versions still require compatibility tests.

- [LiteLLM proxy capabilities](https://docs.litellm.ai/docs/providers/litellm_proxy)
- [LangChain OpenAI-compatible integration and limitations](https://docs.langchain.com/oss/python/integrations/chat/openai)
- [LangGraph persistence](https://docs.langchain.com/oss/python/langgraph/persistence) and [interrupts](https://docs.langchain.com/oss/python/langgraph/interrupts)
- [Docling document model](https://docling-project.github.io/docling/concepts/docling_document/) and [supported formats](https://docling-project.github.io/docling/usage/supported_formats/)
- [LiteParse](https://developers.llamaindex.ai/liteparse) and [CLI output capabilities](https://developers.llamaindex.ai/liteparse/cli-reference)
- [Qdrant point IDs and vectors](https://qdrant.tech/documentation/concepts/points/)
- [Memgraph Python/Bolt client](https://memgraph.com/docs/client-libraries/python) and [MAGE Leiden](https://memgraph.com/docs/advanced-algorithms/available-algorithms/leiden_community_detection)
