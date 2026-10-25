# DocBrain coding backlog: regulatory knowledge and site documentation

Status: **planned, not implemented**. All 35 task checkboxes are open. This backlog turns the [implementation plan](./implementation_plan.md) into coding increments using supplied legislation and draft site-document examples. Synthetic fixtures are explicitly identified. No service writes, operational document generation, or application changes were made to create it. DB-001–DB-030 retain their IDs; DB-031–DB-035 add mixed-source ingestion and the Documentation Agent.

## 1. The example is a versioned legal document, not a text file

### Source inventory and evidence limits

| Artifact | Observed identity and use |
| --- | --- |
| [Raw PDF](../assets/raw/GLOBAL.AU/Recycling%20and%20Waste%20Reduction%20Act%202020/C2026C00317.pdf) | `C2026C00317`, compilation 3 of *Recycling and Waste Reduction Act 2020*, 1 July 2026; cover includes amendments by Act No. 68, 2025. 213 physical PDF pages. |
| [JSON sidecar](../assets/raw/GLOBAL.AU/Recycling%20and%20Waste%20Reduction%20Act%202020/C2026C00317.json) | Principal Act `C2020A00119`; `register_id=C2026C00317`; original Act date `2020-12-15`; version start `2026-07-01`; retrieval date `2026-10-11`; mutable `/latest/text` source URL. |
| [Existing Markdown](../assets/parsed/GLOBAL.AU/C2020A00119-recycling-and-waste-reduction-act-2020.md) | Front matter matches the JSON sidecar field-for-field. 5,639 lines; 188 section headings across five chapters; three HTML tables plus Markdown tables in the endnotes. No per-block PDF coordinates or parser lineage. |
| [LiteParse candidate](../assets/parsed/GLOBAL.AU/C2026C00317.md) | User-supplied LiteParse attribution; same claimed compilation. 7,122 lines (last line has no newline), 327,775 bytes, no YAML front matter or HTML tables; partial pipe tables, contents, running headers/footers, and page separators remain. Engine version, settings, runtime, and native responses were not supplied. |

PDF footer: **“Authorised Version C2026C00317 registered 21/07/2026”**. Keep registration date distinct from compilation date, original assent date, retrieval date, and system ingestion time. `last_amended` and `version_start` are supplied metadata; they do not establish that every individual provision commenced on that date. The first document-level as-of implementation must expose that limitation.

Fingerprints of the supplied bytes, for fixture registration rather than application special cases:

```text
PDF    998e9f4ed2390e3bd3f557552b405cbd1934198f5e4c3095649da45aa0c0b465
JSON   695bbe04269b42c36ca79bf086b14ec24c56c550ecdc1e604ff7689ac5ea42f2
MD     ee0aa90bcc0fc78800ad67f88c8201e640f6bbdef7b47edf6ccc7d15bf2f1949
LITE   b2700d01f4b586464ada341751f4404fc0eefac4881ac365bf9775117bc6cf7a
```

The PDF cover, structure, and provisions in the page table below were inspected. Markdown structure, HTML table item counts, metadata equality, and hashes were checked mechanically. **This is not a full PDF-to-Markdown equivalence audit**, and neither parser service was run. Both Markdown files are candidate comparison artifacts, not ground truth merely because they exist. Freeze reviewed spans in DB-003 before treating them as golden fixtures. `MD` above and the page-table Markdown locators below refer to the earlier structured Markdown; `LITE` identifies the supplied LiteParse export.

### LiteParse comparison: observed export defects, not an engine verdict

| Observed in the supplied LiteParse export | Coding requirement / comparison check |
| --- | --- |
| No YAML; cover names compilation 3 and 1 July 2026. Line 1 references absent `img_p1_1.png`. | Import using an explicit artifact/source association, reconcile cover facts with JSON, and retain unknown parser profile. Report the missing image without fetching it or rejecting all readable text. Do not claim the missing image is irrelevant without review. |
| 449 Markdown headings, 212 standalone `-----` separators, 210 compilation-date footer occurrences. Body sections generally use `#####`; repeated running headers also use heading syntax. | Separate contents and page furniture from body hierarchy; heading counts are not section counts and separators are not reliable physical-page IDs. Preserve original spans when removing furniture from normalized text. |
| Section 2, lines 481–519: column 1, subsection (2), column 2, and column 3 are interleaved. | Preserve commencement rule, date, and the column-3 exclusion as distinct, correctly associated evidence; a text-presence check alone cannot pass E02. |
| Sections 20/22, lines 1121–1206, and 142, lines 5346–5383: subsection numbers, labels, and penalties sometimes run together; page furniture interrupts clauses. | Recover numbering and offence/civil/exception scope independently of line starts; verify E03/E04/E10/E11 and include control text containing cross-references that must not start new subsections. |
| Section 151, lines 5692–5919: person and decision columns become detached; rows 17–22 have empty person cells followed by prose; item 7/14/22 continuations cross page boundaries. | Check every reviewed item/person/decision association across physical pages 175–178. Detect unresolved alignment, preserve source fragments, and quarantine affected relationships. Do not infer pairings merely by zipping extracted column lists. |
| Sections 153/154, lines 5922–5956: personal-decision exclusion, 30-day trigger, extension, and tribunal route remain visible, but several subsection starts are inline. | Verify clause boundaries and qualifiers through E08/E09, not a bag of retained keywords. |

The earlier Markdown has explicit HTML structure for sections 2, 106, and 151; the LiteParse export has no HTML tables. This difference supports table-focused comparison, not a claim that all LiteParse text is missing or that the earlier Markdown is legally complete. Compare immutable inputs against the same PDF-reviewed expectations, keep candidate results separate, and record every correction as a new derived artifact with reviewed lineage. Docling output is not yet available for comparison. Runtime/cost and native-coordinate claims require a reproducible parser run in DB-008.

### Concrete structure the implementation must preserve

