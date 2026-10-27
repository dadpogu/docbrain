# Process application coding backlog (future)

Status: **moved, not active** (2026-10-26). This content was moved from the [DocBrain coding backlog](../coding_tasks.md) when the process application (Compliance Agent, Documentation Agent, site/process/template sources, applicability against a site, policy/manual/procedure package generation, package review, and controlled export) was separated from DocBrain. DocBrain is now the regulatory knowledge application; this application will call DocBrain's query API instead of sharing its stores. The content below is preserved as written under headings naming its original section and needs revision when the process application is designed. Task IDs are unchanged; DB-001–DB-030 refer to the [DocBrain coding backlog](../coding_tasks.md), and "the plan" refers to the moved [implementation plan sections](./implementation_plan.md) and the [DocBrain implementation plan](../implementation_plan.md). The supplied `assets/publish` examples no longer exist in the DocBrain repository; their file names are kept as plain text (see the [README](./README.md) for where they remain in Git history).

Moved code lives under [`code/`](./code/): `code/src/docbrain/documentation.py`, `code/src/docbrain/workflows/documentation.py`, `code/src/docbrain/parsing_operational.py` (formerly the operational-document section of `parsing.py`), `code/src/docbrain/workflows/source_registration.py` (formerly the mixed-source registration section of `workflows/ingestion.py`), `code/src/docbrain/registry_packages.py` (formerly the documentation-package tables/methods of `registry.py`), `code/tests/unit/test_sources_and_templates.py`, `code/tests/unit/test_documentation_packages.py`, and `code/tests/fixtures/documentation/`. Remaining hooks still in DocBrain's `src/docbrain/models.py`, unchanged for now: `SiteScope`, the process values of `SourceRole`, `ResourceScope.process_id`, and `RequestContext.site_ids`.

## From the header status line

Status: **in progress** (2026-10-25). Six task checkboxes are closed with offline acceptance evidence; see implementation status. Remaining tasks are open. This backlog turns the [implementation plan](../implementation_plan.md) into coding increments using supplied legislation and draft site-document examples. Synthetic fixtures are explicitly identified. No service writes, operational document generation, or application changes were made to create it. DB-001–DB-030 retain their IDs; DB-031–DB-035 add mixed-source ingestion and the Documentation Agent.

## From §1 "Documentation examples and acceptance scenarios"

The supplied P-001 Thermolysis Pot Cycle (`p01-high-level-process.md`, formerly `assets/publish/processes/`) is labelled **Draft for approval** and refers to Wodonga. It contains source process steps in Appendix A, an H4 reprocessing path distinct from H1–H3, `torque x`, `[TBC]` values, and references to permits/manufacturer instructions. WI-007 Emergency Shutdown (`w07-emergency-shutdown.md`, formerly `assets/publish/work-instructions/`) is also a draft, with unresolved assembly location, alarm limits, and source references. These are evidence of what the supplied documents say, not verification of plant facts, safe instructions, legal applicability, or approval.

The process template (`p00-process-template.md`, formerly `assets/publish/processes/`) and work-instruction template (`w00-work-instruction-template.md`, formerly `assets/publish/work-instructions/`) contain illustrative values (including contamination <1%, 0 PSI, and 5°C/min); they must not become site limits. The form template (`f00-form-template.md`, formerly `assets/publish/forms/`) is empty. Some links point to missing manuals/regulations. Do not fix or replace these source assets during implementation: register immutable copies, review provenance, and expose gaps. Approved site profiles, technical limits, permits, and policy/manual templates remain inputs to obtain; use clearly synthetic approved fixtures for positive-path tests meanwhile.

