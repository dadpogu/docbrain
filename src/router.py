"""
Query Intent Classifier & Adaptive Store Router.
Addresses Gap 2: Preventing 3x Query Amplification via Intent Routing & Fallback.
"""

from typing import List, Dict, Tuple, Optional
import json
import re
from .models import QueryIntent


class QueryRouter:
    """
    Two-Tier Adaptive Router:
    Tier 1: High-speed keyword / heuristic rule matcher (sub-millisecond).
    Tier 2: LiteLLM structured intent classification for nuanced / ambiguous queries.
    """

    # Heuristics for Tier 1
    THEMATIC_PATTERNS = [
        r"\b(summarize|summary|overview|high-level|main themes|key takeaways|executive summary)\b",
        r"\b(what does the whole document say|broad scope|synthesis)\b"
    ]
    RELATIONAL_PATTERNS = [
        r"\b(how is .* connected to|relationship between|who owns|affiliated with|subsidiaries of)\b",
        r"\b(multi-hop|path between|supply chain of|governed by)\b"
    ]
    GLOBAL_PATTERNS = [
        r"\b(across all documents|throughout the corpus|recurring issues|systemic risks)\b",
        r"\b(all organizations mentioned|cross-cutting)\b"
    ]
    FACTUAL_PATTERNS = [
        r"\b(section|clause|article|paragraph|page|exact wording|define|definition of)\b",
        r"\b(what is the deadline|penalty amount|interest rate|date of)\b"
    ]

    def __init__(self, litellm_client=None, model: str = "gpt-4o-mini"):
        self.litellm = litellm_client
        self.model = model

    def fast_classify(self, query: str) -> Optional[QueryIntent]:
        """Tier 1: Heuristic classification to avoid LLM invocation for obvious queries."""
        q_lower = query.lower()

        for pattern in self.GLOBAL_PATTERNS:
            if re.search(pattern, q_lower):
                return QueryIntent.GLOBAL_CORPUS

        for pattern in self.THEMATIC_PATTERNS:
            if re.search(pattern, q_lower):
                return QueryIntent.THEMATIC_SUMMARY

        for pattern in self.RELATIONAL_PATTERNS:
            if re.search(pattern, q_lower):
                return QueryIntent.MULTI_HOP_RELATIONAL

        for pattern in self.FACTUAL_PATTERNS:
            if re.search(pattern, q_lower):
                return QueryIntent.FACTUAL_LOOKUP

        return None  # Pass to Tier 2

    async def classify_intent(self, query: str) -> Tuple[QueryIntent, float]:
        """
        Classify intent using Tier 1 rules first, falling back to LLM structured output.
        Returns: (QueryIntent, confidence_score)
        """
        fast_result = self.fast_classify(query)
        if fast_result:
            return fast_result, 0.95

        # Tier 2: LLM Structured Classification
        prompt = f"""You are a specialized query analyzer for a multi-store RAG system.
Given the user query, classify it into exactly ONE of the following categories:
- factual_lookup: Point lookup, specific clauses, numbers, exact definitions, specific facts.
- thematic_summary: High-level overview, multi-section summaries, executive syntheses.
- multi_hop_relational: Questions about entity connections, ownership, relationships, dependencies.
- global_corpus: High-level patterns or clustering across all documents in the corpus.
- complex_hybrid: Multi-part or ambiguous queries requiring vector, graph, and summary perspectives.

User Query: "{query}"

Return valid JSON in this exact structure:
{{"intent": "factual_lookup", "confidence": 0.90, "reasoning": "brief explanation"}}
"""
        if not self.litellm:
            # Default fallback when LLM is unavailable in offline test mode
            return QueryIntent.COMPLEX_HYBRID, 0.50

        try:
            response = await self.litellm.acompletion(
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
                response_format={"type": "json_object"},
                temperature=0.0
            )
            data = json.loads(response.choices[0].message.content)
            intent_str = data.get("intent", "complex_hybrid")
            confidence = float(data.get("confidence", 0.70))
            return QueryIntent(intent_str), confidence
        except Exception:
            return QueryIntent.COMPLEX_HYBRID, 0.50

    def get_dispatch_plan(self, intent: QueryIntent) -> Dict[str, Any]:
        """
        Determines target stores, concurrency, and weight configuration.
        """
        plans = {
            QueryIntent.FACTUAL_LOOKUP: {
                "target_stores": ["vector_store"],
                "weights": {"vector_store": 1.0},
                "min_confidence_threshold": 0.72,
                "enable_fallback": True
            },
            QueryIntent.THEMATIC_SUMMARY: {
                "target_stores": ["semantic_layer"],
                "weights": {"semantic_layer": 1.0},
                "min_confidence_threshold": 0.65,
                "enable_fallback": True
            },
            QueryIntent.MULTI_HOP_RELATIONAL: {
                "target_stores": ["knowledge_graph"],
                "weights": {"knowledge_graph": 1.2, "vector_store": 0.8},
                "min_confidence_threshold": 0.68,
                "enable_fallback": True
            },
            QueryIntent.GLOBAL_CORPUS: {
                "target_stores": ["knowledge_graph_communities", "semantic_layer_l3"],
                "weights": {"knowledge_graph": 1.0, "semantic_layer": 1.0},
                "min_confidence_threshold": 0.60,
                "enable_fallback": True
            },
            QueryIntent.COMPLEX_HYBRID: {
                "target_stores": ["vector_store", "semantic_layer", "knowledge_graph"],
                "weights": {"vector_store": 1.0, "semantic_layer": 0.9, "knowledge_graph": 1.1},
                "min_confidence_threshold": 0.50,
                "enable_fallback": False
            }
        }
        return plans.get(intent, plans[QueryIntent.COMPLEX_HYBRID])
