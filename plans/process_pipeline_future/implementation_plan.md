# Process application implementation plan (future)

Status: **moved, not active** (2026-10-26). These sections were moved from the [DocBrain implementation plan](../implementation_plan.md) when the process application (Compliance Agent, Documentation Agent, site/process/template sources, applicability against a site, policy/manual/procedure package generation, package review, and controlled export) was separated from DocBrain. DocBrain is now the regulatory knowledge application; this application will call DocBrain's query API instead of sharing its stores. The content below is preserved as written under headings naming its original section and needs revision when the process application is designed. Task and scenario IDs refer to the [process coding backlog](./coding_tasks.md) and the [DocBrain coding backlog](../coding_tasks.md). The `assets/publish` directory no longer exists in the DocBrain repository.

## From §1 "Deliver grounded answers before autonomous actions"

The opening paragraph as originally written:

Build a Python application that ingests regulatory, process, and site-specific documents, answers questions with inspectable source evidence, explains changes, and generates site-specific policies, manuals, and procedures for human approval. The **Documentation Agent**, within RETRIEVE, combines applicable regulatory obligations with process evidence and site facts through the shared retrieval broker. Its versioned output packages live under `assets/publish` in local development. The agents, prompts, tools, and workflows live in this repository; hosted providers supply parsing, models, vector storage, and graph storage.

## From §1 "Working assumptions"

- Process descriptions, site profiles, equipment instructions, permits, existing organizational documents, and templates join the same knowledge pipeline with distinct source roles and approval states. A folder name or a document's self-declared status is not evidence of authenticated approval. Existing `assets/publish` examples are reference inputs only when explicitly registered; do not recursively ingest generated outputs.

## From §4 "Identity, provenance, and legal time"

| Object | Required identity and metadata |
| --- | --- |
| Site/process context | Tenant-scoped site/process IDs, jurisdiction, activities, equipment, roles, permits, effective revisions, and evidence for each fact. Unknown applicability is explicit; missing site scope is not global scope. |
| Applicability decision | Requirement version, site/process revision, `applicable`/`not_applicable`/`undetermined`, rationale, source spans, missing facts, reviewer identity and decision revision. Model suggestions remain unapproved. |
| Documentation package | Package/revision IDs, document kinds/IDs, target site/process, pinned source manifest and applicability decisions, template/model/prompt profiles, section-to-source/control mappings, unresolved issues, file hashes, status, owner/approver records, effective date, and dependency ledger. |

Source classification paragraph as originally written (DocBrain keeps the regulatory source classes: law, permit conditions, standards, and guidance):

Classify each source as regulatory authority, process description, site fact, organizational policy/procedure, template, or generated derivative; additionally distinguish law, permit conditions, standards, and guidance within authority sources. Record tenant/site/process scope, source approval state, document owner, revision, and dependency provenance on chunks, assertions, summaries, and evidence bundles. Organization-wide material must be explicitly assigned an authorized shared scope. A federal Act matching the topic does not establish that a particular site or activity is subject to it; applicable state law, permits, rules, and exemptions may be missing.

Keep three independent states: a knowledge build being queryable, a document's review/effective status, and a generated package's export status. Neither presence in `assets/publish` nor ingestion approval makes a document effective organizational policy. Templates supply layout, not facts or mandatory limits. Existing draft instructions may inform a visibly provisional draft, but cannot establish verified plant safety limits or legal duties.

## From §5 "Workflows to implement in this repository"

### Documentation Agent workflow (RETRIEVE)

`authorize target → pin source/site/process revisions → assess applicability and gaps → plan document set → retrieve evidence per section → draft → validate package → human review → export approved revision`

- Accept a site, process scope, as-of date, requested document types, approved template references, and optional prior package revision. Initial required types are **policy**, **manual**, and **procedure**; process maps, work instructions, and blank forms are linked supporting artifacts where requested. Manual sections reference procedures by stable IDs and exact revisions rather than duplicating inconsistent instructions.
- Retrieve regulatory obligations and operational evidence separately under the same authorized snapshot, then join them through reviewed applicability decisions and requirement/control dependencies. Preserve source class in the evidence bundle. Rank alone cannot resolve conflicts or turn an internal preference into law. Missing permits, delegated rules, equipment specifications, or site facts become actionable gap items with an owner to confirm, not invented content.
- Draft in bounded section-level calls using a package-wide outline, terminology/role register, document-ID register, and shared evidence map. Store section outputs and checkpoints; cap total tokens, sections, corrective rounds, time, and retries. No requirement to fit a manual into the Q&A evidence token budget or meet Q&A latency targets.
- Each substantive requirement, operating step, numerical limit, role assignment, and legal statement links to immutable evidence or is explicitly labelled a proposed organizational control needing approval. Preserve `torque x`, `[TBC]`, and missing-rule limitations as unresolved issues. Never copy template examples such as `0 PSI` or `5°C/min` into a site instruction without validated site evidence. Safety-critical missing/conflicting facts block approval, even when a draft can be produced.
- Validate coverage of selected applicable obligations; list exclusions and rationale. Check citations, numeric/unit/modality fidelity, step prerequisites/hold points, policy/manual/procedure consistency, cross-document links, source status, and site isolation. An LLM judge cannot authorize a safety-critical procedure. Require designated site/process and compliance reviewers; safety-critical content requires a competent technical reviewer. Exact people and role policy are deployment inputs.
- Use `draft → in_review → approved → published` as the successful document lifecycle, with rejection returning a new draft revision. Bind decisions to package content hashes and the source/template/applicability revisions. Any content edit invalidates prior approval; dependency changes before approval or export force reassessment. An export is not an external filing, staff notification, or instruction to operate equipment.
- Export Markdown first to `assets/publish/<tenant-id>/<site-id>/<package-id>/<revision>/`, with `policies/`, `manuals/`, `procedures/`, and requested supporting document directories. Include `manifest.json`, `evidence.json`, and `review.md` for identity/status/checksums, section-level traceability, approvals, gaps, and change rationale. Draft exports are permitted only with conspicuous draft/not-for-operational-use status and must never become the current approved package. PDF/DOCX rendering is deferred until required.
- The application owns rendering and safe paths; the model never selects filesystem destinations. Stage a complete package, verify hashes/links, move it into an immutable revision directory, then update the registry's current published reference with compare-and-swap. Reconcile crash-orphaned exports; retries cannot duplicate publication, overwrite existing examples, or expose a partial package as current. Readers use the registry's approved reference, not a directory scan.
- Law, permit, site/process, equipment, or approved organizational-source changes mark dependent packages `needs_review`; retain the prior revision and show its review-required state, but do not silently rewrite or present it as current validated guidance. Revocation/erasure also applies to exported derivatives and downloads. Re-ingestion of an approved generated document is explicit, carries original lineage and derivative classification, and cannot provide circular support for its own obligations.

