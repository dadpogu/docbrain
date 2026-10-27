"""Shared human-approval contract (DB-025).

A decision binds the exact proposal revision, content hash, and dependency hash the reviewer saw.
Reviewers come from the trusted :class:`RequestContext`, never from tool or model input. The
contract only updates DocBrain records; it performs no external action.

Rules enforced on every decision:

* unauthenticated, cross-tenant, or self-approving reviewers are rejected;
* the reviewer must hold one of the review's still-unsatisfied required roles;
* stale revisions/hashes and replayed or repeated decisions are rejected;
* unresolved blockers (for example unknown safety limits) cannot be approved away;
* safety-critical proposals additionally need a ``technical_reviewer`` approval.
"""

from __future__ import annotations

from enum import StrEnum
from typing import Any

from pydantic import BaseModel, ConfigDict

from ..models import RequestContext
from ..registry import Registry, RegistryConflict

TECHNICAL_REVIEWER = "technical_reviewer"


class ReviewStatus(StrEnum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    STALE = "stale"  # dependencies changed before a final decision


class ReviewDecision(StrEnum):
    APPROVE = "approve"
    REJECT = "reject"


class ReviewRejected(Exception):
    """The decision request was refused; nothing was recorded."""


class StaleProposal(ReviewRejected):
    pass


class ProposalSubmission(BaseModel):
    model_config = ConfigDict(frozen=True)

    subject_kind: str
    subject_id: str
    revision: int
    content_hash: str
    dependency_hash: str
    required_roles: frozenset[str]
    author_id: str
    safety_critical: bool = False
    blockers: tuple[str, ...] = ()


def submit_for_review(registry: Registry, tenant_id: str, submission: ProposalSubmission) -> str:
    if not submission.required_roles:
        raise ValueError("a review needs at least one designated reviewer role")
    return registry.create_review(
        tenant_id,
        submission.subject_kind,
        submission.subject_id,
        submission.revision,
        submission.content_hash,
        submission.model_dump(mode="json"),
    )


def _required(record: dict[str, Any]) -> set[str]:
    roles = set(record["required_roles"])
    if record.get("safety_critical"):
        roles.add(TECHNICAL_REVIEWER)
    return roles


def decide(
    registry: Registry,
    ctx: RequestContext,
    review_id: str,
    *,
    decision: ReviewDecision,
    role: str,
    decision_id: str,
    expected_revision: int,
    expected_content_hash: str,
    expected_dependency_hash: str,
    rationale: str,
) -> ReviewStatus:
    """Record one reviewer decision atomically and return the resulting review status."""

    def policy(review: dict[str, Any], _: dict[str, Any]) -> str:
        record = review["record"]
        if not ctx.authenticated or ctx.tenant_id != review["tenant_id"]:
            raise ReviewRejected("reviewer is not authenticated for this tenant")
        if review["status"] != ReviewStatus.PENDING:
            raise ReviewRejected(f"review is {review['status']}, not pending")
        if (
            expected_revision != review["revision"]
            or expected_content_hash != review["content_hash"]
            or expected_dependency_hash != record["dependency_hash"]
        ):
            raise StaleProposal("the decision refers to a different proposal revision or dependency set")
        if ctx.principal_id == record["author_id"]:
            raise ReviewRejected("authors cannot review their own proposals")
        if role not in ctx.roles:
            raise ReviewRejected(f"reviewer does not hold role {role!r}")
        approved_roles = {d["role"] for d in review["decisions"] if d["decision"] == ReviewDecision.APPROVE}
        outstanding = _required(record) - approved_roles
        if role not in outstanding:
            raise ReviewRejected(f"role {role!r} is not an outstanding reviewer role")
        if decision is ReviewDecision.REJECT:
            return ReviewStatus.REJECTED
        if record.get("blockers"):
            raise ReviewRejected("unresolved blockers must be fixed in a new revision; they cannot be waived")
        return ReviewStatus.APPROVED if outstanding == {role} else ReviewStatus.PENDING

    try:
        status = registry.apply_decision(
            review_id,
            decision_id,
            ctx.principal_id,
            {
                "decision": decision.value,
                "role": role,
                "reviewer_id": ctx.principal_id,
                "revision": expected_revision,
                "content_hash": expected_content_hash,
                "dependency_hash": expected_dependency_hash,
                "rationale": rationale,
            },
            policy,
        )
    except RegistryConflict as exc:
        raise ReviewRejected(str(exc)) from exc
    return ReviewStatus(status)


def mark_stale(registry: Registry, review_id: str) -> None:
    """Invalidate a pending review whose dependencies changed. Final decisions are kept as history."""
    registry.set_review_status(review_id, ReviewStatus.PENDING, ReviewStatus.STALE)
