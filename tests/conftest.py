from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

import pytest

from docbrain.adapters.artifacts import LocalBlobStore
from docbrain.models import ParsedLegislation, RequestContext
from docbrain.parsing import parse_legislation_markdown
from docbrain.registry import Registry

REPO = Path(__file__).resolve().parents[1]
ASSETS = REPO / "assets"
EARLIER_MD = ASSETS / "parsed" / "GLOBAL.AU" / "C2020A00119-recycling-and-waste-reduction-act-2020.md"
LITEPARSE_MD = ASSETS / "parsed" / "GLOBAL.AU" / "C2026C00317.md"
RAW_DIR = ASSETS / "raw" / "GLOBAL.AU" / "Recycling and Waste Reduction Act 2020"
SIDECAR_JSON = RAW_DIR / "C2026C00317.json"
FIXTURES = REPO / "tests" / "fixtures"


def read_text(path: Path) -> str:
    """Decode bytes exactly (no newline translation), as the parser receives artifacts."""
    return path.read_bytes().decode("utf-8")


def to_lf(text: str) -> str:
    return text.replace("\r\n", "\n")


def to_crlf(text: str) -> str:
    return to_lf(text).replace("\n", "\r\n")


def load_fixture(*parts: str) -> Any:
    return json.loads((FIXTURES.joinpath(*parts)).read_text(encoding="utf-8"))


class FakeClock:
    def __init__(self) -> None:
        self.now = datetime(2026, 10, 25, 9, 0, tzinfo=UTC)

    def __call__(self) -> datetime:
        return self.now

    def advance(self, seconds: float) -> None:
        self.now += timedelta(seconds=seconds)


@pytest.fixture(scope="session")
def expected() -> dict[str, Any]:
    return load_fixture("recycling_act", "expected_structure.json")


@pytest.fixture(scope="session")
def earlier() -> ParsedLegislation:
    return parse_legislation_markdown(read_text(EARLIER_MD), "art_earlier")


@pytest.fixture(scope="session")
def lite_text() -> str:
    return read_text(LITEPARSE_MD)


@pytest.fixture(scope="session")
def lite(lite_text: str) -> ParsedLegislation:
    return parse_legislation_markdown(lite_text, "art_lite")


@pytest.fixture
def clock() -> FakeClock:
    return FakeClock()


@pytest.fixture
def registry(tmp_path: Path, clock: FakeClock) -> Registry:
    reg = Registry(tmp_path / "registry.sqlite3", LocalBlobStore(tmp_path / "blobs"), clock=clock)
    reg.migrate()
    yield reg
    reg.close()


def context(
    tenant: str = "t1",
    *,
    sites: tuple[str, ...] = (),
    roles: tuple[str, ...] = (),
    principal: str = "user-1",
    partitions: tuple[str, ...] = ("internal",),
) -> RequestContext:
    return RequestContext(
        tenant_id=tenant,
        principal_id=principal,
        access_partitions=frozenset(partitions),
        site_ids=frozenset(sites),
        roles=frozenset(roles),
    )
