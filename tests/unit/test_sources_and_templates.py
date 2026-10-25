"""DB-031: mixed source roles, site scope, and template rules using supplied drafts and a synthetic pack."""

from __future__ import annotations

import hashlib
from datetime import date
from pathlib import Path

import pytest

from docbrain.documentation import TemplateRequirements, find_template_leakage, validate_template
from docbrain.models import ResourceScope, SiteScope, SiteScopeKind, SourceRole
from docbrain.parsing import parse_operational_markdown
from docbrain.registry import NotFound, Registry
from docbrain.workflows.ingestion import SourceRegistration, register_operational_source
from tests.conftest import FIXTURES, REPO, context, load_fixture

PUBLISH = REPO / "assets" / "publish"
P001 = PUBLISH / "processes" / "p01-high-level-process.md"
WI007 = PUBLISH / "work-instructions" / "w07-emergency-shutdown.md"
WI_TEMPLATE = PUBLISH / "work-instructions" / "w00-work-instruction-template.md"
P_TEMPLATE = PUBLISH / "processes" / "p00-process-template.md"
FORM_TEMPLATE = PUBLISH / "forms" / "f00-form-template.md"
PACK = FIXTURES / "documentation"


def exists_from(path: Path):  # type: ignore[no-untyped-def]
    return lambda target: (path.parent / target).exists()


def test_supplied_reference_assets_are_unchanged() -> None:
    for rel, digests in load_fixture("documentation", "supplied_assets.json")["assets"].items():
        assert hashlib.sha256((REPO / rel).read_bytes()).hexdigest() in digests, rel


def test_draft_examples_keep_claimed_status_and_expose_gaps(registry: Registry) -> None:
    site = SiteScope.site("wodonga")
    p001 = register_operational_source(
        registry,
        "t1",
        P001.read_bytes(),
        SourceRegistration(role=SourceRole.PROCESS_DESCRIPTION, site=site, process_id="thermolysis"),
        link_exists=exists_from(P001),
    )
    wi007 = register_operational_source(
        registry,
        "t1",
        WI007.read_bytes(),
        SourceRegistration(role=SourceRole.PROCESS_DESCRIPTION, site=site, process_id="thermolysis"),
        link_exists=exists_from(WI007),
    )
    assert p001.document.doc_id == "t1:site:P-001@wodonga" and wi007.document.doc_id == "t1:site:WI-007@wodonga"
    for source in (p001, wi007):
        assert source.claimed_status == "Draft for approval"
        assert source.document.approval.claimed_label == "Draft for approval"
        assert not source.document.approval.is_verified  # a label is not an authenticated approval
        assert {"placeholder_tbc", "missing_reference"} <= set(source.findings)
    assert "unresolved_variable" in p001.findings  # "torque x" stays unresolved
    doc = parse_operational_markdown(P001.read_text(encoding="utf-8"), "a", link_exists=exists_from(P001))
    assert len(doc.findings_of("unresolved_variable")) == 3
    assert any("op-manual.md" in f.text for f in doc.findings_of("missing_reference"))


def test_missing_site_scope_is_unresolved_not_shared(registry: Registry) -> None:
    source = register_operational_source(
        registry, "t1", P001.read_bytes(), SourceRegistration(role=SourceRole.PROCESS_DESCRIPTION)
    )
    assert not source.site_scope_resolved
    assert source.document.scope.site.kind is SiteScopeKind.UNRESOLVED
    with pytest.raises(NotFound):
        registry.read_artifact(context("t1", sites=("wodonga",)), source.artifact_id)


def test_synthetic_sites_stay_isolated_and_sharing_is_explicit(registry: Registry) -> None:
    pack = load_fixture("documentation", "pack.json")
    tenant = pack["tenant_id"]
    registered = {}
    for entry in pack["sources"]:
        site = SiteScope.site(entry["site"]) if "site" in entry else SiteScope.shared(*entry["shared_with"])
        registered[entry["path"]] = register_operational_source(
            registry,
            tenant,
            (PACK / entry["path"]).read_bytes(),
            SourceRegistration(role=SourceRole(entry["role"]), site=site),
        )
    a = registered["site_a/p100-pot-cycle.md"]
    b = registered["site_b/p100-pot-cycle.md"]
    policy = registered["shared/pol-001-records.md"]
    assert a.document.doc_id != b.document.doc_id  # same process ID and title, different sites
    ctx_a, ctx_b = context(tenant, sites=("site-a",)), context(tenant, sites=("site-b",))
    assert b"< 55 \xc2\xb0C" in registry.read_artifact(ctx_a, a.artifact_id)
    with pytest.raises(NotFound):
        registry.read_artifact(ctx_a, b.artifact_id)
    with pytest.raises(NotFound):
        registry.read_artifact(ctx_b, a.artifact_id)
    assert registry.read_artifact(ctx_a, policy.artifact_id)
    with pytest.raises(NotFound):
        registry.read_artifact(ctx_b, policy.artifact_id)  # shared only with site A
    assert policy.document.source_role is SourceRole.ORGANIZATIONAL_POLICY  # never legislation
    for site, facts in pack["expected"].items():
        source = a if site == "site-a" else b
        doc = parse_operational_markdown(registry.read_text(context(tenant, sites=(site,)), source.artifact_id), "x")
        roles = [row.cells[0].text for row in doc.tables[0].rows]
        assert roles == facts["roles"]
        assert facts["lid_opening_limit"] in {v.normalized for v in doc.stated_values}


