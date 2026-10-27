# Process documentation sections moved out of DocBrain `docs/`

These sections were moved from `docs/` on 2026-10-26, when the process application (Compliance Agent, Documentation Agent, site and process sources, templates, policy/manual/procedure package generation, review, and export to `assets/publish`) was separated from DocBrain. DocBrain is now the regulatory knowledge application; see [README.md](./README.md).

The text below is verbatim from the original files. Only relative links were changed so they resolve from this folder: links to the stage documents now point to `../../docs/`, and links to source files point to `../../src/`. Links to `./implementation_plan.md` and `./coding_tasks.md` were left as written; from this folder they point to the process sections moved into [implementation_plan.md](./implementation_plan.md) and [coding_tasks.md](./coding_tasks.md). The one backlog anchor was updated to match its heading in the moved backlog. The `assets/publish` examples mentioned below were removed from the working tree (see [README.md](./README.md)).

Where a paragraph mixed regulatory and process content, the regulatory part stays in the original file in edited form, and the full original paragraph is kept here.

## From `docs/rag_architecture.md` — introduction (original text)

A unified, tri-focal retrieval architecture for regulatory compliance, risk analysis, and generation of site-specific policies, manuals, and procedures from regulatory, process, and site knowledge.

## From `docs/rag_architecture.md` — "Implementation baseline" (original bullets)

- **In-repository execution:** LangChain tools/model composition and LangGraph ingestion, answering, and approval workflows. The retrieval broker and compliance agents are part of DocBrain, not separate products to procure.
- **Release order:** cited vector Q&A → grounded graph relationships → evaluated hierarchical/global retrieval and approval-gated site documentation. Mixed-source/site contracts start during ingestion; Documentation Agent delivery does not require optional community retrieval to succeed.
- **Trust:** tenant/site/process access checks apply to all stores, derived summaries, and exported documents. Extracted law, site facts, draft process descriptions, templates, proposed controls, and approved policy remain distinct. Citation presence alone does not prove claim support, applicability, or approval.
- **Documentation Agent:** lives in RETRIEVE and uses the shared broker to generate document packages; authenticated application operations handle review and publication to `assets/publish`. The model cannot approve itself, write arbitrary paths, or operate plant/business systems.

## From `docs/rag_architecture.md` — "Knowledge inputs and generated outputs have different authority" (original section)

### Knowledge inputs and generated outputs have different authority

The source-document input in the overview below includes legislation/rules, permits, standards/guidance, process descriptions, site/equipment facts, and existing organizational documents. All use PARSE → EXTRACT → ENCODE, retaining source class, revision, approval state, and authorized site/process scope. Templates are formatting inputs, not evidence for legal duties or operating limits. Topic similarity alone never establishes regulatory applicability.

The Documentation Agent's router arrow denotes a retrieval request; the Evidence Bundle also returns to that agent for drafting and verification. The ordinary Q&A response path is separate from controlled document publication. Knowledge-index publication does not approve a generated policy, and an existing file under `assets/publish` is not automatically approved knowledge.

## From `docs/rag_architecture.md` — §1 overview diagram (removed node)

```mermaid
        DOCAGENT["Documentation Agent"]:::agent --> ROUTER
```

## From `docs/rag_architecture.md` — §2 lifecycle table, Stage 4 row (original text)

| Lifecycle Stage | Detailed Documentation Guide | Key Responsibilities | Reference Implementation |
| :--- | :--- | :--- | :--- |
| **Stage 4: Retrieve** | [rag_retrieve.md](../../docs/rag_retrieve.md) | Routing, grounding, fusion, corrective Q&A, and Documentation Agent generation with applicability assessment, package validation, human review, and controlled export. | [`router.py`](../../src/router.py), [`broker_fusion.py`](../../src/broker_fusion.py); planned `workflows/documentation.py` |

## From `docs/rag_architecture.md` — §4.3 "Documentation Agent: evidence to controlled site documents"

### 4.3 Documentation Agent: evidence to controlled site documents

