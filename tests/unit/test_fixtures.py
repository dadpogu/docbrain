"""DB-003: supplied artifacts match the fixture inventory, and E-case expectations point at real structure."""

from __future__ import annotations

import hashlib
from typing import Any

import pytest

from docbrain.models import ParsedLegislation
from tests.conftest import REPO, load_fixture

INVENTORY = load_fixture("recycling_act", "inventory.json")
MANIFEST = load_fixture("recycling_act", "manifest.json")
CASES = load_fixture("..", "..", "evals", "recycling_act", "cases.json")["cases"]


@pytest.mark.parametrize("artifact", INVENTORY["artifacts"], ids=lambda a: a["id"])
def test_supplied_artifacts_match_a_recorded_variant(artifact: dict[str, Any]) -> None:
    digest = hashlib.sha256((REPO / artifact["path"]).read_bytes()).hexdigest()
    assert digest in artifact["sha256_variants"].values()
    assert set(artifact["sha256_variants"].values()) <= {a["sha256"] for a in MANIFEST["artifacts"]}


def table_row_supported(parsed: ParsedLegislation, owner: str, row: str) -> bool:
    for table in parsed.tables:
        if table.owner_key == owner and table.evidence_eligible and any(r.key == row for r in table.rows):
            return True
    return False


def unmet(parsed: ParsedLegislation) -> dict[str, list[str]]:
    problems: dict[str, list[str]] = {}
    for case in CASES:
        missing = [k for k in case.get("required_support", []) if k not in parsed.provisions]
        missing += [k for k in case.get("required_structure", []) if k not in parsed.provisions]
        missing += [
            f"{t['owner']}#row{t['row']}"
            for t in case.get("required_table_rows", [])
            if not table_row_supported(parsed, t["owner"], t["row"])
        ]
        missing += [k for k in case.get("expected_absent", []) if k in parsed.provisions]
        repealed = {r.provision for r in parsed.repeals}
        missing += [f"repeal:{k}" for k in case.get("required_repeal_evidence", []) if k not in repealed]
        for query, key in case.get("queries", {}).items():
            found = parsed.find(query)
            if found is None or found.key != key:
                missing.append(f"query:{query}")
        if missing:
            problems[case["id"]] = missing
    return problems


def test_earlier_markdown_supports_every_case_structurally(earlier: ParsedLegislation) -> None:
    assert unmet(earlier) == {}


def test_liteparse_cannot_pass_table_dependent_cases(lite: ParsedLegislation) -> None:
    # The LiteParse candidate keeps its defects visible: unresolved tables and unmarked definitions.
    assert unmet(lite) == {
        "E02": ["s2(1)#row1"],
        "E07": ["s151(1)#row1"],
        "E09": ["s151(1)#row1"],
        "E20": ["s10/def:CEO"],
    }