def test_identity_survives_moves_and_derivatives_keep_lineage(registry: Registry) -> None:
    data = (PACK / "site_a" / "p100-pot-cycle.md").read_bytes()
    reg = SourceRegistration(role=SourceRole.PROCESS_DESCRIPTION, site=SiteScope.site("site-a"))
    first = register_operational_source(registry, "t1", data, reg, original_name="site_a/p100-pot-cycle.md")
    moved = register_operational_source(registry, "t1", data, reg, original_name="archive/2026/renamed.md")
    assert moved.document.doc_id == first.document.doc_id and moved.artifact_id == first.artifact_id
    with pytest.raises(ValueError):
        register_operational_source(
            registry,
            "t1",
            b"# Manual: Generated\n",
            SourceRegistration(role=SourceRole.GENERATED_DERIVATIVE, site=SiteScope.site("site-a")),
        )
    derived = register_operational_source(
        registry,
        "t1",
        b"# Manual: Generated\n**Document ID:** MAN-1\n",
        SourceRegistration(
            role=SourceRole.GENERATED_DERIVATIVE, site=SiteScope.site("site-a"), derived_from=(first.artifact_id,)
        ),
    )
    record = registry.get_artifact(context("t1", sites=("site-a",)), derived.artifact_id)
    assert record.derived_from == (first.artifact_id,)
    assert derived.document.source_role is SourceRole.GENERATED_DERIVATIVE


def requirements(kind: str) -> TemplateRequirements:
    return TemplateRequirements.model_validate(load_fixture("documentation", "template_requirements.json")[kind])


def test_templates_are_validated_against_reviewed_requirements() -> None:
    wi = validate_template(
        parse_operational_markdown(WI_TEMPLATE.read_text(encoding="utf-8"), "wi"), requirements("work_instruction")
    )
    process = validate_template(
        parse_operational_markdown(P_TEMPLATE.read_text(encoding="utf-8"), "p"), requirements("process")
    )
    form = validate_template(
        parse_operational_markdown(FORM_TEMPLATE.read_text(encoding="utf-8"), "f"), requirements("form")
    )
    assert wi.valid and process.valid
    assert not form.valid and form.problems[0] == "template is empty"
    assert {"0psi", "5°c/min"} <= wi.profile.illustrative_values
    too_strict = TemplateRequirements(
        template_kind="work_instruction",
        required_sections=("Isolation Points",),
        reviewed_by="r",
        reviewed_on=date(2026, 10, 25),
    )
    assert not validate_template(
        parse_operational_markdown(WI_TEMPLATE.read_text(encoding="utf-8"), "wi"), too_strict
    ).valid


def test_template_example_values_never_become_site_facts() -> None:
    template = validate_template(
        parse_operational_markdown(WI_TEMPLATE.read_text(encoding="utf-8"), "wi"), requirements("work_instruction")
    ).profile
    draft = parse_operational_markdown(
        "# Work Instruction: Start Kiln\n\n| 1 | Check gauge. | Must be at 0 PSI. |\n| 2 | Ramp. | 5°C/min |\n", "d"
    )
    assert [f.value for f in find_template_leakage(draft, template)] == ["0 PSI", "5°C/min"]
    assert [f.value for f in find_template_leakage(draft, template, frozenset({"0psi"}))] == ["5°C/min"]
    site_a = parse_operational_markdown((PACK / "site_a" / "p100-pot-cycle.md").read_text(encoding="utf-8"), "a")
    assert find_template_leakage(site_a, template) == []


def test_site_and_legal_sources_keep_distinct_roles(registry: Registry) -> None:
    with pytest.raises(ValueError):
        register_operational_source(
            registry, "t1", b"# Act\n", SourceRegistration(role=SourceRole.REGULATORY_AUTHORITY)
        )
    assert ResourceScope(tenant_id="t1").site.kind is SiteScopeKind.NOT_SITE_SPECIFIC
