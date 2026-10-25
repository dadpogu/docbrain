"""DB-025 approval contract and the documentation package lifecycle state logic."""

from __future__ import annotations

from pathlib import Path

import pytest

from docbrain.adapters.artifacts import LocalBlobStore
from docbrain.registry import Registry
from docbrain.workflows.change_review import (
    TECHNICAL_REVIEWER,
    ProposalSubmission,
    ReviewDecision,
    ReviewRejected,
    ReviewStatus,
    StaleProposal,
    decide,
    submit_for_review,
)
from docbrain.workflows.documentation import (
    Dependency,
    DocumentationPackages,
    PackageDocument,
    PackageDraft,
    PackageError,
    PackageStatus,
)
from tests.conftest import FakeClock, context

AUTHOR = context(principal="author", sites=("site-a",))
SITE = context(principal="site-reviewer", roles=("site_reviewer",), sites=("site-a",))
COMPLIANCE = context(principal="compliance-reviewer", roles=("compliance_reviewer",), sites=("site-a",))
TECH = context(principal="engineer", roles=(TECHNICAL_REVIEWER,), sites=("site-a",))


def proposal(**overrides) -> ProposalSubmission:  # type: ignore[no-untyped-def]
    values = dict(
        subject_kind="procedure_proposal",
        subject_id="prop-1",
        revision=1,
        content_hash="c1",
        dependency_hash="d1",
        required_roles=frozenset({"site_reviewer", "compliance_reviewer"}),
        author_id="author",
    )
    values.update(overrides)
    return ProposalSubmission(**values)


def approve(reg: Registry, ctx, review_id: str, role: str, decision_id: str, **kw):  # type: ignore[no-untyped-def]
    args = dict(
        decision=ReviewDecision.APPROVE,
        role=role,
        decision_id=decision_id,
        expected_revision=1,
        expected_content_hash="c1",
        expected_dependency_hash="d1",
        rationale="checked",
    )
    args.update(kw)
    return decide(reg, ctx, review_id, **args)


def test_decisions_bind_reviewer_roles_and_hashes(registry: Registry) -> None:
    review = submit_for_review(registry, "t1", proposal())
    with pytest.raises(ReviewRejected):
        approve(registry, context(principal="author", roles=("site_reviewer",)), review, "site_reviewer", "d0")
    with pytest.raises(ReviewRejected):
        approve(registry, SITE, review, "compliance_reviewer", "d0")  # role not held
    with pytest.raises(StaleProposal):
        approve(registry, SITE, review, "site_reviewer", "d0", expected_content_hash="c0")
    with pytest.raises(ReviewRejected):
        approve(registry, context("t2", principal="x", roles=("site_reviewer",)), review, "site_reviewer", "d0")
    assert approve(registry, SITE, review, "site_reviewer", "d1") is ReviewStatus.PENDING
    with pytest.raises(ReviewRejected):
        approve(registry, COMPLIANCE, review, "compliance_reviewer", "d1")  # replayed decision ID
    with pytest.raises(ReviewRejected):
        approve(registry, SITE, review, "site_reviewer", "d2")  # same reviewer twice
    assert approve(registry, COMPLIANCE, review, "compliance_reviewer", "d3") is ReviewStatus.APPROVED
    with pytest.raises(ReviewRejected):
        approve(registry, TECH, review, TECHNICAL_REVIEWER, "d4")
    assert [d["reviewer_id"] for d in registry.get_review(review)["decisions"]] == [
        "site-reviewer",
        "compliance-reviewer",
    ]


def test_pending_review_resumes_after_restart(tmp_path: Path) -> None:
    clock = FakeClock()
    first = Registry(tmp_path / "r.sqlite3", LocalBlobStore(tmp_path / "b"), clock=clock)
    first.migrate()
    review = submit_for_review(first, "t1", proposal())
    approve(first, SITE, review, "site_reviewer", "d1")
    first.close()
    restarted = Registry.open(tmp_path / "r.sqlite3", LocalBlobStore(tmp_path / "b"), clock=clock)
    assert approve(restarted, COMPLIANCE, review, "compliance_reviewer", "d2") is ReviewStatus.APPROVED
    with pytest.raises(ReviewRejected):
        approve(restarted, SITE, review, "site_reviewer", "d1")
    restarted.close()


def test_blockers_and_safety_review_cannot_be_waived(registry: Registry) -> None:
    blocked = submit_for_review(registry, "t1", proposal(subject_id="p2", blockers=("torque value unknown",)))
    with pytest.raises(ReviewRejected):
        approve(registry, SITE, blocked, "site_reviewer", "b1")
    assert (
        decide(
            registry,
            SITE,
            blocked,
            decision=ReviewDecision.REJECT,
            role="site_reviewer",
            decision_id="b2",
            expected_revision=1,
            expected_content_hash="c1",
            expected_dependency_hash="d1",
            rationale="fix gaps",
        )
        is ReviewStatus.REJECTED
    )
    safety = submit_for_review(registry, "t1", proposal(subject_id="p3", safety_critical=True))
    approve(registry, SITE, safety, "site_reviewer", "s1")
    assert approve(registry, COMPLIANCE, safety, "compliance_reviewer", "s2") is ReviewStatus.PENDING
    assert approve(registry, TECH, safety, TECHNICAL_REVIEWER, "s3") is ReviewStatus.APPROVED