| Finding | Why a generic text splitter or answer generator is insufficient |
| --- | --- |
| Act ID differs from compilation ID | Register the PDF and Markdown under the same logical Act and claimed compilation, with separate artifact provenance; do not create two unrelated documents or claim the Markdown was generated by the new parser. |
| Cover, compilation notes, contents, body, endnotes | Contents entries and running `Section 20` headers must not become duplicate substantive provisions. Endnotes remain available for history questions. |
| Physical versus printed pages | Cover/front matter occupy PDF pages 1–12; body starts at physical page 13, printed page 1. Store both labels. The observed offset is not a global parser rule. |
| Heading levels skip directly to `######` sections | Build Chapter → Part → Division → Subdivision → Section ancestry from available levels; do not invent missing levels. Section 76 has all five levels; section 171 belongs directly to Chapter 5. |
| Sections `65`, `65A`, `65B`, `66` | Preserve alphanumeric identifiers and document order. Numeric-only extraction loses two current sections. |
| Sections 122 and 187 are absent from the body | Endnote 4 records repeal by No. 68, 2025. Distinguish repeal evidence from a parser omission; do not reconstruct missing historical wording. |
| Subsection/paragraph/subparagraph and unnumbered labels | `20(1)(b)`, `18(2)(a)(i)`, “Fault-based offence”, “Civil penalty provision”, “Exception”, and trailing penalty blocks have different roles. Labels and penalties inherit the correct provision context. |
| Mixed HTML and Markdown tables | Section 2 has a spanning title and multiple header rows; section 106 has eight data items with inline lists; section 151 has 28 data items. `colspan`, `<br>`, italics, and repeated PDF headers carry structure. |
| Definition scope and references | Section 10 defines `CEO` by reference to another Act; section 172(5) defines `relevant person` locally. Do not use an unrelated global definition or invent the contents of an unavailable Act. |
| Rule-making powers versus operative duties | Sections 17, 18, 77 and 142 depend on rules. “Rules may prescribe” is not proof that every exporter has a particular obligation or that a particular retention period exists. |
| Nearly identical offence text | Sections 21/23 use knowing conduct with 5 years/300 units and civil 600; sections 22/24 use reckless conduct with 3 years/180 units and civil 360. Word-overlap deduplication must not collapse them. |
| Time, units, alternatives, exceptions | Twelve months is a maximum exemption duration, fourteen days in section 76 is a minimum notice interval, thirty days in section 153 has a trigger and extension, and “as soon as practicable” is not a fixed number of days. |

### Inspected PDF page anchors

Physical page numbers below are **1-based**. Printed labels are source text. Convert explicitly if a parser uses zero-based indices.

| Evidence | Physical PDF page(s) | Printed page(s) | Markdown locator at inspected revision |
| --- | --- | --- | --- |
| Section 2, commencement table and column-3 exclusion | 13 | 1 | Lines 73–101 |
| Section 20(2)–(4), criminal/civil penalties and limited strict liability | 31 | 19 | Lines 608–637 |
| Section 22, reckless conduct and exception | 33–34 | 21–22 | Lines 674–709 |
| Section 26(4), exemption event/period limit | 38 | 26 | Lines 790–821 |
| Section 142, records and penalties | 163–164 | 151–152 | Lines 4245–4296 |
| Section 151, reviewable-decision table | 175–178 | 163–166 | Lines 4565–4727 |
| Section 153, internal review | 179 | 167 | Lines 4738–4759 |
| Section 154, tribunal review | 180 | 168 | Lines 4760–4771 |
| Endnote 4, repeal of section 122 / section 187 | 211 / 213 | 199 / 201 | Rows labelled `s 122` / `s 187`, after line 5479 |

Section 151's PDF table continues across four pages: items 1–7, 8–14, 15–22, and 23–28 respectively. These boundaries are useful parser fixtures, not rules to hard-code into ingestion.

## 2. Source-driven acceptance scenarios

These are proposed checks of behavior, not certified legal advice or an already executed evaluation suite. Exact expected wording need not match; conditions, numbers, provenance, and uncertainty must. PDF-confirmed page anchors are listed above; the additional cases are grounded in inspected Markdown and need PDF span review in DB-003.

| Case | Request or input | Expected observable result / plausible wrong answer to reject |
| --- | --- | --- |
| E01 | Import PDF+JSON, earlier Markdown, and LiteParse Markdown, then repeat | One logical Act, one claimed official compilation, separate artifact/derivation records and candidate builds; identical re-import does not create a new logical build. Do not merge candidates' chunks, count them as independent corroboration, or automatically attribute PDF coordinates to Markdown. |
| E02 | “When did this Act originally commence?” | Section 2 table says the day after Royal Assent; column 3 gives 16 December 2020. Explain column 3 is not part of the Act under 2(2). Do not substitute the 2026 compilation date. |
| E03 | “What are the section 20 penalties?” | Section 20(2): imprisonment for 5 years or 300 penalty units, or both; 20(4): civil 600 units. Keep categories separate and avoid unsupported dollar conversion. Strict liability under 20(3) attaches only to 20(1)(b),(c). |
| E04 | “Compare knowing and reckless false representations on export entry.” | Sections 21 and 22 remain distinct: 5 years/300/civil 600 versus 3 years/180/civil 360. Include the material-particular exception in subsection (5) of each. Do not fuse the near-duplicate passages into one penalty. |
| E05 | “Does an exemption always last twelve months?” | No: 26(4) caps the specified event/period; 29(1) ends it at the earliest applicable event, period, rules period, or revocation. Do not turn a maximum into a guaranteed term or twelve months into a fixed day count. |
| E06 | “What do I need to apply for an exemption?” | Retrieve 25 and 172 together, plus relevant 173–174 qualifications: who applies, recipient, approved manner/form if applicable, rules-required information/documents, fee condition/waiver. Missing rules/forms are disclosed; no invented fee or universal form. |
| E07 | “Who is affected by refusal of an exemption?” | Section 151(1), item 1 pairs the section-25 applicant with refusal under 26(1)(b); include both cells and row identity. Do not pair that applicant with item 2's licence decision. |
| E08 | “How long do I have for internal review?” | 153(2): 30 days after the decision first came to the applicant's notice, or a further period allowed by the reviewer. Include 153(1)'s personal-decision exclusion. Not 30 days after the decision was made, and not an absolute unextendable deadline. |
| E09 | “The Minister personally refused my exemption. Is internal review available under section 153?” | Explain the personal-decision exclusion and the section-154 tribunal route for affected persons, with 151 item 1 as needed. Do not give a tribunal filing deadline absent from these provisions. |
| E10 | “How many years does section 142 require export records to be kept?” | Explain that rules determine the period under 142(2)(c), and the period is not supplied by this Act alone. Return a supported partial answer plus missing-rule dependency, not a guessed seven years or empty generic refusal. |
| E11 | “What are the section 142 non-compliance penalties?” | Subject to a requirement under the rules and non-compliance under 142(3): strict-liability offence 60 penalty units, civil 250. Do not substitute section 20's penalties. |
| E12 | “How quickly must an export licence holder report a changed address?” | Section 61(1)(d): notify CEO in writing as soon as practicable. Preserve this qualitative deadline; do not borrow section 76's fourteen days. |
| E13 | “Does section 76 give everyone fourteen days before membership is required?” | No blanket grace period: 76(1) states membership duty; 76(4)–(5) limit applying for a civil penalty order by requiring notice/non-compliance and a specified day at least fourteen days later. Applicability also depends on 77. |
| E14 | “Who publishes the quarterly exemption and licence reports?” | Distinguish 65A Minister/exemptions/Department website from 65B CEO/licences/NEPA website, retain section 65 disclosure restrictions, and cite the two distinct sections. |
| E15 | “What is the current wording of section 122?” | No operative body text for section 122 in this compilation; endnote 4 records repeal. Do not answer with section 123 or invent the earlier text. Same control case for section 187. |
| E16 | “What applied on 30 June 2026?” with only this compilation available | Disclose the lack of a suitable earlier version. Do not silently apply the 1 July 2026 compilation or infer historical wording from amendment-history labels. |
| E17 | “Does the Act require every exporter to obtain a licence?” | Explain rule-dependent conditions under 17–18 and applicable exemptions under 25–32; do not assert universal applicability or decide a business's compliance without its facts and applicable rules. |
| E18 | “Summarize export controls and product stewardship.” | Cover Chapter 2 and all three Chapter 3 regimes (voluntary, co-regulatory, mandatory), with grounded source coverage. Chapter 1's simplified outline alone is insufficient support for detailed obligations. |
| E19 | Query `s 65B`, `section 65b`, or `65B(5)` | Same canonical section lookup within the selected Act/version; never section 65 or 65A. `s 1` must not prefix-match 10 or 151. |
| E20 | “What does the CEO definition say?” | Section 10 refers to the *National Environmental Protection Agency Act 2025*, with a note identifying NEPA's CEO. Return the cross-reference and source note; do not fabricate the external Act's definition. |

