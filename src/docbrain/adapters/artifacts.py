"""Immutable, content-addressed artifact bytes (DB-006 local development adapter).

The blob store knows nothing about tenants or permissions: the registry owns artifact records and
authorizes every read before asking for bytes. Paths are derived only from validated SHA-256 digests,
so callers can never supply a filesystem path.
"""

from __future__ import annotations

import hashlib
import os
import re
import tempfile
from pathlib import Path

_DIGEST = re.compile(r"^[0-9a-f]{64}$")


class InvalidArtifactReference(ValueError):
    pass


class ArtifactIntegrityError(RuntimeError):
    pass


class LocalBlobStore:
    def __init__(self, root: Path | str) -> None:
        self.root = Path(root).resolve()
        self.root.mkdir(parents=True, exist_ok=True)

    def _path(self, digest: str) -> Path:
        if not isinstance(digest, str) or not _DIGEST.match(digest):
            raise InvalidArtifactReference("artifact digests are 64 lowercase hex characters")
        path = (self.root / "sha256" / digest[:2] / digest).resolve()
        if not path.is_relative_to(self.root):
            raise InvalidArtifactReference("artifact path escapes the store root")
        return path

    def put(self, data: bytes) -> str:
        digest = hashlib.sha256(data).hexdigest()
        path = self._path(digest)
        if path.exists():
            return digest  # identical bytes are stored once
        path.parent.mkdir(parents=True, exist_ok=True)
        fd, tmp = tempfile.mkstemp(dir=path.parent, prefix=".incoming-")
        try:
            with os.fdopen(fd, "wb") as handle:
                handle.write(data)
                handle.flush()
                os.fsync(handle.fileno())
            os.chmod(tmp, 0o444)
            os.replace(tmp, path)
        except BaseException:
            if os.path.exists(tmp):
                os.unlink(tmp)
            raise
        return digest

    def get(self, digest: str) -> bytes:
        path = self._path(digest)
        data = path.read_bytes()
        if hashlib.sha256(data).hexdigest() != digest:
            raise ArtifactIntegrityError(f"stored bytes for {digest} do not match their digest")
        return data

    def exists(self, digest: str) -> bool:
        return self._path(digest).exists()