def package_draft(step: str = "Confirm Kiln K-1 is below 55 °C.", process_rev: str = "2.0") -> PackageDraft:
    return PackageDraft(
        documents=(
            PackageDocument(document_id="POL-A1", kind="policy", title="Batch policy", content="Policy text."),
            PackageDocument(
                document_id="MAN-A1", kind="manual", title="Operations manual", content="See PRO-A1 rev 1."
            ),
            PackageDocument(document_id="PRO-A1", kind="procedure", title="Pot cycle", content=step),
        ),
        dependencies=(
            Dependency(kind="site_process", ref_id="t1:site:P-100@site-a", revision=process_rev),
            Dependency(kind="template", ref_id="WI-template", revision="sha-46919975"),
        ),
    )


def test_package_lifecycle_requires_fresh_approval_and_current_dependencies(registry: Registry) -> None:
    packages = DocumentationPackages(registry)
    with pytest.raises(PackageError):
        packages.create_package(context(principal="x", sites=("site-b",)), "site-a", "k1")
    pkg = packages.create_package(AUTHOR, "site-a", "k1")
    assert packages.create_package(AUTHOR, "site-a", "k1") == pkg  # idempotent
    rev1 = packages.add_revision(AUTHOR, pkg, package_draft())
    packages.submit(AUTHOR, pkg, rev1.revision, frozenset({"site_reviewer", "compliance_reviewer"}))

    def vote(ctx, role, did, view):  # type: ignore[no-untyped-def]
        return packages.decide(
            ctx,
            pkg,
            view.revision,
            decision=ReviewDecision.APPROVE,
            role=role,
            decision_id=did,
            expected_content_hash=view.content_hash,
            expected_dependency_hash=view.dependency_hash,
            rationale="ok",
        )

    assert vote(SITE, "site_reviewer", "p1", rev1) is PackageStatus.IN_REVIEW
    # Editing a step creates a new revision; the old revision's hashes cannot approve it.
    rev2 = packages.add_revision(AUTHOR, pkg, package_draft(step="Confirm Kiln K-1 is below 50 °C."))
    assert rev2.content_hash != rev1.content_hash
    packages.submit(AUTHOR, pkg, rev2.revision, frozenset({"site_reviewer", "compliance_reviewer"}))
    with pytest.raises(StaleProposal):
        packages.decide(
            COMPLIANCE,
            pkg,
            rev2.revision,
            decision=ReviewDecision.APPROVE,
            role="compliance_reviewer",
            decision_id="p2",
            expected_content_hash=rev1.content_hash,
            expected_dependency_hash=rev1.dependency_hash,
            rationale="old token",
        )
    assert vote(COMPLIANCE, "compliance_reviewer", "p3", rev2) is PackageStatus.IN_REVIEW
    assert vote(SITE, "site_reviewer", "p4", rev2) is PackageStatus.APPROVED
    current = package_draft(step="x").dependencies
    assert packages.publication_blockers(AUTHOR, pkg, rev2.revision, current) == []
    # A process revision change before publication forces review and blocks publication.
    changed = Dependency(kind="site_process", ref_id="t1:site:P-100@site-a", revision="2.1")
    assert packages.dependency_changed(AUTHOR, pkg, changed) == [rev1.revision, rev2.revision]
    assert packages.revision(AUTHOR, pkg, rev2.revision).status is PackageStatus.NEEDS_REVIEW
    rev1_review = packages.revision(AUTHOR, pkg, rev1.revision).review_id
    assert rev1_review is not None and registry.get_review(rev1_review)["status"] == ReviewStatus.STALE
    with pytest.raises(PackageError):
        packages.mark_published(AUTHOR, pkg, rev2.revision, current)


def test_package_publication_after_approval(registry: Registry) -> None:
    packages = DocumentationPackages(registry)
    pkg = packages.create_package(AUTHOR, "site-a", "k2")
    incomplete = PackageDraft(documents=package_draft().documents[:2], dependencies=package_draft().dependencies)
    with pytest.raises(PackageError):
        packages.submit(
            AUTHOR, pkg, packages.add_revision(AUTHOR, pkg, incomplete).revision, frozenset({"site_reviewer"})
        )
    view = packages.add_revision(AUTHOR, pkg, package_draft())
    packages.submit(AUTHOR, pkg, view.revision, frozenset({"site_reviewer"}))
    with pytest.raises(PackageError):
        packages.mark_published(AUTHOR, pkg, view.revision, package_draft().dependencies)  # not approved yet
    packages.decide(
        SITE,
        pkg,
        view.revision,
        decision=ReviewDecision.APPROVE,
        role="site_reviewer",
        decision_id="q1",
        expected_content_hash=view.content_hash,
        expected_dependency_hash=view.dependency_hash,
        rationale="ok",
    )
    published = packages.mark_published(AUTHOR, pkg, view.revision, package_draft().dependencies)
    assert published.status is PackageStatus.PUBLISHED
    assert registry.get_package(pkg)["published_revision"] == view.revision