Use these as visible development cases. DB-018 adds separate held-out questions and variations; a system that memorizes these questions has not met the quality gate. Do not assert actual legal applicability, penalty-dollar values, or specific business status from this example alone.

### Documentation examples and acceptance scenarios

The supplied [P-001 Thermolysis Pot Cycle](../assets/publish/processes/p01-high-level-process.md) is labelled **Draft for approval** and refers to Wodonga. It contains source process steps in Appendix A, an H4 reprocessing path distinct from H1–H3, `torque x`, `[TBC]` values, and references to permits/manufacturer instructions. [WI-007 Emergency Shutdown](../assets/publish/work-instructions/w07-emergency-shutdown.md) is also a draft, with unresolved assembly location, alarm limits, and source references. These are evidence of what the supplied documents say, not verification of plant facts, safe instructions, legal applicability, or approval.

The [process template](../assets/publish/processes/p00-process-template.md) and [work-instruction template](../assets/publish/work-instructions/w00-work-instruction-template.md) contain illustrative values (including contamination <1%, 0 PSI, and 5°C/min); they must not become site limits. The [form template](../assets/publish/forms/f00-form-template.md) is empty. Some links point to missing manuals/regulations. Do not fix or replace these source assets during implementation: register immutable copies, review provenance, and expose gaps. Approved site profiles, technical limits, permits, and policy/manual templates remain inputs to obtain; use clearly synthetic approved fixtures for positive-path tests meanwhile.

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

## 3. Coding sequence and completion rules

All paths below refer to the target `src/docbrain/` package unless prefixed otherwise. Reuse the current modules through the migration map in [project structure](./project_structure.md). Tests target public contracts/results rather than private helper calls. Keep constants such as 188 sections, 28 items, and source hashes in fixture expectations, never application branches.

| Plan phase | Tasks | Deliverable |
| --- | --- | --- |
| 0 — foundation | DB-001–DB-003 | Importable package, compatibility checks, reviewed source fixtures |
| 1 — source/ingestion | DB-004–DB-011, DB-031 | Versioned artifacts, mixed source roles/site scope, structure, references, chunking, durable jobs |
| 2 — cited Q&A | DB-012–DB-018 | Published Qdrant builds, evidence, bounded answers, API/CLI, MVP evaluation |
| 3 — graph | DB-019–DB-021 | Regulatory assertions, Memgraph persistence, grounded graph retrieval |
| 4 — summaries | DB-022–DB-023 | Document/corpus summaries and optional communities |
| 5 — documentation/impact/review | DB-024–DB-025, DB-032–DB-035 | Applicability, policy/manual/procedure generation, review, controlled export, and change impact |
| 6 — lifecycle/security/release | DB-026–DB-030 | Retention, adversarial checks, resource controls, restore/release gates |

Implement trusted scope checks with the first retrieval/storage interfaces; DB-027 is the comprehensive adversarial gate, not the first authorization work. Likewise, DB-026 extends the MVP's basic tombstone behavior rather than deferring deletion correctness until the end.

The first end-to-end demo is **E10**: ingest the Act, retrieve 142(2)(c), cite the exact source, and explain why a number of years cannot be supplied. This exercises ingestion, provenance, retrieval, qualified answers, and missing dependencies without needing a graph or an invented regulation.

### Phase 0 — establish an executable baseline

#### DB-001 — Package and characterize the prototype

- [ ] **Depends on:** none. **Files:** `pyproject.toml`, lockfile, `src/docbrain/`, `tests/unit/`, CI configuration.
- Move current public components into an installable package in a behavior-preserving step; repair import/type errors and retain supported imports deliberately. Add offline test, lint, and type-check commands. Add secret exclusions before creating local configuration.
- **Accept:** clean-environment install/import succeeds; pure chunk identity and asymmetric weighted-RRF examples have independently computed expected outputs; no hosted credentials are needed for offline tests. Record prototype limitations instead of changing algorithms during the move.

#### DB-002 — Settings, external contracts, and capability diagnostics

