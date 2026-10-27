"""DB-025 approval contract."""

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