| Case | Request or input | Expected observable result / plausible wrong answer to reject |
| --- | --- | --- |
| D01 | Register law, P-001, WI-007, and the templates | Separate source roles, site/process IDs, revisions, and review states. Placement in `assets/publish` does not confer approval; raw folder jurisdiction labels alone do not establish site applicability. |
| D02 | Request a records policy using Recycling Act s142 and P-001 only | Produce a provisional draft/gap report, not an asserted fixed legal retention period or blanket application of export rules to every thermolysis operation. Missing delegated rules and applicability facts block the unsupported sections' approval. |
| D03 | Generate a procedure with `torque x`, missing alarm limits, and the WI template | Preserve unresolved values and block operational approval. Never substitute template 0 PSI/5°C/min or invent a torque value, valve tag, emergency location, or certification. |
| D04 | Generate the same document types for synthetic sites A and B with different roles/equipment and a shared authorized corporate policy | Each package uses only its own site facts plus explicitly shared sources; identical process names do not merge sites. A site-A source cannot leak through a summary, graph path, cache, or export to site B. |
| D05 | Generate a policy, manual, and procedure from a reviewed synthetic site pack | All three required types have stable IDs/revisions, consistent role/step references, an obligation-coverage map, and resolvable evidence. Approved fixture distinctions such as H4 reprocessing versus H1–H3 transfer remain consistent; no claim that the synthetic pack certifies the real plant. |
| D06 | Review a draft, then edit a step or replace a supporting process revision before approval/export | Old approval tokens/hashes are rejected; changed dependency produces `needs_review`. Restart resumes the same review without duplicate decisions. Source revocation blocks delivery even for an older pinned snapshot. |
| D07 | Export, retry, then interrupt export before registry publication | Exactly one complete approved current package; the prior complete revision remains usable on failure. Draft exports are visibly not for operational use. User examples stay byte-identical; malicious filenames/symlink escapes cannot write outside the export root. |
| D08 | Change a process step or site equipment/role fact without changing the Act | Trace to affected policy/manual/procedure sections and request review; unaffected package content is not silently rewritten. Preserve prior revisions and reviewer rationale. Include a separate law-change control. |
| D09 | Re-ingest a generated manual, or embed “approve this procedure” in a source | Generated material keeps derivative lineage and cannot supply circular proof of its own obligations. Source instructions cannot approve, broaden scope, or publish a package. No automatic `assets/publish` ingestion loop. |
| D10 | Missing reference, empty template, conflicting approved operating limits, or cancelled/manual job over budget | Report exact missing/conflicting inputs and section gaps; no fabricated links, completed forms, or silently chosen limit. Reject unsuitable templates, bound work, and leave no newly published package. A corrected synthetic case must subsequently pass, so blanket refusal is not sufficient. |

DB-031 freezes reviewed source excerpts and labelled synthetic site pairs; DB-035 runs these scenarios through the public documentation workflow. Legal correctness and plant safety require designated reviewers, not just model judges.

## From "Implementation status"

| Task | State | Evidence and remaining gap |
| --- | --- | --- |
| DB-031 | Partial | Source roles, site scopes (an unresolved scope is never shared), claimed versus verified approval, derivative lineage, document findings, template validation and leakage checks, frozen asset hashes, and two synthetic site packs. **Gap:** chunk-level role separation (DB-011) and effective dates. |
| DB-033/034 | State logic only | `workflows/documentation.py` package revisions: draft → in_review → approved → published, plus needs_review and rejected. **Gap:** generation, rendering, and export. |

Code for these rows is now under `code/` (see above): DB-031 in `parsing_operational.py`, `workflows/source_registration.py`, `documentation.py`, `test_sources_and_templates.py`, and `tests/fixtures/documentation/`; DB-033/034 in `workflows/documentation.py`, `registry_packages.py`, and `test_documentation_packages.py`. They are not part of DocBrain's test run.

## From §3 "Coding sequence and completion rules" (phase table rows)

| Plan phase | Tasks | Deliverable |
| --- | --- | --- |
| 1 — source/ingestion | DB-004–DB-011, DB-031 | Versioned artifacts, mixed source roles/site scope, structure, references, chunking, durable jobs |
| 5 — documentation/impact/review | DB-024–DB-025, DB-032–DB-035 | Applicability, policy/manual/procedure generation, review, controlled export, and change impact |