- [ ] **Depends on:** DB-001. **Files:** `settings.py`, adapter protocol definitions beside their consumers, `adapters/models.py`, `cli.py`, `tests/contracts/`.
- Validate endpoints, secret references, namespace, role aliases, embedding profile, parser protocol, and required/optional capabilities. Implement `doctor`: read-only by default, explicit disposable-namespace write probes. Probe LiteLLM structured output and embeddings; Qdrant dense/sparse/filters; Memgraph Bolt and procedure inventory; PostgreSQL/checkpointer compatibility. Parser jobs may be asynchronous; capabilities must describe the supplied wrapper rather than assume a universal REST API.
- **Accept:** unavailable graph capability does not prevent a declared vector-only profile; missing required gateway credentials does. Embedding dimension/profile mismatch fails before writes. No probe modifies a production namespace or logs secrets. Report exact tested service/client versions and blocked checks.

#### DB-003 — Freeze reviewed example fixtures and source locators

- [ ] **Depends on:** DB-001. **Files:** `tests/fixtures/recycling_act/`, `evals/recycling_act/`, fixture inventory documentation.
- Register all four supplied hashes, identities, metadata, and source locations. Review the page-table spans and E01–E20 expectations against the PDF; add compact licensed excerpts and expected structural/semantic output. Preserve both Markdown candidates unchanged, including LiteParse's detached table fragments, inline subsection starts, page furniture, and missing image reference. Store coordinates from actual extraction, not manual global page arithmetic.
- **Accept:** fixture checks verify hashes and explicit expected clause/table relationships, including all 28 section-151 item/person/decision tuples reviewed independently of either candidate. Record candidate versus reviewed status and reviewer provenance; LiteParse attribution does not imply known version/options or an executed benchmark. Missing raw fixtures for scanned PDFs, DOCX/HTML, malformed files, and actual earlier compilations remain visible gaps; synthetic variants are labelled synthetic and never replace the original assets.

### Phase 1 — ingest source structure without changing its meaning

#### DB-004 — Define immutable identity, legal-time, and provenance contracts

- [ ] **Depends on:** DB-001, DB-003. **Files:** `models.py`, `tests/unit/`.
- Add logical document, official version, artifact, parse/build, block, source span, reference, evidence, and scope models. For the example, namespace `C2020A00119` by tenant/authority and associate official compilation `C2026C00317`; readable examples may look like `au:C2020A00119/C2026C00317/s153(2)(b)`. Actual chunk IDs also include build identity. Define UUID point mapping independently of display IDs.
- Record source-effective, compilation, registration, retrieval, and observed timestamps separately; allow unknown interval ends. Support multiple spans per evidence item, physical page index, printed page label, coordinate system, and immutable text-artifact offsets. References may be resolved, external-unavailable, ambiguous, or explicitly repealed.
- **Accept:** E01/E16; moving/renaming the raw folder leaves document identity intact; altered source bytes create a new artifact and conflicting claims about one official source require review. Different parser renderings are distinct derivations of the same claimed official version, not by themselves conflicting legal versions. `65A`, `65B`, and two tenants' section 153 IDs never collide. Validate source span boundaries against their artifact, not normalized text.

#### DB-005 — Import and reconcile legislation metadata

- [ ] **Depends on:** DB-004. **Files:** `parsing.py`, `registry.py`, metadata tests.
- Read the sibling JSON and Markdown YAML safely; validate scalar types and field meanings. Accept metadata-less LiteParse Markdown with an explicit manifest linking its checksum to the raw PDF/JSON and claimed version; do not search by basename and silently attach a sidecar. Preserve provider metadata separately from verified cover/footer facts. Support spaces in paths. Treat `/latest/text` as a source alias, not an immutable version identity or permission to fetch current content.
- **Accept:** supplied JSON/front matter and LiteParse cover facts reconcile without conflict; intentionally changed `register_id`, compilation date, or title produces a reviewable conflict, not silent precedence. An unassociated metadata-less import remains unresolved rather than acquiring identity from its filename. `2020-12-15`, `2026-07-01`, `2026-07-21`, and `2026-10-11` keep distinct meanings. Importing either Markdown does not assert a verified parser run or fabricate per-page spans.

#### DB-006 — Store immutable source and derived artifacts

- [ ] **Depends on:** DB-004, DB-005. **Files:** `adapters/artifacts.py`, `registry.py`, storage migrations, adapter tests.
- Save original bytes, sidecars, parser responses, canonical text, and corrections with checksums and lineage. Start with a local adapter and the supplied hosted storage backend when known. Keep large artifacts outside workflow checkpoints; create safe, scoped source references rather than arbitrary local paths.
- **Accept:** duplicate bytes reuse content storage without merging tenant permissions; a corrected Markdown revision retains the original and its diff. Retrieved excerpts match immutable text spans byte/text-for-text under the documented encoding. Path traversal and unauthorized artifact reads fail before content is returned.

#### DB-007 — Parse the supplied mixed Markdown into canonical blocks

- [ ] **Depends on:** DB-004, DB-005, DB-006. **Files:** `parsing.py`, focused parser tests.
- Implement a real Markdown/HTML parsing path for both candidates, preserving headings, inline definitions, lists, HTML/pipe tables, and source offsets. Separate compilation notes/contents/body/endnotes and retain page furniture as source metadata rather than substantive provisions. Preserve legal numbering independent of Markdown depth or line starts; retain unnumbered offence/exception labels within their section. Keep mappings from normalized blocks to original artifact spans even when removing repeated furniture or joining lines. Record unresolved structure rather than inventing it.
- **Accept:** earlier structured Markdown yields five chapters and 188 section nodes, including 65A/65B and no operative 122/187 nodes; compare the LiteParse tree against those independently reviewed identifiers and report omissions/duplicates. A second synthetic fixture with different counts still parses. Section 76's full ancestry and section 171's shorter ancestry are correct. LiteParse's inline `142(2)`/`153(2)` are distinct from preceding paragraphs; references such as `subsection (1)` do not become new clauses. `20(1)(a)` and `21(1)(a)` remain distinct; CRLF and Unicode non-breaking hyphens do not break lookup or source spans. The missing image produces a warning without an implicit fetch; page separators alone never establish PDF coordinates.

#### DB-008 — Compare supplied candidates, benchmark parsers, and implement the chosen adapter