The existing P-001 process and WI-007 emergency-shutdown documents are draft examples, not validated instructions. Their unresolved values and referenced but unavailable source documents are deliberate acceptance cases. Do not claim the supplied Recycling Act establishes Wodonga plant operating limits or covers all Victorian obligations.

Agent tool list as originally written (DocBrain keeps the other tools; `propose_document_package` and export belong here):

Tools exposed to agents are narrow: `search_evidence`, `fetch_source_span`, `trace_requirement`, `compare_versions`, `propose_control`, and `propose_document_package`. Approval and export are authenticated application operations, not model tools. Tool inputs do not grant access: tenant and permissions come from trusted request context. Database credentials, unrestricted query tools, and arbitrary filesystem writes are never given to the model.

## From §6 "Phase 5 — Site documentation, change impact, and controlled publication"

**Build:** version diffing, obligation comparison, site/process applicability assessment, dependency impact traversal, Documentation Agent generation of policy/manual/procedure packages, approval/rejection/resume endpoints, controlled `assets/publish` exports, and append-only decision history. Ingest mixed source roles and site metadata in Phase 1; do not defer that schema work until generation. Add reviewer-readable evidence exports; no UI framework is needed until an actual review workflow requires it.

**Gate:** a selected site receives a consistent policy, manual, and procedure package grounded in authorized regulatory and operational evidence. Missing safety limits or applicability evidence blocks approval; template example values never become site facts. Site A's facts do not leak into site B's documents. A changed law or process identifies the correct downstream sections; editorial changes do not silently alter approved procedures. Reviewed proposals resume after process restart; export failure cannot replace the last complete approved package. Unauthorized, stale, and replayed approval requests are rejected. Generated suggestions remain visibly distinct from extracted law and approved organizational policy.

## From §7 "Proposed API and operator surface"

| Surface | Behavior |
| --- | --- |
| `POST /v1/document-packages` | Queue Documentation Agent work for an authorized site/process, requested types, template revisions, as-of date, optional previous revision, and idempotency key; return job/package IDs. |
| `GET /v1/document-packages/{id}` | Authorized revision/status, document inventory, gaps, evidence/coverage map, review decisions, and source dependencies. |
| `POST /v1/document-packages/{id}/exports` | Export the expected revision/hash in explicit draft or approved mode after current authorization/dependency checks; return an authorized artifact reference, not an arbitrary filesystem path. |
| `GET /v1/document-packages/{id}/artifacts/{artifact_id}` | Reauthorize access to a specific immutable exported file; surface draft, superseded, or needs-review status. |

CLI sentence as originally written:

Planned CLI verbs: `doctor`, `ingest`, `job`, `query`, `source`, `evaluate`, `document generate/inspect/export`, `review`, and explicit admin-only `migrate`/`reconcile`. Share implementation with API handlers; avoid a second retrieval or documentation pipeline.

## From §8 "Evaluation and release criteria"

- Documentation evaluations: obligation-to-section coverage, grounded operating limits/roles, unresolved-gap reporting, cross-document consistency, site isolation, stale-review rejection, crash-safe export, and propagation of law/process changes. Run all three required document types on labelled synthetic site fixtures plus reviewed excerpts from the supplied draft examples. Require zero unsupported safety-critical limits and zero publication of unapproved or dependency-stale content. Long-document job budgets are measured separately from Q&A.

## From §10 "Decisions to validate, not blockers to writing code"

Documentation inputs and shared-release items as originally written:

For documentation, register authoritative site/process inputs, licences/permits, manufacturer instructions, approved templates, document numbering, responsible reviewers, and effective-date rules. Existing draft examples are not substitutes for those approvals; the supplied form template is empty and some referenced manuals/regulations are absent. Before shared release, confirm identity provider, tenant/site/access model, expected document/page volume, concurrency, retention/legal hold, publication destination/access policy, and operational owners. `assets/publish` is the local export root, not permission to commit sensitive site documents or deploy a public file server.
