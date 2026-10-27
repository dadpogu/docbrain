"""Durable registry: artifacts, documents, versions, metadata claims, builds, jobs, reviews.

This is the SQLite single-process development mode named in the implementation plan. Every
state-changing operation runs in one ``BEGIN IMMEDIATE`` transaction, and decisions that must not be
lost or duplicated (job leases, review decisions) use compare-and-swap updates.
The schema is applied only by an explicit :meth:`Registry.migrate` call, never implicitly.
"""

from __future__ import annotations

import difflib
import json
import re
import sqlite3
import uuid
from collections.abc import Callable, Iterator, Sequence
from contextlib import contextmanager
from datetime import UTC, datetime, timedelta
from enum import StrEnum
from pathlib import Path
from typing import Any

from pydantic import BaseModel, ConfigDict

from .adapters.artifacts import LocalBlobStore
from .models import (
    ArtifactRecord,
    ArtifactRole,
    Derivation,
    LogicalDocument,
    OfficialVersion,
    RequestContext,
    ResourceScope,
    SourceSpan,
    is_authorized,
)
from .parsing import MetadataBasis, MetadataClaim, MetadataReconciliation, reconcile_claims

SCHEMA_VERSION = 1
_ID_NAMESPACE = uuid.UUID("8d0c3f4e-7a2b-5e19-a6c4-1f3e9b7d2a55")

_SCHEMA = """
CREATE TABLE schema_version (version INTEGER NOT NULL);
CREATE TABLE artifacts (
    artifact_id TEXT PRIMARY KEY,
    tenant_id TEXT NOT NULL,
    scope_json TEXT NOT NULL,
    sha256 TEXT NOT NULL,
    size INTEGER NOT NULL,
    media_type TEXT NOT NULL,
    role TEXT NOT NULL,
    original_name TEXT,
    derivation_json TEXT,
    created_at TEXT NOT NULL
);
CREATE TABLE artifact_lineage (
    artifact_id TEXT NOT NULL REFERENCES artifacts(artifact_id),
    parent_artifact_id TEXT NOT NULL REFERENCES artifacts(artifact_id),
    position INTEGER NOT NULL,
    PRIMARY KEY (artifact_id, parent_artifact_id)
);
CREATE TABLE documents (
    doc_id TEXT PRIMARY KEY,
    tenant_id TEXT NOT NULL,
    record_json TEXT NOT NULL,
    created_at TEXT NOT NULL
);
CREATE TABLE versions (
    version_id TEXT PRIMARY KEY,
    doc_id TEXT NOT NULL REFERENCES documents(doc_id),
    record_json TEXT NOT NULL,
    created_at TEXT NOT NULL
);
CREATE TABLE renderings (
    version_id TEXT NOT NULL REFERENCES versions(version_id),
    artifact_id TEXT NOT NULL REFERENCES artifacts(artifact_id),
    relation TEXT NOT NULL,
    PRIMARY KEY (version_id, artifact_id)
);
CREATE TABLE metadata_claims (
    version_id TEXT NOT NULL REFERENCES versions(version_id),
    field TEXT NOT NULL,
    claim_json TEXT NOT NULL,
    basis TEXT NOT NULL,
    artifact_id TEXT NOT NULL,
    PRIMARY KEY (version_id, field, basis, artifact_id)
);
CREATE TABLE review_items (
    item_id TEXT PRIMARY KEY,
    tenant_id TEXT NOT NULL,
    kind TEXT NOT NULL,
    subject TEXT NOT NULL,
    detail_json TEXT NOT NULL,
    status TEXT NOT NULL,
    created_at TEXT NOT NULL
);
CREATE TABLE builds (
    build_id TEXT PRIMARY KEY,
    tenant_id TEXT NOT NULL,
    version_id TEXT,
    artifact_id TEXT NOT NULL REFERENCES artifacts(artifact_id),
    pipeline_fingerprint TEXT NOT NULL,
    status TEXT NOT NULL,
    output_artifact_id TEXT,
    created_at TEXT NOT NULL,
    UNIQUE (tenant_id, version_id, artifact_id, pipeline_fingerprint)
);
CREATE TABLE jobs (
    job_id TEXT PRIMARY KEY,
    job_key TEXT NOT NULL UNIQUE,
    tenant_id TEXT NOT NULL,
    kind TEXT NOT NULL,
    state TEXT NOT NULL,
    attempts INTEGER NOT NULL DEFAULT 0,
    max_attempts INTEGER NOT NULL,
    lease_owner TEXT,
    lease_token TEXT,
    lease_expires_at TEXT,
    heartbeat_at TEXT,
    cancel_requested INTEGER NOT NULL DEFAULT 0,
    error TEXT,
    payload_json TEXT NOT NULL,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);
CREATE TABLE job_stages (
    job_id TEXT NOT NULL REFERENCES jobs(job_id),
    stage TEXT NOT NULL,
    output_json TEXT NOT NULL,
    completed_at TEXT NOT NULL,
    attempt INTEGER NOT NULL,
    PRIMARY KEY (job_id, stage)
);
CREATE TABLE reviews (
    review_id TEXT PRIMARY KEY,
    tenant_id TEXT NOT NULL,
    subject_kind TEXT NOT NULL,
    subject_id TEXT NOT NULL,
    revision INTEGER NOT NULL,
    content_hash TEXT NOT NULL,
    record_json TEXT NOT NULL,
    status TEXT NOT NULL,
    created_at TEXT NOT NULL,
    UNIQUE (subject_kind, subject_id, revision)
);
CREATE TABLE review_decisions (
    decision_id TEXT PRIMARY KEY,
    review_id TEXT NOT NULL REFERENCES reviews(review_id),
    reviewer_id TEXT NOT NULL,
    record_json TEXT NOT NULL,
    decided_at TEXT NOT NULL,
    UNIQUE (review_id, reviewer_id)
);
CREATE TABLE audit_events (
    event_id INTEGER PRIMARY KEY AUTOINCREMENT,
    tenant_id TEXT NOT NULL,
    kind TEXT NOT NULL,
    subject TEXT NOT NULL,
    detail_json TEXT NOT NULL,
    at TEXT NOT NULL
);
"""