- [ ] **Depends on:** DB-002, DB-003, DB-004, DB-006, DB-009. **Files:** `adapters/parser.py`, `parsing.py`, `tests/contracts/`, parser evaluation runner.
- First run an offline comparison of both supplied Markdown candidates against DB-003's reviewed expectations, with per-case mismatches and unresolved spans. This substep needs no service access. Then submit the same raw PDF to available LiteParse/Docling services using their actual contracts, persist native responses and export transformations, and normalize into DB-007's blocks. Record engine/wrapper versions, settings, source hashes, and separate extraction/normalization timings. Compare reading order, clause coverage, table associations, source positions, latency, and cost; mark unavailable measurements as unknown, not zero. Select a primary parser on measured results; do not build an automatic fallback without a demonstrated failure class.
- **Accept:** distinguish physical page 13 from printed page 1; prevent contents/running headers from duplicating section 20; correctly cite page-spanning section 22. A passing parser preserves all 28 section-151 item/person/decision associations across four PDF pages, including boundaries 7/8, 14/15, and 22/23, using DB-009's contract. Counting 28 item numbers is insufficient. The supplied LiteParse export must expose its unresolved alignments rather than pass through guessed repairs. Also check section 2's column-3 exclusion and sections 20/22/142/153 qualifiers. Compare against independently reviewed PDF spans, not complete equality with either Markdown. Bound job polling/retry/cancellation and expose unsupported formats. Record offline results separately if hosted runs are blocked; that does not close the adapter task. PDF failure leaves the qualified Markdown-only path usable with its weaker provenance explicitly stated.

#### DB-009 — Preserve table semantics and source classifications

- [ ] **Depends on:** DB-003, DB-007. **Files:** `parsing.py`, table fixtures/tests.
- Define canonical cells, header relationships, row keys, spanning cells, per-cell provenance, and explicit unresolved table fragments; implement the supplied HTML/Markdown tables first. DB-008 maps PDF continuations to this contract and must stitch them only with structural evidence. Detached columns, blank cells followed by prose, and interrupted rows must not be silently zipped or filled from another candidate. Re-extraction or human correction creates a new derived artifact with supporting source spans and review provenance. Keep classifications for body provisions, definitions, notes, simplified outlines, compilation information, and amendment history; do not assume every table or explanatory-looking block is normative law.
- **Accept:** section 151 retains exactly 28 correctly associated item records in the earlier structured Markdown; item 13's multi-person list stays in its own cell. Section 106 retains eight items and their conditional grounds. Section 2 separates the operative commencement rule from column 3's explicitly non-Act information (E02/E07). LiteParse's unresolved section-151 fragments are visible in source inspection but excluded from table-derived answer/graph evidence; section 2's interleaved text cannot pass solely because all words are present. Include a synthetic misordered-column case where naive positional pairing gives the wrong person/decision result. Endnote abbreviation-table line wrapping does not create fake obligations. This task can close without a parser endpoint; PDF continuation parity is a separate DB-008 gate.

#### DB-010 — Resolve clause references and scoped definitions

- [ ] **Depends on:** DB-004, DB-007, DB-009. **Files:** `parsing.py` or a cohesive `references.py` module, reference tests.
- Extract section/subsection/paragraph/item references with the owning Act/version and local context; resolve `subsection (1)` locally and distinguish external Acts. Index dictionary aliases and section-local definitions. Preserve AND/OR, inclusive item ranges, “except”, and “earliest of” rather than flattening them to unrelated sentences.
- **Accept:** section 25's note links to 172–174; section 153 resolves table-item ranges 1/11–13 versus 2–10/14–28; 172(5)'s `relevant person` does not inherit an audit definition. `CEO` exposes an unavailable external dependency (E20); 122/187 references can point to repeal history without invented body text. Ambiguous or apparently inconsistent references produce warnings, not silent correction. E06/E07/E09 can retrieve support through references before a graph database exists.

#### DB-011 — Clause-aware chunking and resumable ingestion jobs

- [ ] **Depends on:** DB-002, DB-006, DB-007, DB-010. **Files:** `chunking.py`, `registry.py`, `worker.py`, `workflows/ingestion.py`, PostgreSQL migrations, job tests.
- Create evidence-sized chunks with structural IDs, verbatim spans, optional faithful normalized text, and links to parent/exception/penalty/table context. Split oversized sections/tables without losing header/condition context. Persist job stages, leases, heartbeat, attempt budgets, cancellation, and output references using the registry and LangGraph checkpoints; make replayed stages idempotent.
- **Accept:** subsection 22(5)'s exception remains retrievable with 22(1)–(4); a section-151 row can be retrieved with its headers; no chunk is just `Civil penalty: 600 penalty units` without its owning provision. Interrupt after parsing and resume without another logical build or lost artifact. A cancelled/expired worker cannot publish. Chunk IDs change when chunking/profile changes, while source identity does not; content reuse retains new version-specific provenance.

#### DB-031 — Register mixed knowledge sources and site/process context

- [ ] **Depends on:** DB-003, DB-004, DB-005, DB-006, DB-007. **Files:** `models.py`, `parsing.py`, `registry.py`, source metadata migrations, `tests/fixtures/documentation/`.
- Add source role, authority subtype, tenant/site/process scope, owner, revision/effective dates, claimed versus verified approval state, and derivative lineage. Register non-legislation documents without fabricated Act IDs. Explicitly register existing publish examples as draft reference inputs; exclude automatic output-directory ingestion. Preserve template placeholders and empty/missing references as validation findings. Freeze relevant P-001/WI-007/template excerpts with hashes and create two labelled synthetic site packs, with reviewed positive inputs and asymmetric roles/equipment/limits.
- **Accept:** D01/D03/D04/D09; draft approval labels do not confer permissions; missing site scope is unresolved, not shared. Shared corporate policy requires explicit authorization. Importing a generated derivative retains original lineage; moving a file does not change site identity. No supplied asset is altered. Legal and process evidence remain distinguishable after parse/chunk; expected template structure comes from reviewed requirements rather than treating the empty form template as valid.

### Phase 2 — build the first cited Q&A release

#### DB-012 — Embed and persist versioned Qdrant points