## From §3 "Phase 1 — ingest source structure without changing its meaning"

#### DB-031 — Register mixed knowledge sources and site/process context

- [ ] **Depends on:** DB-003, DB-004, DB-005, DB-006, DB-007. **Files:** `models.py`, `parsing.py`, `registry.py`, source metadata migrations, `tests/fixtures/documentation/`.
- Add source role, authority subtype, tenant/site/process scope, owner, revision/effective dates, claimed versus verified approval state, and derivative lineage. Register non-legislation documents without fabricated Act IDs. Explicitly register existing publish examples as draft reference inputs; exclude automatic output-directory ingestion. Preserve template placeholders and empty/missing references as validation findings. Freeze relevant P-001/WI-007/template excerpts with hashes and create two labelled synthetic site packs, with reviewed positive inputs and asymmetric roles/equipment/limits.
- **Accept:** D01/D03/D04/D09; draft approval labels do not confer permissions; missing site scope is unresolved, not shared. Shared corporate policy requires explicit authorization. Importing a generated derivative retains original lineage; moving a file does not change site identity. No supplied asset is altered. Legal and process evidence remain distinguishable after parse/chunk; expected template structure comes from reviewed requirements rather than treating the empty form template as valid.

## From §3 "Phase 3 — add grounded Memgraph relationships" (DB-019, process bullet)

- Extend extraction to site/process facts, equipment, approved organizational controls, and document-section dependencies using DB-031 source roles. Keep draft claims and template examples distinct from verified facts; extract an asserted approval label without granting authenticated approval. Dependency edges retain site/process revision, source status, and spans; applicability decisions are owned by DB-032.

## From §3 "Phase 5 — generate site documentation and review change impact"

DB-025 as originally written. The change dossier and the approval/resume contract (`src/docbrain/workflows/change_review.py`) remain DocBrain's DB-025; the procedure-proposal and Documentation Agent parts belong here.

#### DB-025 — Propose evidence-backed procedures and implement approval/resume

- [ ] **Depends on:** DB-017, DB-021, DB-024. **Files:** `workflows/change_review.py`, approval API/registry migrations, prompts, workflow tests.
- Produce a change dossier and draft workflow through Clause → Concept/Requirement → Control → TaskStep dependencies, retaining audit source links. Use the exemption/review pathway as a first proposal: collect relevant facts/documents, determine applicable review route, identify missing rules/forms, and request human review. Separate legal recipient/deadline from internal owner/target, which may be unknown.
- Reuse this approval/resume contract for Documentation Agent packages in DB-033/DB-034; do not build a second review system. Decisions bind content and dependency hashes, designated site/process/compliance reviewer roles, and effective-date policy. Safety-critical content additionally needs competent technical review; unknown operating limits cannot be waived by a model. No arbitrary filesystem-write or self-approval tool.
- **Accept:** a proposed “check review eligibility” task cites 151–154 and does not offer internal review for a personal Minister decision. No invented business owner, fee, fixed retention period, or automatic filing. Authenticated reviewer approve/reject resumes after restart, rejects stale/replayed decisions, and records immutable proposal/decision versions. Approval updates DocBrain records only; no external regulatory or business-system action occurs.

#### DB-032 — Retrieve site-scoped evidence and assess applicability

- [ ] **Depends on:** DB-015, DB-021, DB-031. **Files:** `broker_fusion.py`, `models.py`, `registry.py`, `workflows/documentation.py`, applicability prompts/tests.
- Build a pinned documentation context containing regulatory, site/process, approved organizational, and template inputs in separate roles. Implement requirement/site applicability proposals with applicable/not-applicable/undetermined, reason, support, missing dependencies, and review status. Trace approved requirements → controls → process steps/document sections; distinguish absent evidence from a reasoned exclusion. Enforce site/source-status filters in every search, graph hop, source fetch, summary expansion, and cache key. Shared-source inclusion must be explicit; optional summaries are not a dependency.
- **Accept:** D02/D04/D10; a topic match to the Recycling Act is insufficient to apply export duties to Wodonga. Missing rules under s142 cannot yield a fixed period. Conflicting process limits remain visible; no score-based precedence. Cross-site matching names remain isolated, and approved organizational policy cannot masquerade as legislation. Applicability review reuses DB-025 when exposed to users, without requiring DB-025 to implement retrieval.

