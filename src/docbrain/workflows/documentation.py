"""Documentation package lifecycle (DB-033/034 state logic; no generation or file export yet).

``draft → in_review → approved → published`` with ``rejected`` and ``needs_review`` exits. Every
content edit is a new immutable revision with a new content hash, so an approval can never carry
over to edited content. A dependency change (law, site/process fact, template, applicability
decision) marks affected revisions ``needs_review`` and invalidates their pending reviews. Approval
and publication are application operations bound to hashes; models never call them.
"""

from __future__ import annotations

import json
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from ..models import RequestContext, sha256_hex
from ..registry import NotFound, Registry, deterministic_id
from .change_review import ProposalSubmission, ReviewDecision, ReviewStatus, decide, mark_stale, submit_for_review

REQUIRED_DOCUMENT_KINDS = frozenset({"policy", "manual", "procedure"})


class PackageStatus(StrEnum):
    DRAFT = "draft"
    IN_REVIEW = "in_review"
    APPROVED = "approved"
    PUBLISHED = "published"
    REJECTED = "rejected"
    NEEDS_REVIEW = "needs_review"


class PackageDocument(BaseModel):
    model_config = ConfigDict(frozen=True)

    document_id: str
    kind: str
    title: str
    content: str


class Dependency(BaseModel):
    """A pinned input: source version, site/process revision, template, or applicability decision."""

    model_config = ConfigDict(frozen=True)

    kind: str
    ref_id: str
    revision: str


class PackageDraft(BaseModel):
    model_config = ConfigDict(frozen=True)

    documents: tuple[PackageDocument, ...]
    dependencies: tuple[Dependency, ...]
    blockers: tuple[str, ...] = ()  # e.g. unresolved safety-critical values; block approval, not drafting
    safety_critical: bool = False


class PackageError(Exception):
    pass


