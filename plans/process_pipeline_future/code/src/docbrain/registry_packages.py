"""Moved from src/docbrain/registry.py (process application): package tables and Registry methods."""

PACKAGE_SCHEMA = """
CREATE TABLE packages (
    package_id TEXT PRIMARY KEY,
    tenant_id TEXT NOT NULL,
    record_json TEXT NOT NULL,
    current_revision INTEGER,
    approved_revision INTEGER,
    published_revision INTEGER,
    created_at TEXT NOT NULL
);
CREATE TABLE package_revisions (
    package_id TEXT NOT NULL REFERENCES packages(package_id),
    revision INTEGER NOT NULL,
    record_json TEXT NOT NULL,
    status TEXT NOT NULL,
    created_at TEXT NOT NULL,
    PRIMARY KEY (package_id, revision)
);
"""


class RegistryPackagesMixin:  # methods were defined on Registry
    # ------------------------------------------------------------------------------------
    # Documentation packages
    # ------------------------------------------------------------------------------------

    def create_package(self, package_id: str, tenant_id: str, record: dict[str, Any]) -> None:
        with self._tx() as db:
            db.execute(
                "INSERT OR IGNORE INTO packages (package_id, tenant_id, record_json, created_at) VALUES (?, ?, ?, ?)",
                (package_id, tenant_id, json.dumps(record, sort_keys=True), self._now()),
            )

    def get_package(self, package_id: str) -> dict[str, Any]:
        row = self._db.execute("SELECT * FROM packages WHERE package_id = ?", (package_id,)).fetchone()
        if row is None:
            raise NotFound("package not found")
        out = dict(row)
        out["record"] = json.loads(out.pop("record_json"))
        return out

    def add_package_revision(self, package_id: str, record: dict[str, Any], status: str) -> int:
        with self._tx() as db:
            row = db.execute(
                "SELECT COALESCE(MAX(revision), 0) AS rev FROM package_revisions WHERE package_id = ?", (package_id,)
            ).fetchone()
            revision = int(row["rev"]) + 1
            db.execute(
                "INSERT INTO package_revisions VALUES (?, ?, ?, ?, ?)",
                (package_id, revision, json.dumps(record, sort_keys=True), status, self._now()),
            )
            db.execute("UPDATE packages SET current_revision = ? WHERE package_id = ?", (revision, package_id))
            return revision

    def get_package_revision(self, package_id: str, revision: int) -> dict[str, Any]:
        row = self._db.execute(
            "SELECT * FROM package_revisions WHERE package_id = ? AND revision = ?", (package_id, revision)
        ).fetchone()
        if row is None:
            raise NotFound("package revision not found")
        out = dict(row)
        out["record"] = json.loads(out.pop("record_json"))
        return out

    def package_revisions(self, package_id: str) -> list[dict[str, Any]]:
        rows = self._db.execute(
            "SELECT revision FROM package_revisions WHERE package_id = ? ORDER BY revision", (package_id,)
        ).fetchall()
        return [self.get_package_revision(package_id, r["revision"]) for r in rows]

    def transition_package_revision(
        self, package_id: str, revision: int, expected: Sequence[str], status: str, *, pointer: str | None = None
    ) -> None:
        """Compare-and-swap a revision status, optionally moving the approved/published pointer with it."""
        if pointer not in (None, "approved_revision", "published_revision"):
            raise ValueError("unknown package pointer")
        with self._tx() as db:
            placeholders = ",".join("?" for _ in expected)
            cursor = db.execute(
                f"UPDATE package_revisions SET status = ? WHERE package_id = ? AND revision = ? "
                f"AND status IN ({placeholders})",
                (status, package_id, revision, *expected),
            )
            if cursor.rowcount != 1:
                raise RegistryConflict(f"package {package_id} revision {revision} is not in {list(expected)}")
            if pointer:
                db.execute(f"UPDATE packages SET {pointer} = ? WHERE package_id = ?", (revision, package_id))
            tenant = db.execute("SELECT tenant_id FROM packages WHERE package_id = ?", (package_id,)).fetchone()
            self._audit(tenant["tenant_id"], "package_revision_status", f"{package_id}#{revision}", {"status": status})