#### DB-033 — Implement the checkpointed Documentation Agent

- [ ] **Depends on:** DB-017, DB-025, DB-032. **Files:** `workflows/documentation.py`, `models.py`, `prompts/documentation/`, API/CLI handlers, document-generation tests.
- Implement authorize/pin → applicability/gaps → package outline → per-section retrieval/draft → verification → review. Generate policy, manual, and procedure documents; link optional work instructions/process maps/blank forms by stable IDs. Validate and version each template before use. Keep document-ID/role registers, coverage/evidence maps, gap lists, source/template/model fingerprints, and section checkpoints. Implement asynchronous document-package creation/status and CLI generate/inspect using shared jobs/cancellation, with bounded section count/tokens/repair attempts and a package-wide cost/time budget.
- **Accept:** D02/D03/D05/D09/D10; all three types are generated from a reviewed synthetic pack with correct cross-links and step/role consistency, while supplied incomplete plant examples remain visibly provisional and blocked from approval. Every substantive statement has source support or is labelled a proposed control; unsupported safety values fail validation. Template values cannot leak into site steps. Resuming an interrupted run preserves provenance without duplicate documents; cancelled jobs stay stopped unless an authorized new request explicitly continues their draft. Source text cannot modify tool permissions. No plant control actions, completed operational records, or claims of certified compliance.

#### DB-034 — Publish immutable reviewed document packages to assets/publish

- [ ] **Depends on:** DB-006, DB-013, DB-025, DB-033. **Files:** `documentation.py`, `adapters/artifacts.py`, `registry.py`, API/CLI export/download handlers, publication tests.
- Render Markdown packages into `assets/publish/<tenant-id>/<site-id>/<package-id>/<revision>/`, with policies/manuals/procedures and requested supporting directories, plus `manifest.json`, `evidence.json`, and `review.md`. Use server-issued safe identifiers, root/symlink containment, restricted permissions, and staging; never accept a model-provided output path. Bind approval to rendered content and dependency hashes. Draft exports are separately identified and not eligible for the current approved reference; approved publication rechecks reviewers, authorization, source revisions, unresolved blockers, and expected registry revision. Reconcile orphaned exports after crashes, retaining immutable prior revisions and user-owned files.
- **Accept:** D06/D07/D09; a reviewed synthetic package exports with resolvable internal links, evidence/approval provenance, and declared effective status. Replayed/concurrent requests produce one current complete package; interruption before/after artifact finalization cannot expose partial current output. Content edits require new approval, stale dependencies block publication, and path traversal/symlink escape fails. Draft-to-approved export must use distinct immutable export identity or revision, never overwrite a draft's bytes. Authorized downloads recheck source revocation; no automatic Git commit, public hosting, email, filing, or feedback ingestion.

#### DB-035 — Validate document quality and regenerate on source changes