def _canonical(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def content_hash(documents: tuple[PackageDocument, ...]) -> str:
    return sha256_hex(_canonical(sorted((d.model_dump() for d in documents), key=lambda d: d["document_id"])))


def dependency_hash(dependencies: tuple[Dependency, ...]) -> str:
    return sha256_hex(
        _canonical(sorted((d.model_dump() for d in dependencies), key=lambda d: (d["kind"], d["ref_id"])))
    )


class RevisionView(BaseModel):
    package_id: str
    revision: int
    status: PackageStatus
    content_hash: str
    dependency_hash: str
    review_id: str | None = None
    blockers: list[str] = Field(default_factory=list)


class DocumentationPackages:
    def __init__(self, registry: Registry) -> None:
        self.registry = registry

    def create_package(self, ctx: RequestContext, site_id: str, idempotency_key: str) -> str:
        if site_id not in ctx.site_ids:
            raise PackageError("caller is not authorized for this site")
        package_id = deterministic_id("pkg", ctx.tenant_id, site_id, idempotency_key)
        self.registry.create_package(package_id, ctx.tenant_id, {"site_id": site_id})
        return package_id

    def _package(self, ctx: RequestContext, package_id: str) -> dict[str, Any]:
        package = self.registry.get_package(package_id)
        if package["tenant_id"] != ctx.tenant_id or package["record"]["site_id"] not in ctx.site_ids:
            raise PackageError("package not found")
        return package

    def add_revision(self, ctx: RequestContext, package_id: str, draft: PackageDraft) -> RevisionView:
        self._package(ctx, package_id)
        ids = [d.document_id for d in draft.documents]
        if len(ids) != len(set(ids)):
            raise PackageError("document IDs must be unique within a package")
        record = {
            "documents": [d.model_dump() for d in draft.documents],
            "dependencies": [d.model_dump() for d in draft.dependencies],
            "blockers": list(draft.blockers),
            "safety_critical": draft.safety_critical,
            "content_hash": content_hash(draft.documents),
            "dependency_hash": dependency_hash(draft.dependencies),
            "author_id": ctx.principal_id,
            "review_id": None,
        }
        revision = self.registry.add_package_revision(package_id, record, PackageStatus.DRAFT)
        return self.revision(ctx, package_id, revision)

    def revision(self, ctx: RequestContext, package_id: str, revision: int) -> RevisionView:
        self._package(ctx, package_id)
        row = self.registry.get_package_revision(package_id, revision)
        record = row["record"]
        review_id = deterministic_id("rev", "documentation_package", package_id, str(revision))
        try:
            self.registry.get_review(review_id)
            found: str | None = review_id
        except NotFound:
            found = None
        return RevisionView(
            package_id=package_id,
            revision=revision,
            status=PackageStatus(row["status"]),
            content_hash=record["content_hash"],
            dependency_hash=record["dependency_hash"],
            review_id=found,
            blockers=record["blockers"],
        )

    def submit(self, ctx: RequestContext, package_id: str, revision: int, required_roles: frozenset[str]) -> str:
        view = self.revision(ctx, package_id, revision)
        record = self.registry.get_package_revision(package_id, revision)["record"]
        missing = REQUIRED_DOCUMENT_KINDS - {d["kind"] for d in record["documents"]}
        if missing:
            raise PackageError(f"package lacks required document kinds: {sorted(missing)}")
        review_id = submit_for_review(
            self.registry,
            ctx.tenant_id,
            ProposalSubmission(
                subject_kind="documentation_package",
                subject_id=package_id,
                revision=revision,
                content_hash=view.content_hash,
                dependency_hash=view.dependency_hash,
                required_roles=required_roles,
                author_id=record["author_id"],
                safety_critical=record["safety_critical"],
                blockers=tuple(record["blockers"]),
            ),
        )
        self.registry.transition_package_revision(package_id, revision, [PackageStatus.DRAFT], PackageStatus.IN_REVIEW)
        return review_id

    def decide(
        self,
        ctx: RequestContext,
        package_id: str,
        revision: int,
        *,
        decision: ReviewDecision,
        role: str,
        decision_id: str,
        expected_content_hash: str,
        expected_dependency_hash: str,
        rationale: str,
    ) -> PackageStatus:
        self._package(ctx, package_id)
        view = self.revision(ctx, package_id, revision)
        if view.review_id is None:
            raise PackageError("revision has not been submitted for review")
        status = decide(
            self.registry,
            ctx,
            view.review_id,
            decision=decision,
            role=role,
            decision_id=decision_id,
            expected_revision=revision,
            expected_content_hash=expected_content_hash,
            expected_dependency_hash=expected_dependency_hash,
            rationale=rationale,
        )
        if status is ReviewStatus.APPROVED:
            self.registry.transition_package_revision(
                package_id, revision, [PackageStatus.IN_REVIEW], PackageStatus.APPROVED, pointer="approved_revision"
            )
        elif status is ReviewStatus.REJECTED:
            self.registry.transition_package_revision(
                package_id, revision, [PackageStatus.IN_REVIEW], PackageStatus.REJECTED
            )
        return self.revision(ctx, package_id, revision).status

    def dependency_changed(self, ctx: RequestContext, package_id: str, changed: Dependency) -> list[int]:
        """Mark every live revision pinned to another revision of ``changed.ref_id`` as needing review."""
        self._package(ctx, package_id)
        affected: list[int] = []
        live = [PackageStatus.DRAFT, PackageStatus.IN_REVIEW, PackageStatus.APPROVED, PackageStatus.PUBLISHED]
        for row in self.registry.package_revisions(package_id):
            if row["status"] not in live:
                continue
            pinned = [
                d for d in row["record"]["dependencies"] if d["kind"] == changed.kind and d["ref_id"] == changed.ref_id
            ]
            if not pinned or all(d["revision"] == changed.revision for d in pinned):
                continue
            view = self.revision(ctx, package_id, row["revision"])
            if (
                view.review_id is not None
                and self.registry.get_review(view.review_id)["status"] == ReviewStatus.PENDING
            ):
                mark_stale(self.registry, view.review_id)
            self.registry.transition_package_revision(package_id, row["revision"], live, PackageStatus.NEEDS_REVIEW)
            affected.append(row["revision"])
        return affected

    def publication_blockers(
        self, ctx: RequestContext, package_id: str, revision: int, current: tuple[Dependency, ...]
    ) -> list[str]:
        """Reasons the revision may not become the current published package (empty when it may)."""
        view = self.revision(ctx, package_id, revision)
        reasons: list[str] = []
        if view.status is not PackageStatus.APPROVED:
            reasons.append(f"revision is {view.status.value}, not approved")
        if view.blockers:
            reasons.append("unresolved blockers remain")
        if dependency_hash(current) != view.dependency_hash:
            reasons.append("pinned dependencies no longer match the current source revisions")
        return reasons

    def mark_published(
        self, ctx: RequestContext, package_id: str, revision: int, current: tuple[Dependency, ...]
    ) -> RevisionView:
        reasons = self.publication_blockers(ctx, package_id, revision, current)
        if reasons:
            raise PackageError("; ".join(reasons))
        self.registry.transition_package_revision(
            package_id, revision, [PackageStatus.APPROVED], PackageStatus.PUBLISHED, pointer="published_revision"
        )
        return self.revision(ctx, package_id, revision)
