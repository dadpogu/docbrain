"""DB-001: the moved prototype keeps its supported imports and pure behaviors."""

from __future__ import annotations

import hashlib
from fractions import Fraction

import docbrain
from docbrain import CanonicalChunk, QueryIntent, QueryRouter, RetrievalBroker


def test_public_prototype_imports_are_retained() -> None:
    for name in docbrain.__all__:
        assert hasattr(docbrain, name), name


def test_chunk_identity_is_deterministic() -> None:
    chunk = CanonicalChunk.create("doc_x", 7, "Penalty: 60 penalty units.", "Section 142 > (4)", [164])
    again = CanonicalChunk.create("doc_x", 7, "Penalty: 60 penalty units.", "Section 142 > (4)", [164])
    assert chunk.chunk_id == "doc_x#c0007"
    assert chunk.content_hash == hashlib.sha256(b"Penalty: 60 penalty units.").hexdigest()
    assert chunk == again
    assert CanonicalChunk.create("doc_x", 8, "Penalty: 60 penalty units.", "", []).chunk_id != chunk.chunk_id


def test_weighted_rrf_matches_hand_computed_scores_for_asymmetric_ranks() -> None:
    broker = RetrievalBroker(default_k=60)
    fused = broker.compute_weighted_rrf(
        {"vector": [{"id": "A"}, {"id": "B"}, {"id": "C"}], "graph": [{"id": "C"}, {"id": "A"}]},
        {"vector": 1.0, "graph": 2.0},
    )
    # Independently computed: score(d) = sum(weight / (60 + rank)).
    expected = {
        "C": Fraction(1, 63) + Fraction(2, 61),
        "A": Fraction(1, 61) + Fraction(2, 62),
        "B": Fraction(1, 62),
    }
    assert [item["id"] for item in fused] == ["C", "A", "B"]
    for item in fused:
        assert abs(item["rrf_score"] - float(expected[item["id"]])) < 1e-12


def test_router_dispatch_plan_resolves_after_import_fix() -> None:
    router = QueryRouter()
    assert router.fast_classify("What is the exact wording of section 142?") is QueryIntent.FACTUAL_LOOKUP
    assert router.get_dispatch_plan(QueryIntent.FACTUAL_LOOKUP)["target_stores"] == ["vector_store"]