- [ ] **Depends on:** DB-002, DB-004, DB-011, DB-031. **Files:** `adapters/models.py`, `adapters/vector.py`, explicit Qdrant migrations, adapter tests.
- Batch dense and pinned sparse embeddings; cache by scoped content/profile; use named vectors and deterministic UUID point IDs. Index document/version/build, tenant/site/process/access partition, source role/review status, clause or section key, and artifact references. Official Act identifiers are optional for non-legal sources. Support ID fetch and complete paginated scans. Collection creation/migration is explicit, not a side effect of answering.
- **Accept:** re-upload does not duplicate points; `s65B` exact lookup resolves the right payload; a profile dimension mismatch fails before writes; synthetic data exceeding one scroll page are all visited. Query/document sparse profiles agree and IDF is applied once. Unauthorized payloads cannot be retrieved by guessing a UUID. Verify against actual disposable Qdrant, not only mocks.

#### DB-013 — Publish snapshots and reconcile interrupted builds

- [ ] **Depends on:** DB-011, DB-012. **Files:** `registry.py`, `lifecycle.py`, manifest migrations, integration tests.
- Validate required stage outputs and provenance, then atomically publish an immutable manifest in PostgreSQL. Pin a manifest on reads and enforce selected build IDs in every search/fetch. Add minimal tombstoning and revision-scoped cache invalidation for the MVP; preserve historical evidence according to policy.
- **Accept:** crash after some Qdrant writes leaves the old published snapshot visible; restart/reconcile completes or cleans the new staging build. Competing publishers cannot overwrite each other's selected document versions. A synthetic changed version never changes old citation text. A tombstoned/revoked document is denied at final delivery despite an older pinned snapshot; rollback cannot restore forbidden access.

#### DB-014 — Retrieve exact clauses and hybrid candidates with context

- [ ] **Depends on:** DB-010, DB-012, DB-013. **Files:** `router.py`, `broker_fusion.py`, retrieval tests.
- Parse explicit Act/section references into exact filters; combine dense/sparse retrieval and reference/context expansion under identical authorization/version filters. Handle mixed questions rather than first-keyword-wins routing. Distinguish an absent section, explicitly repealed section, unavailable rule, and unavailable historical version.
- **Accept:** E03/E07/E10/E15/E16/E19 retrieve the right source/type or explain absence. E06 reaches application requirements rather than only section 25. E09 includes the personal-decision exception and tribunal provision. Case/punctuation normalization may aid search but must not modify verbatim source text or cause section-prefix collisions.

#### DB-015 — Fuse, rerank, and build evidence without erasing distinctions

- [ ] **Depends on:** DB-014. **Files:** `broker_fusion.py`, `models.py`, evidence tests.
- Normalize provider results, merge canonical identities with contribution metadata, use weighted RRF, and optionally rerank with declared score semantics. Deduplicate exact/context overlap conservatively; preserve differences in actor, mental state, modality, amount, and exception. Count tokens with an explicit profile and reserve room for required qualifying context.
- **Accept:** E04 retains both knowing/reckless offence evidence despite high word overlap. A small budget yields an explicit incomplete/insufficient result instead of a penalty-only answer missing its exception. Asymmetric rank lists produce independently calculated order; repeated requests do not accumulate mutated store-contribution metadata. Every evidence item has authorized versioned support; no normalized RRF score is labelled a truth probability.

#### DB-016 — Implement bounded LangGraph answering and verification

- [ ] **Depends on:** DB-002, DB-015. **Files:** `workflows/answering.py`, `prompts/`, answer models/tests.
- Implement authorize/pin → retrieve → assess missing facets → synthesize → verify with at most two corrective rounds and one repair round, plus no-progress/deadline/cost stops. Generate claim-level citations and structured missing-dependency warnings. Verify citation/span existence and numeric/modality consistency; keep semantic support assessment distinct from those mechanical checks.
- **Accept:** E10 returns a supported explanation and missing-rule warning, not a fixed retention period; E08 includes trigger/extension/exclusion; E03 does not invent a dollar amount. Missing evidence produces `partial`/`insufficient_evidence`, and citation fabrication triggers repair or abstention. Progress can stream, but an unchecked answer is not emitted as verified. No automatic external search or database-write tools.

#### DB-017 — Expose the vertical slice through API and CLI

- [ ] **Depends on:** DB-011, DB-013, DB-016. **Files:** `api.py`, `cli.py`, transport tests.
- Implement the plan's ingestion/job/cancel, evidence-query, answer, source-inspection, and health endpoints with shared application functions. Bind trusted tenant/scope to every call; support explicit local development identity but reject that mode in shared deployment. Use opaque or correctly encoded source IDs in URLs; `#` in a readable clause ID must not become a browser fragment.
- **Accept:** ingest the supplied PDF+JSON or imported Markdown, poll the job, ask E10, and open the exact authorized source. Invalid budget/scope, unknown version, cancelled job, and unavailable dependency have typed responses. Source inspection reports physical and printed pages only when known. API/CLI produce equivalent evidence identities without maintaining two pipelines.

#### DB-018 — Establish the MVP regression and evaluation gate

- [ ] **Depends on:** DB-003, DB-017. **Files:** `evals/recycling_act/`, evaluation runner, `tests/integration/`, CI jobs.
- Convert reviewed E-cases into structured expectations (required support, must-have qualifiers, forbidden claims), then add held-out paraphrases/unanswerable questions and the other six Markdown documents. Run the same expectations against isolated builds for each Recycling Act candidate, with the same retrieval/model settings; never combine both as independent supporting sources. Report parse/association defects separately from retrieval, citation, claim-support, abstention, latency, and usage metrics. Offline regressions use controlled dependencies; budgeted hosted-model evaluation is explicit.
- **Accept:** baseline E10 demo works against real disposable services; failures such as `142 = seven years`, `153 = thirty days from decision date`, or collapsed E04 penalties fail the gate even if citation strings are present. E16 is not “answered” from the wrong version. Add table-dependent questions spanning section-151 page boundaries: an unresolved candidate must explain missing reliable table evidence rather than guess, while the reviewed build must answer the correct associations. Such safe abstention passes the safety check, not the full-document coverage gate; report excluded evidence and lost coverage. Enforce plan thresholds only on eligible query classes and reviewed fixtures; this single Act cannot validate genuine corpus-wide or multi-version reasoning.

### Phase 3 — add grounded Memgraph relationships

#### DB-019 — Extract typed legal assertions, not generic entities