```diagram
┌───────────────────────────┐     ┌──────────────────────────────┐
│ Site/process + document   │────▶│ Documentation Agent          │
│ request + template refs   │     │ Authorize, pin, plan sections│
└───────────────────────────┘     └──────────────┬───────────────┘
                                               │ section queries
                                               ▼
┌───────────────────────────┐     ┌──────────────────────────────┐
│ Scoped knowledge: law,    │◀───▶│ Shared Retrieval Broker      │
│ permits, processes, sites │     │ Evidence + missing sources   │
└───────────────────────────┘     └──────────────┬───────────────┘
                                               ▼
                                 ┌──────────────────────────────┐
                                 │ Applicability + drafting     │
                                 │ Policy / manual / procedure  │
                                 └──────────────┬───────────────┘
                                               ▼
                                 ┌──────────────────────────────┐
                                 │ Verify coverage, consistency │
                                 │ and source support; list gaps│
                                 └──────────────┬───────────────┘
                                               ▼
                                 ┌──────────────────────────────┐
                                 │ Authorized human review      │
                                 │ Reject/revise or approve hash│
                                 └──────────────┬───────────────┘
                                               ▼
                                 ┌──────────────────────────────┐
                                 │ Controlled application export│
                                 │ assets/publish/.../revision/ │
                                 └──────────────────────────────┘
```

LangGraph checkpoints preserve the outline, per-section drafts, source snapshot, applicability decisions, missing facts, and review state. The agent links applicable requirements → controls → document sections/steps, retaining exact regulatory and operational source spans. Process or site changes are first-class change triggers alongside law changes. Conflicts and unresolved dependencies require review, not automatic precedence based on retrieval score.

Exports contain Markdown documents, a package manifest, evidence mappings, and review/gap records. Draft exports are marked **not for operational use**; only approved, dependency-current revisions can become the registry's published package. Safe staging and idempotent publication preserve previous complete packages. Approval is bound to exact content and dependencies; edits or source changes invalidate it. Generated documents are not recursively ingested as independent authority.

