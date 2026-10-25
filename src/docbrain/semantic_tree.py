"""
Semantic Layer: RAPTOR Tree Construction, Qdrant Persistence, and Hierarchical Traversal.
Addresses Gap 3: Concrete Semantic Layer Storage & Algorithmic Traversal.
"""

from typing import List, Dict, Any, Optional
import numpy as np
from .models import CanonicalChunk, SemanticTreeNode


class RaptorTreeBuilder:
    """
    Constructs a multi-level hierarchical summary tree from raw document chunks.
    Recursively clusters chunks/summaries and generates abstract parent summaries.
    """

    def __init__(self, litellm_client=None, model: str = "gpt-4o-mini", max_levels: int = 3):
        self.litellm = litellm_client
        self.model = model
        self.max_levels = max_levels

    def _cluster_embeddings(self, embeddings: np.ndarray, max_clusters: int = 5) -> List[List[int]]:
        """
        Clusters embeddings into semantic groups using Cosine Distance & Agglomerative/GMM grouping.
        Returns a list of index lists (e.g., [[0, 1, 3], [2, 4]]).
        """
        n_samples = len(embeddings)
        if n_samples <= 2:
            return [list(range(n_samples))]

        # Determine optimal number of clusters
        k = min(max_clusters, max(2, n_samples // 3))
        
        # Simple cosine k-means clustering approximation
        from sklearn.cluster import AgglomerativeClustering
        clustering = AgglomerativeClustering(
            n_clusters=k,
            metric="cosine",
            linkage="average"
        )
        labels = clustering.fit_predict(embeddings)

        clusters: Dict[int, List[int]] = {}
        for idx, label in enumerate(labels):
            clusters.setdefault(label, []).append(idx)
        return list(clusters.values())

    async def _summarize_cluster(self, texts: List[str], level: int) -> Dict[str, str]:
        """Prompts LLM to synthesize related text into a coherent summary."""
        combined_text = "\n---\n".join(texts)
        prompt = f"""You are a document synthesis specialist creating a Level {level} summary.
Below are several related excerpts from a document:
{combined_text}

Task:
1. Provide a concise, highly informative title.
2. Provide a 2-4 sentence synthesis capturing all primary themes, facts, and relationships.

Format your output as:
TITLE: <Your Title>
SUMMARY: <Your Summary>
"""
        if not self.litellm:
            return {
                "title": f"Level {level} Cluster Summary",
                "summary": f"Summary of {len(texts)} sections regarding core concepts."
            }

        response = await self.litellm.acompletion(
            model=self.model,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.1
        )
        content = response.choices[0].message.content
        title = "Summary"
        summary = content
        for line in content.split("\n"):
            if line.startswith("TITLE:"):
                title = line.replace("TITLE:", "").strip()
            elif line.startswith("SUMMARY:"):
                summary = line.replace("SUMMARY:", "").strip()

        return {"title": title, "summary": summary}

    async def build_tree_for_document(
        self,
        doc_id: str,
        chunks: List[CanonicalChunk],
        get_embedding_fn
    ) -> List[SemanticTreeNode]:
        """
        Recursively builds RAPTOR tree from Level 0 (chunks) up to Level 3.
        Returns all created SemanticTreeNode instances across all levels.
        """
        all_tree_nodes: List[SemanticTreeNode] = []

        # Level 0: Wrap chunks as base nodes
        current_level_nodes: List[Dict[str, Any]] = []
        for c in chunks:
            current_level_nodes.append({
                "id": c.chunk_id,
                "text": c.text,
                "embedding": c.dense_vector,
                "leaf_chunks": [c.chunk_id]
            })

        current_level = 1
        while current_level <= self.max_levels and len(current_level_nodes) > 1:
            embeddings = np.array([n["embedding"] for n in current_level_nodes])
            clusters = self._cluster_embeddings(embeddings)

            next_level_nodes: List[Dict[str, Any]] = []

            for cluster_idx, member_indices in enumerate(clusters):
                cluster_members = [current_level_nodes[i] for i in member_indices]
                cluster_texts = [m["text"] for m in cluster_members]
                cluster_children_ids = [m["id"] for m in cluster_members]

                # Flatten leaf chunks
                all_leaf_chunks = []
                for m in cluster_members:
                    all_leaf_chunks.extend(m.get("leaf_chunks", []))

                # Generate summary
                res = await self._summarize_cluster(cluster_texts, current_level)
                node_id = f"{doc_id}#L{current_level}_c{cluster_idx:02d}"
                summary_emb = await get_embedding_fn(res["summary"])

                node = SemanticTreeNode(
                    node_id=node_id,
                    doc_id=doc_id,
                    level=current_level,
                    summary_text=res["summary"],
                    title=res["title"],
                    children_node_ids=cluster_children_ids,
                    leaf_chunk_ids=all_leaf_chunks,
                    embedding=summary_emb
                )
                all_tree_nodes.append(node)

                next_level_nodes.append({
                    "id": node_id,
                    "text": res["summary"],
                    "embedding": summary_emb,
                    "leaf_chunks": all_leaf_chunks
                })

            current_level_nodes = next_level_nodes
            current_level += 1

        return all_tree_nodes


class HierarchicalTreeSearcher:
    """
    Executes hierarchical top-down search or collapsed multi-level search in Qdrant.
    """

    def __init__(self, qdrant_client, collection_name: str = "rag_semantic_layer"):
        self.client = qdrant_client
        self.collection = collection_name

    async def top_down_search(self, query_vector: List[float], top_root_k: int = 2, final_chunk_k: int = 5) -> List[Dict[str, Any]]:
        """
        Step 1: Match top high-level summaries (Level 2 or Level 3).
        Step 2: Collect leaf_chunk_ids from matched summary nodes.
        Step 3: Retrieve and rank only the candidate chunks in Qdrant.
        """
        # Search highest levels first (level >= 2)
        root_results = await self.client.search(
            collection_name=self.collection,
            query_vector=query_vector,
            query_filter={"must": [{"key": "level", "range": {"gte": 2}}]},
            limit=top_root_k
        )

        candidate_chunk_ids = set()
        for hit in root_results:
            candidate_chunk_ids.update(hit.payload.get("leaf_chunk_ids", []))

        if not candidate_chunk_ids:
            return []

        # Retrieve direct raw chunks matching candidate IDs
        chunk_results = await self.client.search(
            collection_name="rag_chunks",
            query_vector=query_vector,
            query_filter={"must": [{"key": "chunk_id", "match": {"any": list(candidate_chunk_ids)}}]},
            limit=final_chunk_k
        )
        return chunk_results

    async def collapsed_search(self, query_vector: List[float], limit: int = 10, level_decay: float = 0.9) -> List[Dict[str, Any]]:
        """
        Searches all levels simultaneously, applying level decay to normalize abstract vs specific matches.
        """
        results = await self.client.search(
            collection_name=self.collection,
            query_vector=query_vector,
            limit=limit
        )
        rescored = []
        for hit in results:
            level = hit.payload.get("level", 0)
            adjusted_score = hit.score * (level_decay ** level)
            rescored.append({
                "node_id": hit.payload.get("node_id"),
                "level": level,
                "text": hit.payload.get("summary_text"),
                "score": adjusted_score,
                "leaf_chunk_ids": hit.payload.get("leaf_chunk_ids", [])
            })
        rescored.sort(key=lambda x: x["score"], reverse=True)
        return rescored