- [ ] **Depends on:** DB-002, DB-010, DB-011, DB-018. **Files:** `graph_engine.py`, `models.py`, extraction prompts/tests.
- Replace generic fallback ontology behavior with typed actors, provisions, concepts, requirements, rule dependencies, permissions/powers, exceptions, and sanctions. Carry condition expressions, qualitative/quantitative time, trigger, units, and exact support. Unknown types or ungrounded values go to review, not default `Organization`/`PARTNERS_WITH` objects.
- Extend extraction to site/process facts, equipment, approved organizational controls, and document-section dependencies using DB-031 source roles. Keep draft claims and template examples distinct from verified facts; extract an asserted approval label without granting authenticated approval. Dependency edges retain site/process revision, source status, and spans; applicability decisions are owned by DB-032.
- **Accept:** E03/E04 preserve criminal/civil categories, knowing/reckless states, and limited strict-liability scope. E05 encodes a maximum plus earliest-ending conditions, not a guaranteed duration; E13 records a minimum notice interval rather than a delayed membership duty. E12 remains qualitative. `Minister`, `CEO`, exporter, licence holder, and applicant are not merged by co-occurrence. E10 creates a missing-rule dependency, not a retention requirement with an invented value.

#### DB-020 — Persist versioned assertions in Memgraph

- [ ] **Depends on:** DB-002, DB-013, DB-019. **Files:** `adapters/graph.py`, `graph_engine.py`, Memgraph migrations, contract tests.
- Implement parameterized bounded writes/reads using tested Memgraph syntax. Separate stable identities from immutable assertion/evidence versions, including edge evidence and review state. Graph build readiness participates in manifest publication when the graph profile is required. No APOC/GDS dependency or automatic privileged migrations.
- **Accept:** replaying extraction changes neither relationship multiplicity nor weights; unchanged aliases cannot overwrite reviewed descriptions/history. Same-name actors across tenants stay isolated. Incomplete graph writes stay invisible; a selected vector-only build advertises missing graph capability. Run actual Memgraph transaction, uniqueness, and filter tests in a disposable namespace.

#### DB-021 — Ground graph paths back to source evidence

- [ ] **Depends on:** DB-015, DB-020. **Files:** `graph_engine.py`, `broker_fusion.py`, graph retrieval tests.
- Add named traversal tools such as `trace_review_route` and general bounded reference/requirement traversal, with parameter schemas and approved relation types. Fetch supporting chunks for every asserted edge before answer synthesis. Keep deterministic citation/reference expansion available when graph service is optional or down.
- **Accept:** E09 follows application/refusal → section 151 item 1 → section 153 exception → section 154 and returns supporting spans. Injecting a forbidden intermediate edge/node cannot produce a path or leak its description. `s10 → external Act` is an unresolved reference if the target is absent, not an invented cross-document fact. Test a real cross-document example from the remaining corpus separately; one Act alone is insufficient proof of that feature.

### Phase 4 — add summaries only after the baseline is measurable

#### DB-022 — Build grounded section/chapter summaries

- [ ] **Depends on:** DB-013, DB-015, DB-018. **Files:** `semantic_tree.py`, summary prompts, semantic collection migration/tests.
- Start from the Act's document hierarchy, then evaluate semantic clustering rather than requiring every document to have a fixed number of levels. Store complete parent/child/leaf links and scope/build dependencies; summary prose is derived evidence, not a verbatim quote. Return to leaf passages for exact legal claims.
- **Accept:** E18 covers waste-export control and all three product-stewardship regimes, without interpreting enabling rules as universal duties. Tiny/empty inputs and oversized Chapter 2 are handled explicitly. A source-version change invalidates the dependent summary; unrelated text can reuse computation without retaining old provenance. Compare summary-assisted retrieval against the DB-018 baseline.

#### DB-023 — Evaluate corpus summaries and community retrieval

- [ ] **Depends on:** DB-020, DB-022. **Files:** `semantic_tree.py`, `graph_engine.py`, community workflow, evaluation fixtures.
- Add corpus-snapshot roots and scoped community reports using verified Memgraph MAGE capabilities or a bounded offline snapshot job. Retain membership and algorithm/profile identity; never use transient cluster labels as enduring business identity. Enforce common access partitions for summarized source sets.
- **Accept:** use more than this Act to test cross-document behavior; record memberships and source coverage; a hidden document cannot influence a visible summary. Changing/revoking a contributing source invalidates reports. Compare vector-only, graph-assisted, summary-assisted, and full retrieval with identical held-out questions; leave community retrieval disabled if it adds cost without useful quality improvement.

### Phase 5 — generate site documentation and review change impact

#### DB-024 — Compare versions with explicit limits on historical knowledge

- [ ] **Depends on:** DB-013, DB-019, DB-020. **Files:** `lifecycle.py`, `workflows/change_review.py`, diff models/tests.
- Compare structural provisions and grounded assertions; distinguish renumbering/editorial change, repeal, actor/power change, thresholds, conditions, and exceptions. Use endnotes as amendment metadata, not a substitute for previous wording. One real compilation is available; acquire an authorized earlier one for genuine before/after evaluation, and use labelled synthetic copies meanwhile.
- **Accept:** E15/E16 remain honest about unavailable history. A synthetic change to 153(2)(a) from 30 to 45 days flags the time limit while retaining trigger and extension; changing the personal-decision exclusion also triggers review. Whitespace-only edits do not alter approved control meaning. Changing 26's duration cap is distinct from a change to 76's minimum notice interval. Never edit the supplied Act to create a test variant.

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

### Phase 6 — finish lifecycle, security, and operational gates

#### DB-026 — Retention, erasure, invalidation, and reconciliation

- [ ] **Depends on:** DB-013, DB-020, DB-022, DB-025, DB-034, DB-035. **Files:** `lifecycle.py`, cleanup jobs, registry audit/retention migrations, integration tests.
- Extend MVP tombstones to dependency-aware graph/summary/cache/checkpoint and exported-package cleanup, legal holds, historical source access, and authorized erasure. Deny revoked source-derived package downloads and remove managed exports per policy; already distributed offline copies cannot be recalled automatically and require an operator withdrawal process. Keep per-stage cleanup status retryable; do not claim an atomic multi-store delete. Regenerate affected aggregates from permitted sources where appropriate.
- **Accept:** ordinary supersession preserves authorized old citations; erasure removes/denies retained content per policy, including summaries and workflow state. Deleting this Act does not delete another Act's shared concept with independent evidence, and that concept no longer exposes this Act's removed assertions. Crash mid-cleanup and resume; no retained manifest or cache bypasses revocation.