class RegistryError(Exception):
    pass


class NotFound(RegistryError):
    """Missing or not authorized. The two are deliberately indistinguishable to callers."""


class RegistryConflict(RegistryError):
    pass


class SchemaMissing(RegistryError):
    pass


class LeaseLost(RegistryError):
    pass


class JobCancelled(RegistryError):
    pass


class JobState(StrEnum):
    QUEUED = "queued"
    RUNNING = "running"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    CANCELLED = "cancelled"


class JobRecord(BaseModel):
    job_id: str
    job_key: str
    tenant_id: str
    kind: str
    state: JobState
    attempts: int
    max_attempts: int
    lease_owner: str | None
    lease_expires_at: datetime | None
    cancel_requested: bool
    error: str | None
    payload: dict[str, Any]


class Lease(BaseModel):
    model_config = ConfigDict(frozen=True)

    job_id: str
    token: str
    owner: str
    attempt: int


def deterministic_id(prefix: str, *parts: str) -> str:
    return f"{prefix}_{uuid.uuid5(_ID_NAMESPACE, '|'.join(parts)).hex}"


def _iso(value: datetime | None) -> str | None:
    return value.isoformat() if value else None


class Registry:
    def __init__(self, path: Path | str, blobs: LocalBlobStore, *, clock: Callable[[], datetime] | None = None) -> None:
        self._db = sqlite3.connect(str(path), isolation_level=None, check_same_thread=False)
        self._db.row_factory = sqlite3.Row
        self._db.execute("PRAGMA foreign_keys = ON")
        self._db.execute("PRAGMA busy_timeout = 5000")
        self.blobs = blobs
        self.clock = clock or (lambda: datetime.now(UTC))

    @classmethod
    def open(cls, path: Path | str, blobs: LocalBlobStore, *, clock: Callable[[], datetime] | None = None) -> Registry:
        """Open an existing registry. Raises :class:`SchemaMissing` until :meth:`migrate` has run."""
        registry = cls(path, blobs, clock=clock)
        if registry.schema_version() != SCHEMA_VERSION:
            registry.close()
            raise SchemaMissing(f"registry at {path} needs an explicit migration to version {SCHEMA_VERSION}")
        return registry

    def schema_version(self) -> int | None:
        try:
            row = self._db.execute("SELECT version FROM schema_version").fetchone()
        except sqlite3.OperationalError:
            return None
        return int(row["version"]) if row else None

    def migrate(self) -> None:
        current = self.schema_version()
        if current == SCHEMA_VERSION:
            return
        if current is not None:
            raise RegistryError(f"no migration path from schema {current}")
        with self._tx():
            for statement in _SCHEMA.split(";"):
                if statement.strip():
                    self._db.execute(statement)
            self._db.execute("INSERT INTO schema_version (version) VALUES (?)", (SCHEMA_VERSION,))

    def close(self) -> None:
        self._db.close()

    @contextmanager
    def _tx(self) -> Iterator[sqlite3.Connection]:
        self._db.execute("BEGIN IMMEDIATE")
        try:
            yield self._db
        except BaseException:
            self._db.execute("ROLLBACK")
            raise
        self._db.execute("COMMIT")

    def _now(self) -> str:
        return self.clock().isoformat()

    def _audit(self, tenant_id: str, kind: str, subject: str, detail: dict[str, Any]) -> None:
        self._db.execute(
            "INSERT INTO audit_events (tenant_id, kind, subject, detail_json, at) VALUES (?, ?, ?, ?, ?)",
            (tenant_id, kind, subject, json.dumps(detail, sort_keys=True, default=str), self._now()),
        )

    def audit_events(self, tenant_id: str) -> list[dict[str, Any]]:
        rows = self._db.execute(
            "SELECT kind, subject, detail_json, at FROM audit_events WHERE tenant_id = ? ORDER BY event_id",
            (tenant_id,),
        ).fetchall()
        return [
            {"kind": r["kind"], "subject": r["subject"], "detail": json.loads(r["detail_json"]), "at": r["at"]}
            for r in rows
        ]

    # ------------------------------------------------------------------------------------
    # Artifacts
    # ------------------------------------------------------------------------------------

    def register_artifact(
        self,
        scope: ResourceScope,
        data: bytes,
        *,
        media_type: str,
        role: ArtifactRole,
        original_name: str | None = None,
        derived_from: Sequence[str] = (),
        derivation: Derivation | None = None,
    ) -> ArtifactRecord:
        """Store bytes once; records are per scope, so identical bytes never merge permissions."""
        digest = self.blobs.put(data)
        artifact_id = deterministic_id("art", scope.model_dump_json(), digest, role.value)
        with self._tx() as db:
            row = db.execute("SELECT * FROM artifacts WHERE artifact_id = ?", (artifact_id,)).fetchone()
            if row is None:
                for parent in derived_from:
                    if db.execute("SELECT 1 FROM artifacts WHERE artifact_id = ?", (parent,)).fetchone() is None:
                        raise NotFound(f"parent artifact {parent} is not registered")
                db.execute(
                    "INSERT INTO artifacts VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                    (
                        artifact_id,
                        scope.tenant_id,
                        scope.model_dump_json(),
                        digest,
                        len(data),
                        media_type,
                        role.value,
                        original_name,
                        derivation.model_dump_json() if derivation else None,
                        self._now(),
                    ),
                )
                for position, parent in enumerate(derived_from):
                    db.execute("INSERT INTO artifact_lineage VALUES (?, ?, ?)", (artifact_id, parent, position))
                self._audit(scope.tenant_id, "artifact_registered", artifact_id, {"sha256": digest, "role": role.value})
                row = db.execute("SELECT * FROM artifacts WHERE artifact_id = ?", (artifact_id,)).fetchone()
            return self._artifact(row)

    def _artifact(self, row: sqlite3.Row) -> ArtifactRecord:
        parents = self._db.execute(
            "SELECT parent_artifact_id FROM artifact_lineage WHERE artifact_id = ? ORDER BY position",
            (row["artifact_id"],),
        ).fetchall()
        return ArtifactRecord(
            artifact_id=row["artifact_id"],
            scope=ResourceScope.model_validate_json(row["scope_json"]),
            sha256=row["sha256"],
            size=row["size"],
            media_type=row["media_type"],
            role=ArtifactRole(row["role"]),
            original_name=row["original_name"],
            derived_from=tuple(p["parent_artifact_id"] for p in parents),
            derivation=Derivation.model_validate_json(row["derivation_json"]) if row["derivation_json"] else None,
            created_at=datetime.fromisoformat(row["created_at"]),
        )

    def get_artifact(self, ctx: RequestContext, artifact_id: str) -> ArtifactRecord:
        if not isinstance(artifact_id, str) or not re.fullmatch(r"art_[0-9a-f]{32}", artifact_id):
            raise NotFound("artifact not found")
        row = self._db.execute("SELECT * FROM artifacts WHERE artifact_id = ?", (artifact_id,)).fetchone()
        if row is None:
            raise NotFound("artifact not found")
        record = self._artifact(row)
        if not is_authorized(ctx, record.scope):
            raise NotFound("artifact not found")
        return record

    def read_artifact(self, ctx: RequestContext, artifact_id: str) -> bytes:
        return self.blobs.get(self.get_artifact(ctx, artifact_id).sha256)

    def read_text(self, ctx: RequestContext, artifact_id: str) -> str:
        return self.read_artifact(ctx, artifact_id).decode("utf-8", errors="strict")

    def excerpt(self, ctx: RequestContext, span: SourceSpan) -> str:
        """Return exactly the artifact text the span addresses, after authorizing the read."""
        return span.excerpt(self.read_text(ctx, span.artifact_id))

    def record_correction(
        self, ctx: RequestContext, original_id: str, corrected: bytes, *, author: str, reason: str
    ) -> tuple[ArtifactRecord, ArtifactRecord]:
        """Store a corrected revision plus its diff. The original artifact is never modified."""
        original = self.get_artifact(ctx, original_id)
        before = self.read_text(ctx, original_id)
        after = corrected.decode("utf-8", errors="strict")
        correction = self.register_artifact(
            original.scope,
            corrected,
            media_type=original.media_type,
            role=ArtifactRole.CORRECTION,
            derived_from=(original_id,),
            derivation=Derivation(method="manual_correction", author=author, reason=reason),
        )
        diff = "".join(
            difflib.unified_diff(
                before.splitlines(keepends=True),
                after.splitlines(keepends=True),
                fromfile=original_id,
                tofile=correction.artifact_id,
            )
        )
        diff_record = self.register_artifact(
            original.scope,
            diff.encode("utf-8"),
            media_type="text/x-diff",
            role=ArtifactRole.CORRECTION_DIFF,
            derived_from=(original_id, correction.artifact_id),
            derivation=Derivation(method="unified_diff", author=author, reason=reason),
        )
        return correction, diff_record

    # ------------------------------------------------------------------------------------
    # Documents, versions, renderings, metadata claims
    # ------------------------------------------------------------------------------------

    def register_document(self, doc: LogicalDocument) -> LogicalDocument:
        with self._tx() as db:
            row = db.execute("SELECT record_json FROM documents WHERE doc_id = ?", (doc.doc_id,)).fetchone()
            if row is not None:
                # Identity fields must agree; descriptive metadata disagreements belong in claims.
                existing = LogicalDocument.model_validate_json(row["record_json"])
                identity = ("key", "source_role", "authority_subtype", "scope")
                if any(getattr(existing, f) != getattr(doc, f) for f in identity):
                    raise RegistryConflict(f"document {doc.doc_id} is already registered with a different identity")
                return existing
            db.execute(
                "INSERT INTO documents VALUES (?, ?, ?, ?)",
                (doc.doc_id, doc.key.tenant_id, doc.model_dump_json(), self._now()),
            )
            self._audit(doc.key.tenant_id, "document_registered", doc.doc_id, {"role": doc.source_role.value})
            return doc

    def get_document(self, ctx: RequestContext, doc_id: str) -> LogicalDocument:
        row = self._db.execute("SELECT record_json FROM documents WHERE doc_id = ?", (doc_id,)).fetchone()
        if row is None:
            raise NotFound("document not found")
        doc = LogicalDocument.model_validate_json(row["record_json"])
        if not is_authorized(ctx, doc.scope):
            raise NotFound("document not found")
        return doc

    def documents(self, tenant_id: str) -> list[LogicalDocument]:
        rows = self._db.execute("SELECT record_json FROM documents WHERE tenant_id = ? ORDER BY doc_id", (tenant_id,))
        return [LogicalDocument.model_validate_json(r["record_json"]) for r in rows]

    def register_version(self, version: OfficialVersion) -> OfficialVersion:
        with self._tx() as db:
            if db.execute("SELECT 1 FROM documents WHERE doc_id = ?", (version.doc_id,)).fetchone() is None:
                raise NotFound(f"document {version.doc_id} is not registered")
            row = db.execute("SELECT record_json FROM versions WHERE version_id = ?", (version.version_id,)).fetchone()
            if row is not None:
                existing = OfficialVersion.model_validate_json(row["record_json"])
                if existing != version:
                    raise RegistryConflict(f"version {version.version_id} is already registered differently")
                return existing
            db.execute(
                "INSERT INTO versions VALUES (?, ?, ?, ?)",
                (version.version_id, version.doc_id, version.model_dump_json(), self._now()),
            )
            return version

    def versions(self, doc_id: str) -> list[OfficialVersion]:
        rows = self._db.execute("SELECT record_json FROM versions WHERE doc_id = ? ORDER BY version_id", (doc_id,))
        return [OfficialVersion.model_validate_json(r["record_json"]) for r in rows]

    def link_rendering(self, version_id: str, artifact_id: str, relation: str) -> None:
        """Record that an artifact claims to render (or describe) a version. Idempotent."""
        with self._tx() as db:
            db.execute("INSERT OR IGNORE INTO renderings VALUES (?, ?, ?)", (version_id, artifact_id, relation))

    def renderings(self, version_id: str) -> dict[str, str]:
        rows = self._db.execute("SELECT artifact_id, relation FROM renderings WHERE version_id = ?", (version_id,))
        return {r["artifact_id"]: r["relation"] for r in rows}

    def record_claims(self, version_id: str, claims: Sequence[MetadataClaim]) -> None:
        with self._tx() as db:
            for claim in claims:
                db.execute(
                    "INSERT OR IGNORE INTO metadata_claims VALUES (?, ?, ?, ?, ?)",
                    (version_id, claim.field, claim.model_dump_json(), claim.basis.value, claim.artifact_id),
                )

    def reconcile_version(self, tenant_id: str, version_id: str) -> MetadataReconciliation:
        """Reconcile all claims; each conflicting field opens one review item (idempotently)."""
        rows = self._db.execute("SELECT claim_json FROM metadata_claims WHERE version_id = ?", (version_id,))
        reconciliation = reconcile_claims(MetadataClaim.model_validate_json(r["claim_json"]) for r in rows)
        with self._tx() as db:
            for conflict in reconciliation.conflicts:
                subject = f"{version_id}#{conflict.field}"
                detail = {
                    "field": conflict.field,
                    "claims": [
                        {"value": str(c.value), "basis": c.basis.value, "artifact_id": c.artifact_id}
                        for c in conflict.claims
                    ],
                }
                db.execute(
                    "INSERT OR IGNORE INTO review_items VALUES (?, ?, ?, ?, ?, ?, ?)",
                    (
                        deterministic_id("rvi", "metadata_conflict", subject, json.dumps(detail, sort_keys=True)),
                        tenant_id,
                        "metadata_conflict",
                        subject,
                        json.dumps(detail, sort_keys=True),
                        "open",
                        self._now(),
                    ),
                )
        return reconciliation

    def review_items(self, tenant_id: str, *, status: str = "open") -> list[dict[str, Any]]:
        rows = self._db.execute(
            "SELECT item_id, kind, subject, detail_json FROM review_items WHERE tenant_id = ? AND status = ? "
            "ORDER BY subject",
            (tenant_id, status),
        )
        return [
            {
                "item_id": r["item_id"],
                "kind": r["kind"],
                "subject": r["subject"],
                "detail": json.loads(r["detail_json"]),
            }
            for r in rows
        ]

    # ------------------------------------------------------------------------------------
    # Builds
    # ------------------------------------------------------------------------------------

    def get_or_create_build(
        self, tenant_id: str, version_id: str | None, artifact_id: str, pipeline_fingerprint: str
    ) -> tuple[str, bool]:
        build_id = deterministic_id("bld", tenant_id, version_id or "-", artifact_id, pipeline_fingerprint)
        with self._tx() as db:
            cursor = db.execute(
                "INSERT OR IGNORE INTO builds VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                (build_id, tenant_id, version_id, artifact_id, pipeline_fingerprint, "staging", None, self._now()),
            )
            return build_id, cursor.rowcount == 1

    def set_build_status(self, build_id: str, status: str, output_artifact_id: str | None = None) -> None:
        with self._tx() as db:
            db.execute(
                "UPDATE builds SET status = ?, output_artifact_id = COALESCE(?, output_artifact_id) WHERE build_id = ?",
                (status, output_artifact_id, build_id),
            )

    def get_build(self, build_id: str) -> dict[str, Any]:
        row = self._db.execute("SELECT * FROM builds WHERE build_id = ?", (build_id,)).fetchone()
        if row is None:
            raise NotFound("build not found")
        return dict(row)

    def builds(self, tenant_id: str) -> list[dict[str, Any]]:
        rows = self._db.execute("SELECT * FROM builds WHERE tenant_id = ? ORDER BY created_at", (tenant_id,))
        return [dict(r) for r in rows]

    # ------------------------------------------------------------------------------------
    # Jobs: idempotent enqueue, leases, heartbeats, attempt budgets, cancellation
    # ------------------------------------------------------------------------------------

    def enqueue_job(
        self, tenant_id: str, kind: str, job_key: str, payload: dict[str, Any], *, max_attempts: int = 3
    ) -> JobRecord:
        job_id = deterministic_id("job", job_key)
        with self._tx() as db:
            db.execute(
                "INSERT OR IGNORE INTO jobs (job_id, job_key, tenant_id, kind, state, max_attempts, payload_json, "
                "created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (
                    job_id,
                    job_key,
                    tenant_id,
                    kind,
                    JobState.QUEUED.value,
                    max_attempts,
                    json.dumps(payload, sort_keys=True),
                    self._now(),
                    self._now(),
                ),
            )
        return self.get_job(job_id)

    def get_job(self, job_id: str) -> JobRecord:
        row = self._db.execute("SELECT * FROM jobs WHERE job_id = ?", (job_id,)).fetchone()
        if row is None:
            raise NotFound("job not found")
        return JobRecord(
            job_id=row["job_id"],
            job_key=row["job_key"],
            tenant_id=row["tenant_id"],
            kind=row["kind"],
            state=JobState(row["state"]),
            attempts=row["attempts"],
            max_attempts=row["max_attempts"],
            lease_owner=row["lease_owner"],
            lease_expires_at=datetime.fromisoformat(row["lease_expires_at"]) if row["lease_expires_at"] else None,
            cancel_requested=bool(row["cancel_requested"]),
            error=row["error"],
            payload=json.loads(row["payload_json"]),
        )

    def jobs(self, tenant_id: str) -> list[JobRecord]:
        rows = self._db.execute("SELECT job_id FROM jobs WHERE tenant_id = ? ORDER BY created_at, job_id", (tenant_id,))
        return [self.get_job(r["job_id"]) for r in rows.fetchall()]

    def claim_job(self, job_id: str, owner: str, *, lease_seconds: float = 60.0) -> Lease | None:
        """Claim a queued job, or one whose lease expired. Returns ``None`` when it cannot be claimed."""
        now = self.clock()
        token = uuid.uuid4().hex
        with self._tx() as db:
            row = db.execute("SELECT * FROM jobs WHERE job_id = ?", (job_id,)).fetchone()
            if row is None:
                raise NotFound("job not found")
            if row["cancel_requested"]:
                db.execute(
                    "UPDATE jobs SET state = ?, lease_token = NULL, updated_at = ? WHERE job_id = ?",
                    (JobState.CANCELLED.value, now.isoformat(), job_id),
                )
                return None
            expired = row["lease_expires_at"] is not None and datetime.fromisoformat(row["lease_expires_at"]) <= now
            claimable = row["state"] == JobState.QUEUED.value or (row["state"] == JobState.RUNNING.value and expired)
            if not claimable:
                return None
            if row["attempts"] >= row["max_attempts"]:
                db.execute(
                    "UPDATE jobs SET state = ?, error = ?, lease_token = NULL, updated_at = ? WHERE job_id = ?",
                    (JobState.FAILED.value, "attempt budget exhausted", now.isoformat(), job_id),
                )
                self._audit(row["tenant_id"], "job_failed", job_id, {"reason": "attempt budget exhausted"})
                return None
            attempt = row["attempts"] + 1
            db.execute(
                "UPDATE jobs SET state = ?, attempts = ?, lease_owner = ?, lease_token = ?, lease_expires_at = ?, "
                "heartbeat_at = ?, updated_at = ? WHERE job_id = ?",
                (
                    JobState.RUNNING.value,
                    attempt,
                    owner,
                    token,
                    (now + timedelta(seconds=lease_seconds)).isoformat(),
                    now.isoformat(),
                    now.isoformat(),
                    job_id,
                ),
            )
            return Lease(job_id=job_id, token=token, owner=owner, attempt=attempt)

    def _check_lease(self, db: sqlite3.Connection, lease: Lease) -> sqlite3.Row:
        row = db.execute("SELECT * FROM jobs WHERE job_id = ?", (lease.job_id,)).fetchone()
        if row is None:
            raise NotFound("job not found")
        if row["cancel_requested"]:
            raise JobCancelled(lease.job_id)
        if (
            row["state"] != JobState.RUNNING.value
            or row["lease_token"] != lease.token
            or datetime.fromisoformat(row["lease_expires_at"]) <= self.clock()
        ):
            raise LeaseLost(lease.job_id)
        return row

    def _with_lease(self, lease: Lease, action: Callable[[sqlite3.Connection, sqlite3.Row], Any]) -> Any:
        """Run ``action`` only while ``lease`` is live; a pending cancellation is committed, then raised."""
        try:
            with self._tx() as db:
                return action(db, self._check_lease(db, lease))
        except JobCancelled:
            with self._tx() as db:
                db.execute(
                    "UPDATE jobs SET state = ?, lease_token = NULL, updated_at = ? WHERE job_id = ? "
                    "AND cancel_requested = 1",
                    (JobState.CANCELLED.value, self._now(), lease.job_id),
                )
            raise

    def heartbeat(self, lease: Lease, *, lease_seconds: float = 60.0) -> None:
        now = self.clock()
        self._with_lease(
            lease,
            lambda db, _: db.execute(
                "UPDATE jobs SET lease_expires_at = ?, heartbeat_at = ?, updated_at = ? WHERE job_id = ?",
                ((now + timedelta(seconds=lease_seconds)).isoformat(), now.isoformat(), now.isoformat(), lease.job_id),
            ),
        )

    def stage_output(self, job_id: str, stage: str) -> dict[str, Any] | None:
        row = self._db.execute(
            "SELECT output_json FROM job_stages WHERE job_id = ? AND stage = ?", (job_id, stage)
        ).fetchone()
        return json.loads(row["output_json"]) if row else None

    def complete_stage(self, lease: Lease, stage: str, output: dict[str, Any]) -> dict[str, Any]:
        """Persist a stage result under a live lease. A replayed stage keeps its first output."""

        def action(db: sqlite3.Connection, _: sqlite3.Row) -> dict[str, Any]:
            db.execute(
                "INSERT OR IGNORE INTO job_stages VALUES (?, ?, ?, ?, ?)",
                (lease.job_id, stage, json.dumps(output, sort_keys=True), self._now(), lease.attempt),
            )
            row = db.execute(
                "SELECT output_json FROM job_stages WHERE job_id = ? AND stage = ?", (lease.job_id, stage)
            ).fetchone()
            return dict(json.loads(row["output_json"]))

        return dict(self._with_lease(lease, action))

    def finish_job(self, lease: Lease) -> None:
        def action(db: sqlite3.Connection, row: sqlite3.Row) -> None:
            db.execute(
                "UPDATE jobs SET state = ?, lease_token = NULL, updated_at = ? WHERE job_id = ?",
                (JobState.SUCCEEDED.value, self._now(), lease.job_id),
            )
            self._audit(row["tenant_id"], "job_succeeded", lease.job_id, {"attempt": lease.attempt})

        self._with_lease(lease, action)

    def fail_attempt(self, lease: Lease, error: str) -> JobState:
        """Release a failed attempt: requeue within the attempt budget, otherwise fail the job."""

        def action(db: sqlite3.Connection, row: sqlite3.Row) -> JobState:
            state = JobState.QUEUED if row["attempts"] < row["max_attempts"] else JobState.FAILED
            db.execute(
                "UPDATE jobs SET state = ?, error = ?, lease_token = NULL, lease_expires_at = NULL, updated_at = ? "
                "WHERE job_id = ?",
                (state.value, error[:2000], self._now(), lease.job_id),
            )
            return state

        return JobState(self._with_lease(lease, action))

    def request_cancel(self, job_id: str) -> JobRecord:
        with self._tx() as db:
            row = db.execute("SELECT state, tenant_id FROM jobs WHERE job_id = ?", (job_id,)).fetchone()
            if row is None:
                raise NotFound("job not found")
            if row["state"] in (JobState.SUCCEEDED.value, JobState.FAILED.value):
                raise RegistryConflict(f"job {job_id} already {row['state']}")
            db.execute("UPDATE jobs SET cancel_requested = 1, updated_at = ? WHERE job_id = ?", (self._now(), job_id))
            if row["state"] == JobState.QUEUED.value:
                db.execute("UPDATE jobs SET state = ? WHERE job_id = ?", (JobState.CANCELLED.value, job_id))
            self._audit(row["tenant_id"], "job_cancel_requested", job_id, {})
        return self.get_job(job_id)

    # ------------------------------------------------------------------------------------
    # Reviews (shared approval contract storage)
    # ------------------------------------------------------------------------------------

    def create_review(
        self,
        tenant_id: str,
        subject_kind: str,
        subject_id: str,
        revision: int,
        content_hash: str,
        record: dict[str, Any],
    ) -> str:
        review_id = deterministic_id("rev", subject_kind, subject_id, str(revision))
        with self._tx() as db:
            row = db.execute("SELECT content_hash FROM reviews WHERE review_id = ?", (review_id,)).fetchone()
            if row is not None:
                if row["content_hash"] != content_hash:
                    raise RegistryConflict("a different proposal already exists for this revision")
                return review_id
            db.execute(
                "INSERT INTO reviews VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (
                    review_id,
                    tenant_id,
                    subject_kind,
                    subject_id,
                    revision,
                    content_hash,
                    json.dumps(record, sort_keys=True),
                    "pending",
                    self._now(),
                ),
            )
            self._audit(tenant_id, "review_created", review_id, {"subject": subject_id, "revision": revision})
        return review_id

    def get_review(self, review_id: str) -> dict[str, Any]:
        row = self._db.execute("SELECT * FROM reviews WHERE review_id = ?", (review_id,)).fetchone()
        if row is None:
            raise NotFound("review not found")
        out = dict(row)
        out["record"] = json.loads(out.pop("record_json"))
        out["decisions"] = [
            json.loads(r["record_json"])
            for r in self._db.execute(
                "SELECT record_json FROM review_decisions WHERE review_id = ? ORDER BY decided_at, decision_id",
                (review_id,),
            )
        ]
        return out

    def apply_decision(
        self,
        review_id: str,
        decision_id: str,
        reviewer_id: str,
        decision: dict[str, Any],
        policy: Callable[[dict[str, Any], dict[str, Any]], str],
    ) -> str:
        """Atomically validate (via ``policy``) and append a decision; returns the new review status.

        ``policy(review, decision)`` sees the review with all earlier decisions and raises to reject.
        Replayed decision IDs and second decisions by the same reviewer are rejected by constraints.
        """
        with self._tx() as db:
            review = self.get_review(review_id)
            if db.execute("SELECT 1 FROM review_decisions WHERE decision_id = ?", (decision_id,)).fetchone():
                raise RegistryConflict("decision already recorded (replay)")
            status = policy(review, decision)
            try:
                db.execute(
                    "INSERT INTO review_decisions VALUES (?, ?, ?, ?, ?)",
                    (decision_id, review_id, reviewer_id, json.dumps(decision, sort_keys=True), self._now()),
                )
            except sqlite3.IntegrityError as exc:
                raise RegistryConflict("reviewer has already decided this review") from exc
            cursor = db.execute(
                "UPDATE reviews SET status = ? WHERE review_id = ? AND status = ?",
                (status, review_id, review["status"]),
            )
            if cursor.rowcount != 1:
                raise RegistryConflict("review changed concurrently")
            self._audit(
                review["tenant_id"],
                "review_decision",
                review_id,
                {"decision_id": decision_id, "reviewer": reviewer_id, "status": status},
            )
            return status

    def set_review_status(self, review_id: str, expected: str, status: str) -> None:
        with self._tx() as db:
            cursor = db.execute(
                "UPDATE reviews SET status = ? WHERE review_id = ? AND status = ?", (status, review_id, expected)
            )
            if cursor.rowcount != 1:
                raise RegistryConflict(f"review {review_id} is not {expected}")


__all__ = [
    "JobCancelled",
    "JobRecord",
    "JobState",
    "Lease",
    "LeaseLost",
    "MetadataBasis",
    "NotFound",
    "Registry",
    "RegistryConflict",
    "RegistryError",
    "SchemaMissing",
    "deterministic_id",
]