Existing P-001 and WI-007 are draft examples with unresolved operating values and missing source references. Preserve them unchanged; registration must record their actual trust status. Safety-critical gaps require qualified technical review before publication. The [implementation plan](./implementation_plan.md#documentation-agent-workflow-retrieve) defines package paths, contracts, API, and review rules; DB-031–DB-035 in the [backlog](./coding_tasks.md) define delivery checks.

## From `docs/rag_architecture.md` — §5 "Quality Assurance & Continuous Evaluation", Documentation quality metric

- **Documentation quality:** reviewed obligation coverage, correctly grounded site facts/limits, consistent roles and cross-document references, visible gaps, and isolation between sites. Valid citation IDs alone are insufficient. Reject unsupported safety-critical instructions, stale approvals, circular evidence, and partial-package publication; test change propagation from process and site inputs as well as legislation.

## From `docs/rag_retrieve.md` — introduction (original text)

A technical guide for agents to retrieve regulatory, process, and site evidence, build grounded answers, and generate site-specific policy/manual/procedure packages through the Documentation Agent.

## From `docs/rag_retrieve.md` — "Documentation requests" note

**Documentation requests:** use the same authorized broker but a separate checkpointed generation workflow, not the ordinary Q&A response path. Bind tenant/site/process and source roles before retrieval; templates and generated derivatives cannot become legal or site-fact authority. Long manuals use bounded per-section retrieval and package-wide budgets. See Section 8 and the [plan](./implementation_plan.md#documentation-agent-workflow-retrieve) for review/export contracts.

## From `docs/rag_retrieve.md` — Section 8 "Documentation Agent within RETRIEVE"

## 8. Documentation Agent within RETRIEVE

**Planned implementation:** `workflows/documentation.py` orchestrates LangChain model/tool calls via LangGraph; `documentation.py` validates/renders packages and prepares controlled exports. Reuse the broker, source resolver, jobs, registry, and review contracts. No second vector index or independent agent service is needed.

### 8.1 Inputs and evidence separation

A request identifies an authorized site/process, as-of date, document types (policy, manual, procedure), template revisions, and optional prior package. Tenant identity and permitted scope come from trusted context. Pin source/site/process revisions and separately retrieve:

1. Regulatory obligations, permits, standards, and guidance, with their distinct authority and applicability status.
2. Process steps, site roles/equipment, approved operating limits, and existing organizational requirements, with exact revision and review state.
3. Templates for layout and existing draft/generated documents for explicitly labelled reference or revision comparison, not independent authority.

Each section bundle includes source class/status, site/process scope, immutable spans, reviewed applicability decision IDs, missing/conflicting facts, and dependencies. Dense/sparse, graph expansion, summaries, and direct fetches enforce the same filters. Compression cannot discard a limit's unit, exception, prerequisite, or source role. An unavailable site licence or rule stays a gap; regulatory text and internal preferences are never merged simply because their wording is similar.

### 8.2 Drafting and validation

Plan a package outline and stable document IDs, then draft sections using a shared role/terminology register and obligation-to-section coverage map. Policy states commitments and accountabilities; manual explains the management system and links its procedures; procedures specify supported roles, prerequisites, steps, hold points, records, and escalation paths. This describes document structure, not permission to invent missing operational content.

Every substantive statement must have immutable support or be marked as a proposed organizational control. Preserve uncertainties such as `torque x` and `[TBC]`; templates' example values are not defaults. Check evidence support, numeric/unit/modality fidelity, regulatory applicability, cross-document consistency, resolvable links, and critical gaps before requesting review. Source status can permit a provisional draft while still blocking operational approval. Budgeted retrieval/repair loops end with actionable gaps, not endless attempts to fill them from model memory.

For the supplied P-001/WI-007 drafts, do not infer confirmed emergency locations, alarm settings, permit conditions, or manufacturer limits. The Recycling Act alone does not prove which duties apply at the site. D01–D10 in the [backlog](./coding_tasks.md#from-1-documentation-examples-and-acceptance-scenarios) cover these failure cases and a corrected synthetic positive case.

### 8.3 Review, export, and later changes

Use the existing authenticated approval API and LangGraph interrupts for site/process and compliance review, plus competent technical review of safety-critical content. Decisions bind the exact content/dependency hashes. Missing critical evidence, changed inputs, rejected proposals, or revoked reviewer permissions prevent publication; a source instruction or model judge cannot approve anything.

The application exports Markdown packages under `assets/publish/<tenant-id>/<site-id>/<package-id>/<revision>/` with a manifest, evidence map, and review/gap record. Draft exports carry a not-for-operational-use label and are never current approved output. Staged complete exports become current only through the registry after approval and current-dependency checks; the model does not write files. Preserve supplied examples and previous revisions. Source updates mark dependent packages needs-review and generate a diff proposal; no silent regeneration or automatic ingestion of generated files. Artifact downloads recheck scope and revocation. Full API and filesystem contracts are defined in the implementation plan; PDF/DOCX export and external distribution are not initial requirements.

## From `docs/rag_extract.md` — "Site documentation extension"

**Site documentation extension:** process descriptions and site documents contribute versioned facts about activities, equipment, roles, prerequisites, and operating limits, each carrying source class, scope, and review state. Model `Site`, `Process`, `DocumentSection`, and reviewed requirement-to-site applicability alongside the four-tier model. A template example or draft process statement cannot become an approved fact merely by extraction. Preserve applicable/not-applicable/undetermined decisions with rationale, source spans, and reviewer provenance; unresolved law/permit/process conflicts remain review items.

The Documentation Agent links approved requirements → controls → generated policy/manual/procedure sections, and separately links those sections to supporting site/process facts. Track source, template, and applicability revisions in the dependency ledger. Both legal changes and site/process changes invalidate affected generated sections; outputs retain derivative lineage and cannot prove their own source obligations. DB-031–DB-035 in the [backlog](./coding_tasks.md) define this extension; the ontology examples below remain illustrative and incomplete.

## From `docs/rag_extract.md` — §5.5 "The \"Needs Review\" Quarantine Protocol", point 4

4. Generated document packages with changed dependencies become `needs_review`; retain previous content, surface affected sections and a proposed diff, and obtain site/process plus compliance review (and competent technical review for safety-critical content). Do not silently update `assets/publish`, replace human edits, or continue to present stale packages as current validated guidance. Review and export use the shared registry contracts in the implementation plan.

## From `docs/rag_parse.md` — introduction and "Mixed-source contract" (original text)

A detailed engineering guide for agents to ingest regulatory, process, and site documents, preserve structural hierarchy, normalize complex formats, and retain source-grounded assertions.

**Mixed-source contract:** preserve source role (regulatory authority, process description, site fact, organizational document, template, generated derivative), tenant/site/process scope, revision/effective dates, and claimed versus verified approval status. Non-legal documents need document/section IDs, not fabricated Act/clause identifiers. Preserve process ordering, prerequisites, hold points, equipment tags, role references, and explicit unknowns such as `torque x`/`[TBC]`. A template's sample limit is not a site fact. Missing source references or empty templates become findings, not invented content. Existing `assets/publish` files are imported only through explicit registration; generated output is excluded from automatic ingestion. DB-031 in the [backlog](./coding_tasks.md) defines acceptance cases.

## From `docs/rag_encode.md` — "Mixed-source/site indexing" (original text)

**Mixed-source/site indexing:** carry tenant/site/process scope, source role, authority subtype, review/effective state, and derivative lineage into chunk payloads, graph assertions, summary dependencies, and retrieval/cache predicates. Shared corporate sources require explicit scope; an absent site ID is not permission to share. Do not merge regulatory obligations with similar process instructions or template examples. Summaries must preserve these distinctions and cannot combine sources with incompatible audiences. Index publication makes evidence queryable; it does not approve an organizational document. Generated `assets/publish` packages enter knowledge only through explicit registration with original dependency lineage, never recursive ingestion. Source changes invalidate dependent documentation packages as well as summaries; see DB-031–DB-035 in the [backlog](./coding_tasks.md).

## From `docs/rag_deployment.md` — "Documentation Agent deployment boundary"

### Documentation Agent deployment boundary

Run documentation jobs in the existing DocBrain worker with LangGraph checkpoints and LiteLLM calls; no additional hosted agent platform is required. Provision private export storage and designated site/process/compliance reviewers, with competent technical review for safety-critical documents. Local development exports use `assets/publish/<tenant-id>/<site-id>/<package-id>/<revision>/`; shared deployments use the artifact backend with the same logical layout and authorization rules. The supplied draft examples must not be overwritten or treated as approved inputs automatically.

Do not expose `assets/publish` as a public static directory or commit generated sensitive site content by default. Authorize package/download endpoints, enforce root/path/symlink containment and least-privilege storage access, and recheck source permissions at delivery. Back up package files, evidence/approval manifests, registry current references, and pending review checkpoints together; rehearse interrupted export recovery. Law/process/site changes mark dependent packages needs-review. Distributed offline copies require an operator withdrawal process; deleting the managed export cannot recall them. Budget long document jobs independently from interactive Q&A, and stage only complete reviewed packages as current.

## From `docs/project_structure.md` — current layout, `/assets/publish` entry

- `/assets/publish` Supplied draft process/work-instruction/form examples and the target root for controlled Documentation Agent exports. Presence here is not approval; preserve existing files and register any reference input explicitly.

## From `docs/project_structure.md` — target application layout (removed modules)

```text
src/docbrain/
├── documentation.py            # package validation, rendering, controlled export
├── workflows/
│   └── documentation.py        # site applicability, outline, sections, package review
```

## From `docs/project_structure.md` — "Planned documentation inputs and export layout"

## Planned documentation inputs and export layout

Process and site inputs use the existing raw → parsed → reviewed-derived lifecycle with metadata for tenant/site/process, source role, revision, and review state; authority is not inferred from a directory. Existing files in `assets/publish` are not moved or overwritten. P-001 and WI-007 are draft reference examples; template example values are not approved plant facts. Obtain authoritative site/permit/equipment inputs and approved policy/manual templates before operational publication.

```text
assets/publish/<tenant-id>/<site-id>/<package-id>/<revision>/
├── manifest.json               # file hashes, scope, revisions, status, dependencies
├── evidence.json               # section → obligation/control/source span mappings
├── review.md                   # reviewer decisions, gaps, change rationale
├── policies/                   # organizational commitments and accountabilities
├── manuals/                    # management system and controlled procedure links
├── procedures/                 # supported roles, steps, prerequisites, hold points
├── work-instructions/          # optional requested supporting detail
└── forms/                      # optional blank templates, never invented records
```

Markdown is the initial export format. Server-issued IDs determine paths; package creation/status/export/download share API/CLI application functions. A staged complete package is made current only after authorized review and a registry publication check. Draft exports are labelled not for operational use and use immutable identities distinct from approved exports. Keep source and approval lineage with every revision; dependency changes mark it needs-review. Do not recursively ingest output or serve the root publicly. In shared deployments, use private managed artifact storage with the same logical layout; local files are review/export artifacts, not the job/checkpoint database. See DB-031–DB-035 in the [coding backlog](./coding_tasks.md).