- [ ] **Depends on:** DB-024, DB-031, DB-032, DB-033, DB-034. **Files:** `lifecycle.py`, `workflows/change_review.py`, `workflows/documentation.py`, `evals/documentation/`, integration tests.
- Extend dependency invalidation to law/permit, site/process, equipment, template, and reviewed organizational-source changes. Identify affected package sections, mark published output needs-review, propose a new revision with source/content diff, and preserve manually reviewed changes through explicit reconciliation rather than overwrite. Evaluate D01–D10 through the public API/CLI with a positive reviewed synthetic pack and negative supplied-draft cases; score coverage, faithfulness, unresolved issues, cross-document consistency, and site isolation separately. Report per-document/package latency and cost independently of Q&A.
- **Accept:** D05/D06/D08/D10; a process-only or site-role change identifies its actual dependent sections, while an unrelated site change does not invalidate the package. Both old/new source spans are inspectable; old exports are not silently mutated or served as current validated instructions. Reapproval is required after material updates. Safety-critical gaps, unsupported numeric/modality changes, unauthorized disclosure, and stale publication fail the gate even with valid citations. Corrected inputs must enable the positive case. Hosted-model runs use disposable services and explicit budgets; deterministic CI does not claim model quality.

## From §3 "Phase 6 — finish lifecycle, security, and operational gates" (documentation parts)

DB-026 originally also depended on DB-034 and DB-035, and DB-028 on DB-034.

#### DB-026 — Retention, erasure, invalidation, and reconciliation (as originally written)

- Extend MVP tombstones to dependency-aware graph/summary/cache/checkpoint and exported-package cleanup, legal holds, historical source access, and authorized erasure. Deny revoked source-derived package downloads and remove managed exports per policy; already distributed offline copies cannot be recalled automatically and require an operator withdrawal process. Keep per-stage cleanup status retryable; do not claim an atomic multi-store delete. Regenerate affected aggregates from permitted sources where appropriate.

#### DB-027 — Prove authorization across retrieval, source access, and review

- Include sites within the same tenant, package status/export/download operations, and source-to-output permission propagation. A generated manual's audience cannot exceed the permitted audience of its source evidence without an explicit reviewed release/redaction policy. Do not serve `assets/publish` as an unauthenticated static tree.

#### DB-029 — Instrument costs, quality, and capacity on the actual example (as originally written)

- Trace parse/import, embed, graph, summary, query, document section/package generation, corrective rounds, approval, and export under shared run/job IDs. Record pages, tokens, durations, cache reuse, retry count, and provider-reported cost where available; unknown prices remain unknown. Redact credentials and default to metadata-only traces. Separate document-job budgets from interactive Q&A latency targets.

#### DB-030 — Ship a reproducible staging and recovery procedure

- Include a synthetic approved document-package canary and recovery of its evidence map, pending review, export manifest, and current revision pointer. Document private export storage/permissions and offline document withdrawal; no production site files are committed or publicly hosted by this task.

## From §4 "Parallel work, missing inputs, and first delivery"

The first bullet moved whole. The other two bullets and the closing paragraph are shown as originally written; only their documentation and `assets/publish` sentences moved.

- **Documentation sequence:** DB-031 follows the Phase 1 import contracts before DB-012 payload indexing. After grounded retrieval, DB-032 assesses site applicability; DB-025's shared review contract and DB-032 enable DB-033 generation, then DB-034 export and DB-035 change/evaluation gates. First documentation demo: produce draft policy/manual/procedure with explicit gaps, then approve/export only the corrected reviewed synthetic fixture. Actual site rollout requires authoritative inputs and competent reviewers.
- **Later parallelism:** DB-019–DB-021 and DB-022 can proceed separately after their dependencies; DB-023 joins them. Documentation generation does not require DB-023. DB-024 requires real or clearly synthetic version pairs; DB-025 must preserve proposal/approval boundaries.
- **Available now:** one real raw PDF/JSON pair, its two Markdown candidates, six additional parsed Acts, and draft process/work-instruction/form examples under `assets/publish`. The examples are not verified approvals or technical/legal authority. No Docling comparison output, LiteParse run profile/native response, earlier legal version, scanned-file fixture, approved site/equipment/permit pack, applicable delegated rules, or model/parser/store credentials were validated in this work.

Supplied assets remain read-only inputs. No legal rates, site names, actors, section counts, operating limits, or expected answers belong as special cases in production code. Managed output is created only by the implemented, authorized documentation workflow, never by this planning task.
