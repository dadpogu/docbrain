"""
Document Lifecycle & Cascade Invalidation Engine.
Addresses Gap 6: Handling Document Updates, Deletions, Stale Nodes, and Cascade Sync.
"""

from typing import List, Dict, Any, Optional
import hashlib


class DocumentLifecycleManager:
    """
    Ensures transactional consistency across Qdrant and Neo4j when documents are updated or deleted.
    """

    def __init__(self, qdrant_client=None, neo4j_driver=None, cache_client=None):
        self.qdrant = qdrant_client
        self.neo4j = neo4j_driver
        self.cache = cache_client

    @staticmethod
    def compute_doc_hash(raw_bytes: bytes) -> str:
        """Computes SHA-256 fingerprint of the source document."""
        return hashlib.sha256(raw_bytes).hexdigest()

    async def cascade_delete_document(self, doc_id: str) -> Dict[str, Any]:
        """
        Executes a cascade deletion across all 3 representations:
        1. Deletes raw chunks from Qdrant `rag_chunks`.
        2. Deletes RAPTOR tree nodes from Qdrant `rag_semantic_layer`.
        3. Prunes Neo4j entity/relationship provenance and sweeps orphan nodes.
        4. Evicts related semantic cache entries.
        """
        results: Dict[str, Any] = {"doc_id": doc_id, "status": "success", "purged": {}}

        # Step 1: Purge Vector Store Chunks
        if self.qdrant:
            del_vec = await self.qdrant.delete(
                collection_name="rag_chunks",
                points_selector={"filter": {"must": [{"key": "doc_id", "match": {"value": doc_id}}]}}
            )
            results["purged"]["vector_chunks"] = True

            # Step 2: Purge Semantic Layer Tree Nodes
            del_tree = await self.qdrant.delete(
                collection_name="rag_semantic_layer",
                points_selector={"filter": {"must": [{"key": "doc_id", "match": {"value": doc_id}}]}}
            )
            results["purged"]["semantic_tree_nodes"] = True

        # Step 3: Prune Neo4j Knowledge Graph Provenance & Sweep Orphans
        if self.neo4j:
            async with self.neo4j.session() as session:
                # 3a. Remove doc_id from entity provenance
                cypher_prune_entities = """
                MATCH (e:Entity)
                WHERE $doc_id IN e.doc_ids
                SET e.doc_ids = [d IN e.doc_ids WHERE d <> $doc_id],
                    e.source_chunk_ids = [c IN e.source_chunk_ids WHERE NOT c STARTS WITH $doc_prefix]
                WITH e
                WHERE size(e.doc_ids) = 0
                DETACH DELETE e;
                """
                await session.run(cypher_prune_entities, {
                    "doc_id": doc_id,
                    "doc_prefix": f"{doc_id}#"
                })

                # 3b. Sweep orphan relationships with empty provenance
                cypher_prune_relations = """
                MATCH ()-[r]->()
                WHERE ANY(c IN r.source_chunk_ids WHERE c STARTS WITH $doc_prefix)
                SET r.source_chunk_ids = [c IN r.source_chunk_ids WHERE NOT c STARTS WITH $doc_prefix]
                WITH r
                WHERE size(r.source_chunk_ids) = 0
                DELETE r;
                """
                await session.run(cypher_prune_relations, {
                    "doc_prefix": f"{doc_id}#"
                })
                results["purged"]["knowledge_graph_entities_and_relations"] = True

        # Step 4: Evict Semantic Cache
        if self.cache:
            await self.cache.delete_by_tag(doc_id)
            results["purged"]["semantic_cache"] = True

        return results

    async def detect_document_diff(self, doc_id: str, new_chunks: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Determines which chunks were added, modified, or deleted to enable differential re-indexing.
        """
        # Retrieve existing chunk hashes from Qdrant
        existing_hashes = {}
        if self.qdrant:
            existing_records = await self.qdrant.scroll(
                collection_name="rag_chunks",
                scroll_filter={"must": [{"key": "doc_id", "match": {"value": doc_id}}]},
                with_payload=["chunk_id", "content_hash"],
                limit=1000
            )
            for record in existing_records[0]:
                existing_hashes[record.payload["chunk_id"]] = record.payload["content_hash"]

        new_hashes = {c["chunk_id"]: c["content_hash"] for c in new_chunks}

        added = [c for c in new_chunks if c["chunk_id"] not in existing_hashes]
        modified = [
            c for c in new_chunks 
            if c["chunk_id"] in existing_hashes and existing_hashes[c["chunk_id"]] != c["content_hash"]
        ]
        deleted_ids = [cid for cid in existing_hashes if cid not in new_hashes]

        return {
            "doc_id": doc_id,
            "added_count": len(added),
            "modified_count": len(modified),
            "deleted_count": len(deleted_ids),
            "added_chunks": added,
            "modified_chunks": modified,
            "deleted_chunk_ids": deleted_ids
        }