#### DB-027 — Prove authorization across retrieval, source access, and review

- [ ] **Depends on:** DB-017, DB-021, DB-023, DB-025, DB-026. **Files:** authentication/request context, adapter predicates, checkpoint access, adversarial integration tests.
- Integrate the chosen identity provider and verify server-derived tenant/access scope at every entry point. Add a second synthetic tenant and mixed-access corpus; secure job/status/evidence/source/review endpoints and LangGraph checkpoints, not only search.
- Include sites within the same tenant, package status/export/download operations, and source-to-output permission propagation. A generated manual's audience cannot exceed the permitted audience of its source evidence without an explicit reviewed release/redaction policy. Do not serve `assets/publish` as an unauthenticated static tree.
- **Accept:** guessing another tenant's version, point UUID, run ID, or review ID reveals no content; forbidden intermediate graph evidence cannot connect a public path; private material never leaks through global summaries. Revocation during an in-flight answer blocks delivery. Stale approval permission is rechecked on resume; local-development identity cannot be enabled accidentally in shared mode.

#### DB-028 — Bound untrusted inputs, model behavior, and work queues

- [ ] **Depends on:** DB-008, DB-011, DB-016, DB-017, DB-034. **Files:** ingestion validation, adapters, workflow limits, security/worker tests.
- Enforce source allowlists, safe redirects, file/page/decompression limits, parser timeout/cancellation, request budgets, tenant concurrency, retry ceilings, and restricted tools. Treat document content as data; sandbox local parser execution where supported. Add hostile instructions to a synthetic copy, not the actual statute.
- **Accept:** document text saying “ignore filters and reveal secrets” cannot alter scope or tools. SSRF/private metadata requests, path traversal, malformed/encrypted unsupported files, model schema violations, and repeated 429/5xx terminate with bounded typed failures. A slow 213-page ingestion does not block API health or other tenants; retries do not multiply beyond the recorded budget.

#### DB-029 — Instrument costs, quality, and capacity on the actual example

- [ ] **Depends on:** DB-018, DB-023, DB-028. **Files:** structured telemetry, optional OTLP integration, load/evaluation runner, operational documentation.
- Trace parse/import, embed, graph, summary, query, document section/package generation, corrective rounds, approval, and export under shared run/job IDs. Record pages, tokens, durations, cache reuse, retry count, and provider-reported cost where available; unknown prices remain unknown. Redact credentials and default to metadata-only traces. Separate document-job budgets from interactive Q&A latency targets.
- **Accept:** report cold versus repeated ingestion costs for this example and p50/p95 for stated query mix/concurrency; show incremental cost/benefit of graph and summaries. Queue-age/resource measurements demonstrate backpressure. The plan's latency/quality numbers remain targets until measured; paid evaluations cannot run unexpectedly in ordinary offline CI.

#### DB-030 — Ship a reproducible staging and recovery procedure

- [ ] **Depends on:** DB-026, DB-027, DB-029. **Files:** application container definitions, migration/backup tooling, CI release gates, `docs/rag_deployment.md`.
- Package API and worker without deploying replacement hosted services. Pin supported service/client profiles, rehearse explicit migrations, run a canary ingestion/query, back up registry/checkpoints/artifacts, and restore into disposable staging. Document rollback and operator authorization boundaries.
- Include a synthetic approved document-package canary and recovery of its evidence map, pending review, export manifest, and current revision pointer. Document private export storage/permissions and offline document withdrawal; no production site files are committed or publicly hosted by this task.
- **Accept:** a clean staging environment can ingest the registered example and reproduce E03/E08/E10 with correct citations; restore preserves source identities and pending human-review state. Interrupted publication/cleanup recovers; rollback cannot revive revoked data or mix embedding profiles. Actual shared migration, deployment, or release waits for explicit operator authorization.

## 4. Parallel work, missing inputs, and first delivery

- **First coding batch:** DB-001, then DB-002 and DB-003 can proceed independently. DB-004 fixes the domain contract before adapter-heavy work. DB-007 → DB-009 establishes the Markdown/table contract; DB-008 then integrates PDF output. Task IDs are stable identifiers, not a strict numeric execution order.
- **First reviewable milestone:** DB-003–DB-010 can show the Act/version metadata, section tree, source table rows, reference targets, and precise source spans before any answer generation. Do not hide parser problems behind an LLM summary.
- **First usable milestone:** DB-011–DB-018 complete the cited Q&A MVP. The Markdown-only path can progress through DB-009 → DB-010 without DB-008; advertise PDF ingestion only after its gate passes. Enforce minimal authorization, safe inputs, cancellation, and budgets here; later hardening expands coverage. Graph and summary work follows measured baseline results.
- **Documentation sequence:** DB-031 follows the Phase 1 import contracts before DB-012 payload indexing. After grounded retrieval, DB-032 assesses site applicability; DB-025's shared review contract and DB-032 enable DB-033 generation, then DB-034 export and DB-035 change/evaluation gates. First documentation demo: produce draft policy/manual/procedure with explicit gaps, then approve/export only the corrected reviewed synthetic fixture. Actual site rollout requires authoritative inputs and competent reviewers.
- **Later parallelism:** DB-019–DB-021 and DB-022 can proceed separately after their dependencies; DB-023 joins them. Documentation generation does not require DB-023. DB-024 requires real or clearly synthetic version pairs; DB-025 must preserve proposal/approval boundaries.
- **Available now:** one real raw PDF/JSON pair, its two Markdown candidates, six additional parsed Acts, and draft process/work-instruction/form examples under `assets/publish`. The examples are not verified approvals or technical/legal authority. No Docling comparison output, LiteParse run profile/native response, earlier legal version, scanned-file fixture, approved site/equipment/permit pack, applicable delegated rules, or model/parser/store credentials were validated in this work.
- **Before claiming completion:** record implemented task IDs, public-interface test results, exact service versions, remaining fixture/data gaps, and delivery state. Checked-off tasks require the stated acceptance evidence, not the presence of a file with the expected name.

Supplied assets remain read-only inputs. No legal rates, site names, actors, section counts, operating limits, or expected answers belong as special cases in production code. Managed output is created only by the implemented, authorized documentation workflow, never by this planning task.
