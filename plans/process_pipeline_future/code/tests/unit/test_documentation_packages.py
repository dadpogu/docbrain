"""Moved from tests/unit/test_review_and_packages.py: documentation package lifecycle (process application).

Uses AUTHOR/SITE/COMPLIANCE/TECH, approve(), and fixtures from the original module."""

from docbrain.workflows.documentation import (
    Dependency,
    DocumentationPackages,
    PackageDocument,
    PackageDraft,
    PackageError,
    PackageStatus,
)


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
