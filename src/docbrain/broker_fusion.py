"""
Retrieval Broker: Weighted RRF, Cross-Encoder Re-ranking, Deduplication & Evidence Bundling.
Addresses Gap 5: Disparate Score Incommensurability & Evidence Quality Assurance.
"""

from typing import List, Dict, Any, Optional
from collections import defaultdict
from .models import (
    EvidenceBundle, EvidenceItem, EvidenceType, QueryIntent,
    CanonicalChunk, SemanticTreeNode, ProvenanceSpan
)


class RetrievalBroker:
    """
    Coordinates multi-store candidate gathering, rank fusion, cross-encoder scoring,
    and compilation into a verified Evidence Bundle.
    """

    def __init__(self, reranker_client=None, default_k: int = 60, token_limit: int = 3500):
        self.reranker = reranker_client
        self.default_k = default_k
        self.token_limit = token_limit

    def compute_weighted_rrf(
        self,
        ranked_lists: Dict[str, List[Dict[str, Any]]],
        store_weights: Dict[str, float]
    ) -> List[Dict[str, Any]]:
        """
        Combines ranked lists from disparate stores using Weighted Reciprocal Rank Fusion.
        RRF_score(d) = sum(w_s * (1 / (k + rank_s(d))))
        """
        rrf_scores = defaultdict(float)
        candidate_items = {}

        for store_name, items in ranked_lists.items():
            weight = store_weights.get(store_name, 1.0)
            for rank_idx, item in enumerate(items, start=1):
                item_id = item["id"]
                score_increment = weight * (1.0 / (self.default_k + rank_idx))
                rrf_scores[item_id] += score_increment

                if item_id not in candidate_items:
                    candidate_items[item_id] = item
                # Record store contribution
                candidate_items[item_id].setdefault("found_in_stores", []).append(store_name)

        fused_candidates = []
        for item_id, score in rrf_scores.items():
            item = candidate_items[item_id]
            item["rrf_score"] = score
            fused_candidates.append(item)

        fused_candidates.sort(key=lambda x: x["rrf_score"], reverse=True)
        return fused_candidates

    async def rerank_with_cross_encoder(
        self,
        query: str,
        candidates: List[Dict[str, Any]],
        top_n: int = 15
    ) -> List[Dict[str, Any]]:
        """
        Applies a Cross-Encoder to compute calibrated relevance scores [0.0 - 1.0].
        """
        if not candidates:
            return []

        # If reranker client is provided, call cross-encoder; otherwise normalize RRF
        if self.reranker:
            pairs = [[query, c["text"]] for c in candidates]
            scores = await self.reranker.predict(pairs)
            for idx, score in enumerate(scores):
                candidates[idx]["cross_score"] = float(score)
            candidates.sort(key=lambda x: x["cross_score"], reverse=True)
        else:
            # Fallback normalization when reranker is offline
            max_score = candidates[0].get("rrf_score", 1.0) or 1.0
            for c in candidates:
                c["cross_score"] = round(c.get("rrf_score", 0.0) / max_score, 4)

        return candidates[:top_n]

    def deduplicate_and_compress(self, candidates: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Prunes passages with extreme text overlap (e.g., child chunks overlapping section summaries).
        """
        deduped = []
        seen_texts = []

        for c in candidates:
            text = c["text"]
            # Fast Jaccard word-set check to eliminate duplicate passages
            words = set(text.lower().split())
            is_dup = False
            for seen in seen_texts:
                overlap = len(words.intersection(seen)) / max(1, len(words.union(seen)))
                if overlap > 0.85:
                    is_dup = True
                    break
            if not is_dup:
                deduped.append(c)
                seen_texts.append(words)

        return deduped

    def compile_evidence_bundle(
        self,
        query: str,
        intent: QueryIntent,
        fused_items: List[Dict[str, Any]]
    ) -> EvidenceBundle:
        """
        Packages pruned, scored evidence into a typed EvidenceBundle for downstream Agent synthesis.
        """
        evidence_items: List[EvidenceItem] = []
        running_token_count = 0

        for idx, item in enumerate(fused_items, start=1):
            approx_tokens = len(item["text"].split()) * 1.3
            if running_token_count + approx_tokens > self.token_limit:
                break

            citation_id = f"EV-{idx:02d}"
            ev_type = EvidenceType(item.get("evidence_type", EvidenceType.EXACT_EXCERPT))

            prov = None
            if "provenance" in item:
                prov = ProvenanceSpan(**item["provenance"])

            ev = EvidenceItem(
                citation_id=citation_id,
                source_store=item.get("source_store", "VectorStore"),
                evidence_type=ev_type,
                content=item["text"],
                relevance_score=item.get("cross_score", 0.8),
                supporting_chunk_ids=item.get("leaf_chunk_ids", [item.get("id")]),
                provenance=prov,
                graph_path=item.get("graph_path"),
                metadata=item.get("metadata", {})
            )
            evidence_items.append(ev)
            running_token_count += int(approx_tokens)

        return EvidenceBundle(
            query=query,
            classified_intent=intent,
            evidence_items=evidence_items,
            total_sources_consulted=len(fused_items),
            token_budget_used=running_token_count
        )
